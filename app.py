from flask import Flask, render_template, request, redirect, url_for, flash,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_master.db'  # Change this for PostgreSQL if needed
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] ='#Arcanine17'
db = SQLAlchemy(app)

# Define User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # Store hashed password
    is_admin = db.Column(db.Boolean, default=False)
    fullname = db.Column(db.String(150), nullable=False)
    dob = db.Column(db.Date, nullable=False)  # Storing as Date format
    qualification = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def log():
    return render_template('login.html')

@app.route('/reg')
def reg():
    return render_template('register.html')


# 🔹 LOGIN ROUTE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch user from the database
        user = User.query.filter_by(email=email).first()

        # Check if user exists and password is correct
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['fullname'] = user.fullname
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to dashboard after login
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')

# 🔹 LOGOUT ROUTE
@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

# 🔹 DASHBOARD (Protected Route)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first!', 'warning')
        return redirect(url_for('login'))
    
    return f"Welcome {session['fullname']}! This is your dashboard."


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['fullname']
        qualification = request.form['qualification']
        dob = request.form['dob']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists! Please log in.', 'danger')
            return redirect(url_for('register'))

        # Convert dob from string to date format
        dob = datetime.strptime(dob, '%Y-%m-%d').date()

        # Hash password before storing
        hashed_password = generate_password_hash(password)

        # Create a new user
        new_user = User(
            email=email,
            password=hashed_password,
            fullname=fullname,
            qualification=qualification,
            dob=dob
        )

        # Add and commit to database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        #return render_template('login.html')
        return redirect(url_for('login'))

    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)

