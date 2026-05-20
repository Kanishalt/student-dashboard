import requests
import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session
import random
import time
import smtplib
import sqlite3

app = Flask(__name__)

app.permanent_session_lifetime = timedelta(minutes=30)
# =========================
# DATABASE SETUP
# =========================

conn = sqlite3.connect("database.db", check_same_thread=False)

cursor = conn.cursor()

# TODOS
cursor.execute("""
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    title TEXT,
    steps TEXT
)
""")

# FLASHCARDS
cursor.execute("""
CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    question TEXT,
    answer TEXT
)
""")

# NOTES
# NOTES
cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    filename TEXT,
    content TEXT
)
""")

# EXAMS
cursor.execute("""
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    title TEXT,
    date TEXT
)
""")

# FLASHNOTES
cursor.execute("""
CREATE TABLE IF NOT EXISTS flashnotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    content TEXT
)
""")

conn.commit()

app.secret_key = os.environ.get("SECRET_KEY")
EMAIL = os.environ.get("EMAIL")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")


# =========================
# SEND OTP FUNCTION
# =========================

def send_otp(receiver, otp):

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    data = {
        "sender": {
            "name": "Student Dashboard",
            "email": EMAIL
        },

        "to": [
            {
                "email": receiver
            }
        ],

        "subject": "Your OTP Code",

        "htmlContent": f"""
        <h2>Your OTP is: {otp}</h2>

        <p>OTP valid for 5 minutes.</p>

        <p>Do not share this code.</p>
        """
    }

    requests.post(url, json=data, headers=headers)


# =========================
# LOGIN PAGE
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    # already logged in
    if session.get("logged_in"):
        return redirect("/dashboard")

    if request.method == "POST":

        email = request.form["email"]

        otp = str(random.randint(100000, 999999))

        session["otp"] = otp
        session["email"] = email
        session["otp_time"] = time.time()
        send_otp(email, otp)

        return redirect("/verify")

    return render_template("login.html")


# =========================
# VERIFY OTP
# =========================

# =========================
# VERIFY OTP
# =========================

@app.route("/verify", methods=["GET", "POST"])
def verify():

    if request.method == "POST":

        user_otp = request.form["otp"]

        otp_time = session.get("otp_time")

        # OTP expired
        if otp_time and time.time() - otp_time > 300:

            return render_template(
                "verify.html",
                error="⌛ OTP Expired"
            )

        # CORRECT OTP
        if user_otp == session.get("otp"):

            session.permanent = True
            session["logged_in"] = True

            return redirect("/dashboard")

        # WRONG OTP
        else:

            return render_template(
                "verify.html",
                error="❌ Wrong OTP"
            )

    return render_template("verify.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):
        return redirect("/")

    cursor.execute(
        "SELECT * FROM exams WHERE email=?",
        (session["email"],)
    )

    exams = cursor.fetchall()

    return render_template(
        "index.html",
        exams=exams
    )

# =========================
# TIMER
# =========================

@app.route('/timer')
def timer():

    if not session.get("logged_in"):
        return redirect("/")

    return render_template("timer.html")


# =========================
# NOTES
# =========================

@app.route('/notes', methods=["GET", "POST"])
def notes():

    if not session.get("logged_in"):
        return redirect("/")

    email = session["email"]

    # SAVE NOTE
    if request.method == "POST":
        
        filename = request.form["filename"]

        content = request.form["content"]

        cursor.execute(
            "INSERT INTO notes (email, filename, content) VALUES (?, ?, ?)",
            (email, filename, content)
        )

        conn.commit()

    # LOAD USER NOTES
    cursor.execute(
        "SELECT * FROM notes WHERE email=?",
        (email,)
    )

    all_notes = cursor.fetchall()

    return render_template(
        "notes.html",
        notes=all_notes
    )


# =========================
# TODO
# =========================

@app.route('/todo', methods=["GET", "POST"])
def todo():

    if not session.get("logged_in"):
        return redirect("/")

    email = session["email"]

    # SAVE ROUTINE
    if request.method == "POST":

        title = request.form["title"]
        steps = request.form["steps"]

        cursor.execute(
            "INSERT INTO todos (email, title, steps) VALUES (?, ?, ?)",
            (email, title, steps)
        )

        conn.commit()

        return redirect("/todo")

    # LOAD ROUTINES
    cursor.execute(
        "SELECT * FROM todos WHERE email=?",
        (email,)
    )

    routines = cursor.fetchall()

    return render_template(
        "todo.html",
        routines=routines
    )

@app.route("/delete_todo/<int:id>")
def delete_todo(id):

    if not session.get("logged_in"):
        return redirect("/")

    cursor.execute(
        "DELETE FROM todos WHERE id=?",
        (id,)
    )

    conn.commit()

    return redirect("/todo")


# =========================
# CALENDAR
# =========================

@app.route('/calendar', methods=["GET", "POST"])
def calendar():

    if not session.get("logged_in"):
        return redirect("/")

    email = session["email"]

    # SAVE EXAM
    if request.method == "POST":

        title = request.form["title"]
        date = request.form["date"]

        cursor.execute(
            "INSERT INTO exams (email, title, date) VALUES (?, ?, ?)",
            (email, title, date)
        )

        conn.commit()

        return redirect("/calendar")

    # LOAD EXAMS
    cursor.execute(
        "SELECT * FROM exams WHERE email=?",
        (email,)
    )

    exams = cursor.fetchall()

    return render_template(
        "calendar.html",
        exams=exams
    )

@app.route("/delete_exam/<int:id>")
def delete_exam(id):

    if not session.get("logged_in"):
        return redirect("/")

    cursor.execute(
        "DELETE FROM exams WHERE id=?",
        (id,)
    )

    conn.commit()

    return redirect("/calendar")


# =========================
# FLASHCARDS
# =========================

@app.route('/flashcards', methods=["GET", "POST"])
def flashcards():

    if not session.get("logged_in"):
        return redirect("/")

    email = session["email"]

    # SAVE CARD
    if request.method == "POST":

        question = request.form["question"]
        answer = request.form["answer"]

        cursor.execute(
            "INSERT INTO flashcards (email, question, answer) VALUES (?, ?, ?)",
            (email, question, answer)
        )

        conn.commit()

        return redirect("/flashcards")

    # LOAD CARDS
    cursor.execute(
        "SELECT * FROM flashcards WHERE email=?",
        (email,)
    )

    cards = cursor.fetchall()

    return render_template(
        "flashcards.html",
        cards=cards
    )

@app.route("/delete_flashcard/<int:id>")
def delete_flashcard(id):

    if not session.get("logged_in"):
        return redirect("/")

    cursor.execute(
        "DELETE FROM flashcards WHERE id=?",
        (id,)
    )

    conn.commit()

    return redirect("/flashcards")


# =========================
# FLASH NOTES
# =========================

@app.route('/flashnotes', methods=["GET", "POST"])
def flashnotes():

    if not session.get("logged_in"):
        return redirect("/")

    email = session["email"]

    # SAVE FLASHNOTE
    if request.method == "POST":

        topic = request.form["topic"]
        content = request.form["content"]

        full_content = topic + "|||" + content

        cursor.execute(
            "INSERT INTO flashnotes (email, content) VALUES (?, ?)",
            (email, full_content)
        )

        conn.commit()

        return redirect("/flashnotes")

    # LOAD FLASHNOTES
    cursor.execute(
        "SELECT * FROM flashnotes WHERE email=?",
        (email,)
    )

    notes = cursor.fetchall()

    return render_template(
        "flashnotes.html",
        notes=notes
    )

@app.route("/delete_note/<int:id>")
def delete_note(id):

    if not session.get("logged_in"):
        return redirect("/")

    cursor.execute(
        "DELETE FROM notes WHERE id=?",
        (id,)
    )

    conn.commit()

    return redirect("/notes")

@app.route("/delete_flashnote/<int:id>")
def delete_flashnote(id):

    if not session.get("logged_in"):
        return redirect("/")

    cursor.execute(
        "DELETE FROM flashnotes WHERE id=?",
        (id,)
    )

    conn.commit()

    return redirect("/flashnotes")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run()