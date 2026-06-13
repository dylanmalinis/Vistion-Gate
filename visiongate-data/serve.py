"""Production entry point for the VisionGate data layer.

Runs the Flask app under Waitress, a real WSGI server, instead of Flask's
built-in development server (which prints a "do not use in production" warning).

    python serve.py

Configure host/port in config.py.
"""

import logging

from waitress import serve

import config
from app import app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("VisionGate data layer (PROD/waitress) on http://%s:%s "
                 "(recognizer=%s, alerts=%s)", config.HOST, config.PORT,
                 config.RECOGNIZER_BACKEND, config.ALERT_BACKEND)
    serve(app, host=config.HOST, port=config.PORT)
