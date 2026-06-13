"""Configuration for the VisionGate data / AI layer (Role C).

Everything here is tuned so the whole pipeline runs on a laptop with no special
hardware or accounts. Flip the backend switches when you move to the Pi, wire a
real alert channel, or harden for a real deployment.

Secrets read from environment variables so you never commit them:
    VISIONGATE_API_KEY            - shared key the Pi must send (see API_KEY)
    VISIONGATE_ADMIN_PASSWORD     - dashboard admin password
    VISIONGATE_SECRET_KEY         - Flask session signing key
    VISIONGATE_DB                 - override the SQLite path (used by tests)
    VISIONGATE_TELEGRAM_TOKEN     - Telegram bot token (telegram alert backend)
    VISIONGATE_TELEGRAM_CHAT_ID   - Telegram chat id  (telegram alert backend)
"""

import os

# --- Server ---------------------------------------------------------------
# The firmware (api_client.py) posts to http://localhost:8000/verify, so we
# serve on 8000 to match it out of the box.
HOST = "0.0.0.0"
PORT = 8000

# --- Storage --------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("VISIONGATE_DB", os.path.join(BASE_DIR, "visiongate.db"))
IMAGE_DIR = os.path.join(BASE_DIR, "captures")  # where captured frames are saved

# --- Security -------------------------------------------------------------
# Shared key the Pi must send as the X-API-Key header on /verify and /enroll.
# CHANGE THIS in production via the VISIONGATE_API_KEY env var.
API_KEY = os.environ.get("VISIONGATE_API_KEY", "visiongate-dev-key")

# Dashboard admin login. CHANGE THIS via VISIONGATE_ADMIN_PASSWORD.
ADMIN_USERNAME = os.environ.get("VISIONGATE_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("VISIONGATE_ADMIN_PASSWORD", "visiongate")

# Signs the session cookie. CHANGE THIS via VISIONGATE_SECRET_KEY.
SECRET_KEY = os.environ.get("VISIONGATE_SECRET_KEY", "dev-secret-change-me")

# --- Recognition ----------------------------------------------------------
# "stub"            -> deterministic, no heavy deps, runs anywhere (default).
# "face_recognition" -> real dlib-based matching (enable on the Pi once the
#                       face_recognition package is installed).
RECOGNIZER_BACKEND = "stub"

# A face is only GRANTED when it matches a registered user AND the match
# confidence is at least this. Anything below -> DENIED / UNKNOWN.
CONFIDENCE_THRESHOLD = 0.75

# Stub-only control so you can demo both paths on a laptop:
#   "auto"     -> deterministic result derived from the image bytes + enrolled users
#   "GRANTED"  -> always match the first enrolled user (or "Demo User") at high confidence
#   "DENIED"   -> always return UNKNOWN at low confidence
#   "<a name>" -> always return that exact name at high confidence
STUB_RESULT = "auto"

# face_recognition tolerance (lower = stricter). 0.6 is the library default.
FACE_MATCH_TOLERANCE = 0.6

# --- Enrollment -----------------------------------------------------------
# How many camera frames to capture per person during a scan enrollment.
# More frames = more robust matching.
ENROLL_FRAMES_NEEDED = 5

# --- Privacy / retention --------------------------------------------------
# Delete saved capture images and their events older than this many days on
# startup. Set to 0 to keep everything forever.
CAPTURE_RETENTION_DAYS = 7

# If False, frames from DENIED / UNKNOWN attempts are NOT written to disk
# (the event is still logged, just without an image). Avoids storing photos of
# strangers indefinitely.
STORE_UNKNOWN_CAPTURES = True

# --- Alerts ---------------------------------------------------------------
# "console"  -> log to stdout and append to alerts.log (default, no secrets).
# "telegram" -> send a Telegram message (set the token + chat id below).
ALERT_BACKEND = "console"
ALERT_LOG_PATH = os.path.join(BASE_DIR, "alerts.log")

TELEGRAM_BOT_TOKEN = os.environ.get("VISIONGATE_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("VISIONGATE_TELEGRAM_CHAT_ID", "")
