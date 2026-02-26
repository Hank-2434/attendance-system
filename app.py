from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# ------------------ DATABASE PATH ------------------
if os.environ.get("RENDER") == "true":
    DB_NAME = "/tmp/attendance.db"
else:
    DB_NAME = os.path.join(os.path.dirname(__file__), "attendance.db")

# ------------------ LOGIN REQUIRED DECORATOR ------------------
def login_required(roles=None):
    def wrapper(fn):
        def decorated(*args, **kwargs):
            if "username" not in session:
                return redirect("/login")
            if roles and session.get("role") not in roles:
                return "Access denied"
            return fn(*args, **kwargs)
        decorated.__name__ = fn.__name__
        return decorated
    return wrapper

# ------------------ INITIALIZE DATABASE ------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        gender TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        time_in TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ------------------ CLASS SCHEDULE ------------------
SCHEDULE = {
    "Monday": {"start": "08:00", "grace": 10},
    "Tuesday": {"start": "07:00", "grace": 10},
    "Wednesday": {"start": "08:00", "grace": 10},
    "Thursday": {"start": "07:00", "grace": 10},
    "Friday": {"start": "08:00", "grace": 10},
}

# ------------------ LANDING PAGE ------------------
@app.route("/")
def landing():
    if "username" in session:
        return redirect("/home")
    return render_template("landing.html")

# ------------------ LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
        result = cursor.fetchone()
        conn.close()

        if result:
            session["username"] = username
            session["role"] = result[0]
            return redirect("/home")
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

# ------------------ REGISTER ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Automatically assign adviser role to the first 3 accounts
        adviser_accounts = ["Hank", "Zen Ablao", "Rey Batiles"]  # REPLACE with your actual usernames
        role = "adviser" if username in adviser_accounts else "student"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, password, role)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username already exists")
        conn.close()
        return redirect("/login")
    return render_template("register.html")

# ------------------ LOGOUT ------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ------------------ HOME PAGE ------------------
@app.route("/home")
@login_required()
def home():
    return render_template("index.html", username=session.get("username"), role=session.get("role"))

# ------------------ ADD STUDENT ------------------
@app.route("/add_student", methods=["GET", "POST"])
@login_required(roles=["adviser", "secretary"])
def add_student():
    if request.method == "POST":
        student_id = request.form["student_id"]
        name = request.form["name"]
        gender = request.form["gender"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO students (student_id, name, gender) VALUES (?, ?, ?)",
                (student_id, name, gender)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
        return redirect("/home")
    return render_template("add_student.html")

# ------------------ REMOVE STUDENT ------------------
@app.route("/remove_student", methods=["GET", "POST"])
@login_required(roles=["adviser"])
def remove_student():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if request.method == "POST":
        student_id = request.form["student_id"]
        cursor.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        cursor.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
        conn.commit()
        return redirect("/remove_student")
    cursor.execute("SELECT student_id, name FROM students")
    students = cursor.fetchall()
    conn.close()
    return render_template("remove_student.html", students=students)

# ------------------ ATTENDANCE ------------------
@app.route("/attendance", methods=["GET", "POST"])
@login_required(roles=["adviser", "secretary", "student"])
def attendance():
    if request.method == "POST":
        student_id = request.form["student_id"]

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE student_id=?", (student_id,))
        result = cursor.fetchone()
        if result:
            name = result[0]

            today = datetime.now()
            day_of_week = today.strftime("%A")
            if day_of_week in SCHEDULE:
                start_time = datetime.strptime(SCHEDULE[day_of_week]["start"], "%H:%M")
                late_cutoff = start_time + timedelta(minutes=SCHEDULE[day_of_week]["grace"])
            else:
                late_cutoff = datetime.now()

            status = "On Time" if datetime.now().time() <= late_cutoff.time() else "Late"
            date = today.strftime("%Y-%m-%d")
            time_in = today.strftime("%H:%M")

            cursor.execute("SELECT * FROM attendance WHERE student_id=? AND date=?", (student_id, date))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO attendance (student_id, name, date, time_in, status) VALUES (?, ?, ?, ?, ?)",
                    (student_id, name, date, time_in, status)
                )
                conn.commit()
        conn.close()
    return render_template("attendance.html")

# ------------------ TOTAL ATTENDANCE ------------------
@app.route("/total_attendance")
@login_required(roles=["adviser", "secretary"])
def total_attendance():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, COUNT(*)
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.gender = 'Male'
        GROUP BY status
    """)
    male_data = cursor.fetchall()

    cursor.execute("""
        SELECT status, COUNT(*)
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.gender = 'Female'
        GROUP BY status
    """)
    female_data = cursor.fetchall()

    conn.close()
    return render_template("total_attendance.html", male_data=male_data, female_data=female_data)

# ------------------ RUN APP ------------------
if __name__ == "__main__":

    app.run(host="0.0.0.0", port=10000, debug=True)
