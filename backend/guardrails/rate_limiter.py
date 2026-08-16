import time
import threading
from typing import Dict, List, Tuple, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from backend.config.settings import settings

class SlidingWindowRateLimiter:
    """
    Thread-safe sliding-window rate limiter tracking per-client IP request timestamps.
    Automatically purges expired window entries to prevent memory bloat.
    """
    def __init__(self, requests_per_minute: int = 60, window_seconds: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """
        Determines if the client IP is within its allowed rate limit.
        Returns: (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            if client_ip not in self._history:
                self._history[client_ip] = [now]
                return True, 0

            # Filter timestamps within current sliding window
            timestamps = [t for t in self._history[client_ip] if t > window_start]
            
            if len(timestamps) >= self.requests_per_minute:
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(oldest_in_window + self.window_seconds - now))
                self._history[client_ip] = timestamps
                return False, retry_after

            timestamps.append(now)
            self._history[client_ip] = timestamps
            return True, 0

    def reset(self):
        with self._lock:
            self._history.clear()


# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter(
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)


def get_client_ip(request: Request) -> str:
    """Extracts client IP considering standard reverse-proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take first IP in comma-separated list
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that throttles `/api/text/query`, `/api/text/query/stream`,
    and `/api/voice/query` requests against volumetric spam and DDoS attacks.
    """
    async def dispatch(self, request: Request, call_next):
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)

        # Rate limit only query generation endpoints
        path = request.url.path
        if path.startswith("/api/text/query") or path.startswith("/api/voice/query"):
            client_ip = get_client_ip(request)
            allowed, retry_after = rate_limiter.is_allowed(client_ip)

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Rate limit is {rate_limiter.requests_per_minute} req/min. Please wait {retry_after}s before retrying.",
                        "retry_after": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
                )

        return await call_next(request)
