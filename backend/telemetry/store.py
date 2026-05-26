from typing import List, Dict, Any


class EventStore:
    def append(self, event: Dict[str, Any]):
        raise NotImplementedError

    def list(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError
