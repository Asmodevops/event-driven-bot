from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)


def create_engine(
    database_url: str,
    *,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 1800,
) -> AsyncEngine:
    """Создать движок БД с настроенным пулом соединений.

    Дефолт SQLAlchemy (pool_size=5) мал под нагрузку: при сотнях запросов в
    секунду и нескольких инстансах сервиса соединения кончатся первыми.
    - ``pool_size`` — постоянных соединений в пуле;
    - ``max_overflow`` — дополнительных при всплеске (сверх pool_size);
    - ``pool_timeout`` — сколько ждать свободное соединение, прежде чем упасть;
    - ``pool_recycle`` — пересоздавать соединение раз в N секунд (чтобы БД не
      рвала «протухшие» коннекты).
    """
    return create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
