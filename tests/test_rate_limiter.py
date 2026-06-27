import time

from sender.rate_limiter import RateLimiter


async def test_allows_burst_up_to_capacity() -> None:
    limiter = RateLimiter(rate=5, per=1.0)
    start = time.monotonic()
    for _ in range(5):
        await limiter.acquire()
    # Полный бакет выдаёт всю ёмкость без ожидания.
    assert time.monotonic() - start < 0.1


async def test_throttles_beyond_capacity() -> None:
    # Пополнение 5 токенов/сек → 6-й токен должен подождать ~0.2с.
    limiter = RateLimiter(rate=5, per=1.0)
    for _ in range(5):
        await limiter.acquire()

    start = time.monotonic()
    await limiter.acquire()
    assert time.monotonic() - start >= 0.15
