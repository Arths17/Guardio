import sys
import os
import json
import pytest
from fastapi.testclient import TestClient

# ensure project root is on path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app
from backend.telemetry_helper import EVENT_STORE, store_event

client = TestClient(app)


# -------------------------
# Load sample events
# -------------------------
sample_path = os.path.join(os.path.dirname(__file__), "gemini_sample_events.json")

with open(sample_path, "r") as f:
    sample_events = json.load(f)


# -------------------------
# Test: telemetry endpoint exists + structure
# -------------------------
def test_telemetry_events_basic():
    # clear state to avoid flaky tests
    EVENT_STORE.clear()

    r = client.get("/telemetry/events")
    assert r.status_code == 200

    events = r.json()
    assert isinstance(events, list)


# -------------------------
# Test: sample events ingestion + validation
# -------------------------
def test_telemetry_events_schema_and_data():
    # reset store
    EVENT_STORE.clear()

    # inject sample events into in-memory store
    for event in sample_events:
        store_event(event)

    r = client.get("/telemetry/events")
    assert r.status_code == 200

    events = r.json()

    assert len(events) == len(sample_events)

    for event in events:
        # required telemetry fields
        assert "event_id" in event
        assert "request_id" in event
        assert "timestamp" in event
        assert "method" in event
        assert "path" in event
        assert "status_code" in event
        assert "latency_ms" in event

        # sanity checks (important, not just structure)
        assert isinstance(event["latency_ms"], (int, float))
        assert event["latency_ms"] >= 0
        assert event["method"] in ["GET", "POST", "PUT", "DELETE", "PATCH"]


# -------------------------
# Test: real request generates telemetry
# -------------------------
def test_telemetry_is_recorded_from_requests():
    EVENT_STORE.clear()

    # trigger real middleware logging
    r = client.get("/health")
    assert r.status_code == 200

    r2 = client.get("/telemetry/events")
    assert r2.status_code == 200

    events = r2.json()

    assert len(events) >= 1

    event = events[-1]
    assert event["path"] == "/health"
    assert event["method"] == "GET"