"""Сценарий: зарегистрировать пользователя по /start и поздороваться."""

import logging

from adapters import IDGenerator
from contracts import IncomingMessage, OutgoingMessage
from database.repositories import UserRepository
from domain import (
    UoW,
    User as DomainUser,
)
from user_service import keyboards, lexicon
from user_service.publisher import OutgoingPublisher


logger = logging.getLogger("user_service")


class RegisterUser:
    """Создаёт пользователя (если он новый) и просит sender поздороваться."""

    def __init__(
        self,
        users: UserRepository,
        uow: UoW,
        id_generator: IDGenerator,
        publisher: OutgoingPublisher,
    ) -> None:
        self._users = users
        self._uow = uow
        self._id_generator = id_generator
        self._publisher = publisher

    async def __call__(self, command: IncomingMessage) -> None:
        tg_user = command.from_user
        if tg_user is None:
            return

        if await self._users.get_by_telegram_id(tg_user.id) is None:
            user = DomainUser.create(
                id=self._id_generator.generate(),
                telegram_id=tg_user.id,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                full_name=tg_user.full_name,
                username=tg_user.username,
                language_code=tg_user.language_code or "ru",
            )
            await self._users.add(user)
            await self._uow.commit()
            logger.info("Зарегистрирован новый пользователь telegram_id=%s", tg_user.id)

        await self._publisher.publish(
            OutgoingMessage(
                chat_id=command.chat.id,
                text=lexicon.GREETING.format(name=tg_user.full_name),
                buttons=keyboards.ping(),
                trace_id=command.trace_id,
            )
        )
