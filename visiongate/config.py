"""Configuration values for the VisionGate controller."""

import os

# Recognition API settings.
API_URL = "http://localhost:8000/verify"
API_TIMEOUT_SECONDS = 5

# Camera-enrollment endpoints on the data server (used by enroll_runner.py).
ENROLL_PENDING_URL = "http://localhost:8000/enroll/pending"
ENROLL_SUBMIT_URL = "http://localhost:8000/enroll"

# Shared secret the data server requires (X-API-Key header). Must match the
# data layer's VISIONGATE_API_KEY. Override here or via the env var.
API_KEY = os.environ.get("VISIONGATE_API_KEY", "visiongate-dev-key")

# Require a second factor (a whitelisted RFID tap) AFTER a face is granted
# before the door actually unlocks. Defends against face spoofing (a printed
# photo can fool basic face recognition). Leave False for the simple demo.
REQUIRE_SECOND_FACTOR = False

# Keep this True while testing without the Computer Science recognition API.
MOCK_API = True

# In mock mode, switch this between "GRANTED" and "DENIED" to test both paths.
MOCK_API_RESULT = "GRANTED"

# RFID fallback settings.
RFID_ENABLED = True
RFID_WHITELIST = {
    "CARD-1234",
    "CARD-5678",
}

# Simulated timing values.
RELAY_UNLOCK_SECONDS = 3
DENY_LED_SECONDS = 2
FALLBACK_WAIT_SECONDS = 2

# Main loop settings.
# Set to None on the Raspberry Pi when you want the program to run forever.
MAX_CYCLES = 5
