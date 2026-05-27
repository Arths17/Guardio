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
        try:
            from backend.db import db

            db.save_replay(rid, self.store[rid]["events"])
        except Exception:
            pass
        return rid

    def list(self):
        items = [
            {
                "id": rid,
                "event_count": len(payload["events"]),
                "ts": payload["ts"],
            }
            for rid, payload in self.store.items()
        ]

        try:
            from backend.db import db

            cached_ids = {item["id"] for item in items}
            for row in db.list_replays():
                if row["id"] not in cached_ids:
                    items.append(row)
        except Exception:
            pass

        return items

    def get(self, rid: str):
        payload = self.store.get(rid)
        if payload is None:
            try:
                from backend.db import db

                events = db.get_events(rid)
            except Exception:
                return None

            return events or None
        return payload["events"]

    def summary(self, rid: str):
        payload = self.store.get(rid)
        if payload is None:
            try:
                from backend.db import db

                events = db.get_events(rid)
                rows = [row for row in db.list_replays() if row["id"] == rid]
            except Exception:
                return None

            if not events and not rows:
                return None

            row = (
                rows[0]
                if rows
                else {
                    "id": rid,
                    "ts": utc_now_iso(),
                    "event_count": len(events),
                }
            )
            return {
                "id": rid,
                "event_count": len(events),
                "ts": row.get("ts"),
            }
        return {
            "id": rid,
            "event_count": len(payload["events"]),
            "ts": payload["ts"],
        }


replays = ReplayStore()


def save_replay(replay_data: Dict[str, Any]) -> Dict[str, Any]:
    stored = deepcopy(replay_data)
    _REPLAY_CACHE[stored["id"]] = stored
    try:
        from backend.db import db

        db.save_replay(stored["id"], stored.get("events", []))
    except Exception:
        pass
    return stored


def list_replays() -> List[Dict[str, Any]]:
    items = [
        {
            "id": rid,
            "name": payload.get("name"),
            "event_count": len(payload.get("events", [])),
        }
        for rid, payload in _REPLAY_CACHE.items()
    ]

    try:
        from backend.db import db

        cached_ids = {item["id"] for item in items}
        for row in db.list_replays():
            if row["id"] not in cached_ids:
                items.append(row)
    except Exception:
        pass

    return items


def get_replay(rid: str):
    replay_data = _REPLAY_CACHE.get(rid)
    if replay_data is not None:
        return deepcopy(replay_data)

    try:
        from backend.db import db

        events = db.get_events(rid)
    except Exception:
        return None

    if not events:
        return None

    return {"id": rid, "events": events}


def delete_replay(rid: str):
    _REPLAY_CACHE.pop(rid, None)
    try:
        from backend.db import db

        db.purge_replay(rid)
    except Exception:
        pass


def get_replay_summary(rid: str):
    replay_data = _REPLAY_CACHE.get(rid)
    if replay_data is None:
        try:
            from backend.db import db

            events = db.get_events(rid)
            rows = [row for row in db.list_replays() if row["id"] == rid]
        except Exception:
            return None

        if not events and not rows:
            return None

        event_counts = Counter(
            event.get("type", "unknown") for event in events
        )
        row = rows[0] if rows else {"id": rid, "ts": utc_now_iso()}
        return {
            "id": row.get("id", rid),
            "name": None,
            "total_events": len(events),
            "event_counts": dict(event_counts),
            "event_types": dict(event_counts),
        }

    events = replay_data.get("events", [])
    event_counts = Counter(event.get("type", "unknown") for event in events)
    return {
        "id": replay_data.get("id", rid),
        "name": replay_data.get("name"),
        "total_events": len(events),
        "event_counts": dict(event_counts),
        "event_types": dict(event_counts),
    }
