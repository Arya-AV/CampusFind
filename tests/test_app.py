import unittest
import tempfile
from pathlib import Path
from datetime import date, timedelta

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

    def test_report_item_rejects_future_date(self):
        future_date = (date.today() + timedelta(days=2)).isoformat()
        with campus_app.get_db() as conn:
            initial_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

        response = self.client.post("/report", data={
            "title": "Future Item",
            "category": "Books",
            "item_status": "Lost",
            "description": "Lost book from the future",
            "location": "Library",
            "item_date": future_date,
            "contact_name": "Time Traveler",
            "contact_email": "traveler@example.com"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The item date cannot be in the future.", response.data)

        with campus_app.get_db() as conn:
            final_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            future_item = conn.execute("SELECT * FROM items WHERE title = 'Future Item'").fetchone()

        self.assertEqual(initial_count, final_count)
        self.assertIsNone(future_item)

    def test_report_item_accepts_valid_current_and_past_date(self):
        valid_date = date.today().isoformat()
        response = self.client.post("/report", data={
            "title": "Today Notebook",
            "category": "Books",
            "item_status": "Found",
            "description": "Spiral notebook found today",
            "location": "Seminar Hall",
            "item_date": valid_date,
            "contact_name": "Student B",
            "contact_email": "student_b@example.com"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your item has been reported successfully.", response.data)
        self.assertIn(b"Today Notebook", response.data)


if __name__ == "__main__":
    unittest.main()
