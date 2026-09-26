"""Small in-memory rate limits for public endpoints (sign-in codes, citizen reports, contact form).

One API process keeps its own counters; that is enough for the pilot (one process). With several
processes behind a load balancer, move the counters to Redis (see docs/scaling.md).
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from .config import settings

_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """The caller's IP. X-Forwarded-For is trusted only when TRUST_PROXY=true (behind our own proxy)."""
    if settings().trust_proxy:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hit(bucket: str, key: str, limit: int, window_s: int) -> None:
    """Count one call; raise 429 (with Retry-After) when `key` made more than `limit` calls in `window_s`."""
    now = time.monotonic()
    q = _hits[f"{bucket}:{key}"]
    while q and now - q[0] > window_s:
        q.popleft()
    if len(q) >= limit:
        retry = int(window_s - (now - q[0])) + 1
        raise HTTPException(
            429, f"Too many requests — try again in {retry} s", headers={"Retry-After": str(retry)}
        )
    q.append(now)


def per_ip(request: Request, bucket: str, limit: int, window_s: int) -> None:
    hit(bucket, client_ip(request), limit, window_s)


def reset() -> None:
    """Tests only."""
    _hits.clear()
