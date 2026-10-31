"""User authentication package for CampusFind.

Provides encrypted password management, SQLite user storage,
login/logout/signup routes, and authentication decorators.
"""

from userauth.models import (
    init_auth_db,
    hash_password,
    verify_password,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
)
from userauth.routes import (
    auth_bp,
    login_required,
    get_current_user,
)

__all__ = [
    "auth_bp",
    "init_auth_db",
    "login_required",
    "get_current_user",
    "hash_password",
    "verify_password",
    "create_user",
    "authenticate_user",
    "get_user_by_id",
    "get_user_by_email",
]

