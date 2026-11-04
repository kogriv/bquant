"""Гейты исследования воспроизводят фикстуру заказчика флаг в флаг.

Фикстура — `tests/fixtures/evaluation/gates/` (синтетическая; контракт — у запросившей
лаборатории). Рядом — то, что пакет решил сам: прежние правила читают прежние столбцы,
готовый `q` берётся только по явному `m_total=None`.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import (
    BeatsBase, Criterion, Holds, HoldsFolds, MinEffect, Placebo, YearsStable, apply_rules, default_criterion,
)

HERE = Path(__file__).resolve().parents[1] / "fixtures" / "evaluation" / "gates"
REF = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
ROWS = pd.read_csv(HERE / "rows.csv")
P = REF["params"]
RULES = [
    BeatsBase(P["q_alpha"]),
    Placebo(P["placebo_alpha"]),
    MinEffect(P["min_effect"], column="mean_diff"),
    YearsStable(P["years_share"], positive="years_pos"),
    Holds(threshold=P["min_effect"], alpha=P["holds_alpha"]),
]
FLAGS = ["ok_beats_base", "ok_placebo", "ok_min_effect", "ok_years_stable", "ok_holds", "pass"]
EXPECTED = pd.DataFrame(REF["rows"])


def test_the_fixture_is_the_one_it_says():
    assert (EXPECTED["variant"].tolist() == ROWS["variant"].tolist())
    assert set(ROWS["source"]) == {"synthetic", "crafted"}


def test_every_row_and_every_flag_reproduces_by_rule():
    got = pd.DataFrame([apply_rules(row, RULES) for row in ROWS.to_dict("records")])
    for flag in FLAGS:
        bad = ROWS["variant"][got[flag] != EXPECTED[flag]].tolist()
        assert not bad, (flag, bad)
    assert {flag: int(got[flag].sum()) for flag in FLAGS} == REF["counts"]


def test_the_criterion_keeps_the_given_q_when_told_to():
    out = Criterion(RULES).evaluate(ROWS, m_total=None)
    for flag in FLAGS:
        assert out[flag].tolist() == EXPECTED[flag].tolist(), flag
    pd.testing.assert_series_equal(out["q"], ROWS["q"])
    assert "m_total" not in out


def test_without_a_q_column_keeping_it_is_refused():
    with pytest.raises(ValueError, match="no q column"):
        Criterion(RULES).evaluate(ROWS.drop(columns="q"), m_total=None)


def test_with_m_total_the_q_is_recomputed_even_if_one_is_there():
    stale = ROWS.assign(q=0.0)
    out = Criterion(RULES).evaluate(stale, m_total=len(ROWS))
    assert (out["q"] != 0.0).any()
    assert out["m_total"].unique().tolist() == [len(ROWS)]


@pytest.mark.parametrize("case", REF["holds_folds"], ids=lambda c: str(c["signs"]))
def test_the_folds_hold_only_when_all_k_are_above_zero(case):
    assert HoldsFolds(case["k"]).check({"fold_signs": case["signs"]}) is case["ok_holds"]


def test_folds_that_are_not_a_sequence_do_not_hold():
    rule = HoldsFolds(2)
    for row in ({}, {"fold_signs": None}, {"fold_signs": "11"}, {"fold_signs": [1, float("nan")]}):
        assert rule.check(row) is False
    assert apply_rules({"fold_signs": [0.3, 0.1]}, [rule]) == {"ok_holds_folds": True, "pass": True}


def test_the_old_rules_still_read_the_old_columns():
    row = {"excess_mean": 0.2, "mean_diff": -1.0, "years_n": 3, "years_net_pos": 2, "years_pos": 0}
    assert MinEffect(0.1).check(row) is True
    assert YearsStable().check(row) is True
    assert MinEffect(0.1, column="mean_diff").check(row) is False
    assert YearsStable(positive="years_pos").check(row) is False
    assert default_criterion().rules[2] == YearsStable(2 / 3)


@pytest.mark.parametrize("row, ok", [
    ({"placebo_p": 0.04, "placebo_mean_diff": 9.0, "mean_diff": 1.0}, True),       # a finite p decides alone
    ({"placebo_p": 0.05, "placebo_mean_diff": 0.0, "mean_diff": 1.0}, False),
    ({"placebo_p": np.nan, "placebo_mean_diff": 0.49, "mean_diff": 1.0}, True),
    ({"placebo_p": None, "placebo_mean_diff": 0.5, "mean_diff": 1.0}, False),      # exactly half fails
    ({"placebo_mean_diff": np.nan, "mean_diff": 1.0}, False),
])
def test_the_placebo_reads_p_first_and_falls_back_to_half_the_effect(row, ok):
    assert Placebo().check(row) is ok


def test_the_new_rules_describe_themselves():
    assert BeatsBase().describe() == {"rule": "BeatsBase", "name": "beats_base", "alpha": 0.05}
    assert HoldsFolds(4).describe()["column"] == "fold_signs"
