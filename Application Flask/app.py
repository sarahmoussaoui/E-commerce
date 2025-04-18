from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    flash,
    jsonify,
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
from flask_mail import Mail, Message

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from datetime import datetime  # This imports the datetime class
import datetime as dt_module
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
)
from reportlab.lib import colors

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
bcrypt = Bcrypt(app)

# Flask-Login Setup
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"

# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")


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
    return None


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()

        # Create users table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            FirstName TEXT NOT NULL,
            LastName TEXT NOT NULL,
            Email TEXT UNIQUE NOT NULL,
            phoneNum TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
        """
        )

        # Create products table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_url TEXT
        )
        """
        )

        # Create enchere table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS enchere (
            id_enchere INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            prix REAL NOT NULL,
            date_fin TEXT NOT NULL,
            adresse TEXT,
            etat TEXT DEFAULT 'active'
        )
        """
        )

        # Create historique_enchere table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS historique_enchere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_enchere INTEGER NOT NULL,
            id_user INTEGER NOT NULL,
            proposed_price REAL NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_enchere) REFERENCES enchere(id_enchere),
            FOREIGN KEY (id_user) REFERENCES users(id)
        )
        """
        )

        # Create commande table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS commande (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            delivery_option TEXT NOT NULL,
            delivery_cost REAL NOT NULL,
            total_amount REAL NOT NULL,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        )

        # Create commande_items table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS commande_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            FOREIGN KEY (commande_id) REFERENCES commande(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
        )

        # Create messages table
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            objet TEXT NOT NULL,
            message TEXT NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            is_treated INTEGER DEFAULT 0,
            admin_response TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        )

        conn.commit()
        conn.close()


# Initialize database tables
init_db()


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("FirstName")
        last_name = request.form.get("LastName")
        email = request.form.get("Email")
        phone_num = request.form.get("phoneNum")
        password = request.form.get("password")

        if not all([first_name, last_name, email, phone_num, password]):
            flash("All fields are required.", "warning")
            return render_template("register.html")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (FirstName, LastName, Email, phoneNum, password) VALUES (?, ?, ?, ?, ?)",
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
        user = conn.execute("SELECT * FROM users WHERE Email = ?", (email,)).fetchone()
        conn.close()

        if user is None:
            flash("User not found. Please register.", "danger")
            return render_template("login.html")

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
            session["user_id"] = user["id"]
            session["email"] = email
            flash("Login successful!", "success")

            if user["is_admin"] == 1:
                return redirect(url_for("home_admin"))
            else:
                return redirect(url_for("home"))

        flash("Invalid email or password", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


@app.route("/home_admin")
@login_required
def home_admin():
    if not current_user.is_admin:
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()

    # Existing counts
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM enchere WHERE etat = 'active'")
    auction_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM commande WHERE status = 'pending'")
    order_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM messages WHERE is_treated = 0")
    message_count = cursor.fetchone()[0]

    # NEW: Get recent orders (last 5 orders)
    cursor.execute(
        """
        SELECT 
            c.id, 
            u.FirstName, 
            u.LastName, 
            c.total_amount, 
            c.order_date, 
            c.status
        FROM commande c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.order_date DESC
        LIMIT 5
    """
    )
    recent_orders = cursor.fetchall()

    conn.close()

    return render_template(
        "home_admin.html",
        product_count=product_count,
        auction_count=auction_count,
        order_count=order_count,
        message_count=message_count,
        recent_orders=recent_orders,  # NEW: Pass recent orders to template
    )


@app.route("/order_details/<int:order_id>")
@login_required
def order_details(order_id):
    conn = get_db()
    cursor = conn.cursor()

    # Get order details
    cursor.execute(
        """
        SELECT c.*, u.FirstName, u.LastName 
        FROM commande c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = ?
    """,
        (order_id,),
    )
    order = cursor.fetchone()

    # Get order items
    cursor.execute(
        """
        SELECT ci.*, p.name as product_name , p.image_url as product_img
        FROM commande_items ci
        JOIN products p ON ci.product_id = p.id
        WHERE ci.commande_id = ?
    """,
        (order_id,),
    )
    items = cursor.fetchall()

    conn.close()

    return render_template("admin_orders_details.html", order=order, items=items)


# ... (Additional routes would continue here with the same pattern of fixes)


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

        # Get delivery details from the form
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

            # Step 1: Insert into `commande` (order-level details)
            cursor.execute(
                """
                INSERT INTO commande (user_id, address, delivery_option, delivery_cost, total_amount, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (
                    current_user.get_id(),
                    delivery_address,
                    delivery_option,
                    delivery_cost / 100,  # Convert back to EUR
                    final_total / 100,  # Convert back to EUR
                ),
            )
            commande_id = cursor.lastrowid  # Get the last inserted commande ID

            # Step 2: Insert each product into `commande_items`
            for item in cart:
                # Get the product's price to store historical data
                cursor.execute(
                    "SELECT price FROM products WHERE id = ?", (item["product_id"],)
                )
                product = cursor.fetchone()
                if not product:
                    continue  # Skip if product doesn't exist (edge case)

                price_per_unit = product[0]

                cursor.execute(
                    """
                    INSERT INTO commande_items (commande_id, product_id, quantity, price_per_unit)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        commande_id,
                        item["product_id"],
                        item["quantity"],
                        price_per_unit,
                    ),
                )

                # Step 3: Update stock for each product
                cursor.execute(
                    """
                    UPDATE products 
                    SET stock = stock - ? 
                    WHERE id = ? AND stock >= ?
                    """,
                    (item["quantity"], item["product_id"], item["quantity"]),
                )

            conn.commit()
            conn.close()

            # Step 4: Generate invoice & clear cart
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
    invoice_filename = f"handmade_invoice_{int(time.time())}.pdf"
    invoice_path = os.path.join(invoices_folder, invoice_filename)

    # Create PDF with elegant styling
    doc = SimpleDocTemplate(
        invoice_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=60,
    )
    styles = getSampleStyleSheet()

    # Add custom styles
    styles.add(
        ParagraphStyle(
            name="HandmadeTitle",
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#8B5A2B"),  # Warm brown
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="HandmadeSubtitle",
            fontSize=12,
            textColor=colors.HexColor("#555555"),
            fontName="Helvetica-Oblique",
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="HandmadeHeading",
            fontSize=14,
            textColor=colors.HexColor("#8B5A2B"),
            fontName="Helvetica-Bold",
            spaceAfter=10,
        )
    )

    story = []

    # Beautiful Header with Handmade Theme
    logo_path = "path_to_your_logo.png"  # Add your logo here
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=100, height=100))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Artisan's Touch Collections", styles["HandmadeTitle"]))
    story.append(Paragraph("Handcrafted with Love & Care", styles["HandmadeSubtitle"]))
    story.append(Spacer(1, 5))

    # Company Information with elegant styling
    company_address = "123 Crafters Lane, Artisan Valley, AV 98765"
    company_phone = "+1 (555) 987-6543"
    company_email = "hello@artisanstouch.com"
    company_social = "@ArtisansTouch"

    contact_info = f"""
    <font color='#555555'>{company_address}</font><br/>
    <font color='#555555'>Phone: {company_phone}</font><br/>
    <font color='#555555'>Email: {company_email}</font><br/>
    <font color='#8B5A2B'>Follow us: {company_social}</font>
    """

    story.append(Paragraph(contact_info, styles["Normal"]))
    story.append(Spacer(1, 30))

    # Invoice Title with decorative line
    story.append(Paragraph("INVOICE", styles["HandmadeTitle"]))
    story.append(
        HRFlowable(
            width="100%", thickness=1, lineCap="round", color=colors.HexColor("#D2B48C")
        )
    )  # Tan color
    story.append(Spacer(1, 30))

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

    # User Information with beautiful formatting
    customer_info = f"""
    <b><font color='#8B5A2B'>Bill To:</font></b><br/>
    <font color='#555555'>{user_name}</font><br/>
    <font color='#555555'>{user_email}</font><br/>
    <font color='#555555'>{user_phone}</font>
    """
    story.append(Paragraph(customer_info, styles["Normal"]))
    story.append(Spacer(1, 30))

    # Purchased Items Table with handmade aesthetic
    data = [["Handmade Item", "Quantity", "Unit Price", "Total"]]
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
    # Simple delivery line
    data.append(["", "", "Delivery", f"{delivery_cost / 100:.2f} EUR"])

    # Create the table with beautiful styling
    table = Table(data, colWidths=[200, 60, 80, 80])
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#D2B48C"),
                ),  # Header color
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -2),
                    colors.HexColor("#FAF0E6"),
                ),  # Light beige
                ("BACKGROUND", (-1, -1), (-1, -1), colors.HexColor("#FAF0E6")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#555555")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D2B48C")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 30))

    # Total Amount with emphasis
    total_text = f"""
    <b><font color='#8B5A2B' size=14>Total Amount:</font></b>
    <font size=14 color='#8B5A2B'> {total / 100:.2f} EUR</font>
    """
    story.append(Paragraph(total_text, styles["Normal"]))
    story.append(Spacer(1, 40))

    # Thank You Message
    appreciation = """
    <i><font color='#8B5A2B'>
    Thank you for supporting handmade craftsmanship!<br/>
    Each item is lovingly created by our artisans.<br/>
    We hope it brings you as much joy as it did us to make it.
    </font></i>
    """
    story.append(Paragraph(appreciation, styles["HandmadeSubtitle"]))
    story.append(Spacer(1, 20))

    # Build the PDF
    doc.build(story)

    print(f"Beautiful invoice saved at: {invoice_path}")
    return invoice_path


# Home Page: Display Products
@app.route("/gestion_produits")
@login_required
def gestion_produits():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("gestion_produits.html", products=products)


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

        return redirect(url_for("gestion_produits"))

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

        return redirect(url_for("gestion_produits"))

    return render_template("update_product.html", product=product)


# Delete Product Page
@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("gestion_produits"))


#  Encheres


@app.route("/gestion_encheres")
@login_required
def gestion_encheres():
    conn = get_db()
    encheres = conn.execute("SELECT * FROM enchere").fetchall()

    # Convert date strings to datetime objects
    processed_encheres = []
    for enchere in encheres:
        enchere_dict = dict(enchere)
        enchere_dict["date_fin"] = datetime.strptime(
            enchere_dict["date_fin"], "%Y-%m-%d"
        )
        processed_encheres.append(enchere_dict)

    conn.close()
    return render_template(
        "gestion_encheres.html",
        encheres=processed_encheres,
        current_date=datetime.now(),
    )


@app.route("/add_enchere", methods=["GET", "POST"])
@login_required
def add_enchere():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        image_url = request.form["image_url"]
        prix = float(request.form["prix"])
        date_fin = request.form["date_fin"]
        adresse = request.form["adresse"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO enchere (name, description, image_url, prix, date_fin,adresse) VALUES (?, ?, ?, ?, ?,?)",
            (name, description, image_url, prix, date_fin, adresse),
        )
        conn.commit()
        conn.close()

        return redirect(url_for("gestion_encheres"))

    return render_template("add_enchere.html")


@app.route("/update_enchere/<int:enchere_id>", methods=["GET", "POST"])
@login_required
def update_enchere(enchere_id):
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the auction details
    enchere = cursor.execute(
        "SELECT * FROM enchere WHERE id_enchere = ?", (enchere_id,)
    ).fetchone()

    if not enchere:
        return redirect(url_for("gestion_encheres"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        image_url = request.form["image_url"]
        prix = float(request.form["prix"])
        date_fin = request.form["date_fin"]
        adresse = request.form["adresse"]

        cursor.execute(
            """
    UPDATE enchere 
    SET name=?, description=?, image_url=?, prix=?, date_fin=?, adresse=?
    WHERE id_enchere=?
    """,
            (name, description, image_url, prix, date_fin, adresse, enchere_id),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("gestion_encheres"))

    return render_template("update_enchere.html", enchere=enchere)


@app.route("/delete_enchere/<int:enchere_id>", methods=["POST"])
@login_required
def delete_enchere(enchere_id):
    conn = get_db()
    cursor = conn.cursor()

    # Delete bids associated with this auction first
    cursor.execute("DELETE FROM historique_enchere WHERE id_enchere = ?", (enchere_id,))

    # Then delete the auction itself
    cursor.execute("DELETE FROM enchere WHERE id_enchere = ?", (enchere_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("gestion_encheres"))


@app.route("/home_page")
def home():
    return render_template("home.html")


@app.route("/aboutus")
def about_us():
    return render_template("about_us.html")


@app.route("/contactus")
def contact_us():
    return render_template("contact_us.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Get form data and user info
        user_id = session.get("_user_id")
        if not user_id:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        # Get the subject and message from form
        subject = request.form.get("subject")
        message_text = request.form.get("message")

        if not subject or not message_text:
            return (
                jsonify(
                    {"success": False, "message": "Subject and message are required"}
                ),
                400,
            )

        # Get current datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert data into the database
        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO messages (user_id, objet, message, date, is_treated)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, subject, message_text, current_date, 0),
            )
            conn.commit()
            return jsonify(
                {
                    "success": True,
                    "message": "Thank you! We will respond to your message soon.",
                }
            )
        except Exception as e:
            conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Error saving your message. Please try again.",
                    }
                ),
                500,
            )
        finally:
            conn.close()

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


@app.route("/admin/orders")
def admin_orders():
    cursor = get_db()

    # Fetch all orders with user and product information
    orders = cursor.execute(
        """
        SELECT 
            commande.id as order_id, 
            commande.user_id, 
            users.FirstName, 
            users.LastName, 
            users.Email, 
            commande.address, 
            commande.delivery_option, 
            commande.delivery_cost, 
            commande.total_amount, 
            commande.order_date, 
            commande.status,
            commande_items.product_id,
            products.name as product_name,
            commande_items.quantity,
            commande_items.price_per_unit
        FROM commande
        JOIN users ON commande.user_id = users.id
        JOIN commande_items ON commande.id = commande_items.commande_id
        JOIN products ON commande_items.product_id = products.id
        """
    ).fetchall()

    # Calculate summary statistics

    # Initialize counters
    pending_count = 0
    today_count = 0
    today = datetime.now().date()

    orders_dict = {}
    for order in orders:
        order_id = order["order_id"]
        if order_id not in orders_dict:
            orders_dict[order_id] = {
                "user_id": order["user_id"],
                "FirstName": order["FirstName"],
                "LastName": order["LastName"],
                "Email": order["Email"],
                "address": order["address"],
                "delivery_option": order["delivery_option"],
                "delivery_cost": order["delivery_cost"],
                "total_amount": order["total_amount"],
                "order_date": (
                    datetime.strptime(order["order_date"], "%Y-%m-%d %H:%M:%S").date()
                    if isinstance(order["order_date"], str)
                    else order["order_date"]
                ),
                "status": order["status"],
                "order_items": [],
            }

            # Count pending orders
            if order["status"].lower() == "pending":
                pending_count += 1

            # Count today's orders
            order_date = orders_dict[order_id]["order_date"]
            if isinstance(order_date, str):
                order_date = datetime.strptime(order_date, "%Y-%m-%d %H:%M:%S").date()
            if order_date == today:
                today_count += 1

        orders_dict[order_id]["order_items"].append(
            {
                "product_id": order["product_id"],
                "product_name": order["product_name"],
                "quantity": order["quantity"],
                "price_per_unit": order["price_per_unit"],
            }
        )

    cursor.close()

    return render_template(
        "admin_orders.html",
        orders=orders_dict,
        total_orders=len(orders_dict),
        pending_orders=pending_count,
        today_orders=today_count,
    )


@app.route("/admin/update_order_status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    new_status = request.form["status"]
    conn = conn = get_db()
    cursor = conn.cursor()

    # Update the order status
    cursor.execute(
        """
        UPDATE commande
        SET status = ?
        WHERE id = ?
    """,
        (new_status, order_id),
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_orders"))


@app.route("/encherir", methods=["POST"])
@app.route("/encherir", methods=["POST"])
def encherir():
    try:
        data = request.json
        enchere_id = data.get("id_enchere")
        prix = float(data.get("prix"))  # Convertir en float
        first_name = data.get("firstName")
        last_name = data.get("lastName")
        email = data.get("email")
        phone = data.get("phone")

        db = get_db()
        cursor = db.cursor()

        # Vérifier si l'utilisateur existe
        cursor.execute("SELECT id FROM users WHERE Email = ?", (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 400

        user_id = user["id"]

        # Enregistrer l'enchère dans historique_enchere
        cursor.execute(
            """
            INSERT INTO historique_enchere (id_enchere, id_user, proposed_price)
            VALUES (?, ?, ?)
            """,
            (enchere_id, user_id, prix),
        )

        # Mettre à jour le prix de départ dans enchere
        cursor.execute(
            """
            UPDATE enchere
            SET prix = ?
            WHERE id_enchere = ?
            """,
            (prix, enchere_id),
        )

        db.commit()

        return jsonify({"message": "Enchère enregistrée avec succès !"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


from datetime import datetime


@app.route("/admin/historique_encheres", methods=["GET"])
def historique_encheres():
    conn = get_db()
    cursor = conn.cursor()

    # Get current date
    current_date = datetime.now().date()

    # SQL Query to join historique_enchere, enchere, and users tables
    cursor.execute(
        """
        SELECT 
            e.image_url, 
            e.name AS enchere_name, 
            e.date_fin, 
            u.FirstName || ' ' || u.LastName AS user_full_name, 
            u.phoneNum,
            h.proposed_price,
            e.etat,
            CASE 
                WHEN e.etat = 'Annulée' THEN 'Annulée'
                WHEN e.date_fin < ? THEN 'Terminée'
                ELSE 'En cours'
            END AS calculated_etat
        FROM historique_enchere h
        JOIN enchere e ON h.id_enchere = e.id_enchere
        JOIN users u ON h.id_user = u.id
        ORDER BY e.name, h.proposed_price DESC, e.date_fin DESC
    """,
        (current_date,),
    )

    historique = cursor.fetchall()

    # Count completed auctions
    completed_count = sum(
        1 for item in historique if item["calculated_etat"] == "Terminée"
    )

    conn.close()

    return render_template(
        "historique_encheres.html",
        historique=historique,
        completed_count=completed_count,
    )


@app.route("/encheres")
@login_required
def encher_user():
    conn = get_db()
    encheres = conn.execute("SELECT * FROM enchere").fetchall()
    conn.close()
    today = datetime.now().date()
    encheres = [dict(enchere) for enchere in encheres]
    return render_template(
        "encher_user.html", encheres=encheres, today=today, datetime=dt_module
    )


@app.route("/enchere/<int:enchere_id>")
@login_required
def enchere_detail(enchere_id):
    db = get_db()

    # Get auction details
    enchere = db.execute(
        "SELECT * FROM enchere WHERE id_enchere = ?", (enchere_id,)
    ).fetchone()

    if not enchere:
        abort(404, "Auction not found")

    # Get highest bid
    highest_bid = (
        db.execute(
            "SELECT MAX(proposed_price) FROM historique_enchere WHERE id_enchere = ?",
            (enchere_id,),
        ).fetchone()[0]
        or enchere["prix"]
    )  # Default to starting price if no bids

    # Calculate auction status
    try:
        end_date = datetime.strptime(enchere["date_fin"], "%Y-%m-%d").date()
        today = datetime.now().date()
        is_ended = end_date < today
    except ValueError as e:
        abort(500, f"Invalid date format in database: {str(e)}")

    # Get bid count and bid history
    bid_count = db.execute(
        "SELECT COUNT(*) FROM historique_enchere WHERE id_enchere = ?", (enchere_id,)
    ).fetchone()[0]

    # Get all bids for this auction (sorted by price descending)
    bids = db.execute(
        "SELECT * FROM historique_enchere WHERE id_enchere = ? ORDER BY proposed_price DESC",
        (enchere_id,),
    ).fetchall()

    return render_template(
        "enchere_detail.html",
        enchere=enchere,
        user=current_user,
        highest_bid=highest_bid,
        is_ended=is_ended,
        bid_count=bid_count,
        bids=bids,
        today_date=today,  # Pass as date object for Python comparisons
        today_str=today.strftime("%Y-%m-%d"),  # Pass as string for display/JS
        datetime=dt_module,  # Pass datetime module for template usage
        end_date_str=enchere["date_fin"],  # Original string from DB
    )


@app.route("/ajouter_enchere", methods=["POST"])
def ajouter_enchere():
    data = request.json
    id_enchere = data.get("id_enchere")
    prix = data.get("prix")
    nom = data.get("nom")
    email = data.get("email")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Récupérer l'utilisateur basé sur l'email
    cursor.execute("SELECT id FROM users WHERE Email = ?", (email,))
    user = cursor.fetchone()

    if user:
        id_user = user[0]
    else:
        return jsonify({"message": "Utilisateur non trouvé"}), 400

    # Insérer l'enchère dans la table historique_enchere
    cursor.execute(
        "INSERT INTO historique_enchere (id_enchere, id_user, proposed_price) VALUES (?, ?, ?)",
        (id_enchere, id_user, prix),
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Votre enchère a été enregistrée avec succès!"})


# fonction pour afficher mes encheres
@app.route("/admin/auction_winners", methods=["GET", "POST"])
def auction_winners():
    conn = get_db()
    cursor = conn.cursor()

    # Handle email sending
    if request.method == "POST":
        recipient_email = request.form["recipient_email"]
        message_subject = request.form["message_subject"]
        message_body = request.form["message_body"]

        try:
            # Create and send the email
            msg = Message(
                subject=message_subject, recipients=[recipient_email], body=message_body
            )
            mail.send(msg)
            flash(f"Email sent successfully to {recipient_email}", "success")
        except Exception as e:
            app.logger.error(f"Failed to send email: {str(e)}")
            flash(f"Failed to send email: {str(e)}", "error")

        return redirect(url_for("auction_winners"))

    # Get auctions with their highest bids and bidder info
    cursor.execute(
        """
        SELECT 
            e.id_enchere,
            e.name AS auction_name,
            e.image_url,
            e.date_fin,
            MAX(h.proposed_price) AS winning_bid,
            u.id AS winner_id,
            u.FirstName || ' ' || u.LastName AS winner_name,
            u.Email AS winner_email,
            u.phoneNum AS winner_phone,
            e.etat,
            CASE 
                WHEN e.etat = 'Annulée' THEN 'Annulée'
                WHEN e.date_fin < date('now') THEN 'Terminée'
                ELSE 'En cours'
            END AS auction_status
        FROM enchere e
        JOIN historique_enchere h ON e.id_enchere = h.id_enchere
        JOIN users u ON h.id_user = u.id
        GROUP BY e.id_enchere
        HAVING winning_bid = h.proposed_price
        ORDER BY e.date_fin DESC
        """
    )

    winners = cursor.fetchall()
    conn.close()

    return render_template("winner_enchere.html", winners=winners)


@app.route("/mes_encheres")
@login_required
def mes_encheres():
    user_id = session.get("user_id")

    if not user_id:
        return redirect(
            url_for("login")
        )  # Redirige vers la page de connexion si l'utilisateur n'est pas connecté

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT e.name, e.image_url, he.proposed_price, e.etat 
        FROM historique_enchere he
        JOIN enchere e ON he.id_enchere = e.id_enchere
        WHERE he.id_user = ?
    """,
        (user_id,),
    )

    encheres = cursor.fetchall()
    conn.close()

    return render_template("mes_encheres.html", encheres=encheres)


# fonction pour supprimer un enchere cote user
@app.route("/supprimer_enchere", methods=["POST"])
@login_required
def supprimer_enchere():
    enchere_id = request.form.get("enchere_id")
    user_id = session.get("user_id")

    if not enchere_id or not user_id:
        return redirect(url_for("mes_encheres"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Supprimer uniquement si l'enchère appartient à l'utilisateur
    cursor.execute(
        "DELETE FROM historique_enchere WHERE id = ? AND id_user = ?",
        (enchere_id, user_id),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("mes_encheres"))


# @app.route("/encherir", methods=["POST"])
# def encherir():
#     try:
#         data = request.json
#         enchere_id = data.get("id_enchere")
#         prix = data.get("prix")
#         first_name = data.get("firstName")
#         last_name = data.get("lastName")
#         email = data.get("email")
#         phone = data.get("phone")

#         db = get_db()
#         cursor = db.cursor()

#         # Vérifier si l'utilisateur existe déjà
#         cursor.execute("SELECT id FROM users WHERE Email = ?", (email,))
#         user = cursor.fetchone()

#         if not user:
#             return jsonify({"message": "Utilisateur non trouvé"}), 400

#         user_id = user["id"]

#         # Enregistrer l'enchère dans historique_enchere
#         cursor.execute(
#             """
#             INSERT INTO historique_enchere (id_enchere, id_user, proposed_price)
#             VALUES (?, ?, ?)
#             """,
#             (enchere_id, user_id, prix),
#         )
#         db.commit()

#         return jsonify({"message": "Enchère enregistrée avec succès !"})

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/admin/historique_encheres", methods=["GET"])
# def historique_encheres():
#     conn = get_db()
#     cursor = conn.cursor()

#     # SQL Query to join historique_enchere, enchere, and users tables
#     cursor.execute("""
#         SELECT
#             e.image_url,
#             e.name AS enchere_name,
#             e.date_fin,
#             u.FirstName || ' ' || u.LastName AS user_full_name,
#             u.phoneNum,
#             h.proposed_price,
#             e.etat
#         FROM historique_enchere h
#         JOIN enchere e ON h.id_enchere = e.id_enchere
#         JOIN users u ON h.id_user = u.id
#         ORDER BY e.name, h.proposed_price DESC, e.date_fin DESC
#     """)

#     historique = cursor.fetchall()
#     conn.close()

#     return render_template("historique_encheres.html", historique=historique)


if __name__ == "__main__":
    app.run(debug=True)
