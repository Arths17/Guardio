import os
from fastapi import Header, HTTPException, status, Depends


def get_api_key(x_api_key: str | None = Header(default=None)) -> str:
    expected = os.environ.get("GUARDIO_API_KEY", "devkey")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key"
        )
    return x_api_key


def require_auth(x_api_key: str = Depends(get_api_key)):
    return x_api_key
