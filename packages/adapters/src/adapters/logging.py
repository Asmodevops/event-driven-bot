"""Единое структурное логирование для всех сервисов q_bot.

Зачем: одно действие пользователя проходит через gateway → NATS → сервис →
NATS → sender. Чтобы проследить его сквозь все процессы, в каждую строку лога
подставляется ``trace_id`` — он рождается в gateway и едет в полях контрактов.
Логи пишем в JSON (по одной строке на событие) — такие удобно собирать и
фильтровать по ``trace_id``. Для локальной разработки можно включить
человекочитаемый формат переменной окружения ``LOG_JSON=0``.

Использование:
    configure_logging("gateway")        # один раз на старте сервиса
    set_trace_id(message.trace_id)      # в начале обработки апдейта/сообщения
"""

from contextvars import ContextVar
from datetime import datetime, UTC
import json
import logging
import os


# trace_id текущего обрабатываемого действия. ContextVar изолирован по asyncio-таске,
# поэтому параллельные обработки не путают свои trace_id между собой.
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_trace_id(trace_id: str | None) -> None:
    """Привязать trace_id к текущему контексту (в начале обработки сообщения)."""
    _trace_id.set(trace_id)


def get_trace_id() -> str | None:
    return _trace_id.get()


class _TraceIdFilter(logging.Filter):
    """Подкладывает trace_id в каждую запись лога (или ``-``, если его нет)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"
        return True


class _JsonFormatter(logging.Formatter):
    """Форматирует запись лога в одну JSON-строку."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", "-"),
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(service: str) -> None:
    """Настроить корневой логгер сервиса. Вызывать один раз на старте.

    Формат и уровень управляются окружением:
    - ``LOG_LEVEL`` — уровень (по умолчанию ``INFO``);
    - ``LOG_JSON`` — ``1`` (по умолчанию) JSON-логи; ``0`` — человекочитаемый
      формат для локальной разработки.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_logs = os.getenv("LOG_JSON", "1") != "0"

    handler = logging.StreamHandler()
    handler.addFilter(_TraceIdFilter())
    if json_logs:
        handler.setFormatter(_JsonFormatter(service))
    else:
        handler.setFormatter(
            logging.Formatter(
                f"%(asctime)s %(levelname)s [{service}] [%(trace_id)s] "
                "%(name)s: %(message)s"
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
