"""Pydantic-модели, которые летают через NATS.

Их (де)сериализует каждый сервис, поэтому этот модуль — единый источник правды
о формате сообщений. Вместо отдельного типа под каждую команду gateway публикует
один универсальный ``IncomingMessage`` (и ``IncomingCallback``) с полностью
распарсенным апдейтом; маршрутизация — по NATS subject, а не по типу payload.

Сквозной ``trace_id`` помогает прослеживать одно действие пользователя через все
сервисы. Модуль не зависит от aiogram — разбор aiogram→контракт живёт в gateway.
"""

from datetime import datetime

from pydantic import BaseModel


class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    full_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramChat(BaseModel):
    id: int
    # "private" | "group" | "supergroup" | "channel"
    type: str
    title: str | None = None
    username: str | None = None


class IncomingMessage(BaseModel):
    """Полностью распарсенное входящее сообщение Telegram."""

    update_id: int
    message_id: int
    date: datetime
    chat: TelegramChat
    # Отсутствует у постов в каналах.
    from_user: TelegramUser | None = None
    text: str | None = None
    trace_id: str


class IncomingCallback(BaseModel):
    """Распарсенный callback-запрос (нажатие inline-кнопки)."""

    update_id: int
    # callback_query.id — нужен, чтобы ответить на колбэк.
    callback_id: str
    from_user: TelegramUser
    # Сообщение, к которому прикреплена кнопка (может быть недоступно/старым).
    chat: TelegramChat | None = None
    message_id: int | None = None
    # callback_query.data (≤64 байт). Полезная нагрузка кнопки — кладите сюда что
    # нужно, например id владельца, чтобы потребитель сравнил его с from_user.id и
    # отклонил нажатия чужих людей в групповом чате.
    data: str | None = None
    trace_id: str


class Button(BaseModel):
    """Inline-кнопка: подпись и ``callback_data``.

    ``callback_data`` (≤64 байт) прилетит обратно в ``IncomingCallback.data``,
    когда пользователь нажмёт кнопку — по нему потребитель решает, что делать.
    Контракт не зависит от aiogram: sender сам собирает из этого клавиатуру.
    """

    text: str
    callback_data: str


class OutgoingMessage(BaseModel):
    """Сообщение, которое sender должен доставить пользователю.

    Повторяет нужные параметры Telegram ``sendMessage``.
    """

    chat_id: int
    text: str
    parse_mode: str | None = None
    # Inline-клавиатура: список рядов кнопок. ``None`` — без клавиатуры.
    buttons: list[list[Button]] | None = None
    trace_id: str


class DeadLetter(BaseModel):
    """«Мёртвое» сообщение: не удалось обработать после всех попыток.

    Складывается в отдельный DLQ-стрим, чтобы не зацикливать обработку и
    сохранить контекст для разбора: что это было, откуда, почему упало и
    сколько раз пытались.
    """

    # subject, из которого пришло исходное сообщение.
    source_subject: str
    # Исходное сообщение целиком (как JSON), чтобы можно было переотправить.
    payload: dict
    # Текст последней ошибки.
    error: str
    # Сколько раз пытались обработать.
    attempts: int
    trace_id: str | None = None
