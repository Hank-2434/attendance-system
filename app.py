from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB_NAME = "attendance.db"

# Simple schedule example
SCHEDULE = {
    "Monday": {"start": "08:00", "grace": 10},
    "Tuesday": {"start": "07:00", "grace": 10},
    "Wednesday": {"start": "08:00", "grace": 10},
    "Thursday": {"start": "07:00", "grace": 10},
    "Friday": {"start": "08:00", "grace": 10},
}

# Home page
@app.route("/")
def index():
    return render_template("index.html")

# Add student page
@app.route("/add_student", methods=["GET", "POST"])
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
        return redirect("/")
    return render_template("add_student.html")

@app.route("/remove_student", methods=["GET", "POST"])
def remove_student():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        student_id = request.form["student_id"]
        cursor.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        cursor.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
        conn.commit()
        return redirect("/remove_student")

    cursor.execute("SELECT student_id, name, gender FROM students ORDER BY name")
    students = cursor.fetchall()
    conn.close()

    return render_template("remove_student.html", students=students)

# Attendance page
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if request.method == "POST":
        student_id = request.form["student_id"]

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

            cursor.execute(
                "SELECT * FROM attendance WHERE student_id=? AND date=?",
                (student_id, date)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO attendance (student_id, name, date, time_in, status) VALUES (?, ?, ?, ?, ?)",
                    (student_id, name, date, time_in, status)
                )
                conn.commit()

    # ✅ Always fetch students for display
    cursor.execute("SELECT student_id, name, gender FROM students ORDER BY name")
    students = cursor.fetchall()
    conn.close()

    return render_template("attendance.html", students=students)

@app.route("/view/Male")
def view_male():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.student_id, a.name, a.date, a.time_in, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.gender = 'Male'
        ORDER BY a.date DESC
    """)
    records = cursor.fetchall()
    conn.close()

    return render_template("view_gender.html", records=records, gender="Male")

@app.route("/view/Female")
def view_female():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.student_id, a.name, a.date, a.time_in, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.gender = 'Female'
        ORDER BY a.date DESC
    """)
    records = cursor.fetchall()
    conn.close()

    return render_template("view_gender.html", records=records, gender="Female")

    
@app.route("/total_attendance")
def total_attendance():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Male attendance totals
    cursor.execute("""
        SELECT status, COUNT(*)
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.gender = 'Male'
        GROUP BY status
    """)
    male_data = cursor.fetchall()

    # Female attendance totals
    cursor.execute("""
        SELECT status, COUNT(*)
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.gender = 'Female'
        GROUP BY status
    """)
    female_data = cursor.fetchall()

    conn.close()

    return render_template(
        "total_attendance.html",
        male_data=male_data,
        female_data=female_data
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)