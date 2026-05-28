from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import WebSocket

from backend.telemetry.telemetry import telemetry

_logger = logging.getLogger("guardio.ws")
_MAX_QUEUE = 256  # drop oldest when client is too slow


class _Client:
    """One per connected WebSocket. Writer drains queue independently."""

    __slots__ = ("ws", "queue", "_task")

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.queue: asyncio.Queue[Optional[str]] = asyncio.Queue(
            maxsize=_MAX_QUEUE
        )
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        self._task = asyncio.create_task(
            self._writer(), name=f"ws-writer-{id(self)}"
        )

    async def _writer(self) -> None:
        try:
            while True:
                msg = await self.queue.get()
                if msg is None:
                    return
                await self.ws.send_text(msg)
        except Exception:
            pass  # connection closed; manager.disconnect will clean up

    def enqueue(self, msg: str) -> bool:
        """Non-blocking. Returns False if the message was dropped."""
        try:
            self.queue.put_nowait(msg)
            return True
        except asyncio.QueueFull:
            # Evict oldest then retry — slow client, but don't stall others
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(msg)
                return True
            except Exception:
                return False

    async def close(self) -> None:
        try:
            self.queue.put_nowait(None)  # sentinel stops the writer
        except asyncio.QueueFull:
            pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass


class WebSocketManager:
    def __init__(self) -> None:
        self._clients: Dict[int, _Client] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

        # Send initial state directly before joining the pool.
        # If this fails the client never enters the broadcast pool.
        try:
            from backend.simulation import sim
            from backend.defense import defense
            from backend.utils import utc_now_iso

            state = {
                "type": "state",
                "simulation": sim.snapshot(),
                "defense": await defense.get_snapshot(),
                "clients": len(self._clients) + 1,
                "ts": utc_now_iso(),
            }
            await websocket.send_json(state)
        except Exception:
            _logger.exception("Failed to send initial state; dropping WS")
            return

        client = _Client(websocket)
        client.start()
        async with self._lock:
            self._clients[id(websocket)] = client
        telemetry.increment("websocket_clients")

    async def disconnect(self, websocket: WebSocket) -> None:
        key = id(websocket)
        async with self._lock:
            client = self._clients.pop(key, None)
        if client:
            await client.close()
        telemetry.increment("websocket_disconnects")

    async def broadcast_json(self, message: dict) -> None:
        telemetry.record_event(message)
        try:
            serialized = json.dumps(message, default=str)
        except Exception:
            _logger.warning("Failed to serialize broadcast: %r", message)
            return

        async with self._lock:
            clients = list(self._clients.values())

        dropped = sum(1 for c in clients if not c.enqueue(serialized))
        if dropped:
            telemetry.increment("websocket_drops", dropped)

    async def count(self) -> int:
        async with self._lock:
            return len(self._clients)


manager = WebSocketManager()
