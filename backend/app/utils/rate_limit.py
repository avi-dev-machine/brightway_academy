"""In-process sliding-window rate limiter.

Limits are per worker process. Behind a reverse proxy run uvicorn with --proxy-headers
so request.client reflects the real client address.
"""

import threading
import time
from collections import deque

from fastapi import Request

from app.exceptions import RateLimitedError

_MAX_TRACKED_KEYS = 10_000


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        """Record a hit for `key`; raise RateLimitedError when the limit is exceeded."""
        if self.limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(self.window - (now - hits[0])) + 1)
                raise RateLimitedError(headers={"Retry-After": str(retry_after)})
            hits.append(now)
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._prune(now)

    def _prune(self, now: float) -> None:
        stale = [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
