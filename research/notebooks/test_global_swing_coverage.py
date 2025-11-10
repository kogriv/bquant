"""Utility helpers to compare swing coverage between per-zone and global modes."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones.pipeline import analyze_zones
from tests.fixtures import create_sample_ohlcv_data
from tests.fixtures.swing_mocks import (
    evenly_spaced_pivots,
    fake_zigzag_indicator_context,
)


def _build_zones_df(data: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "zone_id": [0, 1, 2],
            "type": ["bull", "bear", "bull"],
            "start_time": [data.index[5], data.index[35], data.index[65]],
            "end_time": [data.index[25], data.index[55], data.index[95]],
        }
    )


def _coverage(result) -> float:
    if not result.zones:
        return 0.0

    covered = 0
    for zone in result.zones:
        metadata = (zone.features or {}).get("metadata", {})
        metrics = metadata.get("swing_metrics", {})
        swings = metrics.get("rally_count", 0) + metrics.get("drop_count", 0)
        if swings > 0:
            covered += 1
    return covered / len(result.zones)


def compare_swing_coverage() -> Dict[str, float]:
    """Run the pipeline in both modes and report swing coverage improvement."""

    data = create_sample_ohlcv_data(110)
    data.index = pd.date_range("2024-10-01", periods=len(data), freq="H")
    zones_df = _build_zones_df(data)
    pivot_indices = [0, 30, 60, 90, len(data) - 1]
    pivot_timestamps = [data.index[i] for i in pivot_indices]

    with fake_zigzag_indicator_context(pivot_timestamps):
        global_result = (
            analyze_zones(data)
            .with_cache(enable=False)
            .with_strategies(swing="zigzag")
            .with_swing_scope("global")
            .detect_zones("preloaded", zones_data=zones_df, zone_types=["any"])
            .build()
        )

        per_zone_result = (
            analyze_zones(data)
            .with_cache(enable=False)
            .with_strategies(swing="zigzag")
            .with_swing_scope("per_zone")
            .detect_zones("preloaded", zones_data=zones_df, zone_types=["any"])
            .build()
        )

    global_coverage = _coverage(global_result)
    per_zone_coverage = _coverage(per_zone_result)
    improvement_pct = (global_coverage - per_zone_coverage) * 100

    return {
        "global": global_coverage,
        "per_zone": per_zone_coverage,
        "improvement_pct": improvement_pct,
    }


if __name__ == "__main__":  # pragma: no cover
    from pprint import pprint

    pprint(compare_swing_coverage())
