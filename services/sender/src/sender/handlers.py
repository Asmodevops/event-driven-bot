"""Роутер sender: тонкая обёртка над слоем application.

Единственная точка отправки в Telegram: тянет сообщения из стрима ``outgoing``
батчами (поштучная обработка). Подтверждением сообщений управляем вручную
(``AckPolicy.MANUAL``), чтобы делать повторы с задержкой: хэндлер читает номер
попытки из JetStream, зовёт интерактор ``DeliverMessage`` и применяет его
вердикт ack/nack. Вся логика доставки — в ``sender.application``.
"""

import logging

from dishka import FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import JStream, NatsRouter, PullSub
from faststream.nats.annotations import NatsMessage
from nats.js.api import ConsumerConfig

from adapters import set_trace_id
from contracts import OutgoingMessage, Streams, Subjects
from sender.application import DeliverMessage, Nack
from sender.config import settings


logger = logging.getLogger("sender")

router = NatsRouter()
_outgoing_stream = JStream(name=Streams.OUTGOING, subjects=[Subjects.SEND_ALL])


@router.subscriber(
    Subjects.SEND_OUT,
    stream=_outgoing_stream,
    durable="sender",
    pull_sub=PullSub(
        batch_size=settings.sender_batch_size,
        timeout=settings.sender_batch_timeout,
    ),
    ack_policy=AckPolicy.MANUAL,
    # max_deliver ограничивает число попыток на стороне JetStream.
    config=ConsumerConfig(max_deliver=settings.sender_max_attempts),
)
@inject
async def deliver(
    message: OutgoingMessage,
    msg: NatsMessage,
    deliver_message: FromDishka[DeliverMessage],
) -> None:
    set_trace_id(message.trace_id)
    attempt = msg.raw_message.metadata.num_delivered
    outcome = await deliver_message(message, attempt)
    if isinstance(outcome, Nack):
        await msg.nack(delay=outcome.delay)
    else:
        await msg.ack()
