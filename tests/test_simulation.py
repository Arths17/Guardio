from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_simulation_start_and_stop():
    # Start the simulation
    response = client.post("/simulation/start")
    assert response.status_code == 200
    assert response.json() == {"status": "simulation started"}

    # Check status while running
    status_response = client.get("/simulation/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["running"] is True
    assert status_data["active_attack"] is not None

    # Stop the simulation
    stop_response = client.post("/simulation/stop")
    assert stop_response.status_code == 200
    assert stop_response.json() == {"status": "simulation stopped"}

    # Check status after stopping
    final_status_response = client.get("/simulation/status")
    assert final_status_response.status_code == 200
    final_status_data = final_status_response.json()
    assert final_status_data["running"] is False
    assert final_status_data["active_attack"] is None


def test_simulation_attack_flow():
    # Start the simulation
    client.post("/simulation/start")

    # Trigger an attack
    attack_response = client.post("/simulation/attack", json={"name": "ddos"})
    assert attack_response.status_code == 200
    assert attack_response.json() == {"status": "attack ddos started"}

    # Check status during attack
    status_response = client.get("/simulation/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["running"] is True
    assert status_data["active_attack"] == "ddos"

    # Stop the simulation to end the attack
    client.post("/simulation/stop")

    # Check status after stopping
    final_status_response = client.get("/simulation/status")
    assert final_status_response.status_code == 200
    final_status_data = final_status_response.json()
    assert final_status_data["running"] is False
    assert final_status_data["active_attack"] is None