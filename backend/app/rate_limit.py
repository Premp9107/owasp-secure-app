"""In-process login and registration limiter.

This is a single-process control. It resets when the API process restarts and
is not shared across multiple workers. See SECURITY.md.
"""

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        self._events.clear()

    def _prune(self, key: str, window: int) -> list[float]:
        now = time.monotonic()
        stamps = [stamp for stamp in self._events[key] if now - stamp < window]
        self._events[key] = stamps
        return stamps

    def is_blocked(self, key: str, limit: int, window: int) -> bool:
        return len(self._prune(key, window)) >= limit

    def record(self, key: str) -> None:
        self._events[key].append(time.monotonic())

    def clear_key(self, key: str) -> None:
        self._events.pop(key, None)


limiter = RateLimiter()
