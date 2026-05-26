import time
import uuid
import json
import logging
from datetime import datetime
from collections import deque
from typing import Optional, Dict, Any, Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from pydantic import BaseModel, Field


# =========================
# Logging Setup
# =========================

logger = logging.getLogger("telemetry")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
logger.addHandler(handler)


def log_event(event: dict):
    event["logged_at"] = datetime.utcnow().isoformat()
    logger.info(json.dumps(event))


# =========================
# In-memory replay store
# =========================

EVENT_STORE: Deque[Dict[str, Any]] = deque(maxlen=1000)


def store_event(event: Dict[str, Any]):
    EVENT_STORE.append(event)


def get_events():
    return list(EVENT_STORE)


# =========================
# Event Schema (optional but useful)
# =========================

class TelemetryEvent(BaseModel):
    event_id: str
    request_id: str
    timestamp: datetime

    method: str
    path: str
    status_code: int
    latency_ms: float

    request_body: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =========================
# Middleware
# =========================

class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Try to capture JSON body safely
        body = None
        try:
            body = await request.json()
        except Exception:
            body = None

        response = await call_next(request)

        latency_ms = (time.time() - start) * 1000

        event = {
            "event_id": str(uuid.uuid4()),
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),

            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),

            "request_body": body,
        }

        log_event(event)
        store_event(event)

        response.headers["X-Request-ID"] = request_id
        return response