"""Автоответ на callback-запросы (нажатия inline-кнопок).

Telegram требует ответить на каждый callback (``answerCallbackQuery``), иначе у
пользователя бесконечно крутятся «часики» на кнопке. Это лёгкий обязательный
ack, который надо сделать сразу при обработке апдейта — поэтому gateway делает
его напрямую (в очередь→sender гонять нельзя, добавит задержку и сломает UX).

Расширяет стандартный ``CallbackAnswerMiddleware`` aiogram: подавляет
``TelegramBadRequest`` (например, если колбэк уже устарел) — такой ответ всё
равно ни на что не влияет, а падать из-за него не нужно.
"""

from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from aiogram import loggers
from aiogram.dispatcher.flags import get_flag
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery
from aiogram.types import CallbackQuery, TelegramObject
from aiogram.utils.callback_answer import CallbackAnswer, CallbackAnswerMiddleware


class SafeCallbackAnswerMiddleware(CallbackAnswerMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        callback_answer = data["callback_answer"] = self.construct_callback_answer(
            properties=get_flag(data, "callback_answer")
        )

        if not callback_answer.disabled and callback_answer.answered:
            await self._safe_answer(event, callback_answer)
        try:
            return await handler(event, data)
        finally:
            if not callback_answer.disabled and not callback_answer.answered:
                await self._safe_answer(event, callback_answer)

    @staticmethod
    async def _safe_answer(
        event: CallbackQuery,
        callback_answer: CallbackAnswer,
    ) -> AnswerCallbackQuery | None:
        with suppress(TelegramBadRequest):
            loggers.middlewares.info("Safe answer to callback query id=%s", event.id)
            return await event.answer(
                text=callback_answer.text,
                show_alert=callback_answer.show_alert,
                url=callback_answer.url,
                cache_time=callback_answer.cache_time,
            )
        return None
