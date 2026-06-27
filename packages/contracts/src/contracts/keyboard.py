"""Строитель inline-клавиатуры в формате контракта.

``KeyboardBuilder`` копит кнопки и раскладывает их по рядам (``width``/``adjust``),
как aiogram ``InlineKeyboardBuilder``, но возвращает нейтральный
``list[list[Button]]`` — без aiogram. Так клавиатуру может собрать любой сервис
(в т. ч. aiogram-free ``user_service``), а реальную разметку из неё строит уже
``sender``. Кнопки добавляются по одной и вызовы можно сцеплять.

Пример::

    KeyboardBuilder().button("Да", "yes").button("Нет", "no").as_markup(width=2)
"""

from typing import Self

from contracts.messages import Button


def _chunk(buttons: list[Button], sizes: list[int]) -> list[list[Button]]:
    """Разрезать кнопки на ряды по размерам ``sizes`` (последний повторяется)."""
    rows: list[list[Button]] = []
    start = 0
    step = 0
    while start < len(buttons):
        size = sizes[min(step, len(sizes) - 1)]
        rows.append(buttons[start : start + size])
        start += size
        step += 1
    return rows


class KeyboardBuilder:
    """Удобная сборка клавиатуры в виде ``list[list[Button]]``."""

    def __init__(self) -> None:
        self._buttons: list[Button] = []

    def button(self, text: str, callback_data: str) -> Self:
        """Добавить кнопку. Возвращает себя — вызовы можно сцеплять."""
        self._buttons.append(Button(text=text, callback_data=callback_data))
        return self

    def as_markup(
        self, width: int = 1, adjust: tuple[int, ...] | None = None
    ) -> list[list[Button]]:
        """Разложить кнопки по рядам и вернуть раскладку.

        ``width`` — по сколько кнопок в ряд (если ``adjust`` не задан).
        ``adjust`` — ширины рядов по порядку; последняя повторяется для остатка
        (как в aiogram). Например, ``adjust=(2, 1)`` → первый ряд 2 кнопки,
        дальше по одной.
        """
        if not self._buttons:
            return []
        sizes = list(adjust) if adjust else [width]
        return _chunk(self._buttons, sizes)


def combine_keyboards(*layouts: list[list[Button]]) -> list[list[Button]]:
    """Склеить несколько клавиатур в одну (ряды идут подряд)."""
    return [row for layout in layouts for row in layout]
