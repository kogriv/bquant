"""Схемная валидация выносит вердикт, а не подтверждает что угодно.

G42. `DataSchema.validate_dataframe()` была заглушкой, безусловно возвращавшей
`is_valid=True`. На любом кадре: пустом, без единого объявленного поля, с текстом
вместо цен. Схема `macd` требует три колонки, которых у встроенного сэмпла нет, и
всё равно объявляла его валидным.

Признание «не реализовано» при этом в результате было — в `recommendations`, то есть
в поле, которое никто не читает после того, как вердикт получен. Худшее место для
такого признания: оно снимает вину с автора и ничего не сообщает вызывающему.

Заодно чинится `AttributeError` при `IndicatorSchema('что-угодно-ещё')`: ветка
«схема неизвестна, оставляем без ограничений» обращалась к `self.logger`, которого у
схемы не было, — то есть аккуратно описанное поведение ни разу не исполнялось.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.data.samples import get_sample_data
from bquant.data.schemas import (
    MACD_SCHEMA,
    OHLCV_SCHEMA,
    RSI_SCHEMA,
    IndicatorSchema,
    validate_with_schema,
)


@pytest.fixture(scope="module")
def sample() -> pd.DataFrame:
    return get_sample_data("tv_xauusd_1h")


def test_a_missing_required_column_is_refused(sample):
    """Главный случай: сэмпл не несёт колонок MACD, и схема обязана это сказать."""

    result = validate_with_schema(sample, "macd")

    assert result.is_valid is False
    assert "macd_12_26_9__line" in " ".join(result.issues)
    assert result.stats["missing_required"] == [
        "macd_12_26_9__line", "macd_12_26_9__signal", "macd_12_26_9__hist",
    ]


def test_matching_data_passes(sample):
    """Обратная сторона: кадр, который схеме соответствует, обязан пройти."""

    result = validate_with_schema(sample, "ohlcv")

    assert result.is_valid is True
    assert result.issues == []
    assert result.stats["checked_fields"] == ["open", "high", "low", "close", "volume"]


def test_an_optional_field_may_be_absent():
    """`volume` объявлен опциональным — его отсутствие не отказ."""

    frame = pd.DataFrame({"open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5]})

    result = OHLCV_SCHEMA.validate_dataframe(frame)

    assert result.is_valid is True
    assert result.stats["absent_optional"] == ["volume"]


def test_a_rule_violation_is_counted_and_named():
    """Правило «цена положительна» обязано сработать и назвать, где и сколько раз."""

    frame = pd.DataFrame({
        "open": [1.0, -2.0], "high": [2.0, 3.0],
        "low": [1.0, 2.0], "close": [1.5, -2.5],
    })

    result = OHLCV_SCHEMA.validate_dataframe(frame)

    assert result.is_valid is False
    assert result.stats["rule_violations"] == {"open": 1, "close": 1}


def test_rsi_outside_its_range_is_refused():
    """У RSI правило диапазона объявлено схемой — оно должно применяться."""

    result = RSI_SCHEMA.validate_dataframe(pd.DataFrame({"rsi_14": [50.0, 150.0]}))

    assert result.is_valid is False
    assert result.stats["rule_violations"] == {"rsi_14": 1}


def test_a_non_numeric_column_is_refused():
    """Тип объявлен схемой; текст вместо цены — расхождение, а не мелочь."""

    frame = pd.DataFrame({
        "open": ["a", "b"], "high": [2.0, 3.0], "low": [1.0, 2.0], "close": [1.5, 2.5],
    })

    result = OHLCV_SCHEMA.validate_dataframe(frame)

    assert result.is_valid is False
    assert "expected float" in " ".join(result.issues)


def test_an_unknown_schema_name_is_refused_by_name():
    """Отказ обязан перечислить, что вообще есть."""

    result = validate_with_schema(pd.DataFrame({"x": [1]}), "нет_такой_схемы")

    assert result.is_valid is False
    assert "нет_такой_схемы" in " ".join(result.issues)
    assert "ohlcv" in " ".join(result.recommendations)


def test_an_unknown_indicator_leaves_the_schema_unconstrained():
    """Ветка, которая раньше падала с AttributeError вместо записи в лог."""

    schema = IndicatorSchema("stochastic")

    assert schema.required_fields == []
    assert schema.validate_dataframe(pd.DataFrame({"x": [1.0]})).is_valid is True


def test_the_verdict_is_not_a_constant(sample):
    """Пин против возврата заглушки: два кадра — два разных вердикта."""

    assert validate_with_schema(sample, "ohlcv").is_valid is True
    assert validate_with_schema(sample, "rsi").is_valid is False
