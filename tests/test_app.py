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

    def test_invalid_category_parameter(self):
        # Testing unknown category parameter does not crash the server and returns 200 OK
        response = self.client.get("/?category=InvalidNonExistentCategory")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Explore listings", response.data)

    def test_invalid_status_parameter(self):
        # Testing unknown status parameter does not crash the server and returns 200 OK
        response = self.client.get("/?status=NotARealStatus")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Explore listings", response.data)

    def test_invalid_sort_parameter_falls_back_to_newest(self):
        # Testing unknown sort value does not cause 500 error and falls back gracefully
        response = self.client.get("/?sort=invalid_sort_value")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Explore listings", response.data)

    def test_multiple_invalid_parameters_combined(self):
        # Testing combinations of invalid parameters together
        response = self.client.get("/?category=FakeCategory&status=FakeStatus&sort=gibberish")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Explore listings", response.data)

if __name__ == "__main__":
    unittest.main()