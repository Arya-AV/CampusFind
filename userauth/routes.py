import functools
from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from userauth.models import (
    authenticate_user,
    create_user,
    get_user_by_id,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def get_db():
    """Lazily obtain the database context manager from app."""
    import app
    return app.get_db()


def get_current_user():
    """Return the currently authenticated user dictionary or None."""
    return getattr(g, "user", None)


@auth_bp.before_app_request
def load_logged_in_user():
    """Load the user record from SQLite on every request if session exists."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        try:
            with get_db() as conn:
                g.user = get_user_by_id(conn, user_id)
        except Exception:
            g.user = None

        if g.user is None:
            # Stale session
            session.clear()


@auth_bp.app_context_processor
def inject_auth_user():
    """Make current_user accessible in all Jinja templates."""
    return {"current_user": g.user}


def login_required(view):
    """Decorator to require login for specific routes."""
    @functools.wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            is_ajax = (
                request.is_json
                or request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or "application/json" in request.headers.get("Accept", "")
            )
            if is_ajax:
                return jsonify({
                    "success": False,
                    "error": "Authentication required",
                    "authenticated": False,
                }), 401

            flash("Please sign in or create an account to report an item.", "error")
            next_target = request.full_path if request.query_string else request.path
            return redirect(url_for("index", auth="login", next=next_target))
        return view(*args, **kwargs)
    return wrapped_view


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new user account with hashed password."""
    is_json = request.is_json
    data = request.get_json(silent=True) or request.form

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    next_url = data.get("next") or request.args.get("next") or url_for("index")

    errors = []
    if not name:
        errors.append("Please enter your name.")
    if not email:
        errors.append("Please enter your email.")
    if not password:
        errors.append("Please enter a password.")
    elif len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        error_msg = errors[0]
        if is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        flash(error_msg, "error")
        return redirect(url_for("index", auth="signup", next=next_url))

    try:
        with get_db() as conn:
            user = create_user(conn, name=name, email=email, password=password)
    except ValueError as e:
        if is_json:
            return jsonify({"success": False, "error": str(e)}), 400
        flash(str(e), "error")
        return redirect(url_for("index", auth="signup", next=next_url))

    # Log in immediately upon signup
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    success_msg = f"Account created! Welcome to CampusFind, {user['name']}."
    flash(success_msg, "success")

    if is_json:
        return jsonify({
            "success": True,
            "message": success_msg,
            "redirect": next_url,
            "user": user,
        })
    return redirect(next_url)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate an existing user by email and password."""
    is_json = request.is_json
    data = request.get_json(silent=True) or request.form

    email = data.get("email", "").strip()
    password = data.get("password", "")
    next_url = data.get("next") or request.args.get("next") or url_for("index")

    if not email or not password:
        error_msg = "Please enter both email and password."
        if is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        flash(error_msg, "error")
        return redirect(url_for("index", auth="login", next=next_url))

    with get_db() as conn:
        user = authenticate_user(conn, email, password)

    if user is None:
        error_msg = "Invalid email or password."
        if is_json:
            return jsonify({"success": False, "error": error_msg}), 401
        flash(error_msg, "error")
        return redirect(url_for("index", auth="login", next=next_url))

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    success_msg = f"Welcome back, {user['name']}!"
    flash(success_msg, "success")

    if is_json:
        return jsonify({
            "success": True,
            "message": success_msg,
            "redirect": next_url,
            "user": user,
        })
    return redirect(next_url)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Sign the user out and clear the session."""
    session.clear()
    flash("You have been signed out.", "success")
    if request.is_json:
        return jsonify({"success": True, "redirect": url_for("index")})
    return redirect(url_for("index"))


@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Return JSON authentication status of current session."""
    if g.user:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": g.user["id"],
                "name": g.user["name"],
                "email": g.user["email"],
            }
        })
    return jsonify({"authenticated": False, "user": None})

