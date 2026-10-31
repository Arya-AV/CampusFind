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


class SortingRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db = campus_app.DATABASE
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "sorting_test.db"
        campus_app.DATABASE = cls.db_path
        campus_app.app.config["TESTING"] = True
        cls.client = campus_app.app.test_client()

        with campus_app.get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    item_status TEXT NOT NULL CHECK(item_status IN ('Lost', 'Found', 'Returned')),
                    description TEXT NOT NULL,
                    location TEXT NOT NULL,
                    item_date TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    contact_email TEXT NOT NULL,
                    image_filename TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            test_items = [
                ("Old Item", "Books", "Lost", "Oldest item", "Library", "2026-10-10", "User A", "a@example.com", None),
                ("Middle Item Earlier ID", "Electronics", "Found", "First item on same date", "Lab 1", "2026-10-20", "User B", "b@example.com", None),
                ("Middle Item Later ID", "Accessories", "Found", "Second item on same date", "Lab 2", "2026-10-20", "User C", "c@example.com", None),
                ("New Item", "Bags", "Lost", "Newest item", "Hall", "2026-10-30", "User D", "d@example.com", None),
            ]
            conn.executemany("""
                INSERT INTO items (title, category, item_status, description, location, item_date,
                                   contact_name, contact_email, image_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, test_items)

    @classmethod
    def tearDownClass(cls):
        campus_app.DATABASE = cls.original_db
        cls.temp_dir.cleanup()

    def test_default_sort_when_no_parameter_supplied(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        pos_new = response.data.find(b"New Item")
        pos_mid_later = response.data.find(b"Middle Item Later ID")
        pos_mid_earlier = response.data.find(b"Middle Item Earlier ID")
        pos_old = response.data.find(b"Old Item")

        self.assertNotEqual(pos_new, -1)
        self.assertNotEqual(pos_mid_later, -1)
        self.assertNotEqual(pos_mid_earlier, -1)
        self.assertNotEqual(pos_old, -1)

        self.assertLess(pos_new, pos_mid_later)
        self.assertLess(pos_mid_later, pos_mid_earlier)
        self.assertLess(pos_mid_earlier, pos_old)

    def test_newest_first_sorting(self):
        response = self.client.get("/?sort=newest")
        self.assertEqual(response.status_code, 200)
        pos_new = response.data.find(b"New Item")
        pos_mid_later = response.data.find(b"Middle Item Later ID")
        pos_mid_earlier = response.data.find(b"Middle Item Earlier ID")
        pos_old = response.data.find(b"Old Item")

        self.assertNotEqual(pos_new, -1)
        self.assertNotEqual(pos_mid_later, -1)
        self.assertNotEqual(pos_mid_earlier, -1)
        self.assertNotEqual(pos_old, -1)

        self.assertLess(pos_new, pos_mid_later)
        self.assertLess(pos_mid_later, pos_mid_earlier)
        self.assertLess(pos_mid_earlier, pos_old)

    def test_oldest_first_sorting(self):
        response = self.client.get("/?sort=oldest")
        self.assertEqual(response.status_code, 200)
        pos_old = response.data.find(b"Old Item")
        pos_mid_later = response.data.find(b"Middle Item Later ID")
        pos_mid_earlier = response.data.find(b"Middle Item Earlier ID")
        pos_new = response.data.find(b"New Item")

        self.assertNotEqual(pos_old, -1)
        self.assertNotEqual(pos_mid_later, -1)
        self.assertNotEqual(pos_mid_earlier, -1)
        self.assertNotEqual(pos_new, -1)

        self.assertLess(pos_old, pos_mid_later)
        self.assertLess(pos_mid_later, pos_mid_earlier)
        self.assertLess(pos_mid_earlier, pos_new)

    def test_equal_dates_tie_breaking_behavior(self):
        # Both Middle Item Earlier ID (id 2) and Middle Item Later ID (id 3) share date 2026-10-20.
        # Intended tie-breaker is id DESC, so Middle Item Later ID must precede Middle Item Earlier ID.
        for sort_param in ["", "?sort=newest", "?sort=oldest"]:
            with self.subTest(sort=sort_param):
                response = self.client.get(f"/{sort_param}")
                self.assertEqual(response.status_code, 200)
                pos_later = response.data.find(b"Middle Item Later ID")
                pos_earlier = response.data.find(b"Middle Item Earlier ID")
                self.assertNotEqual(pos_later, -1)
                self.assertNotEqual(pos_earlier, -1)
                self.assertLess(pos_later, pos_earlier)


if __name__ == "__main__":
    unittest.main()
