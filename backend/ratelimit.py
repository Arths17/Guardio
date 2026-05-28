from __future__ import annotations

import logging
import time
from collections import deque, defaultdict
from typing import DefaultDict, Deque

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_logger = logging.getLogger("backend.ratelimit")

_CLEANUP_INTERVAL = 1_000  # evict stale identifiers every N requests


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter.

    Uses per-identifier deque buckets (O(1) amortized eviction).
    Stale identifiers are purged every ``_CLEANUP_INTERVAL`` requests to
    prevent unbounded memory growth under many unique clients.
    """

    def __init__(self, app, limit_per_min: int = 120) -> None:
        super().__init__(app)
        self.limit_per_min = limit_per_min
        self.window = 60.0
        self._buckets: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._req_count = 0

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        ident = request.headers.get("x-api-key") or client
        now = time.monotonic()

        bucket = self._buckets[ident]
        cutoff = now - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.limit_per_min:
            _logger.warning("Rate limit exceeded: %s", ident)
            raise HTTPException(status_code=429, detail="rate limit exceeded")

        bucket.append(now)

        self._req_count += 1
        if self._req_count % _CLEANUP_INTERVAL == 0:
            self._evict_stale(now)

        return await call_next(request)

    def _evict_stale(self, now: float) -> None:
        cutoff = now - self.window
        stale = [
            k for k, dq in self._buckets.items()
            if not dq or dq[-1] < cutoff
        ]
        for k in stale:
            del self._buckets[k]
        if stale:
            _logger.debug("Evicted %d stale rate-limit buckets", len(stale))


__all__ = ["RateLimitMiddleware"]
