import unittest
import unittest.mock
import tempfile
import time
import io
import sqlite3
from contextlib import contextmanager
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

    def test_unauthenticated_cannot_mark_item_returned(self):
        # Ensure session is clear
        self.client.get("/auth/logout")

        # Try to mark an item without logging in
        res = self.client.post("/item/1/returned")
        # Should redirect to login
        self.assertEqual(res.status_code, 302)
        self.assertIn("auth=login", res.headers["Location"])

        # Status in DB should not be changed
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT item_status FROM items WHERE id = 1").fetchone()
            self.assertNotEqual(item["item_status"], "Returned")

    def test_other_user_cannot_mark_other_peoples_lost_item(self):
        # User A creates a lost item
        self.register_and_login(name="User A", email="usera_lost@example.com")
        self.client.post("/report", data={
            "title": "User A Red Jacket",
            "category": "Clothing",
            "item_status": "Lost",
            "description": "Warm red winter jacket.",
            "location": "Locker Room",
            "item_date": "2026-10-28",
            "contact_name": "User A",
            "contact_email": "usera_lost@example.com",
        })
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = 'User A Red Jacket'").fetchone()
            item_id = item["id"]

        # User B logs in
        self.client.get("/auth/logout")
        self.register_and_login(name="User B Attacker", email="userb_lost@example.com")

        # 1. Frontend check: User B does NOT see the mark button
        detail_res = self.client.get(f"/item/{item_id}")
        self.assertNotIn(b"Mark as recovered / found", detail_res.data)
        self.assertNotIn(b"Mark as returned", detail_res.data)
        self.assertIn(b"Only the person who posted this listing can update or close it", detail_res.data)

        # 2. Backend check: User B sends POST /item/<item_id>/returned directly
        post_res = self.client.post(f"/item/{item_id}/returned")
        # Must be rejected with 403 Forbidden!
        self.assertEqual(post_res.status_code, 403)
        self.assertIn(b"Access Denied (403)", post_res.data)

        # 3. Database check: Item status is STILL Lost!
        with campus_app.get_db() as conn:
            check_item = conn.execute("SELECT item_status FROM items WHERE id = ?", (item_id,)).fetchone()
            self.assertEqual(check_item["item_status"], "Lost")

    def test_other_user_cannot_mark_other_peoples_found_item(self):
        # User A creates a found item
        self.register_and_login(name="User A Finder", email="usera_found@example.com")
        self.client.post("/report", data={
            "title": "User A Found Keychain",
            "category": "Keys",
            "item_status": "Found",
            "description": "Found near north gate.",
            "location": "North Gate",
            "item_date": "2026-10-28",
            "contact_name": "User A",
            "contact_email": "usera_found@example.com",
        })
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = 'User A Found Keychain'").fetchone()
            item_id = item["id"]

        # User B logs in
        self.client.get("/auth/logout")
        self.register_and_login(name="User B Meddler", email="userb_found@example.com")

        # 1. Frontend check: User B does NOT see the mark button
        detail_res = self.client.get(f"/item/{item_id}")
        self.assertNotIn(b"Mark as returned", detail_res.data)
        self.assertIn(b"Only the person who posted this listing can update or close it", detail_res.data)

        # 2. Backend check: User B sends POST /item/<item_id>/returned directly
        post_res = self.client.post(f"/item/{item_id}/returned")
        # Must be rejected with 403 Forbidden!
        self.assertEqual(post_res.status_code, 403)
        self.assertIn(b"Access Denied (403)", post_res.data)

        # 3. Database check: Item status is STILL Found!
        with campus_app.get_db() as conn:
            check_item = conn.execute("SELECT item_status FROM items WHERE id = ?", (item_id,)).fetchone()
            self.assertEqual(check_item["item_status"], "Found")

    def test_owner_can_mark_own_found_post_as_returned(self):
        # User A creates a found item
        self.register_and_login(name="Finder User", email="finder@example.com")
        self.client.post("/report", data={
            "title": "Finder Found Headphones",
            "category": "Electronics",
            "item_status": "Found",
            "description": "Found in cafeteria.",
            "location": "Cafeteria",
            "item_date": "2026-10-29",
            "contact_name": "Finder User",
            "contact_email": "finder@example.com",
        })
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = 'Finder Found Headphones'").fetchone()
            item_id = item["id"]

        # Owner views detail page: button IS present
        detail_res = self.client.get(f"/item/{item_id}")
        self.assertIn(b"Mark as returned", detail_res.data)

        # Owner marks returned
        rec_res = self.client.post(f"/item/{item_id}/returned", follow_redirects=True)
        self.assertEqual(rec_res.status_code, 200)
        self.assertIn(b"Item marked as returned", rec_res.data)

        with campus_app.get_db() as conn:
            check_item = conn.execute("SELECT item_status FROM items WHERE id = ?", (item_id,)).fetchone()
            self.assertEqual(check_item["item_status"], "Returned")

    def test_cannot_mark_unassigned_sample_post(self):
        self.register_and_login(name="Random User", email="random@example.com")
        # Item 1 is seeded sample item without user_id
        res = self.client.post("/item/1/returned")
        self.assertEqual(res.status_code, 403)

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

    def test_recently_viewed_not_tracked_for_unauthenticated_guests(self):
        with campus_app.get_db() as conn:
            count_before = conn.execute("SELECT COUNT(*) FROM recently_viewed").fetchone()[0]

        # Unauthenticated user visits item 1
        res_item = self.client.get("/item/1")
        self.assertEqual(res_item.status_code, 200)

        # Homepage should NOT have recently viewed section
        res_home = self.client.get("/")
        self.assertNotIn(b"Recently viewed items", res_home.data)

        # Database count should not increase
        with campus_app.get_db() as conn:
            count_after = conn.execute("SELECT COUNT(*) FROM recently_viewed").fetchone()[0]
            self.assertEqual(count_after, count_before)

    def test_recently_viewed_tracked_and_displayed_for_logged_in_user(self):
        self.register_and_login(name="Frank", email="frank@example.com")

        # Before viewing any items, recently viewed section is not displayed
        res_before = self.client.get("/")
        self.assertNotIn(b"Recently viewed items", res_before.data)

        # Frank views item 1 and item 2
        self.client.get("/item/1")
        self.client.get("/item/2")

        # Homepage now displays the recently viewed section
        res_after = self.client.get("/")
        self.assertIn(b"Recently viewed items", res_after.data)
        self.assertIn(b"Black Backpack", res_after.data)
        self.assertIn(b"Blue Water Bottle", res_after.data)

    def test_recently_viewed_ordering_and_deduplication(self):
        self.register_and_login(name="Grace", email="grace@example.com")

        # Grace views item 1, then item 2 with distinct timestamps
        self.client.get("/item/1")
        time.sleep(0.01)
        self.client.get("/item/2")

        with campus_app.get_db() as conn:
            user = conn.execute("SELECT id FROM users WHERE email = 'grace@example.com'").fetchone()
            recent = conn.execute("""
                SELECT item_id FROM recently_viewed
                WHERE user_id = ?
                ORDER BY viewed_at DESC
            """, (user["id"],)).fetchall()
            # Item 2 was viewed most recently
            self.assertEqual([r["item_id"] for r in recent], [2, 1])

        # Re-visiting item 1 bumps it to the top
        time.sleep(0.01)
        self.client.get("/item/1")
        with campus_app.get_db() as conn:
            recent = conn.execute("""
                SELECT item_id FROM recently_viewed
                WHERE user_id = ?
                ORDER BY viewed_at DESC
            """, (user["id"],)).fetchall()
            # Item 1 is now most recent, no duplicate rows
            self.assertEqual([r["item_id"] for r in recent], [1, 2])

    def test_recently_viewed_isolated_per_user(self):
        # User 1 views item 1
        self.register_and_login(name="User One", email="user1@example.com")
        self.client.get("/item/1")

        # Logout
        self.client.get("/auth/logout")

        # User 2 logs in
        self.register_and_login(name="User Two", email="user2@example.com")
        res_user2 = self.client.get("/")
        # User 2 should NOT see recently viewed section since User 2 has not viewed anything
        self.assertNotIn(b"Recently viewed items", res_user2.data)

    def test_clear_recently_viewed(self):
        self.register_and_login(name="Henry", email="henry@example.com")
        self.client.get("/item/1")

        # Confirm it appears
        res_before = self.client.get("/")
        self.assertIn(b"Recently viewed items", res_before.data)

        # Clear recently viewed
        clear_res = self.client.post("/recently-viewed/clear", follow_redirects=True)
        self.assertEqual(clear_res.status_code, 200)
        self.assertIn(b"Browsing history cleared", clear_res.data)
        self.assertNotIn(b"recently-viewed-section", clear_res.data)

    def test_uploaded_image_deleted_on_db_insert_failure(self):
        self.register_and_login(name="Image Test User", email="imagetest@example.com")

        # Dummy valid PNG bytes
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        upload_folder = Path(campus_app.app.config["UPLOAD_FOLDER"])
        before_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()

        # Simulate database failure specifically during INSERT INTO items
        original_get_db = campus_app.get_db

        @contextmanager
        def failing_get_db():
            with original_get_db() as conn:
                real_execute = conn.execute

                def mock_execute(query, *args, **kwargs):
                    if "INSERT INTO items" in query:
                        raise sqlite3.OperationalError("Simulated database failure during item creation")
                    return real_execute(query, *args, **kwargs)

                mock_conn = unittest.mock.MagicMock(wraps=conn)
                mock_conn.execute.side_effect = mock_execute
                yield mock_conn

        with unittest.mock.patch("app.get_db", side_effect=failing_get_db):
            with self.assertRaises(Exception):
                self.client.post("/report", data={
                    "title": "Failed DB Item",
                    "category": "Electronics",
                    "item_status": "Lost",
                    "description": "This item should fail to insert into DB.",
                    "location": "Library",
                    "item_date": "2026-10-30",
                    "contact_name": "Image Test User",
                    "contact_email": "imagetest@example.com",
                    "image": (io.BytesIO(image_content), "test_orphaned.png"),
                })

        # Verify that no new orphaned file remained in the uploads directory
        after_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()
        orphaned = after_files - before_files
        self.assertEqual(len(orphaned), 0, f"Orphaned files remained on disk: {orphaned}")


if __name__ == "__main__":
    unittest.main()
