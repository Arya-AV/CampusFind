import re
import unittest
import tempfile
from pathlib import Path

import app as campus_app


def add_item(title, image_filename=None):
    """Insert a Found item directly into the test database and return its ID."""
    with campus_app.get_db() as conn:
        return conn.execute(
            """
            INSERT INTO items (title, category, item_status, description, location,
                               item_date, contact_name, contact_email, image_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (title, "Other", "Found", "Test item.", "Test Hall", "2026-10-21",
             "Campus Desk", "helpdesk@example.com", image_filename),
        ).lastrowid


def recent_card_ids(response):
    """Return the item IDs of the Recently viewed cards in a response, in order."""
    return [int(item_id) for item_id in re.findall(r'data-item-id="(\d+)"', response.get_data(as_text=True))]


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

    def test_item_detail_marks_item_to_record(self):
        response = self.client.get("/item/1")
        self.assertIn(b'data-record-view="1"', response.data)

    def test_home_page_has_recently_viewed_section(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('data-recently-viewed-limit="6"', page)
        self.assertRegex(page, r'<section[^>]*data-recently-viewed[^>]*data-url="/recently-viewed"[^>]*hidden')
        self.assertIn("Recently viewed", page)
        self.assertIn("data-recently-viewed-empty", page)

    def test_recently_viewed_keeps_order_and_removes_duplicates(self):
        response = self.client.get("/recently-viewed?ids=3,1,2,1,3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recent_card_ids(response), [3, 1, 2])

    def test_recently_viewed_skips_missing_items(self):
        response = self.client.get("/recently-viewed?ids=99999,1,88888")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recent_card_ids(response), [1])

        response = self.client.get("/recently-viewed?ids=99999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recent_card_ids(response), [])

    def test_recently_viewed_ignores_invalid_ids(self):
        response = self.client.get(
            "/recently-viewed",
            query_string={"ids": "abc,-1,0,,1.5,²,99999999999999999999999, 2 "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recent_card_ids(response), [2])

        response = self.client.get("/recently-viewed")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recent_card_ids(response), [])

    def test_recently_viewed_is_limited(self):
        limit = campus_app.RECENTLY_VIEWED_LIMIT
        ids = [add_item(f"Limit test {n}") for n in range(limit + 2)]
        response = self.client.get("/recently-viewed", query_string={"ids": ",".join(map(str, ids))})
        self.assertEqual(recent_card_ids(response), ids[:limit])

    def test_recently_viewed_cards_show_title_image_and_link(self):
        photo_id = add_item("Silver Phone", image_filename="phone.png")
        page = self.client.get("/recently-viewed", query_string={"ids": f"{photo_id},1"}).get_data(as_text=True)
        self.assertIn("Silver Phone", page)
        self.assertIn('src="/static/uploads/phone.png"', page)
        self.assertIn(f'href="/item/{photo_id}"', page)
        self.assertIn("Black Backpack", page)
        self.assertIn('href="/item/1"', page)
        self.assertIn("placeholder-symbol", page)

    def test_recently_viewed_escapes_titles(self):
        item_id = add_item('<img src=x onerror="alert(1)">')
        page = self.client.get(f"/recently-viewed?ids={item_id}").get_data(as_text=True)
        self.assertIn("&lt;img src=x", page)
        self.assertNotIn("<img src=x", page)


if __name__ == "__main__":
    unittest.main()
