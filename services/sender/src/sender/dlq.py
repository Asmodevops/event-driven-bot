from faststream.nats import JStream, NatsBroker

from contracts import DeadLetter, Streams, Subjects


class DeadLetterPublisher:
    """Складывает не доставленные после всех попыток сообщения в DLQ-стрим."""

    def __init__(self, broker: NatsBroker) -> None:
        stream = JStream(name=Streams.DLQ, subjects=[Subjects.DLQ_ALL])
        self._publisher = broker.publisher(Subjects.SEND_DLQ, stream=stream)

    async def publish(self, dead_letter: DeadLetter) -> None:
        await self._publisher.publish(dead_letter)
