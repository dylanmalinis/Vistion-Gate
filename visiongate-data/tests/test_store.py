"""Tests for the SQLite store: users, events, enrollment sessions, retention."""

import store


def test_user_roundtrip_preserves_encodings():
    store.add_user("Ali", [[0.1, 0.2], [0.3, 0.4]])
    users = store.get_users()
    assert len(users) == 1
    assert users[0]["name"] == "Ali"
    assert users[0]["encodings"] == [[0.1, 0.2], [0.3, 0.4]]


def test_remove_user():
    store.add_user("Ali", [[0.1]])
    assert store.remove_user("Ali") is True
    assert store.remove_user("Ali") is False
    assert store.get_users() == []


def test_events_and_stats():
    store.log_event(name="Ali", result="GRANTED", confidence=0.9, image_path=None)
    store.log_event(name="UNKNOWN", result="DENIED", confidence=0.3, image_path=None)
    store.log_event(name="UNKNOWN", result="DENIED", confidence=0.2, image_path=None)

    stats = store.get_stats()
    assert stats["total"] == 3
    assert stats["granted"] == 1
    assert stats["denied"] == 2
    assert stats["deny_rate"] == round(2 / 3, 3)

    recent = store.get_recent_events(limit=2)
    assert len(recent) == 2
    assert recent[0]["id"] > recent[1]["id"]  # newest first


def test_enrollment_session_lifecycle():
    store.start_enrollment("Bob", frames_needed=2)
    pending = store.get_active_enrollment()
    assert pending["name"] == "Bob"
    assert pending["frames_collected"] == 0

    s1 = store.add_enrollment_frame([0.1])
    assert s1["frames_collected"] == 1
    assert s1["status"] == "active"

    s2 = store.add_enrollment_frame([0.2])
    assert s2["status"] == "complete"

    # The user now exists with both encodings, and no session is active.
    users = {u["name"]: u for u in store.get_users()}
    assert "Bob" in users
    assert len(users["Bob"]["encodings"]) == 2
    assert store.get_active_enrollment() is None


def test_cancel_enrollment():
    store.start_enrollment("Carol", frames_needed=3)
    assert store.cancel_enrollment() is True
    assert store.get_active_enrollment() is None
    assert store.cancel_enrollment() is False


def test_purge_disabled_is_noop():
    store.log_event(name="Ali", result="GRANTED", confidence=0.9, image_path=None)
    assert store.purge_old_data(0) == 0
    assert store.get_stats()["total"] == 1
