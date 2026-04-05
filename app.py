from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

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

def seed_studios_if_empty():
    con = db()
    count = con.execute("SELECT COUNT(*) FROM studios").fetchone()[0]
    if count == 0:
        con.executemany(
            "INSERT INTO studios (name) VALUES (?)",
            [
                ("East",),
                ("West",),
            ]
        )
        con.commit()

seed_studios_if_empty()

def seed_students_if_empty():
    con = db()
    count = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        con.executemany(
            "INSERT INTO students (name, classes_remaining, studio_id) VALUES (?, ?, ?)",
            [
("Allanah Sage", -1, 2) , # West
("Allie Carpenter", 0, 2) , # West
("Alyssa Battista", -1, 2) , # West
("Alyssa Gerard", 0, 1) , # East
("Ann Donner", 0, 2) , # West
("Anna Battista", -1, 2) , # West
("AnnaRose Vandebrake", 0, 2) , # West
("Anthony Makula", 1, 2) , # West
("Artemis Michaelides", 4, 2) , # West
("Aubrey Curtis", 0, 1) , # East
("Barbara Burke", 6, 2) , # West
("Bill Heckman", 7, 2) , # West
("Bobby Shaffer", -1, 2) , # West
("Camille (Cami) Snead", 4, 2) , # West
("Carol DiBenedetto", 1, 2) , # West
("Cathy Stohr", 1, 1) , # East
("Cheryl Hendrickson", -1, 1) , # East
("Christina Domondon", 10, 1) , # East
("Ciara Reifenstein", 2, 1) , # East
("Cindy Breeze", 0, 2) , # West
("Clare Swanson", 0, 2) , # West
("Colt Bakke", 0, 2) , # West
("Cynthia Lofaro", 2, 1) , # East
("Danielle Hernandez", -2, 2) , # West
("Darrell Mack", -4, 2) , # West
("Delaney Mersich", 3, 2) , # West
("Diane McConnell", 0, 2) , # West
("Donna Perry", 0, 2) , # West
("Donna Headry", 2, 2) , # West
("Dylan Curtis", 0, 1) , # East
("Dylan Smith", 1, 2) , # West
("Eileen Stair", 0, 2) , # West
("Elijah Atkinson ", 0, 2) , # West
("Ella Passamonte", 4, 2) , # West
("Ellie Schauber", 1, 2) , # West
("Emily Defilippo", 0, 2) , # West
("Emma Henderson", 3, 2) , # West
("Emma Miller", 0, 2) , # West
("Erin Cobb", 13, 1) , # East
("Faith Ronnenberg ", 0, 2) , # West
("Fiona Michaelides", 4, 2) , # West
("Gabrielle Rodriguez", 2, 2) , # West
("Gail Sielaff", 2, 2) , # West
("Gemma Skolen", 0, 2) , # West
("Gina Gaudioso", 2, 2) , # West
("Grace Knerr", 0, 2) , # West
("Gretchen Breon", 0, 2) , # West
("Haley Wentworth", 2, 2) , # West
("Harper Lipski", 0, 2) , # West
("Heather Collins", 0, 2) , # West
("Jack Hammell", -2, 2) , # West
("Jackie Lofaro", 2, 1) , # East
("Jen Dickinson", 0, 2) , # West
("JoAnn Chinappi", -1, 2) , # West
("Joel Bellis ", 0, 2) , # West
("Jordyn Emens", 1, 2) , # West
("Josh Christensen", -4, 2) , # West
("Joyce Iati", 4, 2) , # West
("Juliana  Ronnenberg", 0, 2) , # West
("Julie Watkins", 1, 2) , # West
("Julie Wiant", -1, 1) , # East
("Kai Shifley", 0, 2) , # West
("Kaja Sip", 0, 2) , # West
("Karen Fien", 5, 2) , # West
("Karen Schwartzman", 0, 1) , # East
("Kathleen Miller", 0, 2) , # West
("Katie Keuer", 2, 2) , # West
("Kendrya Cook", -1, 2) , # West
("Laura Landis", 0, 2) , # West
("Leah Landis", 0, 2) , # West
("Len Ippolito", 8, 2) , # West
("Liana Hughson", 4, 2) , # West
("Lily Landis", 0, 2) , # West
("Linda Davis", -1, 2) , # West
("Liz Redden", -4, 2) , # West
("Lola Smith", 1, 2) , # West
("Luana Shifley ", 0, 2) , # West
("Lucy Landis", 0, 2) , # West
("Lucy Shaffer", 6, 2) , # West
("Luna Luan", 8, 2) , # West
("Madalyn Gerard", 0, 1) , # East
("Maddy Rapp", 0, 2) , # West
("Maria McCarthy", 0, 2) , # West
("Mary Hammele", 7, 1) , # East
("Mateo Arrendell", 0, 2) , # West
("Max Brown", 0, 2) , # West
("McKinley Shipe", 4, 2) , # West
("Melanie Ippolito", 4, 2) , # West
("Michael Makula", 1, 2) , # West
("Monica Makula", 1, 2) , # West
("Mya Arrendell", 0, 2) , # West
("Niam Brown", 0, 2) , # West
("Nora Mersich", 4, 2) , # West
("Norah Glor", 0, 2) , # West
("Orry Johnson", 0, 2) , # West
("Rhonda Shaffer", 0, 1) , # East
("Rita Dean", 0, 2) , # West
("Rowan Shipe", 4, 2) , # West
("Sadie Atwood", -5, 2) , # West
("Selena Luan", 0, 2) , # West
("Shalimar Arrayo", 0, 2) , # West
("Sharon Kincaid", 4, 2) , # West
("Suzette Coleman", 3, 2) , # West
("Sylvia Michaelides", 4, 2) , # West
("Taylor Hale", 0, 2) , # West
("Teagan Clarkin", -1, 2) , # West
("Teddy Shaffer", 5, 2) , # West
("Tiernan Shipe", 4, 2) , # West
("Vicki Casperson", 6, 2) , # West
("Ava Radens", 0, 2) , # West
("Sawyer Schutz", 2, 2) , # West
("Fabian ", 0, 2) , # West
("Sue Ranelli ", 0, 1) , # East
("Mollie Warnock", 3, 1) , # East
("Joann Alibrandi", 0, 1) , # East
("Riley ", -1, 2) , # West
("Logan Burger", 1, 2) , # West
("Eliza", 0, 2) , # West
("Kendra Rosetti", 1, 1) , # East
("Sam Lane ", 1, 1) , # East
("Alex Lane", 1, 1) , # East
("Nathaniel Lane ", 1, 1) , # East
("Lori Kwasneski", -4, 2) , # West
("Kristen", -4, 1) , # East
("Lynn McGraw", 0, 1) , # East
("Daniel Sova", -3, 2) , # West
("Finley Atkinson", 0, 2) , # West
("Ollie Shaffer", 3, 2) , # West
("Betty Northrup", 0, 2) , # West
("Fred Dean", -1, 2) , # West
("Annie Barth", 3, 1) , # East
("Christina Saunders", 2, 1) , # East
("Roxanne Cannarozzo", 4, 2) , # West
("Andrea Cannarozzo", 4, 2) , # West
("Skye Jeanat", 4, 2) , # West
("Shanie Jeanat", 4, 2) , # West
("Ricky Jeanat", 4, 2) , # West
("Kathy Peterson", 2, 2) , # West
("Rita Marie Geary", -3, 1) , # East
("Heather Satterwhite", 3, 1) , # East
("Chloe Grab", 5, 2) , # West
("Lyric", 0, 2) , # West
("Tiifany Malo", 5, 1) , # East
("Hazel Benedict ", 3, 2) , # West
("Maggie Clemens", -2, 1) , # East
("Kiley Kapica", 1, 2) , # West
("Vivienne Servo", 2, 2) , # West
("Johnny Servo", 2, 2) , # West
("Mikala Muto", 0, 2) , # West
("Nina Domondon", 0, 1) , # East
("Kathy Verzillo", 0, 1) , # East
("Elijah Martinnez", 0, 2) , # West

            ]
        )
        con.commit()

seed_students_if_empty()

@app.route("/")
def home():
    return "Backend is running"

@app.route("/studios")
def studios():
    rows = db().execute("SELECT id, name FROM studios").fetchall()
    return jsonify([{"id": r[0], "name": r[1]} for r in rows])

@app.route("/studios.js")
def studios_js():
    rows = db().execute("SELECT id, name FROM studios").fetchall()
    payload = [{"id": r[0], "name": r[1]} for r in rows]
    js = "window.STUDIOS = " + str(payload).replace("'", '"') + ";"
    return app.response_class(js, mimetype="application/javascript")

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

# TEMP SEED ENDPOINTS (OK during setup; remove later)
@app.route("/admin/seed_studios", methods=["POST"])
def seed_studios():
    studios_list = (request.json or {}).get("studios", [])
    con = db()
    for name in studios_list:
        con.execute("INSERT INTO studios (name) VALUES (?)", (name,))
    con.commit()
    return "Studios added"

@app.route("/admin/seed_studios_get")
def seed_studios_get():
    studios_list = ["Main Studio", "Community Center", "Private Lessons"]
    con = db()
    for name in studios_list:
        con.execute("INSERT INTO studios (name) VALUES (?)", (name,))
    con.commit()
    return "Studios added via GET"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
