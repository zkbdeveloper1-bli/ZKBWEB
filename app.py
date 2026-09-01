
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import timedelta

app = Flask(__name__)

# -------------------------
# SECRET KEY
# -------------------------

app.secret_key = secrets.token_hex(32)

# -------------------------
# DATABASE
# -------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///zkbweb.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -------------------------
# USER MODEL
# -------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    session_token = db.Column(db.String(100), nullable=True)


# -------------------------
# MESSAGE MODEL
# -------------------------

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    sender = db.Column(
        db.String(50),
        nullable=False
    )

    # Purani database mein receiver column hai.
    # Group chat mein har message ka receiver "all" hoga.
    receiver = db.Column(
        db.String(50),
        nullable=False,
        default="all"
    )

    text = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


# -------------------------
# CREATE DATABASE + USERS
# -------------------------

with app.app_context():

    db.create_all()

    users = [
        ("user1", "password1"),
        ("user2", "password2"),
        ("user3", "password3")
    ]

    for username, password in users:

        existing = User.query.filter_by(
            username=username
        ).first()

        if not existing:

            new_user = User(
                username=username,
                password_hash=generate_password_hash(password)
            )

            db.session.add(new_user)

    db.session.commit()


# -------------------------
# LOGIN
# -------------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if "username" in session:
        return redirect("/home")

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(
            username=username
        ).first()

        if user and check_password_hash(
            user.password_hash,
            password
        ):

            token = secrets.token_hex(32)

            user.session_token = token

            db.session.commit()

            session["username"] = username
            session["token"] = token

            session.permanent = True

            app.permanent_session_lifetime = timedelta(
                minutes=15
            )

            return redirect("/home")

        return render_template(
            "login.html",
            error="Username ya password ghalat hai."
        )

    return render_template("login.html")


# -------------------------
# HOME
# -------------------------

@app.route("/home")
def home():

    if "username" not in session:
        return redirect("/")

    user = User.query.filter_by(
        username=session["username"]
    ).first()

    # Session security check
    if not user or user.session_token != session.get("token"):

        session.clear()

        return redirect("/")

    # ALL users ko ALL messages nazar aayenge
    messages = Message.query.order_by(
        Message.created_at.asc()
    ).all()

    return render_template(
        "home.html",
        username=session["username"],
        messages=messages
    )


# -------------------------
# SEND MESSAGE
# -------------------------

@app.route("/send", methods=["POST"])
def send():

    if "username" not in session:
        return redirect("/")

    text = request.form.get(
        "text",
        ""
    ).strip()

    if not text:
        return redirect("/home")

    # Group message
    # receiver = all
    message = Message(
        sender=session["username"],
        receiver="all",
        text=text
    )

    db.session.add(message)

    db.session.commit()

    return redirect("/home")


# -------------------------
# CHANGE PASSWORD
# -------------------------

@app.route("/change-password", methods=["POST"])
def change_password():

    if "username" not in session:
        return redirect("/")

    # Sirf User1 password change kar sakta hai
    if session["username"] != "user1":
        return "Access denied"

    username = request.form.get(
        "username"
    )

    new_password = request.form.get(
        "new_password",
        ""
    ).strip()

    # Sirf User2 aur User3
    if username not in ["user2", "user3"]:
        return "Invalid user"

    if not new_password:
        return "Password required"

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return "User not found"

    user.password_hash = generate_password_hash(
        new_password
    )

    db.session.commit()

    return redirect("/home")


# -------------------------
# LOGOUT
# -------------------------

@app.route("/logout")
def logout():

    if "username" in session:

        user = User.query.filter_by(
            username=session["username"]
        ).first()

        if user:

            user.session_token = None

            db.session.commit()

    # Session delete
    session.clear()

    return redirect("/")


# -------------------------
# RUN SERVER
# -------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )

