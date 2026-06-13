"""Tests for the HTTP contract: auth gates, verify policy, enrollment flow."""

import base64

import config
import recognizer
import store


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


# --- Open + auth gates ----------------------------------------------------

def test_health_is_open(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_verify_requires_api_key(client):
    resp = client.post("/verify", json={"image_base64": _b64(b"x")})
    assert resp.status_code == 401


def test_dashboard_requires_login(client):
    resp = client.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 302  # redirected to /login
    assert "/login" in resp.headers["Location"]


def test_api_events_requires_login(client):
    resp = client.get("/api/events")
    assert resp.status_code == 401


# --- Verify behaviour -----------------------------------------------------

def test_verify_bad_input(client, api_headers):
    resp = client.post("/verify", json={"nope": 1}, headers=api_headers)
    assert resp.status_code == 400
    assert resp.get_json()["result"] == "DENIED"


def test_verify_granted_shape(client, api_headers, monkeypatch):
    monkeypatch.setattr(config, "STUB_RESULT", "GRANTED")
    store.add_user("Ali", [recognizer.make_encoding(b"x")])

    resp = client.post("/verify", json={"image_base64": _b64(b"frame")}, headers=api_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["result"] == "GRANTED"
    assert body["name"] == "Ali"
    assert set(body) == {"result", "name", "confidence", "event_id"}
    assert body["event_id"] is not None


def test_confidence_below_threshold_denies(client, api_headers, monkeypatch):
    # Stub grants at 0.95; raise the bar above that -> policy must DENY.
    monkeypatch.setattr(config, "STUB_RESULT", "GRANTED")
    monkeypatch.setattr(config, "CONFIDENCE_THRESHOLD", 0.99)
    store.add_user("Ali", [recognizer.make_encoding(b"x")])

    resp = client.post("/verify", json={"image_base64": _b64(b"frame")}, headers=api_headers)
    assert resp.get_json()["result"] == "DENIED"


def test_recognize_alias_works(client, api_headers, monkeypatch):
    monkeypatch.setattr(config, "STUB_RESULT", "DENIED")
    resp = client.post("/recognize", json={"image_b64": _b64(b"frame")}, headers=api_headers)
    assert resp.status_code == 200
    assert resp.get_json()["result"] == "DENIED"


# --- Camera enrollment flow ----------------------------------------------

def test_full_enrollment_flow(admin_client, api_headers, monkeypatch):
    monkeypatch.setattr(config, "ENROLL_FRAMES_NEEDED", 3)

    # Admin starts a scan.
    resp = admin_client.post("/enroll/start", json={"name": "Dana"})
    assert resp.status_code == 200

    # Pi sees the pending scan (needs the API key, not a login).
    pending = admin_client.get("/enroll/pending", headers=api_headers).get_json()
    assert pending["active"] is True and pending["name"] == "Dana"

    # Pi submits frames until complete.
    last = None
    for i in range(3):
        last = admin_client.post("/enroll", json={"image_base64": _b64(f"f{i}".encode())},
                                 headers=api_headers).get_json()
    assert last["status"] == "complete"

    # User is now registered with 3 samples.
    users = {u["name"]: u for u in store.get_users()}
    assert "Dana" in users and len(users["Dana"]["encodings"]) == 3


def test_enroll_without_session_conflicts(admin_client, api_headers):
    resp = admin_client.post("/enroll", json={"image_base64": base64.b64encode(b"x").decode()},
                             headers=api_headers)
    assert resp.status_code == 409


def test_enroll_start_requires_login(client):
    resp = client.post("/enroll/start", json={"name": "X"})
    assert resp.status_code == 401
