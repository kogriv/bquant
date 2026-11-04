"""Парная разность, контраст групп и плацебо воспроизводят фикстуру заказчика.

Фикстура — `tests/fixtures/evaluation/paired/` (синтетическая; контракт и генератор — у
запросившей лаборатории). Числа сходятся до 1e-9, счётчики и `placebo_p` — точно. Рядом —
то, что фикстура не задаёт числами: сопоставление по ключу и отказы.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import (
    PermuteColumn, PermuteFlags, SignFlip, contrast_stats, paired_stats, permutation_placebo,
)

HERE = Path(__file__).resolve().parents[1] / "fixtures" / "evaluation" / "paired"
REF = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
UNITS = pd.read_csv(HERE / "units.csv")
BOOT = np.arange(REF["boot_months"][0], REF["boot_months"][1] + 1)
TOL = REF["tolerance"]
CASES = [(s, k) for s in (1, 2, 3) for k in ("boot_share", "normal")]


def _close(a, b, what):
    if b is None or np.isnan(b):
        assert a is None or np.isnan(a), (what, a)
        return
    assert abs(a - b) <= TOL * max(1.0, abs(b)), (what, a, b)


def _compare(got, want):
    for key, expected in want.items():
        if key == "inputs":
            continue
        if key == "years":
            assert set(map(int, expected)) == set(got["years"]), "years"
            for year, row in expected.items():
                for field, value in row.items():
                    if field == "mean_diff":
                        _close(got["years"][int(year)][field], value, f"years.{year}.{field}")
                    else:
                        assert got["years"][int(year)][field] == value, f"years.{year}.{field}"
        elif key in ("mean_diff", "se", "p"):
            _close(got[key], expected, key)
        else:
            assert got[key] == expected, key


def _frames(units):
    variant = units[["unit_id", "month", "variant"]].rename(columns={"variant": "net"})
    base = units[["unit_id", "month", "base"]].rename(columns={"base": "net"})
    return variant, base


@pytest.mark.parametrize("seed, kind", CASES)
def test_the_paired_statistics_reproduce(seed, kind):
    variant, base = _frames(UNITS)
    got = paired_stats(variant, base, key="unit_id", boot_months=BOOT, B=REF["B"], seed=seed, p_kind=kind)
    _compare(got, REF["paired"][f"seed{seed}_{kind}"])
    assert (got["n_variant"], got["n_base"], got["p_kind"]) == (300, 300, kind)


@pytest.mark.parametrize("seed, kind", CASES)
def test_the_contrast_reproduces(seed, kind):
    got = contrast_stats(UNITS["variant"], UNITS["low"], UNITS["high"], month=UNITS["month"], boot_months=BOOT,
                         B=REF["B"], seed=seed, p_kind=kind)
    _compare(got, REF["contrast"][f"seed{seed}_{kind}"])


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_placebos_reproduce(seed):
    d = (UNITS["variant"] - UNITS["base"]).to_numpy()
    flip = permutation_placebo(float(d.mean()), SignFlip(d), n_perm=REF["n_perm"], seed=seed)
    want = REF["placebo"][f"paired_sign_flip_seed{seed}"]
    _close(flip["placebo_mean_diff"], want["placebo_mean_diff"], "sign_flip mean")
    assert (flip["placebo_p"], flip["n_perm"]) == (want["placebo_p"], want["n_perm"])

    v, low, high = UNITS["variant"].to_numpy(), UNITS["low"].to_numpy(), UNITS["high"].to_numpy()
    flags = permutation_placebo(float(v[low].mean() - v[high].mean()), PermuteFlags(v, low, high),
                                n_perm=REF["n_perm"], seed=seed)
    want = REF["placebo"][f"contrast_permute_flags_seed{seed}"]
    _close(flags["placebo_mean_diff"], want["placebo_mean_diff"], "permute_flags mean")
    assert flags["placebo_p"] == want["placebo_p"]


def test_a_constant_difference_has_no_p():
    edge = REF["edges"]["constant_diff"]
    months = UNITS["month"].to_numpy()[:50]
    variant = pd.DataFrame({"u": range(50), "month": months, "net": 0.3})
    base = pd.DataFrame({"u": range(50), "month": months, "net": 0.0})
    got = paired_stats(variant, base, key="u", boot_months=BOOT, B=REF["B"], seed=1)
    _compare(got, edge)
    assert got["se"] < 1e-12 and np.isnan(got["p"])


@pytest.mark.parametrize("name, flags", [
    ("contrast_empty_group", lambda: (UNITS["low"], np.zeros(len(UNITS), bool))),
    ("contrast_small_group", lambda: (np.r_[np.ones(9, bool), np.zeros(len(UNITS) - 9, bool)], UNITS["high"])),
])
def test_a_group_too_small_gives_nan(name, flags):
    a, b = flags()
    got = contrast_stats(UNITS["variant"], a, b, month=UNITS["month"], boot_months=BOOT, B=REF["B"], seed=1)
    _compare(got, REF["edges"][name])


def test_years_on_the_threshold_are_counted_and_below_it_are_not():
    edge = REF["edges"]["years_edge"]
    ym, yd = np.asarray(edge["inputs"]["month"]), np.asarray(edge["inputs"]["d"])
    variant = pd.DataFrame({"u": range(len(yd)), "month": ym, "net": yd})
    base = variant.assign(net=0.0)
    got = paired_stats(variant, base, key="u", boot_months=np.arange(2020 * 12, 2024 * 12), B=REF["B"], seed=1)
    _compare(got, edge)
    assert (got["years_n"], got["years_pos"]) == (2, 1)
    assert got["replicates_used"] < REF["B"]


@pytest.mark.parametrize("name, months, d", [
    ("zero_replicates", np.repeat(np.arange(2024 * 12, 2024 * 12 + 12), 4), np.tile([0.3, -0.3, 0.7, -0.7], 12)),
    ("zero_replicates_boundary", np.r_[np.repeat(np.arange(2024 * 12, 2024 * 12 + 11), 2), [2024 * 12 + 11]],
     np.r_[np.tile([0.4, -0.4], 11), [1.0]]),
])
def test_replicate_means_of_exactly_zero(name, months, d):
    variant = pd.DataFrame({"u": range(len(d)), "month": months, "net": d})
    got = paired_stats(variant, variant.assign(net=0.0), key="u", boot_months=np.arange(2024 * 12, 2024 * 12 + 12),
                       B=REF["B"], seed=1)
    _compare(got, REF["edges"][name])


def test_units_are_matched_by_key_and_the_unmatched_are_counted():
    variant, base = _frames(UNITS)
    dropped = base.sample(10, random_state=0)["unit_id"]
    got = paired_stats(variant, base[~base["unit_id"].isin(dropped)].iloc[::-1], key="unit_id", boot_months=BOOT, seed=1)
    kept = UNITS[~UNITS["unit_id"].isin(dropped)]
    same = paired_stats(*_frames(kept), key="unit_id", boot_months=BOOT, seed=1)
    assert (got["n_variant"], got["n_base"], got["n"]) == (300, 290, 290)
    assert got["mean_diff"] == same["mean_diff"] and got["se"] == same["se"] and got["p"] == same["p"]


def test_a_key_repeated_on_one_side_is_refused():
    variant, base = _frames(UNITS)
    with pytest.raises(ValueError, match="more than one unit"):
        paired_stats(pd.concat([variant, variant.head(1)]), base, key="unit_id", boot_months=BOOT)


@pytest.mark.parametrize("call, reason", [
    (lambda v, b: paired_stats(v, b, key="unit_id", boot_months=BOOT, p_kind="t"), "p_kind"),
    (lambda v, b: paired_stats(v, b, key="zone_id", boot_months=BOOT), "no \\['zone_id'\\]"),
    (lambda v, b: paired_stats(v, b, key="unit_id", boot_months=BOOT[:6]), "outside the bootstrap"),
    (lambda v, b: paired_stats(v, b, key="unit_id", boot_months=BOOT, min_year_units=0), "min_year_units"),
    (lambda v, b: contrast_stats([1.0, 2.0], [True], [False, True], month=[1, 1], boot_months=[1]), "one length"),
    (lambda v, b: permutation_placebo(0.0, lambda perm: 0.0), "n_units"),
])
def test_what_cannot_be_read_is_refused(call, reason):
    with pytest.raises(ValueError, match=reason):
        call(*_frames(UNITS))


def test_the_balanced_sign_flip_has_exactly_half_plus_signs():
    d = np.ones(7)
    seen = []
    permutation_placebo(1.0, lambda perm: seen.append(int((perm < 7 // 2).sum())) or 0.0, n_units=7, n_perm=20, seed=4)
    assert set(seen) == {3}
    assert SignFlip(d)(np.arange(7)) == pytest.approx((3 - 4) / 7)


def test_the_column_placebo_shuffles_one_column_and_leaves_the_frame():
    frame = pd.DataFrame({"signal": np.arange(10.0), "outcome": np.arange(10.0)})
    stat = PermuteColumn(frame, "signal", lambda f: float(np.corrcoef(f["signal"], f["outcome"])[0, 1]))
    out = permutation_placebo(1.0, stat, n_perm=50, seed=2)
    assert out["placebo_mean_diff"] < 0.5 and frame["signal"].tolist() == list(np.arange(10.0))
    with pytest.raises(ValueError, match="no column"):
        PermuteColumn(frame, "nope", lambda f: 0.0)


def test_a_replicate_mean_of_exactly_zero_counts_as_not_better():
    # continuous outcomes never give a replicate mean of exactly 0, so the fixture cannot
    # tell <= 0 from < 0; here two months sum to zero and a third is positive
    from bquant.analysis.evaluation import BlockBootstrap
    months = np.array([0, 0, 1, 1, 2])
    d = np.array([1.0, -1.0, 2.0, -2.0, 3.0])
    variant = pd.DataFrame({"u": range(5), "month": months, "net": d})
    base = variant.assign(net=0.0)
    got = paired_stats(variant, base, key="u", boot_months=[0, 1, 2], B=2000, seed=5)
    means = BlockBootstrap([0, 1, 2], 2000, 5).means(d, months)
    assert np.mean(means == 0) > 0.05                    # the case does reach the boundary
    assert got["p"] == np.mean(means <= 0)
