from typing import List, Dict, Any
import uuid

from .utils import utc_now_iso


class ReplayStore:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}

    def save(self, events: List[dict]) -> str:
        rid = uuid.uuid4().hex
        self.store[rid] = {"id": rid, "ts": utc_now_iso(), "events": list(events)}
        return rid

    def list(self):
        return [
            {"id": rid, "event_count": len(payload["events"]), "ts": payload["ts"]}
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
        return {"id": rid, "event_count": len(payload["events"]), "ts": payload["ts"]}


replays = ReplayStore()
