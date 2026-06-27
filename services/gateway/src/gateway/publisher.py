from faststream.nats import JStream, NatsBroker

from contracts import IncomingCallback, IncomingMessage, Streams, Subjects


class CommandPublisher:
    """Публикует распарсенный входящий апдейт в стрим команд.

    Внутри держит publisher-объекты FastStream, привязанные к стриму — благодаря
    этому стрим гарантированно создаётся при старте брокера. Сабджект выбирается
    по типу апдейта: команда и нажатие кнопки едут в разные сабджекты одного
    стрима, чтобы у каждого был свой консьюмер.
    """

    def __init__(self, broker: NatsBroker) -> None:
        stream = JStream(name=Streams.COMMANDS, subjects=[Subjects.CMD_ALL])
        self._commands = broker.publisher(Subjects.CMD_START, stream=stream)
        self._callbacks = broker.publisher(Subjects.CMD_CALLBACK, stream=stream)

    async def publish(self, message: IncomingMessage | IncomingCallback) -> None:
        if isinstance(message, IncomingCallback):
            await self._callbacks.publish(message)
        else:
            await self._commands.publish(message)
