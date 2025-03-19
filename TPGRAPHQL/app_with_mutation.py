from flask import Flask, request, jsonify, render_template
import graphene

# Définition du type GraphQL
class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="Stranger"))
    goodbye = graphene.String(name=graphene.String(default_value="Stranger"))
    users = graphene.List(graphene.String)

    def resolve_hello(self, info, name):
        return f"Hello, {name}!"
    
    def resolve_goodbye(self, info, name):
        return f"Goodbye, {name}!"
    
    def resolve_users(self, info):
        # Retourne une liste d'utilisateurs fictifs
        return ["Alice", "Bob", "Charlie"]

# Définition de la Mutation
class CreateUser(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
    
    success = graphene.Boolean()
    message = graphene.String()
    
    def mutate(self, info, name):
        # Exemple simple de création d'un utilisateur (pas de base de données ici)
        # Vous pouvez stocker l'utilisateur dans une base de données ou dans une liste pour plus de complexité.
        # Exemple de stockage dans une liste
        users_list.append(name)  # Ajouter l'utilisateur à la liste globale fictive
        return CreateUser(success=True, message=f"User {name} created successfully!")

# Définition du schéma de mutation
class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()

# Création du schéma GraphQL avec Query et Mutation
schema = graphene.Schema(query=Query, mutation=Mutation)

# Liste fictive d'utilisateurs pour démonstration
users_list = []

# Initialisation de l'application Flask
app = Flask(__name__)

@app.route("/")
def index():
    # Afficher la page d'accueil avec un formulaire pour envoyer des requêtes GraphQL
    return render_template("index_mutation.html")

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

