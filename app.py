from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_zkbweb'

# File Upload Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB Max Limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Session Expiry Time (15 Minutes)
app.permanent_session_lifetime = timedelta(minutes=15)

# Database Models
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(10), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserSession(db.Model):
    username = db.Column(db.String(50), primary_key=True)
    force_logout = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# Credentials
USERS = {
    "User 1": "1234",
    "User 2": "1234",
    "User 3": "1234"
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def check_force_logout():
    if 'user' in session:
        user_sess = UserSession.query.get(session['user'])
        if user_sess and user_sess.force_logout:
            user_sess.force_logout = False
            db.session.commit()
            session.pop('user', None)
            return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USERS and USERS[username] == password:
            session.permanent = True
            session['user'] = username
            
            user_sess = UserSession.query.get(username)
            if not user_sess:
                user_sess = UserSession(username=username, force_logout=False)
                db.session.add(user_sess)
            else:
                user_sess.force_logout = False
            db.session.commit()
            
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template('home.html', user=session['user'], messages=messages)

@app.route('/send', methods=['POST'])
def send():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    file = request.files.get('file')
    filename = None
    file_type = None

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        secured_name = secure_filename(file.filename)
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secured_name}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        file_type = 'image' if ext in {'png', 'jpg', 'jpeg', 'gif'} else 'zip'

    if content or filename:
        msg = Message(sender=session['user'], content=content, filename=filename, file_type=file_type)
        db.session.add(msg)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/force_logout/<target_user>', methods=['POST'])
def force_logout(target_user):
    if session.get('user') == 'User 1' and target_user in ['User 2', 'User 3']:
        user_sess = UserSession.query.get(target_user)
        if user_sess:
            user_sess.force_logout = True
        else:
            user_sess = UserSession(username=target_user, force_logout=True)
            db.session.add(user_sess)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)