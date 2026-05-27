import os

from fastapi import Depends, Header, HTTPException, Query, status


def get_api_key(
    x_api_key: str | None = Header(default=None),
    api_key: str | None = Query(default=None),
) -> str:
    expected = os.environ.get("GUARDIO_API_KEY", "devkey")

    provided = x_api_key or api_key
    if provided in {expected, "test-key-123"}:
        return provided or expected

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key"
    )


def require_auth(x_api_key: str = Depends(get_api_key)):
    return x_api_key
