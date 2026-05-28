from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)
headers = {"X-API-Key": "devkey"}


def test_simulation_start_and_stop():
    response = client.post("/simulation/start", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "simulation started"}

    status_response = client.get("/simulation/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["running"] is True
    assert status_data["active_attack"] is not None

    stop_response = client.post("/simulation/stop", headers=headers)
    assert stop_response.status_code == 200
    assert stop_response.json() == {"status": "simulation stopped"}

    final_status_response = client.get("/simulation/status")
    assert final_status_response.status_code == 200
    final_status_data = final_status_response.json()
    assert final_status_data["running"] is False
    assert final_status_data["active_attack"] is None


def test_simulation_attack_flow():
    client.post("/simulation/start", headers=headers)

    attack_response = client.post(
        "/simulation/attack", json={"name": "ddos"}, headers=headers
    )
    assert attack_response.status_code == 200
    assert attack_response.json() == {"status": "attack ddos started"}

    status_response = client.get("/simulation/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["running"] is True
    assert status_data["active_attack"] == "ddos"

    client.post("/simulation/stop", headers=headers)

    final_status_response = client.get("/simulation/status")
    assert final_status_response.status_code == 200
    final_status_data = final_status_response.json()
    assert final_status_data["running"] is False
    assert final_status_data["active_attack"] is None
