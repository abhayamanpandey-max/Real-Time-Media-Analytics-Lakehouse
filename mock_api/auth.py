"""
mock_api/auth.py

Bearer token authentication dependency for the Mock API.
The token is read from config['api']['token'] at startup.
Swapping to a real API auth scheme = changing the dependency implementation only.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status

from config.loader import load_config


@lru_cache(maxsize=1)
def get_config() -> dict:
    """Load config once at startup (cached)."""
    return load_config()


def verify_bearer_token(request: Request, config: dict = Depends(get_config)) -> None:
    """
    FastAPI dependency. Validates the Authorization: Bearer <token> header.
    Raises HTTP 401 if the header is missing or the token is incorrect.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
        )
    token = auth_header.removeprefix("Bearer ").strip()
    expected = config["api"]["token"]
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token.",
        )
