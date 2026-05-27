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
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.ai_client import suggest_defense_for_event, summarize_replay
from backend.auth import require_auth
from backend.defense import defense
from backend.replay import replays
from backend.simulation import sim
from backend.telemetry import telemetry
from backend.telemetry_helper import TelemetryMiddleware, get_events
from backend.ws_manager import manager

app = FastAPI(title="Guardio Backend")
app.add_middleware(TelemetryMiddleware)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "ts": _utc_timestamp()})


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
async def simulation_start():
    await sim.start()
    return {"status": "simulation started"}


@app.post("/simulation/stop")
async def simulation_stop():
    await sim.stop()
    return {"status": "simulation stopped"}


@app.post("/simulation/attack")
async def simulation_attack(payload: dict):
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
