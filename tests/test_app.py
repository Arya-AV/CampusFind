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

    def test_mark_found_item_as_returned_succeeds(self):
        response = self.client.post("/item/2/returned", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Item marked as returned", response.data)
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT item_status FROM items WHERE id = 2").fetchone()
            self.assertEqual(item["item_status"], "Returned")

    def test_mark_lost_item_as_returned_rejected(self):
        response = self.client.post("/item/1/returned", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Only found items can be marked as returned.", response.data)
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT item_status FROM items WHERE id = 1").fetchone()
            self.assertEqual(item["item_status"], "Lost")

    def test_mark_nonexistent_item_as_returned_returns_404(self):
        response = self.client.post("/item/99999/returned")
        self.assertEqual(response.status_code, 404)

    def test_mark_already_returned_item_handled_safely(self):
        self.client.post("/item/3/returned")
        response = self.client.post("/item/3/returned", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT item_status FROM items WHERE id = 3").fetchone()
            self.assertEqual(item["item_status"], "Returned")


if __name__ == "__main__":
    unittest.main()
