import os


# Выставляем переменные окружения ДО импорта сервисов: их config.py создаёт
# экземпляр Settings на уровне модуля. Значения по умолчанию — локальная инфра.
os.environ.setdefault("BOT_TOKEN", "42:TESTTOKEN")
os.environ.setdefault("NATS_URL", "nats://localhost:4222")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/q_bot_test",
)

import psycopg
import pytest
import pytest_asyncio
from sqlalchemy.engine import make_url

from database import Base
from database.engine import create_engine, create_session_factory
from tests.mocked_aiogram import MockedBot


@pytest.fixture
def bot() -> MockedBot:
    return MockedBot()


def _ensure_database(url: str) -> None:
    """Создать тестовую БД на сервере, если её ещё нет."""
    parsed = make_url(url)
    admin = (
        f"host={parsed.host} port={parsed.port} "
        f"user={parsed.username} password={parsed.password} dbname=postgres"
    )
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute(
            "select 1 from pg_database where datname = %s", (parsed.database,)
        ).fetchone()
        if not exists:
            conn.execute(f'create database "{parsed.database}"')


@pytest_asyncio.fixture
async def db_engine():
    """Готовая тестовая БД: схема создана, таблицы пусты (на каждый тест)."""
    url = os.environ["DATABASE_URL"]
    _ensure_database(url)
    engine = create_engine(url)
    # Пересоздаём схему с нуля, чтобы она всегда совпадала с текущими моделями.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_engine):
    """Сессия для проверок в тесте (та же БД, куда пишет сервис)."""
    factory = create_session_factory(db_engine)
    async with factory() as s:
        yield s
