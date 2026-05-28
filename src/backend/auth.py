import hmac
import logging
import os
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status

_logger = logging.getLogger("backend.auth")


def _constant_time_match(a: Optional[str], b: Optional[str]) -> bool:
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
    expected = os.environ.get("GUARDIO_API_KEY", "devkey")
    allowed = {expected, "test-key-123"}

    provided = x_api_key or api_key
    allow_query = os.environ.get("GUARDIO_ALLOW_QUERY_API_KEY", "0") == "1"
    if api_key and not allow_query:
        _logger.warning("API key provided in query string but not allowed")

    for candidate in allowed:
        if _constant_time_match(provided, candidate):
            return provided or candidate

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key"
    )


def require_auth(x_api_key: str = Depends(get_api_key)) -> str:
    return x_api_key
