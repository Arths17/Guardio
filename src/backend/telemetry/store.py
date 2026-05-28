from __future__ import annotations

from copy import deepcopy
from itertools import count
from typing import Any, Dict, List

from ..utils import utc_now_iso

EVENT_STORE: List[Dict[str, Any]] = []
_EVENT_IDS = count(1)


def store_event(event: Dict[str, Any]) -> Dict[str, Any]:
    stored = deepcopy(event)
    stored.setdefault("event_id", f"evt-{next(_EVENT_IDS)}")
    stored.setdefault("request_id", stored["event_id"])
    stored.setdefault("timestamp", utc_now_iso())
    EVENT_STORE.append(stored)
    return stored


def get_events() -> List[Dict[str, Any]]:
    return deepcopy(EVENT_STORE)
