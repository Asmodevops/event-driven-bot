"""Тесты общего логирования: trace_id попадает в JSON-строку лога."""

import json
import logging

from adapters import set_trace_id
from adapters.logging import _JsonFormatter, _TraceIdFilter


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )


def test_json_log_includes_bound_trace_id() -> None:
    set_trace_id("trace-42")
    record = _record("привет")
    _TraceIdFilter().filter(record)

    line = _JsonFormatter("gateway").format(record)
    payload = json.loads(line)

    assert payload["trace_id"] == "trace-42"
    assert payload["service"] == "gateway"
    assert payload["level"] == "INFO"
    assert payload["msg"] == "привет"


def test_json_log_without_trace_id_uses_placeholder() -> None:
    set_trace_id(None)
    record = _record("no trace")
    _TraceIdFilter().filter(record)

    payload = json.loads(_JsonFormatter("sender").format(record))

    assert payload["trace_id"] == "-"
