# VisionGate — Team TODO

What's left, grouped by who owns it. The data/AI layer is largely built; the
remaining work is mostly **on the real Raspberry Pi hardware** plus a few
polish items. Check items off as you go.

> Legend: 🔴 blocker / must-do · 🟡 important · 🟢 nice-to-have

---

## EE / ECE — Hardware

The transistor + relay driver is already simulated (LTSpice). Now make it real.

- [ ] 🔴 Confirm and order all parts from the BOM (see root README §9)
- [ ] 🔴 Build the regulated **5V power rail** for the Pi + peripherals
- [ ] 🔴 Build the **transistor → relay** driver on a breadboard (with the flyback diode)
- [ ] 🔴 Wire the **3 LEDs** (green / red / yellow) with current-limiting resistors
- [ ] 🟡 Wire the **active buzzer**
- [ ] 🔴 Connect the **Pi Camera v2** to the CSI ribbon connector
- [ ] 🟡 Wire the **RC522 RFID** reader (SPI pins)
- [ ] 🟡 Wire the **PIR motion sensor**
- [ ] 🔴 Hand CE a **pinout / wiring table** (which GPIO drives what)
- [ ] 🟡 Test relay switching with CE's GPIO test script (fires < 50 ms)
- [ ] 🟢 Simulate the door strike with an LED load before using the real solenoid
- [ ] 🟡 Stress-test the supply under full load (Pi + relay + LEDs + buzzer)
- [ ] 🟢 Finalize the clean schematic (KiCad) + BOM with part numbers/costs
- [ ] 🟢 Record the hardware demo clip

---

## CE — Firmware (Raspberry Pi)

The state machine, API client, RFID, and camera-enroll runner are written and
tested in **simulated** mode. Now connect the real hardware.

- [ ] 🔴 Replace simulated `hardware.py` with real GPIO code (LEDs, relay, buzzer, PIR) — `gpiozero` / `RPi.GPIO`
- [ ] 🔴 Replace simulated `camera.py` with real Pi camera capture (`picamera2`) → JPEG → base64
- [ ] 🟡 Replace simulated `rfid.py` with real RC522 reads (`mfrc522`) and load the real card whitelist
- [ ] 🔴 In `config.py`: set `MOCK_API = False`, point `API_URL` at the data server's address, set the matching `API_KEY`
- [ ] 🔴 Confirm the **relay fires within 200 ms** of a GRANTED response; API timeout (>5 s) defaults to DENY
- [ ] 🟡 Run `enroll_runner.py` on the Pi (on demand, or as a small service) so dashboard scans capture frames
- [ ] 🟢 Decide whether to enable `REQUIRE_SECOND_FACTOR` (face **and** RFID to unlock)
- [ ] 🟡 Write a **systemd service** so VisionGate auto-starts on boot and auto-restarts on crash
- [ ] 🟡 Fill in the firmware README pinout table + setup steps
- [ ] 🔴 Full end-to-end test on hardware: motion → capture → verify → relay → log
- [ ] 🟢 Record the firmware demo clip

---

## CS — AI & Data

Mostly done and tested. Remaining work is turning on real recognition and
locking down the deployment.

- [ ] 🔴 Install `face_recognition` + `numpy` (on the Pi or a host), set `RECOGNIZER_BACKEND = "face_recognition"`
- [ ] 🔴 Re-enroll the team with **real face scans** (camera) and delete the stub test users
- [ ] 🔴 Validate the model: **≥ 85% accuracy** and **≤ 3 s** latency on the Pi 4 *(biggest project risk — test early)*
- [ ] 🔴 Set real secrets in a `.env` file (API key, admin password, secret key) — see "Keep Private" below
- [ ] 🟡 Tune `CONFIDENCE_THRESHOLD` on real captures
- [ ] 🟡 Decide where the data server runs (the Pi itself, or a laptop/server on the same network) and that the Pi can reach it
- [ ] 🟢 (Optional) Wire **Telegram alerts**: create a bot via BotFather, set token + chat id, `ALERT_BACKEND = "telegram"`
- [ ] 🟢 Set the capture **retention** window and decide `STORE_UNKNOWN_CAPTURES` for privacy
- [ ] 🟢 Show capture thumbnails on the dashboard (nice-to-have)
- [ ] 🟢 Record the data/dashboard demo clip

---

## Shared / Integration

- [ ] 🔴 Agree on the **data server address** (IP/port) all three layers use
- [ ] 🔴 One full integration run with all three layers connected
- [ ] 🟢 Assemble the final demo video

---

## 🔒 Keep Private — do NOT make these public

This repo is fine to **share publicly so others can try the project** — the
*code* is not secret. What must stay private are the **secrets** (passwords/keys)
and the **personal data** (people's faces and logs). None of these are in git
(they're git-ignored or read from a `.env` file), so they stay on your machine.

**Before you share or push, make sure these are NOT committed:**

1. **`visiongate-data/.env`** — your real API key, admin password, session
   secret, and Telegram token. (Git-ignored. Copy `.env.example` → `.env` and
   fill it in. Never put real values directly in `config.py`.)
2. **`visiongate-data/visiongate.db`** — the database of **enrolled faces**.
   These are biometric data of real people — treat them like passwords.
   (Git-ignored.)
3. **`visiongate-data/captures/`** — saved **photos** of everyone who triggered
   the camera. (Git-ignored.)
4. **`visiongate-data/alerts.log`** — record of denied attempts. (Git-ignored.)
5. **Anything tied to your Pi/network** — Wi-Fi passwords, SSH keys, the Pi's
   real IP address, your Telegram chat id. Don't paste these into code or docs.

**Why people can still "try it out" safely:** they clone the repo, copy
`.env.example` to their own `.env`, set *their own* password and API key, and
enroll *their own* faces. They never get your secrets or your face database —
those never left your computer. If you ever expose the server to the open
internet (instead of a private/home network), the admin login + API key are
what stop strangers from reaching your dashboard or spoofing the door, so keep
those strong.
