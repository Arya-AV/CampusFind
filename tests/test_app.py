import unittest
import tempfile
from pathlib import Path

import app as campus_app
from userauth.models import verify_password


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

    def setUp(self):
        # Clear session before each test
        with self.client.session_transaction() as sess:
            sess.clear()

    def register_and_login(self, name="Test User", email="testuser@example.com", password="password123"):
        self.client.post("/auth/signup", data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        })

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Explore listings", response.data)
        # Auth modal is present
        self.assertIn(b"authModal", response.data)

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

    def test_report_requires_login(self):
        # Unauthenticated users are redirected to login
        response = self.client.get("/report")
        self.assertEqual(response.status_code, 302)
        self.assertIn("auth=login", response.headers["Location"])

    def test_report_form_loads_when_authenticated(self):
        self.register_and_login(name="Alice Reporter", email="alice@example.com")
        response = self.client.get("/report")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Item details", response.data)
        # Prefilled contact info
        self.assertIn(b"alice@example.com", response.data)
        self.assertIn(b"Alice Reporter", response.data)

    def test_signup_stores_encrypted_password(self):
        # Register user
        res = self.client.post("/auth/signup", data={
            "name": "Security Tester",
            "email": "secure@example.com",
            "password": "secret_plain_text_password",
            "confirm_password": "secret_plain_text_password",
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Inspect database record directly
        with campus_app.get_db() as conn:
            user = conn.execute(
                "SELECT password_hash FROM users WHERE email = ?",
                ("secure@example.com",)
            ).fetchone()
            self.assertIsNotNone(user)
            stored_hash = user["password_hash"]

            # Ensure plaintext password is NOT stored anywhere in the database
            self.assertNotEqual(stored_hash, "secret_plain_text_password")
            self.assertNotIn("secret_plain_text_password", stored_hash)

            # Ensure hash verifies correctly
            self.assertTrue(verify_password(stored_hash, "secret_plain_text_password"))
            self.assertFalse(verify_password(stored_hash, "wrong_password"))

    def test_signup_duplicate_email_rejected(self):
        self.client.post("/auth/signup", data={
            "name": "First User",
            "email": "unique@example.com",
            "password": "password123",
            "confirm_password": "password123",
        })
        res = self.client.post("/auth/signup", data={
            "name": "Second User",
            "email": "unique@example.com",
            "password": "password123",
            "confirm_password": "password123",
        }, follow_redirects=True)
        self.assertIn(b"already exists", res.data)

    def test_login_and_logout(self):
        # Register
        self.client.post("/auth/signup", data={
            "name": "Bob Login",
            "email": "bob@example.com",
            "password": "mypassword123",
            "confirm_password": "mypassword123",
        })
        self.client.get("/auth/logout")

        # Wrong password
        res_fail = self.client.post("/auth/login", data={
            "email": "bob@example.com",
            "password": "wrongpassword",
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", res_fail.data)

        # Correct password
        res_ok = self.client.post("/auth/login", data={
            "email": "bob@example.com",
            "password": "mypassword123",
        }, follow_redirects=True)
        self.assertIn(b"Welcome back, Bob Login", res_ok.data)

        # Check status endpoint
        res_status = self.client.get("/auth/status")
        self.assertEqual(res_status.get_json()["authenticated"], True)

        # Logout
        res_logout = self.client.get("/auth/logout", follow_redirects=True)
        self.assertIn(b"You have been signed out", res_logout.data)

        res_status_after = self.client.get("/auth/status")
        self.assertEqual(res_status_after.get_json()["authenticated"], False)

    def test_report_item_links_user(self):
        # Register user Charlie
        self.register_and_login(name="Charlie Owner", email="charlie@example.com")

        # Post a Lost item
        post_res = self.client.post("/report", data={
            "title": "Charlie Blue Umbrella",
            "category": "Accessories",
            "item_status": "Lost",
            "description": "Left behind in science lab.",
            "location": "Science Lab 3",
            "item_date": "2026-10-25",
            "contact_name": "Charlie Owner",
            "contact_email": "charlie@example.com",
        }, follow_redirects=True)
        self.assertEqual(post_res.status_code, 200)

        # Verify database record has user_id linked
        with campus_app.get_db() as conn:
            item = conn.execute(
                "SELECT * FROM items WHERE title = ?",
                ("Charlie Blue Umbrella",)
            ).fetchone()
            self.assertIsNotNone(item)
            self.assertIsNotNone(item["user_id"])

            user = conn.execute("SELECT id FROM users WHERE email = ?", ("charlie@example.com",)).fetchone()
            self.assertEqual(item["user_id"], user["id"])

        # Check detail page shows ownership
        detail_res = self.client.get(f"/item/{item['id']}")
        self.assertIn(b"You reported this", detail_res.data)
        # Owner can mark lost item as recovered/found
        self.assertIn(b"Mark as recovered / found", detail_res.data)

    def test_owner_can_mark_lost_item_recovered(self):
        self.register_and_login(name="Dana", email="dana@example.com")
        self.client.post("/report", data={
            "title": "Dana Scientific Calculator",
            "category": "Electronics",
            "item_status": "Lost",
            "description": "TI-84 calculator.",
            "location": "Math Building",
            "item_date": "2026-10-26",
            "contact_name": "Dana",
            "contact_email": "dana@example.com",
        })

        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = ?", ("Dana Scientific Calculator",)).fetchone()
            item_id = item["id"]

        # Mark recovered
        rec_res = self.client.post(f"/item/{item_id}/returned", follow_redirects=True)
        self.assertEqual(rec_res.status_code, 200)
        self.assertIn(b"marked as recovered", rec_res.data)

        with campus_app.get_db() as conn:
            updated = conn.execute("SELECT item_status FROM items WHERE id = ?", (item_id,)).fetchone()
            self.assertEqual(updated["item_status"], "Returned")

    def test_my_listings_filter(self):
        self.register_and_login(name="Eva", email="eva@example.com")
        self.client.post("/report", data={
            "title": "Eva Silver Watch",
            "category": "Accessories",
            "item_status": "Found",
            "description": "Found on sports field bench.",
            "location": "Sports Field",
            "item_date": "2026-10-27",
            "contact_name": "Eva",
            "contact_email": "eva@example.com",
        })

        # Test index with mine=1
        res = self.client.get("/?mine=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Eva Silver Watch", res.data)
        # Should not show other seeded items in my listings
        self.assertNotIn(b"Black Backpack", res.data)


if __name__ == "__main__":
    unittest.main()
