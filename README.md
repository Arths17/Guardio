# Guardio — Backend

<!-- cspell:ignore Guardio guardio devkey GUARDIO venv uvicorn wscat Cytoscape pytest -->

[![CI](https://github.com/Arths17/Guardio/actions/workflows/ci.yml/badge.svg)](https://github.com/Arths17/Guardio/actions/workflows/ci.yml)

This repository provides the backend for Guardio: a FastAPI-based, real-time
simulation and WebSocket service that emits network/attack events for a
visualization frontend. The backend is a self-contained prototype intended for
development, demos and education — it simulates network traffic and attacks,
supports basic defenses and detection, and persists replays to a local
SQLite database.

Key components

- `backend/main.py`: API and WebSocket entrypoints.
- `backend/simulation.py`: synthetic network + attack simulator (packet events,
- DDoS and malware scenarios).
- `backend/ws_manager.py`: WebSocket broadcasting for live clients.
- `backend/replay.py`: in-memory replay store (also persisted to SQLite).
- `backend/defense.py`: simple defense manager (firewall blocks, segments,
- honeypots).
- `backend/ids.py`: lightweight IDS scoring and alert generation.
- `backend/db.py`: SQLite persistence for replays and events (guardio.db).
- `backend/auth.py`: minimal API-key auth dependency (header `X-API-Key`).

What this backend provides

- Live event stream over WebSocket (`/ws`) with events such as `packet`,
- `attack`, `alert`, and `dropped`.
- REST control endpoints to start/stop the simulator and launch attacks.
- Simple defensive controls (block/unblock hosts) that affect simulation
- behavior in real time.
- Network segmentation and honeypot controls for containment-style demos.
- IDS alerts emitted when packets exceed a suspicion threshold.
- Replay saving (in-memory and optional persisted to `guardio.db`).
- Runtime status and metrics endpoints for live monitoring.

Secure endpoints

Most control endpoints require a header `X-API-Key`. The default development
key is `devkey`. Override with the `GUARDIO_API_KEY` environment variable in
production.

Important endpoints

- `GET /health` — health check.
- `GET /status` — simulation and defense snapshot.
- `GET /metrics` — telemetry and runtime counters.
- `POST /start` — start simulation (requires `X-API-Key`).
- `POST /stop` — stop simulation and save replay (requires `X-API-Key`).
- `POST /attack` — launch an attack, JSON body `{ "name": "ddos" }`
- (requires `X-API-Key`).
- `POST /defense/firewall/block` — block host, JSON `{ "host": "host-1" }`
- (requires `X-API-Key`).
- `POST /defense/firewall/unblock` — unblock host (requires `X-API-Key`).
- `POST /defense/segment` — create a segment, JSON `{ "name": "prod", "hosts": ["srv-1"] }`.
- `DELETE /defense/segment/{name}` — remove a segment.
- `POST /defense/honeypot` — add a honeypot host.
- `DELETE /defense/honeypot` — remove a honeypot host.
- `GET /defense/status` — view active blocks, segments and honeypots.
- `GET /replays` and `GET /replay/{id}` — list and fetch saved replays.
- `WebSocket /ws?api_key=devkey` — connect to receive live events (packets, alerts, state).

Quick start (local)

1. Create and activate a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. Start the server (development):

```bash
uvicorn backend.main:app --reload --port 8000
```

1. Example requests (use header `X-API-Key: devkey`):

```bash
# start simulation
curl -X POST -H "X-API-Key: devkey" http://127.0.0.1:8000/start

# block a host
curl -X POST -H "Content-Type: application/json" -H "X-API-Key: devkey" -d '{"host":"host-1"}' http://127.0.0.1:8000/defense/firewall/block

# connect to websocket (example with wscat)
wscat -c ws://127.0.0.1:8000/ws
```

Docker

Build and run the provided image:

```bash
docker build -t guardio-backend .
docker run -p 8000:8000 -e GUARDIO_API_KEY=yourkey guardio-backend
```

Testing and CI

- Unit tests are under `tests/` and run with `pytest`.
- A basic GitHub Actions workflow is included at
  `.github/workflows/ci.yml` that installs deps and runs tests.

Notes & next steps

- This backend is intentionally prototype-level: simulation is synthetic and
  randomized (no packet capture). For production you may want to add:
  persistent user accounts, stronger auth, async DB (SQLModel/SQLAlchemy),
  richer IDS rulesets, telemetry/metrics, and integration with a frontend
  visualization (Three.js / Cytoscape / WebGL).

Files to inspect

- [backend/main.py](backend/main.py)
- [backend/simulation.py](backend/simulation.py)
- [backend/defense.py](backend/defense.py)
- [backend/ids.py](backend/ids.py)
- [backend/db.py](backend/db.py)
- [backend/replay.py](backend/replay.py)
- [Dockerfile](Dockerfile)
- [requirements.txt](requirements.txt)
