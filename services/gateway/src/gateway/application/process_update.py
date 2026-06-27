"""Интеракторы gateway: апдейт aiogram → команда в NATS."""

import logging
from uuid import uuid4

from aiogram.types import CallbackQuery, Message

from adapters import set_trace_id
from gateway.application.parsing import parse_callback, parse_message
from gateway.publisher import CommandPublisher


logger = logging.getLogger("gateway")


class ProcessMessage:
    """Команда (например /start): родить trace_id, распарсить, опубликовать."""

    def __init__(self, publisher: CommandPublisher) -> None:
        self._publisher = publisher

    async def __call__(self, update_id: int, message: Message) -> None:
        # Здесь рождается trace_id — он поедет в полях контракта через все сервисы.
        trace_id = uuid4().hex
        set_trace_id(trace_id)
        logger.info("Команда /start от user_id=%s", message.from_user.id)
        await self._publisher.publish(parse_message(update_id, message, trace_id))


class ProcessCallback:
    """Нажатие inline-кнопки: родить trace_id, распарсить, опубликовать.

    «Часики» у пользователя гасит SafeCallbackAnswerMiddleware — здесь только
    парсим и публикуем. Сам ответ пришлёт потребитель через sender.
    """

    def __init__(self, publisher: CommandPublisher) -> None:
        self._publisher = publisher

    async def __call__(self, update_id: int, callback: CallbackQuery) -> None:
        trace_id = uuid4().hex
        set_trace_id(trace_id)
        logger.info(
            "Callback data=%s от user_id=%s", callback.data, callback.from_user.id
        )
        await self._publisher.publish(parse_callback(update_id, callback, trace_id))
