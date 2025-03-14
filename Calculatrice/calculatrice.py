from flask import Flask, request, jsonify
app = Flask(__name__)
@app.route('/')
def home():
 return "Bienvenue dans le service Web Calculatrice"
# Endpoint pour additionner deux nombres
@app.route('/add', methods=['GET'])
def add():
 # Récupérer les paramètres 'a' et 'b' de l'URL
 a = request.args.get('a', type=float)
 b = request.args.get('b', type=float)

 if a is None or b is None:
  return jsonify({"error": "Les paramètres 'a' et 'b' sont requis"}), 400

 # Calculer la somme
 result = a + b
 return jsonify({"result": result})
# Endpoint pour soustraire deux nombres
@app.route('/subtract', methods=['GET'])
def subtract():
 # Récupérer les paramètres 'a' et 'b' de l'URL
 a = request.args.get('a', type=float)
 b = request.args.get('b', type=float)

 if a is None or b is None:
  return jsonify({"error": "Les paramètres 'a' et 'b' sont requis"}), 400

 # Calculer la soustraction
 result = a - b
 return jsonify({"result": result})
# Endpoint pour multiplier deux nombres
@app.route('/multiply', methods=['GET'])
def multiply():
 # Récupérer les paramètres 'a' et 'b' de l'URL
 a = request.args.get('a', type=float)
 b = request.args.get('b', type=float)

 if a is None or b is None:
  return jsonify({"error": "Les paramètres 'a' et 'b' sont requis"}), 400

 # Calculer la multiplication
 result = a * b
 return jsonify({"result": result})
# Endpoint pour diviser deux nombres
@app.route('/divide', methods=['GET'])
def divide():
 # Récupérer les paramètres 'a' et 'b' de l'URL
 a = request.args.get('a', type=float)
 b = request.args.get('b', type=float)

 if a is None or b is None:
  return jsonify({"error": "Les paramètres 'a' et 'b' sont requis"}), 400

 # Vérifier si on essaie de diviser par zéro
 if b == 0:
  return jsonify({"error": "Division par zéro interdite"}), 400

 # Calculer la division
 result = a / b
 return jsonify({"result": result})
if __name__ == '__main__':
  app.run(debug=True)