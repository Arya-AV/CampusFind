import sqlite3
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash


def init_auth_db(conn: sqlite3.Connection) -> None:
    """Create the users table and indexes if they do not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")


def hash_password(password: str) -> str:
    """Securely hash a password using Werkzeug's default algorithm."""
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plaintext password against the stored password hash."""
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)


def create_user(conn: sqlite3.Connection, name: str, email: str, password: str) -> Dict[str, Any]:
    """Validate and insert a new user with an encrypted password hash."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not name or len(name) > 80:
        raise ValueError("Please provide your name (up to 80 characters).")
    if not email or "@" not in email or "." not in email or len(email) > 120:
        raise ValueError("Please provide a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")
    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters.")

    existing = conn.execute(
        "SELECT id FROM users WHERE lower(email) = ?",
        (email,)
    ).fetchone()
    if existing:
        raise ValueError("An account with this email address already exists.")

    pwd_hash = hash_password(password)
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, pwd_hash)
    )
    user_id = cursor.lastrowid
    return {
        "id": user_id,
        "name": name,
        "email": email,
    }


def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify email and password and return the user record if valid."""
    email = (email or "").strip().lower()
    if not email or not password:
        return None

    row = conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE lower(email) = ?",
        (email,)
    ).fetchone()

    if row is None:
        return None

    if not verify_password(row["password_hash"], password):
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
    }


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user by ID without sensitive password hash."""
    if not user_id:
        return None
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by email without sensitive password hash."""
    email = (email or "").strip().lower()
    if not email:
        return None
    row = conn.execute(
        "SELECT id, name, email, created_at FROM users WHERE lower(email) = ?",
        (email,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)

