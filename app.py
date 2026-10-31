import os
import secrets
import warnings
from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3
import uuid
from contextlib import contextmanager

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    # Minimal fallback .env parser if python-dotenv is not installed
    env_file = BASE_DIR / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

from userauth import auth_bp, init_auth_db, login_required

DATABASE = BASE_DIR / "campusfind.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_secret_key():
    """Load Flask secret key from environment or safely generate an ephemeral key."""
    key = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")
    if key:
        return key

    # Handle missing secret key safely: generate an ephemeral cryptographic key
    warnings.warn(
        "SECRET_KEY is not set in environment or .env file. "
        "Generated an ephemeral key for this session. "
        "Set SECRET_KEY in your .env file or environment for persistent sessions.",
        RuntimeWarning,
        stacklevel=2,
    )
    return secrets.token_hex(32)


def get_debug_mode():
    """Determine whether debug mode is enabled from environment variables (disabled by default)."""
    val = os.environ.get("FLASK_DEBUG", "").strip().lower()
    return val in ("1", "true", "yes", "on", "development")


app = Flask(__name__)
app.config["SECRET_KEY"] = get_secret_key()
app.config["DEBUG"] = get_debug_mode()
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Register user authentication blueprint
app.register_blueprint(auth_bp)

CATEGORIES = [
    "Electronics",
    "ID Cards",
    "Bags",
    "Books",
    "Clothing",
    "Keys",
    "Accessories",
    "Other",
]
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
        # Create users table
        init_auth_db(conn)

        # Create items table with user_id foreign key
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
                user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # Migration: Ensure user_id column exists if table was created previously
        columns = [row[1] for row in conn.execute("PRAGMA table_info(items)").fetchall()]
        if "user_id" not in columns:
            conn.execute("ALTER TABLE items ADD COLUMN user_id INTEGER REFERENCES users(id)")

        # Create recently_viewed table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recently_viewed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                viewed_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
                UNIQUE (user_id, item_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recently_viewed_user ON recently_viewed(user_id, viewed_at DESC)")

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
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_globals():
    return {
        "categories": CATEGORIES,
        "statuses": STATUSES,
        "current_year": date.today().year,
        "current_user": getattr(g, "user", None),
    }


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "newest")
    only_mine = request.args.get("mine", "").strip() in ("1", "true")
    current_user = getattr(g, "user", None)

    query = """
        SELECT items.*, users.name AS poster_name
        FROM items
        LEFT JOIN users ON items.user_id = users.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (items.title LIKE ? OR items.description LIKE ? OR items.location LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    if category in CATEGORIES:
        query += " AND items.category = ?"
        params.append(category)
    if status in STATUSES:
        query += " AND items.item_status = ?"
        params.append(status)
    if only_mine and current_user:
        query += " AND items.user_id = ?"
        params.append(current_user["id"])

    query += " ORDER BY items.item_date " + ("ASC" if sort == "oldest" else "DESC") + ", items.id DESC"
    with get_db() as conn:
        items = conn.execute(query, params).fetchall()
        counts = {
            "all": conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
            "lost": conn.execute("SELECT COUNT(*) FROM items WHERE item_status='Lost'").fetchone()[0],
            "found": conn.execute("SELECT COUNT(*) FROM items WHERE item_status='Found'").fetchone()[0],
            "returned": conn.execute("SELECT COUNT(*) FROM items WHERE item_status='Returned'").fetchone()[0],
        }
        my_count = 0
        if current_user:
            my_count = conn.execute(
                "SELECT COUNT(*) FROM items WHERE user_id = ?",
                (current_user["id"],)
            ).fetchone()[0]

        # Fetch recently viewed items only for logged-in users and only on the main unfiltered page
        recently_viewed = []
        if current_user and not (search or category or status or only_mine):
            recently_viewed = conn.execute("""
                SELECT items.*, users.name AS poster_name
                FROM recently_viewed
                JOIN items ON recently_viewed.item_id = items.id
                LEFT JOIN users ON items.user_id = users.id
                WHERE recently_viewed.user_id = ?
                ORDER BY recently_viewed.viewed_at DESC
                LIMIT 6
            """, (current_user["id"],)).fetchall()

    return render_template(
        "index.html",
        items=items,
        counts=counts,
        q=search,
        selected_category=category,
        selected_status=status,
        sort=sort,
        only_mine=only_mine,
        my_count=my_count,
        recently_viewed=recently_viewed,
    )


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    current_user = getattr(g, "user", None)
    with get_db() as conn:
        item = conn.execute("""
            SELECT items.*, users.name AS poster_name, users.email AS poster_email
            FROM items
            LEFT JOIN users ON items.user_id = users.id
            WHERE items.id = ?
        """, (item_id,)).fetchone()
        if item is None:
            abort(404)

        # Record item view if user is logged in
        if current_user:
            now_ts = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO recently_viewed (user_id, item_id, viewed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET viewed_at = excluded.viewed_at
            """, (current_user["id"], item_id, now_ts))

    is_owner = bool(current_user and item["user_id"] == current_user["id"])
    return render_template("detail.html", item=item, is_owner=is_owner)


@app.route("/recently-viewed/clear", methods=["POST"])
@login_required
def clear_recently_viewed():
    current_user = getattr(g, "user", None)
    if current_user:
        with get_db() as conn:
            conn.execute("DELETE FROM recently_viewed WHERE user_id = ?", (current_user["id"],))
        flash("Browsing history cleared.", "success")
    return redirect(url_for("index"))


@app.route("/report", methods=["GET", "POST"])
@login_required
def report_item():
    current_user = getattr(g, "user", None)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        item_status = request.form.get("item_status", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        item_date = request.form.get("item_date", "").strip()
        contact_name = request.form.get("contact_name", "").strip() or (current_user["name"] if current_user else "")
        contact_email = request.form.get("contact_email", "").strip() or (current_user["email"] if current_user else "")

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
                suffix = secure_filename(image.filename).rsplit(".", 1)[1].lower()
                image_filename = f"{uuid.uuid4().hex}.{suffix}"

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("report.html", form=request.form, today=date.today().isoformat())

        saved_image_path = None
        if image_filename:
            upload_dir = Path(app.config.get("UPLOAD_FOLDER", UPLOAD_DIR))
            upload_dir.mkdir(parents=True, exist_ok=True)
            saved_image_path = upload_dir / image_filename
            image.save(saved_image_path)

        user_id = current_user["id"] if current_user else None

        try:
            with get_db() as conn:
                cursor = conn.execute("""
                    INSERT INTO items (title, category, item_status, description, location, item_date,
                                       contact_name, contact_email, image_filename, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, category, item_status, description, location, item_date,
                      contact_name, contact_email, image_filename, user_id))
                item_id = cursor.lastrowid
        except Exception:
            # Clean up uploaded image if database insertion fails
            if saved_image_path and saved_image_path.exists():
                try:
                    saved_image_path.unlink()
                except OSError:
                    pass
            raise

        flash(f"Your {item_status.lower()} item has been reported successfully.", "success")
        return redirect(url_for("item_detail", item_id=item_id))

    default_form = {}
    if current_user:
        default_form["contact_name"] = current_user["name"]
        default_form["contact_email"] = current_user["email"]

    return render_template("report.html", form=default_form, today=date.today().isoformat())


@app.route("/item/<int:item_id>/returned", methods=["POST"])
@login_required
def mark_returned(item_id):
    current_user = g.user
    with get_db() as conn:
        item = conn.execute("SELECT id, item_status, user_id FROM items WHERE id = ?", (item_id,)).fetchone()
        if item is None:
            abort(404)

        # STRICT AUTHORIZATION: Only the user who created this post can update it!
        if item["user_id"] is None or item["user_id"] != current_user["id"]:
            abort(403)

        if item["item_status"] != "Returned":
            conn.execute("UPDATE items SET item_status='Returned' WHERE id=?", (item_id,))

    if item["item_status"] == "Lost":
        flash("Great news! Your lost item has been marked as recovered.", "success")
    else:
        flash("Item marked as returned. Great news!", "success")

    return redirect(url_for("item_detail", item_id=item_id))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_error):
    flash("Image is too large. Maximum upload size is 5 MB.", "error")
    return redirect(url_for("report_item"))


init_db()

if __name__ == "__main__":
    debug_mode = get_debug_mode()
    host = os.environ.get("FLASK_RUN_HOST", os.environ.get("HOST", "127.0.0.1"))
    port = int(os.environ.get("FLASK_RUN_PORT", os.environ.get("PORT", 5000)))
    app.run(host=host, port=port, debug=debug_mode)
