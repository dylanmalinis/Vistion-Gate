"""RFID fallback interface for VisionGate."""

import logging
import time

import config


def read_card_id() -> str | None:
    """Read an RFID card ID later.

    The simulated version returns a known card after a short delay.
    Return None when no card is found or the reader fails.
    """
    logging.info("Waiting for RFID card (simulated).")
    time.sleep(config.FALLBACK_WAIT_SECONDS)
    return "CARD-1234"


def is_card_whitelisted(card_id: str | None) -> bool:
    if not card_id:
        logging.warning("No RFID card ID was read.")
        return False

    allowed = card_id in config.RFID_WHITELIST
    logging.info("RFID card %s whitelist result: %s", card_id, allowed)
    return allowed
