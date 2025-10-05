"""Tests for the dynamic pandas-ta loader integration."""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.core.exceptions import IndicatorCalculationError
from bquant.indicators.base import IndicatorFactory, LibraryIndicator
from bquant.indicators.library.manager import LibraryManager
from bquant.indicators.library.pandas_ta import PandasTALoader


@pytest.fixture
def pandas_ta_test_env(monkeypatch):
    """Reset loader state and configure discovery for tests."""

    monkeypatch.setattr(PandasTALoader, "_indicators_registered", False)
    monkeypatch.setattr(PandasTALoader, "_available_indicators", [])
    monkeypatch.setattr(PandasTALoader, "_function_cache", {})
    monkeypatch.setattr(PandasTALoader, "_ta_module", None)
    monkeypatch.setattr(
        PandasTALoader, "is_available", classmethod(lambda cls: True)
    )
    monkeypatch.setattr(IndicatorFactory, "_registry", {})
    monkeypatch.setattr(IndicatorFactory, "_library_functions", {})
    monkeypatch.setattr(LibraryManager, "_loaders", {"pandas_ta": None})

    def configure(functions):
        def stub(cls):
            cls._function_cache = functions
            cls._available_indicators = sorted(functions.keys())
            return functions

        monkeypatch.setattr(
            PandasTALoader,
            "_discover_all_functions",
            classmethod(stub),
        )

    return configure


def test_load_all_libraries_registers_dynamic_indicators(
    pandas_ta_test_env, monkeypatch
):
    """Ensure the loader registers every discovered indicator and reports via logs."""

    def simple_sma(close, length: int = 3):
        return close.rolling(length).mean()

    def range_indicator(high, low, close, window: int = 2):
        return pd.DataFrame({"range": (high - low).abs()})

    functions = {
        "simple_sma": simple_sma,
        "range_indicator": range_indicator,
    }
    pandas_ta_test_env(functions)

    loader_messages = []
    manager_messages = []

    def make_recorder(collection):
        def recorder(message, *args, **kwargs):
            if args:
                try:
                    collection.append(message % args)
                except TypeError:
                    collection.append(message)
            else:
                collection.append(message)

        return recorder

    monkeypatch.setattr(
        "bquant.indicators.library.pandas_ta.logger.info",
        make_recorder(loader_messages),
    )
    monkeypatch.setattr(
        "bquant.indicators.library.manager.logger.info",
        make_recorder(manager_messages),
    )

    results = LibraryManager.load_all_libraries()

    assert results == {"pandas_ta": 2}
    assert set(IndicatorFactory._registry.keys()) == {
        "pandas_ta_simple_sma",
        "pandas_ta_range_indicator",
    }

    info = LibraryManager.get_library_info("pandas_ta")
    assert info["available"] is True
    assert info["indicators_count"] == 2
    assert sorted(info["indicators"]) == ["range_indicator", "simple_sma"]

    assert any("Registered 2 pandas-ta indicators" in msg for msg in loader_messages)
    combined_messages = "\n".join(manager_messages)
    assert "Loaded 2 indicators from pandas_ta" in combined_messages


def test_indicator_calculation_wraps_failures(pandas_ta_test_env):
    """Indicator.calculate should surface errors as IndicatorCalculationError."""

    def unstable(close, fail: bool = False):
        if fail:
            raise RuntimeError("boom")
        return close

    pandas_ta_test_env({"unstable": unstable})

    LibraryManager.load_all_libraries()

    indicator = IndicatorFactory.create("pandas_ta", "unstable")
    data = PandasTALoader._generate_sample_data()

    with pytest.raises(IndicatorCalculationError, match="boom"):
        indicator.calculate(data, fail=True)


def test_library_manager_exposes_new_indicators(pandas_ta_test_env):
    """A newly discovered pandas-ta function should be ready for use immediately."""

    def brand_new(close, length: int = 4):
        return pd.DataFrame({"brand_new": close.rolling(length).mean()})

    pandas_ta_test_env({"brand_new": brand_new})

    LibraryManager.load_all_libraries()

    factory_indicator = IndicatorFactory.create("pandas_ta", "brand_new", length=5)
    assert isinstance(factory_indicator, LibraryIndicator)

    data = PandasTALoader._generate_sample_data()
    result = factory_indicator.calculate(data)
    assert "brand_new" in result.data.columns

    manager_indicator = LibraryManager.create_indicator(
        "pandas_ta", "brand_new", length=6
    )
    assert isinstance(manager_indicator, LibraryIndicator)
    manager_result = manager_indicator.calculate(data)
    assert "brand_new" in manager_result.data.columns

    indicators = IndicatorFactory.list_indicators()
    assert indicators["pandas_ta_brand_new"] == "library"
