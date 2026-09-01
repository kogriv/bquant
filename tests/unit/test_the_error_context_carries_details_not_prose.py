"""Контекст операции сообщает имя операции свойством, а не только текстом.

`BQuantErrorContext` оборачивал чужое исключение в исключение пакета и вписывал имя
операции **только в текст сообщения**. Программе, поймавшей ошибку, оставался разбор
строки — при том что у `BQuantError` есть `details` ровно для этого.

Тот же принцип, что вывели на G31: статус, имя, режим — свойство, а не проза.
"""

from __future__ import annotations

import pytest

from bquant.core.exceptions import BQuantError, BQuantErrorContext, ConfigurationError


def test_the_operation_name_is_readable_by_a_program():
    with pytest.raises(BQuantError) as excinfo:
        with BQuantErrorContext("загрузка данных"):
            1 / 0

    assert excinfo.value.details["operation"] == "загрузка данных"
    assert excinfo.value.details["original_error"] == "ZeroDivisionError"


@pytest.mark.parametrize("raised,expected", [
    (ValueError, ConfigurationError),
    (TypeError, ConfigurationError),
    (ZeroDivisionError, BQuantError),
    (KeyError, BQuantError),
])
def test_the_wrapping_type_follows_the_original(raised, expected):
    """Ошибка аргумента становится ошибкой конфигурации, прочее — базовой."""

    with pytest.raises(expected) as excinfo:
        with BQuantErrorContext("операция"):
            raise raised("boom")

    assert excinfo.value.details["original_error"] == raised.__name__


def test_a_package_error_passes_through_with_its_own_details():
    """Своё оборачивать незачем — и подменять его детали тем более."""

    with pytest.raises(BQuantError) as excinfo:
        with BQuantErrorContext("операция"):
            raise BQuantError("уже наша", {"symbol": "XAUUSD"})

    assert excinfo.value.details == {"symbol": "XAUUSD"}


def test_the_original_exception_stays_chained():
    """Обёртка не должна прятать первопричину."""

    with pytest.raises(BQuantError) as excinfo:
        with BQuantErrorContext("операция"):
            1 / 0

    assert isinstance(excinfo.value.__cause__, ZeroDivisionError)
