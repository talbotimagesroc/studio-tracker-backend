from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)
DB_FILE = "data.db"

def db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS studios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            classes_remaining INTEGER,
            studio_id INTEGER
        )
    """)
    con.commit()

init_db()

@app.route("/")
def home():
    return "Backend is running"

@app.route("/studios")
def studios():
    rows = db().execute("SELECT id, name FROM studios").fetchall()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])

@app.route("/students")
def students():
    studio_id = request.args.get("studio_id")
    if not studio_id:
        return jsonify([])
    rows = db().execute(
        "SELECT id, name, classes_remaining FROM students WHERE studio_id = ?",
        (studio_id,)
    ).fetchall()
    return jsonify([
        {"id": r[0], "name": r[1], "classes_remaining": r[2]}
        for r in rows
    ])

# ✅ TEMP SEED ENDPOINT — MUST BE ABOVE app.run()
@app.route("/admin/seed_studios", methods=["POST"])
def seed_studios():
    studios = request.json.get("studios", [])
    con = db()
    for name in studios:
        con.execute("INSERT INTO studios (name) VALUES (?)", (name,))
    con.commit()
    return "Studios added"

# 🚫 NOTHING BELOW THIS LINE EXCEPT app.run()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
