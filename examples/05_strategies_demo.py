"""
Strategy Pattern usage demonstration - Universal Pipeline v2.1.

API Stability: STABLE (strategies are universal)

This example demonstrates:
1. Using different swing strategies with Universal Pipeline
2. Comparing strategy results across multiple indicators
3. Accessing strategy metrics via zone.features
4. Strategy selection guidelines
5. indicator_context contract demonstration
"""

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones


def main():
    print("=" * 60)
    print("BQuant Strategy Pattern Demo - Universal Pipeline v2.1")
    print("=" * 60)
    
    # Load sample data
    print("\n1. Loading data...")
    data = get_sample_data('tv_xauusd_1h')
    print(f"   Loaded {len(data)} bars of XAUUSD 1H data")
    
    # Test Universal Pipeline with different indicators
    print("\n2. Testing Universal Pipeline with multiple indicators...")
    
    indicators_to_test = [
        ('custom', 'macd', {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}),
        ('pandas_ta', 'rsi', {'length': 14}),
        ('pandas_ta', 'ao', {'fast': 5, 'slow': 34})
    ]
    
    for source, name, params in indicators_to_test:
        print(f"\n   === Testing {name.upper()} with Universal Strategies ===")
        
        # Universal Pipeline - работает с ЛЮБЫМ индикатором
        result = (
            analyze_zones(data)
            .with_indicator(source, name, **params)
            .detect_zones(
                'zero_crossing' if name in ['macd', 'ao'] else 'threshold',
                indicator_col=f'{name}_hist' if name in ['macd', 'ao'] else name,
                upper_threshold=70 if name == 'rsi' else None,
                lower_threshold=30 if name == 'rsi' else None
            )
            .with_strategies(
                swing='find_peaks',      # Работает с ЛЮБЫМ индикатором
                divergence='classic',    # Работает с ЛЮБЫМ индикатором
                volume='standard',       # Работает с ЛЮБЫМ индикатором
                volatility='combined'    # Работает с ЛЮБЫМ индикатором
            )
            .analyze(clustering=False)
            .build()
        )
        
        # indicator_context автоматически адаптируется к каждому индикатору:
        # - line1_col: основная линия индикатора
        # - line2_col: сигнальная линия (если есть)
        # - indicator_name: имя индикатора
        # - source_type: источник индикатора
        # - histogram_col: колонка гистограммы (для zero_crossing detection)
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
        .analyze(clustering=False)
        .build()
    )
    
    print(f"   Found {len(result_macd.zones)} MACD zones")
    if not result_macd.zones:
        print("   No zones found, exiting.")
        return
    
    # Compare swing strategies on first zone
    print("\n4. Comparing swing strategies on first zone...")
    zone = result_macd.zones[0]
    print(f"   Zone ID: {zone.zone_id}")
    print(f"   Type: {zone.type}")
    print(f"   Duration: {zone.duration} bars")
    
    strategies = ['zigzag', 'find_peaks', 'pivot_points']
    
    print("\n   Strategy comparison:")
    print("   " + "-" * 55)
    print(f"   {'Strategy':<15} {'Swings':<8} {'Avg Rally':<12} {'Avg Drop':<12}")
    print("   " + "-" * 55)
    
    for strat in strategies:
        # Test each strategy individually
        result_strategy = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing=strat)
            .analyze(clustering=False)
            .build()
        )
        
        # Find corresponding zone
        strategy_zone = None
        for z in result_strategy.zones:
            if z.zone_id == zone.zone_id:
                strategy_zone = z
                break
        
        if strategy_zone and strategy_zone.features:
            num_swings = strategy_zone.features.get('num_swings', 0)
            avg_rally = strategy_zone.features.get('avg_rally_pct', 0)
            avg_drop = strategy_zone.features.get('avg_drop_pct', 0)
            
            print(f"   {strat:<15} {num_swings:<8} {avg_rally:>10.2%}  {avg_drop:>10.2%}")
        else:
            print(f"   {strat:<15} {'N/A':<8} {'N/A':>10}  {'N/A':>10}")
    
    print("   " + "-" * 55)
    
    # Test all strategies on multiple zones
    print("\n5. Testing all strategies on first 5 zones...")
    
    strategy_stats = {name: {'total_swings': 0, 'zones': 0} for name in strategies}
    
    for zone in result_macd.zones[:5]:
        for strat in strategies:
            result_strategy = (
                analyze_zones(data)
                .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .with_strategies(swing=strat)
                .analyze(clustering=False)
                .build()
            )
            
            # Find corresponding zone
            strategy_zone = None
            for z in result_strategy.zones:
                if z.zone_id == zone.zone_id:
                    strategy_zone = z
                    break
            
            if strategy_zone and strategy_zone.features:
                num_swings = strategy_zone.features.get('num_swings', 0)
                strategy_stats[strat]['total_swings'] += num_swings
                strategy_stats[strat]['zones'] += 1
    
    print("\n   Average swings per zone:")
    for strat, stats in strategy_stats.items():
        avg = stats['total_swings'] / stats['zones'] if stats['zones'] > 0 else 0
        print(f"   {strat:<15}: {avg:.1f} swings/zone")
    
    # Show detailed metrics for one strategy
    print("\n6. Detailed metrics from ZigZag strategy:")
    
    result_zigzag = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='zigzag')
        .analyze(clustering=False)
        .build()
    )
    
    # Find corresponding zone
    zigzag_zone = None
    for z in result_zigzag.zones:
        if z.zone_id == zone.zone_id:
            zigzag_zone = z
            break
    
    if zigzag_zone and zigzag_zone.features:
        features = zigzag_zone.features
        
        print(f"   Swing counts:")
        print(f"      Total swings: {features.get('num_swings', 0)}")
        print(f"      Rallies: {features.get('rally_count', 0)}")
        print(f"      Drops: {features.get('drop_count', 0)}")
        
        print(f"   Amplitudes:")
        print(f"      Avg rally: {features.get('avg_rally_pct', 0):.2%}")
        print(f"      Max rally: {features.get('max_rally_pct', 0):.2%}")
        print(f"      Avg drop: {features.get('avg_drop_pct', 0):.2%}")
        print(f"      Max drop: {features.get('max_drop_pct', 0):.2%}")
        
        print(f"   Ratios:")
        print(f"      Rally/Drop ratio: {features.get('rally_to_drop_ratio', 0):.2f}")
        print(f"      Duration symmetry: {features.get('duration_symmetry', 0):.2f}")
        
        print(f"   Speed:")
        print(f"      Avg rally speed: {features.get('avg_rally_speed_pct_per_bar', 0):.3%}/bar")
        print(f"      Avg drop speed: {features.get('avg_drop_speed_pct_per_bar', 0):.3%}/bar")
    
    # Test other strategies
    print("\n7. Testing other strategy types...")
    
    # Shape strategy
    result_shape = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(shape='statistical')
        .analyze(clustering=False)
        .build()
    )
    
    # Find corresponding zone
    shape_zone = None
    for z in result_shape.zones:
        if z.zone_id == zone.zone_id:
            shape_zone = z
            break
    
    if shape_zone and shape_zone.features:
        features = shape_zone.features
        print(f"   Shape metrics:")
        print(f"      Skewness: {features.get('hist_skewness', 0):.3f}")
        print(f"      Kurtosis: {features.get('hist_kurtosis', 0):.3f}")
        print(f"      Smoothness: {features.get('hist_smoothness', 0):.3f}")
    
    # Divergence strategy
    result_div = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(divergence='classic')
        .analyze(clustering=False)
        .build()
    )
    
    # Find corresponding zone
    div_zone = None
    for z in result_div.zones:
        if z.zone_id == zone.zone_id:
            div_zone = z
            break
    
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
    
    # Volatility strategy
    result_vol = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(volatility='combined')
        .analyze(clustering=False)
        .build()
    )
    
    # Find corresponding zone
    vol_zone = None
    for z in result_vol.zones:
        if z.zone_id == zone.zone_id:
            vol_zone = z
            break
    
    if vol_zone and vol_zone.features:
        features = vol_zone.features
        print(f"   Volatility metrics:")
        print(f"      Score: {features.get('volatility_score', 0):.1f}/10")
        print(f"      Regime: {features.get('volatility_regime', 'unknown')}")
        print(f"      Bollinger width: {features.get('bollinger_width_pct', 0):.2%}")
    
    # Volume strategy
    result_volume = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(volume='standard')
        .analyze(clustering=False)
        .build()
    )
    
    # Find corresponding zone
    volume_zone = None
    for z in result_volume.zones:
        if z.zone_id == zone.zone_id:
            volume_zone = z
            break
    
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


if __name__ == '__main__':
    main()