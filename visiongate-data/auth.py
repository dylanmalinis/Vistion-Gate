"""Authentication helpers for the VisionGate data layer.

Two independent gates:

  @login_required  - protects browser/admin routes with a session cookie set
                     by the /login form. Used for the dashboard, enrollment
                     control, and the data APIs.

  @api_key_required - protects machine routes (the Pi) with an X-API-Key
                      header that must match config.API_KEY. Used for /verify
                      and the camera-enrollment endpoints.

Login routes are unprotected. Everything else opts in via the decorators.
"""

import functools
import hmac

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import config

# Hash the configured admin password once at import.
_ADMIN_HASH = generate_password_hash(config.ADMIN_PASSWORD)


def check_credentials(username: str, password: str) -> bool:
    user_ok = hmac.compare_digest(username or "", config.ADMIN_USERNAME)
    pass_ok = check_password_hash(_ADMIN_HASH, password or "")
    return user_ok and pass_ok


def is_logged_in() -> bool:
    return bool(session.get("admin"))


def login_required(view):
    """For APIs and actions: hard 401 JSON when not authenticated."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return jsonify({"error": "authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


def page_login_required(view):
    """For browser page routes: redirect to the login page when not authenticated."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def api_key_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        provided = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, config.API_KEY):
            return jsonify({"error": "invalid or missing X-API-Key"}), 401
        return view(*args, **kwargs)

    return wrapped
