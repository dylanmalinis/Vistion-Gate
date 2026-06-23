"""Client for the Computer Science recognition API."""

import logging
from typing import Any

import config


def verify_face(image_base64: str) -> bool:
    """Send an image to the recognition API.

    Returns True only when the API clearly grants access. Any timeout, request
    error, malformed response, or unexpected result returns False so the system
    defaults safely to DENY.
    """
    if config.MOCK_API:
        return _mock_verify_face()

    try:
        import requests
    except ImportError:
        logging.exception("The requests package is required when MOCK_API is False.")
        return False

    payload = {"image_base64": image_base64}
    headers = {"X-API-Key": config.API_KEY}

    try:
        response = requests.post(
            config.API_URL,
            json=payload,
            headers=headers,
            timeout=config.API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.Timeout:
        logging.warning("Recognition API timed out after %s seconds.", config.API_TIMEOUT_SECONDS)
        return False
    except requests.RequestException:
        logging.exception("Recognition API request failed.")
        return False
    except ValueError:
        logging.exception("Recognition API returned invalid JSON.")
        return False

    return _parse_api_response(data)


def _mock_verify_face() -> bool:
    result = config.MOCK_API_RESULT.upper()
    logging.info("MOCK_API enabled. Returning mock result: %s", result)
    return result == "GRANTED"


def _parse_api_response(data: dict[str, Any]) -> bool:
    """Parse expected API responses.

    Supported examples:
        {"result": "GRANTED"}
        {"access": "DENIED"}
        {"granted": true}
    """
    if not isinstance(data, dict):
        logging.warning("Recognition API response was not an object.")
        return False

    if isinstance(data.get("granted"), bool):
        return data["granted"]

    result = data.get("result", data.get("access"))
    if isinstance(result, str):
        normalized = result.upper()
        if normalized == "GRANTED":
            return True
        if normalized == "DENIED":
            return False

    logging.warning("Recognition API response did not include a clear grant/deny result: %s", data)
    return False
