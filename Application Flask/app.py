from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
)
from datetime import datetime
import time
import sqlite3
import stripe
from faker import Faker
from io import BytesIO
import os
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from flask import jsonify


load_dotenv()  # Load environment variables

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")  # Use the correct key
app.config["SESSION_PERMANENT"] = False  # Optional: Prevents permanent sessions
app.config["SESSION_TYPE"] = "filesystem"  # Ensures sessions are stored properly
bcrypt = Bcrypt(app)

# Flask-Login Setup
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"  # Show flash message on redirect


# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")

# SQLite Database Path
DATABASE = "inventory.db"


# User Model
class User(UserMixin):
    def __init__(self, id, FirstName, LastName, Email, phoneNum, password, is_admin):
        self.id = id
        self.FirstName = FirstName
        self.LastName = LastName
        self.Email = Email
        self.phoneNum = phoneNum
        self.password = password
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)


# Load User for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(
            user["id"],
            user["FirstName"],
            user["LastName"],
            user["Email"],
            user["phoneNum"],
            user["password"],
            user["is_admin"],
        )
    return None  # Explicitly return None if the user is not found


# Function to get database connection
def get_db():
    conn = sqlite3.connect("database.db")  # Ensure this is your actual DB file
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access
    return conn


# Initialize Database


# Route: Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("FirstName")
        last_name = request.form.get("LastName")
        email = request.form.get("Email")
        phone_num = request.form.get("phoneNum")
        password = request.form.get("password")

        print(
            f"Received Data: {first_name}, {last_name}, {email}, {phone_num}, {password}"
        )

        # Validate input fields
        if not all([first_name, last_name, email, phone_num, password]):
            flash("All fields are required.", "warning")
            return render_template("register.html")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO users (FirstName, LastName, Email, phoneNum, password) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (first_name, last_name, email, phone_num, hashed_password),
            )
            conn.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "danger")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("Email")
        password = request.form.get("password")

        conn = get_db()
        cursor = conn.cursor()
        user = cursor.execute(
            "SELECT * FROM users WHERE Email = ?", (email,)
        ).fetchone()
        conn.close()

        if user is None:  # Handle missing user
            flash("User not found. Please register.", "danger")
            return render_template(
                "login.html"
            )  # Return to login page with flash message

        print("Stored Hashed Password:", user["password"])
        print("Entered Password:", password)
        print("Password Match:", bcrypt.check_password_hash(user["password"], password))

        if bcrypt.check_password_hash(user["password"], password):
            user_obj = User(
                user["id"],
                user["FirstName"],
                user["LastName"],
                user["Email"],
                user["phoneNum"],
                user["password"],
                user["is_admin"],
            )
            login_user(user_obj, remember=True)
            session["email"] = email
            flash("Login successful!", "success")

            # Redirect admin (id = 0) to index_admin, others to index
            if user["is_admin"] == 1:
                return redirect(url_for("index_admin"))
            else:
                return redirect(url_for("index_user"))

        flash("Invalid email or password", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    print("Logging out. Session before:", session)
    logout_user()
    print("Session after logout:", session)
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


# Home Page: Display Products
@app.route("/home_user")
@login_required
def index_user():
    print("User authenticated:", current_user.is_authenticated)
    print("Session Data:", session)  # Debug session contents
    print(
        "Current User ID:", session.get("_user_id")
    )  # Flask-Login stores user_id here

    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    products = [dict(product) for product in products]
    return render_template("index.html", products=products)


# Add Product to Cart
@app.route("/add_to_cart/<int:product_id>/<int:quantity>/<int:stock>")
@login_required
def add_to_cart(product_id, quantity, stock):
    # Check if the quantity is valid (greater than 0 and less than or equal to stock)
    if quantity > stock:
        return jsonify(
            {
                "success": False,
                "message": "The selected quantity is greater than the stock.",
            }
        )
    elif quantity <= 0:
        return jsonify(
            {
                "success": False,
                "message": "Invalid quantity value.",
            }
        )
    # Initialize the cart if it doesn't exist
    if "cart" not in session:
        session["cart"] = []

    product_exists = False

    # Check if the product is already in the cart
    for item in session["cart"]:
        if item["product_id"] == product_id:
            # Check if the updated quantity exceeds the stock
            if item["quantity"] + quantity > stock:
                return jsonify(
                    {
                        "success": False,
                        "message": "The selected quantity is greater than the stock.",
                    }
                )

            item["quantity"] += quantity  # Update quantity if product exists
            session.modified = True
            product_exists = True
            return jsonify({"success": True})

    # If the product is not in the cart, add it
    if not product_exists:
        session["cart"].append({"product_id": product_id, "quantity": quantity})
        session.modified = True

    return jsonify({"success": True})


@app.route("/cart")
@login_required
def view_cart():
    cart = session.get("cart", [])  # Retrieve the cart from the session
    conn = get_db()  # Get the database connection
    products = []  # List to store product details
    total = 0  # Variable to store the total price

    for item in cart:
        # Fetch product details from the database
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (item["product_id"],)
        ).fetchone()

        if product:
            # Convert the SQLite row to a dictionary
            product_dict = dict(product)
            # Add the quantity from the cart to the product dictionary
            product_dict["quantity"] = item["quantity"]
            # Add the product to the products list
            products.append(product_dict)
            # Update the total price
            total += product["price"] * item["quantity"]

    conn.close()  # Close the database connection

    # Ensure delivery_cost is defined in the template
    return render_template(
        "cart.html",
        products=products,
        total=total,
        delivery_cost=0,  # Default value (to prevent UndefinedError)
        stripe_public_key=stripe_public_key,
    )


@app.route("/remove_from_cart", methods=["POST"])
@login_required
def remove_from_cart():
    product_id = int(request.form.get("product_id"))  # Get the product ID from the form
    cart = session.get("cart", [])  # Retrieve the cart from the session

    # Find and remove the product from the cart
    updated_cart = [item for item in cart if item["product_id"] != product_id]

    # Update the session's cart
    session["cart"] = updated_cart

    # Redirect back to the cart page
    return redirect(url_for("view_cart"))


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    db = get_db()
    product = db.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    if not product:
        return "Produit non trouvé", 404  # Handle missing product gracefully

    return render_template("product_detail.html", product=product)


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    try:
        # Get the base total (without delivery cost) from the form
        base_total = request.form.get("total", "0")
        base_total = float(base_total) * 100  # Convert to cents

        # Get the delivery option, cost, and address from the form
        delivery_option = request.form.get("delivery_option", "Sans Livraison")
        delivery_cost = request.form.get("delivery_cost", "0")
        delivery_cost = float(delivery_cost) * 100  # Convert to cents
        delivery_address = request.form.get("delivery_address", "")

        # Calculate the final total (base total + delivery cost)
        final_total = base_total + delivery_cost

        # Ensure the final total is valid
        if final_total < 1:
            return "Error: Amount must be greater than 0.", 400

        # Process payment with Stripe
        charge = stripe.Charge.create(
            amount=int(final_total),  # Use the final total (base + delivery)
            currency="eur",
            description="Payment",
            source=request.form.get("stripeToken"),
        )

        if charge["paid"]:  # Payment successful
            conn = get_db()
            cursor = conn.cursor()
            cart = session.get("cart", [])

            # Save each product in the cart to the commande table
            for item in cart:
                cursor.execute(
                    """
                    INSERT INTO commande (product_id, user_id, quantity, address, delivery_option, delivery_cost, total_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["product_id"],
                        current_user.get_id(),
                        item["quantity"],
                        delivery_address,
                        delivery_option,
                        delivery_cost / 100,  # Convert back to EUR
                        final_total / 100,  # Convert back to EUR
                    ),
                )

                # Update stock for each product in the cart
                cursor.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock > ?",
                    (item["quantity"], item["product_id"], item["quantity"] - 1),
                )

            conn.commit()
            conn.close()

            # Generate invoice and clear cart
            session["invoice"] = generate_invoice(
                cart, final_total, delivery_option, delivery_cost
            )
            session["cart"] = []

            return redirect(url_for("invoice"))

        return "Error: Payment failed.", 400

    except stripe.error.StripeError as e:
        return str(e), 400
    except ValueError:
        return "Error: Invalid amount.", 400


@app.route("/invoice")
@login_required
def invoice():
    return render_template("invoice.html")


@app.route("/download_invoice")
@login_required
def download_invoice():
    if not session.get("invoice"):
        return "No invoice available.", 400

    invoice_path = session["invoice"]

    # Read the file as bytes
    with open(invoice_path, "rb") as f:
        invoice_data = f.read()

    return send_file(
        BytesIO(invoice_data),  # Convert bytes to a file-like object
        mimetype="application/pdf",
        as_attachment=True,
        download_name="invoice.pdf",
    )


def generate_invoice(cart, total, delivery_option, delivery_cost):
    # Ensure 'invoices' folder exists
    invoices_folder = "invoices"
    if not os.path.exists(invoices_folder):
        os.makedirs(invoices_folder)

    # Generate unique invoice filename
    invoice_filename = f"invoice_{int(time.time())}.pdf"
    invoice_path = os.path.join(invoices_folder, invoice_filename)

    # Create PDF
    doc = SimpleDocTemplate(invoice_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Company Information
    company_name = "Tech Solutions Inc."
    company_address = "123 Innovation Street, Tech City, TC 45678"
    company_phone = "+1 (555) 123-4567"
    company_email = "support@techsolutions.com"

    story.append(Paragraph(company_name, styles["Title"]))
    story.append(Paragraph(company_address, styles["Normal"]))
    story.append(Paragraph(f"Phone: {company_phone}", styles["Normal"]))
    story.append(Paragraph(f"Email: {company_email}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Invoice Title
    story.append(Paragraph("INVOICE", styles["Heading1"]))
    story.append(Spacer(1, 20))

    # Fetch User Details
    user_id = current_user.get_id()
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        return "Error: User not found", 400

    user_name = f"{user['FirstName']} {user['LastName']}"
    user_email = user["Email"]
    user_phone = user["phoneNum"]

    # User Information
    story.append(Paragraph("Bill To:", styles["Heading2"]))
    story.append(Paragraph(f"Name: {user_name}", styles["Normal"]))
    story.append(Paragraph(f"Email: {user_email}", styles["Normal"]))
    story.append(Paragraph(f"Phone: {user_phone}", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Purchased Items Table
    data = [["Product", "Quantity", "Unit Price", "Total"]]
    conn = get_db()
    for item in cart:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (item["product_id"],)
        ).fetchone()
        if product:
            data.append(
                [
                    product["name"],
                    str(item["quantity"]),
                    f"{product['price']} EUR",
                    f"{product['price'] * item['quantity']} EUR",
                ]
            )
    conn.close()

    # Add Delivery Option to the Table
    data.append(["Livraison", "", "", f"{delivery_cost / 100:.2f} EUR"])

    # Create the table
    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 20))

    # Total Amount
    story.append(Paragraph(f"Total: {total / 100:.2f} EUR", styles["Heading2"]))
    story.append(Spacer(1, 40))

    # Build the PDF
    doc.build(story)

    print(f"Invoice saved at: {invoice_path}")
    return invoice_path  # Return the saved file path


# Home Page: Display Products
@app.route("/home_admin")
@login_required
def index_admin():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("home_admin.html", products=products)


# Add Product Page
@app.route("/add_product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        image_url = request.form["image_url"]

        conn = get_db()
        conn.execute(
            "INSERT INTO products (name, price, stock, image_url) VALUES (?, ?, ?, ?)",
            (name, price, stock, image_url),
        )
        conn.commit()
        conn.close()

        flash("Product added successfully!", "success")
        return redirect(url_for("index_admin"))

    return render_template("add_product.html")


# Update Product Page
@app.route("/update_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def update_product(product_id):
    conn = get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        image_url = request.form["image_url"]

        conn.execute(
            "UPDATE products SET name=?, price=?, stock=?, image_url=? WHERE id=?",
            (name, price, stock, image_url, product_id),
        )
        conn.commit()
        conn.close()

        flash("Product updated successfully!", "success")
        return redirect(url_for("index_admin"))

    return render_template("update_product.html", product=product)


# Delete Product Page
@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    flash("Product deleted successfully!", "danger")
    return redirect(url_for("index_admin"))


@app.route("/aboutus")
def about_us():
    return render_template("about_us.html")


@app.route("/contactus")
def contact_us():
    return render_template("contact_us.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Get form data
        user_id = session.get("_user_id")
        objet = request.form["email"]
        message_text = request.form["message"]
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert data into the database
        conn = get_db()
        conn.execute(
            """
            INSERT INTO messages (user_id, objet, message, date, is_treated)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user_id, objet, message_text, current_date, 0),
        )
        conn.commit()
        conn.close()

        # Return a JSON response indicating success
        return jsonify(
            {
                "success": True,
                "message": "Thank you! We will treat your message in the nearest time.",
            }
        )

    # If GET request, just render the contact page
    return render_template("contact_us.html")


@app.route("/get_messages", methods=["GET"])
def get_messages():
    user_id = session.get("_user_id")
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    # Fetch messages from the database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT messages.id, messages.objet, messages.message, messages.date, messages.is_treated, messages.admin_response, users.FirstName, users.LastName
        FROM messages
        JOIN users ON messages.user_id = users.id
        WHERE messages.user_id = ?
        ORDER BY messages.date DESC
        """,
        (user_id,),
    )
    messages = cursor.fetchall()
    conn.close()

    # Convert the result to a list of dictionaries
    messages_list = [
        {
            "id": msg[0],
            "objet": msg[1],
            "message": msg[2],
            "date": msg[3],
            "is_treated": msg[4],
            "admin_response": msg[5],  # Include admin_response
            "user_name": f"{msg[6]} {msg[7]}",  # Combine first and last name
        }
        for msg in messages
    ]

    return jsonify(messages_list)


@app.route("/admin/reply", methods=["POST"])
def admin_reply():
    message_id = request.form.get("message_id")
    admin_response = request.form.get("response")

    # Update the database: mark as treated and store the response
    conn = get_db()
    conn.execute(
        """
        UPDATE messages
        SET is_treated = 1, admin_response = ?
        WHERE id = ?
        """,
        (admin_response, message_id),
    )
    conn.commit()
    conn.close()

    # Optionally, send an email to the user with the response
    # (You can use Flask-Mail or another email library for this)

    return jsonify({"success": True, "message": "Reply sent successfully!"})


@app.route("/admin/messages", methods=["GET"])
def admin_messages():
    # Get filter parameters from the request
    status_filter = request.args.get("status", "pending")  # Default: pending
    date_filter = request.args.get("date", "")  # Default: all dates
    email_filter = request.args.get("email", "")  # Default: all emails

    # Build the SQL query based on filters
    query = """
        SELECT messages.id, messages.objet, messages.message, messages.date, messages.is_treated, messages.admin_response, users.FirstName, users.LastName, users.Email
        FROM messages
        JOIN users ON messages.user_id = users.id
        WHERE 1=1
    """
    params = []

    # Status filter
    if status_filter == "pending":
        query += " AND messages.is_treated = 0"
    elif status_filter == "treated":
        query += " AND messages.is_treated = 1"

    # Date filter
    if date_filter == "last_day":
        query += " AND messages.date >= datetime('now', '-1 day')"
    elif date_filter == "last_week":
        query += " AND messages.date >= datetime('now', '-7 days')"
    elif date_filter == "last_month":
        query += " AND messages.date >= datetime('now', '-1 month')"

    # Email filter
    if email_filter:
        query += " AND users.Email LIKE ?"
        params.append(f"%{email_filter}%")

    # Order by date (newest first)
    query += " ORDER BY messages.date DESC"

    # Fetch messages from the database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    messages = cursor.fetchall()
    conn.close()

    # Convert the result to a list of dictionaries
    messages_list = [
        {
            "id": msg[0],
            "objet": msg[1],
            "message": msg[2],
            "date": msg[3],
            "is_treated": msg[4],
            "admin_response": msg[5],
            "user_name": f"{msg[6]} {msg[7]}",  # Combine first and last name
            "user_email": msg[8],  # User email
        }
        for msg in messages
    ]

    return render_template("admin_messages.html", messages=messages_list)


# add_sample_products()

if __name__ == "__main__":
    app.run(debug=True)
