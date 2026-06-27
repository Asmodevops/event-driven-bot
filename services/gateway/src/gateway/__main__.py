"""Точка входа gateway.

Поллит Telegram и публикует распарсенные апдейты в NATS JetStream. Сам gateway
не ходит в БД и не содержит бизнес-логики — только решает, в какой subject
отправить апдейт. Пока обрабатывает один случай — команду ``/start``.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from dishka.integrations.aiogram import setup_dishka
from faststream.nats import NatsBroker

from adapters import configure_logging
from gateway.config import settings
from gateway.handlers import router
from gateway.ioc import create_container
from gateway.middlewares import SafeCallbackAnswerMiddleware, ThrottlingMiddleware
from gateway.publisher import CommandPublisher


logger = logging.getLogger("gateway")


async def main() -> None:
    configure_logging("gateway")

    # Собираем контейнер и берём из него готовые зависимости.
    container = create_container(settings)
    broker = await container.get(NatsBroker)
    bot = await container.get(Bot)
    dp = await container.get(Dispatcher)
    # Форсируем создание publisher до старта брокера, чтобы стрим объявился.
    await container.get(CommandPublisher)

    # Анти-флуд на сообщениях и колбэках (отсекаем до публикации в очереди).
    throttling = ThrottlingMiddleware(settings.throttle_time)
    dp.message.middleware(throttling)
    dp.callback_query.middleware(throttling)
    # Автоответ на колбэки (убирает «часики» у пользователя).
    dp.callback_query.middleware(SafeCallbackAnswerMiddleware())

    dp.include_router(router)
    setup_dishka(container, dp)

    await broker.start()
    logger.info("Gateway запущен, поллинг Telegram")
    try:
        await dp.start_polling(bot)
    finally:
        await broker.stop()
        await bot.session.close()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
