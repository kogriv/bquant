"""
Strategy Pattern usage demonstration.

API Stability: STABLE (strategies are universal)

This example demonstrates:
1. Using different swing strategies
2. Comparing strategy results
3. Accessing strategy metrics
4. Strategy selection guidelines
"""

from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer
from bquant.analysis.zones import ZoneFeaturesAnalyzer


def main():
    print("=" * 60)
    print("BQuant Strategy Pattern Demo")
    print("=" * 60)
    
    # Load sample data
    print("\n1. Loading data...")
    data = get_sample_data('tv_xauusd_1h')
    print(f"   Loaded {len(data)} bars of XAUUSD 1H data")
    
    # Analyze zones
    print("\n2. Analyzing MACD zones...")
    analyzer = MACDZoneAnalyzer()
    result = analyzer.analyze_complete(data, perform_clustering=False)
    print(f"   Found {len(result.zones)} zones")
    print(f"   Bull zones: {result.statistics['bull_zones']}")
    print(f"   Bear zones: {result.statistics['bear_zones']}")
    
    if not result.zones:
        print("   No zones found, exiting.")
        return
    
    # Compare swing strategies on first zone
    print("\n3. Comparing swing strategies on first zone...")
    zone = result.zones[0]
    zone_dict = analyzer._zone_to_dict(zone)
    print(f"   Zone ID: {zone.zone_id}")
    print(f"   Type: {zone.type}")
    print(f"   Duration: {zone.duration} bars")
    
    strategies = ['zigzag', 'find_peaks', 'pivot_points']
    
    print("\n   Strategy comparison:")
    print("   " + "-" * 55)
    print(f"   {'Strategy':<15} {'Swings':<8} {'Avg Rally':<12} {'Avg Drop':<12}")
    print("   " + "-" * 55)
    
    for strat in strategies:
        fa = ZoneFeaturesAnalyzer(swing_strategy=strat)
        features = fa.extract_zone_features(zone_dict)
        swing_metrics = features.metadata.get('swing_metrics', {})
        
        num_swings = swing_metrics.get('num_swings', 0)
        avg_rally = swing_metrics.get('avg_rally_pct', 0)
        avg_drop = swing_metrics.get('avg_drop_pct', 0)
        
        print(f"   {strat:<15} {num_swings:<8} {avg_rally:>10.2%}  {avg_drop:>10.2%}")
    
    print("   " + "-" * 55)
    
    # Test all strategies on multiple zones
    print("\n4. Testing all strategies on first 5 zones...")
    
    strategy_stats = {name: {'total_swings': 0, 'zones': 0} for name in strategies}
    
    for zone in result.zones[:5]:
        zone_dict = analyzer._zone_to_dict(zone)
        
        for strat in strategies:
            fa = ZoneFeaturesAnalyzer(swing_strategy=strat)
            features = fa.extract_zone_features(zone_dict)
            swing_metrics = features.metadata.get('swing_metrics', {})
            
            strategy_stats[strat]['total_swings'] += swing_metrics.get('num_swings', 0)
            strategy_stats[strat]['zones'] += 1
    
    print("\n   Average swings per zone:")
    for strat, stats in strategy_stats.items():
        avg = stats['total_swings'] / stats['zones'] if stats['zones'] > 0 else 0
        print(f"   {strat:<15}: {avg:.1f} swings/zone")
    
    # Show detailed metrics for one strategy
    print("\n5. Detailed metrics from ZigZag strategy:")
    fa = ZoneFeaturesAnalyzer(swing_strategy='zigzag')
    features = fa.extract_zone_features(zone_dict)
    swing = features.metadata.get('swing_metrics', {})
    
    print(f"   Swing counts:")
    print(f"      Total swings: {swing.get('num_swings', 0)}")
    print(f"      Rallies: {swing.get('rally_count', 0)}")
    print(f"      Drops: {swing.get('drop_count', 0)}")
    
    print(f"   Amplitudes:")
    print(f"      Avg rally: {swing.get('avg_rally_pct', 0):.2%}")
    print(f"      Max rally: {swing.get('max_rally_pct', 0):.2%}")
    print(f"      Avg drop: {swing.get('avg_drop_pct', 0):.2%}")
    print(f"      Max drop: {swing.get('max_drop_pct', 0):.2%}")
    
    print(f"   Ratios:")
    print(f"      Rally/Drop ratio: {swing.get('rally_to_drop_ratio', 0):.2f}")
    print(f"      Duration symmetry: {swing.get('duration_symmetry', 0):.2f}")
    
    print(f"   Speed:")
    print(f"      Avg rally speed: {swing.get('avg_rally_speed_pct_per_bar', 0):.3%}/bar")
    print(f"      Avg drop speed: {swing.get('avg_drop_speed_pct_per_bar', 0):.3%}/bar")
    
    # Test other strategies
    print("\n6. Testing other strategy types...")
    
    # Shape strategy
    analyzer_shape = ZoneFeaturesAnalyzer(
        swing_strategy='zigzag',
        shape_strategy='statistical'
    )
    features_shape = analyzer_shape.extract_zone_features(zone_dict)
    shape = features_shape.metadata.get('shape_metrics', {})
    
    if shape:
        print(f"   Shape metrics:")
        print(f"      Skewness: {shape.get('hist_skewness', 0):.3f}")
        print(f"      Kurtosis: {shape.get('hist_kurtosis', 0):.3f}")
        print(f"      Smoothness: {shape.get('hist_smoothness', 0):.3f}")
    
    # Divergence strategy
    analyzer_div = ZoneFeaturesAnalyzer(
        swing_strategy='zigzag',
        divergence_strategy='classic'
    )
    features_div = analyzer_div.extract_zone_features(zone_dict)
    div = features_div.metadata.get('divergence_metrics', {})
    
    if div and div.get('divergence_count', 0) > 0:
        print(f"   Divergence detected:")
        print(f"      Type: {div.get('divergence_type')}")
        print(f"      Count: {div.get('divergence_count')}")
        print(f"      Strength: {div.get('divergence_strength', 0):.2f}")
    else:
        print(f"   No divergences detected")
    
    # Volatility strategy
    analyzer_vol = ZoneFeaturesAnalyzer(
        swing_strategy='zigzag',
        volatility_strategy='combined'
    )
    features_vol = analyzer_vol.extract_zone_features(zone_dict)
    vol = features_vol.metadata.get('volatility_metrics', {})
    
    if vol:
        print(f"   Volatility metrics:")
        print(f"      Score: {vol.get('volatility_score', 0):.1f}/10")
        print(f"      Regime: {vol.get('volatility_regime', 'unknown')}")
        print(f"      Bollinger width: {vol.get('bollinger_width_pct', 0):.2%}")
    
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
    print("=" * 60)


if __name__ == '__main__':
    main()

