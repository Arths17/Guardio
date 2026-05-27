from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

valid_api_key = "test-key-123"
invalid_api_key = "bad-key"

def test_auth():
    # Test with valid API key
    response = client.post(
        "/defense/firewall/block",
        json={"host": "malicious.com"},
        headers={"x-api-key": valid_api_key},
    )
    assert response.status_code == 200
    assert response.json() == {"blocked": "malicious.com"}

    # Test with invalid API key
    response = client.post(
        "/defense/firewall/block",
        json={"host": "malicious.com"},
        headers={"x-api-key": invalid_api_key},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid api key"}

    # Test with missing API key
    response = client.post(
        "/defense/firewall/block",
        json={"host": "malicious.com"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid api key"}

