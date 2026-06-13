"""VisionGate data-layer Flask API + dashboard (Role C).

Machine endpoints (Pi, protected by X-API-Key):
  POST /verify           - the contract the firmware calls to check a face.
  POST /recognize        - alias of /verify (the PRD's documented name).
  GET  /enroll/pending   - is there a scan enrollment waiting? (Pi polls this)
  POST /enroll           - submit one captured frame toward the active scan.

Admin endpoints (browser, protected by session login):
  GET  /                 - live dashboard.
  GET  /login, /logout   - admin authentication.
  POST /enroll/start     - begin a camera scan for a named person.
  POST /enroll/cancel    - abort the active scan.
  POST /users/delete     - remove a registered user.
  GET  /api/events,/api/stats,/api/enroll/status - dashboard data feeds.

Open:
  GET  /health           - liveness probe.

Verification flow: decode image -> recognize -> threshold -> (maybe) save
frame -> log event -> alert if denied -> return {result, name, confidence,
event_id}.
"""

import base64
import binascii
import logging
import os
from datetime import datetime, timezone

from flask import (Flask, jsonify, redirect, render_template, request,
                   session, url_for)

import alerts
import auth
import config
import recognizer
import store

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
# Re-read templates from disk each request so dashboard edits show up on a
# browser refresh without restarting the server.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True


def _bootstrap() -> None:
    os.makedirs(config.IMAGE_DIR, exist_ok=True)
    store.init_db()
    removed = store.purge_old_data(config.CAPTURE_RETENTION_DAYS)
    if removed:
        logging.info("Retention purge removed %s old event(s).", removed)


def _save_capture(image_bytes: bytes, event_time: str) -> str | None:
    """Persist the raw frame so the dashboard/log can reference it."""
    try:
        safe_stamp = event_time.replace(":", "-").replace(".", "-")
        filename = f"{safe_stamp}.jpg"
        path = os.path.join(config.IMAGE_DIR, filename)
        with open(path, "wb") as fh:
            fh.write(image_bytes)
        return os.path.relpath(path, config.BASE_DIR)
    except OSError:
        logging.exception("Failed to save capture image.")
        return None


def _decode_image(data: dict) -> tuple[bytes | None, str | None]:
    """Pull and decode the base64 image from a request body.
    Returns (image_bytes, error_message)."""
    image_b64 = data.get("image_base64") or data.get("image_b64")
    if not isinstance(image_b64, str) or not image_b64:
        return None, "missing image_base64"
    try:
        return base64.b64decode(image_b64, validate=True), None
    except (binascii.Error, ValueError):
        return None, "image_base64 is not valid base64"


# --- Verification ---------------------------------------------------------

def _handle_verify():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"result": "DENIED", "name": "UNKNOWN", "confidence": 0.0,
                        "event_id": None, "error": "invalid JSON body"}), 400

    image_bytes, error = _decode_image(data)
    if error:
        return jsonify({"result": "DENIED", "name": "UNKNOWN", "confidence": 0.0,
                        "event_id": None, "error": error}), 400

    event_time = data.get("timestamp") or datetime.now(timezone.utc).isoformat()

    # 1. Recognize.
    match = recognizer.recognize(image_bytes)

    # 2. Grant policy: known face AND confidence over threshold.
    granted = (
        match.name != recognizer.UNKNOWN
        and match.confidence >= config.CONFIDENCE_THRESHOLD
    )
    result = "GRANTED" if granted else "DENIED"

    # 3. Persist the frame (privacy: optionally skip strangers) and log.
    image_path = None
    if granted or config.STORE_UNKNOWN_CAPTURES:
        image_path = _save_capture(image_bytes, event_time)
    event_id = store.log_event(
        name=match.name, result=result, confidence=match.confidence,
        image_path=image_path, timestamp=event_time,
    )

    logging.info("Verify -> result=%s name=%s confidence=%.3f event_id=%s",
                 result, match.name, match.confidence, event_id)

    # 4. Alert on anything not granted.
    if not granted:
        alerts.send_alert({"result": result, "name": match.name,
                           "confidence": match.confidence, "event_id": event_id,
                           "timestamp": event_time})

    # 5. Respond. The firmware only reads `result`; the rest drives the dashboard.
    return jsonify({"result": result, "name": match.name,
                    "confidence": match.confidence, "event_id": event_id})


@app.post("/verify")
@auth.api_key_required
def verify():
    return _handle_verify()


@app.post("/recognize")
@auth.api_key_required
def recognize_alias():
    return _handle_verify()


# --- Camera enrollment (Pi side, API-key protected) -----------------------

@app.get("/enroll/pending")
@auth.api_key_required
def enroll_pending():
    """The Pi polls this. Returns the active scan, or {active: false}."""
    sess = store.get_active_enrollment()
    if not sess:
        return jsonify({"active": False})
    return jsonify({"active": True, **sess})


@app.post("/enroll")
@auth.api_key_required
def enroll_frame():
    """The Pi posts one captured frame toward the active scan."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "invalid JSON body"}), 400

    image_bytes, error = _decode_image(data)
    if error:
        return jsonify({"error": error}), 400

    try:
        encoding = recognizer.make_encoding(image_bytes)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422  # e.g. no face detected

    updated = store.add_enrollment_frame(encoding)
    if updated is None:
        return jsonify({"error": "no active enrollment session"}), 409
    return jsonify(updated)


# --- Admin enrollment control (browser, login protected) ------------------

@app.post("/enroll/start")
@auth.login_required
def enroll_start():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    store.start_enrollment(name, config.ENROLL_FRAMES_NEEDED)
    return jsonify({"active": True, "name": name,
                    "frames_needed": config.ENROLL_FRAMES_NEEDED,
                    "frames_collected": 0})


@app.post("/enroll/cancel")
@auth.login_required
def enroll_cancel():
    cancelled = store.cancel_enrollment()
    return jsonify({"cancelled": cancelled})


@app.get("/api/enroll/status")
@auth.login_required
def enroll_status():
    sess = store.get_active_enrollment()
    return jsonify(sess or {"active": False})


@app.post("/users/delete")
@auth.login_required
def users_delete():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    removed = store.remove_user(name)
    return jsonify({"removed": removed})


# --- Auth routes ----------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if auth.check_credentials(username, password):
            session["admin"] = True
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        return render_template("login.html", error="Invalid credentials."), 401
    return render_template("login.html", error=None)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- Health + dashboard data feeds ---------------------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok", "recognizer": config.RECOGNIZER_BACKEND})


@app.get("/api/events")
@auth.login_required
def api_events():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
    except ValueError:
        limit = 50
    return jsonify(store.get_recent_events(limit))


@app.get("/api/stats")
@auth.login_required
def api_stats():
    return jsonify(store.get_stats())


@app.get("/api/users")
@auth.login_required
def api_users():
    users = store.get_users()
    return jsonify([{"name": u["name"], "samples": len(u["encodings"]),
                     "created_at": u["created_at"]} for u in users])


@app.get("/")
@auth.page_login_required
def dashboard():
    return render_template("dashboard.html")


_bootstrap()


def create_app():
    """Factory used by serve.py / tests."""
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("VisionGate data layer (DEV server) on http://%s:%s "
                 "(recognizer=%s, alerts=%s)", config.HOST, config.PORT,
                 config.RECOGNIZER_BACKEND, config.ALERT_BACKEND)
    app.run(host=config.HOST, port=config.PORT, debug=False)
