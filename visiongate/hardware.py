"""Simulated hardware interface for VisionGate.

Replace the logging calls in this file with real Raspberry Pi GPIO code later.
Keeping GPIO access behind these functions makes the rest of the application
easy to test on any computer.
"""

import logging
import time

import config


def setup_hardware() -> None:
    """Initialize GPIO pins, LEDs, buzzer, relay, and motion sensor later."""
    logging.info("Hardware setup complete (simulated).")


def cleanup_hardware() -> None:
    """Release GPIO resources later."""
    logging.info("Hardware cleanup complete (simulated).")


def show_idle_led() -> None:
    """Show the yellow idle LED behavior."""
    logging.info("Yellow LED on: waiting for motion (simulated).")


def wait_for_motion() -> bool:
    """Wait for PIR motion sensor input later.

    The simulated version always detects motion so the state machine can be
    tested immediately.
    """
    logging.info("Motion detected by simulated PIR sensor.")
    return True


def show_green_led() -> None:
    logging.info("Green LED on: access granted (simulated).")


def show_red_led() -> None:
    logging.info("Red LED on: access denied (simulated).")


def clear_leds() -> None:
    logging.info("All LEDs off (simulated).")


def beep_once() -> None:
    logging.info("Buzzer beep once (simulated).")


def triple_beep() -> None:
    logging.info("Buzzer triple beep (simulated).")


def unlock_relay() -> None:
    """Fire the door relay for a fixed unlock period."""
    logging.info("Relay unlocked for %s seconds (simulated).", config.RELAY_UNLOCK_SECONDS)
    time.sleep(config.RELAY_UNLOCK_SECONDS)
    logging.info("Relay locked again (simulated).")
