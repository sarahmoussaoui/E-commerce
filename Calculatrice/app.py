from flask import Flask, render_template, request, jsonify
import requests
app = Flask(__name__)
# URL du service Flask pour effectuer les calculs
base_url = "http://127.0.0.1:5000"
@app.route('/')
def index():
 return render_template('index.html')
@app.route('/calculate', methods=['POST'])
def calculate():
 # Récupérer les données envoyées par le formulaire
 a = float(request.form['a'])
 b = float(request.form['b'])
 operation = request.form['operation']
 # Effectuer l'opération demandée en appelant le service REST
 if operation == 'add':
  response = requests.get(f"{base_url}/add", params={"a": a, "b": b})
 elif operation == 'subtract':
  response = requests.get(f"{base_url}/subtract", params={"a": a, "b": b})
 elif operation == 'multiply':
  response = requests.get(f"{base_url}/multiply", params={"a": a, "b": b})
 elif operation == 'divide':
  response = requests.get(f"{base_url}/divide", params={"a": a, "b": b})

 # Récupérer la réponse et la renvoyer à l'utilisateur
 if response.status_code == 200:
  result = response.json()['result']
 else:
  result = response.json()['error']

 return jsonify({'result': result})
if __name__ == '__main__':
  app.run(debug=True,port=5001)