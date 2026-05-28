# Guardio Backend API

Overview
- FastAPI backend for simulation, defense controls, replay storage, AI helpers, and telemetry.
- Interactive docs are available at `/docs` and `/redoc`.

Authentication
- Use header `X-API-Key` for protected HTTP endpoints.
- Default development key is `devkey`.
- WebSocket connections can also pass `api_key` in the query string; header auth is still preferred.

Health and status
- `GET /live` — liveness probe.
- `GET /health` — alias for `/live`.
- `GET /ready` — readiness probe with database snapshot.
- `GET /status` — combined simulation, defense, client, and attack snapshot.
- `GET /simulation/status` — simulation-only status.
- `GET /defense/status` — defense-only status.

Simulation and replays
- `POST /start` — start the simulator.
- `POST /stop` — stop the simulator and return a `replay_id`.
- `POST /attack` — launch an attack by name, e.g. `{"name":"ddos"}`.
- `POST /simulation/start` — simulation alias for start.
- `POST /simulation/stop` — simulation alias for stop.
- `POST /simulation/attack` — simulation alias for attack.
- `GET /replays` — list stored replays.
- `GET /replay/{rid}` — fetch replay events by replay id.

Defense controls
- `POST /defense/firewall/block` — block a host, e.g. `{"host":"host-1"}`.
- `POST /defense/firewall/unblock` — unblock a host.
- `POST /defense/segment` — create a segment, e.g. `{"name":"prod","hosts":["srv-1"]}`.
- `DELETE /defense/segment/{name}` — delete a segment.
- `POST /defense/honeypot` — add a honeypot host.
- `DELETE /defense/honeypot` — remove a honeypot host.

AI helpers
- `POST /ai/summarize/{rid}` — summarize a replay.
- `POST /ai/suggest` — suggest a defensive action for an event.
- `POST /AI/generate` — free-form text generation via Gemini.
- Set `GUARDIO_DISABLE_AI=true` to stub AI responses in tests or local runs.

Telemetry and metrics
- `GET /metrics` — JSON telemetry snapshot.
- `GET /metrics/prometheus` — Prometheus exposition format.
- `GET /telemetry/events` — recent stored telemetry events.

WebSocket
- `GET /ws` — connect with `?api_key=YOUR_KEY` or the `X-API-Key` header.
- The server sends an initial `state` message on connect.
- Send `ping` to receive a `pong` response with a timestamp.

Examples
- See `examples/` for a small Python client and usage notes.

Notes
- The server uses structured logging, request-id middleware, a lifespan-based startup/shutdown flow, and a global exception handler.
- Run `python -m uvicorn backend.main:app --reload` for local development.
