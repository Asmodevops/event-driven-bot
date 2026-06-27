from faststream.nats import JStream, NatsBroker

from contracts import OutgoingMessage, Streams, Subjects


class OutgoingPublisher:
    """Публикует ответ пользователю в стрим исходящих сообщений (его читает sender)."""

    def __init__(self, broker: NatsBroker) -> None:
        stream = JStream(name=Streams.OUTGOING, subjects=[Subjects.SEND_ALL])
        self._publisher = broker.publisher(Subjects.SEND_OUT, stream=stream)

    async def publish(self, message: OutgoingMessage) -> None:
        await self._publisher.publish(message)
