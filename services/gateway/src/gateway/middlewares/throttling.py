"""Анти-флуд: отсекает слишком частые апдейты от одного пользователя.

Работает в gateway — на входе в систему, ДО публикации в очереди. Так флуд не
тратит ресурсы очередей, БД и sender'а. Дроп молчаливый: лишний апдейт просто
не передаётся дальше (никаких ответов в очередь, иначе бы сами флудили).

Хранилище — in-memory ``TTLCache``: gateway работает в одном экземпляре (поллинг
нельзя дублировать), поэтому распределённый счётчик не нужен. Если gateway когда-
нибудь начнут масштабировать, кэш переедет в Redis.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, throttle_time: float) -> None:
        # Ключ живёт throttle_time секунд; пока он есть — апдеты юзера дропаются.
        self._cache: TTLCache[int, None] = TTLCache(maxsize=10_000, ttl=throttle_time)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Части медиа-группы (альбом) приходят пачкой — их не троттлим.
        if isinstance(event, Message) and event.media_group_id:
            return await handler(event, data)

        user: User | None = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        if user.id in self._cache:
            return None  # молчаливый дроп
        self._cache[user.id] = None
        return await handler(event, data)
