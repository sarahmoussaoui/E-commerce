from flask import Flask, jsonify

app = Flask(__name__)

students = [
    {"id": 1, "name": "Ali", "mention": "Excellent"},
    {"id": 2, "name": "Sara", "mention": "Bien"},
    {"id": 3, "name": "Mehdi", "mention": "Passable"},
    {"id": 4, "name": "Nadia", "mention": "Bien"}
]

@app.route('/students/major', methods=['GET'])
def get_major():
    return jsonify(students[0]) if students else jsonify({}), 200

@app.route('/students/remove-passable', methods=['DELETE'])
def remove_passable_students():
    global students
    students = [s for s in students if s['mention'] != "Passable"]
    return jsonify({"message": "Passable students removed"}), 200

@app.route('/students/count-bien', methods=['GET'])
def count_bien_students():
    count = sum(1 for s in students if s['mention'] == "Bien")
    return jsonify({"count": count}), 200

if __name__ == '__main__':
    app.run(debug=True)
