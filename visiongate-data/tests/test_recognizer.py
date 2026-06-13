"""Tests for the recognition engine (stub backend)."""

import config
import recognizer
import store


def test_make_encoding_is_deterministic():
    a = recognizer.make_encoding(b"same-frame")
    b = recognizer.make_encoding(b"same-frame")
    assert a == b
    assert len(a) == 8


def test_forced_granted(monkeypatch):
    monkeypatch.setattr(config, "STUB_RESULT", "GRANTED")
    store.add_user("Ali", [recognizer.make_encoding(b"x")])
    result = recognizer.recognize(b"anything")
    assert result.name == "Ali"
    assert result.confidence >= config.CONFIDENCE_THRESHOLD


def test_forced_denied(monkeypatch):
    monkeypatch.setattr(config, "STUB_RESULT", "DENIED")
    result = recognizer.recognize(b"anything")
    assert result.name == recognizer.UNKNOWN
    assert result.confidence < config.CONFIDENCE_THRESHOLD


def test_auto_with_no_users_is_unknown(monkeypatch):
    monkeypatch.setattr(config, "STUB_RESULT", "auto")
    result = recognizer.recognize(b"no-users-enrolled")
    assert result.name == recognizer.UNKNOWN
