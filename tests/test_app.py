import io
import os
import sqlite3
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

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


class TestReportItemImageCleanup(unittest.TestCase):
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

    @patch("app.sqlite3.connect")
    def test_cleanup_after_simulated_db_failure(self, mock_connect):
        mock_connect.side_effect = sqlite3.Error("simulated failure")

        upload_dir = campus_app.UPLOAD_FOLDER
        before = set(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else set()

        image_data = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        response = self.client.post(
            "/report",
            data={
                "title": "Lost Wallet",
                "description": "Black leather",
                "location": "Library",
                "contact": "555-0000",
                "image": (image_data, "wallet.png"),
            },
            content_type="multipart/form-data",
        )

        after = set(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else set()
        self.assertEqual(before, after)

    def test_successful_report_preserves_image(self):
        upload_dir = campus_app.UPLOAD_FOLDER
        before = set(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else set()

        image_data = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        response = self.client.post(
            "/report",
            data={
                "title": "Lost Wallet",
                "description": "Black leather",
                "location": "Library",
                "contact": "555-0000",
                "image": (image_data, "wallet.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)

        after = set(os.listdir(upload_dir)) if os.path.isdir(upload_dir) else set()
        new_files = after - before
        self.assertTrue(new_files)  # one new image remains

        # Cleanup created test image
        for f in new_files:
            try:
                os.remove(os.path.join(upload_dir, f))
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
