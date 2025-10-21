"""
Simple swing strategy architecture test
"""
import sys
import os
from pathlib import Path

# Suppress logging
os.environ['PYTHONIOENCODING'] = 'utf-8'
import logging
logging.basicConfig(level=logging.ERROR)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones.pipeline import ZoneAnalysisBuilder

print("\n" + "=" * 80)
print("SWING STRATEGY ARCHITECTURE TEST")
print("=" * 80)

# Prepare data
df = get_sample_data('tv_xauusd_1h').tail(500)
if 'time' in df.columns:
    df = df.set_index('time')

# Calculate MACD
indicator = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
result = indicator.calculate(df)
for col in result.data.columns:
    df[col] = result.data[col]

print(f"\nData shape: {df.shape}")

# ============================================================================
# TEST 1: Builder API default behavior
# ============================================================================
print("\n" + "-" * 80)
print("TEST 1: Builder API (default behavior)")
print("-" * 80)

result1 = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=False)
    .build()
)

print(f"Zones detected: {len(result1.zones)}")

if result1.zones:
    zone = result1.zones[0]
    print(f"First zone features keys: {len(zone.features) if zone.features else 0} keys")
    
    # Check for swing metrics
    swing_keys = []
    if zone.features:
        swing_keys = [k for k in zone.features.keys() 
                     if 'swing' in str(k).lower() or 'peak' in str(k).lower() or 'trough' in str(k).lower()]
    
    print(f"Swing-related keys found: {len(swing_keys)}")
    if swing_keys:
        print(f"Keys: {swing_keys[:5]}")
        for key in swing_keys[:3]:
            print(f"  {key}: {zone.features.get(key)}")
    else:
        print("NO swing metrics in default builder!")

# ============================================================================
# TEST 2: Direct UniversalZoneAnalyzer with swing_strategy
# ============================================================================
print("\n" + "-" * 80)
print("TEST 2: Direct UniversalZoneAnalyzer with swing_strategy='find_peaks'")
print("-" * 80)

try:
    # Detect zones
    detector = ZoneDetectionRegistry.get('zero_crossing')
    detection_config = ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_col': 'macd_hist'}
    )
    zones = detector.detect_zones(df, detection_config)
    print(f"Zones detected: {len(zones)}")
    
    # Create analyzer WITH swing_strategy
    analyzer = UniversalZoneAnalyzer(swing_strategy='find_peaks')
    
    # Analyze
    result2 = analyzer.analyze_zones(zones, df, perform_clustering=False)
    
    print(f"Zones analyzed: {len(result2.zones)}")
    
    if result2.zones:
        zone = result2.zones[0]
        print(f"First zone features keys: {len(zone.features) if zone.features else 0} keys")
        
        # Check for swing metrics
        swing_keys = []
        if zone.features:
            swing_keys = [k for k in zone.features.keys() 
                         if 'swing' in str(k).lower() or 'peak' in str(k).lower() or 'trough' in str(k).lower()]
        
        print(f"Swing-related keys found: {len(swing_keys)}")
        if swing_keys:
            print(f"Keys: {swing_keys[:5]}")
            for key in swing_keys[:3]:
                print(f"  {key}: {zone.features.get(key)}")
            print("\nSUCCESS: Direct analyzer with swing_strategy WORKS!")
        else:
            print("ERROR: No swing metrics even with swing_strategy!")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 3: Check ZoneAnalysisBuilder.analyze() signature
# ============================================================================
print("\n" + "-" * 80)
print("TEST 3: ZoneAnalysisBuilder.analyze() method signature")
print("-" * 80)

import inspect
sig = inspect.signature(ZoneAnalysisBuilder.analyze)
params = [p for p in sig.parameters.keys() if p != 'self']
print(f"Parameters: {params}")
print(f"Has swing_strategy parameter: {'swing_strategy' in params}")

# ============================================================================
# TEST 4: Check UniversalZoneAnalyzer.__init__ signature
# ============================================================================
print("\n" + "-" * 80)
print("TEST 4: UniversalZoneAnalyzer.__init__() signature")
print("-" * 80)

sig2 = inspect.signature(UniversalZoneAnalyzer.__init__)
params2 = [p for p in sig2.parameters.keys() if p != 'self']
print(f"Parameters: {params2}")
print(f"Has swing_strategy parameter: {'swing_strategy' in params2}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
PROBLEM IDENTIFIED:

1. ZoneAnalysisBuilder.analyze() does NOT accept swing_strategy
   - Only accepts: clustering, n_clusters, regression, validation
   
2. UniversalZoneAnalyzer DOES accept swing_strategy in __init__
   - Can be configured directly
   
3. Builder creates default UniversalZoneAnalyzer() without strategies
   - No way to pass swing_strategy through Builder API

SOLUTION OPTIONS:

A) Add .with_strategies() method to Builder
B) Extend .analyze() to accept swing_strategy parameter
C) Add .with_analyzer() to pass custom UniversalZoneAnalyzer
D) Use UniversalZoneAnalyzer directly (workaround)

RECOMMENDATION: Extend Builder to support analytical strategies configuration
""")

print("\n" + "=" * 80)
print("END")
print("=" * 80)

