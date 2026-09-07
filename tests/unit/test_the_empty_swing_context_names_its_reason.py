"""Пустой контекст свингов обязан говорить, почему он пуст (G70).

До 2026-09-07 четыре разные ситуации давали один и тот же объект — пустой
`SwingContext` и нулевые `SwingMetrics`:

1. ряд короче, чем нужно детектору (`legs * 2` у ZigZag);
2. вырожденный ряд (почти константные high/low — на нём numba-ядро pandas-ta падает
   нативно, поэтому ветка и появилась);
3. детектор недоступен (`pandas-ta` пропущен, `zigzag` не найден, исключение внутри);
4. детектор отработал и не нашёл движений — **это замер**.

Замер цены на встроенном сэмпле (`tv_xauusd_1h`, MACD по линии, 30 зон): здоровый
прогон — 29 зон со свингами, 193 свинга; тот же прогон со сломанным детектором — те
же 30 зон, **0** со свингами, и `build()` успешен. Отличить одно от другого читателю
результата было нечем: причина жила только в строке лога.

Теперь: глобальный проход без детектора **отказывает** (класс G54 — просили один
алгоритм, получили другой), а всякая законная пустота несёт `degraded` с именем
причины. Четвёртый случай — `degraded is None`: ноль как результат замера.
"""

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.models import SwingContext, SwingPoint
from bquant.analysis.zones.strategies.swing import ZigZagSwingStrategy
from bquant.core.exceptions import AnalysisError
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager


def _frame(n=60, flat=False):
    base = np.full(n, 100.0) if flat else np.linspace(100, 110, n) + np.sin(np.linspace(0, 6, n))
    return pd.DataFrame(
        {
            "open": base,
            "high": base if flat else base + 1.0,
            "low": base if flat else base - 1.0,
            "close": base,
            "volume": np.full(n, 1000.0),
        },
        index=pd.date_range("2024-01-01", periods=n, freq="h"),
    )


def _build(scope, data):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing="zigzag")
        .with_swing_scope(scope)
        .with_cache(enable=False)
        .analyze(clustering=False)
        .build()
    )


def _reasons(result):
    """(num_swings, degraded) по зонам — что читатель результата видит на самом деле."""
    seen = {}
    for zone in result.zones:
        metrics = (zone.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}
        key = (metrics.get("num_swings", 0), metrics.get("degraded"))
        seen[key] = seen.get(key, 0) + 1
    return seen


@pytest.fixture
def broken_detector(monkeypatch):
    """pandas-ta есть, а `zigzag` из неё не достаётся."""
    original = LibraryManager.create_indicator

    def unavailable(source, name, **params):
        if name == "zigzag":
            raise KeyError("LIBRARY indicator 'zigzag' from 'pandas_ta' not found")
        return original(source, name, **params)

    monkeypatch.setattr(LibraryManager, "create_indicator", staticmethod(unavailable))


def test_the_global_pipeline_refuses_instead_of_returning_a_successful_zero(broken_detector):
    """Тот же класс, что G54: неудавшийся глобальный проход — неудавшийся прогон."""
    data = get_sample_data("tv_xauusd_1h")

    with pytest.raises(RuntimeError) as exc:
        _build("global", data)

    message = str(exc.value)
    assert "zigzag" in message
    # Пайплайн обязан назвать и то, что просили, и выход: без этого отказ
    # неотличим от поломки самого пайплайна.
    assert "per_zone" in message or "swing" in message


def test_the_healthy_global_run_is_unchanged():
    """Отказ не должен стоить ничего тем, у кого детектор на месте."""
    result = _build("global", get_sample_data("tv_xauusd_1h"))

    assert len(result.zones) == 30
    with_swings = sum(
        1
        for z in result.zones
        if ((z.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}).get("num_swings")
    )
    assert with_swings == 29
    # Ни одна зона здорового прогона не помечена деградацией по вине детектора.
    assert all(
        ((z.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}).get("degraded")
        != "detector_unavailable"
        for z in result.zones
    )


def test_per_zone_keeps_running_but_says_why_the_metrics_are_zero(broken_detector):
    """Внутри зоны прогон продолжается — пустота названа, а не спрятана."""
    result = _build("per_zone", get_sample_data("tv_xauusd_1h"))

    reasons = _reasons(result)
    assert set(reasons) == {(0, "detector_unavailable"), (0, "too_short")}
    assert reasons[(0, "detector_unavailable")] == 27
    assert reasons[(0, "too_short")] == 3


def test_a_zone_where_the_detector_found_nothing_is_a_measurement():
    """Четвёртый случай: детектор отработал, движений нет — причины быть не должно."""
    result = _build("per_zone", get_sample_data("tv_xauusd_1h"))

    reasons = _reasons(result)
    empty_but_measured = reasons.get((0, None), 0)
    assert empty_but_measured > 0, reasons
    # И то же самое в обратную сторону: там, где свинги есть, причины нет.
    assert all(reason is None for count, reason in reasons if count)


def test_the_three_reasons_are_told_apart_at_the_strategy_level(broken_detector):
    """Одна и та же пустота, три разных имени."""
    short = ZigZagSwingStrategy(legs=10, deviation=0.01).calculate_global(_frame(12))
    assert short.degraded == "too_short"

    flat = ZigZagSwingStrategy(legs=2, deviation=0.01).calculate_global(_frame(200, flat=True))
    assert flat.degraded == "degenerate"

    # Недоступный детектор внутри зоны: контекст пуст и назван.
    per_zone = ZigZagSwingStrategy(legs=2, deviation=0.01)._swing_context(
        _frame(60), scope="per_zone"
    )
    assert per_zone.degraded == "detector_unavailable"

    with pytest.raises(AnalysisError):
        ZigZagSwingStrategy(legs=2, deviation=0.01).calculate_global(_frame(60))


def test_a_context_cannot_claim_a_reason_and_carry_points():
    """Инвариант модели: причина названа только у той пустоты, которая пуста."""
    point = SwingPoint(0, pd.Timestamp("2024-01-01").to_pydatetime(), 5, 100.0, "peak")

    with pytest.raises(ValueError) as exc:
        SwingContext(
            swing_points=[point],
            indices=np.array([5]),
            full_data_length=100,
            strategy_name="zigzag",
            strategy_params={},
            degraded="too_short",
        )

    assert "degraded" in str(exc.value)
