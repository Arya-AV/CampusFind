import unittest
import tempfile
from datetime import date
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
        self.assertIn(b'name="csrf_token"', response.data)
        with self.client.session_transaction() as flask_session:
            token = flask_session[campus_app.CSRF_SESSION_KEY]
        self.assertIn(f'value="{token}"'.encode(), response.data)

    def csrf_token(self, path):
        self.client.get(path)
        with self.client.session_transaction() as flask_session:
            return flask_session[campus_app.CSRF_SESSION_KEY]

    def test_state_changing_posts_reject_missing_and_invalid_csrf_tokens(self):
        initial_count = self.item_count()
        for data in ({}, {"csrf_token": "invalid-token"}):
            with self.subTest(data=data):
                report_response = self.client.post("/report", data=data)
                returned_response = self.client.post("/item/2/returned", data=data)
                self.assertEqual(report_response.status_code, 400)
                self.assertEqual(returned_response.status_code, 400)

        self.assertEqual(self.item_count(), initial_count)
        with campus_app.get_db() as conn:
            status = conn.execute("SELECT item_status FROM items WHERE id = 2").fetchone()[0]
        self.assertEqual(status, "Found")

    def test_valid_csrf_token_allows_report_submission(self):
        token = self.csrf_token("/report")
        response = self.client.post("/report", data={
            "csrf_token": token,
            "title": "CSRF test item",
            "category": "Books",
            "item_status": "Lost",
            "description": "A valid test report.",
            "location": "Library",
            "item_date": date.today().isoformat(),
            "contact_name": "Test User",
            "contact_email": "test@example.edu",
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(response.headers["Location"]).status_code, 200)

    def test_valid_csrf_token_allows_marking_item_returned(self):
        detail_page = self.client.get("/item/2")
        with self.client.session_transaction() as flask_session:
            token = flask_session[campus_app.CSRF_SESSION_KEY]
        self.assertIn(f'value="{token}"'.encode(), detail_page.data)
        response = self.client.post(
            "/item/2/returned", data={"csrf_token": token}, follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This item has been reunited with its owner", response.data)

    def item_count(self):
        with campus_app.get_db() as conn:
            return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
