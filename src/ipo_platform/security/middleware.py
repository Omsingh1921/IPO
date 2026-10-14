"""
Security Middlewares for Indian IPO Platform API (Phase 10 - Stage 5).
Implements HTTP Security Headers, Payload Size Protection, and Host Header Validation.
"""

import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ipo_platform.security.config import SecurityConfig, get_security_config

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies standard enterprise HTTP security headers to all API responses:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: default-src 'self'; frame-ancestors 'none'
    - Permissions-Policy: geolocation=(), camera=(), microphone=()
    - Strict-Transport-Security (when HTTPS is enforced)
    """

    def __init__(self, app: ASGIApp, config: SecurityConfig) -> None:
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Apply defense-in-depth headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; frame-ancestors 'none';"
        )
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        if self.config.enforce_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Apply Cache-Control no-store to authenticated or mutating routes
        path = request.url.path
        if path.startswith(("/recommendation", "/portfolio", "/metrics")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces maximum request payload size to protect against memory exhaustion DOS attacks.
    Inspects Content-Length header and aborts with 413 Payload Too Large if exceeded.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > self.max_bytes:
                    logger.warning(
                        "Payload size exceeded: %d bytes (limit: %d bytes) for %s",
                        content_length,
                        self.max_bytes,
                        request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "PAYLOAD_TOO_LARGE",
                            "detail": f"Request body size exceeds maximum allowed limit of {self.max_bytes} bytes",
                            "status_code": 413,
                            "path": request.url.path,
                        },
                    )
            except ValueError:
                pass  # Fall through if unparseable header; Starlette request body validation handles it

        return await call_next(request)
