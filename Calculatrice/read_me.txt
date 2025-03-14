clientcal.py : executer dabord le serveur calculatrice.py puis clientcal.py
  Explication du code
  1. Importation de la bibliothèque requests : Nous utilisons cette bibliothèque pour envoyer
  des requêtes HTTP GET à notre API Flask.
  2. Définition des fonctions pour chaque opération :
  • add(a, b) : Effectue une addition.
  • subtract(a, b) : Effectue une soustraction.
  • multiply(a, b) : Effectue une multiplication.
  • divide(a, b) : Effectue une division et vérifie si b est égal à zéro pour éviter la
  division par zéro.
  3. Requête HTTP GET : Chaque fonction construit l'URL appropriée (par exemple, /add,
  /subtract, etc.) et y ajoute les paramètres a et b dans la requête avec requests.get().
  4. Traitement de la réponse : Si le code de statut de la réponse est 200 (succès), le programme
  extrait et renvoie le résultat de l'opération. Sinon, il renvoie le message d'erreur.
  5. Test des différentes opérations : Le programme client teste toutes les opérations (addition,
  soustraction, multiplication, division) et affiche les résultats.



app.py : execute calculatrice.py then app.py
  Explication du code
  1. Backend (app.py) :
  • Le serveur Flask a un endpoint principal / qui charge la page HTML.
  • L'endpoint /calculate gère la logique du calcul. Il reçoit les paramètres via une
  requête POST (en utilisant le formulaire HTML), envoie les paramètres au service Flask
  (via les API /add, /subtract, /multiply, /divide), puis renvoie le résultat
  sous forme JSON.
  2. Frontend (index.html) :
  • Un formulaire HTML permet à l'utilisateur d'entrer deux nombres et de choisir
  l'opération.
  • Il existe quatre boutons correspondant aux opérations d'addition, soustraction,
  multiplication et division.
  • Le JavaScript permet d'envoyer la requête AJAX (avec fetch) au serveur Flask pour
  effectuer le calcul sans recharger la page.
  • Le résultat est affiché sous le formulaire après la réponse du serveur.
  3. CSS (styles.css) :
  • Ce fichier contient des styles simples pour rendre l'interface utilisateur plus attrayante et
  bien disposée.
  Lancer le projet
  1. D'abord, assurez-vous que votre API Flask est en cours d'exécution (le service de calculatrice
  avec les endpoints /add, /subtract, /multiply, /divide).
  2. Ensuite, lancez l'application Flask pour l'interface web avec :
  2. python app.py
  3. Ouvrez un navigateur et allez à l'adresse http://127.0.0.1:8080/. Vous verrez
  l'interface de la calculatrice.
  Conclusion
  Ce projet vous offre une interface web simple qui consomme votre service de calculatrice en utilisant
  Flask et AJAX. 