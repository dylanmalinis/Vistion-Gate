"""Main VisionGate Raspberry Pi control program."""

import logging
import time
from enum import Enum, auto

import api_client
import camera
import config
import hardware
import rfid


class State(Enum):
    IDLE = auto()
    CAPTURE = auto()
    VERIFY = auto()
    SECOND_FACTOR = auto()
    GRANT = auto()
    DENY = auto()
    FALLBACK = auto()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def run_state_machine() -> None:
    state = State.IDLE
    image_base64: str | None = None
    cycles_completed = 0

    hardware.setup_hardware()

    try:
        while config.MAX_CYCLES is None or cycles_completed < config.MAX_CYCLES:
            logging.info("Current state: %s", state.name)

            if state == State.IDLE:
                hardware.show_idle_led()
                if hardware.wait_for_motion():
                    state = State.CAPTURE
                else:
                    time.sleep(0.2)

            elif state == State.CAPTURE:
                image_base64 = camera.capture_image_base64()
                if image_base64:
                    state = State.VERIFY
                elif config.RFID_ENABLED:
                    logging.warning("Camera failed. Moving to RFID fallback.")
                    state = State.FALLBACK
                else:
                    logging.warning("Camera failed and RFID is disabled. Denying access.")
                    state = State.DENY

            elif state == State.VERIFY:
                if image_base64 is None:
                    logging.warning("No image available for verification. Denying access.")
                    state = State.DENY
                    continue

                access_granted = api_client.verify_face(image_base64)
                if not access_granted:
                    state = State.DENY
                elif config.REQUIRE_SECOND_FACTOR:
                    # Face passed, but require a whitelisted RFID tap before
                    # unlocking. Defends against face-spoofing (e.g. a photo).
                    logging.info("Face granted. Awaiting second factor (RFID).")
                    state = State.SECOND_FACTOR
                else:
                    state = State.GRANT

            elif state == State.SECOND_FACTOR:
                card_id = rfid.read_card_id()
                if rfid.is_card_whitelisted(card_id):
                    state = State.GRANT
                else:
                    logging.warning("Second factor failed. Denying access.")
                    state = State.DENY

            elif state == State.GRANT:
                hardware.show_green_led()
                hardware.beep_once()
                hardware.unlock_relay()
                hardware.clear_leds()
                image_base64 = None
                cycles_completed += 1
                state = State.IDLE

            elif state == State.DENY:
                hardware.show_red_led()
                hardware.triple_beep()
                time.sleep(config.DENY_LED_SECONDS)
                hardware.clear_leds()
                image_base64 = None
                cycles_completed += 1
                state = State.IDLE

            elif state == State.FALLBACK:
                card_id = rfid.read_card_id()
                access_granted = rfid.is_card_whitelisted(card_id)
                state = State.GRANT if access_granted else State.DENY

    except KeyboardInterrupt:
        logging.info("VisionGate stopped by user.")
    finally:
        hardware.cleanup_hardware()


def main() -> None:
    configure_logging()
    logging.info("Starting VisionGate controller.")
    run_state_machine()
    logging.info("VisionGate controller stopped.")


if __name__ == "__main__":
    main()
