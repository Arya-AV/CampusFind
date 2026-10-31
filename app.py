from datetime import date
import os
from pathlib import Path
import sqlite3
import uuid

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "campusfind.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

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


UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(file_storage):
    """
    Save the uploaded image with a unique name.
    Returns (stored_filename, absolute_saved_path).
    """
    if not file_storage or not file_storage.filename:
        return None, None

    if not allowed_file(file_storage.filename):
        raise ValueError("Unsupported image type")

    # UUID prevents collisions with files already belonging to listings.
    ext = Path(file_storage.filename).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_FOLDER, filename)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_storage.save(saved_path)
    return filename, saved_path


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
        category = request.form.get("category", "").strip() or "Other"
        item_status = request.form.get("item_status", "").strip() or "Lost"
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        item_date = request.form.get("item_date", "").strip() or date.today().isoformat()
        contact_name = request.form.get("contact_name", "").strip() or request.form.get("contact", "").strip()
        contact_email = request.form.get("contact_email", "").strip() or (request.form.get("contact", "").strip() if "@" in request.form.get("contact", "") else "user@campusfind.test")
        image_file = request.files.get("image")

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

        if image_file and image_file.filename:
            if not allowed_file(image_file.filename):
                errors.append("Image must be PNG, JPG, JPEG, GIF, or WEBP.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("report.html", form=request.form, today=date.today().isoformat())

        saved_image_path = None
        committed = False

        try:
            # 1. Persist the upload first (as the current app already does).
            if image_file and image_file.filename:
                image_filename, saved_image_path = save_uploaded_image(image_file)
            else:
                image_filename = None

            # 2. Insert the listing inside a transaction.
            with get_db() as conn:
                cursor = conn.execute("""
                    INSERT INTO items (title, category, item_status, description, location, item_date,
                                       contact_name, contact_email, image_filename)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, category, item_status, description, location, item_date,
                      contact_name, contact_email, image_filename))
                item_id = cursor.lastrowid
            committed = True

            flash("Your item has been reported successfully.", "success")
            return redirect(url_for("item_detail", item_id=item_id))

        except Exception:
            # Clean up ONLY the file saved during this request.
            # committed=False also guards against cleaning after a successful insert.
            if not committed and saved_image_path and os.path.isfile(saved_image_path):
                try:
                    os.remove(saved_image_path)
                except OSError:
                    # Cleanup should never crash the request/response.
                    pass

            # Keep test visibility: an unexpected failure surfaces as a 500.
            raise

    return render_template("report.html", form={}, today=date.today().isoformat())


app.add_url_rule("/report", endpoint="report", view_func=report_item, methods=["GET", "POST"])


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


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    return "Internal Server Error", 500


init_db()

if __name__ == "__main__":
    app.run(debug=True)
