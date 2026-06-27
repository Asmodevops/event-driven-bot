"""Фейковые Bot/Session aiogram, чтобы тесты не ходили в Telegram API.

Адаптировано из тестового хелпера самого aiogram
(https://github.com/aiogram/aiogram/blob/dev-3.x/tests/mocked_bot.py):
исходящие запросы копятся в ``requests``, заранее заданные ответы — в ``responses``.
"""

from collections import deque
from collections.abc import AsyncGenerator
from typing import Any, TYPE_CHECKING

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.base import Response, TelegramType
from aiogram.types import ResponseParameters, UNSET_PARSE_MODE, User


class MockedSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.responses: deque[Response[TelegramType]] = deque()
        self.requests: deque[TelegramMethod[TelegramType]] = deque()
        self.closed = True

    def add_result(self, response: Response[TelegramType]) -> Response[TelegramType]:
        self.responses.append(response)
        return response

    def get_request(self) -> TelegramMethod[TelegramType]:
        return self.requests.popleft()

    async def close(self) -> None:
        self.closed = True

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = UNSET_PARSE_MODE,
    ) -> TelegramType:
        self.closed = False
        self.requests.append(method)
        response: Response[TelegramType] = self.responses.popleft()
        self.check_response(
            bot=bot,
            method=method,
            status_code=response.error_code,
            content=response.model_dump_json(),
        )
        return response.result  # type: ignore[return-value]

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        yield b""


class MockedBot(Bot):
    if TYPE_CHECKING:
        session: MockedSession

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            kwargs.pop("token", "42:TEST"), session=MockedSession(), **kwargs
        )
        self._me = User(
            id=self.id,
            is_bot=True,
            first_name="BotName",
            last_name="BotSurname",
            username="bot",
            language_code="en-US",
        )

    def add_result_for(
        self,
        method: type[TelegramMethod[TelegramType]],
        ok: bool,
        result: TelegramType = None,
        description: str | None = None,
        error_code: int = 200,
        migrate_to_chat_id: int | None = None,
        retry_after: int | None = None,
    ) -> Response[TelegramType]:
        response = Response[method.__returning__](  # type: ignore[name-defined]
            ok=ok,
            result=result,
            description=description,
            error_code=error_code,
            parameters=ResponseParameters(
                migrate_to_chat_id=migrate_to_chat_id,
                retry_after=retry_after,
            ),
        )
        self.session.add_result(response)
        return response

    def get_request(self) -> TelegramMethod[TelegramType]:
        return self.session.get_request()
