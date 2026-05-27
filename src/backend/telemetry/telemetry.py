from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


class Telemetry:
    def __init__(self) -> None:
        self._counts: Dict[str, int] = {}
        self._last_event: Dict[str, Any] | None = None

    def increment(self, name: str, amount: int = 1) -> None:
        self._counts[name] = self._counts.get(name, 0) + amount

    def record_event(self, event: Dict[str, Any]) -> None:
        self._last_event = deepcopy(event)
        self.increment("events")

    def snapshot(self) -> Dict[str, Any]:
        return {
            "counts": dict(self._counts),
            "last_event": deepcopy(self._last_event),
        }

    def reset(self) -> None:
        self._counts.clear()
        self._last_event = None


telemetry = Telemetry()
