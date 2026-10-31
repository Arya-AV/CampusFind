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

    def test_pagination_multiple_pages(self):
        # Insert test items to verify pagination boundaries
        with get_db() as conn:
            for i in range(10):
                conn.execute("""
                    INSERT INTO items (title, category, item_status, description, location, item_date,
                                       contact_name, contact_email)
                    VALUES (?, 'Electronics', 'Lost', 'Desc', 'Loc', '2026-10-25', 'Test', 't@e.com')
                """, (f"Paginated Item {i}",))

        # Page 1
        res1 = self.client.get("/?page=1")
        self.assertEqual(res1.status_code, 200)
        self.assertIn(b"Page 1 of", res1.data)
        self.assertIn(b"Next", res1.data)

        # Page 2
        res2 = self.client.get("/?page=2")
        self.assertEqual(res2.status_code, 200)
        self.assertIn(b"Previous", res2.data)

    def test_pagination_invalid_and_out_of_range(self):
        # Invalid page defaults to page 1
        res_invalid = self.client.get("/?page=-5")
        self.assertEqual(res_invalid.status_code, 200)
        self.assertIn(b"Page 1 of", res_invalid.data)

        # Non-integer page defaults to page 1
        res_text = self.client.get("/?page=abc")
        self.assertEqual(res_text.status_code, 200)
        self.assertIn(b"Page 1 of", res_text.data)

    def test_pagination_preserves_query_parameters(self):
        res = self.client.get("/?category=Electronics&status=Lost&sort=oldest&page=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"category=Electronics", res.data)
        self.assertIn(b"status=Lost", res.data)

if __name__ == "__main__":
    unittest.main()