# Guardio

<!-- cspell:ignore Guardio guardio devkey uvicorn wscat pytest venv GUARDIO -->

[![CI](https://github.com/Arths17/Guardio/actions/workflows/ci.yml/badge.svg)](https://github.com/Arths17/Guardio/actions/workflows/ci.yml)

Real-time cyberattack visualization and infrastructure defense platform. Stream live attack simulations across a world map, inspect 108 geo-tagged infrastructure nodes, and follow attack propagation through an interactive force graph — all in a dark, operational SOC-style interface.

---

## Quick start

No API keys required. The backend defaults to `devkey` and AI features degrade gracefully without a Gemini key.

> **All `make` commands must be run from the project root** (`Guardio/`), not from `frontend/`.

### 1 — Install dependencies

```bash
cd Guardio
make install
```

Or without `make`:

```bash
cd Guardio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2 — Start the backend

In terminal 1, from the project root:

```bash
make dev-backend
```

Equivalent manual command:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 3 — Start the frontend

In terminal 2, from the project root:

```bash
make dev-frontend
```

Equivalent manual command:

```bash
cd frontend && npm run dev
```

Frontend runs at `http://localhost:3000`.

### 4 — Use it

1. Open `http://localhost:3000`
2. Click **START SIM** in the top bar — the world map fills with live packet arcs and node state changes
3. Launch a named attack from the top bar: **DDOS**, **MALWARE**, **RANSOMWARE**, **PHISHING**, **BOTNET**, or **APT**
4. Navigate views with the left icon rail:
   - **Threat Map** — world map with animated attack arcs, node pulses, click any node for details
   - **Infra Graph** — force-directed graph of all 108 nodes grouped by security zone
   - **Timeline** — expandable incident log with forensic detail and MITRE ATT&CK phases
   - **Intelligence** — protocol breakdown, IDS alert table, attack summary, defense action log
   - **AI Copilot** — query the AI assistant about your current threat posture

---

## Configuration

No configuration is required to run locally. The defaults work out of the box.

Copy `.env.example` to `.env` if you want to override anything:

```bash
cp .env.example .env
```

| Variable | Default | Description |
| --- | --- | --- |
| `GUARDIO_API_KEY` | `devkey` | API key for control endpoints. The frontend sends `devkey` automatically. |
| `GUARDIO_DISABLE_AI` | `false` | Set to `true` to stub all AI responses without needing a Gemini key. |
| `GEMINI_API_KEY` | *(none)* | Optional. Enables real AI suggestions in the Copilot panel. Without it, AI returns a stub message instead of erroring. |
| `GUARDIO_RATE_LIMIT_PER_MIN` | `120` | HTTP rate limit per IP per minute. |

**Frontend** (copy `frontend/.env.local.example` to `frontend/.env.local`):

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/ws` | WebSocket endpoint. |
| `NEXT_PUBLIC_API_KEY` | `devkey` | Must match `GUARDIO_API_KEY` on the backend. |

---

## Docker

Run the full backend stack with a single command:

```bash
docker compose up --build
# or: make docker-up
```

This starts:

- `guardio` backend on port `8000` (AI disabled, API key `devkey`)
- `prometheus` metrics on port `9090`

Then start the frontend separately:

```bash
cd frontend && npm install && npm run dev
```

---

## Architecture

```text
frontend/                   Next.js 15 + React 19
  src/
    app/                    Root layout, globals, page
    components/
      layout/               AppShell, TopBar, Sidebar
      map/                  ThreatMap (world map + animated attack arcs)
      graph/                InfraGraph (SVG force-directed layout)
      timeline/             IncidentTimeline (expandable forensic log)
      intelligence/         ThreatIntelPanel (charts, alerts, protocols)
      ai/                   AICopilot (Gemini-backed assistant)
      shared/               AlertFeed, LiveMetrics
    store/                  Zustand state (nodes, arcs, alerts, incidents)
    lib/                    WebSocket client with auto-reconnect
    types/                  All WebSocket event types

backend/
  main.py                   FastAPI app, all HTTP + WebSocket endpoints
  simulation.py             Attack engine + background tick loop
  topology.py               108-node geo-aware network topology
  ws_manager.py             Per-client async queue broadcaster
  ids.py                    Rate-based IDS scoring and alerts
  defense.py                Firewall blocks, segments, honeypots
  replay.py                 In-memory + SQLite replay store
  db.py                     SQLite persistence (guardio.db)
  auth.py                   Constant-time HMAC API key validation
  AI/gemini.py              Gemini wrapper with circuit breaker
```

### WebSocket events

All events arrive on `ws://localhost:8000/ws`. The frontend connects automatically on load.

| Event type | Description |
| --- | --- |
| `state` | Initial topology snapshot on connect, simulation on/off |
| `packet` | Single network packet with src/dst lat-lng, protocol, color |
| `attack` | Attack lifecycle: `start` → `update` (phases) → `end` |
| `node_update` | Node state machine transition (healthy → compromised → encrypted…) |
| `threat_level` | Global threat level 0–100 with status label |
| `alert` | IDS detection with score, level (medium/high/critical), reason |
| `defense_action` | Automated mitigation event (quarantine, rate-limit, etc.) |
| `dropped` | Packet blocked by firewall or segment isolation |
| `honeypot` | Honeypot triggered by attacker |
| `infra_telemetry` | Periodic load metrics for sampled nodes |

### Node states

| State | Color | Meaning |
| --- | --- | --- |
| `healthy` | Green | Normal operation |
| `probing` | Yellow | Reconnaissance detected |
| `stressed` | Orange | High load or flood in progress |
| `compromised` | Red | Host breached |
| `encrypted` | Purple | Ransomware locked |
| `recovering` | Cyan | Mitigation applied |
| `isolated` | Gray | Segment-isolated |
| `offline` | Dark | Service unavailable |

### Attack simulations

| Attack | Phases |
| --- | --- |
| `ddos` | probe → flood (20 sources) → saturation → anycast mitigation |
| `malware` | initial infection → wave spreading (SMB/RDP) → EDR quarantine |
| `ransomware` | lateral movement → exfiltration → encryption → ransom demand |
| `phishing` | spear-phishing campaign → credential theft → credential replay |
| `botnet` | C2 recruitment → bot enrollment → coordinated DDoS |
| `apt` | OSINT recon → zero-day access → persistence → lateral movement → exfil |

---

## API reference

All control endpoints require the `X-Api-Key` header (default: `devkey`). Read-only endpoints have no auth requirement.

### Simulation

```text
POST /start                         Start simulation
POST /stop                          Stop simulation, returns replay_id
POST /attack  { "name": "ddos" }    Launch named attack
GET  /simulation/status             Current simulation state
GET  /topology                      Full node topology with current states
```

### Defense

```text
POST   /defense/firewall/block    { "host": "host-1" }
POST   /defense/firewall/unblock  { "host": "host-1" }
POST   /defense/segment           { "name": "prod", "hosts": ["srv-1"] }
DELETE /defense/segment/{name}
POST   /defense/honeypot          { "host": "iot-3" }
DELETE /defense/honeypot          { "host": "iot-3" }
GET    /defense/status
```

### Replays

```text
GET  /replays          List saved replay IDs
GET  /replay/{id}      Fetch all events for a replay
```

### AI

```text
POST /ai/suggest        { event object }    Defense suggestion for an event
POST /ai/summarize/{id}                     AI summary of a replay
POST /AI/generate       { "prompt": "..." } Raw Gemini generation
```

### Monitoring

```text
GET /health
GET /status
GET /metrics
GET /metrics/prometheus    Prometheus exposition format
GET /telemetry/events
```

---

## Development

```bash
make test      # Run pytest suite
make lint      # mypy type check
make clean     # Remove venv and cache
make help      # List all make targets
```

Tests live in `tests/`. The CI workflow runs on every push via GitHub Actions.

---

## Tech stack

**Backend:** Python 3.11, FastAPI, uvicorn, asyncio, SQLite, Pydantic, google-genai, prometheus-client

**Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS v3, Framer Motion, Zustand, react-simple-maps, recharts, d3-geo
