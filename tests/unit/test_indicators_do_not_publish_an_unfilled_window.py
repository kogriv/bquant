"""Индикатор не публикует значение там, где его окно ещё не заполнено.

G45. Внутри одного пакета соглашение о прогреве было расколото: `SimpleMovingAverage`
и `BollingerBands` закрывали голову ряда маской `period-1`, а `ExponentialMovingAverage`
и `MACD` отдавали числа с самого первого бара. То есть `sma_20` и `ema_20`, посчитанные
одной библиотекой на одном кадре, по-разному отвечали на вопрос «определено ли среднее
за двадцать баров на пятом баре».

Цена раскола видна не в самих индикаторах, а ниже по течению: детектор пересечений нуля
принимал непрогретую голову MACD за сигнал и строил на ней зоны, неотличимые от
настоящих. На встроенном сэмпле таких зон было шесть из восьмидесяти трёх, а самая
длинная из них — двенадцать баров при медиане корпуса одиннадцать.

Отдельно стоит нулевой бар: там обе EMA равны одной и той же цене закрытия, поэтому
линия MACD равна **ровно** 0.0 — идеальный ноль, изготовленный инициализацией.
"""

from __future__ import annotations

import numpy as np
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.indicators.custom import (
    BollingerBands,
    ExponentialMovingAverage,
    MACD,
    RelativeStrengthIndex,
    SimpleMovingAverage,
)


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


def _leading_nan(series) -> int:
    """Сколько значений в голове ряда не опубликовано."""
    values = series.to_numpy()
    defined = np.flatnonzero(~np.isnan(values))
    return len(values) if len(defined) == 0 else int(defined[0])


# --------------------------------------------------------------------------- #
# 1. Прогрев закрыт у всех, и закрыт по объявленной длине окна
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("indicator,expected", [
    (SimpleMovingAverage(period=20), {"sma_20": 19}),
    (ExponentialMovingAverage(period=20), {"ema_20": 19}),
    (BollingerBands(period=20), {
        "bbands_20_2__upper": 19,
        "bbands_20_2__middle": 19,
        "bbands_20_2__lower": 19,
        "bbands_20_2__width": 19,
        "bbands_20_2__percent": 19,
    }),
    (MACD(), {
        "macd_12_26_9__line": 25,
        "macd_12_26_9__signal": 33,
        "macd_12_26_9__hist": 33,
    }),
])
def test_the_head_of_the_series_is_not_published(indicator, expected, data):
    frame = indicator.calculate(data).data

    measured = {column: _leading_nan(frame[column]) for column in frame.columns}
    assert measured == expected


def test_the_warmup_follows_the_parameters_not_a_constant(data):
    """Окно задаёт вызов, значит и прогрев обязан считаться от вызова."""

    assert _leading_nan(ExponentialMovingAverage(period=50).calculate(data).data["ema_50"]) == 49
    assert _leading_nan(ExponentialMovingAverage(period=5).calculate(data).data["ema_5"]) == 4

    frame = MACD(fast_period=5, slow_period=10, signal_period=3).calculate(data).data
    assert _leading_nan(frame["macd_5_10_3__line"]) == 9
    assert _leading_nan(frame["macd_5_10_3__hist"]) == 11


@pytest.mark.parametrize("indicator,column", [
    (ExponentialMovingAverage(period=20), "ema_20"),
    (SimpleMovingAverage(period=20), "sma_20"),
    (MACD(), "macd_12_26_9__hist"),
])
def test_the_masked_head_is_wholly_absent_and_the_rest_wholly_present(
    indicator, column, data
):
    """Маска обязана быть сплошной: дырок внутри опубликованной части нет."""

    series = indicator.calculate(data).data[column]
    warmup = _leading_nan(series)

    assert series.iloc[:warmup].isna().all()
    assert series.iloc[warmup:].notna().all()


# --------------------------------------------------------------------------- #
# 2. Соглашение одно на весь пакет, и оно же — внешнее
# --------------------------------------------------------------------------- #

def test_the_package_answers_the_window_question_the_same_way_twice(data):
    """`sma_20` и `ema_20` обязаны сходиться в том, где среднее определено."""

    sma = SimpleMovingAverage(period=20).calculate(data).data["sma_20"]
    ema = ExponentialMovingAverage(period=20).calculate(data).data["ema_20"]

    assert _leading_nan(sma) == _leading_nan(ema)


def test_the_convention_matches_the_external_library(data):
    """Соглашение не изобретено: pandas-ta закрывает голову теми же длинами."""

    pandas_ta = pytest.importorskip("pandas_ta")  # noqa: F841
    from bquant.indicators import IndicatorFactory

    pairs = [
        (SimpleMovingAverage(period=20), ("sma", {"length": 20})),
        (ExponentialMovingAverage(period=20), ("ema", {"length": 20})),
        (RelativeStrengthIndex(period=14), ("rsi", {"length": 14})),
    ]
    for own, (name, params) in pairs:
        own_frame = own.calculate(data).data
        external = IndicatorFactory.create("pandas_ta", name, **params).calculate(data).data
        assert _leading_nan(own_frame[own_frame.columns[0]]) == \
            _leading_nan(external[external.columns[0]]), name

    own_macd = MACD().calculate(data).data
    external_macd = IndicatorFactory.create(
        "pandas_ta", "macd", fast=12, slow=26, signal=9
    ).calculate(data).data
    line = [c for c in external_macd.columns if c.startswith("MACD_")][0]
    hist = [c for c in external_macd.columns if c.startswith("MACDh_")][0]
    assert _leading_nan(own_macd["macd_12_26_9__line"]) == _leading_nan(external_macd[line])
    assert _leading_nan(own_macd["macd_12_26_9__hist"]) == _leading_nan(external_macd[hist])


def test_the_manufactured_zero_of_the_first_bar_is_not_published(data):
    """На нулевом баре обе EMA — одна и та же цена, и линия там ровно 0.0.

    Такой ноль неотличим от настоящего пересечения, а детектор зон читает именно
    пересечение нуля. Публиковать его нельзя.
    """

    line = MACD().calculate(data).data["macd_12_26_9__line"]
    assert np.isnan(line.iloc[0])


# --------------------------------------------------------------------------- #
# 3. Следствие ниже по течению: зон в прогреве нет
# --------------------------------------------------------------------------- #

def test_no_zone_is_built_where_the_indicator_says_nothing(data):
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .analyze(clustering=False)
        .build()
    )

    hist = result.data[result.column_schema.column("hist")]
    first_defined = _leading_nan(hist)

    early = [(z.zone_id, z.start_idx, z.end_idx) for z in result.zones
             if z.start_idx < first_defined]
    assert not early, f"зоны построены на непрогретой голове: {early}"
