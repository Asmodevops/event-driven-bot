import asyncio
import time


class RateLimiter:
    """Простой глобальный токен-бакет.

    Разрешает ``rate`` операций за ``per`` секунд, пополняясь непрерывно. Этого
    достаточно, чтобы держать глобальный лимит Telegram, пока sender в одном
    экземпляре; per-chat троттлинг и распределённый бакет в Redis — потом, если
    sender начнут масштабировать.
    """

    def __init__(self, rate: float, per: float) -> None:
        self._capacity = rate
        self._tokens = rate
        self._refill_per_second = rate / per
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self._tokens = min(
                    self._capacity,
                    self._tokens + (now - self._updated_at) * self._refill_per_second,
                )
                self._updated_at = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                await asyncio.sleep((1 - self._tokens) / self._refill_per_second)
