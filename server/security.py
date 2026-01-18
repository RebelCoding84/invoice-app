from __future__ import annotations

from fastapi import Header, HTTPException, status

from server.settings import API_KEY


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Verify X-API-Key header for API access."""
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
