from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)
DB = "classes.db"


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            studio TEXT NOT NULL CHECK (studio IN ('East','West'))
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            classes_purchased INTEGER NOT NULL CHECK (classes_purchased > 0),
            cost REAL NOT NULL CHECK (cost >= 0),
            FOREIGN KEY(student_id) REFERENCES students(id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('attended','charged')),
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
        """)


@app.route("/", methods=["GET", "POST"])
def index():
    init_db()
    con = db()

    if request.method == "POST":
        form_type = request.form.get("type")

        if form_type == "add_student":
            name = request.form["name"].strip()
            studio = request.form["studio"]
            con.execute(
                "INSERT OR IGNORE INTO students (name, studio) VALUES (?, ?)",
                (name, studio)
            )
            con.commit()
            return redirect(url_for("index"))

        if form_type == "purchase":
            con.execute(
                "INSERT INTO purchases (student_id, date, classes_purchased, cost) VALUES (?, ?, ?, ?)",
                (
                    int(request.form["student_id"]),
                    request.form["date"],
                    int(request.form["classes"]),
                    float(request.form["cost"]),
                )
            )
            con.commit()
            return redirect(url_for("index"))

        if form_type == "attendance":
            con.execute(
                "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                (
                    int(request.form["student_id"]),
                    request.form["date"],
                    request.form["status"],  # attended OR charged; both count as 1 used
                )
            )
            con.commit()
            return redirect(url_for("index"))

    students = con.execute("SELECT * FROM students ORDER BY studio, name").fetchall()

    report = con.execute("""
        SELECT
            s.id,
            s.name,
            s.studio,
            COALESCE(SUM(p.classes_purchased), 0) AS purchased,
            (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id) AS used,
            COALESCE(SUM(p.classes_purchased), 0) -
            (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id) AS remaining,
            COALESCE(SUM(p.cost), 0) AS total_spent
        FROM students s
        LEFT JOIN purchases p ON p.student_id = s.id
        GROUP BY s.id
        ORDER BY s.studio, s.name
    """).fetchall()

    purchase_totals = con.execute("""
        SELECT
            s.name,
            s.studio,
            COALESCE(SUM(p.classes_purchased), 0) AS classes_purchased,
            COALESCE(SUM(p.cost), 0) AS total_spent
        FROM students s
        LEFT JOIN purchases p ON p.student_id = s.id
        GROUP BY s.id
        ORDER BY total_spent DESC, s.name
    """).fetchall()

    # Optional helper lists (nice for undo)
    recent_attendance = con.execute("""
        SELECT a.id, a.date, a.status, s.name AS student_name
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        ORDER BY a.id DESC
        LIMIT 15
    """).fetchall()

    recent_purchases = con.execute("""
        SELECT p.id, p.date, p.classes_purchased, p.cost, s.name AS student_name
        FROM purchases p
        JOIN students s ON s.id = p.student_id
        ORDER BY p.id DESC
        LIMIT 15
    """).fetchall()

    return render_template(
        "index.html",
        students=students,
        report=report,
        purchase_totals=purchase_totals,
        recent_attendance=recent_attendance,
        recent_purchases=recent_purchases,
        today=date.today().isoformat()
    )


@app.route("/attendance/<int:student_id>")
def attendance_history(student_id):
    init_db()
    con = db()
    student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    records = con.execute(
        "SELECT id, date, status FROM attendance WHERE student_id=? ORDER BY date",
        (student_id,)
    ).fetchall()
    return render_template("attendance.html", student=student, records=records)


# ✅ NEW: Delete a specific attendance record (undo mistake)
@app.route("/attendance/delete/<int:attendance_id>", methods=["POST"])
def delete_attendance(attendance_id):
    init_db()
    con = db()
    con.execute("DELETE FROM attendance WHERE id = ?", (attendance_id,))
    con.commit()

    # return user where they came from, if present
    next_url = request.form.get("next") or url_for("index")
    return redirect(next_url)


# ✅ NEW: Delete a specific purchase record (optional undo)
@app.route("/purchase/delete/<int:purchase_id>", methods=["POST"])
def delete_purchase(purchase_id):
    init_db()
    con = db()
    con.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    con.commit()

    next_url = request.form.get("next") or url_for("index")
    return redirect(next_url)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
