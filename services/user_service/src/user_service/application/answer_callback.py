"""Сценарий: ответить на нажатие inline-кнопки."""

import logging

from contracts import IncomingCallback, OutgoingMessage
from user_service import keyboards, lexicon
from user_service.publisher import OutgoingPublisher


logger = logging.getLogger("user_service")


class AnswerCallback:
    """Решает по ``data`` нажатой кнопки, что ответить пользователю.

    Эталонный путь колбэка: gateway распарсил нажатие → сюда; «часики» у
    пользователя gateway уже погасил (SafeCallbackAnswerMiddleware).
    """

    def __init__(self, publisher: OutgoingPublisher) -> None:
        self._publisher = publisher

    async def __call__(self, callback: IncomingCallback) -> None:
        # Сообщение с кнопкой могло устареть — тогда отвечать некуда.
        if callback.chat is None:
            return

        if callback.data == keyboards.PING:
            logger.info("Колбэк ping от telegram_id=%s", callback.from_user.id)
            await self._publisher.publish(
                OutgoingMessage(
                    chat_id=callback.chat.id,
                    text=lexicon.PONG,
                    trace_id=callback.trace_id,
                )
            )
