from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Dict, List
import uuid

from backend.utils import utc_now_iso


_REPLAY_CACHE: Dict[str, Dict[str, Any]] = {}


class ReplayStore:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}

    def save(self, events: List[dict]) -> str:
        rid = uuid.uuid4().hex
        self.store[rid] = {
            "id": rid,
            "ts": utc_now_iso(),
            "events": list(events),
        }
        return rid

    def list(self):
        return [
            {
                "id": rid,
                "event_count": len(payload["events"]),
                "ts": payload["ts"],
            }
            for rid, payload in self.store.items()
        ]

    def get(self, rid: str):
        payload = self.store.get(rid)
        if payload is None:
            return None
        return payload["events"]

    def summary(self, rid: str):
        payload = self.store.get(rid)
        if payload is None:
            return None
        return {
            "id": rid,
            "event_count": len(payload["events"]),
            "ts": payload["ts"],
        }


replays = ReplayStore()


def save_replay(replay_data: Dict[str, Any]) -> Dict[str, Any]:
    stored = deepcopy(replay_data)
    _REPLAY_CACHE[stored["id"]] = stored
    return stored


def list_replays() -> List[Dict[str, Any]]:
    return [
        {
            "id": rid,
            "name": payload.get("name"),
            "event_count": len(payload.get("events", [])),
        }
        for rid, payload in _REPLAY_CACHE.items()
    ]


def get_replay(rid: str):
    replay_data = _REPLAY_CACHE.get(rid)
    return deepcopy(replay_data) if replay_data is not None else None


def delete_replay(rid: str):
    _REPLAY_CACHE.pop(rid, None)


def get_replay_summary(rid: str):
    replay_data = _REPLAY_CACHE.get(rid)
    if replay_data is None:
        return None

    events = replay_data.get("events", [])
    event_counts = Counter(event.get("type", "unknown") for event in events)
    return {
        "id": replay_data.get("id", rid),
        "name": replay_data.get("name"),
        "total_events": len(events),
        "event_counts": dict(event_counts),
        "event_types": dict(event_counts),
    }
