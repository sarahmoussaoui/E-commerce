Application Flask/
│
├── app.py                  # Fichier principal de l'application Flask
├── inventory.db            # Base de données SQLite pour l'inventaire
├── requirements.txt        # Fichier listant les dépendances du projet
├── templates/              # Dossier contenant les templates HTML
│   ├── base.html           # Template de base pour les autres pages
│   ├── index.html          # Page d'accueil avec la liste des produits
│   ├── cart.html           # Page du panier d'achat
│   └── invoice.html        # Page de confirmation de commande
├── static/                 # Dossier pour les fichiers statiques (CSS, images, etc.)
│   └── style.css           # Fichier CSS pour le style de l'application
└── invoices/               # Dossier pour stocker les factures PDF générées
└── .env

Fonctionnalités de l'application:
  Panier d'achat : Un panier d'achat où les utilisateurs peuvent ajouter des produits. ( done)
  Paiement avec Stripe : Intégrer Stripe pour gérer les paiements en ligne. (proceed to payment not done --> search to active smthg, panier doit se vider)
  Gestion d'inventaire avec SQLite : Utiliser une base de données SQLite pour gérer les stocks de produits. (done)
  Gestion des factures en PDF avec ReportLab : Générer des factures en PDF après un achat. (not done)
  Gestion du panier (done)
  régler le probleme d'image ( not done)


Creating a venv:
  python -m venv venv
  venv\Scripts\activate
  deactivate

  Libraries:
  pip install -r requirements.txt

2. Installer SQLite (si nécessaire)
  Sur Windows : 
  Télécharge SQLite depuis le site officiel : https://sqlite.org/download.html, precisely : sqlite-tools-win-x64-3490100.zip
    (6.12 MiB)	
  Télécharge le fichier sqlite-tools-win32-x86-*.zip (ou sqlite-tools-win32-x64-*.zip pour une version 64 bits).
  Extrais le fichier ZIP et place le dossier dans un répertoire facile d'accès (par exemple, C:\sqlite).
  Ajoute le chemin du dossier à ton PATH système :
  Clique droit sur Ce PC ou Ordinateur > Propriétés > Paramètres système avancés > Variables d'environnement.
  Dans la section Variables système, trouve la variable Path et clique sur Modifier.
  Ajoute le chemin du dossier SQLite (par exemple, C:\sqlite).
  Ouvre un nouveau terminal et exécute sqlite3 pour vérifier que l'installation a réussi.
  access sqllite terminal:
    check version installed correctly:
      python -c "import sqlite3; print(sqlite3.sqlite_version)"
      enter terminal with database: sqlite3 inventory.db
      quit terminal : .quit or .exit or force with cltr+C
      show tables: .tables
      describe table : .schema products
      for more commands : .help


Obtiens ta clé API Stripe :
  Connecte-toi à ton tableau de bord Stripe (https://dashboard.stripe.com).
  Va dans Developers > API keys.
  Tu verras deux clés : une clé publique (pk_test_...) et une clé secrète (sk_test_...).
  La clé publique est utilisée côté client (dans le formulaire de paiement), et la clé secrète est utilisée côté serveur (dans app.py).
  Configure la clé API secrete dans app.py  et publique dans cart.html

Accède à l'interface admin pour ajouter des produits
  Démarre ton application Flask.
  Accède à l'interface admin via l'URL : http://127.0.0.1:5000/admin/add_product
  Utilise le formulaire pour ajouter des produits.


On genere des produits aleatoires avec faker, les images aleatoires  du site Lorem Picsum:
  https://picsum.photos/200/300
  et on ajoute un code qui permet de generer pour chaque produit son image



Activer la tokenisation pour votre clé
Accédez à votre tableau de bord Stripe :
👉 Paramètres d'intégration Stripe
Activez la tokenisation côté client pour votre clé publiable.
Pour activer cette interface, veuillez accéder à votre tableau de bord https://dashboard.stripe.com/settings/integration .
Si l'option n'est pas disponible, votre compte pourrait ne pas être éligible à la tokenisation côté client. Dans ce cas, vous devez utiliser Stripe Elements pour des paiements sécurisés.