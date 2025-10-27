#!/usr/bin/env python3
"""Strategy Pattern usage demonstration - Universal Pipeline v2.1."""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pandas as pd

# Добавляем путь к проекту, чтобы пример можно было запускать из репозитория
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("PANDAS_TA_SUPPRESS_WARNINGS", "1")
os.environ.setdefault("PANDAS_TA_SUPPRESS_IMPORT_WARNINGS", "1")
os.environ.setdefault("PANDAS_TA_VERBOSE", "0")
os.environ.setdefault("PANDAS_TA_SILENT", "1")

from bquant.core.logging_config import setup_logging

setup_logging(
    console_level="CRITICAL",
    file_level="ERROR",
    log_to_file=False,
    use_colors=False,
    reset_loggers=True,
    profile="critical",
)

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones


def prepare_sample_data(dataset: str = "mt_xauusd_m15") -> pd.DataFrame:
    """Загружает и подготавливает данные для демонстрации стратегий."""

    df = get_sample_data(dataset)

    if "time" in df.columns:
        index = pd.to_datetime(df["time"], utc=True).dt.tz_convert(None)
        df = df.set_index(index)
        df.index.name = "time"

    # Удаляем столбцы без практической ценности для демо
    if "spread" in df.columns:
        df = df.drop(columns=["spread"])

    # Готовим прокси для гипотез и волатильности
    df["price_return"] = df["close"].pct_change().fillna(0)
    df["abs_price_return"] = df["price_return"].abs()

    if "volume" not in df.columns:
        df["volume"] = 0.0
    else:
        df["volume"] = df["volume"].fillna(method="ffill").fillna(0)

    return df


def main() -> None:
    print("=" * 60)
    print("BQuant Strategy Pattern Demo - Universal Pipeline v2.1")
    print("=" * 60)

    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    # Load sample data
    print("\n1. Loading data...")
    data = prepare_sample_data()
    print(f"   Loaded {len(data)} bars of XAUUSD M15 data")
    if isinstance(data.index, pd.DatetimeIndex) and not data.empty:
        print(f"   Period: {data.index[0]} -> {data.index[-1]}")

    # Test Universal Pipeline with different indicators
    print("\n2. Testing Universal Pipeline with multiple indicators...")

    indicators_to_test = [
        {
            "source": "custom",
            "name": "macd",
            "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "detection": {"strategy": "zero_crossing", "indicator_col": "macd_hist"},
        },
        {
            "source": "custom",
            "name": "rsi",
            "params": {"period": 14},
            "detection": {
                "strategy": "threshold",
                "indicator_col": "rsi_14",
                "upper_threshold": 60,
                "lower_threshold": 40,
                "require_cross": False,
            },
        },
    ]

    for indicator in indicators_to_test:
        name = indicator["name"]
        print(f"\n   === Testing {name.upper()} with Universal Strategies ===")

        detection_cfg = dict(indicator["detection"])
        detection_strategy = detection_cfg.pop("strategy")

        result = (
            analyze_zones(data)
            .with_indicator(indicator["source"], indicator["name"], **indicator["params"])
            .detect_zones(detection_strategy, **detection_cfg)
            .with_strategies(
                swing="find_peaks",      # Работает с ЛЮБЫМ индикатором
                divergence="classic",    # Работает с ЛЮБЫМ индикатором
                volume="standard",       # Работает с ЛЮБЫМ индикатором
                volatility="combined",   # Работает с ЛЮБЫМ индикатором
            )
            .analyze(clustering=False)
            .build()
        )

        print(f"   Detected {len(result.zones)} zones using {name} indicator")
        if result.zones:
            first_zone = result.zones[0]
            if first_zone.features:
                print(f"   Strategy context: {first_zone.features.get('indicator_name', 'unknown')}")
                print(f"   Zone type: {first_zone.type}")
                print(f"   Duration: {first_zone.duration} bars")

    # Focus on MACD for detailed strategy comparison
    print("\n3. Detailed strategy comparison with MACD...")

    result_macd = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='find_peaks')
        .analyze(clustering=False)
        .build()
    )

    print(f"   Found {len(result_macd.zones)} MACD zones")
    if not result_macd.zones:
        print("   No zones found, exiting.")
        return

    # Compare swing strategies on first zone
    print("\n4. Comparing swing strategies on first zone...")
    zone = next(
        (
            z
            for z in result_macd.zones
            if (z.features or {}).get('macd_amplitude') or (z.features or {}).get('num_peaks')
        ),
        result_macd.zones[0],
    )
    print(f"   Zone ID: {zone.zone_id}")
    print(f"   Type: {zone.type}")
    print(f"   Duration: {zone.duration} bars")

    strategies = ['zigzag', 'find_peaks', 'pivot_points']

    print("\n   Strategy comparison:")
    print("   " + "-" * 55)
    print(f"   {'Strategy':<15} {'Swings':<8} {'Avg Rally':<12} {'Avg Drop':<12}")
    print("   " + "-" * 55)

    def extract_matching_zone(zones, reference):
        for candidate in zones:
            if candidate.zone_id == reference.zone_id:
                return candidate
        for candidate in zones:
            if candidate.start_idx == reference.start_idx and candidate.end_idx == reference.end_idx:
                return candidate
        return next((z for z in zones if z.features), None)

    def summarize_zone(target_zone):
        if target_zone is None:
            return None, None, None

        features = target_zone.features or {}

        def first_available(keys, default=None):
            for key in keys:
                value = features.get(key)
                if value not in (None, 0):
                    return value
            return default

        swings = features.get('num_swings')
        if swings is None:
            peaks = features.get('num_peaks')
            troughs = features.get('num_troughs')
            if peaks is not None or troughs is not None:
                swings = (peaks or 0) + (troughs or 0)

        avg_rally = first_available(['avg_rally_pct', 'avg_swing_up_pct', 'average_rally_pct'])
        avg_drop = first_available(['avg_drop_pct', 'avg_swing_down_pct', 'average_drop_pct'])

        if (swings in (None, 0) or avg_rally in (None, 0) or avg_drop in (None, 0)) and hasattr(target_zone, 'data'):
            price_changes = target_zone.data['close'].pct_change().dropna()
            if swings in (None, 0):
                swings = max(len(price_changes), 0)
            if avg_rally in (None, 0) and not price_changes.empty:
                positives = price_changes[price_changes > 0]
                negatives = price_changes[price_changes < 0]
                avg_rally = positives.mean() if not positives.empty else 0.0
                avg_drop = negatives.mean() if not negatives.empty else 0.0

        return swings if swings is not None else 0, avg_rally or 0.0, avg_drop or 0.0

    strategy_results = {}
    for strat in strategies:
        result_strategy = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing=strat)
            .analyze(clustering=False)
            .build()
        )
        strategy_results[strat] = result_strategy

        strategy_zone = extract_matching_zone(result_strategy.zones, zone)

        swings, avg_rally, avg_drop = summarize_zone(strategy_zone)

        if strategy_zone:
            print(f"   {strat:<15} {swings:<8} {avg_rally:>10.2%}  {avg_drop:>10.2%}")
        else:
            print(f"   {strat:<15} {'N/A':<8} {'N/A':>10}  {'N/A':>10}")

    print("   " + "-" * 55)

    # Test all strategies on multiple zones
    print("\n5. Testing all strategies on first 5 zones...")

    strategy_stats = {name: {'total_swings': 0, 'zones': 0} for name in strategies}

    for zone in result_macd.zones[:5]:
        for strat, result_strategy in strategy_results.items():
            strategy_zone = extract_matching_zone(result_strategy.zones, zone)

            if strategy_zone:
                swings, _, _ = summarize_zone(strategy_zone)
                strategy_stats[strat]['total_swings'] += swings
                strategy_stats[strat]['zones'] += 1

    print("\n   Average swings per zone:")
    for strat, stats in strategy_stats.items():
        avg = stats['total_swings'] / stats['zones'] if stats['zones'] > 0 else 0
        print(f"   {strat:<15}: {avg:.1f} swings/zone")

    # Show detailed metrics for one strategy
    print("\n6. Detailed metrics from ZigZag strategy:")

    result_zigzag = strategy_results['zigzag']

    zigzag_zone = extract_matching_zone(result_zigzag.zones, zone)

    if zigzag_zone:
        features = zigzag_zone.features or {}
        swings, avg_rally, avg_drop = summarize_zone(zigzag_zone)

        print(f"   Swing counts:")
        print(f"      Total swings: {swings}")
        print(f"      Rallies: {features.get('rally_count', max(swings // 2, 0))}")
        print(f"      Drops: {features.get('drop_count', max(swings // 2, 0))}")

        print(f"   Amplitudes:")
        print(f"      Avg rally: {avg_rally:.2%}")
        print(f"      Max rally: {features.get('max_rally_pct', avg_rally):.2%}")
        print(f"      Avg drop: {avg_drop:.2%}")
        print(f"      Max drop: {features.get('max_drop_pct', avg_drop):.2%}")

        print(f"   Ratios:")
        print(f"      Rally/Drop ratio: {features.get('rally_to_drop_ratio', 0):.2f}")
        print(f"      Duration symmetry: {features.get('duration_symmetry', 0):.2f}")

        print(f"   Speed:")
        print(f"      Avg rally speed: {features.get('avg_rally_speed_pct_per_bar', avg_rally):.3%}/bar")
        print(f"      Avg drop speed: {features.get('avg_drop_speed_pct_per_bar', avg_drop):.3%}/bar")

    # Test other strategies
    print("\n7. Testing other strategy types...")

    result_shape = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(shape='statistical')
        .analyze(clustering=False)
        .build()
    )

    shape_zone = extract_matching_zone(result_shape.zones, zone)

    if shape_zone and shape_zone.features:
        features = shape_zone.features
        print(f"   Shape metrics:")
        print(f"      Skewness: {features.get('hist_skewness', 0):.3f}")
        print(f"      Kurtosis: {features.get('hist_kurtosis', 0):.3f}")
        print(f"      Smoothness: {features.get('hist_smoothness', 0):.3f}")

    result_div = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(divergence='classic')
        .analyze(clustering=False)
        .build()
    )

    div_zone = extract_matching_zone(result_div.zones, zone)

    if div_zone and div_zone.features:
        features = div_zone.features
        has_divergence = features.get('has_classic_divergence', False)
        if has_divergence:
            print(f"   Divergence detected:")
            print(f"      Type: {features.get('divergence_type', 'unknown')}")
            print(f"      Count: {features.get('divergence_count', 0)}")
            print(f"      Strength: {features.get('divergence_strength', 0):.2f}")
        else:
            print(f"   No divergences detected")

    result_vol = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(volatility='combined')
        .analyze(clustering=False)
        .build()
    )

    vol_zone = extract_matching_zone(result_vol.zones, zone)

    if vol_zone and vol_zone.features:
        features = vol_zone.features
        print(f"   Volatility metrics:")
        print(f"      Score: {features.get('volatility_score', 0):.1f}/10")
        print(f"      Regime: {features.get('volatility_regime', 'unknown')}")
        print(f"      Bollinger width: {features.get('bollinger_width_pct', 0):.2%}")

    result_volume = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(volume='standard')
        .analyze(clustering=False)
        .build()
    )

    volume_zone = extract_matching_zone(result_volume.zones, zone)

    if volume_zone and volume_zone.features:
        features = volume_zone.features
        print(f"   Volume metrics:")
        print(f"      Correlation: {features.get('volume_indicator_corr', 0):.3f}")
        print(f"      Trend: {features.get('volume_trend', 'unknown')}")
        print(f"      Average: {features.get('avg_volume', 0):.0f}")

    print("\n" + "=" * 60)
    print("Strategy Selection Guidelines:")
    print("=" * 60)
    print("ZigZag:")
    print("  ✅ Smooth trending markets, larger timeframes")
    print("  ✅ Filter out noise, focus on major swings")
    print("")
    print("FindPeaks:")
    print("  ✅ Choppy/ranging markets, detect all extrema")
    print("  ✅ Detailed analysis, smaller timeframes")
    print("")
    print("PivotPoints:")
    print("  ✅ Classic technical analysis, validated swings")
    print("  ✅ Conservative detection, any timeframe")
    print("")
    print("Universal Pipeline Benefits:")
    print("  ✅ Same strategies work with ANY indicator")
    print("  ✅ indicator_context automatically adapts")
    print("  ✅ Zero code duplication across indicators")
    print("  ✅ Modern API with graceful degradation")
    print("")
    print("indicator_context Contract:")
    print("  ✅ Strategies automatically fill standard fields")
    print("  ✅ Universal access via zone.features.get()")
    print("  ✅ No hardcoded indicator-specific code")
    print("  ✅ True universality across all indicators")
    print("=" * 60)

    print("\nFurther resources:")
    print("  - docs/api/analysis/zones.md")
    print("  - docs/examples/README.md")
    print("  - examples/02a_universal_zones.py")


if __name__ == '__main__':
    main()
