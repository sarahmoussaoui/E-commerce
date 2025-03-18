import requests
import json
# L'URL de l'API GraphQL
url = "http://127.0.0.1:5000/graphql"
# Requête GraphQL pour demander un "hello"
query = """
{
 hello(name: "Alice")
}
"""
# Envoi de la requête au serveur Flask GraphQL
response = requests.post(url, json={'query': query})
# Affichage de la réponse
if response.status_code == 200:
 data = response.json()
 print("Réponse du serveur GraphQL : ", json.dumps(data, indent=2))
else:
 print(f"Erreur lors de la requête: {response.status_code}")
