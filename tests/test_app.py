import unittest
import unittest.mock
import tempfile
import time
import io
import os
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
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
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

    def test_secret_key_loaded_from_environment(self):
        # When SECRET_KEY is set in environment, it should be loaded
        with unittest.mock.patch.dict(os.environ, {"SECRET_KEY": "my-custom-production-secret-1234"}):
            key = campus_app.get_secret_key()
            self.assertEqual(key, "my-custom-production-secret-1234")

    def test_missing_secret_key_handled_safely_with_ephemeral_key(self):
        # When neither SECRET_KEY nor FLASK_SECRET_KEY is set
        env_without_secret = {k: v for k, v in os.environ.items() if k not in ("SECRET_KEY", "FLASK_SECRET_KEY")}
        with unittest.mock.patch.dict(os.environ, env_without_secret, clear=True):
            key1 = campus_app.get_secret_key()
            key2 = campus_app.get_secret_key()
            # Generates strong random keys
            self.assertIsInstance(key1, str)
            self.assertGreaterEqual(len(key1), 32)
            # Ephemeral keys are unique and not hardcoded
            self.assertNotEqual(key1, "change-this-development-key")
            self.assertNotEqual(key1, key2)

    def test_debug_mode_disabled_by_default(self):
        # Default with no FLASK_DEBUG set should be False
        env_without_debug = {k: v for k, v in os.environ.items() if k != "FLASK_DEBUG"}
        with unittest.mock.patch.dict(os.environ, env_without_debug, clear=True):
            self.assertFalse(campus_app.get_debug_mode())

    def test_debug_mode_enabled_only_with_explicit_setting(self):
        # True only for explicit development settings
        for truthy in ("1", "true", "True", "TRUE", "yes", "on", "development"):
            with unittest.mock.patch.dict(os.environ, {"FLASK_DEBUG": truthy}):
                self.assertTrue(campus_app.get_debug_mode(), f"Expected True for {truthy}")

        # False for any other or empty settings
        for falsy in ("0", "false", "False", "no", "off", "production", "", "random"):
            with unittest.mock.patch.dict(os.environ, {"FLASK_DEBUG": falsy}):
                self.assertFalse(campus_app.get_debug_mode(), f"Expected False for {falsy}")

    def test_source_code_has_no_hardcoded_development_secret(self):
        # Ensure 'change-this-development-key' is never hardcoded in app.py
        app_source_path = campus_app.BASE_DIR / "app.py"
        with open(app_source_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("change-this-development-key", content)

    def test_gitignore_protects_env_files(self):
        # Ensure .env is in .gitignore and .env.example exists
        gitignore_path = campus_app.BASE_DIR / ".gitignore"
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()]
        self.assertIn(".env", lines)
        self.assertTrue((campus_app.BASE_DIR / ".env.example").is_file())



    # --- Tests for Image Content Validation ---

    def _create_sample_image_bytes(self, fmt="PNG"):
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(buf, format=fmt)
        return buf.getvalue()

    def test_accept_valid_images_all_supported_formats(self):
        """Verify that genuine images in all supported formats (PNG, JPG, JPEG, GIF, WEBP) are accepted and saved."""
        self.register_and_login(name="Valid Image User", email="validimg@example.com")
        upload_folder = Path(campus_app.app.config["UPLOAD_FOLDER"])

        format_cases = [
            ("PNG", "item_test.png"),
            ("JPEG", "item_test.jpg"),
            ("JPEG", "item_test.jpeg"),
            ("GIF", "item_test.gif"),
            ("WEBP", "item_test.webp"),
        ]

        for fmt, filename in format_cases:
            img_bytes = self._create_sample_image_bytes(fmt)
            before_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()

            res = self.client.post("/report", data={
                "title": f"Valid {fmt} Item",
                "category": "Electronics",
                "item_status": "Lost",
                "description": f"Valid {fmt} image test description.",
                "location": "Lab 1",
                "item_date": "2026-10-30",
                "contact_name": "Valid Image User",
                "contact_email": "validimg@example.com",
                "image": (io.BytesIO(img_bytes), filename),
            }, follow_redirects=False)

            # Successfully redirected to item detail page
            self.assertEqual(res.status_code, 302, f"Failed for format {fmt} with filename {filename}")
            item_detail_url = res.headers["Location"]

            # Confirm file was stored on disk
            after_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()
            new_files = after_files - before_files
            self.assertEqual(len(new_files), 1, f"Image was not saved to disk for {filename}")

            # Verify image file is shown on item detail page
            detail_res = self.client.get(item_detail_url)
            self.assertEqual(detail_res.status_code, 200)
            saved_filename = list(new_files)[0].name
            self.assertIn(saved_filename.encode("utf-8"), detail_res.data)

            # Cleanup test file
            for f in new_files:
                try:
                    f.unlink()
                except OSError:
                    pass

    def test_reject_text_file_renamed_to_allowed_extension(self):
        """Verify that a text file renamed with an allowed extension (.png) is rejected and not saved to disk."""
        self.register_and_login(name="Text File User", email="textfile@example.com")
        upload_folder = Path(campus_app.app.config["UPLOAD_FOLDER"])
        before_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()

        with campus_app.get_db() as conn:
            item_count_before = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

        fake_text_image = b"Hello, this is merely a text file renamed to photo.png."

        res = self.client.post("/report", data={
            "title": "Fake Image Item",
            "category": "Electronics",
            "item_status": "Lost",
            "description": "Item with disguised text file as image.",
            "location": "Library",
            "item_date": "2026-10-30",
            "contact_name": "Text File User",
            "contact_email": "textfile@example.com",
            "image": (io.BytesIO(fake_text_image), "photo.png"),
        }, follow_redirects=True)

        # Must not redirect to detail; should render form with flash error
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"not a valid image", res.data.lower())

        # Ensure rejected file is NOT saved in uploads directory
        after_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()
        orphaned = after_files - before_files
        self.assertEqual(len(orphaned), 0, f"Rejected file was saved to disk: {orphaned}")

        # Ensure no listing was created in the database
        with campus_app.get_db() as conn:
            item_count_after = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            self.assertEqual(item_count_after, item_count_before)

    def test_reject_disguised_non_image_files(self):
        """Verify that HTML, corrupted headers, empty files, and binary archives are rejected."""
        self.register_and_login(name="Disguise Tester", email="disguise@example.com")
        upload_folder = Path(campus_app.app.config["UPLOAD_FOLDER"])

        disguised_payloads = [
            (b"<!DOCTYPE html><html><script>alert(\'xss\')</script></html>", "script.jpg"),
            (b"GIF89a NOT A REAL GIF DATA STREAM", "corrupted.gif"),
            (b"", "empty.webp"),
            (b"PK\x03\x04\x14\x00\x00\x00\x08\x00ArchiveFakeContent", "archive.png"),
            (b"MZ\x90\x00\x03\x00\x00\x00\x04\x00ExecutableContent", "malware.jpeg"),
        ]

        for payload, filename in disguised_payloads:
            before_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()

            res = self.client.post("/report", data={
                "title": "Disguised Item",
                "category": "Books",
                "item_status": "Found",
                "description": "Testing rejection of disguised non-image file.",
                "location": "Hallway",
                "item_date": "2026-10-30",
                "contact_name": "Disguise Tester",
                "contact_email": "disguise@example.com",
                "image": (io.BytesIO(payload), filename),
            }, follow_redirects=True)

            self.assertEqual(res.status_code, 200, f"Expected 200 re-render for {filename}")
            self.assertIn(b"not a valid image", res.data.lower())

            after_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()
            self.assertEqual(len(after_files - before_files), 0, f"Rejected file was saved to disk for {filename}")

    def test_reject_mismatched_image_format_and_extension(self):
        """Verify that a valid JPEG renamed to .png (or valid PNG renamed to .gif) is rejected."""
        self.register_and_login(name="Mismatch User", email="mismatch@example.com")
        upload_folder = Path(campus_app.app.config["UPLOAD_FOLDER"])
        before_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()

        # Real JPEG content disguised as .png
        real_jpeg_bytes = self._create_sample_image_bytes("JPEG")

        res = self.client.post("/report", data={
            "title": "Mismatched Ext Item",
            "category": "Accessories",
            "item_status": "Lost",
            "description": "JPEG disguised with PNG extension.",
            "location": "Cafeteria",
            "item_date": "2026-10-30",
            "contact_name": "Mismatch User",
            "contact_email": "mismatch@example.com",
            "image": (io.BytesIO(real_jpeg_bytes), "disguised_photo.png"),
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b"not a valid image", res.data.lower())

        after_files = set(upload_folder.glob("*")) if upload_folder.exists() else set()
        self.assertEqual(len(after_files - before_files), 0)

    def test_preserve_existing_5mb_size_limit_and_error_handling(self):
        """Verify that files exceeding MAX_CONTENT_LENGTH (5 MB) are rejected with standard 413 handling."""
        self.register_and_login(name="Oversize User", email="oversize@example.com")

        # 5 MB + 1 KB payload
        oversized_data = b"0" * (5 * 1024 * 1024 + 1024)

        res = self.client.post("/report", data={
            "title": "Huge File Item",
            "category": "Bags",
            "item_status": "Lost",
            "description": "Oversized upload test.",
            "location": "Sports Complex",
            "item_date": "2026-10-30",
            "contact_name": "Oversize User",
            "contact_email": "oversize@example.com",
            "image": (io.BytesIO(oversized_data), "too_large.png"),
        }, follow_redirects=True)

        self.assertIn(b"Maximum upload size is 5 MB", res.data)

    def test_allowed_file_and_validate_image_helpers(self):
        """Unit test allowed_file and validate_image directly for edge cases."""
        # Extension checks
        self.assertTrue(campus_app.allowed_file("valid.png"))
        self.assertTrue(campus_app.allowed_file("PHOTO.JPG"))
        self.assertTrue(campus_app.allowed_file("sample.webp"))
        self.assertFalse(campus_app.allowed_file("document.pdf"))
        self.assertFalse(campus_app.allowed_file("script.py"))
        self.assertFalse(campus_app.allowed_file("no_extension"))

        # Valid image stream
        valid_png = io.BytesIO(self._create_sample_image_bytes("PNG"))
        self.assertTrue(campus_app.validate_image(valid_png, "png"))
        self.assertTrue(campus_app.allowed_file("valid.png", valid_png))

        # Stream rewind verification: stream can be read after validate_image
        self.assertEqual(valid_png.tell(), 0)

        # Invalid stream
        fake_stream = io.BytesIO(b"not an image")
        self.assertFalse(campus_app.validate_image(fake_stream, "png"))
        self.assertFalse(campus_app.allowed_file("fake.png", fake_stream))
        self.assertFalse(campus_app.validate_image(None))



    # --- Tests for Return Confirmation Prompt ---

    def test_confirmation_modal_rendered_for_owner(self):
        """Verify that eligible items render the confirmation modal with title, description, and action buttons."""
        self.register_and_login(name="Confirm Owner", email="confirm_owner@example.com")
        self.client.post("/report", data={
            "title": "Modal Test Backpack",
            "category": "Bags",
            "item_status": "Found",
            "description": "Found a backpack for testing confirmation modal.",
            "location": "Cafeteria",
            "item_date": "2026-10-31",
            "contact_name": "Confirm Owner",
            "contact_email": "confirm_owner@example.com",
        })

        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = 'Modal Test Backpack'").fetchone()
            item_id = item["id"]

        res = self.client.get(f"/item/{item_id}")
        self.assertEqual(res.status_code, 200)

        # Confirm form and modal elements are present
        self.assertIn(b"markReturnedForm", res.data)
        self.assertIn(b"confirmReturnedModal", res.data)
        self.assertIn(b"confirmModalTitle", res.data)
        self.assertIn(b"cancelConfirmBtn", res.data)
        self.assertIn(b"acceptConfirmBtn", res.data)
        self.assertIn(b"closeConfirmModal", res.data)

        # Confirm buttons have appropriate labels
        self.assertIn(b"Mark item as returned?", res.data)
        self.assertIn(b"Cancel", res.data)
        self.assertIn(b"Yes, mark as returned", res.data)

    def test_confirmation_modal_not_rendered_for_non_owner(self):
        """Verify that non-owners cannot see the mark returned form or confirmation modal."""
        # Owner creates item
        self.register_and_login(name="Real Owner", email="real_owner@example.com")
        self.client.post("/report", data={
            "title": "Private Item",
            "category": "Keys",
            "item_status": "Lost",
            "description": "Owner item description",
            "location": "Gym",
            "item_date": "2026-10-31",
            "contact_name": "Real Owner",
            "contact_email": "real_owner@example.com",
        })

        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = 'Private Item'").fetchone()
            item_id = item["id"]

        # Log out and log in as another user
        self.client.get("/auth/logout")
        self.register_and_login(name="Other Viewer", email="other_viewer@example.com")

        res = self.client.get(f"/item/{item_id}")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(b"confirmReturnedModal", res.data)
        self.assertNotIn(b"markReturnedForm", res.data)
        self.assertNotIn(b"acceptConfirmBtn", res.data)

    def test_confirmation_modal_not_rendered_for_already_returned_item(self):
        """Verify that already returned items show the resolved banner and no confirmation modal."""
        self.register_and_login(name="Returned Owner", email="ret_owner@example.com")
        self.client.post("/report", data={
            "title": "Already Resolved Item",
            "category": "Books",
            "item_status": "Found",
            "description": "Already resolved book",
            "location": "Library",
            "item_date": "2026-10-31",
            "contact_name": "Returned Owner",
            "contact_email": "ret_owner@example.com",
        })

        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = 'Already Resolved Item'").fetchone()
            item_id = item["id"]

        # Mark as returned
        self.client.post(f"/item/{item_id}/returned", follow_redirects=True)

        res = self.client.get(f"/item/{item_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"returned-banner", res.data)
        self.assertNotIn(b"confirmReturnedModal", res.data)
        self.assertNotIn(b"markReturnedForm", res.data)


if __name__ == "__main__":
    unittest.main()
