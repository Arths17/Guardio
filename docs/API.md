# Guardio Backend API

Overview
- The backend is a FastAPI app exposing endpoints for simulation, defense controls, replays, AI helpers, and telemetry.
- Interactive docs available at `/docs` (Swagger) and `/redoc` when the server is running.

Authentication
- Use header `X-API-Key` with your API key (tests use `devkey`).

Health
- `GET /live` — liveness probe, returns `{"status":"ok","ts":...}`
- `GET /ready` — readiness probe, includes database snapshot

Simulation & Replays
- `POST /start` — start simulation (requires API key)
- `POST /stop` — stop simulation, returns a `replay_id`
- `POST /attack` — launch named attack in background (json: `{"name":"ddos"}`)
- `GET /replays` — list available replays
- `GET /replay/{rid}` — get a replay's events

Defense Controls
- `POST /defense/firewall/block` — block a host (`{"host":"host-1"}`)
- `POST /defense/firewall/unblock` — unblock a host
- `POST /defense/segment` — create a segment (`{"name":"prod","hosts":["srv-1"]}`)
- `DELETE /defense/segment/{name}` — delete a segment
- `POST /defense/honeypot` — add honeypot
- `DELETE /defense/honeypot` — remove honeypot

AI Helpers
- `POST /ai/summarize/{rid}` — summarize a replay
- `POST /ai/suggest` — suggest a defensive action for an event
- `POST /AI/generate` — free-form text generation (Gemini); set `GUARDIO_DISABLE_AI=true` to stub

Telemetry & Metrics
- `GET /metrics` — JSON telemetry snapshot
- `GET /metrics/prometheus` — Prometheus exposition (requires `prometheus_client` installed)
- `GET /telemetry/events` — recent stored telemetry events

WebSocket
- `GET /ws` — websocket endpoint; connect with query `?api_key=YOUR_KEY`.
  - On connect the server sends a `state` message.
  - Send `ping` to receive a `pong` with timestamp.

Examples
- See `examples/` for a small Python client and usage notes.

Notes
- The server includes structured logging, request-id middleware, and a global exception handler. Run `python -m uvicorn backend.main:app --reload` for local development.
