from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any, Dict, List
import uuid

from backend.utils import utc_now_iso
from backend.lifecycle import create_task

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

            # Persist to DB without blocking the event loop when possible
            try:
                import asyncio

                asyncio.get_running_loop()
            except Exception:
                # No running loop; perform synchronous write
                db.save_replay(rid, self.store[rid]["events"])
            else:
                # Schedule async persistence in background.
                create_task(db.save_replay_async(rid, self.store[rid]["events"]))
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

    async def list_async(self):
        # Return in-memory items first, then append DB items without blocking
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

            db_rows = await db.list_replays_async()
            cached_ids = {item["id"] for item in items}
            for row in db_rows:
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

    async def get_async(self, rid: str):
        payload = self.store.get(rid)
        if payload is not None:
            return list(payload.get("events", []))

        try:
            from backend.db import db

            events = await db.get_events_async(rid)
        except Exception:
            return None

        if not events:
            return None

        return list(events)

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

    async def summary_async(self, rid: str):
        payload = self.store.get(rid)
        if payload is None:
            try:
                from backend.db import db

                events = await db.get_events_async(rid)
                rows = [
                    row for row in await db.list_replays_async() if row["id"] == rid
                ]
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

        events = payload.get("events", [])
        event_counts = Counter(event.get("type", "unknown") for event in events)
        return {
            "id": payload.get("id", rid),
            "event_count": len(events),
            "ts": payload.get("ts"),
            "event_counts": dict(event_counts),
            "event_types": dict(event_counts),
        }


replays = ReplayStore()


def save_replay(replay_data: Dict[str, Any]) -> Dict[str, Any]:
    stored = deepcopy(replay_data)
    _REPLAY_CACHE[stored["id"]] = stored
    try:
        from backend.db import db

        # Prefer async DB persistence when running inside an event loop
        try:
            import asyncio

            asyncio.get_running_loop()
        except Exception:
            db.save_replay(stored["id"], stored.get("events", []))
        else:
            create_task(db.save_replay_async(stored["id"], stored.get("events", [])))
    except Exception:
        pass
    return stored


async def save_replay_async(replay_data: Dict[str, Any]) -> Dict[str, Any]:
    stored = deepcopy(replay_data)
    _REPLAY_CACHE[stored["id"]] = stored
    try:
        from backend.db import db

        await db.save_replay_async(stored["id"], stored.get("events", []))
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


async def list_replays_async() -> List[Dict[str, Any]]:
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
        for row in await db.list_replays_async():
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


async def get_replay_async(rid: str):
    replay_data = _REPLAY_CACHE.get(rid)
    if replay_data is not None:
        return deepcopy(replay_data)

    try:
        from backend.db import db

        events = await db.get_events_async(rid)
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


async def delete_replay_async(rid: str):
    _REPLAY_CACHE.pop(rid, None)
    try:
        from backend.db import db

        await db.purge_replay_async(rid)
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

        event_counts = Counter(event.get("type", "unknown") for event in events)
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


async def get_replay_summary_async(rid: str):
    replay_data = _REPLAY_CACHE.get(rid)
    if replay_data is None:
        try:
            from backend.db import db

            events = await db.get_events_async(rid)
            rows = [row for row in await db.list_replays_async() if row["id"] == rid]
        except Exception:
            return None

        if not events and not rows:
            return None

        event_counts = Counter(event.get("type", "unknown") for event in events)
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
