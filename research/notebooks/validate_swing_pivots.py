"""Validate swing pivot extraction inside zone analysis pipeline.

This research helper script reproduces the swing-metric investigation from
``05_case_study_zone_consistency.py`` with additional instrumentation:

1. Runs the zone analysis pipeline with caching disabled to avoid stale
   metrics when experimenting with strategy parameters.
2. Retrieves the OHLC slice for a representative MACD bull zone and extracts
   the raw swing pivot points produced by the pandas-ta ZigZag indicator.
3. Verifies that the pivots are chronologically ordered and stay within the
   price range of the underlying zone data.
4. Compares default ZigZag parameters with a tuned configuration that yields a
   denser swing profile for the selected zone.

Usage
-----
python research/notebooks/validate_swing_pivots.py \
    --dataset tv_xauusd_1h \
    --legs 3 \
    --deviation 0.008

Optional flags allow selecting a concrete zone id, adjusting legs/deviation,
or skipping the default-parameter comparison.
"""

from __future__ import annotations

import argparse
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

# Ensure project root is importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bquant.core.logging_config import setup_logging, get_logger
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.strategies.swing.zigzag import ZigZagSwingStrategy
from bquant.indicators import LibraryManager

logger = get_logger(__name__)


@dataclass
class PivotExtractionResult:
    pivots: pd.Series
    pivot_frame: pd.DataFrame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect swing pivot points for a zone")
    parser.add_argument(
        "--dataset",
        default="tv_xauusd_1h",
        help="Sample dataset name registered in bquant.data.samples",
    )
    parser.add_argument(
        "--zone-id",
        type=int,
        default=None,
        help="If provided, inspect this exact zone id (must be a bull zone).",
    )
    parser.add_argument(
        "--legs",
        type=int,
        default=3,
        help="ZigZag 'legs' parameter for the tuned run (bars required to confirm a pivot)",
    )
    parser.add_argument(
        "--deviation",
        type=float,
        default=0.008,
        help="ZigZag deviation threshold for the tuned run (as decimal, e.g. 0.008 = 0.8%)",
    )
    parser.add_argument(
        "--skip-default",
        action="store_true",
        help="Skip comparison with default ZigZag parameters",
    )
    return parser.parse_args()


def load_dataset(name: str) -> pd.DataFrame:
    df = get_sample_data(name)
    if "time" in df.columns:
        df = df.set_index("time")
    return df


def run_pipeline(df: pd.DataFrame):
    return (
        analyze_zones(df)
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .with_strategies(swing="zigzag")
        .analyze(clustering=False)
        .build()
    )


def choose_zone(result, explicit_zone_id: Optional[int]) -> "ZoneInfo":  # type: ignore[name-defined]
    bull_zones = [zone for zone in result.zones if zone.type == "bull"]
    if not bull_zones:
        raise RuntimeError("Pipeline did not produce any bull zones")

    avg_duration = statistics.mean(zone.duration for zone in bull_zones)
    logger.info("Detected %d bull zones, average duration %.2f bars", len(bull_zones), avg_duration)

    if explicit_zone_id is not None:
        zone = next((z for z in bull_zones if z.zone_id == explicit_zone_id), None)
        if zone is None:
            raise ValueError(f"Bull zone with id={explicit_zone_id} not found")
        logger.info("Using explicit zone %s (duration=%d bars)", zone.zone_id, zone.duration)
        return zone

    long_zones = [zone for zone in bull_zones if zone.duration >= avg_duration]
    zone = max(long_zones, key=lambda z: z.duration)
    logger.info(
        "Selected longest bull zone above mean duration: id=%s, duration=%d bars",
        zone.zone_id,
        zone.duration,
    )
    return zone


def extract_pivots(zone_data: pd.DataFrame, legs: int, deviation: float) -> PivotExtractionResult:
    zigzag = LibraryManager.create_indicator("pandas_ta", "zigzag", legs=legs, deviation=deviation)
    result = zigzag.calculate(zone_data)
    if result.data.shape[1] < 2:
        return PivotExtractionResult(pd.Series(dtype=float), pd.DataFrame())

    pivot_series = result.data.iloc[:, 1].dropna()
    pivot_frame = zone_data.loc[pivot_series.index, ["open", "high", "low", "close"]].copy()
    pivot_frame.insert(0, "pivot_price", pivot_series.values)
    return PivotExtractionResult(pivot_series, pivot_frame)


def validate_pivots(pivots: pd.Series, zone_data: pd.DataFrame) -> None:
    if pivots.empty:
        logger.warning("No swing pivots detected with provided parameters")
        return

    if not pivots.index.is_monotonic_increasing:
        raise AssertionError("Pivot timestamps are not strictly increasing")

    zone_min = float(zone_data["low"].min())
    zone_max = float(zone_data["high"].max())
    within_range = pivots.between(zone_min, zone_max).all()
    if not within_range:
        raise AssertionError("Pivot prices fall outside the zone price range")

    logger.info(
        "Validated %d pivot points (range %.2f – %.2f) within zone price band %.2f – %.2f",
        len(pivots),
        float(pivots.min()),
        float(pivots.max()),
        zone_min,
        zone_max,
    )


def log_metrics(title: str, metrics) -> None:
    logger.info(
        "%s -> swings=%d, rallies=%d, drops=%d, avg_rally=%.3f%%, avg_drop=%.3f%%",
        title,
        metrics.num_swings,
        metrics.rally_count,
        metrics.drop_count,
        float(metrics.avg_rally_pct),
        float(metrics.avg_drop_pct),
    )


def main() -> None:
    args = parse_args()
    setup_logging(profile="research")

    df = load_dataset(args.dataset)
    logger.info("Loaded dataset '%s' with %d rows", args.dataset, len(df))

    analysis_result = run_pipeline(df)
    zone = choose_zone(analysis_result, args.zone_id)
    zone_data = zone.data[["open", "high", "low", "close"]]

    logger.info("Zone span: %s → %s", zone.start_time, zone.end_time)
    logger.info(
        "Zone price range %.3f – %.3f (close Δ %.3f%%)",
        float(zone_data["low"].min()),
        float(zone_data["high"].max()),
        (float(zone_data["close"].iloc[-1]) / float(zone_data["close"].iloc[0]) - 1) * 100,
    )

    if not args.skip_default:
        default_strategy = ZigZagSwingStrategy()
        default_metrics = default_strategy.calculate(zone_data)
        log_metrics("Default ZigZag (legs=10, deviation=5%)", default_metrics)
        default_pivots = extract_pivots(zone_data, legs=10, deviation=0.05)
        logger.info("Default pivot count: %d", len(default_pivots.pivots))

    tuned_strategy = ZigZagSwingStrategy(legs=args.legs, deviation=args.deviation)
    tuned_metrics = tuned_strategy.calculate(zone_data)
    log_metrics(
        f"Tuned ZigZag (legs={args.legs}, deviation={args.deviation:.3f})",
        tuned_metrics,
    )

    tuned_pivots = extract_pivots(zone_data, legs=args.legs, deviation=args.deviation)
    validate_pivots(tuned_pivots.pivots, zone_data)

    if tuned_pivots.pivot_frame.empty:
        logger.warning("No pivot frame to display; try relaxing deviation or legs")
        return

    logger.info("First/last pivot snapshot:\n%s", tuned_pivots.pivot_frame.head(3))
    logger.info("...\n%s", tuned_pivots.pivot_frame.tail(3))


if __name__ == "__main__":
    main()
