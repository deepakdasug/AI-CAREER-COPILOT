# AI Career Copilot

AI Career Copilot is a Flask application that compares a resume with a target role and creates a career readout with relevant strengths, skill gaps, a learning roadmap, and interview questions. Users can save analyses and revisit them in their account history.

## Features

- Account signup, login, and logout
- Passwords are stored as Werkzeug password hashes, not readable text
- Resume input by pasted text or PDF/DOCX upload
- Sarvam AI analysis for a user-selected career goal
- Saved analysis history with resume and generated recommendations
- Responsive interface with resume input tabs, drag-and-drop upload, and history search

## Requirements

- Python 3.9 or newer (the deployment runtime file currently specifies Python 3.9.16)
- A Sarvam AI API key to run resume analysis
- A MySQL-compatible database such as TiDB for persistent deployment; SQLite is used by default for local development

## Local Setup (Windows PowerShell)

Open PowerShell in the directory containing `app.py` and run:

```powershell
py -3.9 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set the values for your own environment:

```dotenv
SARVAM_API_KEY=your_sarvam_api_key
DATABASE_URL=sqlite:///career_copilot.db
SECRET_KEY=replace_with_a_long_random_secret
```

For TiDB, replace the SQLite value with your TiDB connection string, for example:

```dotenv
DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<database>?ssl_verify_cert=true&ssl_verify_identity=true
```

Use the connection details and TLS options provided by your TiDB cluster. Do not commit `.env` or paste secret values into source control. The application creates missing SQLAlchemy tables when it starts. `create_all()` does not alter existing columns; if upgrading a TiDB database whose `users.password` column is still `VARCHAR(100)`, widen it to `VARCHAR(255)` before signing up new users:

```sql
ALTER TABLE users MODIFY COLUMN password VARCHAR(255);
```

Start the development server:

```powershell
python app.py
```

Open <http://127.0.0.1:5000>. To run through Flask's CLI instead:

```powershell
python -m flask --app app run
```

Resume analysis requires a valid `SARVAM_API_KEY`; the home, signup, and login pages can load without one. The development server is for local testing only.

## Using the App

1. Create an account with a name, email, and password of at least six characters.
2. Log in with the email and password used at signup.
3. On the workspace page, paste resume text or choose a PDF/DOCX file, then enter a target role.
4. Submit the analysis to view strengths, skills to build, a roadmap, and interview practice questions.
5. Open History to review saved analyses or search prior resume text and extracted contact details.

The upload handler recognizes filenames ending in lowercase `.pdf` or `.docx`. Scanned/image-only PDFs may not contain extractable text; use a text-based PDF or paste the resume text instead.

## Run Tests

The test suite uses an isolated in-memory SQLite database and mocks AI responses; it does not write to TiDB or make Sarvam requests.

```powershell
python -m unittest discover -s tests -v
```

## Deployment

The repository includes a `Procfile` configured for Gunicorn:

```text
web: gunicorn app:app
```

Configure `DATABASE_URL`, `SARVAM_API_KEY`, and a strong `SECRET_KEY` as deployment environment variables. Use a production WSGI server and a managed database for deployment; do not use Flask's development server in production.
