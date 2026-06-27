from abc import abstractmethod
from typing import Protocol


class UoW(Protocol):
    """Unit of Work — управление транзакцией.

    Репозитории только готовят изменения (add/update), а решение «зафиксировать
    или откатить» принимает вызывающий код через этот объект. Так одна бизнес-
    операция = одна транзакция, и репозитории не коммитят сами по себе.

    Реализацией служит сам ``AsyncSession`` SQLAlchemy — у него уже есть эти
    методы (см. провайдер в ioc сервиса).
    """

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def flush(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
