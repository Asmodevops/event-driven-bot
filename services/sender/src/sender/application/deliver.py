"""Интерактор доставки: отправить сообщение и решить судьбу (ack/nack).

Виды ошибок:
- **неустранимые** (``chat not found``, бот заблокирован) — повтор не поможет,
  ack, в DLQ не кладём (это норма жизни);
- **лимит Telegram** (``429 RetryAfter``) — nack с задержкой ``retry_after``;
- **временные/неизвестные** (сеть, 5xx, баги) — nack с экспоненциальным backoff;
  после ``max_attempts`` попыток — в DLQ и ack.
"""

from dataclasses import dataclass
import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from contracts import Button, DeadLetter, OutgoingMessage, Subjects
from sender.config import settings
from sender.dlq import DeadLetterPublisher
from sender.rate_limiter import RateLimiter


logger = logging.getLogger("sender")


def _build_markup(
    buttons: list[list[Button]] | None,
) -> InlineKeyboardMarkup | None:
    """Собрать inline-клавиатуру aiogram из кнопок контракта (или None)."""
    if not buttons:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b.text, callback_data=b.callback_data)
                for b in row
            ]
            for row in buttons
        ]
    )


@dataclass(frozen=True, slots=True)
class Ack:
    """Подтвердить сообщение (обработано или дальше повторять бессмысленно)."""


@dataclass(frozen=True, slots=True)
class Nack:
    """Вернуть сообщение в очередь для повтора через ``delay`` секунд."""

    delay: float


class DeliverMessage:
    """Отправляет сообщение в Telegram и возвращает вердикт ``Ack``/``Nack``."""

    def __init__(
        self,
        bot: Bot,
        limiter: RateLimiter,
        dlq: DeadLetterPublisher,
    ) -> None:
        self._bot = bot
        self._limiter = limiter
        self._dlq = dlq

    async def __call__(self, message: OutgoingMessage, attempt: int) -> Ack | Nack:
        """``attempt`` — номер текущей попытки (1 — первая)."""
        await self._limiter.acquire()
        try:
            await self._bot.send_message(
                message.chat_id,
                message.text,
                parse_mode=message.parse_mode,
                reply_markup=_build_markup(message.buttons),
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning(
                "Сообщение не доставлено chat_id=%s: %s", message.chat_id, exc.message
            )
            return Ack()
        except TelegramRetryAfter as exc:
            logger.warning("Лимит Telegram, повтор через %s с", exc.retry_after)
            return Nack(delay=float(exc.retry_after))
        except Exception as exc:
            if attempt >= settings.sender_max_attempts:
                logger.error(
                    "Доставка провалена после %s попыток chat_id=%s: %s",
                    attempt,
                    message.chat_id,
                    exc,
                )
                await self._dlq.publish(
                    DeadLetter(
                        source_subject=Subjects.SEND_OUT,
                        payload=message.model_dump(mode="json"),
                        error=str(exc),
                        attempts=attempt,
                        trace_id=message.trace_id,
                    )
                )
                return Ack()
            delay = settings.backoff_delay(attempt)
            logger.warning(
                "Ошибка доставки (попытка %s), повтор через %s с: %s",
                attempt,
                delay,
                exc,
            )
            return Nack(delay=delay)
        else:
            return Ack()
