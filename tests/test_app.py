import unittest
import tempfile
import io
from unittest.mock import patch
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

    def test_report_item_with_image_success_preserves_file(self):
        data = {
            "title": "Camera",
            "category": "Electronics",
            "item_status": "Found",
            "description": "Black digital camera",
            "location": "Park",
            "item_date": "2026-10-25",
            "contact_name": "Finder",
            "contact_email": "finder@example.com",
            "image": (io.BytesIO(b"image content"), "camera.jpg")
        }
        res = self.client.post("/report", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT image_filename FROM items WHERE title = 'Camera'").fetchone()
            self.assertIsNotNone(item["image_filename"])
            image_path = campus_app.UPLOAD_DIR / item["image_filename"]
            self.assertTrue(image_path.exists())
            if image_path.exists():
                image_path.unlink()

    def test_report_item_cleans_up_upload_on_db_failure(self):
        campus_app.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        unrelated_file = campus_app.UPLOAD_DIR / "unrelated.jpg"
        unrelated_file.write_bytes(b"existing file")

        data = {
            "title": "Broken Upload",
            "category": "Electronics",
            "item_status": "Found",
            "description": "Test item with failing DB",
            "location": "Lab",
            "item_date": "2026-10-25",
            "contact_name": "Tester",
            "contact_email": "tester@example.com",
            "image": (io.BytesIO(b"transient upload content"), "fail.jpg")
        }

        with patch.object(campus_app, "get_db", side_effect=Exception("Simulated DB failure")):
            with self.assertRaises(Exception):
                self.client.post("/report", data=data, content_type="multipart/form-data")

        self.assertTrue(unrelated_file.exists())
        unrelated_file.unlink()

        for f in campus_app.UPLOAD_DIR.glob("*.jpg"):
            self.assertNotEqual(f.read_bytes(), b"transient upload content")


if __name__ == "__main__":
    unittest.main()
