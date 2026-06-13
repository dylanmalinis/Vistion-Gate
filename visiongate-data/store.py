"""SQLite-backed storage for VisionGate.

Tables:
  users               - one row per enrolled person (name + one or more face encodings).
  access_events       - one row per verification attempt (the audit log).
  enrollment_sessions - in-progress camera scans (accumulating frames).

Encodings are stored as a JSON list of encodings (each encoding is itself a
list of floats), so a user can hold several samples for more robust matching.
The same schema works for the stub backend (short numeric signatures) and the
real face_recognition backend (128-d encodings).
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import config


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not already exist. Safe to call repeatedly."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                encodings  TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                name       TEXT NOT NULL,
                result     TEXT NOT NULL,
                confidence REAL NOT NULL,
                image_path TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS enrollment_sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                frames_needed INTEGER NOT NULL,
                encodings     TEXT NOT NULL,
                status        TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )


# --- Users ----------------------------------------------------------------

def add_user(name: str, encodings: list[list[float]]) -> int:
    """Insert or replace a registered user with one or more encodings."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (name, encodings, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                encodings = excluded.encodings,
                created_at = excluded.created_at
            """,
            (name, json.dumps(encodings), now),
        )
        return cur.lastrowid


def remove_user(name: str) -> bool:
    """Delete a user by name. Returns True if a row was removed."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE name = ?", (name,))
        return cur.rowcount > 0


def get_users() -> list[dict[str, Any]]:
    """Return all registered users with decoded encodings (list of encodings)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, encodings, created_at FROM users ORDER BY name"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "encodings": json.loads(r["encodings"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# --- Access events --------------------------------------------------------

def log_event(
    *,
    name: str,
    result: str,
    confidence: float,
    image_path: str | None,
    timestamp: str | None = None,
) -> int:
    """Record one verification attempt. Returns the new event id."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO access_events (timestamp, name, result, confidence, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, name, result, float(confidence), image_path),
        )
        return cur.lastrowid


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent events, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp, name, result, confidence, image_path
            FROM access_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict[str, Any]:
    """Aggregate counts for the dashboard KPI cards."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(result = 'GRANTED'), 0) AS granted,
                COALESCE(SUM(result = 'DENIED'), 0)  AS denied
            FROM access_events
            """
        ).fetchone()
    total = row["total"] or 0
    denied = row["denied"] or 0
    deny_rate = (denied / total) if total else 0.0
    return {
        "total": total,
        "granted": row["granted"] or 0,
        "denied": denied,
        "deny_rate": round(deny_rate, 3),
        "registered_users": len(get_users()),
    }


# --- Enrollment sessions --------------------------------------------------

def start_enrollment(name: str, frames_needed: int) -> int:
    """Begin a scan enrollment. Cancels any other active session first."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("UPDATE enrollment_sessions SET status = 'cancelled' WHERE status = 'active'")
        cur = conn.execute(
            """
            INSERT INTO enrollment_sessions (name, frames_needed, encodings, status, created_at)
            VALUES (?, ?, '[]', 'active', ?)
            """,
            (name, frames_needed, now),
        )
        return cur.lastrowid


def get_active_enrollment() -> dict[str, Any] | None:
    """Return the active enrollment session, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM enrollment_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    encodings = json.loads(row["encodings"])
    return {
        "id": row["id"],
        "name": row["name"],
        "frames_needed": row["frames_needed"],
        "frames_collected": len(encodings),
        "status": row["status"],
    }


def add_enrollment_frame(encoding: list[float]) -> dict[str, Any] | None:
    """Append one encoding to the active session. When enough frames are
    collected, finalize: create the user and mark the session complete.

    Returns the updated session summary, or None if there is no active session.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM enrollment_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None

        encodings = json.loads(row["encodings"])
        encodings.append(encoding)

        if len(encodings) >= row["frames_needed"]:
            add_user(row["name"], encodings)
            conn.execute(
                "UPDATE enrollment_sessions SET encodings = ?, status = 'complete' WHERE id = ?",
                (json.dumps(encodings), row["id"]),
            )
            status = "complete"
        else:
            conn.execute(
                "UPDATE enrollment_sessions SET encodings = ? WHERE id = ?",
                (json.dumps(encodings), row["id"]),
            )
            status = "active"

    return {
        "id": row["id"],
        "name": row["name"],
        "frames_needed": row["frames_needed"],
        "frames_collected": len(encodings),
        "status": status,
    }


def cancel_enrollment() -> bool:
    """Cancel the active enrollment session. Returns True if one was active."""
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE enrollment_sessions SET status = 'cancelled' WHERE status = 'active'"
        )
        return cur.rowcount > 0


# --- Retention / privacy --------------------------------------------------

def purge_old_data(retention_days: int) -> int:
    """Delete events (and their capture files) older than retention_days.
    Returns the number of events removed. No-op when retention_days <= 0.
    """
    if retention_days <= 0:
        return 0

    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    with _connect() as conn:
        old = conn.execute(
            "SELECT id, image_path FROM access_events WHERE timestamp < ?", (cutoff,)
        ).fetchall()
        for row in old:
            if row["image_path"]:
                path = os.path.join(config.BASE_DIR, row["image_path"])
                try:
                    os.remove(path)
                except OSError:
                    pass
        conn.execute("DELETE FROM access_events WHERE timestamp < ?", (cutoff,))

    # Also sweep any orphaned capture files past the cutoff age.
    _purge_old_files(retention_days)
    return len(old)


def _purge_old_files(retention_days: int) -> None:
    if not os.path.isdir(config.IMAGE_DIR):
        return
    cutoff_ts = time.time() - retention_days * 86400
    for fname in os.listdir(config.IMAGE_DIR):
        fpath = os.path.join(config.IMAGE_DIR, fname)
        try:
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff_ts:
                os.remove(fpath)
        except OSError:
            pass
