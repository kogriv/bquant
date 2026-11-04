"""Сделки из зон воспроизводят фикстуру заказчика построчно.

Фикстура — `tests/fixtures/trading/zone_trades/` (контракт формул и генератор — у
запросившей лаборатории): 17 вариантов правил, 136 сделок, 34 пропуска. Времена, `hold`,
`nights`, `mode`, `exit_reason` и `stop_and_take_same_bar` сходятся точно, числа — до 1e-9.
Рядом — отказы, которых в фикстуре нет: недостающий сигнал, зона вне баров, тип зоны без
стороны.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import CostModel, validate_trades
from bquant.analysis.trading import (
    ColumnStop, FixedAtrStop, Horizon, NextOpen, SignalThreshold, TakeProfit, TrailingAfterSignal,
    ZoneBarClose, ZoneChange, zone_trades,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HERE = FIXTURES / "trading" / "zone_trades"
REF = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
BARS = pd.read_csv(FIXTURES / "evaluation" / "baseline" / "bars.csv", parse_dates=["time"]).set_index("time")
ZONES = pd.read_csv(HERE / "zones.csv")
SIGNALS = pd.read_csv(HERE / "signals.csv")
TRADES = pd.read_csv(HERE / "trades.csv", parse_dates=["decision_time", "entry_time", "exit_time"])
SKIPPED = pd.read_csv(HERE / "skipped.csv")
TOL = REF["tolerance"]
NUMBERS = {"entry_price": "entry_price", "exit_price": "exit_price", "atr_points": "atr_points",
           "gross_points": "gross_points", "cost_points": "cost_points", "net_points": "net_points",
           "gross_atr": "gross", "net_atr": "net", "mfe_atr": "mfe", "mae_atr": "mae"}
EXACT = ["zone_id", "k", "side", "decision_time", "entry_time", "exit_time", "hold", "mode", "exit_reason",
         "nights", "dur", "stop_and_take_same_bar"]


def _fallback(name):
    assert name == "zone_change", name
    return ZoneChange()


def _entry(spec):
    if spec["rule"] == "zone_bar_close":
        return ZoneBarClose(k=spec["k"], side=spec["side"])
    assert spec["rule"] == "bar_close" and spec["offset_open"] is True
    return NextOpen(side=spec["side"])


def _exit(spec):
    rule = spec["rule"]
    if rule == "zone_change":
        return ZoneChange()
    if rule == "horizon":
        return Horizon(spec["h"], cap=_fallback(spec["cap"]) if spec.get("cap") else None)
    if rule == "signal_threshold":
        return SignalThreshold(spec["signal"], spec["thr"], k_min=spec["k_min"], require=spec["require"],
                               fallback=_fallback(spec["fallback"]))
    if rule == "trailing_after_signal":
        return TrailingAfterSignal(spec["signal"], spec["thr"], spec["s_atr"], k_min=spec["k_min"],
                                   require=spec["require"], fallback=_fallback(spec["fallback"]))
    assert rule == "take_profit"
    if "level_atr" in spec:
        return TakeProfit(level_atr=spec["level_atr"], fallback=_fallback(spec["fallback"]))
    return TakeProfit(share_of_forecast=spec["share_of_forecast"], forecast=spec["forecast"],
                      fallback=_fallback(spec["fallback"]))


def _stop(spec):
    if spec is None:
        return None
    return FixedAtrStop(spec["value"]) if spec["kind"] == "fixed_atr" else ColumnStop(spec["column"])


def _costs(name):
    spec = REF["costs"][name]
    return None if spec is None else CostModel(**{k: v for k, v in spec.items() if k != "name"})


def _run(name):
    v = REF["variants"][name]
    return zone_trades(BARS, ZONES, point=REF["point"], entry=_entry(v["entry"]), exit=_exit(v["exit"]),
                       stop=_stop(v["stop"]), costs=_costs(v["costs"]), signals=SIGNALS, atr_period=REF["atr_period"])


@pytest.mark.parametrize("name", list(REF["variants"]))
def test_every_variant_reproduces_row_by_row(name):
    got = _run(name)
    want = TRADES[TRADES["variant"] == name].reset_index(drop=True)
    assert len(got.trades) == len(want), (len(got.trades), len(want))
    trades = got.trades.reset_index(drop=True)
    for column in EXACT:
        assert trades[column].tolist() == want[column].tolist(), column
    for theirs, ours in NUMBERS.items():
        expected = want[theirs].to_numpy(float)
        actual = trades[ours].to_numpy(float)
        worst = np.max(np.abs(actual - expected) / np.maximum(1.0, np.abs(expected)), initial=0.0)
        assert worst <= TOL, (ours, worst)
    expected_skips = SKIPPED[SKIPPED["variant"] == name][["zone_id", "reason"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(got.skipped.reset_index(drop=True), expected_skips, check_dtype=False)


def test_the_fixture_covers_what_the_contract_names():
    assert set(SKIPPED["reason"]) == {"atr_nan_at_decision_bar", "exit_beyond_data", "zone_shorter_than_k", "no_side"}
    assert set(TRADES["exit_reason"]) == {"zone_change", "horizon", "signal", "trail", "take", "fallback", "stop"}
    assert TRADES["stop_and_take_same_bar"].sum() >= 1
    assert TRADES.groupby("variant")["mode"].nunique().max() == 1
    assert TRADES.loc[TRADES["variant"] == "zone_k0_zone_change", "nights"].max() > 0      # nights without a cost model


def test_the_frame_is_a_trade_frame_for_evaluation():
    trades = _run("zone_k0_trail07_1_stop2").trades
    validate_trades(trades)
    assert set(trades["mode"]) == {"trailing_after_signal"}
    assert set(trades["exit_reason"]) <= {"trail", "fallback", "stop"}


def test_zones_from_the_pipeline_are_accepted_and_keep_their_side():
    from bquant.analysis.zones import analyze_zones
    from bquant.data.samples import get_sample_data

    result = (analyze_zones(get_sample_data("tv_xauusd_1h"))
              .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
              .detect_zones("zero_crossing", indicator_role="hist").analyze().build())
    bars = result.data
    got = zone_trades(bars, result, point=0.01)
    assert len(got.trades) + len(got.skipped) == len(result.zones)
    by_id = {z.zone_id: (1 if z.type == "bull" else -1) for z in result.zones}
    assert all(by_id[z] == s for z, s in zip(got.trades["zone_id"], got.trades["side"]))
    validate_trades(got.trades)


def _toy_bars(highs, lows, closes):
    index = pd.date_range("2022-01-03", periods=len(closes), freq="h")
    closes = np.asarray(closes, float)
    return pd.DataFrame({"open": closes, "high": highs, "low": lows, "close": closes, "spread": 0.0}, index=index)


def test_a_stop_wins_its_bar_over_a_take():
    # flat at 100 for the ATR warm-up, then one bar that touches both 100.3 and 99.7
    n = 30
    closes = np.full(n, 100.0)
    highs, lows = closes + 0.5, closes - 0.5
    highs[20], lows[20] = 101.0, 99.0
    bars = _toy_bars(highs, lows, closes)
    zones = pd.DataFrame({"zone_id": [0], "start_idx": [18], "end_idx": [25], "side": [1]})
    atr = np.full(n, 1.0)                                    # one ATR = 1.0 in price
    got = zone_trades(bars, zones, point=0.01, exit=TakeProfit(level_atr=0.3), stop=FixedAtrStop(0.3), atr=atr)
    row = got.trades.iloc[0]
    assert (row["exit_reason"], row["stop_and_take_same_bar"]) == ("stop", True)
    assert row["gross"] == pytest.approx(-0.3, abs=1e-12)


@pytest.mark.parametrize("make, reason", [
    (lambda: dict(stop=ColumnStop("stop_atr"), signals=SIGNALS.drop(SIGNALS.index[SIGNALS["zone_id"] == 1][0])), "signal row"),
    (lambda: dict(entry=ZoneBarClose(side="signal"), signals=SIGNALS.drop(columns="signal_side")), "signal_side"),
    (lambda: dict(exit=TakeProfit(share_of_forecast=0.5, forecast="range_forecast_atr"), signals=None), "signal row"),
])
def test_a_missing_signal_is_refused_by_name(make, reason):
    with pytest.raises(ValueError, match=reason):
        zone_trades(BARS, ZONES, point=REF["point"], **make())


@pytest.mark.parametrize("zones, reason", [
    (pd.DataFrame({"zone_id": [0], "start_idx": [470], "end_idx": [480], "side": [1]}), "outside"),
    (pd.DataFrame({"zone_id": [0], "start_idx": [30], "end_idx": [20], "side": [1]}), "starts after"),
    (pd.DataFrame({"zone_id": [0], "start_idx": [20], "end_idx": [30], "side": [0]}), "side"),
    (pd.DataFrame({"zone_id": [0, 0], "start_idx": [20, 40], "end_idx": [30, 50], "side": [1, 1]}), "unique"),
    (pd.DataFrame({"zone_id": [0], "start_idx": [20]}), "no \\["),
])
def test_a_zone_frame_that_does_not_fit_the_bars_is_refused(zones, reason):
    with pytest.raises(ValueError, match=reason):
        zone_trades(BARS, zones, point=REF["point"])


def test_a_zone_type_without_a_side_is_refused():
    class Zone:
        zone_id, type, start_idx, end_idx = 0, "oversold", 20, 30
    with pytest.raises(ValueError, match="no side"):
        zone_trades(BARS, [Zone()], point=REF["point"])


def test_a_bar_spread_model_needs_the_spread_column():
    with pytest.raises(ValueError, match="spread"):
        zone_trades(BARS.drop(columns="spread"), ZONES, point=REF["point"], costs=CostModel())


@pytest.mark.parametrize("bad", [
    lambda: SignalThreshold("p", 0.7, fallback=SignalThreshold("p", 0.5)),
    lambda: TakeProfit(),
    lambda: TakeProfit(level_atr=1.0, share_of_forecast=0.5, forecast="f"),
    lambda: TakeProfit(share_of_forecast=0.5),
    lambda: Horizon(0),
    lambda: Horizon(5, cap=Horizon(3)),
    lambda: ZoneBarClose(k=-1),
    lambda: ZoneBarClose(side="long"),
    lambda: FixedAtrStop(0),
])
def test_a_rule_that_cannot_be_read_is_refused(bad):
    with pytest.raises(ValueError):
        bad()


def test_a_string_is_not_a_rule():
    with pytest.raises(ValueError, match="exit must be"):
        zone_trades(BARS, ZONES, point=REF["point"], exit="zone_change")
    with pytest.raises(ValueError, match="stop must be"):
        zone_trades(BARS, ZONES, point=REF["point"], stop="K * mae_prev1")


def _flat_zone_case(closes, start, end):
    n = len(closes)
    closes = np.asarray(closes, float)
    bars = _toy_bars(closes + 0.05, closes - 0.05, closes)
    zones = pd.DataFrame({"zone_id": [0], "start_idx": [start], "end_idx": [end], "side": [1]})
    return bars, zones, np.full(n, 1.0)


def test_a_signal_on_the_decision_bar_itself_does_not_close_the_trade():
    # the fixture enters at k = 0 with k_min = 1, so k' > k never binds there; here it does
    bars, zones, atr = _flat_zone_case(np.full(40, 100.0), 10, 30)
    signals = pd.DataFrame({"zone_id": 0, "k": range(21), "p": [0.0] * 21})
    signals.loc[signals["k"].isin([2, 5]), "p"] = 0.9           # a signal at the entry age and a later one
    got = zone_trades(bars, zones, point=0.01, entry=ZoneBarClose(k=2), exit=SignalThreshold("p", 0.7),
                      signals=signals, atr=atr)
    row = got.trades.iloc[0]
    assert (row["exit_reason"], row["hold"]) == ("signal", 3)    # bar s + 5, three bars after the decision s + 2


def test_the_trailing_path_starts_at_the_signal_bar_itself():
    # the fixture never pulls back from a best made on the signal bar; here the best is that bar
    closes = np.full(40, 100.0)
    closes[15] = 101.0                                            # the signal bar, the best close
    closes[16:30] = 100.5                                         # 0.5 below it, then flat
    bars, zones, atr = _flat_zone_case(closes, 10, 30)
    signals = pd.DataFrame({"zone_id": 0, "k": range(21), "p": [0.0] * 21})
    signals.loc[signals["k"] == 5, "p"] = 0.9                    # bar s + 5 = 15
    got = zone_trades(bars, zones, point=0.01, exit=TrailingAfterSignal("p", 0.7, s_atr=0.4),
                      signals=signals, atr=atr)
    row = got.trades.iloc[0]
    assert (row["exit_reason"], row["exit_time"]) == ("trail", bars.index[16])


def test_a_capped_horizon_without_the_cap_is_the_old_horizon():
    plain = zone_trades(BARS, ZONES, point=REF["point"], exit=Horizon(6)).trades
    for name in ("zone_k2_horizon6",):
        assert REF["variants"][name]["exit"] == {"rule": "horizon", "h": 6}
    capped = zone_trades(BARS, ZONES, point=REF["point"], exit=Horizon(6, cap=ZoneChange())).trades
    longer = capped["hold"] < plain["hold"]
    assert (capped.loc[~longer].drop(columns="exit_reason").equals(plain.loc[~longer].drop(columns="exit_reason")))
    assert set(capped.loc[longer, "exit_reason"]) <= {"zone_change"}


def test_a_capped_horizon_serves_as_a_fallback():
    got = zone_trades(BARS, ZONES, point=REF["point"], exit=TakeProfit(level_atr=50.0, fallback=Horizon(5, cap=ZoneChange())))
    assert set(got.trades["exit_reason"]) == {"fallback"} and set(got.trades["mode"]) == {"take_profit"}
