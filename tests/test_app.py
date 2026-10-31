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

        # Simulate database insertion raising an error
        with patch("app.get_db", side_effect=Exception("Simulated DB failure")):
            with self.assertRaises(Exception):
                self.client.post("/report", data=data, content_type="multipart/form-data")

        # Verify no orphan test image remains in the uploads directory
        remaining = list(UPLOAD_DIR.glob("*test_fail*"))
        self.assertEqual(len(remaining), 0)

if __name__ == "__main__":
    unittest.main()