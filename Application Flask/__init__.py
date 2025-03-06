import sqlite3
from flask_bcrypt import Bcrypt

bcrypt = (
    Bcrypt()
)  # Initialize Bcrypt (Make sure Flask app is passed if used in a Flask project)


def get_db():
    conn = sqlite3.connect("database.db")  # Ensure this is your actual DB file
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access
    return conn


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
            image_url TEXT
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

    conn.commit()
    conn.close()


""" CREATE ADMIN USER """


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


init_db()
create_admin()
