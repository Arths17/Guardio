import asyncio
from typing import List

from fastapi import WebSocket

from .telemetry import telemetry


class WebSocketManager:
	def __init__(self):
		self.active: List[WebSocket] = []
		self.lock = asyncio.Lock()

	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		async with self.lock:
			self.active.append(websocket)
		telemetry.increment("websocket_clients")
		try:
			from .simulation import sim
			from .defense import defense

			state = {
				"type": "state",
				"simulation": sim.snapshot(),
				"defense": await defense.get_snapshot(),
				"clients": await self.count(),
			}
			await websocket.send_json(state)
		except Exception:
			return

	async def disconnect(self, websocket: WebSocket):
		async with self.lock:
			if websocket in self.active:
				self.active.remove(websocket)
		telemetry.increment("websocket_disconnects")

	async def broadcast_json(self, message):
		async with self.lock:
			websockets = list(self.active)
		telemetry.record_event(message)
		coros = [ws.send_json(message) for ws in websockets]
		if coros:
			await asyncio.gather(*coros, return_exceptions=True)

	async def count(self) -> int:
		async with self.lock:
			return len(self.active)


manager = WebSocketManager()