from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_NAME = "school.db"


# --------- DB INITIALIZATION ----------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Students table
        c.execute('''CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            enrollment_no TEXT UNIQUE NOT NULL,
            dob TEXT,
            class TEXT,
            section TEXT,
            attendance INTEGER DEFAULT 0,
            leaves_taken INTEGER DEFAULT 0,
            email TEXT
        )''')

        # Teachers table
        c.execute('''CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob TEXT,
            teacher_id TEXT UNIQUE NOT NULL,
            classes TEXT,
            email TEXT
        )''')

        # Attendance table
        c.execute('''CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )''')

        # Assignments table
        c.execute('''CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            description TEXT,
            deadline TEXT,
            student_id INTEGER,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(student_id) REFERENCES students(id)
        )''')

        # Holidays table
        c.execute('''CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            occasion TEXT
        )''')

        # Timetable table
        c.execute('''CREATE TABLE IF NOT EXISTS timetables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT, -- 'student' or 'teacher'
            user_id INTEGER,
            day TEXT,
            subject TEXT,
            time TEXT
        )''')

        conn.commit()


# --------- HOME & AUTH ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']

        if role == 'student':
            name = request.form['name']
            enrollment_no = request.form['enrollment_no']

            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM students WHERE name=? AND enrollment_no=?", (name, enrollment_no))
                student = c.fetchone()
                if student:
                    session['user'] = {'role': 'student',
                                       'id': student[0], 'name': student[1]}
                    return redirect(url_for('student_profile'))
                else:
                    flash("Invalid student login")

        elif role == 'teacher':
            name = request.form['name']
            dob = request.form['dob']
            teacher_id = request.form['teacher_id']

            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM teachers WHERE name=? AND dob=? AND teacher_id=?", (name, dob, teacher_id))
                teacher = c.fetchone()
                if teacher:
                    session['user'] = {'role': 'teacher',
                                       'id': teacher[0], 'name': teacher[1]}
                    return redirect(url_for('teacher_profile'))
                else:
                    flash("Invalid teacher login")

    return render_template('login.html')


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        dob = request.form['dob']
        email = request.form['email']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()

            if role == 'student':
                enrollment_no = request.form['enrollment_no']
                c.execute("INSERT INTO students (name, dob, email, enrollment_no) VALUES (?, ?, ?, ?)",
                          (name, dob, email, enrollment_no))
                conn.commit()

            elif role == 'teacher':
                teacher_id = request.form['teacher_id']
                c.execute("INSERT INTO teachers (name, dob, email, teacher_id) VALUES (?, ?, ?, ?)",
                          (name, dob, email, teacher_id))
                conn.commit()

        flash("Sign in successful, you can now login.")
        return redirect(url_for('login'))

    return render_template('signin.html')


# --------- STUDENT ----------
@app.route('/student/profile')
def student_profile():
    if 'user' not in session or session['user']['role'] != 'student':
        return redirect(url_for('login'))

    sid = session['user']['id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Get student details
        c.execute(
            "SELECT name, enrollment_no, dob, class, section, attendance, leaves_taken FROM students WHERE id=?", (sid,))
        student = c.fetchone()

        # Attendance %
        total = c.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=?", (sid,)).fetchone()[0]
        present = c.execute(
            "SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='present'", (sid,)).fetchone()[0]
        attendance_percent = round((present/total)*100, 2) if total > 0 else 0

        # Assignments
        pending_assignments = c.execute(
            "SELECT subject, description, deadline FROM assignments WHERE student_id=? AND status='pending'", (sid,)).fetchall()

    return render_template('student_profile.html',
                           student=student,
                           attendance_percent=attendance_percent,
                           pending_assignments=pending_assignments)


@app.route('/student/attendance')
def student_attendance():
    if 'user' not in session or session['user']['role'] != 'student':
        return redirect(url_for('login'))

    sid = session['user']['id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        records = c.execute(
            "SELECT date, status FROM attendance WHERE student_id=?", (sid,)).fetchall()

    return render_template('attendance.html', attendance_records=records)


@app.route('/student/assignments')
def student_assignments():
    if 'user' not in session or session['user']['role'] != 'student':
        return redirect(url_for('login'))

    sid = session['user']['id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        pending = c.execute(
            "SELECT subject, description, deadline FROM assignments WHERE student_id=? AND status='pending'", (sid,)).fetchall()
        completed = c.execute(
            "SELECT subject, description, deadline FROM assignments WHERE student_id=? AND status='completed'", (sid,)).fetchall()

    return render_template('assignments.html', pending_assignments=pending, completed_assignments=completed)


@app.route('/student/timetable')
def student_timetable():
    if 'user' not in session or session['user']['role'] != 'student':
        return redirect(url_for('login'))

    sid = session['user']['id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        timetable = c.execute(
            "SELECT day, subject, time FROM timetables WHERE user_type='student' AND user_id=?", (sid,)).fetchall()

    return render_template('student_timetable.html', timetable=timetable)


@app.route('/student/holidays')
def student_holidays():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        holidays = c.execute("SELECT date, occasion FROM holidays").fetchall()

    return render_template('holidays.html', holidays=holidays)


# --------- TEACHER ----------
@app.route('/teacher/profile')
def teacher_profile():
    if 'user' not in session or session['user']['role'] != 'teacher':
        return redirect(url_for('login'))

    tid = session['user']['id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        teacher = c.execute(
            "SELECT name, dob, teacher_id, classes FROM teachers WHERE id=?", (tid,)).fetchone()
        students = c.execute(
            "SELECT name, class, section, enrollment_no FROM students").fetchall()

    return render_template('teacher_profile.html', teacher=teacher, students=students)


@app.route('/teacher/timetable')
def teacher_timetable():
    if 'user' not in session or session['user']['role'] != 'teacher':
        return redirect(url_for('login'))

    tid = session['user']['id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        timetable = c.execute(
            "SELECT day, subject, time FROM timetables WHERE user_type='teacher' AND user_id=?", (tid,)).fetchall()

    return render_template('timetable_teacher.html', timetable=timetable)


@app.route('/teacher/mark_attendance/<int:student_id>/<status>')
def mark_attendance(student_id, status):
    if 'user' not in session or session['user']['role'] != 'teacher':
        return redirect(url_for('login'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO attendance (student_id, date, status) VALUES (?, DATE('now'), ?)", (student_id, status))
        conn.commit()

    return redirect(url_for('teacher_profile'))


@app.route('/teacher/upload_assignment/<int:student_id>', methods=['POST'])
def upload_assignment(student_id):
    if 'user' not in session or session['user']['role'] != 'teacher':
        return redirect(url_for('login'))

    subject = request.form['subject']
    description = request.form['description']
    deadline = request.form['deadline']

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO assignments (subject, description, deadline, student_id) VALUES (?, ?, ?, ?)",
                  (subject, description, deadline, student_id))
        conn.commit()

    return redirect(url_for('teacher_profile'))


# --------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
