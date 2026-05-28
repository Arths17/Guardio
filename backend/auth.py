from __future__ import annotations

import hmac
import logging
import os
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status

_logger = logging.getLogger("backend.auth")


def _match(a: Optional[str], b: Optional[str]) -> bool:
    if a is None or b is None:
        return False
    try:
        return hmac.compare_digest(a, b)
    except Exception:
        return False


def get_api_key(
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None),
) -> str:
    """Validate API key with constant-time comparison.

    Header ``X-API-Key`` is the primary channel. Query-string keys are
    only accepted when ``GUARDIO_ALLOW_QUERY_API_KEY=1``.
    """
    expected = os.environ.get("GUARDIO_API_KEY", "devkey")

    allow_query = os.environ.get("GUARDIO_ALLOW_QUERY_API_KEY", "0") == "1"
    if api_key and not allow_query:
        _logger.warning("API key in query string rejected (not allowed)")

    provided = x_api_key or (api_key if allow_query else None)

    # Additional keys allowed via comma-separated env var (for CI/tests)
    extra_raw = os.environ.get("GUARDIO_EXTRA_API_KEYS", "")
    allowed = {expected} | {k for k in extra_raw.split(",") if k}

    for candidate in allowed:
        if _match(provided, candidate):
            return provided  # type: ignore[return-value]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid api key",
    )


def require_auth(x_api_key: str = Depends(get_api_key)) -> str:
    return x_api_key
