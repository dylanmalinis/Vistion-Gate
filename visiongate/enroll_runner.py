"""Camera-enrollment runner (Pi side).

When an admin starts a face scan from the dashboard, the data server holds a
pending enrollment session. This script asks the server if a scan is waiting
and, if so, captures frames with the camera and posts them until the session
is complete. The server turns those frames into the registered face.

Run it on demand (or as a small loop) on the Pi:

    python3 enroll_runner.py            # do one pending scan, if any
    python3 enroll_runner.py --watch    # keep polling for scans

This keeps the main access loop (main.py) untouched: enrollment is a separate,
admin-triggered activity.
"""

import argparse
import logging
import time

import camera
import config


def _session():
    import requests

    headers = {"X-API-Key": config.API_KEY}
    resp = requests.get(config.ENROLL_PENDING_URL, headers=headers,
                        timeout=config.API_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()


def _submit_frame(image_base64: str) -> dict:
    import requests

    headers = {"X-API-Key": config.API_KEY}
    resp = requests.post(config.ENROLL_SUBMIT_URL,
                        json={"image_base64": image_base64}, headers=headers,
                        timeout=config.API_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()


def run_pending_scan() -> bool:
    """If a scan is pending, capture + submit frames until complete.
    Returns True if a scan was processed."""
    try:
        session = _session()
    except Exception:
        logging.exception("Could not reach the enrollment endpoint.")
        return False

    if not session.get("active"):
        return False

    name = session.get("name")
    needed = session.get("frames_needed", 1)
    logging.info("Enrolling '%s' — capturing %s frames.", name, needed)

    while True:
        image_base64 = camera.capture_image_base64()
        if not image_base64:
            logging.warning("Camera capture failed; retrying.")
            time.sleep(0.5)
            continue

        try:
            status = _submit_frame(image_base64)
        except Exception:
            logging.exception("Failed to submit an enrollment frame.")
            return False

        if "error" in status:
            logging.warning("Server rejected frame: %s", status["error"])
            time.sleep(0.5)
            continue

        logging.info("Captured %s/%s for '%s'.",
                     status.get("frames_collected"), status.get("frames_needed"), name)

        if status.get("status") == "complete":
            logging.info("Enrollment of '%s' complete.", name)
            return True

        time.sleep(0.4)  # brief pause so frames differ slightly


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="VisionGate camera-enrollment runner.")
    parser.add_argument("--watch", action="store_true",
                        help="Keep polling for pending scans instead of running once.")
    args = parser.parse_args()

    if not args.watch:
        if not run_pending_scan():
            logging.info("No pending enrollment scan.")
        return

    logging.info("Watching for enrollment scans. Ctrl+C to stop.")
    try:
        while True:
            if not run_pending_scan():
                time.sleep(2)
    except KeyboardInterrupt:
        logging.info("Enrollment runner stopped.")


if __name__ == "__main__":
    main()
