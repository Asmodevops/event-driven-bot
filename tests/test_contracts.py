from datetime import datetime

import pytest

from contracts import (
    IncomingCallback,
    IncomingMessage,
    OutgoingMessage,
    TelegramChat,
    TelegramUser,
)


def _user(**overrides) -> TelegramUser:
    return TelegramUser(
        id=2, is_bot=False, first_name="Neo", full_name="Neo", **overrides
    )


@pytest.mark.parametrize("username", ["tester", None])
def test_incoming_message_round_trip(username: str | None) -> None:
    message = IncomingMessage(
        update_id=1,
        message_id=10,
        date=datetime(2026, 1, 1, 12, 0, 0),
        chat=TelegramChat(id=1, type="private"),
        from_user=_user(username=username),
        text="/start",
        trace_id="t",
    )
    assert IncomingMessage.model_validate_json(message.model_dump_json()) == message


def test_incoming_message_allows_no_sender() -> None:
    # У постов в каналах нет from_user.
    message = IncomingMessage(
        update_id=1,
        message_id=10,
        date=datetime(2026, 1, 1),
        chat=TelegramChat(id=-100, type="channel"),
        text="post",
        trace_id="t",
    )
    assert message.from_user is None


def test_incoming_callback_round_trip() -> None:
    callback = IncomingCallback(
        update_id=1,
        callback_id="abc",
        from_user=_user(),
        chat=TelegramChat(id=1, type="private"),
        message_id=10,
        data="press:1",
        trace_id="t",
    )
    assert IncomingCallback.model_validate_json(callback.model_dump_json()) == callback


def test_outgoing_message_parse_mode_defaults_to_none() -> None:
    message = OutgoingMessage(chat_id=1, text="hi", trace_id="t")
    assert message.parse_mode is None
