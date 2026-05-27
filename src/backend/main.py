from asyncio import create_task
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse

from .AI import gemini as gemini_helper
from .ai_client import suggest_defense_for_event, summarize_replay
from .auth import require_auth
from .db import db
from .defense import defense
from .replay import replays
from .simulation import sim
from .telemetry import telemetry
from .telemetry_helper import TelemetryMiddleware, get_events
from .ws_manager import manager

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

    _ImportedFastAPIInstrumentor = _NoOpFastAPIInstrumentor  # type: ignore[assignment]

FastAPIInstrumentor: Any = _ImportedFastAPIInstrumentor()

from .AI import gemini as gemini_helper
from .ai_client import suggest_defense_for_event, summarize_replay
from .auth import require_auth
from .defense import defense
from .db import db
from .replay import replays
from .simulation import sim
from .telemetry import telemetry
from .telemetry_helper import TelemetryMiddleware, get_events
from .ws_manager import manager

# cspell:ignore Guardio
app = FastAPI(title="Guardio Backend")

# Attach telemetry middleware
app.add_middleware(TelemetryMiddleware)


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


@app.post("/attack")
async def launch_attack(payload: dict, x_api_key: str = Depends(require_auth)):
    name = payload.get("name")
    if not name:
        return JSONResponse({"error": "missing attack name"}, status_code=400)
    # run attack in background
    create_task(sim.launch_attack(name))
    return {"launched": name}


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
    snap = telemetry.snapshot()
    snap["websocket_clients"] = await manager.count()
    snap["simulation"] = sim.snapshot()
    return snap


@app.get("/metrics/prometheus")
def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/defense/status")
async def defense_status():
    return {
        "blocked": list(defense.firewall_blocked_hosts),
        "honeypots": list(defense.honeypots),
        "segments": {k: list(v) for k, v in defense.segments.items()},
    }


# -------------------------
# Replays
# -------------------------
@app.get("/replays")
async def list_replays():
    return {"replays": replays.list()}


@app.get("/replay/{rid}")
async def get_replay(rid: str):
    r = replays.get(rid)
    if r is None:
        return JSONResponse({"error": "not found"}, status_code=404)

    return {"id": rid, "events": r}


# -------------------------
# AI helpers
# -------------------------
@app.post("/ai/summarize/{rid}")
async def ai_summarize(rid: str, x_api_key: str = Depends(require_auth)):
    try:
        text = summarize_replay(rid)
        return {"id": rid, "summary": text}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/ai/suggest")
async def ai_suggest(payload: dict, x_api_key: str = Depends(require_auth)):
    try:
        suggestion = suggest_defense_for_event(payload)
        return {"suggestion": suggestion}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


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


# -------------------------
# WebSocket
# -------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
