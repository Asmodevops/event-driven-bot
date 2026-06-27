"""NATS-сабджекты (subjects), общие для всех сервисов.

Имена сабджектов в одном месте — нет опечаток, и весь поток сообщений виден из
одного файла. Маски ``*_ALL`` используются, чтобы привязать стрим к целому
пространству имён.
"""

from typing import Final


class Subjects:
    # Gateway -> User Service: распарсенная команда /start.
    CMD_START: Final = "tg.cmd.start"
    # Gateway -> User Service: нажатие inline-кнопки (callback_query).
    CMD_CALLBACK: Final = "tg.cmd.callback"
    # Всё пространство команд — фильтр сабджектов для стрима COMMANDS.
    CMD_ALL: Final = "tg.cmd.>"

    # Любой сервис -> Sender: сообщение для доставки пользователю.
    SEND_OUT: Final = "tg.send.out"
    # Всё пространство исходящих — фильтр сабджектов для стрима OUTGOING.
    SEND_ALL: Final = "tg.send.>"

    # «Мёртвые» сообщения, не обработанные после всех попыток.
    # Namespace tg.dlq.> вынесен из tg.send.>, чтобы DLQ не попадал в стрим OUTGOING.
    SEND_DLQ: Final = "tg.dlq.send"
    DLQ_ALL: Final = "tg.dlq.>"
