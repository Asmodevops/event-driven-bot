"""IoC-контейнер gateway.

Здесь объявлено, как собираются зависимости (бот, диспетчер, брокер, publisher).
Сервис их не создаёт сам — он запрашивает готовые у контейнера, а контейнер
внедряет их «снаружи». Settings приходит в контейнер через ``context``.
"""

from aiogram import Bot, Dispatcher
from dishka import (
    AsyncContainer,
    from_context,
    make_async_container,
    provide,
    Provider,
    Scope,
)
from dishka.integrations.aiogram import AiogramProvider
from faststream.nats import NatsBroker

from gateway.application import ProcessCallback, ProcessMessage
from gateway.config import Settings
from gateway.publisher import CommandPublisher


class GatewayProvider(Provider):
    # Settings внедряется в контейнер извне (см. context при сборке).
    settings = from_context(Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def broker(self, settings: Settings) -> NatsBroker:
        return NatsBroker(settings.nats_url)

    @provide(scope=Scope.APP)
    def command_publisher(self, broker: NatsBroker) -> CommandPublisher:
        return CommandPublisher(broker)

    # Интеракторы: dishka сам собирает их, подставляя зависимости из __init__.
    process_message = provide(ProcessMessage, scope=Scope.APP)
    process_callback = provide(ProcessCallback, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def bot(self, settings: Settings) -> Bot:
        return Bot(settings.bot_token)

    @provide(scope=Scope.APP)
    def dispatcher(self) -> Dispatcher:
        return Dispatcher()


def create_container(settings: Settings, *overrides: Provider) -> AsyncContainer:
    """Собрать контейнер. ``overrides`` (последними) подменяют зависимости в тестах."""
    return make_async_container(
        GatewayProvider(),
        AiogramProvider(),
        *overrides,
        context={Settings: settings},
    )
