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
            # return render_template("login.html")

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
@app.route("/add_to_cart/<int:product_id>/<int:quantity>")
@login_required
def add_to_cart(product_id, quantity):
    if "cart" not in session:
        session["cart"] = []

    # Check if the product is already in the cart
    for item in session["cart"]:
        if item["product_id"] == product_id:
            item["quantity"] += quantity  # Update quantity if product exists
            session.modified = True
            return redirect(url_for("index_user"))

    # If the product is not in the cart, add it
    session["cart"].append({"product_id": product_id, "quantity": quantity})
    session.modified = True
    return redirect(url_for("index_user"))


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

    # Render the cart template with the products and total price
    return render_template(
        "cart.html",
        products=products,
        total=total,
        stripe_public_key=stripe_public_key,
    )


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
        total = request.form.get("total", "0")
        total = float(total) * 100  # Convert to cents

        if total < 1:
            return "Error: Amount must be greater than 0.", 400

        # Process payment
        charge = stripe.Charge.create(
            amount=int(total),
            currency="eur",
            description="Payment",
            source=request.form.get("stripeToken"),
        )

        if charge["paid"]:  # Payment successful
            conn = get_db()
            cart = session.get("cart", [])

            # Update stock for each product in the cart
            for item in cart:
                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock > ?",
                    (item["quantity"], item["product_id"], item["quantity"] - 1),
                )

            conn.commit()
            conn.close()

            # Generate invoice and clear cart
            session["invoice"] = generate_invoice(cart, total)
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


def generate_invoice(cart, total):
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


# Initialize Database

# add_sample_products()

if __name__ == "__main__":
    app.run(debug=True)
