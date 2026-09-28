from flask import Flask, render_template, request, redirect, session
from db import engine, Base, SessionLocal
import PyPDF2
import docx
import json
import models  # Important for SQLAlchemy to know what tables to build!
import ai

app = Flask(__name__)
app.secret_key = 'secret123'

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
    return redirect('/login')


# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    db = SessionLocal()
    if request.method == 'POST':
        name=request.form.get("name")
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = db.query(models.User).filter_by(email=email).first()
        if existing_user:
            return 'User already exists'
        
        user = models.User(name=name,email=email, password=password)
        db.add(user)
        db.commit()
        db.close() # Close session when done

        return redirect('/login')
    return render_template('signup.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    db = SessionLocal()
    if request.method == 'POST':
        name=request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.query(models.User).filter_by(name=name,email=email, password=password).first()
        user_name = user.name if user else "Guest"
        if user:
            session['user'] = user.email
            session['user_name']=user_name
            
            db.close()
            return redirect('/dashboard')
        else:
            db.close()
            return 'Invalid credentials'
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

        if resume_text and user_goal:
            
            try:
                result = ai.analyze_resume(resume_text, user_goal)
                
                # Save to database
                db = SessionLocal()
                user = db.query(models.User).filter_by(email=session["user"]).first()
                
                report = models.Reports(
                    user_id = user.id,
                    resume_text = resume_text,
                    result = json.dumps(result) # Changed from r.results to match column name 'result' in models.py
                )

                db.add(report)
                db.commit()
                db.close()

            except Exception as e:
                result = {"error": f"AI error: {str(e)}"}
            print(resume_text)

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
        
    db = SessionLocal()
    user = db.query(models.User).filter_by(email=session["user"]).first()

    # Fixed: Changed models.Report -> models.Reports to match your model class
    import re

    reports = db.query(models.Reports).filter_by(user_id=user.id).all()

    parsed_reports = []

    for r in reports:
        try:
            parsed_results = json.loads(r.result) if r.result else {}
        except Exception:
            parsed_results = {}

        resume = r.resume_text

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
        db.close()
        return render_template("history.html", reports=parsed_reports)


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/login')


if __name__ == "__main__":
    app.run(debug=True)
    






