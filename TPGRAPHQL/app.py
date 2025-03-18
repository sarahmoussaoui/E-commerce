from flask import Flask, request, jsonify, render_template
import graphene

# Définition du type GraphQL
class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="Stranger"))
    goodbye = graphene.String(name=graphene.String(default_value="Stranger"))

    def resolve_hello(self, info, name):
        return f"Hello, {name}!"
    
    def resolve_goodbye(self, info, name):
        return f"Goodbye, {name}!"

# Création du schéma GraphQL
schema = graphene.Schema(query=Query)

# Initialisation de l'application Flask
app = Flask(__name__)

@app.route("/")
def index():
    # Afficher la page d'accueil avec un formulaire pour envoyer des requêtes GraphQL
    return render_template("index.html")

@app.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json()
    if data is None or 'query' not in data:
        return jsonify({'error': 'Missing GraphQL query'}), 400
    
    # Exécution de la requête GraphQL
    result = schema.execute(data.get('query'))
    return jsonify(result.data)

if __name__ == "__main__":
    app.run(debug=True)

