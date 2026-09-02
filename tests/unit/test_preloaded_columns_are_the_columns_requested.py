"""У PRELOADED-индикатора извлекается то, что запрошено, и объявляется то, что извлечено.

G46. `MACDPreloadedIndicator.get_required_columns` был объявлен в теле класса **дважды**:
сначала методом экземпляра, отдающим запрошенные колонки, сразу за ним — классовым
двойником, отдающим умолчания. Python оставляет последнее определение и не говорит ни
слова. Побеждали умолчания, поэтому параметр `required_columns` не действовал ни при
извлечении, ни при валидации.

Наружу это выходило рассогласованием объекта с самим собой: `get_output_columns()`
обещал `['macd']`, `calculate()` возвращал `['macd', 'signal']`, а `metadata` называла
извлечённым первое. И `validate_data()` отвечал `True` на набор с колонкой, которой в
кадре нет вовсе, — потому что проверял не тот список.
"""

from __future__ import annotations

import pytest

from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.mark.parametrize("requested", [
    ["macd"],
    ["macd", "signal"],
    ["signal", "macd"],
    ["rsi"],
])
def test_the_frame_carries_exactly_the_requested_columns(requested, data):
    indicator = MACDPreloadedIndicator(required_columns=requested)
    frame = indicator.calculate(data).data

    assert list(frame.columns) == requested


@pytest.mark.parametrize("requested", [["macd"], ["macd", "signal"], ["rsi"]])
def test_the_object_agrees_with_itself(requested, data):
    """Объявление, результат и метаданные — три ответа на один вопрос."""

    indicator = MACDPreloadedIndicator(required_columns=requested)
    result = indicator.calculate(data)

    assert indicator.get_required_columns() == requested
    assert indicator.get_output_columns() == requested
    assert list(result.data.columns) == requested
    assert result.metadata["extracted_columns"] == requested
    assert indicator.config.columns == requested


def test_defaults_are_still_the_defaults(data):
    indicator = MACDPreloadedIndicator()

    assert indicator.get_required_columns() == ["macd", "signal"]
    assert list(indicator.calculate(data).data.columns) == ["macd", "signal"]


def test_a_column_absent_from_the_data_is_refused_not_confirmed(data):
    """`histogram` в выгрузке TradingView нет; «валидно» здесь — неверный ответ."""

    indicator = MACDPreloadedIndicator(required_columns=["macd", "signal", "histogram"])

    with pytest.raises(ValueError, match="histogram"):
        indicator.validate_data(data)

    with pytest.raises(ValueError, match="histogram"):
        indicator.calculate(data)


def test_the_role_map_covers_every_published_column(data):
    """Роль обязана быть у каждой колонки, которую индикатор кладёт в кадр."""

    indicator = MACDPreloadedIndicator(required_columns=["macd", "signal"])
    frame = indicator.calculate(data).data
    roles = indicator.get_output_roles()

    assert set(roles.values()) == set(frame.columns)


def test_the_nan_count_is_reported_even_when_it_is_zero(data):
    """`None` не отличить от «не считали», а считают здесь всегда."""

    result = MACDPreloadedIndicator().calculate(data)

    assert result.metadata["nan_counts"] == {"macd": 0, "signal": 0}
