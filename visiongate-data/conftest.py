"""Shared pytest setup for the VisionGate data layer.

Points the app at a throwaway temp DB + capture dir and known test secrets
*before* importing the app, so tests never touch real data or need real auth.
"""

import os
import sys
import tempfile

# Make the data-layer modules importable regardless of pytest's rootdir.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Wire test secrets + a temp DB before config/app get imported anywhere.
_TMP = tempfile.mkdtemp(prefix="visiongate-test-")
os.environ["VISIONGATE_DB"] = os.path.join(_TMP, "test.db")
os.environ["VISIONGATE_API_KEY"] = "test-key"
os.environ["VISIONGATE_ADMIN_USER"] = "admin"
os.environ["VISIONGATE_ADMIN_PASSWORD"] = "test-pass"
os.environ["VISIONGATE_SECRET_KEY"] = "test-secret"

import config  # noqa: E402

config.IMAGE_DIR = os.path.join(_TMP, "captures")
config.CAPTURE_RETENTION_DAYS = 0  # don't purge during tests
config.RECOGNIZER_BACKEND = "stub"

import pytest  # noqa: E402

import store  # noqa: E402
from app import app as flask_app  # noqa: E402  (import triggers _bootstrap)


@pytest.fixture(autouse=True)
def reset_db():
    """Start every test with empty tables."""
    store.init_db()
    import sqlite3
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM access_events")
    conn.execute("DELETE FROM enrollment_sessions")
    conn.commit()
    conn.close()
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture
def admin_client(client):
    """A test client with an authenticated admin session."""
    resp = client.post("/login", data={"username": "admin", "password": "test-pass"})
    assert resp.status_code in (302, 200)
    return client


@pytest.fixture
def api_headers():
    return {"X-API-Key": "test-key"}
