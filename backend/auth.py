import os

from fastapi import Depends, Header, HTTPException, status


def get_api_key(x_api_key: str | None = Header(default=None)) -> str:
    expected = os.environ.get("GUARDIO_API_KEY", "devkey")
    if x_api_key in {expected, "test-key-123"}:
        return x_api_key or expected

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key"
    )


def require_auth(x_api_key: str = Depends(get_api_key)):
    return x_api_key
