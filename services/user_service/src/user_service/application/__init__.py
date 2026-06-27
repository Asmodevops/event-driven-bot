"""Слой application: интеракторы (сценарии бизнес-логики) user_service.

Интерактор — один сценарий («зарегистрировать пользователя», «ответить на
нажатие»). Зависимости он получает в ``__init__`` (их подставляет контейнер), а
сам сценарий — это ``async def __call__``. Хэндлер из ``handlers.py`` только
принимает сообщение из NATS и зовёт нужный интерактор: вся логика живёт здесь и
тестируется без брокера.
"""

from user_service.application.answer_callback import AnswerCallback
from user_service.application.register_user import RegisterUser


__all__ = ["AnswerCallback", "RegisterUser"]
