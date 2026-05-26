import os
from asyncio import create_task

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from .simulation import sim
from .ws_manager import manager
from .replay import replays
from .defense import defense
from .auth import require_auth
from .models import AttackRequest, HostActionRequest, SegmentRequest
from .db import db
from .telemetry import telemetry
from .utils import utc_now_iso


app = FastAPI(title="Guardio Backend", version="1.1.0")


def _merge_replay_summaries():
    summaries = {item["id"]: item for item in replays.list()}
    for item in db.list_replays():
        summaries[item["id"]] = item
    return sorted(summaries.values(), key=lambda item: item.get("ts", ""), reverse=True)


def _api_key_expected() -> str:
    return os.environ.get("GUARDIO_API_KEY", "devkey")


async def _require_websocket_auth(websocket: WebSocket):
    api_key = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
    if api_key != _api_key_expected():
        await websocket.close(code=4401)
        raise WebSocketDisconnect(code=4401)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "ts": utc_now_iso()})


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


@app.post("/start")
async def start_sim(x_api_key: str = Depends(require_auth)):
    await sim.start()
    return {"started": True, "ts": utc_now_iso()}


@app.post("/stop")
async def stop_sim(x_api_key: str = Depends(require_auth)):
    rid = await sim.stop()
    return {"stopped": True, "replay_id": rid, "ts": utc_now_iso()}


@app.post("/attack")
async def launch_attack(payload: AttackRequest, x_api_key: str = Depends(require_auth)):
    create_task(sim.launch_attack(payload.name))
    return {"launched": payload.name, "intensity": payload.intensity, "target": payload.target, "ts": utc_now_iso()}


@app.post("/defense/firewall/block")
async def block_host(payload: HostActionRequest, x_api_key: str = Depends(require_auth)):
    await defense.block_host(payload.host)
    return {"blocked": payload.host, "ts": utc_now_iso()}


@app.post("/defense/firewall/unblock")
async def unblock_host(payload: HostActionRequest, x_api_key: str = Depends(require_auth)):
    await defense.unblock_host(payload.host)
    return {"unblocked": payload.host, "ts": utc_now_iso()}


@app.post("/defense/segment")
async def create_segment(payload: SegmentRequest, x_api_key: str = Depends(require_auth)):
    await defense.create_segment(payload.name, set(payload.hosts))
    return {"segment": payload.name, "hosts": payload.hosts, "ts": utc_now_iso()}


@app.delete("/defense/segment/{segment_name}")
async def delete_segment(segment_name: str, x_api_key: str = Depends(require_auth)):
    await defense.remove_segment(segment_name)
    return {"deleted": segment_name, "ts": utc_now_iso()}


@app.post("/defense/honeypot")
async def add_honeypot(payload: HostActionRequest, x_api_key: str = Depends(require_auth)):
    await defense.add_honeypot(payload.host)
    return {"honeypot": payload.host, "ts": utc_now_iso()}


@app.delete("/defense/honeypot")
async def delete_honeypot(payload: HostActionRequest, x_api_key: str = Depends(require_auth)):
    await defense.remove_honeypot(payload.host)
    return {"removed": payload.host, "ts": utc_now_iso()}


@app.get("/defense/status")
async def defense_status():
    return await defense.get_snapshot()


@app.get("/replays")
async def list_replays():
    return {"replays": _merge_replay_summaries()}


@app.get("/replay/{rid}")
async def get_replay(rid: str):
    events = replays.get(rid) or db.get_events(rid)
    if events is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"id": rid, "events": events}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await _require_websocket_auth(websocket)
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "state", "ts": utc_now_iso(), "simulation": sim.snapshot()})
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "ts": utc_now_iso()})
            elif data == "status":
                await websocket.send_json({"type": "status", "ts": utc_now_iso(), "simulation": sim.snapshot(), "defense": await defense.get_snapshot()})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
