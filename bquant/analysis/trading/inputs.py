"""Reading the inputs of the trade builders: the zone frame, the signal table, the bar length.

Shared by :mod:`.zone_trades` and :mod:`.exit_at`, so that both read zones and signals in
one way and refuse the same things.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

_ZONE_SIDES = {"bull": 1, "bear": -1}


def zones_frame(zones: Any, n: int, exit_column: Optional[str] = None) -> pd.DataFrame:
    if exit_column is not None and not isinstance(zones, pd.DataFrame):
        raise ValueError(f"ExitAt reads the exit bar from the zone frame's {exit_column!r} column; pass zones as a frame")
    if isinstance(zones, pd.DataFrame):
        needed = ["zone_id", "start_idx", "end_idx", "side"] + ([exit_column] if exit_column else [])
        missing = [c for c in needed if c not in zones.columns]
        if missing:
            raise ValueError(f"the zone frame has no {missing}; it needs {needed}")
        frame = zones[needed].copy()
        if exit_column:
            if not pd.api.types.is_integer_dtype(frame[exit_column]):
                raise ValueError(f"the exit column {exit_column!r} must be whole bar positions")
            frame = frame.rename(columns={exit_column: "exit_idx"})
    else:
        items = getattr(zones, "zones", zones)
        rows = []
        for zone in items:
            if zone.type not in _ZONE_SIDES:
                raise ValueError(
                    f"zone {zone.zone_id} is of type {zone.type!r}, which has no side; pass a zone frame "
                    "with an explicit side column instead"
                )
            rows.append({"zone_id": zone.zone_id, "start_idx": zone.start_idx, "end_idx": zone.end_idx,
                         "side": _ZONE_SIDES[zone.type]})
        frame = pd.DataFrame(rows, columns=["zone_id", "start_idx", "end_idx", "side"])
    for column in ("start_idx", "end_idx", "side"):
        if len(frame) and not pd.api.types.is_integer_dtype(frame[column]):
            raise ValueError(f"zone column {column!r} must be whole numbers")
    bad = frame[(frame["start_idx"] < 0) | (frame["end_idx"] >= n) | (frame["start_idx"] > frame["end_idx"])]
    if len(bad):
        raise ValueError(f"zone {bad['zone_id'].iloc[0]!r} lies outside the bars or starts after it ends")
    if not frame["side"].isin((1, -1)).all():
        raise ValueError("zone side must be +1 or -1")
    if frame["zone_id"].duplicated().any():
        raise ValueError("zone_id must be unique")
    return frame.reset_index(drop=True)


def signal_table(signals: Optional[pd.DataFrame]) -> Dict[Any, pd.DataFrame]:
    if signals is None:
        return {}
    missing = [c for c in ("zone_id", "k") if c not in signals.columns]
    if missing:
        raise ValueError(f"the signal frame has no {missing}; rows are keyed by zone_id and k")
    if signals.duplicated(["zone_id", "k"]).any():
        raise ValueError("the signal frame has more than one row for some (zone_id, k)")
    return {zid: rows.set_index("k").sort_index() for zid, rows in signals.groupby("zone_id", sort=False)}


def bar_length(index: pd.DatetimeIndex) -> pd.Timedelta:
    steps = pd.Series(index[1:] - index[:-1])
    steps = steps[steps > pd.Timedelta(0)]
    if steps.empty:
        raise ValueError("cannot tell the bar length from fewer than two distinct times; pass bar=")
    return steps.mode().iloc[0]
