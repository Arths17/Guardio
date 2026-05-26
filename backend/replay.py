from typing import List, Dict
import uuid


class ReplayStore:
    def __init__(self):
        self.store: Dict[str, List[dict]] = {}

    def save(self, events: List[dict]) -> str:
        rid = uuid.uuid4().hex
        self.store[rid] = list(events)
        return rid

    def list(self):
        return list(self.store.keys())

    def get(self, rid: str):
        return self.store.get(rid)


replays = ReplayStore()
