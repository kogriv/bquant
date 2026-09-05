"""Реализации индикаторов обязаны держать один контракт (G58).

Четыре находки аудита (AQ-021, 022, 023, 028), каждая воспроизведена до правки:

* `validate_data()` возвращал `False` и писал в лог, а результат никто не читал:
  MACD на 10 барах (нужно 35) отдавал 10 строк `NaN` — неотличимо от прогрева;
  `EMA(20).calculate(data, period=100)` проверял двадцать баров, а не сто; `close`
  из строк и `inf` в `close` считались молча;
* `OptimizedIndicators.ema` на целых ценах давал `[100, 100, 101, 101, 103]` вместо
  `[100, 100.5, 101.75, …]` — `np.zeros_like` наследовал `int64`; RSI и MACD на нём
  наследовали потерю;
* оптимизированный MACD публиковал значения с нулевого бара, custom — с `slow-1` и
  `slow+signal-2`; `fast=0`, `slow <= fast`, `signal=0` принимались;
* `IndicatorId.parameters` был обычным `dict` под `frozen=True`: правка через атрибут
  меняла slug и хэш; `ColumnSchema` ключевала по slug, и custom RSI с pandas-ta RSI
  затирали друг друга.
"""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
import pytest

from bquant.core.exceptions import DataValidationError
from bquant.core.performance import (
    OptimizedIndicators,
    ema_warmup,
    macd_warmup,
    require_macd_periods,
)
from bquant.data.samples import get_sample_data
from bquant.indicators.calculators import validate_indicator_data
from bquant.indicators.custom import MACD, ExponentialMovingAverage, RelativeStrengthIndex
from bquant.indicators.schema import ColumnSchema, FrozenParameters, IndicatorId


@pytest.fixture(scope="module")
def close() -> np.ndarray:
    return get_sample_data("tv_xauusd_1h")["close"].to_numpy(dtype=float)


# --- AQ-021: validation is control flow, not a log line ---------------------------------


def test_too_few_rows_is_a_refusal_not_a_frame_of_nan(close):
    with pytest.raises(DataValidationError, match="10 rows, but at least 35"):
        MACD().calculate(pd.DataFrame({"close": close[:10]}))


def test_the_minimum_follows_the_parameters_of_the_call(close):
    ema = ExponentialMovingAverage(period=20)
    assert ema.get_min_records() == 20
    assert ema.get_min_records(period=100) == 100
    with pytest.raises(DataValidationError, match="at least 100"):
        ema.calculate(pd.DataFrame({"close": close[:40]}), period=100)
    assert len(ema.calculate(pd.DataFrame({"close": close[:40]})).data) == 40


def test_a_non_numeric_close_is_refused_by_name():
    frame = pd.DataFrame({"close": ["1", "2", "3"] * 20})
    # pandas 2 reports `object`, pandas 3 `str`; the refusal is the point, not the label.
    with pytest.raises(DataValidationError, match="not a number"):
        ExponentialMovingAverage(period=5).calculate(frame)


def test_an_infinite_price_is_refused_and_nan_is_not(close):
    with_inf = pd.DataFrame({"close": np.r_[close[:30], np.inf, close[31:60]]})
    with pytest.raises(DataValidationError, match="1 infinite value"):
        ExponentialMovingAverage(period=5).calculate(with_inf)
    with_nan = pd.DataFrame({"close": np.r_[close[:30], np.nan, close[31:60]]})
    assert len(ExponentialMovingAverage(period=5).calculate(with_nan).data) == 60


def test_validate_data_returns_true_or_raises(close):
    assert RelativeStrengthIndex(14).validate_data(pd.DataFrame({"close": close[:50]})) is True
    with pytest.raises(DataValidationError, match="missing required columns"):
        RelativeStrengthIndex(14).validate_data(pd.DataFrame({"open": close[:50]}))
    # The bool-returning convenience keeps its contract by catching the refusal.
    assert validate_indicator_data(pd.DataFrame({"close": close[:5]}), "rsi", period=14) is False
    assert validate_indicator_data(pd.DataFrame({"close": close[:50]}), "rsi", period=14) is True


# --- AQ-022: float in, float out ----------------------------------------------------------


def test_optimized_ema_does_not_truncate_integer_prices():
    ints = np.array([100, 101, 103, 102, 105, 104, 108, 107, 110, 109])
    as_int = OptimizedIndicators.ema(ints, 3)
    as_float = OptimizedIndicators.ema(ints.astype(float), 3)
    assert as_int.dtype == np.float64
    assert np.allclose(as_int, as_float, equal_nan=True)
    assert as_int[2] == pytest.approx(101.75)


def test_optimized_rsi_and_macd_agree_on_integer_and_float_input():
    ints = np.arange(100, 160) + np.array([0, 3, -2, 5, -1] * 12)
    for name, fn in (("rsi", lambda p: OptimizedIndicators.rsi(p, 14)),
                     ("macd", lambda p: OptimizedIndicators.macd(p, 5, 13, 4)[0])):
        assert np.allclose(fn(ints), fn(ints.astype(float)), equal_nan=True), name


# --- AQ-023: one warm-up contract, one parameter check -------------------------------------


def test_optimized_macd_publishes_under_the_custom_contract(close):
    frame = pd.DataFrame({"close": close[:60]})
    custom = MACD(12, 26, 9).calculate(frame).data
    line, signal, hist = OptimizedIndicators.macd(close[:60], 12, 26, 9)

    line_warmup, signal_warmup = macd_warmup(26, 9)
    assert (line_warmup, signal_warmup) == (25, 33)
    assert int(custom.iloc[:, 0].isna().sum()) == int(np.isnan(line).sum()) == line_warmup
    assert int(custom.iloc[:, 1].isna().sum()) == int(np.isnan(signal).sum()) == signal_warmup
    assert int(np.isnan(hist).sum()) == signal_warmup
    assert not np.isnan(line[line_warmup:]).any()


def test_optimized_and_custom_ema_are_the_same_series(close):
    frame = pd.DataFrame({"close": close[:60]})
    custom = ExponentialMovingAverage(20).calculate(frame).data.iloc[:, 0].to_numpy()
    optimized = OptimizedIndicators.ema(close[:60], 20)
    assert int(np.isnan(custom).sum()) == int(np.isnan(optimized).sum()) == ema_warmup(20)
    assert np.allclose(custom[19:], optimized[19:])


@pytest.mark.parametrize("periods", [(0, 26, 9), (26, 12, 9), (12, 12, 9), (12, 26, 0), (12.5, 26, 9)])
def test_bad_macd_periods_are_refused_by_both_implementations(close, periods):
    with pytest.raises(ValueError):
        require_macd_periods(*periods)
    with pytest.raises(ValueError):
        OptimizedIndicators.macd(close[:60], *periods)
    with pytest.raises(ValueError):
        MACD(*periods).calculate(pd.DataFrame({"close": close[:60]}))


# --- AQ-028: identity is immutable and includes the source ---------------------------------


def test_indicator_id_parameters_cannot_be_edited_in_place():
    iid = IndicatorId("custom", "rsi", {"period": 14}, ("period",))
    bag = {iid: "x"}
    with pytest.raises(TypeError):
        iid.parameters["period"] = 99
    assert iid.slug == "rsi_14" and bag[iid] == "x"
    assert iid.parameters == {"period": 14}
    assert isinstance(iid.parameters, FrozenParameters)


def test_indicator_id_survives_pickle_and_the_source_is_in_the_key():
    iid = IndicatorId("pandas_ta", "rsi", {"period": 14}, ("period",))
    assert iid.key == "pandas_ta.rsi_14" and str(iid) == iid.key
    restored = pickle.loads(pickle.dumps(iid))
    assert restored == iid and hash(restored) == hash(iid)


def test_two_sources_with_one_slug_keep_two_columns():
    schema = ColumnSchema()
    custom = IndicatorId("custom", "rsi", {"period": 14}, ("period",))
    library = IndicatorId("pandas_ta", "rsi", {"period": 14}, ("period",))
    schema.register(custom, {"value": "rsi_14"})
    schema.register(library, {"value": "RSI_14"})

    assert schema.column("value", custom) == "rsi_14"
    assert schema.column("value", library) == "RSI_14"
    assert schema.column("value") is None, "two providers of one role: refuse to guess"
    assert schema.roles_of("RSI_14")[0] == library

    restored = ColumnSchema.from_dict(schema.to_dict())
    assert restored.column("value", custom) == "rsi_14"
    assert restored.column("value", library) == "RSI_14"


def test_a_schema_written_without_the_source_is_refused():
    with pytest.raises(ValueError, match="keyed without its source"):
        ColumnSchema.from_dict({
            "entries": {"rsi_14|value": "rsi_14"},
            "indicators": {"rsi_14": {"source": "custom", "name": "rsi",
                                      "parameters": {"period": 14}, "parameter_order": ["period"]}},
        })
