"""Middleware de cabeçalhos e higiene HTTP (OWASP A05)."""

from __future__ import annotations

import secrets
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona cabeçalhos de segurança e correlaciona requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or secrets.token_hex(8)
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)

        response.headers.setdefault("X-Request-ID", request_id)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        # API JSON — CSP restritiva (não serve HTML do portal).
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        # Remove fingerprinting óbvio quando presente.
        if "server" in response.headers:
            del response.headers["server"]

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        response.headers.setdefault("X-Response-Time-Ms", str(elapsed_ms))
        return response
