# VisionGate

**A wall-mounted smart access-control device that uses a camera and AI face
recognition to decide who may enter a space.** It physically controls a door
lock, logs every access attempt, alerts admins on unknown faces, and needs no
keys, cards, or PINs.

This single README is the project's front door: what VisionGate is, how the
pieces fit, **where we are right now**, and **how to run everything**. It
combines the original product requirements with the current state of the code.

---

## 1. The idea

Keys and access cards are expensive, easy to lose or copy, and hard to audit.
VisionGate is a low-cost alternative built on a Raspberry Pi: a person walks
up, the camera captures their face, an AI service decides GRANTED or DENIED,
the door reacts, and every attempt is logged to a live dashboard with an alert
on anyone unrecognized. Total hardware cost target: **under $80**.

---

## 2. How it works (data flow)

```
Person approaches
      │
      ▼
[EE/ECE]  motion sensor + camera capture a frame
      │   (Raspberry Pi hardware)
      ▼
[CE]      firmware encodes the frame and POSTs it to the data API
      │   (state machine: IDLE → CAPTURE → VERIFY → GRANT/DENY)
      ▼
[CS]      data server runs face recognition, applies the confidence
      │   threshold, logs the event, and replies GRANTED / DENIED
      ▼
[CE]      firmware fires the relay (unlock) + LEDs + buzzer
      ▼
[CS]      dashboard updates live; an alert fires if DENIED / UNKNOWN
```

The system is three layers with **one frozen contract** between firmware and
data (see [§7](#7-the-api-contract)).

---

## 3. The three layers (who owns what)

| Layer | Owner | Responsibility | Folder |
|---|---|---|---|
| **Hardware** | EE / ECE | Power, relay/transistor switching, LEDs, buzzer, camera wiring | *(schematic / BOM — see §8)* |
| **Firmware** | CE | The Raspberry Pi brain: state machine, GPIO, camera, API client, RFID | [`visiongate/`](visiongate/) |
| **AI & Data** | CS | Recognition API, database, dashboard, alerts, enrollment | [`visiongate-data/`](visiongate-data/) |

Each layer runs **mock-first** so it can be developed and demoed on a laptop
before the real Raspberry Pi, camera, and door hardware are connected.

---

## 4. Where we are right now

| Capability | Status |
|---|---|
| Firmware state machine (IDLE→CAPTURE→VERIFY→GRANT/DENY/FALLBACK) | DONE Built, runs on laptop (simulated hardware) |
| RFID fallback authentication | DONE Built (simulated) |
| Data API (`/verify`, `/recognize`) | DONE Built, matches the firmware contract |
| Face recognition | DONE Pluggable — stub backend runs now; real `face_recognition` ready for the Pi |
| SQLite event log + stats | DONE Built |
| Live web dashboard | DONE Built (auto-refreshing, off-white theme) |
| DENIED/UNKNOWN alerts | DONE Pluggable — console/file now, Telegram ready |
| Face enrollment from the **camera** (not a file) | DONE Built — admin starts a scan, the Pi captures frames |
| **Admin login** on the dashboard | DONE Built (session login) |
| **API key** between Pi and server | DONE Built (shared `X-API-Key`) |
| **Optional face + RFID two-factor** unlock | DONE Built (off by default) |
| **Capture retention + privacy** controls | DONE Built |
| Automated tests | DONE 21 passing (`pytest`) |
| Production server | DONE Waitress (`serve.py`) |
| Real camera / GPIO / dlib on the Pi | ⏳ Pending — the hardware-dependent step |

> The biggest remaining risk is **real face recognition on the Pi within the
> latency budget** (dlib install + speed). Everything else is proven on a
> laptop; that one needs the actual board.

---

## 5. What changed / was added most recently

This branch added the "make it real" layer on top of the working prototype:

1. **Camera-based enrollment.** You no longer enroll from an image file. An
   admin clicks *Start camera scan* on the dashboard, names the person, and the
   Pi captures several frames and registers the face. Users can now hold
   multiple face samples for more robust matching.
   - Data side: `POST /enroll/start`, `GET /enroll/pending`, `POST /enroll`, `POST /enroll/cancel`.
   - Firmware side: [`visiongate/enroll_runner.py`](visiongate/enroll_runner.py).
2. **Admin login** on the dashboard — it's now a protected control surface, not
   an open page.
3. **Shared API key** so only the real Pi (not anyone on the network) can call
   `/verify` and the enrollment endpoints.
4. **Optional two-factor unlock** (face *and* a whitelisted RFID tap) to defend
   against face spoofing. Off by default; flip `REQUIRE_SECOND_FACTOR`.
5. **Privacy & retention** — old captures/events are purged after N days, and
   you can choose not to store photos of strangers at all.
6. **Tests** (`pytest`) covering the recognizer policy, the store, and the API
   auth/contract.
7. **Production server** via Waitress, instead of Flask's dev server.

---

## 6. How to run it (laptop, no hardware needed)

### A. Start the data layer (CS)

```bash
cd visiongate-data
python -m pip install -r requirements.txt

python serve.py          # production server (recommended)
#   or: python app.py    # Flask dev server
```

Open **http://localhost:8000/** and log in.
Default credentials (CHANGE THESE — see §9): **admin / visiongate**

### B. Enroll a face

**From the dashboard (camera scan):** type a name, click *Start camera scan*,
then run the Pi-side runner so it captures frames:

```bash
cd visiongate
python enroll_runner.py        # captures frames for the pending scan
```

**Or from a file (offline / no camera):**

```bash
cd visiongate-data
python enroll.py --add "Ali" --image any-file.jpg
python enroll.py --list
```

### C. Run the firmware (CE)

```bash
cd visiongate
python main.py
```

By default the firmware uses `MOCK_API = True` (no server needed). To talk to
the real data API, set `MOCK_API = False` in [`visiongate/config.py`](visiongate/config.py)
(it already points at `http://localhost:8000/verify` and sends the API key).

### D. Run the tests

```bash
cd visiongate-data
python -m pytest -q
```

---

## 7. The API contract

The firmware POSTs to **`/verify`** with header `X-API-Key`:

```json
// request
{ "image_base64": "<base64 JPEG>", "timestamp": "<ISO-8601, optional>" }

// response
{ "result": "GRANTED", "name": "Ali", "confidence": 0.91, "event_id": 42 }
```

- `result` is `GRANTED` or `DENIED` — the firmware only needs this field.
- `/recognize` is an alias of `/verify`; `image_b64` is accepted too.
- **Grant policy:** GRANTED only when a registered face matches **and**
  `confidence ≥ 0.75`. Everything else is DENIED and fires an alert.

---

## 8. Configuration & security (read before any real deployment)

All secrets read from environment variables so nothing sensitive is committed.
The defaults are for laptop demos only — **change them for anything real:**

| Setting | Env var | Default (demo) |
|---|---|---|
| Data ↔ Pi shared key | `VISIONGATE_API_KEY` | `visiongate-dev-key` |
| Dashboard password | `VISIONGATE_ADMIN_PASSWORD` | `visiongate` |
| Session signing key | `VISIONGATE_SECRET_KEY` | `dev-secret-change-me` |

Other knobs live in [`visiongate-data/config.py`](visiongate-data/config.py):
recognizer backend, confidence threshold, enrollment frame count, capture
retention days, whether to store unknown faces, and the alert backend.

**Honest security note:** basic face recognition can be fooled by a printed
photo or a phone screen. For a real door, either add liveness detection or
require the **two-factor** (face + RFID) mode. We ship it off by default but
built in — see `REQUIRE_SECOND_FACTOR` in [`visiongate/config.py`](visiongate/config.py).

### Going to real hardware

- **Real faces (Pi):** uncomment `face_recognition` + `numpy` in
  [`visiongate-data/requirements.txt`](visiongate-data/requirements.txt),
  install them, set `RECOGNIZER_BACKEND = "face_recognition"`, and re-enroll
  with real face photos.
- **Telegram alerts:** set `ALERT_BACKEND = "telegram"` plus the token/chat env vars.

---

## 9. Hardware bill of materials (target ~$84)

| Component | Est. cost |
|---|---|
| Raspberry Pi 4 (2GB) | $35 |
| Pi Camera Module v2 | $15 |
| 5V relay module | $5 |
| Door strike solenoid (12V) or sim load | $12 |
| RC522 RFID reader + cards | $5 |
| NPN transistors + resistors + diodes | $3 |
| LEDs + buzzer | $4 |
| Breadboard + jumper wires | $5 |

---

## 10. Repo map

```
visiongate/            Firmware (CE) — Raspberry Pi controller
  main.py              State machine (now with optional 2-factor)
  api_client.py        Calls the data API (sends X-API-Key)
  enroll_runner.py     Camera-enrollment runner (NEW)
  camera.py rfid.py hardware.py config.py

visiongate-data/       AI & data layer (CS)
  app.py               Flask API + dashboard (auth, enrollment, retention)
  recognizer.py        Pluggable face matcher (stub / face_recognition)
  store.py             SQLite: users, events, enrollment sessions
  auth.py              Login + API-key gates (NEW)
  alerts.py            Pluggable alerts (console / telegram)
  enroll.py            File-based enrollment CLI
  serve.py             Production server (waitress) (NEW)
  templates/           dashboard.html, login.html
  tests/               pytest suite (NEW)

README.md              ← you are here
```
