from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_zkbweb_v2'

# Upload Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB Max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.permanent_session_lifetime = timedelta(minutes=30)

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

class UserCredentials(db.Model):
    username = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.String(100), nullable=False)

def init_users():
    default_users = {
        "User 1": "1234",
        "User 2": "1234",
        "User 3": "1234"
    }
    for u, p in default_users.items():
        if not UserCredentials.query.get(u):
            db.session.add(UserCredentials(username=u, password=p))
    db.session.commit()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def check_force_logout():
    db.create_all()
    init_users()
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
        
        user_cred = UserCredentials.query.get(username)
        if user_cred and user_cred.password == password:
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
        return render_template('login.html', error="Invalid Username or Password")
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

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    current_user = session['user']
    target_user = request.form.get('target_user')
    new_password = request.form.get('new_password')

    if not new_password or len(new_password.strip()) == 0:
        return redirect(url_for('home'))

    # Admin User 1 can change anyone's password. Other users can only change their own.
    if current_user == 'User 1' or current_user == target_user:
        user_cred = UserCredentials.query.get(target_user)
        if user_cred:
            user_cred.password = new_password
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