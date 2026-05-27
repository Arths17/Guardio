from asyncio import create_task
from datetime import datetime, timezone
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
import logging
import uuid

from backend.AI import gemini as gemini_helper
from backend.ai_client import suggest_defense_for_event, summarize_replay
from backend.auth import require_auth
from backend.db import db
from backend.defense import defense
from backend.replay import replays
from backend.simulation import sim
from backend.telemetry import telemetry
from backend.telemetry_helper import TelemetryMiddleware, get_events
from backend.ws_manager import manager
from .logging_config import configure_logging
from .env import validate_env

configure_logging()
validate_env()

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST as _CONTENT_TYPE_LATEST,
        generate_latest as _generate_latest,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"

    def _generate_latest_impl() -> bytes:
        return b""
else:

    def _generate_latest_impl() -> bytes:
        return _generate_latest()

CONTENT_TYPE_LATEST = _CONTENT_TYPE_LATEST


def generate_latest() -> bytes:
    return _generate_latest_impl()


try:
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor as _ImportedFastAPIInstrumentor,
    )
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    class _NoOpFastAPIInstrumentor:
        @staticmethod
        def instrument_app(app):
            return None

    _fastapi_instrumentor = _NoOpFastAPIInstrumentor()
else:
    _fastapi_instrumentor = _ImportedFastAPIInstrumentor()

FastAPIInstrumentor = _fastapi_instrumentor

app = FastAPI(title="Guardio Backend")
app.add_middleware(TelemetryMiddleware)

configure_logging()


@app.middleware("http")
async def add_request_id(request, call_next):
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.exception_handler(Exception)
async def handle_unhandled_exception(request, exc: Exception):
    logger = logging.getLogger("backend")
    rid = getattr(request.state, "request_id", None)
    logger.exception("Unhandled exception", exc_info=exc, extra={"request_id": rid})
    payload = {"error": "internal_server_error", "request_id": rid}
    return JSONResponse(payload, status_code=500)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/live")
async def liveness():
    return JSONResponse({"status": "ok", "ts": _utc_timestamp()})


@app.get("/ready")
async def readiness():
    return JSONResponse(
        {
            "status": "ready",
            "ts": _utc_timestamp(),
            "database": db.readiness_snapshot(),
        }
    )


@app.get("/health")
async def health():
    return await liveness()


@app.post("/start")
async def start_sim(x_api_key: str = Depends(require_auth)):
    await sim.start()
    return {"started": True}


@app.post("/stop")
async def stop_sim(x_api_key: str = Depends(require_auth)):
    rid = await sim.stop()
    return {"stopped": True, "replay_id": rid}


@app.post("/attack")
async def launch_attack(payload: dict, x_api_key: str = Depends(require_auth)):
    name = payload.get("name")
    if not name:
        return JSONResponse({"error": "missing attack name"}, status_code=400)
    create_task(sim.launch_attack(name))
    return {"launched": name}


@app.post("/simulation/start")
async def simulation_start(x_api_key: str = Depends(require_auth)):
    await sim.start()
    return {"status": "simulation started"}


@app.post("/simulation/stop")
async def simulation_stop(x_api_key: str = Depends(require_auth)):
    await sim.stop()
    return {"status": "simulation stopped"}


@app.post("/simulation/attack")
async def simulation_attack(
    payload: dict, x_api_key: str = Depends(require_auth)
):
    name = payload.get("name")
    if not name:
        return JSONResponse({"error": "missing attack name"}, status_code=400)
    sim.active_attack = name
    create_task(sim.launch_attack(name))
    return {"status": f"attack {name} started"}


@app.get("/simulation/status")
async def simulation_status():
    return {"running": sim.running, "active_attack": sim.active_attack}


@app.post("/defense/firewall/block")
async def block_host(payload: dict, x_api_key: str = Depends(require_auth)):
    host = payload.get("host")
    if not host:
        return JSONResponse({"error": "missing host"}, status_code=400)
    await defense.block_host(host)
    return {"blocked": host}


@app.post("/defense/firewall/unblock")
async def unblock_host(payload: dict, x_api_key: str = Depends(require_auth)):
    host = payload.get("host")
    if not host:
        return JSONResponse({"error": "missing host"}, status_code=400)
    await defense.unblock_host(host)
    return {"unblocked": host}


@app.post("/defense/segment")
async def create_segment(
    payload: dict, x_api_key: str = Depends(require_auth)
):
    name = payload.get("name")
    hosts = payload.get("hosts") or []
    if not name:
        return JSONResponse({"error": "missing segment name"}, status_code=400)
    await defense.create_segment(name, set(hosts))
    return {"segment": name, "hosts": hosts}


@app.delete("/defense/segment/{name}")
async def delete_segment(name: str, x_api_key: str = Depends(require_auth)):
    await defense.remove_segment(name)
    return {"deleted": name}


@app.post("/defense/honeypot")
async def add_honeypot(payload: dict, x_api_key: str = Depends(require_auth)):
    host = payload.get("host")
    if not host:
        return JSONResponse({"error": "missing host"}, status_code=400)
    await defense.add_honeypot(host)
    return {"honeypot": host}


@app.delete("/defense/honeypot")
async def remove_honeypot(
    payload: dict, x_api_key: str = Depends(require_auth)
):
    host = payload.get("host")
    if not host:
        return JSONResponse({"error": "missing host"}, status_code=400)
    await defense.remove_honeypot(host)
    return {"removed": host}


@app.get("/status")
async def status_snapshot():
    return {
        "simulation": sim.snapshot(),
        "defense": await defense.get_snapshot(),
        "clients": await manager.count(),
        "active_attack": sim.active_attack,
    }


@app.get("/metrics")
async def metrics():
    snapshot = telemetry.snapshot()
    snapshot["websocket_clients"] = await manager.count()
    snapshot["simulation"] = sim.snapshot()
    return snapshot


@app.get("/metrics/prometheus")
def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/defense/status")
async def defense_status():
    return await defense.get_snapshot()


@app.get("/replays")
async def list_replays():
    return {"replays": replays.list()}


@app.get("/replay/{rid}")
async def get_replay(rid: str):
    events = replays.get(rid)
    if events is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"id": rid, "events": events}


@app.post("/ai/summarize/{rid}")
async def ai_summarize(rid: str, x_api_key: str = Depends(require_auth)):
    try:
        return {"id": rid, "summary": summarize_replay(rid)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/ai/suggest")
async def ai_suggest(payload: dict, x_api_key: str = Depends(require_auth)):
    try:
        return {"suggestion": suggest_defense_for_event(payload)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/AI/generate")
async def ai_generate(payload: dict):
    prompt = payload.get("prompt", "")
    try:
        return {"text": gemini_helper.generate_text(prompt)}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Gemini service is currently unavailable",
        )


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, x_api_key: str = Depends(require_auth)
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.get("/telemetry/events")
def telemetry_events():
    return get_events()


FastAPIInstrumentor.instrument_app(app)
