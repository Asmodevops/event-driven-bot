from datetime import datetime

from aiogram import Dispatcher
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from dishka.integrations.aiogram import setup_dishka
from faststream.nats import JStream, NatsBroker, TestNatsBroker

from contracts import IncomingCallback, IncomingMessage, Streams, Subjects
from gateway.application import parse_callback, parse_message
from gateway.config import Settings
from gateway.handlers import router
from gateway.ioc import create_container
from gateway.publisher import CommandPublisher
from tests.mocked_aiogram import MockedBot


def make_message(user_id: int, text: str) -> Message:
    user = User(id=user_id, is_bot=False, first_name="Neo", username="tester")
    chat = Chat(id=user_id, type=ChatType.PRIVATE)
    return Message(
        message_id=5, from_user=user, chat=chat, date=datetime.now(), text=text
    )


def make_callback(user_id: int, data: str) -> CallbackQuery:
    user = User(id=user_id, is_bot=False, first_name="Neo", username="tester")
    return CallbackQuery(
        id="cb1",
        from_user=user,
        chat_instance="ci",
        message=make_message(user_id, "сообщение с кнопкой"),
        data=data,
    )


def test_parse_message_extracts_fields() -> None:
    parsed = parse_message(42, make_message(777, "/start"), trace_id="abc123")
    assert parsed.update_id == 42
    assert parsed.message_id == 5
    assert parsed.text == "/start"
    assert parsed.chat.id == 777
    assert parsed.chat.type == "private"
    assert parsed.from_user is not None
    assert parsed.from_user.id == 777
    assert parsed.from_user.username == "tester"
    assert parsed.trace_id == "abc123"


def test_parse_callback_extracts_fields() -> None:
    parsed = parse_callback(7, make_callback(777, "ping"), trace_id="t1")
    assert parsed.update_id == 7
    assert parsed.callback_id == "cb1"
    assert parsed.from_user.id == 777
    assert parsed.data == "ping"
    assert parsed.chat is not None
    assert parsed.chat.id == 777
    assert parsed.message_id == 5
    assert parsed.trace_id == "t1"


async def test_gateway_routes_command_and_callback(bot: MockedBot) -> None:
    """Сквозной путь gateway: /start едет в CMD_START, нажатие — в CMD_CALLBACK.

    Роутер aiogram цепляется к диспетчеру один раз (его нельзя приложить к двум),
    поэтому обе ветки проверяем в одном тесте.
    """
    container = create_container(Settings())
    broker = await container.get(NatsBroker)
    dp = await container.get(Dispatcher)
    await container.get(CommandPublisher)
    dp.include_router(router)
    setup_dishka(container, dp)

    commands: list[IncomingMessage] = []
    callbacks: list[IncomingCallback] = []
    stream = JStream(name=Streams.COMMANDS, subjects=[Subjects.CMD_ALL])

    @broker.subscriber(Subjects.CMD_START, stream=stream)
    async def capture_command(message: IncomingMessage) -> None:
        commands.append(message)

    @broker.subscriber(Subjects.CMD_CALLBACK, stream=stream)
    async def capture_callback(callback: IncomingCallback) -> None:
        callbacks.append(callback)

    async with TestNatsBroker(broker):
        command_result = await dp.feed_update(
            bot, Update(update_id=1, message=make_message(777, "/start"))
        )
        callback_result = await dp.feed_update(
            bot, Update(update_id=2, callback_query=make_callback(777, "ping"))
        )

        assert command_result is not UNHANDLED
        assert len(commands) == 1
        assert commands[0].from_user.id == 777
        assert commands[0].update_id == 1

        assert callback_result is not UNHANDLED
        assert len(callbacks) == 1
        assert callbacks[0].data == "ping"
        assert callbacks[0].from_user.id == 777
        assert callbacks[0].update_id == 2

    await container.close()
