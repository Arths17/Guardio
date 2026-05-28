import os
import sys

from fastapi.testclient import TestClient  # type: ignore[import-not-found]

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app  # noqa: E402

client = TestClient(app)


def test_unhandled_exception():
    response = client.get("/telemetry/events/nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "Not Found" in response.json().get("detail", "")


def test_gemini_timeout_handling(monkeypatch):
    from backend.AI import gemini as gemini_helper  # noqa: E402

    def mock_generate_text(prompt):
        raise TimeoutError("Simulated Gemini timeout")

    monkeypatch.setattr(gemini_helper, "generate_text", mock_generate_text)

    response = client.post("/AI/generate", json={"prompt": "Hello"})
    assert response.status_code == 503
    assert "detail" in response.json()
    assert "Gemini service is currently unavailable" in response.json().get(
        "detail",
        "",
    )
