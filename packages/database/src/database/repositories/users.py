from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User as UserModel
from domain import User


class UserRepository:
    """Доступ к пользователям. Наружу отдаёт и принимает доменные сущности
    (``domain.User``), а маппинг в модель БД (``UserModel``) прячет внутри.

    Только готовит изменения в сессии (``add``); фиксацию транзакции выполняет
    Unit of Work (``domain.UoW``), а не репозиторий.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        model = await self._session.scalar(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        return self._to_domain(model) if model is not None else None

    async def add(self, user: User) -> None:
        self._session.add(self._to_model(user))

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            telegram_id=model.telegram_id,
            first_name=model.first_name,
            full_name=model.full_name,
            last_name=model.last_name,
            username=model.username,
            language_code=model.language_code,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(user: User) -> UserModel:
        return UserModel(
            id=user.id,
            telegram_id=user.telegram_id,
            first_name=user.first_name,
            full_name=user.full_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
        )
