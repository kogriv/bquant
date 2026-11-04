"""What a round trip costs: the spread, the commission, and the swap over the nights held.

Everything is in **points of the symbol** (price = points × point); a positive number is
an expense. Dividing by ATR, or by anything else, is the caller's business.

Two pieces:

* :func:`rollover_nights` — how many swap nights a trade held, by the server calendar:
  a midnight ``m`` with ``entry < m <= exit`` is charged when the day it closes is a
  weekday (Monday … Friday); the midnight after ``triple_weekday`` counts three times,
  so a full week is seven nights, as in MetaTrader.
* :class:`CostModel` — the cost of one round trip given the spread of the entry bar,
  the side and the nights.

Bars from MetaTrader are bid prices: a buy opens at ask and a sell closes at ask, so a
round trip pays **one** spread. The spread recorded for a historical bar is what the
server stored for it (often the smallest of the bar), not an average — hence the floor
``min_spread_points`` and the ``"fixed"`` mode for a stress test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

import numpy as np
import pandas as pd

_DAY_NS = 86_400 * 10**9
_SPREAD_MODES = ("bar", "fixed")


def _check_triple_weekday(value: Any) -> int:
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool) or not 0 <= int(value) <= 4:
        raise ValueError(
            f"triple_weekday must be a weekday 0 (Monday) … 4 (Friday), got {value!r}: the nights "
            "after Saturday and Sunday are not charged, so a triple night there would never count"
        )
    return int(value)


def _wall_clock_ns(times: Any, name: str) -> np.ndarray:
    values = times if isinstance(times, (pd.Series, pd.Index)) else np.atleast_1d(times)
    index = pd.DatetimeIndex(pd.to_datetime(values))
    if index.tz is not None:
        index = index.tz_localize(None)        # keep the wall clock of the zone given: pass server time
    if index.hasnans:
        raise ValueError(f"{name} has missing times")
    return index.as_unit("ns").asi8


def rollover_nights(entry_time: Any, exit_time: Any, *, triple_weekday: int = 2) -> np.ndarray:
    """Swap nights between each entry and exit, as an integer array.

    ``entry_time`` and ``exit_time`` are paired times (scalars, arrays, Series or an
    index) on the **broker's server clock**. A time with a timezone is read by its own
    wall clock — convert it to the server zone first. The exit is the moment the
    position closes: the close of the last bar (its open time plus one bar) or the open
    of the next one.

    ``triple_weekday`` is the day whose closing midnight counts three times, 0 = Monday;
    most brokers use 2 (Wednesday, the night into Thursday). A symbol specification from
    MetaTrader numbers the day from Sunday = 0: ``triple_weekday = (swap_rollover3day - 1) % 7``
    — :meth:`CostModel.from_symbol_spec` does that.
    """
    triple = _check_triple_weekday(triple_weekday)
    entry = _wall_clock_ns(entry_time, "entry_time")
    exit_ = _wall_clock_ns(exit_time, "exit_time")
    if entry.shape != exit_.shape:
        raise ValueError(f"entry_time and exit_time differ in length: {entry.size} and {exit_.size}")
    if (exit_ < entry).any():
        first = int(np.flatnonzero(exit_ < entry)[0])
        raise ValueError(f"exit before entry at position {first}")
    # Midnights are counted by day number since 1970-01-01 (a Thursday). The midnight that
    # opens day D closes day D - 1, whose weekday (Monday = 0) is (D + 2) % 7.
    first_day = entry // _DAY_NS          # midnights strictly after entry start at first_day + 1
    last_day = exit_ // _DAY_NS           # ... and end at last_day (a midnight equal to exit counts)
    nights = np.zeros(entry.shape, dtype=np.int64)
    for closed in range(5):               # Monday … Friday
        residue = (closed - 2) % 7        # day numbers D with (D + 2) % 7 == closed, i.e. D % 7 == residue
        count = (last_day - residue) // 7 - (first_day - residue) // 7
        nights += count * (3 if closed == triple else 1)
    return nights


@dataclass(frozen=True)
class CostModel:
    """The cost of a round trip, in points.

    ``spread``: ``"bar"`` takes the spread of the entry bar (never below
    ``min_spread_points``; a missing value is 0), ``"fixed"`` takes
    ``fixed_spread_points``. ``commission_points`` is per round trip (entry and exit).
    ``swap_long_points`` / ``swap_short_points`` are per night with MetaTrader's sign —
    a negative swap is paid, so it **adds** to the cost; ``triple_weekday`` is the day
    whose night counts three times (0 = Monday).

    ``cost = spread + commission - swap(side) * nights``.
    """

    spread: str = "bar"
    fixed_spread_points: float = 0.0
    min_spread_points: float = 0.0
    commission_points: float = 0.0
    swap_long_points: float = 0.0
    swap_short_points: float = 0.0
    triple_weekday: int = 2

    def __post_init__(self) -> None:
        if self.spread not in _SPREAD_MODES:
            raise ValueError(f"spread must be one of {_SPREAD_MODES}, got {self.spread!r}")
        for name in ("fixed_spread_points", "min_spread_points", "commission_points",
                     "swap_long_points", "swap_short_points"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)) or not np.isfinite(value):
                raise ValueError(f"{name} must be a finite number, got {value!r}")
        _check_triple_weekday(self.triple_weekday)

    @property
    def uses_swap(self) -> bool:
        """Whether the model charges swap, and so needs the nights."""
        return bool(self.swap_long_points or self.swap_short_points)

    def round_trip(self, spread_points: Optional[Any], entry_idx: Any, side: Any,
                   nights: Optional[Any] = None) -> np.ndarray:
        """Cost of each round trip in points.

        ``spread_points`` is the spread of every bar (indexed by ``entry_idx``; it may be
        ``None`` in the ``"fixed"`` mode), ``entry_idx`` the entry bars, ``side`` +1 or -1
        per trade, ``nights`` the swap nights per trade (:func:`rollover_nights`) —
        required when the model charges swap, and ignored when it does not.
        """
        entry = np.atleast_1d(np.asarray(entry_idx))
        if not np.issubdtype(entry.dtype, np.integer):
            raise ValueError(f"entry_idx must be integer bar positions, got dtype {entry.dtype}")
        sides = np.broadcast_to(np.asarray(side), entry.shape)
        if not np.isin(sides, (1, -1)).all():
            raise ValueError("side must be +1 or -1 for every trade")
        if self.spread == "bar":
            if spread_points is None:
                raise ValueError("the 'bar' spread mode needs spread_points, the spread of every bar")
            bar = np.nan_to_num(np.asarray(spread_points, dtype=float)[entry], nan=0.0)
            spread = np.maximum(bar, self.min_spread_points)
        else:
            spread = np.full(entry.shape, float(self.fixed_spread_points))
        cost = spread + self.commission_points
        if self.uses_swap:
            if nights is None:
                raise ValueError(
                    "this model charges swap, so round_trip needs nights (see rollover_nights); "
                    "without them the swap would silently drop out of the cost"
                )
            held = np.broadcast_to(np.asarray(nights), entry.shape)
            if not np.issubdtype(held.dtype, np.integer) or (held < 0).any():
                raise ValueError("nights must be non-negative whole numbers")
            per_night = np.where(sides > 0, self.swap_long_points, self.swap_short_points)
            cost = cost - per_night * held
        return cost

    @classmethod
    def from_symbol_spec(cls, spec: Mapping[str, Any], **costs: Any) -> "CostModel":
        """A model whose swap comes from a MetaTrader symbol specification.

        ``spec`` needs ``swap_mode`` (only 1 — swap in points — is accepted),
        ``swap_long``, ``swap_short`` and ``swap_rollover3day`` (Sunday = 0). The other
        fields of the model (``spread``, ``fixed_spread_points``, ``min_spread_points``,
        ``commission_points``) come as keywords.
        """
        if spec.get("swap_mode") != 1:
            raise ValueError(
                f"swap_mode is {spec.get('swap_mode')!r}: only 1 (swap in points) can be read as points"
            )
        missing = [key for key in ("swap_long", "swap_short", "swap_rollover3day") if key not in spec]
        if missing:
            raise ValueError(f"the symbol specification has no {', '.join(missing)}")
        swap_fields = {"swap_long_points", "swap_short_points", "triple_weekday"} & set(costs)
        if swap_fields:
            raise ValueError(f"{sorted(swap_fields)} come from the specification, not as keywords")
        return cls(
            swap_long_points=float(spec["swap_long"]),
            swap_short_points=float(spec["swap_short"]),
            triple_weekday=(int(spec["swap_rollover3day"]) - 1) % 7,
            **costs,
        )
