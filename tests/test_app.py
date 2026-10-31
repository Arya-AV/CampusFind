import html
import re
import unittest
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import app as campus_app

ITEM_CARD_LINK = r'class="item-card-link" href="([^"]+)"'
BACK_LINK = r'class="back-link" href="([^"]+)"'
RETURNED_FORM = r'action="([^"]+/returned[^"]*)"'


def split_url(url):
    """Split a URL into its path and a dict of its query parameters."""
    parts = urlsplit(url)
    return parts.path, dict(parse_qsl(parts.query))


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

    def find_url(self, response, pattern):
        """Return the path and query of the first link in the page matching pattern."""
        match = re.search(pattern, response.get_data(as_text=True))
        self.assertIsNotNone(match, f"No link matching {pattern!r} found")
        return split_url(html.unescape(match.group(1)))

    def test_listing_filters_survive_round_trip_through_item_detail(self):
        combinations = [
            {"q": "Backpack"},
            {"q": "Black Backpack"},
            {"category": "Accessories"},
            {"status": "Found"},
            {"sort": "oldest"},
            {"q": "Library", "status": "Lost"},
            {"category": "Electronics", "sort": "oldest"},
            {"q": "card", "category": "ID Cards", "status": "Found", "sort": "oldest"},
        ]
        for filters in combinations:
            with self.subTest(filters=filters):
                listing = self.client.get("/", query_string=filters)
                item_path, item_query = self.find_url(listing, ITEM_CARD_LINK)
                self.assertRegex(item_path, r"^/item/\d+$")
                self.assertEqual(item_query, filters)

                detail = self.client.get(item_path, query_string=item_query)
                self.assertEqual(detail.status_code, 200)
                back_path, back_query = self.find_url(detail, BACK_LINK)
                self.assertEqual(back_path, "/")
                self.assertEqual(back_query, filters)

    def test_back_link_restores_listing_selections(self):
        filters = {"q": "Library", "category": "Bags", "status": "Lost", "sort": "oldest"}
        detail = self.client.get("/item/1", query_string=filters)
        back_path, back_query = self.find_url(detail, BACK_LINK)

        listing = self.client.get(back_path, query_string=back_query)
        page = listing.get_data(as_text=True)
        self.assertIn("Black Backpack", page)
        self.assertIn('value="Library"', page)
        self.assertIn('<option value="Bags" selected>', page)
        self.assertIn('<option value="Lost" selected>', page)
        self.assertIn('<option value="oldest" selected>', page)

    def test_direct_item_visit_links_back_to_all_listings(self):
        response = self.client.get("/item/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.find_url(response, BACK_LINK), ("/", {}))

    def test_invalid_listing_filters_are_dropped_from_back_link(self):
        response = self.client.get(
            "/item/1?q=%20%20&category=Spaceships&status=Missing&sort=sideways&item_id=7&page=2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.find_url(response, BACK_LINK), ("/", {}))

    def test_valid_listing_filters_are_kept_when_others_are_invalid(self):
        response = self.client.get("/item/1?q=bag&category=Spaceships&status=Lost&sort=sideways")
        self.assertEqual(
            self.find_url(response, BACK_LINK), ("/", {"q": "bag", "status": "Lost"})
        )

    def test_item_links_skip_invalid_and_default_filters(self):
        response = self.client.get("/?q=%20&category=Spaceships&status=Lost&sort=newest&item_id=7")
        self.assertEqual(response.status_code, 200)
        _, item_query = self.find_url(response, ITEM_CARD_LINK)
        self.assertEqual(item_query, {"status": "Lost"})

    def test_mark_returned_keeps_listing_filters(self):
        with campus_app.get_db() as conn:
            item_id = conn.execute(
                """
                INSERT INTO items (title, category, item_status, description, location,
                                   item_date, contact_name, contact_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("Green Umbrella", "Accessories", "Found", "A folded green umbrella.",
                 "Bus Stop", "2026-10-21", "Campus Desk", "helpdesk@example.com"),
            ).lastrowid
        filters = {"q": "Umbrella", "status": "Found"}

        detail = self.client.get(f"/item/{item_id}", query_string=filters)
        form_path, form_query = self.find_url(detail, RETURNED_FORM)
        self.assertEqual(form_path, f"/item/{item_id}/returned")
        self.assertEqual(form_query, filters)

        response = self.client.post(form_path, query_string=form_query)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(split_url(response.headers["Location"]), (f"/item/{item_id}", filters))


if __name__ == "__main__":
    unittest.main()
