"""Lightweight middleware: security headers and per-IP rate limiting.

Intentionally dependency-free (stdlib only) so it behaves identically in
local runs and in the self-hosted Cloudflare Tunnel deployment.
"""

import os
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple per-IP sliding-window rate limiter.

    Buckets are keyed by (client_ip, route_group). Limits are per-minute.
    Expensive inference endpoints (/agent/run, /agent/classify, /agent/filter)
    get tighter limits than cheap read endpoints.
    """

    WINDOW_SECONDS = 60

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[tuple[str, str], deque] = defaultdict(deque)
        self.limits = {
            "run": int(os.getenv("RATE_LIMIT_RUN_PER_MINUTE", "10")),
            "classify": int(os.getenv("RATE_LIMIT_CLASSIFY_PER_MINUTE", "30")),
            "filter": int(os.getenv("RATE_LIMIT_FILTER_PER_MINUTE", "30")),
            "read": int(os.getenv("RATE_LIMIT_READ_PER_MINUTE", "60")),
        }

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Deployed behind a Cloudflare Tunnel: the edge sets/overwrites
        # CF-Connecting-IP with the true client IP, so it is trustworthy here.
        # Client-supplied X-Forwarded-For entries are NOT trusted (spoofable).
        # Note: any direct-to-origin path bypassing the tunnel must be blocked
        # at the firewall, otherwise CF-Connecting-IP could be spoofed directly.
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _bucket(path: str) -> str | None:
        if path == "/agent/run":
            return "run"
        if path == "/agent/classify":
            return "classify"
        if path == "/agent/filter":
            return "filter"
        if path.startswith("/agent/"):
            return "read"
        return None  # /health, /, /docs are exempt

    async def dispatch(self, request: Request, call_next):
        # CORS preflights are handled by CORSMiddleware and must not
        # consume the per-endpoint request budget.
        if request.method == "OPTIONS":
            return await call_next(request)

        bucket = self._bucket(request.url.path)
        if bucket is None:
            return await call_next(request)

        key = (self._client_ip(request), bucket)
        now = time.monotonic()
        hits = self._hits[key]

        while hits and now - hits[0] > self.WINDOW_SECONDS:
            hits.popleft()

        if not hits:
            # Drop stale keys so memory stays bounded by active clients only.
            self._hits.pop(key, None)
            hits = self._hits[key]

        if len(hits) >= self.limits[bucket]:
            retry_after = max(1, int(self.WINDOW_SECONDS - (now - hits[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
        return await call_next(request)
