"""Тесты логики доставки sender.

Интерактор ``DeliverMessage`` решает «подтвердить или повторить», поэтому
тестируем его напрямую, передавая номер попытки. Это не требует ни NATS, ни
JetStream-метаданных. Зависимости (бот, лимитер, DLQ) подставляем вручную —
в этом и смысл слоя application. Telegram заменяется на ``MockedBot``.
"""

from aiogram.methods import SendMessage

from contracts import OutgoingMessage, Subjects
from sender.application import Ack, DeliverMessage, Nack
from sender.config import settings
from sender.rate_limiter import RateLimiter
from tests.mocked_aiogram import MockedBot


class _DLQStub:
    def __init__(self) -> None:
        self.letters = []

    async def publish(self, dead_letter) -> None:
        self.letters.append(dead_letter)


class _BoomBot:
    """Бот, у которого отправка падает временной ошибкой (сеть/5xx)."""

    async def send_message(self, *args, **kwargs):
        raise RuntimeError("network down")


def _message() -> OutgoingMessage:
    return OutgoingMessage(chat_id=5, text="hi", trace_id="t")


def _limiter() -> RateLimiter:
    return RateLimiter(rate=1000, per=1)


async def test_success_acks() -> None:
    bot = MockedBot()
    bot.add_result_for(SendMessage, ok=True)

    outcome = await DeliverMessage(bot, _limiter(), _DLQStub())(_message(), 1)

    assert isinstance(outcome, Ack)
    assert isinstance(bot.get_request(), SendMessage)


async def test_permanent_error_acks_without_dlq() -> None:
    bot = MockedBot()
    bot.add_result_for(
        SendMessage, ok=False, error_code=400, description="Bad Request: chat not found"
    )
    dlq = _DLQStub()

    outcome = await DeliverMessage(bot, _limiter(), dlq)(_message(), 1)

    # Неустранимо: подтверждаем и НЕ кладём в DLQ.
    assert isinstance(outcome, Ack)
    assert dlq.letters == []


async def test_rate_limit_nacks_with_retry_after() -> None:
    bot = MockedBot()
    bot.add_result_for(SendMessage, ok=False, error_code=429, retry_after=7)

    outcome = await DeliverMessage(bot, _limiter(), _DLQStub())(_message(), 1)

    assert outcome == Nack(delay=7.0)


async def test_transient_error_nacks_with_backoff() -> None:
    dlq = _DLQStub()

    outcome = await DeliverMessage(_BoomBot(), _limiter(), dlq)(_message(), 2)

    # backoff(2) = base * 2^(2-1) = 2.0 * 2 = 4.0
    assert outcome == Nack(delay=4.0)
    assert dlq.letters == []


async def test_transient_error_goes_to_dlq_on_last_attempt() -> None:
    dlq = _DLQStub()

    outcome = await DeliverMessage(_BoomBot(), _limiter(), dlq)(
        _message(), settings.sender_max_attempts
    )

    assert isinstance(outcome, Ack)
    assert len(dlq.letters) == 1
    letter = dlq.letters[0]
    assert letter.attempts == settings.sender_max_attempts
    assert letter.source_subject == Subjects.SEND_OUT
    assert letter.payload["chat_id"] == 5
    assert letter.trace_id == "t"
