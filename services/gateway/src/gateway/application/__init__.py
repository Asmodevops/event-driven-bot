"""Слой application gateway: разбор апдейтов aiogram и публикация команд.

Здесь рождается trace_id и собирается контракт из объектов aiogram. Хэндлеры в
``handlers.py`` лишь цепляются к роутеру и зовут эти интеракторы.
"""

from gateway.application.parsing import parse_callback, parse_message
from gateway.application.process_update import ProcessCallback, ProcessMessage


__all__ = [
    "ProcessCallback",
    "ProcessMessage",
    "parse_callback",
    "parse_message",
]
