"""Исход при заданном баре выхода: векторно, побитно как построчный путь.

Фикстура — `tests/fixtures/trading/zone_trades/` (лаборатории): `exit_at.csv` — один набор,
`exit_at_sets.csv` — пять наборов с ожидаемыми матрицами `net`. Векторная функция обязана
совпасть с фикстурой и **побитно** с `zone_trades(..., exit=ExitAt())` — на фикстуре и на
случайных барах выхода; построчный путь она не зовёт.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import CostModel, permutation_placebo
from bquant.analysis.trading import (
    ColumnStop, ExitAt, ExitMatrix, FixedAtrStop, NextOpen, ZoneBarClose, trades_at_exit, zone_trades,
)
import importlib

zone_trades_module = importlib.import_module("bquant.analysis.trading.zone_trades")

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HERE = FIXTURES / "trading" / "zone_trades"
REF = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
BARS = pd.read_csv(FIXTURES / "evaluation" / "baseline" / "bars.csv", parse_dates=["time"]).set_index("time")
ZONES = pd.read_csv(HERE / "zones.csv")
SIGNALS = pd.read_csv(HERE / "signals.csv")
EXIT_AT = pd.read_csv(HERE / "exit_at.csv")
SETS = pd.read_csv(HERE / "exit_at_sets.csv").pivot(index="set", columns="zone_id", values="exit_idx")
TRADES = pd.read_csv(HERE / "trades.csv", parse_dates=["decision_time", "entry_time", "exit_time"])
SKIPPED = pd.read_csv(HERE / "skipped.csv")
POINT, TOL = REF["point"], REF["tolerance"]
COST = CostModel(spread="bar", min_spread_points=15.0, commission_points=7.0)
VARIANTS = {
    "exit_at_none": dict(),
    "exit_at_stop2": dict(stop=FixedAtrStop(2.0)),
    "exit_at_stopcol_cost": dict(stop=ColumnStop("stop_atr"), costs=COST),
}


def _rowwise(exit_idx, **kw):
    zones = ZONES.assign(exit_idx=np.asarray(exit_idx, dtype=np.int64))
    return zone_trades(BARS, zones, point=POINT, exit=ExitAt(), signals=SIGNALS, **kw)


def _vector(exit_idx, **kw):
    return trades_at_exit(BARS, ZONES, exit_idx, point=POINT, signals=SIGNALS, **kw)


@pytest.mark.parametrize("name", list(VARIANTS))
def test_one_set_reproduces_the_fixture_and_the_rowwise_path_bit_for_bit(name):
    exit_idx = EXIT_AT.set_index("zone_id").loc[ZONES["zone_id"], "exit_idx"].to_numpy()
    fast = _vector(exit_idx, **VARIANTS[name])
    slow = _rowwise(exit_idx, **VARIANTS[name])
    pd.testing.assert_frame_equal(fast.trades, slow.trades, check_exact=True)
    pd.testing.assert_frame_equal(fast.skipped, slow.skipped, check_exact=True)
    want = TRADES[TRADES["variant"] == name].reset_index(drop=True)
    assert fast.trades["exit_reason"].tolist() == want["exit_reason"].tolist()
    np.testing.assert_allclose(fast.trades["net"], want["net_atr"], rtol=0, atol=TOL)
    assert fast.skipped["reason"].tolist() == SKIPPED[SKIPPED["variant"] == name]["reason"].tolist()


@pytest.mark.parametrize("name", ["exit_at_none", "exit_at_stop2"])
def test_many_sets_give_the_expected_matrix(name):
    got = _vector(SETS.to_numpy(), **VARIANTS[name])
    assert isinstance(got, ExitMatrix) and got.net.shape == tuple(REF["exit_at_sets"]["shape"])
    want = np.array([[np.nan if v is None else v for v in row] for row in REF["exit_at_sets"]["net"][name]])
    assert np.array_equal(np.isnan(got.net), np.isnan(want))
    np.testing.assert_allclose(got.net[~np.isnan(want)], want[~np.isnan(want)], rtol=0, atol=TOL)
    assert (got.skip_reason[np.isnan(want)] != None).all() and (got.skip_reason[~np.isnan(want)] == None).all()  # noqa: E711


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("kw", [dict(), dict(stop=FixedAtrStop(1.0), costs=COST), dict(entry=NextOpen(), stop=FixedAtrStop(0.5)),
                                dict(entry=ZoneBarClose(k=2, side="against_zone"), stop=ColumnStop("stop_atr"))],
                         ids=["plain", "stop+cost", "next_open", "k2_against_column_stop"])
def test_random_exit_bars_match_the_rowwise_path_cell_by_cell(seed, kw):
    rng = np.random.default_rng(seed)
    sets = np.array([[rng.integers(s - 2, e + 5) for s, e in zip(ZONES["start_idx"], ZONES["end_idx"])] for _ in range(6)])
    matrix = _vector(sets, **kw)
    for r, row in enumerate(sets):
        slow = _rowwise(row, **kw)
        fast = _vector(row, **kw)
        pd.testing.assert_frame_equal(fast.trades, slow.trades, check_exact=True)
        pd.testing.assert_frame_equal(fast.skipped, slow.skipped, check_exact=True)
        net = pd.Series(matrix.net[r], index=ZONES["zone_id"])
        assert np.array_equal(net.dropna().index, slow.trades["zone_id"])
        assert (net.dropna().to_numpy() == slow.trades["net"].to_numpy()).all()
        assert (pd.Series(matrix.hold[r], index=ZONES["zone_id"]).dropna().to_numpy() == slow.trades["hold"].to_numpy()).all()


def test_the_vector_path_never_builds_a_trade_row_by_row(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the vector path called the row-by-row builder")
    monkeypatch.setattr(zone_trades_module._Builder, "trade", refuse)
    with pytest.raises(AssertionError, match="row-by-row"):
        _rowwise(EXIT_AT["exit_idx"])                    # the guard is armed
    got = _vector(SETS.to_numpy(), stop=FixedAtrStop(2.0))
    assert got.net.shape == SETS.shape


def test_a_batched_placebo_is_the_one_by_one_placebo_bit_for_bit():
    exit_idx = EXIT_AT.set_index("zone_id").loc[ZONES["zone_id"], "exit_idx"].to_numpy()
    base = _vector(exit_idx).trades.set_index("zone_id")["net"]
    candidates = exit_idx.copy()

    def one(perm):
        shuffled = candidates[perm]
        return float(np.nanmean(_vector(shuffled).trades.set_index("zone_id")["net"].reindex(ZONES["zone_id"])))

    def batch(perms):
        return np.nanmean(_vector(candidates[perms]).net, axis=1)

    observed = float(base.mean())
    slow = permutation_placebo(observed, one, n_units=len(candidates), n_perm=30, seed=3)
    fast = permutation_placebo(observed, batch, n_units=len(candidates), n_perm=30, seed=3, batched=True)
    assert fast == slow
    with pytest.raises(ValueError, match="one value per permutation"):
        permutation_placebo(0.0, lambda perms: np.zeros(3), n_units=5, n_perm=4, batched=True)


@pytest.mark.parametrize("bad, reason", [
    (np.zeros(3, dtype=int), "one bar per zone"),
    (np.zeros((2, 10)), "whole bar positions"),
    (np.zeros((2, 3, 10), dtype=int), "one bar per zone"),
])
def test_exit_bars_that_do_not_fit_the_zones_are_refused(bad, reason):
    with pytest.raises(ValueError, match=reason):
        _vector(bad)


def test_exit_at_reads_its_bar_from_the_zone_frame():
    with pytest.raises(ValueError, match="no \\["):
        zone_trades(BARS, ZONES, point=POINT, exit=ExitAt())
    with pytest.raises(ValueError, match="pass zones as a frame"):
        class Zone:
            zone_id, type, start_idx, end_idx = 0, "bull", 20, 30
        zone_trades(BARS, [Zone()], point=POINT, exit=ExitAt())
