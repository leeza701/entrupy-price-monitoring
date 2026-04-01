"""API key authentication dependency."""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import API_KEYS

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate the API key from the X-API-Key header.

    Returns the key if valid, raises 401 otherwise.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return api_key
