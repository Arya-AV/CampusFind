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

    def create_found_item(self, title):
        with campus_app.get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO items (title, category, item_status, description, location, item_date,
                                       contact_name, contact_email, image_filename)
                   VALUES (?, 'Bags', 'Found', 'A test item', 'Library', '2026-10-01',
                           'Test User', 'test@example.edu', NULL)""",
                (title,),
            )
            return cursor.lastrowid

    def test_found_item_shows_accessible_return_confirmation(self):
        item_id = self.create_found_item("Confirmation dialog test")

        response = self.client.get(f"/item/{item_id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<dialog class="confirmation-dialog"', response.data)
        self.assertIn(b'aria-labelledby="return-confirmation-title"', response.data)
        self.assertIn(b'id="cancel-return"', response.data)
        self.assertIn(b'id="confirm-return"', response.data)
        app_js = Path(campus_app.BASE_DIR, "static", "js", "app.js").read_bytes()
        self.assertIn(b"returnForm.requestSubmit()", app_js)
        with campus_app.get_db() as conn:
            status = conn.execute("SELECT item_status FROM items WHERE id = ?", (item_id,)).fetchone()[0]
        self.assertEqual(status, "Found")

    def test_confirmed_return_submission_updates_item_status(self):
        item_id = self.create_found_item("Return submission test")

        response = self.client.post(f"/item/{item_id}/returned", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Item marked as returned", response.data)
        self.assertIn(b"This item has been reunited with its owner", response.data)
        self.assertNotIn(b"Mark as returned", response.data)

    def test_missing_item_returns_404(self):
        response = self.client.get("/item/99999")
        self.assertEqual(response.status_code, 404)

    def test_report_form_loads(self):
        response = self.client.get("/report")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Item details", response.data)


if __name__ == "__main__":
    unittest.main()
