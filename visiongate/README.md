# VisionGate Raspberry Pi Controller

This is the first clean, testable version of the VisionGate firmware/control
layer. It uses a state machine and simulated hardware so the project can be run
on a laptop before connecting real Raspberry Pi GPIO, camera, relay, buzzer,
LEDs, motion sensor, and RFID hardware.

## State Machine

- `IDLE`: show yellow LED behavior and wait for motion.
- `CAPTURE`: capture a camera image.
- `VERIFY`: send a base64 JPEG image to the recognition API.
- `GRANT`: unlock relay for 3 seconds, show green LED, beep once, then return to `IDLE`.
- `DENY`: show red LED, triple beep, then return to `IDLE`.
- `FALLBACK`: read an RFID card and check a local whitelist.

API calls use a 5 second timeout and default safely to `DENY` if anything fails.

## Run the Test Version

From this directory:

```bash
python3 main.py
```

If `requests` is not installed:

```bash
python3 -m pip install -r requirements.txt
```

## Mock API Mode

The program starts with mock API mode enabled in `config.py`:

```python
MOCK_API = True
MOCK_API_RESULT = "GRANTED"
```

Change `MOCK_API_RESULT` to `"DENIED"` to test the deny path without the CS
recognition API.

When the real API is ready, set:

```python
MOCK_API = False
API_URL = "http://your-api-host/verify"
```

Expected API responses can use one of these simple formats:

```json
{"result": "GRANTED"}
{"access": "DENIED"}
{"granted": true}
```

## Where Real Hardware Code Goes

- `hardware.py`: Raspberry Pi GPIO setup, LEDs, relay, buzzer, and motion sensor.
- `camera.py`: Raspberry Pi camera capture and JPEG base64 encoding.
- `rfid.py`: RFID reader integration and card ID parsing.
- `api_client.py`: already contains the real `requests.post` structure.
