"""Output-column contract tests (G8 stage A).

Three properties are pinned here, each because it was broken or unenforced:

1. **Declared == actual.** Every indicator states its columns in
   ``get_output_columns()`` and then rebuilds the same names inside ``calculate()``.
   Nothing checked that the two agreed, so they could drift silently. They agreed
   when measured on 2026-08-23 — this pins that starting point so the G8 refactor
   can tell "broken in transit" from "was already broken".

2. **Library columns describe the parameters actually requested (G18).**
   ``pandas_ta.py`` used to overwrite the names pandas-ta returned with names
   derived once, at registration time, from default parameters. ``rsi(length=50)``
   computed RSI-50 correctly and labelled the column ``RSI_14``. The values were
   right; the label lied.

3. **Overwriting an input column is announced (G17).** The pipeline merges
   indicator output into the caller's frame by unconditional assignment. The
   bundled TradingView sample carries its own ``macd`` column, so computing MACD
   replaces it. The overwrite stays — some callers legitimately recompute — but it
   is no longer silent.

Analysis: ``devref/gaps/columns/g8_column_contract_measurement_2026-08-23.md``
"""

import logging

import pandas as pd
import pytest

from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory


# Every custom indicator that ships, with non-default parameters where the
# indicator takes any — defaults alone would not exercise parameter handling.
CUSTOM_CASES = [
    ("sma", {"period": 20}, {"period": 35}),
    ("ema", {"period": 20}, {"period": 35}),
    ("rsi", {"period": 14}, {"period": 21}),
    (
        "macd",
        {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        {"fast_period": 5, "slow_period": 35, "signal_period": 5},
    ),
    ("bbands", {"period": 20}, {"period": 50}),
]


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


# --------------------------------------------------------------------------- #
# 1. Declared == actual
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, params",
    [(n, p) for n, p, _ in CUSTOM_CASES] + [(n, p) for n, _, p in CUSTOM_CASES],
    ids=[f"{n}-default" for n, _, _ in CUSTOM_CASES]
    + [f"{n}-nondefault" for n, _, _ in CUSTOM_CASES],
)
def test_custom_declared_columns_match_actual(name, params, data):
    """get_output_columns() must describe what calculate() actually emits."""
    indicator = IndicatorFactory.create("custom", name, **params)
    declared = indicator.get_output_columns()
    actual = indicator.calculate(data).data.columns.tolist()
    assert declared == actual, (
        f"custom.{name}{params}: declares {declared} but emits {actual}. "
        "The two are written as separate literals in the indicator module; keep them "
        "in step (G8 stage B removes the duplication)."
    )


# --------------------------------------------------------------------------- #
# 2. G18 — library columns describe the requested parameters
# --------------------------------------------------------------------------- #
# Curated rather than exhaustive: these are the indicators the documentation
# actually teaches. A blanket sweep over all 158 registered functions would also
# catch `pivots`, whose column count legitimately depends on the input index
# (pandas-ta emits one column instead of nine without an ordered DatetimeIndex) —
# that is the library's behaviour, not our contract.
LIBRARY_CASES = [
    ("rsi", "length", [14, 21, 50]),
    ("sma", "length", [10, 20, 50]),
    ("ema", "length", [10, 20, 50]),
]


@pytest.fixture(scope="module")
def pandas_ta():
    return pytest.importorskip("pandas_ta", reason="pandas-ta not installed")


@pytest.fixture(scope="module")
def library_manager(pandas_ta):
    from bquant.indicators import LibraryManager

    LibraryManager.load_all_libraries()
    return LibraryManager


@pytest.mark.parametrize(
    "name, param, values",
    LIBRARY_CASES,
    ids=[n for n, _, _ in LIBRARY_CASES],
)
def test_library_columns_name_the_requested_parameters(
    name, param, values, data, pandas_ta, library_manager
):
    """The column label must agree with the parameters the caller asked for.

    Checked against pandas-ta's own naming rather than a hardcoded expectation:
    the library is the authority on what its output is called, and the G18 defect
    was precisely that we overwrote its answer with our own stale one.
    """
    emitted = []
    for value in values:
        indicator = library_manager.create_indicator("pandas_ta", name, **{param: value})
        columns = indicator.calculate(data).data.columns.tolist()

        expected = getattr(pandas_ta, name)(data["close"], **{param: value})
        expected_names = (
            [expected.name]
            if isinstance(expected, pd.Series)
            else expected.columns.tolist()
        )

        assert columns == expected_names, (
            f"pandas_ta.{name}({param}={value}) emitted {columns}, but pandas-ta names "
            f"its own result {expected_names}. Registration-time names must not be "
            "reused for an instance built with different parameters (G18)."
        )
        emitted.append(tuple(columns))

    assert len(set(emitted)) == len(values), (
        f"pandas_ta.{name}: different {param} values produced the same column names "
        f"{emitted} — the parameters are not recoverable and the instances collide."
    )


def test_library_declared_columns_match_actual(data, library_manager):
    """The declaration must track the instance's parameters, not the defaults."""
    for name, param, values in LIBRARY_CASES:
        for value in values:
            indicator = library_manager.create_indicator(
                "pandas_ta", name, **{param: value}
            )
            declared = indicator.get_output_columns()
            actual = indicator.calculate(data).data.columns.tolist()
            assert declared == actual, (
                f"pandas_ta.{name}({param}={value}) declares {declared} "
                f"but emits {actual}"
            )


def test_library_defaults_are_unchanged(data, library_manager, pandas_ta):
    """Repairing G18 must not move the names for callers who passed no parameters."""
    indicator = library_manager.create_indicator("pandas_ta", "rsi")
    assert indicator.calculate(data).data.columns.tolist() == ["RSI_14"]


# --------------------------------------------------------------------------- #
# 3. G17 — overwriting an input column is announced
# --------------------------------------------------------------------------- #
class _Capture(logging.Handler):
    """Collect records straight off the module logger.

    `caplog` does not see these: bquant loggers do not propagate to root.
    """

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_pipeline_warns_when_indicator_overwrites_input_column(data):
    """The bundled sample already has a `macd` column; computing MACD replaces it."""
    from bquant.analysis.zones import analyze_macd_zones
    from bquant.analysis.zones.pipeline import ZoneAnalysisPipeline

    assert "macd" in data.columns, (
        "fixture assumption broken: this sample used to ship its own 'macd' column, "
        "which is what makes the overwrite observable"
    )

    logger = logging.getLogger(ZoneAnalysisPipeline.__module__)
    handler = _Capture()
    logger.addHandler(handler)
    try:
        # Cache disabled deliberately: a cached result short-circuits _prepare_data,
        # so the warning is a cold-run signal. The overwrite is baked into the cached
        # result either way — the caller simply saw the warning on the run that
        # produced it.
        analyze_macd_zones(data, enable_cache=False)
    finally:
        logger.removeHandler(handler)

    messages = [r.getMessage() for r in handler.records]
    overwrite_warnings = [m for m in messages if "overwrites" in m]
    assert overwrite_warnings, (
        f"no overwrite warning emitted; captured warnings were {messages}"
    )
    assert "'macd'" in overwrite_warnings[0], (
        f"the warning must name the column it replaced: {overwrite_warnings[0]}"
    )


def test_pipeline_is_quiet_when_nothing_is_overwritten():
    """A frame without colliding names must not produce the warning.

    Guards against the check degrading into an unconditional warning, which would
    train users to ignore it.
    """
    import numpy as np

    from bquant.analysis.zones import analyze_zones
    from bquant.analysis.zones.pipeline import ZoneAnalysisPipeline

    raw = get_sample_data("tv_xauusd_1h")
    clean = raw[["open", "high", "low", "close", "volume"]].copy()
    assert not {"macd", "macd_signal", "macd_hist"} & set(clean.columns)

    logger = logging.getLogger(ZoneAnalysisPipeline.__module__)
    handler = _Capture()
    logger.addHandler(handler)
    try:
        (
            analyze_zones(clean)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26,
                            signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=False)
            .with_cache(False)
            .build()
        )
    finally:
        logger.removeHandler(handler)

    overwrite_warnings = [m for m in (r.getMessage() for r in handler.records)
                          if "overwrites" in m]
    assert not overwrite_warnings, (
        f"warned about an overwrite that did not happen: {overwrite_warnings}"
    )
