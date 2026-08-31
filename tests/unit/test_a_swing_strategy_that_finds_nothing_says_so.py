"""Стратегия, не нашедшая ни одного свинга, обязана сказать об этом.

G35, первая половина. `swing_metrics` с `num_swings: 0` выглядит одинаково в двух
разных случаях: движения не было и порог оказался крупнее самой зоны. Второй случай
на встроенных данных — не редкость, а умолчание: `min_amplitude_pct` пресета
`wide_zone` равен 2% цены при медианном размахе зоны 1.2%.

Проверяется не «сколько свингов нашлось» — это свойство данных и порогов, — а то, что
о полном отсутствии улова сказано **дважды**: числом в метаданных, чтобы могла
спросить программа, и предупреждением, чтобы человек не искал причину в рынке.
"""

from __future__ import annotations

import logging

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data


ANALYZER_LOGGER = "bquant.analysis.zones.analyzer"


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture
def analyzer_warnings(caplog):
    """Слушать логгер анализатора напрямую.

    Пакет настраивает свои логгеры с `propagate=False`, поэтому обычный `caplog`
    их не видит: сообщение печатается, а проверка молчит. Вешаем обработчик
    `caplog` на конкретный логгер и снимаем после теста.
    """

    logger = logging.getLogger(ANALYZER_LOGGER)
    logger.addHandler(caplog.handler)
    previous_level = logger.level
    logger.setLevel(logging.WARNING)
    try:
        yield caplog
    finally:
        logger.removeHandler(caplog.handler)
        logger.setLevel(previous_level)


def analyse(data, *, swing: str, preset: str):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing=swing)
        .with_swing_preset(preset)
        .with_cache(enable=False)
        .analyze()
        .build()
    )


def test_the_result_reports_how_many_zones_got_swings(data):
    result = analyse(data, swing="zigzag", preset="narrow_zone")

    coverage = result.metadata["swing_coverage"]

    assert coverage["zones"] == len(result.zones)
    assert 0 < coverage["zones_with_swings"] <= coverage["zones"]
    assert coverage["strategy"] == "ZigZagSwingStrategy"


def test_an_empty_catch_is_said_out_loud(data, analyzer_warnings):
    """`find_peaks` при широких порогах не находит ничего на этих данных."""

    result = analyse(data, swing="find_peaks", preset="wide_zone")

    assert result.metadata["swing_coverage"]["zones_with_swings"] == 0

    warnings = [record.getMessage() for record in analyzer_warnings.records]
    assert any("found no swings" in message for message in warnings), (
        "Ни одного свинга ни в одной зоне — и ни слова об этом. Ноль неотличим от "
        "измеренного отсутствия движения, поэтому молчать здесь нельзя."
    )
    assert any("narrow_zone" in message for message in warnings), (
        "Предупреждение обязано называть, что попробовать, а не только то, что плохо."
    )


def test_a_non_empty_catch_stays_quiet(data, analyzer_warnings):
    """Обратная сторона: предупреждение не должно превращаться в фон."""

    analyse(data, swing="find_peaks", preset="narrow_zone")

    assert not [
        record
        for record in analyzer_warnings.records
        if "found no swings" in record.getMessage()
    ]


def test_without_a_swing_strategy_there_is_nothing_to_report(data):
    """Поле появляется только там, где о нём есть что сказать."""

    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing=None)
        .with_cache(enable=False)
        .analyze()
        .build()
    )

    # Умолчание `ZoneFeaturesAnalyzer` — zigzag, поэтому стратегия есть всегда, и
    # отчёт о покрытии тоже. Проверяем, что это именно так, а не «иногда есть».
    assert "swing_coverage" in result.metadata
