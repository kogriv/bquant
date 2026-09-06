"""Один механизм — одна реализация (G65, находки аудита AQ-040…043).

Замер до правки (2026-09-06):

* четыре хелпера (`get_statistics`, `is_trending_up`, `is_trending_down`,
  `get_crossovers`) жили тремя копиями в `PreloadedIndicator`, `CustomIndicator` и
  `MACDPreloadedIndicator`; `get_crossovers` отдавал **две разные формы** ответа под
  одним именем, у `CustomIndicator` его не было, а `MACD.get_info()['available_methods']`
  его рекламировал — `MACD().get_crossovers(data)` → `AttributeError`;
* `calculate_moving_averages` считал EMA через фабрику только для первого периода, а
  остальные — `ewm(span).mean()` здесь же: расхождение с `ExponentialMovingAverage` на
  38 / 76 / 174 барах сэмпла для периодов 10 / 20 / 50, максимум 9.96 пункта;
  `IndicatorCalculator` хранил результат по голому имени, и `sma(period=50)` затирал
  `sma(period=10)`;
* пресеты собирали `RSI_{period}` и `AO_{fast}_{slow}` строками — второе место, знавшее
  соглашение pandas-ta об именах;
* `StrategyRegistry` повторял register/get/list пять раз с пятью словарями и без
  политики конфликтов: второй класс под тем же именем молча заменял первый.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.data.samples import get_sample_data
from bquant.indicators import (
    MACD,
    IndicatorFactory,
    MACDPreloadedIndicator,
    SimpleMovingAverage,
)
from bquant.indicators.calculators import (
    STANDARD_SUITE,
    IndicatorCalculator,
    calculate_moving_averages,
    create_indicator_suite,
)
from bquant.analysis.zones.strategies.registry import FAMILIES, StrategyRegistry

PACKAGE = Path(__file__).resolve().parents[2] / "bquant"
HELPERS = ("get_statistics", "is_trending_up", "is_trending_down", "get_crossovers")


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


# --- AQ-040 ---------------------------------------------------------------

def test_the_helpers_are_defined_once_on_the_base_class():
    owners = {}
    for path in (PACKAGE / "indicators").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in HELPERS]:
                owners.setdefault(fn.name, []).append(cls.name)
    assert owners == {name: ["BaseIndicator"] for name in HELPERS}, owners


@pytest.mark.parametrize("cls", [MACD, SimpleMovingAverage, MACDPreloadedIndicator])
def test_every_advertised_method_exists(cls):
    advertised = cls.get_info()["available_methods"]
    missing = [m for m in advertised if not callable(getattr(cls, m, None))]
    assert not missing, f"{cls.__name__} advertises {missing}"
    assert set(HELPERS) <= set(advertised)


def test_custom_macd_has_crossovers_with_the_same_shape_as_preloaded(data):
    custom = MACD().get_crossovers(data)
    preloaded = MACDPreloadedIndicator().get_crossovers(data)
    assert set(custom) == set(preloaded) >= {"bullish_crossovers", "bearish_crossovers", "bullish_indices"}
    assert isinstance(custom["bullish_crossovers"], int) and custom["bullish_crossovers"] > 0


def test_a_helper_refuses_instead_of_answering_with_an_empty_dict(data):
    with pytest.raises(ValueError, match="needs 2 output column"):
        SimpleMovingAverage(period=10).get_crossovers(data)
    with pytest.raises(ValueError, match="not among the outputs"):
        MACD().is_trending_up(data, column="no_such_column")


# --- AQ-041 ---------------------------------------------------------------

def test_moving_averages_are_the_indicator_objects_bar_for_bar(data):
    frame = calculate_moving_averages(data, periods=[10, 50])
    for period in (10, 50):
        for name in ("sma", "ema"):
            expected = IndicatorFactory.create("custom", name, period=period).calculate(data).data.iloc[:, 0]
            assert np.array_equal(frame[f"{name}_{period}"].to_numpy(), expected.to_numpy(), equal_nan=True), \
                f"{name}_{period} differs from the indicator object"


def test_the_suite_is_computed_by_indicator_objects_and_keyed_by_identity(data):
    suite = create_indicator_suite(data)
    assert list(suite) == [
        IndicatorFactory.create("custom", n, **p).get_indicator_id().slug for n, p in STANDARD_SUITE
    ]
    ema26 = IndicatorFactory.create("custom", "ema", period=26).calculate(data).data
    assert suite["ema_26"].data.equals(ema26)


def test_the_calculator_keeps_two_parameterizations_of_one_indicator(data):
    calc = IndicatorCalculator(data, auto_load_libraries=False)
    calc.calculate("sma", period=10)
    calc.calculate("sma", period=50)
    assert set(calc.get_all_results()) == {"custom.sma_10", "custom.sma_50"}
    with pytest.raises(KeyError, match="names 2 results"):
        calc.get_result("sma")
    assert calc.get_result("custom.sma_50").data.columns.tolist() == ["sma_50"]


def test_no_moving_average_is_written_by_hand_in_calculators():
    src = (PACKAGE / "indicators" / "calculators.py").read_text(encoding="utf-8")
    assert ".rolling(" not in src and ".ewm(" not in src


# --- AQ-042 ---------------------------------------------------------------

def test_presets_do_not_spell_library_column_names():
    tree = ast.parse((PACKAGE / "analysis" / "zones" / "presets.py").read_text(encoding="utf-8"))
    def spells_a_column(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value.startswith(("RSI_", "AO_"))
        if isinstance(node, ast.JoinedStr):
            return any(spells_a_column(part) for part in node.values)
        return False

    spelled = sorted({node.lineno for node in ast.walk(tree) if spells_a_column(node)})
    assert not spelled, f"presets.py builds column names by template at lines {spelled}"


def test_the_rsi_preset_detects_on_the_column_the_indicator_declares(data):
    from bquant.analysis.zones.presets import analyze_rsi_zones

    result = analyze_rsi_zones(data, period=21, clustering=False, enable_cache=False)
    declared = IndicatorFactory.create("pandas_ta", "rsi", length=21).get_output_columns()[0]
    assert declared in result.data.columns
    assert result.zones and all(z.indicator_context.get("detection_indicator") for z in result.zones)


# --- AQ-043 ---------------------------------------------------------------

def test_the_registry_has_one_bucket_per_family_and_nothing_else():
    assert set(StrategyRegistry._registry) == set(FAMILIES)
    private = [n for n in vars(StrategyRegistry) if n.startswith("_") and not n.startswith("__") and n != "_registry" and not callable(getattr(StrategyRegistry, n))]
    assert private == [], private
    assert StrategyRegistry.list_all_strategies() == {f: StrategyRegistry.list_strategies(f) for f in FAMILIES}


def test_registering_a_different_class_under_a_taken_name_is_refused():
    class First:
        pass

    class Second:
        pass

    StrategyRegistry.register("shape", "g65_tmp")(First)
    try:
        StrategyRegistry.register("shape", "g65_tmp")(First)  # same class: no-op
        with pytest.raises(ValueError, match="already registered"):
            StrategyRegistry.register("shape", "g65_tmp")(Second)
        assert StrategyRegistry.get("shape", "g65_tmp").__class__ is First
    finally:
        del StrategyRegistry._registry["shape"]["g65_tmp"]


def test_an_unknown_family_is_refused_by_name():
    with pytest.raises(ValueError, match="Unknown strategy family"):
        StrategyRegistry.list_strategies("colour")
