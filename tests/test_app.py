import io
import os
import unittest
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PYTHON_DOTENV_DISABLED"] = "true"
os.environ.pop("SARVAM_API_KEY", None)

from docx import Document
from werkzeug.security import check_password_hash

import app as application
import models
from db import Base, SessionLocal, engine, normalize_database_url


def make_text_pdf():
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = b"BT /F1 12 Tf 72 200 Td (Synthetic PDF resume) Tj ET"
    objects.append(
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
    )
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n".encode() + b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode()
    )
    return io.BytesIO(data)


class CareerCopilotAppTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        application.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = application.app.test_client()

    def create_and_login(self):
        response = self.client.post(
            "/signup",
            data={"name": "Test User", "email": "test@example.com", "password": "secret1"},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/login", data={"email": "test@example.com", "password": "secret1"}
        )
        self.assertEqual(response.status_code, 302)

    def test_mysql_urls_select_installed_pymysql_driver(self):
        for driver in ("mysql", "mysql+mysqldb", "mysql+pymysql"):
            with self.subTest(driver=driver):
                url = normalize_database_url(
                    f"{driver}://user:password@db.example.com:4000/career"
                )
                self.assertEqual(url.drivername, "mysql+pymysql")
                self.assertEqual(url.host, "db.example.com")
                self.assertEqual(url.database, "career")

    def test_public_and_protected_routes(self):
        for path in ("/", "/login", "/signup"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                if path in ("/login", "/signup"):
                    self.assertIn(b"data-password-toggle", response.data)

        for path in ("/dashboard", "/history"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, "/login")

    def test_signup_login_logout_and_legacy_password_preservation(self):
        response = self.client.post(
            "/signup",
            data={"name": "", "email": "bad@example.com", "password": "x"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"at least 6 characters", response.data)

        self.create_and_login()
        with SessionLocal() as db:
            user = db.query(models.User).filter_by(email="test@example.com").first()
            self.assertIsNotNone(user)
            self.assertNotEqual(user.password, "secret1")
            self.assertTrue(check_password_hash(user.password, "secret1"))
            self.assertLessEqual(len(user.password), models.User.__table__.c.password.type.length)

        duplicate = self.client.post(
            "/signup",
            data={"name": "Other", "email": "test@example.com", "password": "secret1"},
        )
        self.assertEqual(duplicate.status_code, 409)

        self.client.get("/logout")
        invalid = self.client.post(
            "/login", data={"email": "test@example.com", "password": "wrong"}
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b"Invalid credentials", invalid.data)

        with SessionLocal() as db:
            legacy_user = models.User(
                name="Legacy User", email="legacy@example.com", password="legacy1"
            )
            db.add(legacy_user)
            db.commit()

        legacy_login = self.client.post(
            "/login", data={"email": "legacy@example.com", "password": "legacy1"}
        )
        self.assertEqual(legacy_login.status_code, 302)
        with SessionLocal() as db:
            legacy_user = db.query(models.User).filter_by(email="legacy@example.com").first()
            self.assertEqual(legacy_user.password, "legacy1")

        self.assertEqual(self.client.get("/logout").status_code, 302)
        self.assertEqual(self.client.get("/history").status_code, 302)

    def test_text_and_docx_analysis_are_saved_to_history(self):
        self.create_and_login()
        result = {
            "skills": ["Python"],
            "missing_skills": ["SQL"],
            "roadmap": ["Practice SQL"],
            "interview_questions": ["Explain SQL joins"],
        }
        with patch.object(application.ai, "analyze_resume", return_value=result) as analyze:
            response = self.client.post(
                "/dashboard",
                data={"resume": "Test User\ntest@example.com\nPython", "role": "Backend Engineer"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Explain SQL joins", response.data)
            self.assertEqual(analyze.call_count, 1)

            document_stream = io.BytesIO()
            document = Document()
            document.add_paragraph("DOCX resume content")
            document.save(document_stream)
            document_stream.seek(0)
            response = self.client.post(
                "/dashboard",
                data={"role": "Backend Engineer", "file": (document_stream, "resume.docx")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(analyze.call_count, 2)
            self.assertEqual(analyze.call_args.args[0].strip(), "DOCX resume content")

            pdf_stream = make_text_pdf()
            response = self.client.post(
                "/dashboard",
                data={"role": "Backend Engineer", "file": (pdf_stream, "resume.pdf")},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(analyze.call_count, 3)
            self.assertEqual(analyze.call_args.args[0].strip(), "Synthetic PDF resume")

        history = self.client.get("/history")
        self.assertEqual(history.status_code, 200)
        self.assertIn(b"Explain SQL joins", history.data)
        self.assertEqual(history.data.count(b'<pre class="resume-text">'), 3)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.Reports).count(), 3)

    def test_upload_and_missing_input_errors_are_shown(self):
        self.create_and_login()
        response = self.client.post("/dashboard", data={"role": "Engineer"})
        self.assertIn(b"Provide resume text", response.data)

        with patch.object(
            application.ai,
            "analyze_resume",
            return_value={"skills": [], "missing_skills": [], "roadmap": [], "interview_questions": []},
        ) as analyze:
            response = self.client.post(
                "/dashboard",
                data={
                    "resume": "resume text",
                    "role": "Engineer",
                    "file": (io.BytesIO(b"bad"), "resume.txt"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(analyze.call_args.args[0], "resume text")

        with SessionLocal() as db:
            report_count = db.query(models.Reports).count()

        response = self.client.post(
            "/dashboard",
            data={"role": "Engineer", "file": (io.BytesIO(b"bad"), "resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertIn(b"PDF error", response.data)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.Reports).count(), report_count)

    def test_ai_failures_are_visible_but_not_saved(self):
        self.create_and_login()
        with patch.object(
            application.ai, "analyze_resume", return_value={"error": "AI unavailable"}
        ):
            response = self.client.post(
                "/dashboard", data={"resume": "resume text", "role": "Engineer"}
            )
        self.assertIn(b"AI unavailable", response.data)
        with SessionLocal() as db:
            self.assertEqual(db.query(models.Reports).count(), 0)

    def test_missing_ai_key_does_not_prevent_app_startup(self):
        response = application.ai.analyze_resume("resume text", "Engineer")
        self.assertEqual(response["error"], "SARVAM_API_KEY is not configured")
        self.assertEqual(self.client.get("/").status_code, 200)


if __name__ == "__main__":
    unittest.main()