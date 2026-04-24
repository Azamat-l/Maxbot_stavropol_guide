from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class TokenBucket:
    capacity: int
    refill_per_sec: float
    tokens: float
    last_ts: float

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_ts
        self.last_ts = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class RateLimiter:
    """
    Простой in‑memory rate limiter.

    - Подходит как базовая защита на 1 инстанс.
    - Для горизонтального масштабирования заменить на Redis‑лимитер.
    """

    def __init__(self, per_minute: int):
        self._capacity = max(1, int(per_minute))
        self._refill_per_sec = self._capacity / 60.0
        self._buckets: dict[str, TokenBucket] = {}

    def allow(self, key: str, cost: float = 1.0) -> bool:
        b = self._buckets.get(key)
        if b is None:
            b = TokenBucket(
                capacity=self._capacity,
                refill_per_sec=self._refill_per_sec,
                tokens=float(self._capacity),
                last_ts=time.monotonic(),
            )
            self._buckets[key] = b
        return b.allow(cost=cost)
