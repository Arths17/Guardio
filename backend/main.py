from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from .simulation import sim
from .ws_manager import manager
from .replay import replays
from .defense import defense
from .auth import require_auth
from datetime import datetime, timezone
from backend.telemetry_helper import TelemetryMiddleware, get_events
from .telemetry.telemetry import telemetry
from .ai_client import summarize_replay, suggest_defense_for_event
from fastapi import HTTPException

app = FastAPI(title="Guardio Backend")
# attach telemetry middleware
app.add_middleware(TelemetryMiddleware)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "ts": datetime.utcnow().isoformat() + "Z"})


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
    # run attack in background
    from asyncio import create_task
    create_task(sim.launch_attack(name))
    return {"launched": name}


from fastapi import Depends


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
async def create_segment(payload: dict, x_api_key: str = Depends(require_auth)):
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
async def remove_honeypot(payload: dict, x_api_key: str = Depends(require_auth)):
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


@app.get("/defense/status")
async def defense_status():
    return {
        "blocked": list(defense.firewall_blocked_hosts),
        "honeypots": list(defense.honeypots),
        "segments": {k: list(v) for k, v in defense.segments.items()}
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
                await websocket.send_json({
                    "type": "pong",
                    "ts": datetime.now(timezone.utc).isoformat()
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)

@app.get("/telemetry/events")
def telemetry_events():
    return get_events()