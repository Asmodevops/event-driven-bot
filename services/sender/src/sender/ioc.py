"""IoC-контейнер sender.

Описывает сборку зависимостей: брокер, бот (для отправки) и лимитер скорости.
Хэндлер получает их готовыми через внедрение.
"""

from aiogram import Bot
from dishka import (
    AsyncContainer,
    from_context,
    make_async_container,
    provide,
    Provider,
    Scope,
)
from dishka_faststream import FastStreamProvider
from faststream.nats import NatsBroker

from sender.application import DeliverMessage
from sender.config import Settings
from sender.dlq import DeadLetterPublisher
from sender.rate_limiter import RateLimiter


class SenderProvider(Provider):
    settings = from_context(Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def broker(self, settings: Settings) -> NatsBroker:
        return NatsBroker(settings.nats_url)

    @provide(scope=Scope.APP)
    def bot(self, settings: Settings) -> Bot:
        return Bot(settings.bot_token)

    @provide(scope=Scope.APP)
    def limiter(self, settings: Settings) -> RateLimiter:
        return RateLimiter(rate=settings.sender_rate, per=settings.sender_per)

    @provide(scope=Scope.APP)
    def dlq(self, broker: NatsBroker) -> DeadLetterPublisher:
        return DeadLetterPublisher(broker)

    # Интерактор: dishka сам собирает его, подставляя зависимости из __init__.
    deliver_message = provide(DeliverMessage, scope=Scope.APP)


def create_container(settings: Settings, *overrides: Provider) -> AsyncContainer:
    """Собрать контейнер. ``overrides`` (последними) подменяют зависимости в тестах."""
    return make_async_container(
        SenderProvider(),
        FastStreamProvider(),
        *overrides,
        context={Settings: settings},
    )
