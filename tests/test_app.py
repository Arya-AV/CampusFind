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
        def test_successful_item_report_is_saved_and_shown(self):
        report = {
            "title": "Lost Calculator",
            "category": "Electronics",
            "item_status": "Lost",
            "description": "A scientific calculator with a blue cover.",
            "location": "Science Building",
            "item_date": "2026-10-25",
            "contact_name": "Sam Student",
            "contact_email": "sam@example.com",
        }

        response = self.client.post("/report", data=report)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/item/"))

        item_id = int(response.headers["Location"].rsplit("/", 1)[1])
        detail_response = self.client.get(f"/item/{item_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn(b"Lost Calculator", detail_response.data)

        with campus_app.get_db() as conn:
            item = conn.execute(
                "SELECT title, item_status, contact_email FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()

        self.assertEqual(item["title"], "Lost Calculator")
        self.assertEqual(item["item_status"], "Lost")
        self.assertEqual(item["contact_email"], "sam@example.com")

if __name__ == "__main__":
    unittest.main()
