import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..utils import utc_now_iso
from .metrics import IN_PROGRESS, REQUEST_COUNT, REQUEST_LATENCY
from .store import store_event


class TelemetryMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        status_code = 500
        IN_PROGRESS.inc()

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000

            IN_PROGRESS.dec()

            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status=str(status_code),
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                path=request.url.path,
            ).observe(duration_ms / 1000)

            store_event(
                {
                    "request_id": request_id,
                    "timestamp": utc_now_iso(),
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": duration_ms,
                }
            )


ObservabilityMiddleware = TelemetryMiddleware
