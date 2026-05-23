"""Rate-limit gate.

Token-bucket per (source, key) where source is a collector / MCP tool name.
In-memory only; swap for Redis-backed limiter before multi-process deploy.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from agents.supervisor.state import SupervisorState, Violation


@dataclass
class Bucket:
    capacity: float
    refill_per_sec: float
    tokens: float
    last: float


class RateLimiter:
    """Process-local token-bucket limiter."""

    def __init__(self) -> None:
        self._buckets: dict[str, Bucket] = {}
        self._lock = threading.Lock()

    def configure(self, key: str, capacity: float, refill_per_sec: float) -> None:
        with self._lock:
            self._buckets[key] = Bucket(
                capacity=capacity,
                refill_per_sec=refill_per_sec,
                tokens=capacity,
                last=time.monotonic(),
            )

    def try_take(self, key: str, cost: float = 1.0) -> bool:
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                # Unknown keys are unrestricted (but logged by the caller).
                return True
            now = time.monotonic()
            elapsed = now - bucket.last
            bucket.tokens = min(
                bucket.capacity,
                bucket.tokens + elapsed * bucket.refill_per_sec,
            )
            bucket.last = now
            if bucket.tokens < cost:
                return False
            bucket.tokens -= cost
            return True


# Module-level default. Swap out in tests by assigning a fresh RateLimiter.
limiter = RateLimiter()


def check_rate_limit(
    state: SupervisorState,
    key: str,
    cost: float = 1.0,
) -> list[Violation]:
    if limiter.try_take(key, cost):
        return []
    return [
        Violation(
            kind="rate_limit",
            detail=f"Rate limit exhausted for {key!r}.",
            raised_at=datetime.now(timezone.utc),
        )
    ]
