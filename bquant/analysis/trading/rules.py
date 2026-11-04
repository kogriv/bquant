"""Rules of a trade: where it enters, where it leaves, where it is stopped.

Every rule is a small frozen object; :func:`~bquant.analysis.trading.zone_trades` asks it
one question about one zone. The notation is the module's:

* ``s``, ``e`` — the first and last bar of the zone, ``d`` its side (+1 / -1);
* ``j`` — the **decision bar**: the bar on whose close the decision is taken. The
  outcome is measured in ``atr[j]``;
* the **window** of a trade is the bars ``j + 1 … x``, where ``x`` is the exit bar. The
  decision bar is not in it.

A rule that cannot produce its bar (the data end first) makes the trade *skipped* with a
named reason rather than shortened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Union

_SIDES = ("zone", "against_zone", "signal")


def _check_side(side: str) -> None:
    if side not in _SIDES:
        raise ValueError(f"side must be one of {_SIDES}, got {side!r}")


def _check_count(value: Any, name: str, minimum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be a whole number >= {minimum}, got {value!r}")


def _check_level(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
        raise ValueError(f"{name} must be a positive number, got {value!r}")


# --------------------------------------------------------------------------- entries


@dataclass(frozen=True)
class ZoneBarClose:
    """Enter at the close of the zone's bar of age ``k`` (``k = 0`` is its first bar).

    The decision bar is ``j = s + k``, the entry bar is ``j`` itself and the entry price
    ``close[j]``. A zone shorter than ``k + 1`` bars gives no trade
    (``zone_shorter_than_k``). ``side``: ``"zone"`` trades the zone's side,
    ``"against_zone"`` the opposite one, ``"signal"`` the sign of the signal column
    ``side_column`` at ``(zone, k)`` — zero means no trade (``no_side``).
    """

    k: int = 0
    side: str = "zone"
    side_column: str = "signal_side"

    def __post_init__(self) -> None:
        _check_count(self.k, "k", 0)
        _check_side(self.side)


@dataclass(frozen=True)
class NextOpen:
    """Decide at the close of the zone's first bar, enter at the open of the next one.

    The decision bar is ``j = s``, the entry bar ``j + 1`` and the entry price
    ``open[j + 1]``; the outcome is still in ``atr[j]``, the ATR known at the decision.
    For rules that do not come from zones, pass one "zone" per decision bar
    (``start_idx = end_idx = j``). ``side`` as in :class:`ZoneBarClose` (age 0).
    """

    side: str = "zone"
    side_column: str = "signal_side"

    def __post_init__(self) -> None:
        _check_side(self.side)

    @property
    def k(self) -> int:
        return 0


Entry = Union[ZoneBarClose, NextOpen]


# --------------------------------------------------------------------------- exits


@dataclass(frozen=True)
class ZoneChange:
    """Leave at the close of the first bar of the next zone, ``x = e + 1``."""

    name: str = field(default="zone_change", init=False)


@dataclass(frozen=True)
class Horizon:
    """Leave at the close of bar ``x = j + h``.

    With ``cap=ZoneChange()`` not later than the zone change: ``x = j + h`` while
    ``j + h < e + 1`` (reason ``horizon``), otherwise ``x = e + 1`` (reason
    ``zone_change``; exactly on the boundary too). Only the bar actually left at has to be
    inside the data. ``mode`` stays ``horizon`` either way.
    """

    h: int = 1
    cap: Optional["ZoneChange"] = None
    name: str = field(default="horizon", init=False)

    def __post_init__(self) -> None:
        _check_count(self.h, "h", 1)
        if self.cap is not None and not isinstance(self.cap, ZoneChange):
            raise ValueError(f"cap must be ZoneChange() or None, got {self.cap!r}")


Fallback = Union[ZoneChange, Horizon]


def _check_fallback(fallback: Any) -> None:
    if not isinstance(fallback, (ZoneChange, Horizon)):
        raise ValueError(
            "fallback must be ZoneChange() or Horizon(h): a rule with a fallback of its own "
            f"cannot stand in for one, got {fallback!r}"
        )


@dataclass(frozen=True)
class SignalThreshold:
    """Leave at the close of the first zone bar whose signal reaches ``thr``.

    The bar ``x = s + k'`` is the first age ``k' >= k_min`` and ``k' > k`` (strictly
    after the decision) that has a signal row, ``signal >= thr`` (a missing value does
    not reach it) and every ``require`` column equal to its value. Without such a bar the
    trade leaves by ``fallback``, and its reason is ``fallback``.
    """

    signal: str
    thr: float
    k_min: int = 1
    require: Mapping[str, Any] = field(default_factory=dict)
    fallback: Fallback = field(default_factory=ZoneChange)
    name: str = field(default="signal_threshold", init=False)

    def __post_init__(self) -> None:
        _check_count(self.k_min, "k_min", 0)
        _check_fallback(self.fallback)
        object.__setattr__(self, "require", dict(self.require))


@dataclass(frozen=True)
class TrailingAfterSignal:
    """From the signal bar on, leave when the close gives back ``s_atr`` from its best.

    The signal bar ``x_s`` is found as in :class:`SignalThreshold`; ``x_fb`` is the bar
    of ``fallback``. Over ``i = x_s … x_fb`` (the signal bar included) the path is
    ``d · (close[i] - entry_price)`` in ``atr[j]`` and the exit the first ``i`` where
    the best path so far minus the path reaches ``s_atr``. No signal, or no such
    pull-back before ``x_fb``, leaves at ``x_fb`` with the reason ``fallback``.
    """

    signal: str
    thr: float
    s_atr: float
    k_min: int = 1
    require: Mapping[str, Any] = field(default_factory=dict)
    fallback: Fallback = field(default_factory=ZoneChange)
    name: str = field(default="trailing_after_signal", init=False)

    def __post_init__(self) -> None:
        _check_count(self.k_min, "k_min", 0)
        _check_level(self.s_atr, "s_atr")
        _check_fallback(self.fallback)
        object.__setattr__(self, "require", dict(self.require))


@dataclass(frozen=True)
class TakeProfit:
    """Leave at a target ``level`` ATR away from the entry price, inside the bar.

    The level is ``level_atr``, or ``share_of_forecast`` times the signal column
    ``forecast`` at the decision ``(zone, k)``. ``target = entry_price + d · level ·
    atr[j]``; the exit is the first bar of ``j + 1 … x_fb`` whose high (long) or low
    (short) reaches it, at the target price. Not reached — ``fallback``.
    """

    level_atr: Optional[float] = None
    share_of_forecast: Optional[float] = None
    forecast: Optional[str] = None
    fallback: Fallback = field(default_factory=ZoneChange)
    name: str = field(default="take_profit", init=False)

    def __post_init__(self) -> None:
        by_level = self.level_atr is not None
        by_share = self.share_of_forecast is not None or self.forecast is not None
        if by_level == by_share:
            raise ValueError("TakeProfit takes either level_atr, or share_of_forecast with forecast")
        if by_level:
            _check_level(self.level_atr, "level_atr")
        else:
            _check_level(self.share_of_forecast, "share_of_forecast")
            if not isinstance(self.forecast, str):
                raise ValueError("share_of_forecast needs forecast, the signal column with the forecast in ATR")
        _check_fallback(self.fallback)


Exit = Union[ZoneChange, Horizon, SignalThreshold, TrailingAfterSignal, TakeProfit]


# --------------------------------------------------------------------------- stops


@dataclass(frozen=True)
class FixedAtrStop:
    """A stop ``value`` ATR (of the decision bar) against the entry price."""

    value: float

    def __post_init__(self) -> None:
        _check_level(self.value, "value")


@dataclass(frozen=True)
class ColumnStop:
    """A stop whose distance in ATR is the signal column ``column`` at the decision.

    An expression such as ``K * mae_prev1`` is computed by the caller into that column;
    the package does not evaluate strings.
    """

    column: str


Stop = Union[FixedAtrStop, ColumnStop]


def describe(rule: Any) -> Dict[str, Any]:
    """The rule as a plain dictionary, for a record of what was run."""
    if rule is None:
        return {}
    out: Dict[str, Any] = {"rule": type(rule).__name__}
    for key, value in vars(rule).items():
        out[key] = describe(value) if hasattr(value, "__dataclass_fields__") else value
    return out
