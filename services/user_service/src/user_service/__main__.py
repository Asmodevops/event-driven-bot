"""Точка входа user_service.

Подписан на стрим ``commands``, сохраняет пользователя в Postgres и публикует
ответ в стрим ``outgoing``. Схему БД накатывает Alembic (см. пакет ``database``).
"""

import asyncio
import logging

from dishka_faststream import setup_dishka
from faststream import FastStream
from faststream.nats import NatsBroker

from adapters import configure_logging
from user_service.config import settings
from user_service.handlers import router
from user_service.ioc import create_container
from user_service.publisher import OutgoingPublisher


logger = logging.getLogger("user_service")


async def main() -> None:
    configure_logging("user_service")

    container = create_container(settings)
    broker = await container.get(NatsBroker)
    # Форсируем создание publisher до старта, чтобы стрим outgoing объявился.
    await container.get(OutgoingPublisher)
    broker.include_router(router)

    app = FastStream(broker)
    setup_dishka(container, app)

    @app.after_shutdown
    async def _close_container() -> None:
        await container.close()

    logger.info("User service запущен")
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
