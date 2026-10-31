from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sqlite3
import uuid
import warnings

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from PIL import Image, UnidentifiedImageError

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "campusfind.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
IMAGE_FORMAT_BY_EXTENSION = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "gif": "GIF",
    "webp": "WEBP",
}
IMAGE_EXTENSION_BY_FORMAT = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-development-key"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

CATEGORIES = ["Electronics", "ID Cards", "Bags", "Books", "Clothing", "Keys", "Accessories", "Other"]
STATUSES = ["Lost", "Found", "Returned"]


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                item_status TEXT NOT NULL CHECK(item_status IN ('Lost', 'Found', 'Returned')),
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                item_date TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact_email TEXT NOT NULL,
                image_filename TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        if count == 0:
            examples = [
                ("Black Backpack", "Bags", "Lost", "A black backpack with a small keychain attached.", "Central Library", "2026-10-23", "Riya Sharma", "riya@example.com", None),
                ("Blue Water Bottle", "Accessories", "Found", "Blue metal bottle found near the canteen.", "Main Canteen", "2026-10-24", "Aman Kumar", "aman@example.com", None),
                ("Student ID Card", "ID Cards", "Found", "An ID card was found outside the electrical department.", "Electrical Department", "2026-10-22", "Campus Desk", "helpdesk@example.com", None),
                ("Wireless Earbuds", "Electronics", "Lost", "Small white wireless earbuds in a charging case.", "Lecture Hall 2", "2026-10-20", "Neha Singh", "neha@example.com", None),
            ]
            conn.executemany("""
                INSERT INTO items (title, category, item_status, description, location, item_date,
                                   contact_name, contact_email, image_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, examples)


def allowed_file(filename):
    return Path(filename).suffix.lower().lstrip(".") in ALLOWED_EXTENSIONS


def valid_image_format(upload):
    extension = Path(upload.filename).suffix.lower().lstrip(".")
    expected_format = IMAGE_FORMAT_BY_EXTENSION.get(extension)
    if expected_format is None:
        return None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload.stream, formats=tuple(IMAGE_EXTENSION_BY_FORMAT)) as image:
                if image.format != expected_format:
                    return None
                image.verify()

            # verify() checks structure without decoding pixels; reopen and load to
            # catch truncated or otherwise undecodable image data as well.
            upload.stream.seek(0)
            with Image.open(upload.stream, formats=(expected_format,)) as image:
                image.load()
            return expected_format
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return None
    finally:
        upload.stream.seek(0)


@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "statuses": STATUSES, "current_year": date.today().year}


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "newest")
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    if category in CATEGORIES:
        query += " AND category = ?"
        params.append(category)
    if status in STATUSES:
        query += " AND item_status = ?"
        params.append(status)
    query += " ORDER BY item_date " + ("ASC" if sort == "oldest" else "DESC") + ", id DESC"
    with get_db() as conn:
        items = conn.execute(query, params).fetchall()
        counts = {
            "all": conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
            "lost": conn.execute("SELECT COUNT(*) FROM items WHERE item_status='Lost'").fetchone()[0],
            "found": conn.execute("SELECT COUNT(*) FROM items WHERE item_status='Found'").fetchone()[0],
            "returned": conn.execute("SELECT COUNT(*) FROM items WHERE item_status='Returned'").fetchone()[0],
        }
    return render_template("index.html", items=items, counts=counts, q=search,
                           selected_category=category, selected_status=status, sort=sort)


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    with get_db() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        abort(404)
    return render_template("detail.html", item=item)


@app.route("/report", methods=["GET", "POST"])
def report_item():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        item_status = request.form.get("item_status", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        item_date = request.form.get("item_date", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        contact_email = request.form.get("contact_email", "").strip()

        errors = []
        if not title or len(title) > 100:
            errors.append("Enter a title between 1 and 100 characters.")
        if category not in CATEGORIES:
            errors.append("Choose a valid category.")
        if item_status not in ("Lost", "Found"):
            errors.append("Choose whether the item was lost or found.")
        if not description or len(description) > 1000:
            errors.append("Enter a description (up to 1,000 characters).")
        if not location or len(location) > 120:
            errors.append("Enter a location (up to 120 characters).")
        try:
            parsed_date = date.fromisoformat(item_date)
            if parsed_date > date.today():
                errors.append("The item date cannot be in the future.")
        except ValueError:
            errors.append("Enter a valid item date.")
        if not contact_name or len(contact_name) > 80:
            errors.append("Enter your name (up to 80 characters).")
        if not contact_email or "@" not in contact_email or len(contact_email) > 120:
            errors.append("Enter a valid contact email.")

        image_filename = None
        image = request.files.get("image")
        if image and image.filename:
            if not allowed_file(image.filename):
                errors.append("Image must be PNG, JPG, JPEG, GIF, or WEBP.")
            else:
                image_format = valid_image_format(image)
                if image_format is None:
                    errors.append("Uploaded file is not a valid PNG, JPG, JPEG, GIF, or WEBP image.")
                else:
                    suffix = IMAGE_EXTENSION_BY_FORMAT[image_format]
                    image_filename = f"{uuid.uuid4().hex}.{suffix}"

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("report.html", form=request.form, today=date.today().isoformat())

        if image_filename:
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            image.save(UPLOAD_DIR / image_filename)

        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO items (title, category, item_status, description, location, item_date,
                                   contact_name, contact_email, image_filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, category, item_status, description, location, item_date,
                  contact_name, contact_email, image_filename))
            item_id = cursor.lastrowid
        flash("Your item has been reported successfully.", "success")
        return redirect(url_for("item_detail", item_id=item_id))

    return render_template("report.html", form={}, today=date.today().isoformat())


@app.route("/item/<int:item_id>/returned", methods=["POST"])
def mark_returned(item_id):
    with get_db() as conn:
        item = conn.execute("SELECT id, item_status FROM items WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            abort(404)
        if item["item_status"] != "Returned":
            conn.execute("UPDATE items SET item_status='Returned' WHERE id=?", (item_id,))
    flash("Item marked as returned. Great news!", "success")
    return redirect(url_for("item_detail", item_id=item_id))


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_error):
    flash("Image is too large. Maximum upload size is 5 MB.", "error")
    return redirect(url_for("report_item"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
