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

    def report_form_data(self, title, contact_email="student@example.edu"):
        return {
            "title": title,
            "category": "Other",
            "item_status": "Found",
            "description": "A test item.",
            "location": "Library",
            "item_date": "2026-10-30",
            "contact_name": "Test Student",
            "contact_email": contact_email,
        }

    def item_exists(self, title):
        with campus_app.get_db() as conn:
            return conn.execute("SELECT id FROM items WHERE title = ?", (title,)).fetchone() is not None

    def test_valid_contact_email_creates_listing(self):
        title = "Valid email submission"
        response = self.client.post("/report", data=self.report_form_data(title, "student+found@example.edu"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.item_exists(title))

    def test_malformed_contact_emails_are_rejected_without_creating_listings(self):
        invalid_emails = [
            "person@",
            "@example.com",
            "person@example",
            "person..name@example.com",
            "person@example..com",
            "person name@example.com",
        ]
        for index, email in enumerate(invalid_emails):
            with self.subTest(email=email):
                title = f"Invalid email submission {index}"
                response = self.client.post("/report", data=self.report_form_data(title, email))

                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Enter a valid contact email address.", response.data)
                self.assertFalse(self.item_exists(title))

    def test_contact_email_length_limit_is_preserved(self):
        max_length_email = f"{'a' * 64}@{'b' * 51}.com"
        self.assertEqual(len(max_length_email), 120)
        accepted_title = "Maximum length email submission"
        accepted_response = self.client.post(
            "/report", data=self.report_form_data(accepted_title, max_length_email)
        )
        self.assertEqual(accepted_response.status_code, 302)
        self.assertTrue(self.item_exists(accepted_title))

        email = f"{'a' * 64}@{'b' * 52}.com"
        self.assertEqual(len(email), 121)
        title = "Overlong email submission"

        response = self.client.post("/report", data=self.report_form_data(title, email))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Contact email must be 120 characters or fewer.", response.data)
        self.assertFalse(self.item_exists(title))


if __name__ == "__main__":
    unittest.main()
