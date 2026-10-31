from io import BytesIO
import unittest
import tempfile
from pathlib import Path

import app as campus_app
from PIL import Image


class CampusFindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_db = campus_app.DATABASE
        cls.original_upload_dir = campus_app.UPLOAD_DIR
        cls.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(cls.temp_dir.name)
        campus_app.DATABASE = temp_path / "test.db"
        campus_app.UPLOAD_DIR = temp_path / "uploads"
        campus_app.init_db()
        campus_app.app.config["TESTING"] = True
        cls.client = campus_app.app.test_client()

    @classmethod
    def tearDownClass(cls):
        campus_app.DATABASE = cls.original_db
        campus_app.UPLOAD_DIR = cls.original_upload_dir
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

    def report_form_data(self, title):
        return {
            "title": title,
            "category": "Other",
            "item_status": "Found",
            "description": "A test item.",
            "location": "Library",
            "item_date": "2026-10-30",
            "contact_name": "Test Student",
            "contact_email": "test@example.com",
        }

    def create_image_bytes(self, image_format):
        image = Image.new("RGB", (2, 2), color="red")
        stream = BytesIO()
        image.save(stream, format=image_format)
        return stream.getvalue()

    def test_valid_supported_images_are_saved(self):
        extensions = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}
        for image_format, extension in extensions.items():
            with self.subTest(image_format=image_format):
                title = f"Valid {image_format} upload"
                response = self.client.post(
                    "/report",
                    data={
                        **self.report_form_data(title),
                        "image": (BytesIO(self.create_image_bytes(image_format)), f"photo.{extension}"),
                    },
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 302)

                with campus_app.get_db() as conn:
                    item = conn.execute(
                        "SELECT image_filename FROM items WHERE title = ?", (title,)
                    ).fetchone()
                self.assertIsNotNone(item)
                self.assertTrue(item["image_filename"].endswith(f".{extension}"))
                saved_image = campus_app.UPLOAD_DIR / item["image_filename"]
                self.assertTrue(saved_image.is_file())
                with Image.open(saved_image) as decoded:
                    self.assertEqual(decoded.format, image_format)
                    decoded.load()

    def test_text_file_renamed_as_png_is_rejected_and_not_saved(self):
        title = "Disguised text upload"
        files_before = set(campus_app.UPLOAD_DIR.iterdir()) if campus_app.UPLOAD_DIR.exists() else set()
        response = self.client.post(
            "/report",
            data={
                **self.report_form_data(title),
                "image": (BytesIO(b"ordinary text, not a PNG image"), "photo.png"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Uploaded file is not a valid", response.data)
        files_after = set(campus_app.UPLOAD_DIR.iterdir()) if campus_app.UPLOAD_DIR.exists() else set()
        self.assertEqual(files_after, files_before)
        with campus_app.get_db() as conn:
            item = conn.execute("SELECT id FROM items WHERE title = ?", (title,)).fetchone()
        self.assertIsNone(item)

    def test_upload_over_five_megabytes_keeps_existing_error_handling(self):
        data = {
            **self.report_form_data("Oversized upload"),
            "image": (BytesIO(b"x" * (5 * 1024 * 1024)), "large.png"),
        }
        response = self.client.post("/report", data=data, content_type="multipart/form-data")
        response.request.environ["wsgi.input"].close()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/report")


if __name__ == "__main__":
    unittest.main()
