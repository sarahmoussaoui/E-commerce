from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import stripe
from reportlab.pdfgen import canvas
from io import BytesIO
import os
from faker import Faker
from random import randint
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
app.secret_key = os.getenv("STRIPE_SECRET_KEY")  # Nécessaire pour les sessions
stripe_public_key = os.getenv("STRIPE_PUBLIC_KEY")  # Remplace par ta clé publique Stripe

# Configuration Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # Remplace par ta clé secrète Stripe

# Chemin vers la base de données SQLite
DATABASE = 'inventory.db'

#  classe product 
class Product:
    def __init__(self, id, name, price, stock):
        self.id = id
        self.name = name
        self.price = price
        self.stock = stock
        self.image_url =  self.generate_image_url()  # Générer une URL d'image fixe
    
    def generate_image_url(self):
        """Génère une URL d'image fixe basée sur l'ID du produit."""
        return f'https://picsum.photos/200/300?random={self.id}'

# Fonction pour se connecter à la base de données
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    return conn

# Créer la table des produits si elle n'existe pas
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Page d'accueil : afficher les produits
@app.route('/')
def index():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    
    # Convertir chaque sqlite3.Row en dictionnaire
    products = [dict(product) for product in products]

    return render_template('index.html', products=products)

# Ajouter un produit au panier
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(product_id)
    session.modified = True  # Assure-toi que la session est marquée comme modifiée
    return redirect(url_for('index'))

# Afficher le panier
@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    conn = get_db()
    products = []
    total = 0
    for product_id in cart:
        product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        if product:
            products.append(product)
            total += product['price']
    conn.close()
    return render_template('cart.html', products=products, total=total, stripe_public_key=stripe_public_key)

# Paiement avec Stripe
@app.route('/checkout', methods=['POST'])
def checkout():
    total = float(request.form['total']) * 100  # Stripe utilise des centimes
    try:
        charge = stripe.Charge.create(
            amount=int(total),
            currency='eur',
            description='Paiement',
            source=request.form['stripeToken']
        )
        # Générer la facture
        invoice_pdf = generate_invoice(session.get('cart', []), total / 100)
        session['cart'] = []  # Vider le panier après paiement
        return send_file(invoice_pdf, as_attachment=True, download_name='facture.pdf')
    except stripe.error.StripeError as e:
        return str(e)

# Générer une facture en PDF avec ReportLab
def generate_invoice(cart, total):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Facture")
    p.drawString(100, 730, f"Total: {total} EUR")
    p.drawString(100, 710, "Articles achetés :")
    y = 690
    for product_id in cart:
        conn = get_db()
        product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        conn.close()
        if product:
            p.drawString(100, y, f"{product['name']} - {product['price']} EUR")
            y -= 20
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer


# Ajouter une route pour ajouter des produits via une interface admin flask --> template add_product.html
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        conn = get_db()
        cursor = conn.cursor()
        
        # Insérer le produit dans la base de données
        cursor.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
        
        # Récupérer l'ID du produit nouvellement inséré
        product_id = cursor.lastrowid
        
        # Créer un objet Product
        product = Product(product_id, name, price, stock)
        
        # Mettre à jour le produit avec l'URL d'image
        cursor.execute("UPDATE products SET image_url = ? WHERE id = ?", (product.image_url, product_id))

        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add_product.html')

# ajouter des produits manuellement generated randomly by Faker
def add_sample_products():
    conn = get_db()
    fake = Faker()  # Initialise Faker
    cursor = conn.cursor()

    # Générer 50 produits aléatoires
    for _ in range(20):
        name = fake.word().capitalize() + ' ' + fake.word().capitalize()  # Exemple : "Super T-shirt"
        price = round(fake.random_number(digits=2)) + 0.99  # Exemple : 19.99
        stock = fake.random_int(min=10, max=200)  # Exemple : 100
        # Insérer le produit dans la base de données
        cursor.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
        
        # Récupérer l'ID du produit nouvellement inséré
        product_id = cursor.lastrowid
        
        # Générer une URL d'image fixe basée sur l'ID
        image_url = f'https://picsum.photos/200/300?random={product_id}'
        
        # Mettre à jour le produit avec l'URL d'image
        cursor.execute("UPDATE products SET image_url = ? WHERE id = ?", (image_url, product_id))
      
    conn.commit()
    conn.close()


# Initialiser la base de données au démarrage
init_db()

# Ajouter des produits de test (appeler cette fonction une seule fois)
add_sample_products()

if __name__ == '__main__':
    app.run(debug=True)