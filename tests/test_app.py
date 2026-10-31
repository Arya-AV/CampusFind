import unittest
import tempfile
from pathlib import Path

import app as campus_app


class CampusFindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db = campus_app.DATABASE
        cls.temp_dir = tempfile.TemporaryDirectory()
        campus_app.DATABASE = Path(cls.temp_dir.name) / "test.db"
        campus_app.init_db()
        campus_app.app.config["TESTING"] = True
        cls.client = campus_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        campus_app.DATABASE = cls.original_db
        cls.temp_dir.cleanup()

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Explore listings", response.data)

    def test_search_finds_sample_item(self):
        response = self.client.get("/?q=Backpack")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Black Backpack", response.data)

    def test_filter_by_status(self):
        response = self.client.get("/?status=Found")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Blue Water Bottle", response.data)
        self.assertNotIn(b"Black Backpack", response.data)

    def test_item_detail_exists(self):
        response = self.client.get("/item/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Black Backpack", response.data)

    def test_missing_item_returns_404(self):
        response = self.client.get("/item/99999")
        self.assertEqual(response.status_code, 404)

    def test_report_form_loads(self):
        response = self.client.get("/report")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Item details", response.data)

    def test_report_item_rejects_malformed_email(self):
        malformed_emails = ["person@", "person", "@domain.com", "person@domain", "a" * 115 + "@example.com"]
        for email in malformed_emails:
            with self.subTest(email=email):
                response = self.client.post("/report", data={
                    "title": "Lost Wallet",
                    "category": "Accessories",
                    "item_status": "Lost",
                    "description": "Black leather wallet",
                    "location": "Cafeteria",
                    "item_date": "2026-10-25",
                    "contact_name": "Test User",
                    "contact_email": email
                }, follow_redirects=True)
                self.assertIn(b"Enter a valid contact email.", response.data)

    def test_report_item_accepts_valid_email(self):
        response = self.client.post("/report", data={
            "title": "Calculator",
            "category": "Electronics",
            "item_status": "Lost",
            "description": "Scientific calculator",
            "location": "Math Lab",
            "item_date": "2026-10-25",
            "contact_name": "Student A",
            "contact_email": "student@example.com"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your item has been reported successfully.", response.data)
        self.assertIn(b"Calculator", response.data)


if __name__ == "__main__":
    unittest.main()
