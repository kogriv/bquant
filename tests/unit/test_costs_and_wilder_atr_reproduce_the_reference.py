"""ATR Уайлдера, ночи ролловера и модель издержек воспроизводят фикстуру заказчика.

Фикстура — `tests/fixtures/evaluation/costs/` (контракт и генератор — у запросившей
лаборатории). ATR и издержки сходятся до 1e-9, ночи — точно. Рядом — отказы, которые
пакет добавил к контракту: молчаливая подмена в издержках не оставляет следа.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import CostModel, rollover_nights
from bquant.data import calculate_atr

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "evaluation"
REF = json.loads((FIXTURES / "costs" / "expected.json").read_text(encoding="utf-8"))
BARS = pd.read_csv(FIXTURES / "baseline" / "bars.csv", parse_dates=["time"]).set_index("time")
POINT = REF["point"]
BAR = pd.Timedelta(seconds=REF["bar_seconds"])
TOL = 1e-9


def _model(name):
    params = {k: v for k, v in REF["models"][name].items() if k != "name"}
    return CostModel(**params)


def _close(actual, expected):
    expected = np.array([np.nan if v is None else v for v in expected], dtype=float)
    actual = np.asarray(actual, dtype=float)
    assert np.array_equal(np.isnan(actual), np.isnan(expected)), "NaN не там, где null"
    ok = ~np.isnan(expected)
    scale = np.maximum(1.0, np.abs(expected[ok]))
    worst = np.max(np.abs(actual[ok] - expected[ok]) / scale)
    assert worst <= TOL, f"расхождение {worst:.3e}"


@pytest.mark.parametrize("period", REF["atr_periods"])
def test_wilder_atr_reproduces_every_bar(period):
    atr = calculate_atr(BARS, period=period, method="wilder")
    _close(atr.to_numpy(), REF["atr"][str(period)]["price"])
    _close(atr.to_numpy() / POINT, REF["atr"][str(period)]["points"])
    assert atr.index.equals(BARS.index)


def test_the_default_atr_is_the_rolling_mean_as_before():
    from bquant.data import calculate_true_range
    default = calculate_atr(BARS, period=14)
    pd.testing.assert_series_equal(default, calculate_true_range(BARS).rolling(14).mean())
    pd.testing.assert_series_equal(default, calculate_atr(BARS, period=14, method="sma"))
    assert not np.allclose(default.dropna(), calculate_atr(BARS, 14, method="wilder")[default.notna()]), \
        "Уайлдер не отличается от скользящего среднего — проверка ничего не различает"


def test_an_unknown_atr_method_is_refused():
    with pytest.raises(ValueError, match="wilder"):
        calculate_atr(BARS, period=14, method="ema")


def _exit_time(case):
    x = case["entry_idx"] + case["hold"] - 1 + case["mode"]
    return BARS.index[x] + (BAR if case["mode"] == 0 else pd.Timedelta(0))


@pytest.mark.parametrize("case", REF["cases"], ids=lambda c: f"e{c['entry_idx']}h{c['hold']}m{c['mode']}")
def test_every_case_reproduces_in_every_model(case):
    assert str(_exit_time(case)) == case["exit_time"]
    assert str(BARS.index[case["entry_idx"]]) == case["entry_time"]
    spread = BARS["spread"].to_numpy(float)
    assert spread[case["entry_idx"]] == case["spread_points_at_entry"]
    for name, expected in case["models"].items():
        model = _model(name)
        nights = rollover_nights(BARS.index[case["entry_idx"]], _exit_time(case), triple_weekday=model.triple_weekday)
        assert nights.tolist() == [expected["nights"]], name
        for side, key in ((1, "cost_long"), (-1, "cost_short")):
            cost = model.round_trip(spread, [case["entry_idx"]], [side], nights)
            assert cost.shape == (1,)
            assert abs(cost[0] - expected[key]) <= TOL * max(1.0, abs(expected[key])), (name, key, cost[0], expected[key])


def test_all_cases_at_once_match_case_by_case():
    entries = np.array([c["entry_idx"] for c in REF["cases"]])
    exits = pd.DatetimeIndex([_exit_time(c) for c in REF["cases"]])
    model = _model("fixed30_swap")
    nights = rollover_nights(BARS.index[entries], exits, triple_weekday=model.triple_weekday)
    assert nights.tolist() == [c["models"]["fixed30_swap"]["nights"] for c in REF["cases"]]
    sides = np.where(np.arange(len(entries)) % 2 == 0, 1, -1)
    cost = model.round_trip(BARS["spread"].to_numpy(float), entries, sides, nights)
    expected = [c["models"]["fixed30_swap"]["cost_long" if s > 0 else "cost_short"] for c, s in zip(REF["cases"], sides)]
    np.testing.assert_allclose(cost, expected, rtol=0, atol=TOL)


def test_a_week_is_seven_nights_from_any_weekday():
    start = pd.Timestamp("2022-01-03 10:00")            # a Monday
    for shift in range(7):
        entry = start + pd.Timedelta(days=shift)
        for triple in range(5):
            assert rollover_nights(entry, entry + pd.Timedelta(days=7), triple_weekday=triple).tolist() == [7]


def test_a_midnight_on_the_exit_counts_and_on_the_entry_does_not():
    tuesday = pd.Timestamp("2022-01-04")
    assert rollover_nights(tuesday, tuesday).tolist() == [0]
    assert rollover_nights(tuesday - pd.Timedelta(hours=1), tuesday).tolist() == [1]
    assert rollover_nights(tuesday, tuesday + pd.Timedelta(hours=23)).tolist() == [0]


def test_a_timezone_is_read_by_its_own_wall_clock():
    naive = rollover_nights(pd.Timestamp("2022-01-05 22:00"), pd.Timestamp("2022-01-06 02:00"))
    aware = rollover_nights(pd.Timestamp("2022-01-05 22:00", tz="Europe/Athens"),
                            pd.Timestamp("2022-01-06 02:00", tz="Europe/Athens"))
    assert naive.tolist() == aware.tolist() == [3]          # the Wednesday night counts three


@pytest.mark.parametrize("triple", [-1, 5, 6, 2.0, True, "2"])
def test_a_triple_night_on_a_weekend_or_not_a_weekday_is_refused(triple):
    with pytest.raises(ValueError, match="triple_weekday"):
        rollover_nights(pd.Timestamp("2022-01-03"), pd.Timestamp("2022-01-04"), triple_weekday=triple)
    with pytest.raises(ValueError, match="triple_weekday"):
        CostModel(triple_weekday=triple)


def test_an_exit_before_the_entry_and_unequal_lengths_are_refused():
    with pytest.raises(ValueError, match="exit before entry"):
        rollover_nights(pd.Timestamp("2022-01-04"), pd.Timestamp("2022-01-03"))
    with pytest.raises(ValueError, match="differ in length"):
        rollover_nights(BARS.index[:3], BARS.index[:2])


def test_a_swap_model_without_nights_is_refused_not_silently_swapless():
    model = _model("fixed30_swap")
    with pytest.raises(ValueError, match="nights"):
        model.round_trip(None, [5], [1])
    assert _model("bar_min15_comm7").round_trip(BARS["spread"].to_numpy(float), [5], [1]).tolist() == [22.0]


def test_a_side_other_than_plus_or_minus_one_is_refused():
    with pytest.raises(ValueError, match="side"):
        _model("bar").round_trip(BARS["spread"].to_numpy(float), [5], [0])


def test_a_missing_bar_spread_is_zero_then_floored():
    spread = np.array([12.0, np.nan, 20.0])
    assert CostModel().round_trip(spread, [0, 1, 2], [1, 1, -1]).tolist() == [12.0, 0.0, 20.0]
    assert CostModel(min_spread_points=15.0).round_trip(spread, [0, 1, 2], [1, 1, -1]).tolist() == [15.0, 15.0, 20.0]


def test_an_unknown_spread_mode_is_refused():
    with pytest.raises(ValueError, match="spread"):
        CostModel(spread="average")


def test_the_symbol_specification_gives_the_swap_and_the_triple_day():
    spec = {"swap_mode": 1, "swap_long": -61.34, "swap_short": 30.75, "swap_rollover3day": 5}
    model = CostModel.from_symbol_spec(spec, spread="bar")
    assert model == _model("bar_swap_triple_friday")
    assert CostModel.from_symbol_spec({**spec, "swap_rollover3day": 3}).triple_weekday == 2


@pytest.mark.parametrize("spec, reason", [
    ({"swap_mode": 2, "swap_long": -1.0, "swap_short": 1.0, "swap_rollover3day": 3}, "swap_mode"),
    ({"swap_long": -1.0, "swap_short": 1.0, "swap_rollover3day": 3}, "swap_mode"),
    ({"swap_mode": 1, "swap_long": -1.0, "swap_short": 1.0}, "swap_rollover3day"),
    ({"swap_mode": 1, "swap_long": -1.0, "swap_short": 1.0, "swap_rollover3day": 6}, "triple_weekday"),
])
def test_a_specification_that_cannot_be_read_as_points_is_refused(spec, reason):
    with pytest.raises(ValueError, match=reason):
        CostModel.from_symbol_spec(spec)
