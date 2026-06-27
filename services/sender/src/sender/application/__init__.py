"""Слой application sender: решение о доставке сообщения в Telegram.

Логика «отправить и решить — подтвердить или повторить» вынесена сюда из
хэндлера. Хэндлер в ``handlers.py`` только читает номер попытки из JetStream и
применяет к сообщению ack/nack по вердикту интерактора.
"""

from sender.application.deliver import Ack, DeliverMessage, Nack


__all__ = ["Ack", "DeliverMessage", "Nack"]
