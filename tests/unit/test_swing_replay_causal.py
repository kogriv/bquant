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


# -- generic contract: other strategies (pre-existing residuals, tracked) -----
# find_peaks (scipy prominence-base lag) and pivot_points (amplitude filter at the
# warm-up edge) have small pre-existing replay-safety gaps that #110 did not touch.
# The oracle pins them so they are visible and cannot regress further; strict xfail
# flips to a failure once tightened, prompting removal of the marker.

@pytest.mark.xfail(strict=True, reason="find_peaks prominence-base lag — #110 generic follow-up")
def test_find_peaks_replay_safe(sample):
    assert _repaint_violations(
        FindPeaksSwingStrategy(distance=3, prominence=0.5), sample) == []


@pytest.mark.xfail(strict=True, reason="pivot_points warm-up-edge repaint — #110 generic follow-up")
def test_pivot_points_replay_safe(sample):
    assert _repaint_violations(
        PivotPointsSwingStrategy(left_bars=3, right_bars=3), sample) == []
