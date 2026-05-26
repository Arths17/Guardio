import pytest
import sys
import os
from fastapi.testclient import TestClient
# ensure project root is on path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from backend.main import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"


def test_defense_block_and_status():
    headers = {"X-API-Key": "devkey"}
    r = client.post("/defense/firewall/block", json={"host": "host-1"}, headers=headers)
    assert r.status_code == 200
    assert r.json().get("blocked") == "host-1"

    r2 = client.get("/defense/status")
    assert r2.status_code == 200
    st = r2.json()
    assert "host-1" in st.get("blocked")
