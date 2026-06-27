"""Тесты middleware gateway.

Throttling проверяем напрямую как вызываемый объект (фейковый handler + data).
CallbackAnswer — только короткое замыкание для не-колбэков; саму логику ответа
обеспечивает протестированный aiogram, дублировать не нужно.
"""

from aiogram.types import User

from gateway.middlewares import SafeCallbackAnswerMiddleware, ThrottlingMiddleware


def _user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name="N")


async def test_throttling_drops_second_update_within_window() -> None:
    middleware = ThrottlingMiddleware(throttle_time=60)
    calls: list[int] = []

    async def handler(event, data):
        calls.append(1)
        return "ok"

    event = object()
    data = {"event_from_user": _user(1)}

    first = await middleware(handler, event, data)
    second = await middleware(handler, event, data)

    assert first == "ok"
    assert second is None  # молчаливый дроп
    assert len(calls) == 1


async def test_throttling_passes_different_users() -> None:
    middleware = ThrottlingMiddleware(throttle_time=60)
    calls: list[int] = []

    async def handler(event, data):
        calls.append(1)
        return "ok"

    event = object()
    await middleware(handler, event, {"event_from_user": _user(1)})
    await middleware(handler, event, {"event_from_user": _user(2)})

    assert len(calls) == 2


async def test_callback_answer_passes_non_callback_events() -> None:
    middleware = SafeCallbackAnswerMiddleware()
    called: list[int] = []

    async def handler(event, data):
        called.append(1)
        return "ok"

    result = await middleware(handler, object(), {})

    assert result == "ok"
    assert called
