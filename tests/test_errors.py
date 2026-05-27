#What to test: * How the backend handles unhandled server exceptions (500 Internal Server Error).

#Enforcing that database downtime or third-party service failures (like an AI/Gemini integration timeout) won't crash the entire FastAPI engine.

#Ensuring stack traces are stripped from production error responses (to prevent data leaks to attackers).

import sys 
import os 
from fastapi.testclient import TestClient # type: ignore[import-not-found]

# ensure project root is on path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app # noqa: E402

client = TestClient(app)

def test_unhandled_exception():
    # This endpoint doesn't exist and should trigger a 404, but we want to ensure it doesn't cause a 500 or crash the server.
    r = client.get("/telemetry/events/nonexistent")
    assert r.status_code == 404
    assert "detail" in r.json()
    assert "Not Found" in r.json().get("detail", "")

def test_gemini_timeout_handling(monkeypatch):
    # Simulate a timeout in the Gemini AI integration
    from backend.AI import gemini as gemini_helper # noqa: E402

    def mock_generate_text(prompt):
        raise TimeoutError("Simulated Gemini timeout")

    monkeypatch.setattr(gemini_helper, "generate_text", mock_generate_text)

    r = client.post("/AI/generate", json={"prompt": "Hello"})
    assert r.status_code == 503  # Service Unavailable
    assert "detail" in r.json()
    assert "Gemini service is currently unavailable" in r.json().get("detail", "")

