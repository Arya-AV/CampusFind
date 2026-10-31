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

    def test_successful_item_reporting_flow(self):
        report_data = {
            "title": "Silver Wristwatch",
            "category": "Accessories",
            "item_status": "Lost",
            "description": "Silver metallic wristwatch with black leather strap.",
            "location": "Sports Complex Court 1",
            "item_date": "2026-10-25",
            "contact_name": "Rohan Gupta",
            "contact_email": "rohan@example.com"
        }
        response = self.client.post("/report", data=report_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        self.assertIn(b"Your item has been reported successfully.", response.data)
        self.assertIn(b"Silver Wristwatch", response.data)
        self.assertIn(b"Sports Complex Court 1", response.data)
        self.assertIn(b"Rohan Gupta", response.data)
        self.assertIn(b"rohan@example.com", response.data)

        with campus_app.get_db() as conn:
            item = conn.execute("SELECT * FROM items WHERE title = 'Silver Wristwatch'").fetchone()
            self.assertIsNotNone(item)
            self.assertEqual(item["category"], "Accessories")
            self.assertEqual(item["item_status"], "Lost")
            self.assertEqual(item["description"], "Silver metallic wristwatch with black leather strap.")
            self.assertEqual(item["location"], "Sports Complex Court 1")
            self.assertEqual(item["contact_name"], "Rohan Gupta")
            self.assertEqual(item["contact_email"], "rohan@example.com")


if __name__ == "__main__":
    unittest.main()
