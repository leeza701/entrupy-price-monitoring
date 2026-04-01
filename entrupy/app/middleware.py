"""Usage-tracking middleware — logs every authenticated request to api_usage table."""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import text

from app.database import AsyncSessionLocal


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Records API key, endpoint, method, and status code for each request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response: Response = await call_next(request)
        elapsed = time.time() - start

        # Only track API calls (not static files)
        if request.url.path.startswith("/api"):
            api_key = request.headers.get("X-API-Key", "anonymous")
            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        text(
                            "INSERT INTO api_usage (api_key, endpoint, method, status_code) "
                            "VALUES (:key, :endpoint, :method, :code)"
                        ),
                        {
                            "key": api_key,
                            "endpoint": request.url.path,
                            "method": request.method,
                            "code": response.status_code,
                        },
                    )
                    await session.commit()
            except Exception:
                pass  # Don't let tracking failures break the API

        return response
