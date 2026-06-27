"""Точка входа sender.

Единственный экземпляр, который шлёт сообщения в Telegram с соблюдением лимитов.
Подписан на стрим ``outgoing`` (durable pull-консьюмер).
"""

import asyncio
import logging

from aiogram import Bot
from dishka_faststream import setup_dishka
from faststream import FastStream
from faststream.nats import NatsBroker

from adapters import configure_logging
from sender.config import settings
from sender.dlq import DeadLetterPublisher
from sender.handlers import router
from sender.ioc import create_container


logger = logging.getLogger("sender")


async def main() -> None:
    configure_logging("sender")

    container = create_container(settings)
    broker = await container.get(NatsBroker)
    # Форсируем создание DLQ-publisher до старта, чтобы DLQ-стрим объявился.
    await container.get(DeadLetterPublisher)
    broker.include_router(router)

    app = FastStream(broker)
    setup_dishka(container, app)

    @app.after_shutdown
    async def _close() -> None:
        bot = await container.get(Bot)
        await bot.session.close()
        await container.close()

    logger.info("Sender запущен")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
