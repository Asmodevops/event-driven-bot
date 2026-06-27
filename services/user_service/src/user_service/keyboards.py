"""Клавиатуры user_service — все inline-кнопки в одном месте.

Кнопка = подпись (из [[lexicon]]) + ``callback_data``. ``callback_data`` — это
служебный ключ нажатия: gateway вернёт его как callback, а интерактор
``AnswerCallback`` по нему поймёт, что нажали. Ключи держим здесь константами,
чтобы «тот, кто рисует кнопку» и «тот, кто обрабатывает нажатие» не разъехались.

Клавиатуры собираем через ``KeyboardBuilder`` (``contracts``): копим кнопки и
раскладываем по рядам (``width``/``adjust``). ``Button`` — это контракт, без
aiogram; реальную inline-клавиатуру из него собирает уже sender.
"""

from contracts import Button, KeyboardBuilder
from user_service import lexicon


# callback_data — служебные ключи нажатий (пользователю не показываются).
PING = "ping"


def ping() -> list[list[Button]]:
    """Клавиатура с одной кнопкой «Пинг» (демонстрирует сквозной путь колбэка)."""
    return KeyboardBuilder().button(lexicon.BTN_PING, PING).as_markup()
