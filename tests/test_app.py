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

    def test_invalid_category_filter_ignored(self):
        response = self.client.get("/?category=InvalidCategory")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Black Backpack", response.data)
        self.assertIn(b"Blue Water Bottle", response.data)
        self.assertIn(b"Student ID Card", response.data)
        self.assertIn(b"Wireless Earbuds", response.data)

    def test_invalid_status_filter_ignored(self):
        response = self.client.get("/?status=InvalidStatus")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Black Backpack", response.data)
        self.assertIn(b"Blue Water Bottle", response.data)
        self.assertIn(b"Student ID Card", response.data)
        self.assertIn(b"Wireless Earbuds", response.data)

    def test_invalid_sort_defaults_to_newest(self):
        response = self.client.get("/?sort=invalid_sort")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertLess(data.index(b"Blue Water Bottle"), data.index(b"Wireless Earbuds"))

    def test_combined_invalid_filters_ignored(self):
        response = self.client.get("/?category=InvalidCategory&status=InvalidStatus&sort=invalid_sort")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Black Backpack", response.data)
        self.assertIn(b"Blue Water Bottle", response.data)
        self.assertIn(b"Student ID Card", response.data)
        self.assertIn(b"Wireless Earbuds", response.data)


if __name__ == "__main__":
    unittest.main()
