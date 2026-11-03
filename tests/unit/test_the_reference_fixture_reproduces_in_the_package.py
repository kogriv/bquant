"""The package reproduces the requester's reference implementation to the digit.

The fixture under ``tests/fixtures/evaluation/`` is synthetic (seed 20261103): 525
trades over three years with one empty month, six windows of eight runs, a balance
curve, and ``expected.json`` — what the reference code printed on exactly these files.
Every number in it is a pre-registered expectation (trace log 2026-11-03): a mismatch
is a defect in the package or in the frozen specification, never a "feature".

Where the package departs from the reference on purpose — key names without a unit
suffix, an empty quarter carried forward, the tail under water — the departure is
listed in ``devref/architecture/evaluation_module_2026-11.md`` §4 and does not change
a single number here (the fixture's quarters are contiguous).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import (
    BeatsRandom,
    BlockBootstrap,
    Criterion,
    MinTrades,
    NetPositive,
    YearsStable,
    benjamini_hochberg,
    evaluate_procedure,
    quarterly_summary,
    trial_stats,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "evaluation"

#: package key → reference key (the reference suffixed its unit; the contract does not)
SUMMARY_KEYS = {
    "n": "n", "long_share": "long_share",
    "net_mean": "net_atr", "net_lo": "net_lo", "net_hi": "net_hi",
    "gross_mean": "gross_atr", "cost_mean": "cost_atr", "rand_mean": "rand_atr",
    "excess_mean": "excess_atr", "excess_lo": "excess_lo", "excess_hi": "excess_hi",
    "excess_se": "excess_se", "p": "p", "p_boot": "p_boot", "hit": "hit",
    "hold_mean": "hold_mean",
    "years_n": "years_n", "years_net_pos": "years_net_pos", "years_ex_pos": "years_ex_pos",
}


@pytest.fixture(scope="module")
def expected():
    return json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def trades():
    return pd.read_csv(FIXTURE / "trades.csv", parse_dates=["entry_time", "exit_time"])


@pytest.fixture(scope="module")
def bootstrap(expected):
    lo, hi = expected["bootstrap"]["months"]
    return BlockBootstrap(np.arange(lo, hi + 1), B=expected["bootstrap"]["B"], seed=expected["bootstrap"]["seed"])


@pytest.fixture(scope="module")
def summary(trades, bootstrap):
    return trial_stats(trades, bootstrap)


def _same(actual, wanted):
    if wanted is None:
        return actual is None or (isinstance(actual, float) and math.isnan(actual))
    return math.isclose(float(actual), float(wanted), rel_tol=1e-9, abs_tol=1e-12)


def test_the_fixture_is_the_one_the_expectations_were_written_for(trades, expected):
    assert len(trades) == expected["trial_stats"]["n"] == 525
    months = trades["entry_time"].dt.year * 12 + trades["entry_time"].dt.month - 1
    lo, hi = expected["bootstrap"]["months"]
    assert set(range(lo, hi + 1)) - set(months) == {2022 * 12 + 6}, "exactly one empty month: 2022-07"


def test_the_summary_reproduces_every_number(summary, expected):
    wanted = expected["trial_stats"]
    off = {k: (summary[k], wanted[ref]) for k, ref in SUMMARY_KEYS.items() if not _same(summary[k], wanted[ref])}
    assert not off, off
    assert summary["p"] == pytest.approx(0.2279927532475281, rel=1e-9)
    assert summary["excess_se"] == pytest.approx(0.037810194280264574, rel=1e-9)


def test_the_years_reproduce(summary, expected):
    for year, wanted in expected["years"].items():
        got = summary["years"][int(year)]
        assert got["n"] == wanted["n"]
        assert got["net"] == pytest.approx(wanted["net"], rel=1e-9)
        assert got["ex"] == pytest.approx(wanted["ex"], rel=1e-9)


def test_benjamini_hochberg_with_m_from_the_caller(expected):
    p = np.array([np.nan if v is None else v for v in expected["bh"]["p"]])
    q = benjamini_hochberg(p, expected["bh"]["m_total"])
    for got, wanted in zip(q, expected["bh"]["q"]):
        assert _same(got, wanted), (got, wanted)


def test_the_criterion_reproduces_the_four_rows_and_none_passes(summary, expected):
    base = {k: v for k, v in summary.items() if k != "years"}
    table = pd.DataFrame([base, {**base, "p": base["p"] / 10, "n": 500}, {**base, "n": 50}, {**base, "p": np.nan}])
    crit = Criterion(rules=[MinTrades(100), NetPositive(), YearsStable(2 / 3), BeatsRandom(0.05, 0.0)])
    result = crit.evaluate(table, m_total=expected["criterion"]["m_total"])
    for got, wanted in zip(result.to_dict("records"), expected["criterion"]["rows"]):
        assert got["n"] == wanted["n"]
        assert _same(got["p"], wanted["p"])
        assert _same(got["q"], wanted["q"])
        for flag in ("ok_min_trades", "ok_net_positive", "ok_years_stable", "ok_beats_random", "pass"):
            assert got[flag] == wanted[flag], (flag, got, wanted)
    assert not result["pass"].any(), "pre-registered: no row passes on the fixture"


def test_the_procedure_reproduces_the_windows_and_the_t(expected):
    runs = pd.read_csv(FIXTURE / "windows.csv")
    result = evaluate_procedure(runs, {"a": 2, "b": 3})
    for got, wanted in zip(result.per_window.to_dict("records"), expected["procedure"]["per_window"]):
        for key in ("chosen", "defaults", "grid_mean", "grid_median", "grid_pos_share", "percentile", "oracle"):
            assert _same(got[key], wanted[key]), (got["window"], key, got[key], wanted[key])
    paired = result.paired
    assert paired.loc["chosen_vs_grid_mean", "t"] == pytest.approx(expected["procedure"]["t_chosen_vs_grid_mean"], rel=1e-9)
    assert paired.loc["chosen_vs_defaults", "t"] == pytest.approx(expected["procedure"]["t_chosen_vs_defaults"], rel=1e-9)
    for variant, wanted in expected["procedure"]["sum"].items():
        assert result.series.loc[variant, "sum"] == pytest.approx(wanted, rel=1e-9)


def test_the_quarters_reproduce(expected):
    curve = pd.read_csv(FIXTURE / "balance.csv", parse_dates=["exit_time"]).set_index("exit_time")["balance"]
    wanted = expected["quarters"]
    got = quarterly_summary(curve, initial=wanted["initial"])
    assert got["q_n"] == wanted["q_n"] == 13
    assert got["q_pos"] == wanted["q_pos"]
    for key in ("q_median", "q_worst", "q_mean_over_std", "max_dd"):
        assert got[key] == pytest.approx(wanted[key], rel=1e-9), key
    assert got["longest_underwater_days"] == wanted["longest_underwater_days"]
    for quarter_end, ret in wanted["q_returns"].items():
        assert got["q_returns"][pd.Timestamp(quarter_end)] == pytest.approx(ret, abs=1e-8), quarter_end
