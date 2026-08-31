"""Кэш обязан отдавать ответ на заданный вопрос, а не на похожий.

G36 со стороны потребителя: тест проверяет не ключ, а то, ради чего ключ нужен —
что при **включённом по умолчанию** кэше запрошенная стратегия метрик действительно
считается. До правки этот сценарий давал 0 зон с метриками волатильности из 32,
потому что отдавалась запись предыдущего прогона, посчитанная без неё.
"""

from __future__ import annotations

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data


def zones_with_volatility(result) -> int:
    return sum(
        1
        for zone in result.zones
        if (zone.features or {}).get("metadata", {}).get("volatility_metrics")
    )


@pytest.fixture(scope="module")
def data():
    # Срез, а не весь набор: свой хэш данных, чтобы тест не зависел от того, что
    # уже лежит в кэше разработчика, и не засорял ключ полного сэмпла.
    return get_sample_data("tv_xauusd_1h").head(600)


def build(data, *, volatility: bool):
    builder = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
    )
    if volatility:
        builder = builder.with_strategies(volatility="combined")
    return builder.analyze().build()


def test_enabling_a_strategy_after_a_cached_run_actually_computes_it(data):
    """Порядок важен: сначала прогон без стратегии, он и наполняет кэш."""

    without = build(data, volatility=False)
    assert zones_with_volatility(without) == 0

    with_strategy = build(data, volatility=True)

    assert zones_with_volatility(with_strategy) > 0, (
        "Кэш отдал результат, посчитанный без запрошенной стратегии. "
        "Ключ снова перестал различать стратегии метрик (G36)."
    )


def test_the_second_identical_run_returns_the_same_content(data):
    """Промахи лечить промахами нельзя: попадание обязано быть верным."""

    first = build(data, volatility=True)
    second = build(data, volatility=True)

    assert zones_with_volatility(first) == zones_with_volatility(second)
    assert len(first.zones) == len(second.zones)
