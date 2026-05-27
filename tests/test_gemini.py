import sys
import os
import json
import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-not-found]

# ensure project root is on path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app  # noqa: E402
from backend.AI import gemini as gemini_helper  # noqa: E402
from backend.telemetry import (  # noqa: E402, type: ignore[import-untyped]
    EVENT_STORE,
    get_events,
    store_event,
)

client = TestClient(app)


# -------------------------
# Load sample events
# -------------------------
sample_path = os.path.join(
    os.path.dirname(__file__), "gemini_sample_events.json"
)

with open(sample_path, "r") as f:
    sample_events = json.load(f)


# -------------------------
# Fixture: clean state per test
# -------------------------
@pytest.fixture(autouse=True)
def clear_telemetry():
    EVENT_STORE.clear()
    yield
    EVENT_STORE.clear()


# -------------------------
# Test: endpoint exists
# -------------------------
def test_telemetry_events_basic():
    r = client.get("/telemetry/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_gemini_stub_generation(monkeypatch):
    monkeypatch.setenv("GUARDIO_DISABLE_AI", "true")

    result = gemini_helper.generate_text("hello world")

    assert result.startswith("[ai-stub] hello world")


# -------------------------
# Test: sample event replay correctness
# -------------------------
def test_telemetry_events_schema_and_data():
    for event in sample_events:
        store_event(event)

    events = get_events()

    assert len(events) == len(sample_events)

    for event in events:
        assert "event_id" in event
        assert "request_id" in event
        assert "timestamp" in event
        assert "method" in event
        assert "path" in event
        assert "status_code" in event
        assert "latency_ms" in event

        assert isinstance(event["latency_ms"], (int, float))
        assert event["latency_ms"] >= 0


# -------------------------
# Test: middleware generates telemetry
# -------------------------
def test_telemetry_is_recorded_from_requests():
    r = client.get("/live")
    assert r.status_code == 200

    events = client.get("/telemetry/events").json()

    assert len(events) >= 1

    event = events[-1]
    assert event["path"] == "/live"
    assert event["method"] == "GET"


# -------------------------
# Test: defense block/unblock telemetry
# -------------------------
def test_defense_block_unblock_telemetry():
    headers = {"X-API-Key": "devkey"}

    r = client.post(
        "/defense/firewall/block", json={"host": "host-1"}, headers=headers
    )
    assert r.status_code == 200

    r2 = client.post(
        "/defense/firewall/unblock", json={"host": "host-1"}, headers=headers
    )
    assert r2.status_code == 200

    events = client.get("/telemetry/events").json()

    block_events = [
        e for e in events if e["path"] == "/defense/firewall/block"
    ]
    unblock_events = [
        e for e in events if e["path"] == "/defense/firewall/unblock"
    ]

    assert len(block_events) >= 1
    assert len(unblock_events) >= 1

    assert block_events[-1]["status_code"] == 200
    assert unblock_events[-1]["status_code"] == 200
