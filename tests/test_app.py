import io
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app, init_db, get_db, UPLOAD_DIR

class CampusFindTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        init_db()

    def test_upload_cleanup_on_database_failure(self):
        test_image = (io.BytesIO(b"fake image data"), "test_fail.png")
        data = {
            "title": "Failure Test Item",
            "category": "Electronics",
            "item_status": "Lost",
            "description": "A test description",
            "location": "Hostel Area",
            "item_date": "2026-10-25",
            "contact_name": "Test User",
            "contact_email": "test@example.com",
            "image": test_image,
        }

        with patch("app.get_db", side_effect=Exception("Simulated DB failure")):
            with self.assertRaises(Exception):
                self.client.post("/report", data=data, content_type="multipart/form-data")

        remaining = list(UPLOAD_DIR.glob("*test_fail*"))
        self.assertEqual(len(remaining), 0)

    def test_csrf_protection_blocks_invalid_post(self):
        app.config["ENABLE_CSRF_TESTS"] = True
        try:
            res = self.client.post("/report", data={"title": "Test"}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 400)
        finally:
            app.config["ENABLE_CSRF_TESTS"] = False

    def test_csrf_protection_allows_valid_token(self):
        app.config["ENABLE_CSRF_TESTS"] = True
        try:
            with self.client.session_transaction() as sess:
                sess["_csrf_token"] = "valid_test_token"
            data = {
                "csrf_token": "valid_test_token",
                "title": "Valid CSRF Item",
                "category": "Keys",
                "item_status": "Lost",
                "description": "Found near gate",
                "location": "Main Gate",
                "item_date": "2026-10-25",
                "contact_name": "Ravi",
                "contact_email": "ravi@example.com",
            }
            res = self.client.post("/report", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 302)
        finally:
            app.config["ENABLE_CSRF_TESTS"] = False

if __name__ == "__main__":
    unittest.main()