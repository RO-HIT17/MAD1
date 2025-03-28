from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
from sqlalchemy.orm import joinedload
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_master.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] ='#Arcanine17'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  
    is_admin = db.Column(db.Boolean, default=False)
    fullname = db.Column(db.String(150), nullable=False)
    dob = db.Column(db.Date, nullable=False)  
    qualification = db.Column(db.String(100), nullable=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Subject {self.name}>'

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    subject = db.relationship('Subject', backref=db.backref('chapters', lazy=True))

    def __repr__(self):
        return f'<Chapter {self.name}>'


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.Date, nullable=False)
    time_duration = db.Column(db.String(10), nullable=False)  
    remarks = db.Column(db.Text, nullable=True)

    chapter = db.relationship('Chapter', backref=db.backref('quizzes', lazy=True))

    def __repr__(self):
        return f'<Quiz on {self.date_of_quiz}>'


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_title = db.Column(db.String(200), nullable=False)
    question_statement = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(255), nullable=False)
    option2 = db.Column(db.String(255), nullable=False)
    option3 = db.Column(db.String(255), nullable=True)
    option4 = db.Column(db.String(255), nullable=True)
    correct_option = db.Column(db.String(10), nullable=False)  
    
    quiz = db.relationship('Quiz', backref=db.backref('questions', lazy=True))

    def __repr__(self):
        return f'<Question {self.question_statement[:50]}...>'


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_stamp_of_attempt = db.Column(db.DateTime, nullable=False)
    total_scored = db.Column(db.Integer, nullable=False)

    quiz = db.relationship('Quiz', backref=db.backref('scores', lazy=True))
    user = db.relationship('User', backref=db.backref('scores', lazy=True))

    def __repr__(self):
        return f'<Score {self.total_scored} by User {self.user_id}>'


with app.app_context():
    db.create_all()  
    if not User.query.filter_by(email="admin@example.com").first():
        admin_user = User(
            email="admin@example.com",
            password=generate_password_hash("admin123", method="pbkdf2:sha256"),
            is_admin=True,
            fullname="Admin User",
            dob=datetime.strptime("1990-01-01", "%Y-%m-%d").date(),  
            qualification="Master's Degree"
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Admin user created!")
    else:
        print("⚠️ Admin user already exists.")
        
@app.route('/')
def log():
    return render_template('login.html')

@app.route('/reg')
def reg():
    return render_template('register.html')

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash('Please log in first!', 'warning')
        return redirect(url_for('login'))

    # Using JOIN to get subject name and count questions efficiently
    quizzes = (
        db.session.query(
            Quiz.id,
            Chapter.name.label("subject_name"),
            Quiz.date_of_quiz,
            Quiz.time_duration,
            db.func.count(Question.id).label("num_questions")
        )
        .join(Chapter, Quiz.chapter_id == Chapter.id)
        .join(Subject, Chapter.subject_id == Subject.id)
        .outerjoin(Question, Question.quiz_id == Quiz.id)
        .group_by(Quiz.id, Subject.name, Quiz.date_of_quiz, Quiz.time_duration)
        .all()
    )

    return render_template('userdashboard.html', quizzes=quizzes)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied! Admins only.', 'danger')
        return redirect(url_for('login'))

    subjects = Subject.query.all()

    # Fetch chapters and count questions
    subjects_with_chapters = []
    for subject in subjects:
        chapters = []
        for chapter in subject.chapters:
            question_count = Question.query.filter_by(quiz_id=chapter.id).count()
            chapters.append({
                'id': chapter.id,
                'name': chapter.name,
                'question_count': question_count
            })
        
        subjects_with_chapters.append({
            'id': subject.id,
            'name': subject.name,
            'chapters': chapters
        })

    return render_template('admin.html', subjects=subjects_with_chapters)


@app.route('/new_sub')
def new_sub():
    return render_template('newsubject.html')

@app.route('/new_chap/<int:sub_id>')
def new_chap(sub_id):
    return render_template('newchapter.html', sub_id=sub_id)

@app.route('/new_quiz')
def new_quiz():
    subjects = Subject.query.all()
    return render_template("newquiz.html", subjects=subjects)

@app.route("/get_chapters/<int:subject_id>")
def get_chapters(subject_id):
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()
    chapter_list = [{"id": c.id, "name": c.name} for c in chapters]
    return jsonify(chapter_list)

@app.route('/new_ques')
def new_ques():
    return render_template('newquestion.html')

@app.route('/quiz_manage')
def quiz_management():
    quizzes = (
        Quiz.query
        .options(
            joinedload(Quiz.chapter),  
            joinedload(Quiz.questions)  
        )
        .all()
    )

    return render_template('quizmanagement.html', quizzes=quizzes)

@app.route('/summary')
def summary():
    return render_template('summary.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        
        user = User.query.filter_by(email=email).first()

        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['fullname'] = user.fullname
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))  

            
            return redirect(url_for('user_dashboard'))  
        
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')  

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        fullname = request.form['fullname']
        qualification = request.form['qualification']
        dob = request.form['dob']

        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists! Please log in.', 'danger')
            return redirect(url_for('register'))

        
        dob = datetime.strptime(dob, '%Y-%m-%d').date()

        
        hashed_password = generate_password_hash(password)

        
        new_user = User(
            email=email,
            password=hashed_password,
            fullname=fullname,
            qualification=qualification,
            dob=dob
        )

        
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/view_quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Please log in to continue.', 'danger')
        return redirect(url_for('login'))

    # Using Join to fetch quiz details and count questions dynamically
    quiz = db.session.query(
        Quiz.id, Quiz.date_of_quiz, Quiz.time_duration,
        Subject.name.label('subject_name'), Chapter.name.label('chapter_name'),
        db.func.count(Question.id).label('num_questions')  # Count number of questions
    ).join(Chapter, Quiz.chapter_id == Chapter.id)\
     .join(Subject, Chapter.subject_id == Subject.id)\
     .outerjoin(Question, Quiz.id == Question.quiz_id)\
     .filter(Quiz.id == quiz_id)\
     .group_by(Quiz.id, Subject.name, Chapter.name)\
     .first()

    if not quiz:
        flash('Quiz not found!', 'danger')
        return redirect(url_for('user_dashboard'))

    return render_template('viewquiz.html', quiz=quiz)


@app.route('/add_subject', methods=['POST'])
def add_subject():
    if not session.get('is_admin'):  
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('admin_dashboard'))

    subject_name = request.form['subject_name']
    description = request.form['description']

    new_subject = Subject(name=subject_name, description=description)
    db.session.add(new_subject)
    db.session.commit()

    flash('Subject added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/add_chapter/<int:subject_id>', methods=['GET', 'POST'])
def add_chapter(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    if request.method == 'POST':
        chapter_name = request.form['name']
        chapter_description = request.form.get('description', '')

        new_chapter = Chapter(subject_id=subject.id, name=chapter_name, description=chapter_description)
        db.session.add(new_chapter)
        db.session.commit()

        flash(f'Chapter "{chapter_name}" added successfully!', 'success')
        return redirect(url_for('admin_dashboard')) 
        
    return render_template('newchapter.html', subject=subject)

@app.route("/add_quiz", methods=["POST"])
def add_quiz():
    try:
        chapter_id = request.form.get("chapter_id")
        date_of_quiz = request.form.get("date")
        time_duration = request.form.get("duration")
        remarks = request.form.get("remarks", "")  

        
        date_of_quiz = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()

        
        new_quiz = Quiz(
            chapter_id=chapter_id,
            date_of_quiz=date_of_quiz,
            time_duration=time_duration,
            remarks=remarks
        )

        
        db.session.add(new_quiz)
        db.session.commit()

        flash("Quiz added successfully!", "success")
        return redirect(url_for("admin_dashboard"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding quiz: {str(e)}", "danger")
        return redirect(url_for("new_quiz"))

@app.route("/new_question/<int:quiz_id>")
def new_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quizzes = Quiz.query.options(joinedload(Quiz.chapter)).all()  

    return render_template("newquestion.html", quiz=quiz, quizzes=quizzes)

@app.route("/add_question", methods=["POST"])
def add_question():
    try:
        quiz_id = int(request.form.get("quiz_id"))  
        question_title = request.form.get("question_title")  
        question_statement = request.form.get("question_statement")
        option1 = request.form.get("option1")
        option2 = request.form.get("option2")
        option3 = request.form.get("option3", "")  
        option4 = request.form.get("option4", "")  
        correct_option = request.form.get("correct_option")

        new_question = Question(
            quiz_id=quiz_id,
            question_title=question_title,  
            question_statement=question_statement,
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_option=correct_option
        )

        db.session.add(new_question)
        db.session.commit()

        flash("Question added successfully!", "success")
        return redirect(url_for("new_question", quiz_id=quiz_id))  

    except Exception as e:
        db.session.rollback()
        flash(f"Error adding question: {str(e)}", "danger")
        return redirect(url_for('quiz_management')) 


@app.route('/chapter/edit/<int:chapter_id>', methods=['POST'])
def edit_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    chapter.name = request.form['chapter_name']
    chapter.description = request.form['chapter_desc']
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/chapter/delete/<int:chapter_id>', methods=['POST'])
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    db.session.delete(chapter)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/question/edit/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    question.question_title = request.form['question_title']
    question.question_statement = request.form['question_statement']
    question.option1 = request.form['option1']
    question.option2 = request.form['option2']
    question.option3 = request.form['option3']
    question.option4 = request.form['option4']
    question.correct_option = request.form['correct_option']
    db.session.commit()
    return redirect(url_for('quiz_management'))

@app.route('/question/delete/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('quiz_management'))


@app.route('/logout')
def logout():
    session.clear()  
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)

