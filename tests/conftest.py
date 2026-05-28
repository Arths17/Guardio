import os
import pytest


@pytest.fixture(autouse=True)
def _test_api_key(monkeypatch):
    """Expose the legacy test key through the new extra-keys mechanism."""
    monkeypatch.setenv("GUARDIO_EXTRA_API_KEYS", "test-key-123")
