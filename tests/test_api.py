import sys
import os
import time
import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-not-found]

# ensure project root is on path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app  # noqa: E402
from backend.defense import defense  # noqa: E402, type: ignore[import-untyped]
from backend.replay import replays  # noqa: E402, type: ignore[import-untyped]
from backend.simulation import sim  # noqa: E402, type: ignore[import-untyped]
from backend.telemetry import (  # noqa: E402, type: ignore[import-untyped]
    telemetry,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    # disable real AI calls in tests
    os.environ["GUARDIO_DISABLE_AI"] = "true"
    telemetry.reset()
    import asyncio

    asyncio.run(defense.reset())
    replays.store.clear()
    sim.running = False
    sim.active_attack = None
    sim._events = []
    sim._compromised_hosts.clear()
    sim._task = None
    yield
    os.environ.pop("GUARDIO_DISABLE_AI", None)


def test_liveness_and_readiness():
    r = client.get("/live")
    assert r.status_code == 200

    data = r.json()
    assert data.get("status") == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200

    body = ready.json()
    assert body.get("status") == "ready"
    assert body["database"]["connected"] is True
    assert body["database"]["migration_count"] >= 1


def test_status_and_metrics():
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert "simulation" in body
    assert "defense" in body

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "counts" in metrics.json()


def test_replay_lifecycle():
    headers = {"X-API-Key": "devkey"}

    started = client.post("/start", headers=headers)
    assert started.status_code == 200

    attack = client.post(
        "/attack", json={"name": "ddos"}, headers=headers
    )
    assert attack.status_code == 200

    time.sleep(0.2)

    stopped = client.post("/stop", headers=headers)
    assert stopped.status_code == 200

    rid = stopped.json()["replay_id"]

    replays_response = client.get("/replays")
    assert replays_response.status_code == 200
    assert any(
        item["id"] == rid
        for item in replays_response.json()["replays"]
    )

    replay = client.get(f"/replay/{rid}")
    assert replay.status_code == 200
    events = replay.json()["events"]
    assert isinstance(events, list)
    assert len(events) >= 1


def test_defense_block_and_status():
    headers = {"X-API-Key": "devkey"}

    r = client.post(
        "/defense/firewall/block", json={"host": "host-1"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json().get("blocked") == "host-1"

    r2 = client.get("/defense/status")
    assert r2.status_code == 200

    st = r2.json()
    assert "host-1" in st.get("blocked", [])


def test_defense_unblock():
    headers = {"X-API-Key": "devkey"}

    # unblock host
    r = client.post(
        "/defense/firewall/unblock", json={"host": "host-1"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json().get("unblocked") == "host-1"

    r2 = client.get("/defense/status")
    assert r2.status_code == 200

    st = r2.json()
    assert "host-1" not in st.get("blocked", [])


def test_segment_and_honeypot_controls():
    headers = {"X-API-Key": "devkey"}

    segment = client.post(
        "/defense/segment",
        json={"name": "prod", "hosts": ["srv-1", "srv-2"]},
        headers=headers,
    )
    assert segment.status_code == 200

    honeypot = client.post(
        "/defense/honeypot",
        json={"host": "srv-9"},
        headers=headers,
    )
    assert honeypot.status_code == 200

    defense_status = client.get("/defense/status")
    body = defense_status.json()
    assert "prod" in body.get("segments", {})
    assert "srv-9" in body.get("honeypots", [])


def test_websocket_auth_and_ping():
    with client.websocket_connect("/ws?api_key=devkey") as ws:
        initial = ws.receive_json()
        assert initial["type"] == "state"

        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_ai_summarize_and_suggest():
    headers = {"X-API-Key": "devkey"}
    # create a small replay in-memory
    from backend.replay import replays

    rid = replays.save(
        [{"type": "attack", "name": "ddos", "ts": "2026-05-26T00:00:00Z"}]
    )

    r = client.post(f"/ai/summarize/{rid}", headers=headers)
    assert r.status_code == 200
    assert "summary" in r.json()

    ev = {
        "type": "packet",
        "src": "host-1",
        "dst": "srv-1",
        "color": "red",
        "ts": "2026-05-26T00:00:00Z",
    }
    s = client.post("/ai/suggest", json=ev, headers=headers)
    assert s.status_code == 200
    assert "suggestion" in s.json()
