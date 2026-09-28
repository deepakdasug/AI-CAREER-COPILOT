from flask import Flask, render_template, request, redirect, session
from db import engine, Base, SessionLocal
from werkzeug.security import check_password_hash, generate_password_hash
import PyPDF2
import docx
import json
import os
from dotenv import load_dotenv
import models  # Important for SQLAlchemy to know what tables to build!
import ai

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Create tables cleanly within the application context so it doesn't loop pointlessly
with app.app_context():
    print("Creating tables in the test database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")


# Home
@app.route("/")
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return render_template('home.html')


# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = (request.form.get("name") or "").strip()
        email = (request.form.get('email') or "").strip().lower()
        password = request.form.get('password') or ""

        if not name or not email or len(password) < 6:
            return render_template('signup.html', error='Enter your name and email, and use a password with at least 6 characters.'), 400

        with SessionLocal() as db:
            existing_user = db.query(models.User).filter_by(email=email).first()
            if existing_user:
                return render_template('signup.html', error='An account with that email already exists.'), 409

            user = models.User(name=name, email=email, password=generate_password_hash(password))
            db.add(user)
            db.commit()
        return redirect('/login')
    return render_template('signup.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or "").strip().lower()
        password = request.form.get('password') or ""

        with SessionLocal() as db:
            user = db.query(models.User).filter_by(email=email).first()
            stored_password = user.password or "" if user else ""
            is_hashed = stored_password.startswith(('scrypt:', 'pbkdf2:'))
            password_matches = (
                check_password_hash(stored_password, password)
                if user and is_hashed
                else bool(user and stored_password == password)
            )

            if password_matches:
                session['user'] = user.email
                session['user_name'] = user.name
                return redirect('/dashboard')

        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


# Dashboard
@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    
    result = None
    
    if request.method == "POST":
        user_goal = request.form.get("role")
        resume_text = request.form.get('resume')

        # Use request.files instead of request.form for files!
        file = request.files.get('file')

        # File handling
        if file and file.filename != "":
            if file.filename.endswith(".pdf"):
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""
                    resume_text = text
                except Exception as e:
                    result = {"error": f"PDF error: {str(e)}"}
            
            elif file.filename.endswith(".docx"):
                try:
                    doc = docx.Document(file)
                    text = ""
                    for para in doc.paragraphs:
                        text += para.text + "\n"
                    resume_text = text
                except Exception as e:
                    result = {"error": f"Docx error: {str(e)}"}

        if resume_text and user_goal and not (result and result.get("error")):

            try:
                result = ai.analyze_resume(resume_text, user_goal)

                if not result.get('error'):
                    with SessionLocal() as db:
                        user = db.query(models.User).filter_by(email=session["user"]).first()
                        if not user:
                            session.clear()
                            return redirect('/login')

                        report = models.Reports(
                            user_id=user.id,
                            resume_text=resume_text,
                            result=json.dumps(result)
                        )
                        db.add(report)
                        db.commit()

            except Exception as e:
                result = {"error": f"AI error: {str(e)}"}
        elif not result:
            result = {"error": "Provide resume text or upload a PDF/DOCX file and enter a career goal."}

    return render_template(
        "dashboard.html",
        user=session["user"],
        user_name=session.get('user_name', 'Guest'),
        
        result=result
    )


# History
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email=session["user"]).first()
        if not user:
            session.clear()
            return redirect('/login')

        reports = db.query(models.Reports).filter_by(user_id=user.id).all()

    # Fixed: Changed models.Report -> models.Reports to match your model class
    import re

    parsed_reports = []

    for r in reports:
        try:
            parsed_results = json.loads(r.result) if r.result else {}
        except Exception:
            parsed_results = {}

        resume = r.resume_text or ""

        # Clean common PDF issues
        resume = resume.replace(".c\nom", ".com")
        resume = resume.replace(".co\nm", ".com")
        resume = resume.replace("(Mobile)\n", "(Mobile) ")

        # Extract details
        email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume)
        phone = re.search(r'(\+?\d[\d\s()-]{8,}\d)', resume)
        linkedin = re.search(r'www\.linkedin\.com/[^\s]+', resume)

        address = ""
        if "Contact" in resume:
            contact_part = resume.split("Contact", 1)[1]

            if phone:
                address = contact_part.split(phone.group(0))[0].strip()
            else:
                address = contact_part[:80].strip()

        parsed_reports.append({
            "address": address,
            "phone": phone.group(0) if phone else "Not Available",
            "email": email.group(0) if email else "Not Available",
            "linkedin": linkedin.group(0) if linkedin else "Not Available",
            "resume": resume,
            "result": parsed_results
        })
    
    return render_template("history.html", reports=parsed_reports)


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)
    






