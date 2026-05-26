import sys
import os
import pytest
from fastapi.testclient import TestClient

# ensure project root is on path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app
from backend.defense import defense
from backend.telemetry.telemetry import telemetry

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    # disable real AI calls in tests
    os.environ["GUARDIO_DISABLE_AI"] = "true"
    telemetry.reset()
    import asyncio

    asyncio.run(defense.reset())
    yield
    os.environ.pop("GUARDIO_DISABLE_AI", None)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200

    data = r.json()
    assert data.get("status") == "ok"


def test_status_and_metrics():
    r = client.get("/status")
    assert r.status_code == 200
    body = r.json()
    assert "simulation" in body
    assert "defense" in body

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "counts" in metrics.json()


def test_defense_block_and_status():
    headers = {"X-API-Key": "devkey"}

    r = client.post("/defense/firewall/block", json={"host": "host-1"}, headers=headers)
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
