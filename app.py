import os
from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
from datetime import date, datetime
import csv
import io
import re

app = Flask(__name__)

# ✅ Persist DB on Render disk when available
DB = os.environ.get("DB_PATH", "/var/data/classes.db")

# (Optional safety) Ensure directory exists if using absolute path
try:
    db_dir = os.path.dirname(DB)
    if db_dir and DB.startswith("/") and not os.path.isdir(db_dir):
        os.makedirs(db_dir, exist_ok=True)
except Exception:
    pass


# --- Helpers ---------------------------------------------------------

def _norm_header(h: str) -> str:
    """Normalize CSV header names like 'Student Name' -> 'student_name'."""
    return re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_")

def _get(row: dict, *keys, default=""):
    """Return the first non-empty value found for any of the provided keys."""
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default

def _to_int(val, default=None):
    try:
        return int(str(val).strip())
    except Exception:
        return default

def _to_float(val, default=None):
    try:
        s = str(val).strip().replace("$", "").replace(",", "")
        return float(s)
    except Exception:
        return default

def db():
    # SQLite on a persistent disk
    conn = sqlite3.connect(DB, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Reduce locking issues under gunicorn threads:
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn

def normalize_date_str(s: str) -> str:
    """
    Normalize a date string to YYYY-MM-DD.
    Accepts:
      - YYYY-MM-DD (returns as-is)
      - M/D/YYYY or MM/DD/YYYY (returns YYYY-MM-DD)
    If it can't parse, returns original.
    """
    if not s:
        return s
    s = s.strip()
    # Already ISO
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    # Common US format from Excel imports
    # Allow 1-2 digit month/day
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", s):
        try:
            dt = datetime.strptime(s, "%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return s
    return s

def ensure_meta_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

def get_meta(con, key):
    row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None

def set_meta(con, key, value):
    con.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))

def migrate_dates_once(con):
    """
    One-time migration: convert any M/D/YYYY stored in purchases.date or attendance.date to ISO YYYY-MM-DD.
    This fixes sorting + consistent display in templates.
    """
    ensure_meta_table(con)
    if get_meta(con, "date_migrated_v1") == "1":
        return

    # purchases
    rows = con.execute("SELECT id, date FROM purchases").fetchall()
    for r in rows:
        old = r["date"]
        new = normalize_date_str(old)
        if new != old:
            con.execute("UPDATE purchases SET date=? WHERE id=?", (new, r["id"]))

    # attendance
    rows = con.execute("SELECT id, date FROM attendance").fetchall()
    for r in rows:
        old = r["date"]
        new = normalize_date_str(old)
        if new != old:
            con.execute("UPDATE attendance SET date=? WHERE id=?", (new, r["id"]))

    set_meta(con, "date_migrated_v1", "1")


# --- Schema ----------------------------------------------------------

def init_db():
    with db() as con:
        # Core tables
        con.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            studio TEXT NOT NULL CHECK (studio IN ('East','West')),
            phone TEXT,
            email TEXT,
            parents TEXT,
            accommodations TEXT
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            classes_purchased INTEGER NOT NULL,
            cost REAL NOT NULL CHECK (cost >= 0),
            payment_method TEXT,
            note TEXT,
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

        # Safe migrations for older DBs
        for col in ("phone", "email", "parents", "accommodations"):
            try:
                con.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass

        for col in ("payment_method", "note"):
            try:
                con.execute(f"ALTER TABLE purchases ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass

        # One-time date normalization migration
        migrate_dates_once(con)

        con.commit()


# --- Routes ----------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    init_db()
    con = db()

    if request.method == "POST":
        t = request.form.get("type")

        if t == "add_student":
            con.execute("""
                INSERT OR IGNORE INTO students
                (name, studio, phone, email, parents, accommodations)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request.form["name"].strip(),
                request.form["studio"],
                request.form.get("phone", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("parents", "").strip(),
                request.form.get("accommodations", "").strip(),
            ))

        elif t == "purchase":
            con.execute("""
                INSERT INTO purchases
                (student_id, date, classes_purchased, cost, payment_method, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                int(request.form["student_id"]),
                normalize_date_str(request.form["date"]),
                int(request.form["classes"]),
                float(request.form["cost"]),
                request.form.get("payment_method", "").strip(),
                request.form.get("note", "").strip(),
            ))

        elif t == "attendance":
            status = (request.form["status"] or "").strip().lower()
            if status.startswith("attended"):
                status = "attended"
            elif status.startswith("charged"):
                status = "charged"
            con.execute(
                "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                (int(request.form["student_id"]), normalize_date_str(request.form["date"]), status)
            )

        con.commit()
        return redirect(url_for("index"))

    # ✅ This list controls your dropdowns; SQL order is authoritative.
    students = con.execute("""
        SELECT *
        FROM students
        ORDER BY name COLLATE NOCASE
    """).fetchall()

    # Student summary
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

    overdrawn_students = [r["name"] for r in report if r["remaining"] < 0]

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

    # ✅ Recent lists sorted by DATE first
    recent_attendance = con.execute("""
        SELECT a.id, a.date, a.status, s.name AS student_name
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        ORDER BY a.date DESC, a.id DESC
        LIMIT 20
    """).fetchall()

    recent_purchases = con.execute("""
        SELECT
            p.id, p.date, p.classes_purchased, p.cost,
            COALESCE(p.payment_method,'') AS payment_method,
            COALESCE(p.note,'') AS note,
            s.name AS student_name
        FROM purchases p
        JOIN students s ON s.id = p.student_id
        ORDER BY p.date DESC, p.id DESC
        LIMIT 10
    """).fetchall()

    return render_template(
        "index.html",
        students=students,
        report=report,
        overdrawn_students=overdrawn_students,
        purchase_totals=purchase_totals,
        recent_attendance=recent_attendance,
        recent_purchases=recent_purchases,
        today=date.today().isoformat()
    )


@app.route("/timeline/<int:student_id>")
def timeline(student_id):
    init_db()
    con = db()

    student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()

    purchases = con.execute("""
        SELECT id, date, classes_purchased, cost,
               COALESCE(payment_method,'') AS payment_method,
               COALESCE(note,'') AS note
        FROM purchases
        WHERE student_id=?
        ORDER BY date ASC, id ASC
    """, (student_id,)).fetchall()

    attendance = con.execute("""
        SELECT id, date, status
        FROM attendance
        WHERE student_id=?
        ORDER BY date ASC, id ASC
    """, (student_id,)).fetchall()

    events = []

    for p in purchases:
        label = f"Purchased {p['classes_purchased']} classes (${p['cost']:.2f})"
        if p["payment_method"].strip():
            label += f" via {p['payment_method'].strip()}"
        if p["note"].strip():
            label += f" — Note: {p['note'].strip()}"

        events.append({
            "kind": "purchase",
            "id": p["id"],
            "date": p["date"],
            "label": label,
            "classes_delta": int(p["classes_purchased"]),
        })

    for a in attendance:
        label = "Attended" if a["status"] == "attended" else "Charged / Not Attended"
        events.append({
            "kind": "attendance",
            "id": a["id"],
            "date": a["date"],
            "label": label,
            "classes_delta": -1,
        })

    kind_order = {"purchase": 0, "attendance": 1}
    events.sort(key=lambda e: (e["date"], kind_order.get(e["kind"], 9), e["id"]))

    return render_template("timeline.html", student=student, events=events)


@app.route("/student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    init_db()
    con = db()
    student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update":
            con.execute("""
                UPDATE students
                SET name=?, studio=?, phone=?, email=?, parents=?, accommodations=?
                WHERE id=?
            """, (
                request.form["name"].strip(),
                request.form["studio"],
                request.form.get("phone", "").strip(),
                request.form.get("email", "").strip(),
                request.form.get("parents", "").strip(),
                request.form.get("accommodations", "").strip(),
                student_id
            ))
            con.commit()
            return redirect(url_for("index"))

        if action == "delete":
            con.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
            con.execute("DELETE FROM purchases WHERE student_id=?", (student_id,))
            con.execute("DELETE FROM students WHERE id=?", (student_id,))
            con.commit()
            return redirect(url_for("index"))

    return render_template("edit_student.html", student=student)


@app.route("/attendance/delete/<int:attendance_id>", methods=["POST"])
def delete_attendance(attendance_id):
    init_db()
    con = db()
    con.execute("DELETE FROM attendance WHERE id=?", (attendance_id,))
    con.commit()
    return redirect(request.form.get("next", url_for("index")))


@app.route("/purchase/delete/<int:purchase_id>", methods=["POST"])
def delete_purchase(purchase_id):
    init_db()
    con = db()
    con.execute("DELETE FROM purchases WHERE id=?", (purchase_id,))
    con.commit()
    return redirect(request.form.get("next", url_for("index")))


# =========================
# ✅ CSV IMPORTS (LOADERS)
# =========================

@app.route("/import/students", methods=["POST"])
def import_students_csv():
    init_db()
    f = request.files.get("file")
    if not f or f.filename == "":
        return redirect(url_for("index"))

    content = f.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    rows = []
    for r in reader:
        rows.append({_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})

    with db() as con:
        for r in rows:
            name = _get(r, "name", "student_name", "student").strip()
            studio = _get(r, "studio").strip().title()

            if not name or studio not in ("East", "West"):
                continue

            con.execute("""
                INSERT OR IGNORE INTO students
                (name, studio, phone, email, parents, accommodations)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                studio,
                _get(r, "phone"),
                _get(r, "email"),
                _get(r, "parents", "parent", "parent_s"),
                _get(r, "accommodations", "allergies", "notes"),
            ))

        con.commit()

    return redirect(url_for("index"))


@app.route("/import/purchases", methods=["POST"])
def import_purchases_csv():
    init_db()
    f = request.files.get("file")
    if not f or f.filename == "":
        return redirect(url_for("index"))

    content = f.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    rows = []
    for r in reader:
        rows.append({_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})

    with db() as con:
        for r in rows:
            student_name = _get(r, "student", "name", "student_name").strip()
            date_str = _get(r, "date", "purchase_date", "event_date").strip()
            classes = _to_int(_get(r, "classes_purchased", "classes", "class_count"), default=None)
            cost = _to_float(_get(r, "cost", "amount"), default=None)

            if not student_name or not date_str or classes is None or cost is None:
                continue

            stu = con.execute("SELECT id FROM students WHERE name=?", (student_name,)).fetchone()
            if not stu:
                continue

            con.execute("""
                INSERT INTO purchases
                (student_id, date, classes_purchased, cost, payment_method, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                int(stu["id"]),
                normalize_date_str(date_str),
                int(classes),
                float(cost),
                _get(r, "payment_method", "payment"),
                _get(r, "note", "notes"),
            ))

        con.commit()

    return redirect(url_for("index"))


@app.route("/import/attendance", methods=["POST"])
def import_attendance_csv():
    init_db()
    f = request.files.get("file")
    if not f or f.filename == "":
        return redirect(url_for("index"))

    content = f.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))

    rows = []
    for r in reader:
        rows.append({_norm_header(k): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})

    def _norm_status(s: str) -> str:
        s = (s or "").strip().lower()
        if s.startswith("attend"):
            return "attended"
        if s.startswith("charg"):
            return "charged"
        if s in ("a", "present", "p"):
            return "attended"
        if s in ("c", "no_show", "noshow", "absent", "charged/not attended"):
            return "charged"
        return ""

    with db() as con:
        for r in rows:
            student_name = _get(r, "student", "name", "student_name").strip()
            date_str = _get(r, "date", "event_date").strip()
            status = _norm_status(_get(r, "status", "attendance_status"))

            if not student_name or not date_str or not status:
                continue

            stu = con.execute("SELECT id FROM students WHERE name=?", (student_name,)).fetchone()
            if not stu:
                continue

            con.execute(
                "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                (int(stu["id"]), normalize_date_str(date_str), status)
            )

        con.commit()

    return redirect(url_for("index"))


# =========================
# ✅ CSV EXPORTS
# =========================

@app.route("/export/current_roster.csv")
def export_current_roster_csv():
    con = db()
    rows = con.execute("""
        SELECT
            name,
            studio,
            COALESCE(phone,'') AS phone,
            COALESCE(email,'') AS email,
            COALESCE(parents,'') AS parents,
            COALESCE(accommodations,'') AS accommodations
        FROM students
        ORDER BY studio, name
    """).fetchall()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Student Name","Studio","Phone","Email","Parent(s)","Allergies/Accommodations"])
    for r in rows:
        w.writerow([r["name"], r["studio"], r["phone"], r["email"], r["parents"], r["accommodations"]])

    resp = Response(out.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=current_roster.csv"
    return resp


@app.route("/export/purchases.csv")
def export_purchases_csv():
    con = db()
    rows = con.execute("""
        SELECT
            p.date,
            s.name AS student,
            s.studio,
            p.classes_purchased,
            p.cost,
            COALESCE(p.payment_method,'') AS payment_method,
            COALESCE(p.note,'') AS note
        FROM purchases p
        JOIN students s ON s.id = p.student_id
""").fetchall()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Date","Student","Studio","Classes Purchased","Amount","Payment Method","Note"])
    for r in rows:
        w.writerow([r["date"], r["student"], r["studio"], r["classes_purchased"], f"{r['cost']:.2f}", r["payment_method"], r["note"]])

    resp = Response(out.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=purchases.csv"
    return resp


@app.route("/export/attendance.csv")
def export_attendance_csv():
    con = db()
    rows = con.execute("""
        SELECT
            a.date,
            s.name AS student,
            s.studio,
            a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        ORDER BY a.date, a.id
    """).fetchall()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Date","Student","Studio","Status"])
    for r in rows:
        w.writerow([r["date"], r["student"], r["studio"], r["status"]])

    resp = Response(out.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=attendance.csv"
    return resp


@app.route("/export/student_balances.csv")
def export_student_balances_csv():
    con = db()
    rows = con.execute("""
        SELECT
            s.name,
            s.studio,
            COALESCE(SUM(p.classes_purchased), 0) AS purchased,
            (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id) AS used,
            COALESCE(SUM(p.classes_purchased), 0) -
            (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id) AS remaining
        FROM students s
        LEFT JOIN purchases p ON p.student_id = s.id
        GROUP BY s.id
        ORDER BY s.studio, s.name
    """).fetchall()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Student","Studio","Purchased","Used","Remaining"])
    for r in rows:
        w.writerow([r["name"], r["studio"], r["purchased"], r["used"], r["remaining"]])

    resp = Response(out.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=student_balances.csv"
    return resp


@app.route("/export/full_timeline.csv")
def export_full_timeline_csv():
    con = db()
    rows = con.execute("""
        SELECT
            p.date AS event_date,
            s.name AS student,
            s.studio,
            'Purchase' AS event_type,
            p.classes_purchased AS classes_purchased,
            p.cost AS cost,
            COALESCE(p.payment_method,'') AS payment_method,
            COALESCE(p.note,'') AS note,
            '' AS attendance_status
        FROM purchases p
        JOIN students s ON s.id = p.student_id

        UNION ALL

        SELECT
            a.date AS event_date,
            s.name AS student,
            s.studio,
            'Attendance' AS event_type,
            '' AS classes_purchased,
            '' AS cost,
            '' AS payment_method,
            '' AS note,
            a.status AS attendance_status
        FROM attendance a
        JOIN students s ON s.id = a.student_id

        ORDER BY event_date
    """).fetchall()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Date","Student","Studio","Event Type","Classes Purchased","Cost","Payment Method","Note","Attendance Status"])
    for r in rows:
        w.writerow([
            r["event_date"],
            r["student"],
            r["studio"],
            r["event_type"],
            r["classes_purchased"],
            r["cost"],
            r["payment_method"],
            r["note"],
            r["attendance_status"],
        ])

    resp = Response(out.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=full_timeline.csv"
    return resp


@app.route("/attendance/all")
def all_attendance():
    init_db()
    con = db()
    rows = con.execute("""
        SELECT
            a.date,
            s.name AS student,
            s.studio,
            a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        ORDER BY a.date ASC, a.id ASC
    """).fetchall()
    return render_template("attendance_all.html", rows=rows)


@app.route("/purchases/all")
def all_purchases():
    init_db()
    con = db()
    rows = con.execute("""
        SELECT
            p.date,
            s.name AS student,
            s.studio,
            p.classes_purchased,
            p.cost,
            COALESCE(p.payment_method,'') AS payment_method,
            COALESCE(p.note,'') AS note
        FROM purchases p
        JOIN students s ON s.id = p.student_id
        ORDER BY p.date ASC, p.id ASC
    """).fetchall()
    return render_template("purchases_all.html", rows=rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)