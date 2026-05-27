from collections import Counter
from threading import Lock
from typing import Any, Dict


class Telemetry:
    def __init__(self):
        self._lock = Lock()
        self._counts = Counter()
        self._last_event: Dict[str, Any] | None = None

    def increment(self, key: str, amount: int = 1):
        with self._lock:
            self._counts[key] += amount

    def record_event(self, event: Dict[str, Any]):
        with self._lock:
            event_type = event.get("type", "unknown")
            self._counts[f"events_{event_type}"] += 1
            self._last_event = dict(event)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counts": dict(self._counts),
                "last_event": self._last_event,
            }

    def reset(self):
        with self._lock:
            self._counts.clear()
            self._last_event = None


telemetry = Telemetry()
