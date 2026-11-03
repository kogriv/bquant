"""Every edge the evaluation module decides is written down here — and each check is
mutation-verified: undo the decision in the code and the matching test goes red.

The decisions (``devref/architecture/evaluation_module_2026-11.md`` §3–§4):

* an empty month is a block — leaving it out narrows every interval;
* a replicate that drew no trade is dropped, not redrawn;
* ``m_total`` from the caller only makes the correction stricter; a candidate with too
  few trades is unranked **before** the correction but still counted;
* a value on a strict threshold has not passed it;
* the baseline is the exact mean over every eligible bar — equal to brute force;
* a quarter without trades is a quarter with return 0; the stretch after the last high
  is reported;
* the input contract refuses by name and never coerces.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import (
    BeatsRandom,
    BlockBootstrap,
    Criterion,
    MinEffect,
    MinTrades,
    NetPositive,
    QuarterMedian,
    QuartersPositive,
    WorstQuarter,
    YearsStable,
    apply_rules,
    attach_random_baseline,
    benjamini_hochberg,
    evaluate_procedure,
    month_key,
    months_between,
    quarterly_summary,
    random_entry_baseline,
    trial_stats,
    validate_trades,
)


SEGMENT = ("2021-01-01", "2023-01-31")   # the synthetic entries run from 2021-01-04 into January 2023


def _trades(n=120, seed=0, start="2021-01-04 09:00", skip_month=None):
    rng = np.random.default_rng(seed)
    hours = np.sort(rng.integers(0, 2 * 365 * 24, n))
    entry = pd.Timestamp(start) + pd.to_timedelta(hours, "h")
    frame = pd.DataFrame({
        "entry_time": entry,
        "side": rng.choice([-1, 1], n),
        "net": rng.normal(0.05, 1.0, n),
        "rand": rng.normal(0.0, 0.3, n),
        "hold": rng.integers(2, 30, n),
    })
    frame["exit_time"] = frame["entry_time"] + pd.to_timedelta(frame["hold"], "h")
    if skip_month is not None:
        frame = frame[~((frame["entry_time"].dt.year == skip_month[0]) & (frame["entry_time"].dt.month == skip_month[1]))]
    return frame.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# bootstrap
# --------------------------------------------------------------------------- #
def test_an_empty_month_is_a_block_and_leaving_it_out_narrows_the_interval():
    trades = _trades(skip_month=(2021, 7))
    segment = months_between(*SEGMENT)
    busy = np.unique(month_key(trades["entry_time"]))
    assert 2021 * 12 + 6 in segment and 2021 * 12 + 6 not in busy
    with_empty = trial_stats(trades, BlockBootstrap(segment, B=500, seed=1))
    without = trial_stats(trades, BlockBootstrap(busy, B=500, seed=1))
    assert with_empty["net_mean"] == without["net_mean"]
    assert with_empty["net_hi"] - with_empty["net_lo"] != without["net_hi"] - without["net_lo"]


def test_a_replicate_that_drew_no_trade_is_dropped_not_redrawn():
    months = np.array([0, 1, 2, 3])            # trades only in month 1: a replicate may miss it
    boot = BlockBootstrap(months, B=400, seed=3)
    replicates = boot.means(np.array([1.0, 2.0, 3.0]), np.array([1, 1, 1]))
    assert np.isnan(replicates).any(), "with three empty months some replicate draws no trade"
    lo, hi, se, kept = boot.interval(np.array([1.0, 2.0, 3.0]), np.array([1, 1, 1]))
    assert len(kept) == 400 - int(np.isnan(replicates).sum()) < 400
    assert lo == hi == 2.0 and se == 0.0, "every surviving replicate holds the same three trades"


def test_a_trade_outside_the_block_list_is_refused():
    boot = BlockBootstrap(months_between("2021-01-01", "2021-12-31"))
    with pytest.raises(ValueError, match="outside the bootstrap's block list"):
        boot.means(np.array([1.0]), np.array([2022 * 12]))


def test_the_same_seed_months_and_b_give_the_same_replicates():
    a = BlockBootstrap(np.arange(10), B=50, seed=7).W
    b = BlockBootstrap(np.arange(10), B=50, seed=7).W
    assert np.array_equal(a, b)
    assert a.sum(axis=1).tolist() == [10] * 50


# --------------------------------------------------------------------------- #
# correction
# --------------------------------------------------------------------------- #
def test_m_total_from_the_caller_only_makes_q_stricter():
    p = np.array([0.001, 0.01, 0.04])
    assert benjamini_hochberg(p, 3).tolist() == pytest.approx([0.003, 0.015, 0.04])
    assert benjamini_hochberg(p, 30).tolist() == pytest.approx([0.03, 0.15, 0.4])
    assert benjamini_hochberg(p, 1).tolist() == pytest.approx([0.003, 0.015, 0.04]), "m never below the number of p"
    assert np.isnan(benjamini_hochberg(np.array([np.nan, 0.5]), 2)[0])


def test_too_few_trades_is_unranked_before_the_correction_but_still_counted():
    table = pd.DataFrame({"n": [200, 10], "p": [0.01, 0.001], "net_mean": [1.0, 1.0],
                          "years_n": [3, 3], "years_net_pos": [3, 3], "excess_lo": [0.5, 0.5]})
    result = Criterion([MinTrades(100), BeatsRandom(0.05)]).evaluate(table, m_total=2)
    assert result.loc[0, "q"] == pytest.approx(0.02), "ranked alone among 2 tests: 0.01 * 2 / 1"
    assert np.isnan(result.loc[1, "q"])
    assert result["pass"].tolist() == [True, False]


# --------------------------------------------------------------------------- #
# thresholds
# --------------------------------------------------------------------------- #
def test_a_value_on_a_strict_threshold_has_not_passed_it():
    assert not NetPositive().check({"n": 10, "net_mean": 0.0})
    assert NetPositive().check({"n": 10, "net_mean": 1e-12})
    assert not BeatsRandom(alpha=0.05, margin=0.1).check({"n": 10, "excess_lo": 0.1, "q": 0.01})
    assert not BeatsRandom(alpha=0.05).check({"n": 10, "excess_lo": 0.2, "q": 0.05})
    assert BeatsRandom(alpha=0.05).check({"n": 10, "excess_lo": 0.2, "q": 0.049})
    assert not BeatsRandom().check({"n": 10, "excess_lo": 0.2, "q": np.nan})


def test_thresholds_written_as_at_least_pass_on_equality():
    assert MinTrades(100).check({"n": 100}) and not MinTrades(100).check({"n": 99})
    assert MinEffect(0.3).check({"excess_mean": 0.3}) and not MinEffect(0.3).check({"excess_mean": 0.2999})
    assert YearsStable(2 / 3, 2).check({"years_n": 3, "years_net_pos": 2})
    assert not YearsStable(2 / 3, 2).check({"years_n": 3, "years_net_pos": 1})
    assert not YearsStable(2 / 3, 2).check({"years_n": 1, "years_net_pos": 1})
    assert QuartersPositive(2 / 3).check({"q_n": 3, "q_pos": 2})
    assert QuarterMedian(0.02).check({"q_median": 0.02}) and not WorstQuarter(-0.25).check({"q_worst": -0.2501})


def test_apply_rules_names_every_rule_and_pass_is_their_conjunction():
    flags = apply_rules({"n": 150, "net_mean": -1.0}, [MinTrades(100), NetPositive()])
    assert flags == {"ok_min_trades": True, "ok_net_positive": False, "pass": False}
    assert MinTrades(7).describe() == {"rule": "MinTrades", "name": "min_trades", "n": 7}


# --------------------------------------------------------------------------- #
# baseline
# --------------------------------------------------------------------------- #
def test_the_baseline_equals_brute_force_over_every_eligible_bar():
    index = pd.date_range("2020-12-20", periods=60, freq="D")
    rng = np.random.default_rng(1)
    close = 100 + np.cumsum(rng.normal(0, 1, 60))

    def outcome(entries, hold, side):
        return side * (close[entries + hold - 1] - close[entries])

    table = random_entry_baseline(index, outcome, holds=[3], lo=2, hi=50)
    for _, row in table.iterrows():
        eligible = [e for e in range(2, 51) if e + 3 - 1 <= 50 and index[e].year == row["year"]]
        brute = np.mean([row["side"] * (close[e + 2] - close[e]) for e in eligible])
        assert row["expectation"] == pytest.approx(brute)
        assert row["bars"] == len(eligible)
    assert table["bars"].sum() == 2 * (50 - 2 - 3 + 2), "every eligible bar, both sides, counted once"


def test_a_trade_without_a_cell_keeps_its_place_in_n_but_not_in_the_advantage():
    index = pd.date_range("2021-01-01", periods=40, freq="h")
    table = random_entry_baseline(index, lambda e, h, s: np.full(len(e), 0.25 * s), holds=[2])
    trades = pd.DataFrame({
        "entry_time": pd.to_datetime(["2021-01-01 05:00", "2021-01-01 06:00", "2021-01-01 07:00"]),
        "exit_time": pd.to_datetime(["2021-01-01 07:00", "2021-01-01 08:00", "2021-01-01 10:00"]),
        "side": [1, -1, 1], "net": [1.0, 1.0, 1.0], "hold": [2, 2, 3],
    })
    with_rand = attach_random_baseline(trades, table)
    assert with_rand["rand"].tolist()[:2] == [0.25, -0.25] and np.isnan(with_rand["rand"].iloc[2])
    summary = trial_stats(with_rand, BlockBootstrap(months_between("2021-01-01", "2021-01-31"), B=20))
    assert summary["n"] == 3
    assert summary["excess_mean"] == pytest.approx((0.75 + 1.25) / 2)
    assert summary["net_mean"] == 1.0


def test_without_a_baseline_the_advantage_is_not_computed_not_assumed():
    trades = _trades().drop(columns=["rand"])
    summary = trial_stats(trades, BlockBootstrap(months_between(*SEGMENT), B=50))
    assert np.isnan(summary["excess_mean"]) and np.isnan(summary["p"])
    assert np.isfinite(summary["net_lo"])
    assert trial_stats(trades.iloc[:0], BlockBootstrap([0], B=5)) == {"n": 0}


def test_a_year_counts_as_a_year_only_with_enough_trades():
    trades = _trades(n=60, seed=4)
    summary = trial_stats(trades, BlockBootstrap(months_between(*SEGMENT), B=50), min_year_trades=10)
    years = summary["years"]
    assert summary["years_n"] == sum(1 for y in years.values() if y["n"] >= 10) < len(years) + 1
    strict = trial_stats(trades, BlockBootstrap(months_between(*SEGMENT), B=50), min_year_trades=10_000)
    assert strict["years_n"] == 0 and strict["years"] == years


# --------------------------------------------------------------------------- #
# quarters
# --------------------------------------------------------------------------- #
def test_a_quarter_without_trades_is_a_quarter_with_return_zero():
    curve = pd.Series([10_500.0, 11_000.0, 10_800.0],
                      index=pd.to_datetime(["2021-02-01", "2021-03-15", "2021-08-01"]))
    got = quarterly_summary(curve, initial=10_000)
    assert got["q_n"] == 3
    assert got["q_returns"][pd.Timestamp("2021-06-30")] == 0.0
    assert got["q_pos"] == 1
    assert got["q_returns"][pd.Timestamp("2021-09-30")] == pytest.approx(10_800 / 11_000 - 1)


def test_the_stretch_after_the_last_high_is_reported():
    days = pd.date_range("2021-01-01", periods=70, freq="D")
    balance = np.concatenate([np.linspace(10_000, 12_000, 30), np.linspace(11_900, 11_000, 40)])
    got = quarterly_summary(pd.Series(balance, index=days), initial=10_000)
    assert got["longest_underwater_days"] == 1, "while rising, every day is a new high"
    assert got["underwater_tail_days"] == 40
    assert got["max_dd"] == pytest.approx(11_000 / 12_000 - 1)


def test_top_k_share_is_the_share_of_profit_made_by_the_best_quarters():
    curve = pd.Series([10_100.0, 10_900.0, 10_800.0, 11_000.0],
                      index=pd.to_datetime(["2021-02-01", "2021-05-01", "2021-08-01", "2021-11-01"]))
    got = quarterly_summary(curve, initial=10_000, top_k=1)
    assert got["top_k_share"] == pytest.approx(800 / 1000)
    losing = quarterly_summary(pd.Series([9_000.0], index=pd.to_datetime(["2021-02-01"])), initial=10_000)
    assert np.isnan(losing["top_k_share"])


# --------------------------------------------------------------------------- #
# procedure
# --------------------------------------------------------------------------- #
def test_a_tie_on_back_goes_to_the_lower_run_and_defaults_must_match_exactly_one_row():
    runs = pd.DataFrame({
        "window": [1, 1, 1, 2, 2, 2],
        "pass": [1, 2, 3, 1, 2, 3],
        "a": [1, 2, 2, 1, 2, 3],
        "back": [5.0, 9.0, 9.0, 1.0, 2.0, 3.0],
        "forward": [10.0, 20.0, 30.0, -1.0, 4.0, 4.0],
    })
    result = evaluate_procedure(runs, {"a": 2})
    first, second = result.per_window.to_dict("records")
    assert first["chosen_pass"] == 2 and first["chosen"] == 20.0
    assert np.isnan(first["defaults"]), "two rows carry a=2 in window 1"
    assert second["defaults"] == 4.0
    assert second["percentile"] == pytest.approx(1 / 3), "strictly below: the equal forward does not count"
    assert result.paired.loc["chosen_vs_defaults", "n"] == 1 and np.isnan(result.paired.loc["chosen_vs_defaults", "t"])
    with pytest.raises(ValueError, match="missing column"):
        evaluate_procedure(runs, {"b": 1})


# --------------------------------------------------------------------------- #
# contract
# --------------------------------------------------------------------------- #
def test_the_contract_refuses_by_name_and_never_coerces():
    good = _trades(n=5)
    assert validate_trades(good) is good
    with pytest.raises(ValueError, match=r"missing required column\(s\) \['net'\]"):
        validate_trades(good.drop(columns=["net"]))
    with pytest.raises(ValueError, match="'side' must be \\+1"):
        validate_trades(good.assign(side=[1, -1, 0, 1, 1]))
    with pytest.raises(ValueError, match="exit_time before entry_time"):
        validate_trades(good.assign(exit_time=good["entry_time"] - pd.Timedelta("1h")))
    with pytest.raises(ValueError, match="'entry_time' must be datetime64"):
        validate_trades(good.assign(entry_time=good["entry_time"].astype(str)))
    with pytest.raises(ValueError, match="'hold' must be a non-negative integer"):
        validate_trades(good.assign(hold=good["hold"].astype(float)))
