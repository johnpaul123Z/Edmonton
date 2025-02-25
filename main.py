#imports 
from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from O365 import Account
import json
from config import client_id, client_secret
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Microsoft OAuth Credentials
credentials = (client_id, client_secret)
scopes = ['Mail.ReadWrite', 'Mail.Send']

# Simple in-memory database for OAuth flow
class MyDB:
    def __init__(self):
        self.storage = {}

    def store_flow(self, flow):
        self.storage['flow'] = flow

    def get_flow(self):
        return self.storage.get('flow')

my_db = MyDB()

def serialize(flow):
    return json.dumps(flow)

def deserialize(flow_str):
    return json.loads(flow_str)

# Profile Model
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=True)
    pass_word = db.Column(db.String(200), nullable=False)  # Hashed passwords

    def set_password(self, password):
        self.pass_word = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pass_word, password)

# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/creat')
def index():
    return render_template('add_profile.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        first_name = request.form.get("first_name")
        pass_word = request.form.get("pass_word")

        # Check if user exists in the database
        user = Profile.query.filter_by(first_name=first_name).first()

        if user and user.check_password(pass_word):  # Verify hashed password
            return "Login Successful!"
        else:
            return "Invalid username or password!"

    return render_template('log.html')  # Show login form for GET requests

@app.route('/stepone')
def auth_step_one():
    callback = url_for('auth_step_two_callback', _external=True).replace("127.0.0.1", "localhost")

    account = Account(credentials)
    url, flow = account.con.get_authorization_url(requested_scopes=scopes, redirect_uri=callback)

    my_db.store_flow(serialize(flow))  # Store flow for Step 2

    return redirect(url)

@app.route('/steptwo')
def auth_step_two_callback():
    account = Account(credentials)

    my_saved_flow_str = my_db.get_flow()
    if not my_saved_flow_str:
        return "Flow state not found. Restart authentication.", 400

    my_saved_flow = deserialize(my_saved_flow_str)

    requested_url = request.url  # Get current URL with auth code

    result = account.con.request_token(requested_url, flow=my_saved_flow)

    if result:
        return render_template('auth_complete.html')

    return "Authentication failed", 400

@app.route('/add', methods=["POST"])
def profile():
    first_name = request.form.get("first_name")
    pass_word = request.form.get("pass_word")

    if first_name and pass_word:
        p = Profile(first_name=first_name)
        p.set_password(pass_word)  # Hash password before storing
        db.session.add(p)
        db.session.commit()
        return redirect('/stepone')
    else:
        return redirect('/')

@app.route('/delete/<int:id>')
def erase(id):
    data = Profile.query.get(id)
    if data:
        db.session.delete(data)
        db.session.commit()
    return redirect('/')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  
    app.run(host='0.0.0.0',port=5000)
