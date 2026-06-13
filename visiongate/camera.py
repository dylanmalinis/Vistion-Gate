"""Camera capture interface for VisionGate."""

import base64
import logging


def capture_image_base64() -> str | None:
    """Capture a JPEG image and return it as a base64 string.

    Replace this fake implementation with Raspberry Pi camera code later.
    Return None if capture fails so the caller can fail safely.
    """
    try:
        fake_jpeg_bytes = b"fake-jpeg-image-for-visiongate-test"
        image_base64 = base64.b64encode(fake_jpeg_bytes).decode("utf-8")
        logging.info("Captured fake camera image.")
        return image_base64
    except Exception:
        logging.exception("Camera capture failed.")
        return None
