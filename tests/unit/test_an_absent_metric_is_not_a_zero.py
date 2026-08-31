"""Не измеренная величина обязана отсутствовать, а не равняться нулю.

G37. Три отдельных утверждения, каждое ловит свою половину дефекта:

1. `NaN` больше не проваливает проверку «>= 0» и не роняет всю группу метрик —
   у зоны длиной ровно в окно Боллинджера разброс ширины не определён, и это
   выражается `None`, а не отказом;
2. когда полосы посчитать нельзя вовсе, отсутствуют именно боллинджеровские
   величины, а ATR-часть остаётся измеренной (раньше возвращался полный набор
   нулей со `squeeze_ratio: 1.0` — правдоподобное измерение вместо признания);
3. инварианты проверяются исключением, а не `assert`: под `python -O` `assert`
   исчезает, и мусор уезжает в статистику молча.
"""

from __future__ import annotations

import ast
import inspect
import math

import pytest

from bquant.analysis.zones.strategies import base as base_module
from bquant.analysis.zones.strategies.base import VolatilityMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.core.exceptions import AnalysisError
from bquant.data.samples import get_sample_data


BB_LENGTH = 20


@pytest.fixture(scope="module")
def strategy():
    return StrategyRegistry.get_volatility_strategy("combined")


@pytest.fixture(scope="module")
def prices():
    return get_sample_data("tv_xauusd_1h")


def test_a_zone_exactly_one_window_long_keeps_its_metrics(strategy, prices):
    """Окно наполняется один раз, `std` по одному значению — `NaN`.

    Раньше здесь срабатывал `assert bollinger_width_std >= 0`, и зона теряла все
    десять величин, включая посчитанные ATR-метрики.
    """

    metrics = strategy.calculate_volatility(prices.head(BB_LENGTH))

    assert metrics.bollinger_width_std is None
    assert metrics.bollinger_width_pct is not None
    assert metrics.avg_atr is not None


def test_absent_bollinger_does_not_pretend_to_be_zero(strategy, prices):
    """Зона короче окна: полос нет, ATR есть."""

    metrics = strategy.calculate_volatility(prices.head(5))

    assert metrics.bollinger_width_pct is None
    assert metrics.bollinger_squeeze_ratio is None
    assert metrics.atr_normalized_range is not None
    assert metrics.avg_atr is not None


def test_the_composite_score_is_absent_together_with_its_parts(strategy, prices):
    """Композит 0–10 на две трети боллинджеровский.

    Число по той же шкале, посчитанное без двух компонент, несопоставимо с
    остальными зонами — поэтому его нет, а вместе с ним нет и подписи-режима.
    """

    metrics = strategy.calculate_volatility(prices.head(5))

    assert metrics.volatility_score is None
    assert metrics.volatility_regime is None


def test_nan_is_rejected_as_undefined_not_as_negative():
    """Сообщение об ошибке обязано называть происходящее своим именем."""

    metrics = VolatilityMetrics(
        bollinger_width_pct=1.0,
        bollinger_width_std=math.nan,
        bollinger_squeeze_ratio=1.0,
        bollinger_upper_touches=0,
        bollinger_lower_touches=0,
        atr_normalized_range=1.0,
        atr_trend="stable",
        avg_atr=1.0,
        volatility_score=5.0,
        volatility_regime="high",
        strategy_name="combined",
    )

    with pytest.raises(AnalysisError, match="bollinger_width_std is NaN"):
        metrics.validate()


def test_a_score_without_a_regime_is_a_contradiction():
    metrics = VolatilityMetrics(
        bollinger_width_pct=None,
        bollinger_width_std=None,
        bollinger_squeeze_ratio=None,
        bollinger_upper_touches=None,
        bollinger_lower_touches=None,
        atr_normalized_range=1.0,
        atr_trend="stable",
        avg_atr=1.0,
        volatility_score=5.0,
        volatility_regime=None,
        strategy_name="combined",
    )

    with pytest.raises(AnalysisError, match="отсутствовать вместе"):
        metrics.validate()


def test_invariants_do_not_disappear_under_optimisation():
    """`assert` выключается флагом `-O` целиком — вместе с проверкой.

    Проверяется источник, а не поведение: под обычным прогоном разницы между
    `assert` и `raise` не видно, а под `-O` видно слишком поздно.
    """

    tree = ast.parse(inspect.getsource(base_module))
    offenders = [
        f"{node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Assert)
    ]

    assert not offenders, (
        "В strategies/base.py снова появился `assert` (строки: "
        + ", ".join(offenders)
        + "). Инвариант метрики — утверждение о данных, а не о коде: "
        "используйте `_require`, он переживает `python -O`."
    )
