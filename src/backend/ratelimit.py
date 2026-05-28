import time
import logging
from typing import Dict, List

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_logger = logging.getLogger("backend.ratelimit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_min: int = 120):
        super().__init__(app)
        self.limit_per_min = limit_per_min
        self.window = 60.0
        self._buckets: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        ident = request.headers.get("x-api-key") or client
        now = time.time()
        bucket = self._buckets.setdefault(ident, [])

        threshold = now - self.window
        while bucket and bucket[0] < threshold:
            bucket.pop(0)

        if len(bucket) >= self.limit_per_min:
            _logger.warning("Rate limit exceeded for %s", ident)
            raise HTTPException(status_code=429, detail="rate limit exceeded")

        bucket.append(now)
        return await call_next(request)


__all__ = ["RateLimitMiddleware"]
