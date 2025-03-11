import sqlite3
from flask_bcrypt import Bcrypt
import random
import posixpath
import shutil
import subprocess
import os


# Step 1: Drop tables if they exist
def drop_tables():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Drop tables if they exist
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS enchere")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS messages")

    conn.commit()
    conn.close()


# Step 2: Initialize Bcrypt
bcrypt = Bcrypt()


# Step 3: Get database connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# Step 4: Initialize database
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create products table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_url TEXT, 
            is_vintage INTEGER NOT NULL DEFAULT 0 CHECK(is_vintage IN (0,1))  
        )
        """
    )
    # Create products Enchere
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS enchere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_user INTEGER,
            id_product INTEGER,
            price REAL NOT NULL,
            FOREIGN KEY (id_user) REFERENCES users(id),
            FOREIGN KEY (id_product) REFERENCES products(id)
        )
        """
    )

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
            is_admin INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1))  
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
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'delivered', 'canceled')),
            FOREIGN KEY (user_id) REFERENCES users(id)
);
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS commande_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commande_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,  
            FOREIGN KEY (commande_id) REFERENCES commande(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id));
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            objet TEXT NOT NULL,
            message TEXT NOT NULL,
            date TEXT NOT NULL,
            is_treated INTEGER DEFAULT 0,
            admin_response TEXT
        )
        """
    )

    conn.commit()
    conn.close()


# Step 5: Insert products
def insert_products():
    conn = get_db()
    cursor = conn.cursor()

    # Directory containing product images
    image_dir = "./static/products_img/"

    # Get all image filenames
    image_files = [
        f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))
    ]

    for image in image_files:
        name = os.path.splitext(image)[
            0
        ]  # Use the filename (without extension) as the product name
        price = random.randint(10, 50)  # Random price between 10 and 50
        stock = random.randint(0, 15)  # Random stock between 0 and 15
        image_url = posixpath.join("products_img", image)  # Store relative path only

        cursor.execute(
            """
            INSERT INTO products (name, price, stock, image_url)
            VALUES (?, ?, ?, ?)
            """,
            (name, price, stock, image_url),
        )

    conn.commit()
    conn.close()


# Step 6: Create admin user
def create_admin():
    conn = get_db()
    cursor = conn.cursor()
    password = "123"
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Insert admin user (allow SQLite to auto-generate the ID)
    try:
        cursor.execute(
            "INSERT INTO users (FirstName, LastName, Email, phoneNum, password, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            ("Admin", "Admin", "admin@gmail.com", "1234567890", hashed_password, 1),
        )
        conn.commit()
        print("Admin user added successfully.")
    except sqlite3.IntegrityError:
        print("Admin user already exists.")

    conn.close()


# Step 7: Create virtual environment and install dependencies
def setup_venv():
    venv_dir = "venv"

    # Step 1: Delete the existing virtual environment if it exists
    if os.path.exists(venv_dir):
        print(f"Deleting existing virtual environment at {venv_dir}...")
        shutil.rmtree(venv_dir)
        print(f"Deleted {venv_dir}.")

    # Step 2: Create a new virtual environment
    print("Creating a new virtual environment...")
    subprocess.run(["python", "-m", "venv", venv_dir], check=True)
    print(f"Virtual environment created at {venv_dir}.")

    # Step 3: Install dependencies in the virtual environment
    if os.name == "nt":  # Windows
        pip_path = os.path.join(venv_dir, "Scripts", "pip")
    else:  # Unix or MacOS
        pip_path = os.path.join(venv_dir, "bin", "pip")

    print("Installing dependencies...")
    subprocess.run([pip_path, "install", "-r", "requirements.txt"], check=True)
    print("Dependencies installed in the virtual environment.")

    # Step 4: Print instructions to activate the virtual environment
    if os.name == "nt":  # Windows
        activate_script = os.path.join(venv_dir, "Scripts", "activate")
        print(
            f"\nTo activate the virtual environment, run the following command:\n{activate_script}"
        )
    else:  # Unix or MacOS
        activate_script = os.path.join(venv_dir, "bin", "activate")
        print(
            f"\nTo activate the virtual environment, run the following command:\nsource {activate_script}"
        )


# Main execution
if __name__ == "__main__":
    # Setup virtual environment and install dependencies
    setup_venv()

    # Drop tables if they exist
    drop_tables()

    # Initialize database
    init_db()

    # Insert products
    insert_products()

    # Create admin user
    create_admin()
