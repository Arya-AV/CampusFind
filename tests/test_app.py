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

    def test_unknown_category_parameter(self):
        response = self.client.get("/?category=InvalidCategory")
        self.assertEqual(response.status_code, 200)
        # Invalid category is ignored, so all sample items remain visible
        self.assertIn(b"Black Backpack", response.data)
        self.assertIn(b"Blue Water Bottle", response.data)

    def test_unknown_status_parameter(self):
        response = self.client.get("/?status=UnknownStatus")
        self.assertEqual(response.status_code, 200)
        # Invalid status is ignored, so items with different statuses remain visible
        self.assertIn(b"Black Backpack", response.data)
        self.assertIn(b"Blue Water Bottle", response.data)

    def test_unknown_sort_falls_back_to_newest_first(self):
        response = self.client.get("/?sort=unknown_sort")
        self.assertEqual(response.status_code, 200)
        # Default newest-first ordering: 2026-10-24 (Blue Water Bottle) before 2026-10-20 (Wireless Earbuds)
        bottle_pos = response.data.find(b"Blue Water Bottle")
        earbuds_pos = response.data.find(b"Wireless Earbuds")
        self.assertNotEqual(bottle_pos, -1)
        self.assertNotEqual(earbuds_pos, -1)
        self.assertLess(bottle_pos, earbuds_pos)

    def test_invalid_parameters_combined_no_server_error(self):
        response = self.client.get("/?category=FakeCategory&status=FakeStatus&sort=invalid_sort")
        self.assertEqual(response.status_code, 200)

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


if __name__ == "__main__":
    unittest.main()
