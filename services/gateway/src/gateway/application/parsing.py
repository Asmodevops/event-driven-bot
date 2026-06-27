"""Разбор объектов aiogram в контракт (чистые функции, удобно тестировать)."""

from aiogram.types import CallbackQuery, Chat, Message, User

from contracts import IncomingCallback, IncomingMessage, TelegramChat, TelegramUser


def _telegram_user(user: User) -> TelegramUser:
    return TelegramUser(
        id=user.id,
        is_bot=user.is_bot,
        first_name=user.first_name,
        full_name=user.full_name,
        last_name=user.last_name,
        username=user.username,
        language_code=user.language_code,
    )


def _parse_user(user: User | None) -> TelegramUser | None:
    return _telegram_user(user) if user is not None else None


def _parse_chat(chat: Chat) -> TelegramChat:
    return TelegramChat(
        id=chat.id,
        type=chat.type,
        title=chat.title,
        username=chat.username,
    )


def parse_message(update_id: int, message: Message, trace_id: str) -> IncomingMessage:
    """Собрать ``IncomingMessage`` из объектов aiogram."""
    return IncomingMessage(
        update_id=update_id,
        message_id=message.message_id,
        date=message.date,
        chat=_parse_chat(message.chat),
        from_user=_parse_user(message.from_user),
        text=message.text,
        trace_id=trace_id,
    )


def parse_callback(
    update_id: int, callback: CallbackQuery, trace_id: str
) -> IncomingCallback:
    """Собрать ``IncomingCallback`` из объектов aiogram.

    У callback всегда есть ``from_user``, а вот сообщение с кнопкой может быть
    недоступно (старое/удалённое) — тогда ``chat``/``message_id`` пустые.
    """
    msg = callback.message
    return IncomingCallback(
        update_id=update_id,
        callback_id=callback.id,
        from_user=_telegram_user(callback.from_user),
        chat=_parse_chat(msg.chat) if msg is not None else None,
        message_id=msg.message_id if msg is not None else None,
        data=callback.data,
        trace_id=trace_id,
    )
