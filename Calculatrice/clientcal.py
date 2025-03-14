import requests
# Base URL de l'API Flask
base_url = "http://127.0.0.1:5000"
# Fonction pour effectuer une addition
def add(a, b):
 response = requests.get(f"{base_url}/add", params={"a": a, "b": b})
 if response.status_code == 200:
  return response.json()["result"]
 else:
  return response.json()["error"]
# Fonction pour effectuer une soustraction
def subtract(a, b):
  response = requests.get(f"{base_url}/subtract", params={"a": a, "b": b})
  if response.status_code == 200:
    return response.json()["result"]
  else:
    return response.json()["error"]
# Fonction pour effectuer une multiplication
def multiply(a, b):
  response = requests.get(f"{base_url}/multiply", params={"a": a, "b": b})
  if response.status_code == 200:
    return response.json()["result"]
  else:
    return response.json()["error"]
# Fonction pour effectuer une division
def divide(a, b):
  response = requests.get(f"{base_url}/divide", params={"a": a, "b": b})
  if response.status_code == 200:
    return response.json()["result"]
  else:
    return response.json()["error"]
# Test des différentes opérations
if __name__ == '__main__':
 a = 10
 b = 5

 print(f"{a} + {b} = {add(a, b)}")
 print(f"{a} - {b} = {subtract(a, b)}")
 print(f"{a} * {b} = {multiply(a, b)}")
 print(f"{a} / {b} = {divide(a, b)}")
 # Tester la division par zéro
 print(f"Test de la division par zéro : {divide(a, 0)}")