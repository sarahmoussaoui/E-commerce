<!-- @format -->

````md
# TP GraphQL et Flask - Résumé

<!-- @format -->

## Concepts et principes de GraphQL

GraphQL est un langage de requête pour les API développé par **Facebook**. Il vise à **optimiser l’interaction avec les données** en permettant aux clients de récupérer exactement les informations nécessaires.

### 1. Langage de Requête (Query Language)

Permet d’exécuter des requêtes spécifiques au lieu d’obtenir un ensemble fixe de données comme en REST.
Exemple de requête GraphQL pour récupérer un utilisateur :

```graphql
{
  user(id: 1) {
    name
    email
  }
}
```
````

Cette requête retourne uniquement les champs **name** et **email** de l’utilisateur avec `id = 1`.

### 2. Unification de l’API

Contrairement à **REST**, qui utilise plusieurs points de terminaison (`/users`, `/posts`), GraphQL utilise un **seul point de terminaison** (`/graphql`), permettant **toutes les opérations (query, mutation, subscription)**.

### 3. Types de requêtes GraphQL

- **Queries** : Lecture des données.  
  _Exemple_ : `{ user(id: 1) { name email } }`
- **Mutations** : Modification des données (ajout, mise à jour, suppression).  
  _Exemple_ :
  ```graphql
  mutation {
    createUser(name: "John", email: "john@example.com") {
      id
      name
    }
  }
  ```
- **Subscriptions** : Écoute des changements en temps réel.  
  _Exemple_ :
  ```graphql
  subscription {
    userAdded {
      id
      name
    }
  }
  ```

### 4. Résolution et Schéma

- **Schéma GraphQL** : Définit les **types de données** et leurs relations.
- **Résolveurs (Resolvers)** : Fonctions permettant de **récupérer ou modifier les données**.
  _Exemple_ : Une requête `{ user(id: 1) { name } }` peut être résolue par une fonction qui va chercher l’information en base de données.

### 5. Avantages de GraphQL

- **Récupération flexible des données** : Pas d’over-fetching (trop de données) ni d’under-fetching (pas assez de données).
- **Optimisation des performances** : Réduction des requêtes réseau.
- **Évolutivité** : Ajout de nouveaux champs sans affecter les requêtes existantes.
- **Documentation automatique** : Documentation générée à partir du schéma GraphQL.

### 6. Exécution des requêtes

Une requête GraphQL est **analysée**, puis chaque champ est traité par son résolveur.
Résultat d’une requête :

```json
{
  "data": {
    "user": {
      "name": "John Doe",
      "email": "john@example.com"
    }
  }
}
```

### 7. Comparaison GraphQL vs REST

| Critère                            | GraphQL                              | REST                                 |
| ---------------------------------- | ------------------------------------ | ------------------------------------ |
| **Points d’accès**                 | Un seul (`/graphql`)                 | Plusieurs (`/users`, `/posts`, etc.) |
| **Récupération des données**       | Ciblée, seulement ce qui est demandé | Peut inclure des données inutiles    |
| **Over-fetching / Under-fetching** | Évite ces problèmes                  | Possible                             |
| **Flexibilité**                    | Très flexible                        | Plus rigide                          |

### 8. Architecture typique d’une API GraphQL

1. **Client** : Effectue une requête GraphQL.
2. **Serveur GraphQL** : Exécute les résolveurs et retourne une réponse JSON.
3. **Base de données** : Contient les données à récupérer.

### 9. Sécurité en GraphQL

- **Limiter la profondeur des requêtes** pour éviter les abus.
- **Contrôle d’accès** pour restreindre les informations sensibles.

## Ajout d'une Mutation dans GraphQL

### 1. Définition de la mutation

```python
class CreateUser(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name):
        users_list.append(name)
        return CreateUser(success=True, message=f"User {name} created successfully!")
```

### 2. Intégration au schéma GraphQL

```python
class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
```

### 3. Gestion des requêtes et mutations

- **Formulaire pour Query** : Permet d’écrire une requête GraphQL et appeler des fonctions comme `hello`.
- **Formulaire pour Mutation** : Permet de soumettre une mutation pour créer un utilisateur (`createUser`).
- **Gestion des requêtes et mutations** : Les deux formulaires envoient respectivement une requête ou une mutation au serveur.
