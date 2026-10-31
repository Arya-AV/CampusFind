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

    def add_pagination_items(self, prefix, count=12):
        with campus_app.get_db() as conn:
            conn.executemany(
                """INSERT INTO items (title, category, item_status, description, location, item_date,
                                       contact_name, contact_email, image_filename)
                   VALUES (?, 'Bags', 'Lost', 'Pagination test item', 'Library', ?, 'Test',
                           'test@example.edu', NULL)""",
                [
                    (f"{prefix} item {index:02d}", f"2026-10-{index + 1:02d}")
                    for index in range(count)
                ],
            )

    def test_listing_pagination_splits_results_into_pages(self):
        self.add_pagination_items("PageSplit")

        first_page = self.client.get("/?q=PageSplit&page=1")
        self.assertEqual(first_page.status_code, 200)
        self.assertIn(b"Page 1 of 2", first_page.data)
        self.assertIn(b"PageSplit item 11", first_page.data)
        self.assertNotIn(b"PageSplit item 02", first_page.data)

        second_page = self.client.get("/?q=PageSplit&page=2")
        self.assertEqual(second_page.status_code, 200)
        self.assertIn(b"Page 2 of 2", second_page.data)
        self.assertIn(b"PageSplit item 02", second_page.data)
        self.assertIn(b"PageSplit item 00", second_page.data)
        self.assertNotIn(b"PageSplit item 11", second_page.data)

    def test_pagination_links_preserve_search_filters_and_sort(self):
        self.add_pagination_items("PageFilter")
        query = "q=PageFilter&category=Bags&status=Lost&sort=oldest"

        first_page = self.client.get(f"/?{query}")
        self.assertEqual(first_page.status_code, 200)
        self.assertIn(
            b'href="/?q=PageFilter&amp;category=Bags&amp;status=Lost&amp;sort=oldest&amp;page=2"',
            first_page.data,
        )

        second_page = self.client.get(f"/?{query}&page=2")
        self.assertEqual(second_page.status_code, 200)
        self.assertIn(b"PageFilter item 09", second_page.data)
        self.assertIn(b"PageFilter item 11", second_page.data)
        self.assertNotIn(b"PageFilter item 08", second_page.data)

    def test_invalid_and_out_of_range_pages_are_clamped(self):
        self.add_pagination_items("PageClamp")

        for page_value in ("not-a-number", "-5", "0"):
            with self.subTest(page=page_value):
                response = self.client.get(f"/?q=PageClamp&page={page_value}")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Page 1 of 2", response.data)
                self.assertIn(b"PageClamp item 11", response.data)

        response = self.client.get("/?q=PageClamp&page=999")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Page 2 of 2", response.data)
        self.assertIn(b"PageClamp item 00", response.data)


if __name__ == "__main__":
    unittest.main()
