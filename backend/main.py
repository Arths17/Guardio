from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from .simulation import sim
from .ws_manager import manager
from .replay import replays
from .defense import defense
from .auth import require_auth
from datetime import datetime
from backend.telemetry_helper import TelemetryMiddleware, get_events

app = FastAPI(title="Guardio Backend")


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


# -------------------------
# Telemetry
# -------------------------
@app.get("/telemetry/events")
def telemetry_events():
    return get_events()