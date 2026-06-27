from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """Доменная сущность пользователя.

    Это «чистый» объект: никакого SQLAlchemy и Telegram — только данные и
    бизнес-правила. Сервисы работают именно с ним, а как он хранится в БД,
    знает только репозиторий (он же мапит сущность в модель и обратно).
    """

    id: UUID
    telegram_id: int
    first_name: str
    full_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str = "ru"
    # Заполняются при чтении из БД; у новой сущности — None.
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: UUID,
        telegram_id: int,
        first_name: str,
        last_name: str | None = None,
        full_name: str,
        username: str | None = None,
        language_code: str = "ru",
    ) -> "User":
        return cls(
            id=id,
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            username=username,
            language_code=language_code,
        )
