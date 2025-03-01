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
import sqlite3
import stripe
from reportlab.pdfgen import canvas
from io import BytesIO
import os
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

load_dotenv()  # Load environment variables

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # Necessary for sessions
bcrypt = Bcrypt(app)

# Flask-Login Setup
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")

# SQLite Database Path
DATABASE = "inventory.db"


# User Model
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def get_id(self):
        return str(self.id)


# Load User for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user["id"], user["username"], user["password"])
    return None  # Explicitly return None if the user is not found


# Function to get database connection
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


# Initialize Database
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create products table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
        """
    )

    # Create users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# Route: Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode(
            "utf-8"
        )

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password),
            )
            conn.commit()
            flash("Account created! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
        finally:
            conn.close()

    return render_template("register.html")


# Route: Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password"], password):
            login_user(User(user["id"], user["username"], user["password"]))
            flash("Login successful!", "success")
            return redirect(url_for("index"))

        flash("Invalid credentials", "danger")
    return render_template("login.html")


# Route: Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


# Home Page: Display Products
@app.route("/")
@login_required
def index():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    products = [dict(product) for product in products]
    return render_template("index.html", products=products)


# Add Product to Cart
@app.route("/add_to_cart/<int:product_id>")
@login_required
def add_to_cart(product_id):
    if "cart" not in session:
        session["cart"] = []
    if product_id not in session["cart"]:  # Prevent duplicate items
        session["cart"].append(product_id)
        session.modified = True
    return redirect(url_for("index"))


# View Cart
@app.route("/cart")
@login_required
def view_cart():
    cart = session.get("cart", [])
    conn = get_db()
    products = []
    total = 0
    for product_id in cart:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if product:
            products.append(dict(product))
            total += product["price"]
    conn.close()
    return render_template(
        "cart.html", products=products, total=total, stripe_public_key=stripe_public_key
    )


# Stripe Checkout
@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    try:
        total = request.form.get("total", "0")
        total = float(total) * 100  # Convert to cents

        if total < 1:
            return "Error: Amount must be greater than 0.", 400

        stripe.Charge.create(
            amount=int(total),
            currency="eur",
            description="Payment",
            source=request.form.get("stripeToken"),
        )

        session["invoice"] = generate_invoice(session["cart"], total).getvalue()
        session["cart"] = []  # Clear cart
        return redirect(url_for("facture"))

    except stripe.error.StripeError as e:
        return str(e), 400
    except ValueError:
        return "Error: Invalid amount.", 400


@app.route("/invoice")
@login_required
def facture():
    return render_template("invoice.html")


@app.route("/download_invoice")
@login_required
def download_facture():
    invoice_data = session.get("invoice")
    if not invoice_data:
        return "No invoice available.", 400

    return send_file(
        BytesIO(invoice_data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="invoice.pdf",
    )


def generate_invoice(cart, total):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Invoice")
    p.drawString(100, 730, f"Total: {total / 100:.2f} EUR")
    p.drawString(100, 710, "Purchased Items:")

    y = 690
    conn = get_db()
    for product_id in cart:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if product:
            p.drawString(100, y, f"{product['name']} - {product['price']} EUR")
            y -= 20
    conn.close()

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# Initialize Database
init_db()

if __name__ == "__main__":
    app.run(debug=True)
