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

    def test_listing_sort_order_newest_and_default(self):
        res_default = self.client.get("/")
        self.assertEqual(res_default.status_code, 200)

        res_newest = self.client.get("/?sort=newest")
        self.assertEqual(res_newest.status_code, 200)

        pos_bottle = res_newest.data.find(b"Blue Water Bottle")
        pos_backpack = res_newest.data.find(b"Black Backpack")
        pos_id = res_newest.data.find(b"Student ID Card")
        pos_earbuds = res_newest.data.find(b"Wireless Earbuds")

        self.assertTrue(pos_bottle < pos_backpack < pos_id < pos_earbuds)

        pos_bottle_def = res_default.data.find(b"Blue Water Bottle")
        pos_backpack_def = res_default.data.find(b"Black Backpack")
        self.assertTrue(pos_bottle_def < pos_backpack_def)

    def test_listing_sort_order_oldest(self):
        res_oldest = self.client.get("/?sort=oldest")
        self.assertEqual(res_oldest.status_code, 200)

        pos_bottle = res_oldest.data.find(b"Blue Water Bottle")
        pos_backpack = res_oldest.data.find(b"Black Backpack")
        pos_id = res_oldest.data.find(b"Student ID Card")
        pos_earbuds = res_oldest.data.find(b"Wireless Earbuds")

        self.assertTrue(pos_earbuds < pos_id < pos_backpack < pos_bottle)

    def test_listing_sort_order_tie_breaking_equal_dates(self):
        with campus_app.get_db() as conn:
            conn.execute("""
                INSERT INTO items (title, category, item_status, description, location, item_date, contact_name, contact_email)
                VALUES ('First Equal Item', 'Books', 'Found', 'Test desc', 'Room 1', '2026-10-21', 'Person 1', 'p1@example.com')
            """)
            conn.execute("""
                INSERT INTO items (title, category, item_status, description, location, item_date, contact_name, contact_email)
                VALUES ('Second Equal Item', 'Books', 'Found', 'Test desc', 'Room 2', '2026-10-21', 'Person 2', 'p2@example.com')
            """)

        res = self.client.get("/?category=Books")
        self.assertEqual(res.status_code, 200)
        pos_first = res.data.find(b"First Equal Item")
        pos_second = res.data.find(b"Second Equal Item")
        self.assertTrue(pos_second < pos_first)


if __name__ == "__main__":
    unittest.main()
