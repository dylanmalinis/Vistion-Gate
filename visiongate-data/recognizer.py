"""Pluggable face-recognition engine.

Two backends share one interface so the rest of the system never changes:

    recognize(image_bytes)    -> RecognitionResult(name, confidence)
    make_encoding(image_bytes) -> list[float]   (one encoding, for enrollment)

- "stub": deterministic, no heavy dependencies. Good for laptop dev and demos.
- "face_recognition": real dlib-based matching against enrolled encodings.

Users may have several enrolled encodings; we match against the closest one.
Switch via config.RECOGNIZER_BACKEND.
"""

import hashlib
import logging
from dataclasses import dataclass

import config
import store

UNKNOWN = "UNKNOWN"


@dataclass
class RecognitionResult:
    name: str
    confidence: float


# --- Public entry points --------------------------------------------------

def recognize(image_bytes: bytes) -> RecognitionResult:
    if config.RECOGNIZER_BACKEND == "face_recognition":
        return _recognize_face_recognition(image_bytes)
    return _recognize_stub(image_bytes)


def make_encoding(image_bytes: bytes) -> list[float]:
    """Produce one encoding for enrollment using the active backend."""
    if config.RECOGNIZER_BACKEND == "face_recognition":
        return _encode_face_recognition(image_bytes)
    return _stub_signature(image_bytes)


# --- Stub backend ---------------------------------------------------------

def _stub_signature(image_bytes: bytes) -> list[float]:
    """A tiny deterministic 'encoding': 8 floats derived from the bytes hash."""
    digest = hashlib.sha256(image_bytes).digest()
    return [b / 255.0 for b in digest[:8]]


def _recognize_stub(image_bytes: bytes) -> RecognitionResult:
    users = store.get_users()
    forced = config.STUB_RESULT

    if forced == "GRANTED":
        name = users[0]["name"] if users else "Demo User"
        return RecognitionResult(name, 0.95)
    if forced == "DENIED":
        return RecognitionResult(UNKNOWN, 0.30)
    if forced != "auto":
        # Treat any other value as an explicit name to return.
        return RecognitionResult(forced, 0.95)

    # auto: deterministically derive a result from the image bytes.
    if not users:
        return RecognitionResult(UNKNOWN, 0.40)

    digest = hashlib.sha256(image_bytes).digest()
    # Use the first byte to decide match vs. stranger, the second to pick a user.
    if digest[0] < 200:  # ~78% of the byte space => a registered user
        user = users[digest[1] % len(users)]
        confidence = 0.78 + (digest[2] / 255.0) * 0.21  # 0.78 .. 0.99
        return RecognitionResult(user["name"], round(confidence, 3))

    confidence = 0.20 + (digest[2] / 255.0) * 0.30  # 0.20 .. 0.50
    return RecognitionResult(UNKNOWN, round(confidence, 3))


# --- Real face_recognition backend ---------------------------------------

def _load_face_recognition():
    try:
        import face_recognition  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        logging.exception(
            "RECOGNIZER_BACKEND='face_recognition' but the library is not "
            "installed. Install it on the Pi or switch back to 'stub'."
        )
        raise
    return face_recognition, np


def _encode_face_recognition(image_bytes: bytes) -> list[float]:
    import io

    face_recognition, _ = _load_face_recognition()
    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        raise ValueError("No face found in the supplied image.")
    return encodings[0].tolist()


def _recognize_face_recognition(image_bytes: bytes) -> RecognitionResult:
    import io

    face_recognition, np = _load_face_recognition()

    users = store.get_users()
    if not users:
        return RecognitionResult(UNKNOWN, 0.0)

    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        return RecognitionResult(UNKNOWN, 0.0)

    probe = encodings[0]

    # Flatten every user's encodings, remembering which user each belongs to.
    known: list = []
    owners: list[str] = []
    for u in users:
        for enc in u["encodings"]:
            known.append(np.array(enc))
            owners.append(u["name"])

    if not known:
        return RecognitionResult(UNKNOWN, 0.0)

    distances = face_recognition.face_distance(known, probe)
    best_idx = int(np.argmin(distances))
    best_distance = float(distances[best_idx])
    # Map distance -> a 0..1 confidence (distance 0 => 1.0, tolerance => ~0).
    confidence = max(0.0, 1.0 - best_distance / config.FACE_MATCH_TOLERANCE)

    if best_distance <= config.FACE_MATCH_TOLERANCE:
        return RecognitionResult(owners[best_idx], round(confidence, 3))
    return RecognitionResult(UNKNOWN, round(confidence, 3))
