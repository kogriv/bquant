"""Replay-causality oracle for swing `confirmation_index` (issue #110).

The contract: a swing declared available at bar ``t`` (``confirmation_index <= t``)
must be **identical** when the strategy is recomputed on the truncated raw series
``data[:t+1]`` — no repainting (pivot replacement/addition/removal) under extension.

Unlike the older `test_swing_global_calculation` tests (which monkeypatch a fixed
pivot list and only check the deviation-scan arithmetic), this oracle reruns the
**real detector** under raw-OHLC truncation — the only way to catch repainting.

Runs on the embedded ``tv_xauusd_1h`` sample (1000 bars — enough for the structural
property; the full-history 100k profile is characterisation, not needed for
correctness) and needs the real pandas-ta zigzag, so the module is skipped when
pandas-ta is unavailable.
"""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("pandas_ta") is None,
    reason="replay-causality oracle needs the real pandas-ta detector",
)

from bquant.data.samples import get_sample_data
from bquant.analysis.zones.strategies.swing import (
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy,
    ZigZagSwingStrategy,
)


@pytest.fixture(scope="module")
def sample():
    return get_sample_data("tv_xauusd_1h")


def _present(context, sp) -> bool:
    """Is a pivot identical to ``sp`` (index, type, price) in ``context``?"""
    return any(
        t.index == sp.index and t.swing_type == sp.swing_type
        and abs(t.price - sp.price) < 1e-6
        for t in context.swing_points
    )


def _repaint_violations(strategy, df) -> list:
    """Pivots absent at their own ``confirmation_index`` under raw truncation.

    For each full-history pivot that claims to be available at ``confirmation_index``,
    rerun the strategy on ``df[:confirmation_index+1]`` and check the pivot is there.
    A non-empty result means the map repaints — the availability claim is a lie.
    """
    full = strategy.calculate_global(df)
    violations = []
    for sp in full.swing_points:
        ci = sp.confirmation_index
        if ci is None or ci >= len(df):
            continue
        truncated = strategy.calculate_global(df.iloc[: ci + 1])
        if not _present(truncated, sp):
            violations.append((sp.index, sp.swing_type, round(sp.price, 2), ci))
    return violations


# -- the fix: ZigZag must be strictly replay-safe (issue #110) ----------------

def test_zigzag_confirmation_is_replay_safe(sample):
    """Every ZigZag swing is observable, unchanged, at its confirmation_index.

    Guards the #110 fix: backtest=True (non-repainting stream) + the detector
    warm-up floor. With the old backtest=False centred detector this fails on ~35%
    of pivots on this sample (and 73% on the downstream narrow_zone cohort).
    """
    violations = _repaint_violations(ZigZagSwingStrategy(legs=3, deviation=0.008), sample)
    assert violations == [], (
        f"{len(violations)} ZigZag pivots repaint under truncation "
        f"(first few: {violations[:5]})"
    )


def test_zigzag_replay_safe_across_configs(sample):
    """Replay-safety holds for other legs/deviation settings, not just one."""
    for legs, dev in [(2, 0.01), (5, 0.005)]:
        violations = _repaint_violations(ZigZagSwingStrategy(legs=legs, deviation=dev), sample)
        assert violations == [], f"legs={legs} dev={dev}: {len(violations)} repaint(s)"


# -- generic contract: the same guarantee on the other strategies (G14) -------

def test_find_peaks_replay_safe(sample):
    """Every find_peaks extremum is observable, unchanged, at its confirmation_index.

    Guards the G14 fix: scipy applies ``distance`` before ``prominence`` and
    greedily by height, so an extremum suppressed by a higher neighbour revives
    once that neighbour is itself suppressed from further right. Confirmation
    therefore waits for the whole suppression chain to settle, not merely for
    ``index + distance``.
    """
    violations = _repaint_violations(
        FindPeaksSwingStrategy(distance=3, prominence=0.5), sample)
    assert violations == [], (
        f"{len(violations)} find_peaks extrema repaint under truncation "
        f"(first few: {violations[:5]})"
    )


def test_find_peaks_replay_safe_across_configs(sample):
    """Replay-safety holds across distance/prominence settings."""
    for distance, prominence in [(2, 1.0), (5, 2.0), (10, 0.5)]:
        violations = _repaint_violations(
            FindPeaksSwingStrategy(distance=distance, prominence=prominence), sample)
        assert violations == [], (
            f"distance={distance} prominence={prominence}: {len(violations)} repaint(s)")


def test_pivot_points_replay_safe(sample):
    """Every pivot is observable, unchanged, at its confirmation_index.

    Guards the G14 fix: the N-bar pattern itself is local and exact, but a context
    is only emitted once two extrema exist, so the first pivot inherits the
    second's confirmation (as ZigZag does).
    """
    violations = _repaint_violations(
        PivotPointsSwingStrategy(left_bars=3, right_bars=3), sample)
    assert violations == [], (
        f"{len(violations)} pivots repaint under truncation "
        f"(first few: {violations[:5]})"
    )


def test_pivot_points_replay_safe_across_configs(sample):
    """Replay-safety holds for other left/right bar settings, including asymmetric."""
    for left, right in [(2, 2), (1, 1), (2, 5), (5, 2)]:
        violations = _repaint_violations(
            PivotPointsSwingStrategy(left_bars=left, right_bars=right), sample)
        assert violations == [], f"left={left} right={right}: {len(violations)} repaint(s)"


# -- adversarial direction: claimed-then-vanished ------------------------------
# The checks above verify that a full-history pivot is already there at its
# confirmation bar. The converse matters just as much to a live consumer: a pivot
# it SEES at time t (confirmation_index <= t) must not evaporate later.

def _vanish_violations(strategy, df, step=50) -> list:
    """Pivots a consumer could act on at bar ``t`` that are absent from full history."""
    full = strategy.calculate_global(df)
    violations = []
    for t in range(50, len(df), step):
        context = strategy.calculate_global(df.iloc[: t + 1])
        for sp in context.swing_points:
            if sp.confirmation_index is None or sp.confirmation_index > t:
                continue
            if not _present(full, sp):
                violations.append((t, sp.index, sp.swing_type))
    return violations


def test_confirmed_swings_do_not_vanish(sample):
    """A swing confirmed as of bar t survives into the full history."""
    for strategy in (
        ZigZagSwingStrategy(legs=3, deviation=0.008),
        FindPeaksSwingStrategy(distance=3, prominence=0.5),
        PivotPointsSwingStrategy(left_bars=3, right_bars=3),
    ):
        violations = _vanish_violations(strategy, sample)
        assert violations == [], (
            f"{type(strategy).__name__}: {len(violations)} confirmed swings vanish "
            f"later (first few: {violations[:5]})"
        )


# -- known limitation: auto-prominence (gap-inventory G15) --------------------
# With `prominence=None` (the find_peaks default) the threshold is derived from the
# observed price range, so it *grows* as bars arrive (1.27 -> 2.07 on this sample).
# An extremum clearing the early, smaller threshold can fail the later, larger one
# and disappear. No confirmation_index can repair that: the filter itself keeps
# moving. Fixing it means changing detection semantics (e.g. a frozen warm-up
# threshold), which is out of scope here — pinned so the limitation stays visible.

@pytest.mark.xfail(strict=True, reason="auto-prominence threshold is not truncation-stable — G15")
def test_auto_prominence_replay_safe(sample):
    assert _vanish_violations(
        FindPeaksSwingStrategy(distance=5, prominence=None), sample) == []
