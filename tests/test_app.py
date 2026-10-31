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

    def test_item_detail_has_print_button(self):
        response = self.client.get("/item/1")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        # Hidden until app.js confirms printing is available and shows it.
        self.assertRegex(page, r'<button[^>]*type="button"[^>]*data-print-page[^>]*\bhidden\b[^>]*>')
        self.assertIn("Print details", page)

    def test_print_button_only_on_item_detail(self):
        response = self.client.get("/")
        self.assertNotIn(b"data-print-page", response.data)

    def test_item_photo_is_marked_for_print(self):
        with campus_app.get_db() as conn:
            item_id = conn.execute(
                """
                INSERT INTO items (title, category, item_status, description, location,
                                   item_date, contact_name, contact_email, image_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("Red Notebook", "Books", "Found", "A red spiral notebook.", "Room 101",
                 "2026-10-21", "Campus Desk", "helpdesk@example.com", "notebook.png"),
            ).lastrowid
        with_photo = self.client.get(f"/item/{item_id}")
        self.assertIn(b'class="detail-visual has-image"', with_photo.data)
        without_photo = self.client.get("/item/1")
        self.assertNotIn(b"has-image", without_photo.data)

    def test_stylesheet_includes_print_layout(self):
        response = self.client.get("/static/css/styles.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"@media print", response.data)
        response.close()


if __name__ == "__main__":
    unittest.main()
