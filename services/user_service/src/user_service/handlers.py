"""Роутер user_service: тонкая транспортная обёртка над слоем application.

Хэндлеры здесь только читают сообщение из стрима ``commands``, привязывают
trace_id и зовут интерактор. Вся логика — в ``user_service.application``.
"""

from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import JStream, NatsRouter, PullSub

from adapters import set_trace_id
from contracts import IncomingCallback, IncomingMessage, Streams, Subjects
from user_service.application import AnswerCallback, RegisterUser


router = NatsRouter()
_commands_stream = JStream(name=Streams.COMMANDS, subjects=[Subjects.CMD_ALL])


@router.subscriber(
    Subjects.CMD_START,
    stream=_commands_stream,
    durable="user_service",
    pull_sub=PullSub(batch_size=10, timeout=1.0),
    # При ошибке хэндлера сообщение переотправляется, а не теряется.
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
@inject
async def handle_start(
    message: IncomingMessage,
    register_user: FromDishka[RegisterUser],
) -> None:
    set_trace_id(message.trace_id)
    await register_user(message)


@router.subscriber(
    Subjects.CMD_CALLBACK,
    stream=_commands_stream,
    durable="user_service_callbacks",
    pull_sub=PullSub(batch_size=10, timeout=1.0),
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
@inject
async def handle_callback(
    callback: IncomingCallback,
    answer_callback: FromDishka[AnswerCallback],
) -> None:
    set_trace_id(callback.trace_id)
    await answer_callback(callback)
