"""Shared bearer token auth middleware for sidecar HTTP endpoints."""

import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Validate Authorization header against API_TOKEN env var.

    Skips auth if API_TOKEN is not set.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = os.environ["API_TOKEN"]

        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {token}":
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await call_next(request)
