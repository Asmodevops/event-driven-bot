from datetime import datetime

from dishka_faststream import setup_dishka
from faststream import FastStream
from faststream.nats import JStream, NatsBroker, TestNatsBroker
import pytest
import pytest_asyncio
from sqlalchemy import select

from contracts import (
    IncomingCallback,
    IncomingMessage,
    OutgoingMessage,
    Streams,
    Subjects,
    TelegramChat,
    TelegramUser,
)
from database.models import User
from user_service.config import Settings
from user_service.handlers import router
from user_service.ioc import create_container


pytestmark = pytest.mark.integration


def incoming(user_id: int, first_name: str = "Neo") -> IncomingMessage:
    return IncomingMessage(
        update_id=user_id,
        message_id=1,
        date=datetime(2026, 1, 1),
        chat=TelegramChat(id=user_id, type="private"),
        from_user=TelegramUser(
            id=user_id,
            is_bot=False,
            first_name=first_name,
            full_name=first_name,
            username="neo",
        ),
        text="/start",
        trace_id=f"t-{user_id}",
    )


def incoming_callback(user_id: int, data: str = "ping") -> IncomingCallback:
    return IncomingCallback(
        update_id=user_id,
        callback_id=f"cb-{user_id}",
        from_user=TelegramUser(
            id=user_id, is_bot=False, first_name="Neo", full_name="Neo", username="neo"
        ),
        chat=TelegramChat(id=user_id, type="private"),
        message_id=1,
        data=data,
        trace_id=f"t-{user_id}",
    )


@pytest_asyncio.fixture
async def wired(db_engine):
    """Поднятый контейнер + брокер user_service и перехват исходящих сообщений."""
    container = create_container(Settings())
    broker = await container.get(NatsBroker)
    broker.include_router(router)
    app = FastStream(broker)
    setup_dishka(container, app)

    captured: list[OutgoingMessage] = []

    @broker.subscriber(
        Subjects.SEND_OUT,
        stream=JStream(name=Streams.OUTGOING, subjects=[Subjects.SEND_ALL]),
    )
    async def capture(message: OutgoingMessage) -> None:
        captured.append(message)

    yield broker, captured
    await container.close()


async def test_handle_start_persists_user_and_replies(wired, session) -> None:
    broker, captured = wired
    async with TestNatsBroker(broker) as br:
        await br.publish(incoming(10), Subjects.CMD_START)
        assert len(captured) == 1
        assert captured[0].chat_id == 10
        assert "Neo" in captured[0].text
        assert captured[0].trace_id == "t-10"

    user = await session.scalar(select(User).where(User.telegram_id == 10))
    assert user is not None
    assert user.username == "neo"
    assert user.full_name == "Neo"


async def test_handle_callback_ping_replies_pong(wired) -> None:
    broker, captured = wired
    async with TestNatsBroker(broker) as br:
        await br.publish(incoming_callback(20), Subjects.CMD_CALLBACK)
        assert len(captured) == 1
        assert captured[0].chat_id == 20
        assert "Понг" in captured[0].text
        assert captured[0].trace_id == "t-20"


async def test_handle_start_is_idempotent(wired, session) -> None:
    broker, _ = wired
    command = incoming(11, first_name="Trinity")
    async with TestNatsBroker(broker) as br:
        await br.publish(command, Subjects.CMD_START)
        await br.publish(command, Subjects.CMD_START)

    users = (await session.scalars(select(User).where(User.telegram_id == 11))).all()
    assert len(users) == 1
