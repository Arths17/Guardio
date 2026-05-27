import pytest

from backend.ws_manager import WebSocketManager


class _FailingWebSocket:
    def __init__(self) -> None:
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, _message) -> None:
        raise RuntimeError("send failed")


@pytest.mark.asyncio
async def test_connect_cleans_up_on_initial_state_failure():
    manager = WebSocketManager()
    websocket = _FailingWebSocket()

    await manager.connect(websocket)

    assert websocket.accepted is True
    assert await manager.count() == 0