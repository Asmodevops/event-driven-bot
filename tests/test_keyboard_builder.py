"""Тесты строителя клавиатур: раскладка кнопок по рядам.

Чистая логика контрактного слоя — ни aiogram, ни NATS не нужны.
"""

from contracts import combine_keyboards, KeyboardBuilder


def _texts(layout) -> list[list[str]]:
    return [[b.text for b in row] for row in layout]


def test_single_button_default_width() -> None:
    layout = KeyboardBuilder().button("Да", "yes").as_markup()
    assert _texts(layout) == [["Да"]]
    assert layout[0][0].callback_data == "yes"


def test_width_groups_buttons_into_rows() -> None:
    layout = (
        KeyboardBuilder()
        .button("1", "1")
        .button("2", "2")
        .button("3", "3")
        .as_markup(width=2)
    )
    # По 2 в ряд, остаток — в последний ряд.
    assert _texts(layout) == [["1", "2"], ["3"]]


def test_adjust_sets_per_row_sizes_and_repeats_last() -> None:
    layout = (
        KeyboardBuilder()
        .button("1", "1")
        .button("2", "2")
        .button("3", "3")
        .button("4", "4")
        .as_markup(adjust=(1, 2))
    )
    # 1 в первом ряду, 2 во втором, дальше последний размер (2) повторяется.
    assert _texts(layout) == [["1"], ["2", "3"], ["4"]]


def test_empty_builder_returns_no_rows() -> None:
    assert KeyboardBuilder().as_markup() == []


def test_combine_keyboards_concatenates_rows() -> None:
    top = KeyboardBuilder().button("a", "a").as_markup()
    bottom = KeyboardBuilder().button("b", "b").button("c", "c").as_markup(width=2)
    assert _texts(combine_keyboards(top, bottom)) == [["a"], ["b", "c"]]
