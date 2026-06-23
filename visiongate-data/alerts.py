"""Pluggable alerting for DENIED / UNKNOWN access attempts.

    send_alert(event) -> None

- "console": log to stdout and append to alerts.log. No accounts or secrets.
- "telegram": POST to the Telegram Bot API (set token + chat id in config).

Switch via config.ALERT_BACKEND. Alerting never raises: a failed alert must
not break the verification response.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import config


def send_alert(event: dict[str, Any]) -> None:
    """Fire an alert for a single denied/unknown event."""
    message = _format_message(event)
    try:
        if config.ALERT_BACKEND == "telegram":
            _send_telegram(message)
        else:
            _send_console(message)
    except Exception:
        logging.exception("Alert delivery failed (backend=%s).", config.ALERT_BACKEND)


def _format_message(event: dict[str, Any]) -> str:
    return (
        "VisionGate ALERT\n"
        f"Result: {event.get('result')}\n"
        f"Name: {event.get('name')}\n"
        f"Confidence: {event.get('confidence')}\n"
        f"Event ID: {event.get('event_id')}\n"
        f"Time: {event.get('timestamp')}"
    )


def _send_console(message: str) -> None:
    logging.warning("ALERT FIRED:\n%s", message)
    stamp = datetime.now(timezone.utc).isoformat()
    with open(config.ALERT_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}]\n{message}\n\n")


def _send_telegram(message: str) -> None:
    import requests

    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logging.error("Telegram alert backend selected but token/chat id are unset.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": config.TELEGRAM_CHAT_ID, "text": message},
        timeout=5,
    )
    resp.raise_for_status()
    logging.info("Telegram alert sent.")
