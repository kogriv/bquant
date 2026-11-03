"""Случайный базис различает способ выхода (режим выхода, по контракту лаборатории стратегий).

Сделка, выходящая на закрытии бара ``e+H−1``, и сделка, выходящая на открытии бара
``e+H``, держат одно и то же ``H`` баров, но им нужен разный последний бар и у них
разные исходы. Режим меняет две вещи, которые в функцию исхода не спрятать: верхнюю
границу допустимых входов и ключ клетки. Фикстура ``tests/fixtures/evaluation/baseline/``
— синтетика лаборатории (сид 20261103, 480 баров H1 через границу года, с выходными);
ожидаемые значения посчитаны её эталонной реализацией и сверены прямым перебором.

Функция исхода — ATR Уайлдера, ночи свопа, издержки — живёт здесь, как у вызывающего:
пакет решает только, какие бары допустимы и как ключевать клетку.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.evaluation import attach_random_baseline, random_entry_baseline

HERE = Path(__file__).resolve().parents[1] / "fixtures" / "evaluation" / "baseline"
EXPECTED = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
DAY_NS = 86_400 * 10**9
BAR_NS = 3_600 * 10**9
MODES = {0: 0, 1: 1}


def _bars() -> pd.DataFrame:
    frame = pd.read_csv(HERE / "bars.csv", parse_dates=["time"]).set_index("time")
    assert len(frame) == EXPECTED["bars"]
    return frame


def _wilder_atr(frame: pd.DataFrame, period: int) -> np.ndarray:
    h, l, c = (frame[k].to_numpy() for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    atr = np.full(len(tr), np.nan)
    atr[period - 1] = tr[:period].mean()
    for i in range(period, len(tr)):
        atr[i] = atr[i - 1] + (tr[i] - atr[i - 1]) / period
    return atr


def _rollovers(entry_ns: np.ndarray, exit_ns: np.ndarray, triple_weekday: int) -> np.ndarray:
    """Ночи свопа: полночь m, entry < m <= exit, после пн–пт; после triple_weekday — за три."""
    a, b = entry_ns // DAY_NS, exit_ns // DAY_NS
    total = np.zeros(np.shape(a), dtype=np.int64)
    for w in range(5):
        r = (w + 1 - 3) % 7
        total += ((b - r) // 7 - (a - r) // 7) * (3 if w == triple_weekday else 1)
    return total


def _outcome_for(frame: pd.DataFrame):
    cost = EXPECTED["cost"]
    point = EXPECTED["point"]
    o, c = frame["open"].to_numpy(), frame["close"].to_numpy()
    spread = frame["spread"].to_numpy()
    t_ns = frame.index.as_unit("ns").asi8
    atr = _wilder_atr(frame, EXPECTED["atr_period"]) / point

    def outcome(entries, hold, side, mode):
        # Выход за концом данных — NaN, а не IndexError: тогда пакет, взявший лишний бар,
        # краснеет на сверке клеток отрезков B и C, а не падением самого теста.
        x = entries + hold - 1 + mode
        beyond = x >= len(o)
        x = np.minimum(x, len(o) - 1)
        exit_price = c[x] if mode == 0 else o[x]
        gross = side * (exit_price - o[entries]) / point
        exit_ns = t_ns[x] + (BAR_NS if mode == 0 else 0)
        nights = _rollovers(t_ns[entries], exit_ns, cost["triple_weekday"])
        swap = cost["swap_long_points"] if side > 0 else cost["swap_short_points"]
        paid = np.maximum(spread[entries], cost["min_spread_points"]) + cost["commission_points"] - swap * nights
        return np.where(beyond, np.nan, (gross - paid) / atr[entries - 1])

    return outcome


@pytest.fixture(scope="module")
def built():
    frame = _bars()
    outcome = _outcome_for(frame)
    out = {}
    for name, seg in EXPECTED["segments"].items():
        lo = max(seg["lo"], EXPECTED["first_valid"])
        kwargs = dict(holds=EXPECTED["holds"], modes=MODES, lo=lo, hi=seg["hi"])
        out[name] = (
            random_entry_baseline(frame.index, outcome, **kwargs),
            random_entry_baseline(frame.index, outcome, by_hour=True, **kwargs),
        )
    return frame, out


def _rows(table: pd.DataFrame, by_hour: bool) -> dict:
    keys = ["year", *(["hour"] if by_hour else []), "side", "hold", "mode"]
    return {tuple(int(v) for v in row[keys]): (row["expectation"], int(row["bars"]))
            for _, row in table.iterrows()}


@pytest.mark.parametrize("segment", sorted(EXPECTED["segments"]))
@pytest.mark.parametrize("by_hour", [False, True], ids=["year", "year_hour"])
def test_every_cell_of_the_reference_reproduces(built, segment, by_hour):
    _, out = built
    table = out[segment][1 if by_hour else 0]
    seg = EXPECTED["segments"][segment]
    expected_rows = seg["table_hour" if by_hour else "table"]
    keys = ["year", *(["hour"] if by_hour else []), "side", "hold", "mode"]
    want = {tuple(int(r[k]) for k in keys): (r["expectation"], r["bars"]) for r in expected_rows}
    got = _rows(table, by_hour)
    assert set(got) == set(want), (
        f"{segment}: клетки не совпали — лишние {sorted(set(got) - set(want))[:5]}, "
        f"недостающие {sorted(set(want) - set(got))[:5]}"
    )
    for key, (value, bars) in want.items():
        assert got[key][1] == bars, f"{segment} {key}: bars {got[key][1]} вместо {bars}"
        assert math.isclose(got[key][0], value, rel_tol=1e-9, abs_tol=1e-12), (segment, key, got[key][0], value)


@pytest.mark.parametrize("segment", sorted(EXPECTED["segments"]))
def test_the_trades_get_the_reference_baseline(built, segment):
    frame, out = built
    table, table_hour = out[segment]
    rows = EXPECTED["segments"][segment]["trades"]
    entry = pd.to_datetime([r["entry_time"] for r in rows])
    trades = pd.DataFrame({
        "entry_time": entry,
        "exit_time": entry + pd.to_timedelta([r["hold"] for r in rows], "h"),
        "side": [r["side"] for r in rows],
        "net": 0.0,
        "hold": np.array([r["hold"] for r in rows], dtype="int64"),
        "mode": [r["mode"] for r in rows],
    })
    for column, got_table, by_hour in (("rand", table, False), ("rand_hour", table_hour, True)):
        got = attach_random_baseline(trades, got_table, by_hour=by_hour)["rand"].to_numpy()
        for i, r in enumerate(rows):
            want = r[column]
            if want is None:
                assert np.isnan(got[i]), f"{segment} сделка {i}: клетки нет, а {column} = {got[i]}"
            else:
                assert math.isclose(got[i], want, rel_tol=1e-9, abs_tol=1e-12), (segment, i, column, got[i], want)
    assert any(r["rand_hour"] is None for r in EXPECTED["segments"]["C"]["trades"]), "фикстура потеряла пустую клетку"


def test_the_tail_moves_the_last_eligible_entry(built):
    """Окну режима с хвостом 1 нужен лишний бар: на хвостовом отрезке у него меньше входов."""
    _, out = built
    table = out["C"][0]
    counts = table.groupby(["hold", "mode"])["bars"].sum() / 2   # две стороны
    for hold in EXPECTED["holds"]:
        if (hold, 0) in counts.index and (hold, 1) in counts.index:
            assert counts[(hold, 1)] == counts[(hold, 0)] - 1, counts


def test_without_modes_the_table_is_as_before(built):
    frame, _ = built
    outcome = _outcome_for(frame)
    plain = random_entry_baseline(frame.index, lambda e, h, s: outcome(e, h, s, 0), holds=[2, 3], lo=3)
    assert list(plain.columns) == ["year", "side", "hold", "expectation", "bars"]
    moded = random_entry_baseline(frame.index, outcome, holds=[2, 3], modes={0: 0}, lo=3)
    pd.testing.assert_frame_equal(plain, moded.drop(columns="mode"))


def test_a_table_with_modes_refuses_trades_without_a_mode(built):
    """Молчаливый «первый режим» подставил бы сделке с выходом на открытии чужое ожидание."""
    _, out = built
    table = out["A"][0]
    trades = pd.DataFrame({
        "entry_time": pd.to_datetime(["2021-12-23 16:00"]), "exit_time": pd.to_datetime(["2021-12-23 18:00"]),
        "side": [1], "net": [0.0], "hold": np.array([2], dtype="int64"),
    })
    with pytest.raises(ValueError, match="keyed by exit mode.*no 'mode' column"):
        attach_random_baseline(trades, table)


@pytest.mark.parametrize("tail", [-1, 0.5, True, "1"])
def test_a_tail_must_be_a_whole_number_of_bars(built, tail):
    frame, _ = built
    with pytest.raises(ValueError, match="tail of mode"):
        random_entry_baseline(frame.index, _outcome_for(frame), holds=[2], modes={1: tail}, lo=3)
