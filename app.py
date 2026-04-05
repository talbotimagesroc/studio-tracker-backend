from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def home():
    return "Backend is running"

@app.route("/studios")
def studios():
    return jsonify([])

@app.route("/students")
def students():
    return jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
