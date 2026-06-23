# VisionGate Data / AI Layer (Role C)

The intelligence and observability half of VisionGate: the recognition API the
firmware calls, the SQLite event log, the live dashboard, the alerting system,
camera-based face enrollment, and admin auth.

> For the whole-project picture (all three layers, status, data flow), see the
> **[root README](../README.md)**. This file is the quick data-layer reference;
> for a full deep dive (flows, every table, diagrams) see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Like the firmware, this is **mock-first**: it runs end-to-end on a laptop with
no camera, no Pi, and no accounts. Config switches turn on the real backends.

## Layout

| File | Responsibility |
|---|---|
| `app.py` | Flask API + dashboard routes |
| `recognizer.py` | Pluggable matcher: `stub` (default) or `face_recognition` |
| `store.py` | SQLite: `users`, `access_events`, `enrollment_sessions` |
| `auth.py` | Admin session login + `X-API-Key` gate |
| `alerts.py` | Pluggable alerts: `console` (default) or `telegram` |
| `enroll.py` | File-based enrollment CLI |
| `serve.py` | Production server (waitress) |
| `config.py` | Thresholds, paths, secrets, backend switches |
| `templates/` | `dashboard.html`, `login.html` |
| `tests/` | pytest suite |

## Run

```bash
python -m pip install -r requirements.txt
python serve.py            # production (waitress); or: python app.py for dev
```

Open http://localhost:8000/ and log in. Demo credentials: **admin / visiongate**
(override with the `VISIONGATE_ADMIN_PASSWORD` env var).

```bash
python -m pytest -q        # run the tests
```

## Endpoints

**Machine (Pi) — require header `X-API-Key`:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/verify` (alias `/recognize`) | Check a face → `{result, name, confidence, event_id}` |
| GET | `/enroll/pending` | Is a camera scan waiting? |
| POST | `/enroll` | Submit one captured frame toward the active scan |

**Admin (browser) — require login:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Live dashboard |
| POST | `/enroll/start` `/enroll/cancel` | Begin / abort a camera scan |
| POST | `/users/delete` | Remove a registered user |
| GET | `/api/events` `/api/stats` `/api/users` `/api/enroll/status` | Dashboard data |

Open: `GET /health`.

**Grant policy:** GRANTED only when a registered face matches **and**
`confidence ≥ CONFIDENCE_THRESHOLD` (0.75). Otherwise DENIED + alert.

## Enrolling a face

**Camera scan (real flow):** on the dashboard, type a name → *Start camera
scan*. The Pi (`../visiongate/enroll_runner.py`) captures
`ENROLL_FRAMES_NEEDED` frames and the server registers the face.

**File (offline):**

```bash
python enroll.py --add "Ali" --image any-file.jpg
python enroll.py --list
python enroll.py --remove "Ali"
```

## Demo the deny/grant paths with the stub

In `config.py`, `STUB_RESULT`:
`"auto"` (hash-derived, default) · `"GRANTED"` · `"DENIED"` · `"<a name>"`.

## Secrets (override via env vars — never commit real values)

`VISIONGATE_API_KEY`, `VISIONGATE_ADMIN_PASSWORD`, `VISIONGATE_SECRET_KEY`,
`VISIONGATE_DB` (tests), `VISIONGATE_TELEGRAM_TOKEN`, `VISIONGATE_TELEGRAM_CHAT_ID`.

## Going to the real backends

- **Real faces (Pi):** uncomment `face_recognition`+`numpy` in
  `requirements.txt`, install, set `RECOGNIZER_BACKEND = "face_recognition"`,
  re-enroll with real photos.
- **Telegram alerts:** set `ALERT_BACKEND = "telegram"` + the token/chat env vars.
