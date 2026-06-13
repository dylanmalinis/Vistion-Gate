"""Configuration values for the VisionGate controller."""

# Recognition API settings.
API_URL = "http://localhost:8000/verify"
API_TIMEOUT_SECONDS = 5

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
