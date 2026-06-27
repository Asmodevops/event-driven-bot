"""IoC-контейнер user_service.

Описывает сборку зависимостей: брокер, publisher, движок БД, фабрику сессий,
саму сессию (на каждое сообщение) и репозиторий. Хэндлер получает их готовыми.
"""

from collections.abc import AsyncIterable

from dishka import (
    AnyOf,
    AsyncContainer,
    from_context,
    make_async_container,
    provide,
    Provider,
    Scope,
)
from dishka_faststream import FastStreamProvider
from faststream.nats import NatsBroker
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine, AsyncSession

from adapters import IDGenerator
from database import create_engine, create_session_factory
from database.repositories import UserRepository
from domain import UoW
from user_service.application import AnswerCallback, RegisterUser
from user_service.config import Settings
from user_service.publisher import OutgoingPublisher


class UserServiceProvider(Provider):
    settings = from_context(Settings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def broker(self, settings: Settings) -> NatsBroker:
        return NatsBroker(settings.nats_url)

    @provide(scope=Scope.APP)
    def id_generator(self) -> IDGenerator:
        return IDGenerator()

    @provide(scope=Scope.APP)
    def outgoing_publisher(self, broker: NatsBroker) -> OutgoingPublisher:
        return OutgoingPublisher(broker)

    @provide(scope=Scope.APP)
    def engine(self, settings: Settings) -> AsyncEngine:
        return create_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )

    @provide(scope=Scope.APP)
    def session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return create_session_factory(engine)

    # Своя сессия на каждое обработанное сообщение (scope REQUEST).
    # Тот же объект отдаём и как AsyncSession (для репозитория), и как UoW
    # (для управления транзакцией в хэндлере) — у сессии уже есть commit/rollback.
    @provide(scope=Scope.REQUEST)
    async def session(
        self, factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AnyOf[AsyncSession, UoW]]:
        async with factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def users(self, session: AsyncSession) -> UserRepository:
        return UserRepository(session)

    # Интеракторы: dishka сам собирает их, подставляя зависимости из __init__.
    register_user = provide(RegisterUser, scope=Scope.REQUEST)
    answer_callback = provide(AnswerCallback, scope=Scope.REQUEST)


def create_container(settings: Settings, *overrides: Provider) -> AsyncContainer:
    """Собрать контейнер. ``overrides`` (последними) подменяют зависимости в тестах."""
    return make_async_container(
        UserServiceProvider(),
        FastStreamProvider(),
        *overrides,
        context={Settings: settings},
    )
