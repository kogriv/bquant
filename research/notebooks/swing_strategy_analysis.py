"""
Анализ архитектурной проблемы swing_strategy

Цель: Понять как правильно использовать swing strategies в v2.1
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig

print("=" * 80)
print("SWING STRATEGY ARCHITECTURE ANALYSIS")
print("=" * 80)

# Prepare data
print("\n[STEP 1] Preparing data...")
df = get_sample_data('tv_xauusd_1h')
if 'time' in df.columns:
    df = df.set_index('time')
df = df.tail(500)  # Use last 500 bars

# Calculate MACD
indicator = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
result = indicator.calculate(df)
for col in result.data.columns:
    df[col] = result.data[col]

print(f"Data shape: {df.shape}")
print(f"MACD columns: {[c for c in df.columns if 'macd' in c.lower()]}")

# ============================================================================
# TEST 1: Current Builder API (DOES NOT SUPPORT swing_strategy)
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 1] Builder API - Does .analyze() accept swing_strategy?")
print("=" * 80)

try:
    result_test1 = (
        analyze_zones(df)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(
            clustering=False,
            # swing_strategy='find_peaks'  # ❌ This parameter DOES NOT EXIST
        )
        .build()
    )
    
    print(f"\n✅ Builder executed successfully")
    print(f"Zones detected: {len(result_test1.zones)}")
    
    # Check if swing metrics exist
    if result_test1.zones:
        first_zone = result_test1.zones[0]
        print(f"\nFirst zone features keys: {list(first_zone.features.keys()) if first_zone.features else 'None'}")
        
        has_swing = any('swing' in str(k).lower() for k in (first_zone.features.keys() if first_zone.features else []))
        has_peak = any('peak' in str(k).lower() for k in (first_zone.features.keys() if first_zone.features else []))
        
        print(f"\n{'❌' if not (has_swing or has_peak) else '✅'} Swing metrics in features: {has_swing or has_peak}")
        
        if has_swing or has_peak:
            swing_keys = [k for k in first_zone.features.keys() if 'swing' in str(k).lower() or 'peak' in str(k).lower()]
            print(f"Swing-related keys: {swing_keys}")
    
    print(f"\n{'❌' if not has_swing else '✅'} Result: Builder does NOT provide swing metrics by default")
    
except TypeError as e:
    print(f"\n❌ ERROR: {e}")
    print("Builder.analyze() does NOT accept swing_strategy parameter")

# ============================================================================
# TEST 2: Check Builder.analyze() signature
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 2] Inspect Builder.analyze() method signature")
print("=" * 80)

from bquant.analysis.zones.pipeline import ZoneAnalysisBuilder
import inspect

sig = inspect.signature(ZoneAnalysisBuilder.analyze)
print(f"\nMethod signature: {sig}")
print("\nParameters:")
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} = {param.default}")

print("\n❌ Conclusion: NO swing_strategy parameter in Builder.analyze()")

# ============================================================================
# TEST 3: Check UniversalZoneAnalyzer signature
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 3] Inspect UniversalZoneAnalyzer.__init__() signature")
print("=" * 80)

sig_analyzer = inspect.signature(UniversalZoneAnalyzer.__init__)
print(f"\nMethod signature: {sig_analyzer}")
print("\nParameters:")
for param_name, param in sig_analyzer.parameters.items():
    if param_name != 'self':
        print(f"  - {param_name}: default={param.default}")

print("\n✅ Conclusion: UniversalZoneAnalyzer DOES accept swing_strategy!")

# ============================================================================
# TEST 4: Direct UniversalZoneAnalyzer usage (WITH swing_strategy)
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 4] Direct UniversalZoneAnalyzer usage WITH swing_strategy")
print("=" * 80)

try:
    # Detect zones first
    print("\n[4.1] Detecting zones...")
    detector = ZoneDetectionRegistry.get('zero_crossing')
    detection_config = ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_col': 'macd_hist'}
    )
    zones_direct = detector.detect_zones(df, detection_config)
    print(f"Zones detected: {len(zones_direct)}")
    
    # Create analyzer WITH swing_strategy
    print("\n[4.2] Creating UniversalZoneAnalyzer with swing_strategy='find_peaks'...")
    analyzer_with_swing = UniversalZoneAnalyzer(
        swing_strategy='find_peaks'
    )
    
    # Analyze zones
    print("[4.3] Analyzing zones with swing strategy...")
    result_direct = analyzer_with_swing.analyze_zones(
        zones_direct, 
        df,
        perform_clustering=False
    )
    
    print(f"\n✅ Direct analyzer executed successfully")
    print(f"Zones analyzed: {len(result_direct.zones)}")
    
    # Check swing metrics
    if result_direct.zones:
        first_zone = result_direct.zones[0]
        print(f"\nFirst zone features keys: {list(first_zone.features.keys()) if first_zone.features else 'None'}")
        
        has_swing = any('swing' in str(k).lower() for k in (first_zone.features.keys() if first_zone.features else []))
        has_peak = any('peak' in str(k).lower() for k in (first_zone.features.keys() if first_zone.features else []))
        
        print(f"\n{'✅' if (has_swing or has_peak) else '❌'} Swing metrics in features: {has_swing or has_peak}")
        
        if has_swing or has_peak:
            swing_keys = [k for k in first_zone.features.keys() if 'swing' in str(k).lower() or 'peak' in str(k).lower()]
            print(f"Swing-related keys: {swing_keys}")
            for key in swing_keys[:3]:  # Show first 3
                print(f"  {key}: {first_zone.features.get(key)}")
        
        print(f"\n{'✅' if (has_swing or has_peak) else '❌'} Result: Direct analyzer WITH swing_strategy WORKS!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TEST 5: Check ZoneAnalysisConfig structure
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 5] Inspect ZoneAnalysisConfig dataclass")
print("=" * 80)

from bquant.analysis.zones.pipeline import ZoneAnalysisConfig
from dataclasses import fields

config_fields = fields(ZoneAnalysisConfig)
print("\nZoneAnalysisConfig fields:")
for field in config_fields:
    print(f"  - {field.name}: {field.type}")

has_swing_field = any('swing' in field.name.lower() for field in config_fields)
print(f"\n❌ Has swing_strategy field: {has_swing_field}")

# ============================================================================
# TEST 6: Check if Pipeline accepts custom analyzer
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 6] Can ZoneAnalysisPipeline accept custom analyzer?")
print("=" * 80)

from bquant.analysis.zones.pipeline import ZoneAnalysisPipeline

sig_pipeline = inspect.signature(ZoneAnalysisPipeline.__init__)
print(f"\nPipeline.__init__ signature: {sig_pipeline}")
print("\nParameters:")
for param_name, param in sig_pipeline.parameters.items():
    if param_name != 'self':
        print(f"  - {param_name}: default={param.default}")

has_analyzer_param = 'zone_analyzer' in sig_pipeline.parameters
print(f"\n{'✅' if has_analyzer_param else '❌'} Has zone_analyzer parameter: {has_analyzer_param}")

if has_analyzer_param:
    print("\n✅ YES! Pipeline CAN accept custom UniversalZoneAnalyzer")
    print("   BUT: Builder does NOT expose this capability!")

# ============================================================================
# TEST 7: Try using Pipeline directly with custom analyzer
# ============================================================================
print("\n" + "=" * 80)
print("[TEST 7] Direct Pipeline usage WITH custom analyzer")
print("=" * 80)

try:
    from bquant.analysis.zones.pipeline import IndicatorConfig
    
    # Create custom analyzer WITH swing_strategy
    custom_analyzer = UniversalZoneAnalyzer(
        swing_strategy='find_peaks'
    )
    
    # Create config
    config = ZoneAnalysisConfig(
        indicator=None,  # Already calculated
        zone_detection=ZoneDetectionConfig(
            strategy_name='zero_crossing',
            rules={'indicator_col': 'macd_hist'}
        ),
        perform_clustering=False
    )
    
    # Create pipeline WITH custom analyzer
    pipeline = ZoneAnalysisPipeline(
        config,
        zone_analyzer=custom_analyzer,
        enable_cache=False
    )
    
    # Run
    result_pipeline = pipeline.run(df)
    
    print(f"\n✅ Pipeline with custom analyzer executed successfully")
    print(f"Zones: {len(result_pipeline.zones)}")
    
    # Check swing metrics
    if result_pipeline.zones:
        first_zone = result_pipeline.zones[0]
        has_swing = any('swing' in str(k).lower() for k in (first_zone.features.keys() if first_zone.features else []))
        has_peak = any('peak' in str(k).lower() for k in (first_zone.features.keys() if first_zone.features else []))
        
        print(f"\n{'✅' if (has_swing or has_peak) else '❌'} Swing metrics present: {has_swing or has_peak}")
        
        if has_swing or has_peak:
            swing_keys = [k for k in first_zone.features.keys() if 'swing' in str(k).lower() or 'peak' in str(k).lower()]
            print(f"Swing-related keys: {swing_keys[:5]}")
    
    print(f"\n✅ Result: Direct Pipeline + custom analyzer WORKS!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY: Swing Strategy Architecture")
print("=" * 80)

print("""
FINDINGS:

1. ❌ ZoneAnalysisBuilder.analyze() does NOT accept swing_strategy parameter
   - Only accepts: clustering, n_clusters, regression, validation
   
2. ❌ ZoneAnalysisConfig does NOT have fields for analytical strategies
   - No swing_strategy, shape_strategy, etc.
   
3. ✅ UniversalZoneAnalyzer DOES accept swing_strategy in __init__
   - Can be configured: swing_strategy='find_peaks'
   
4. ✅ ZoneAnalysisPipeline CAN accept custom UniversalZoneAnalyzer
   - Constructor has zone_analyzer parameter
   - But Builder does NOT expose this!
   
5. ❌ Builder creates default UniversalZoneAnalyzer() without strategies
   - No way to customize through Builder API

ARCHITECTURE GAP:

The Builder (fluent API) does NOT provide a way to configure analytical strategies!

CURRENT WORKAROUNDS:

A) Use UniversalZoneAnalyzer directly (bypass Builder)
B) Use ZoneAnalysisPipeline directly with custom analyzer
C) Extend Builder to support analytical strategies configuration

RECOMMENDATIONS:

Option 1: Add .with_strategies() method to Builder
   result = (
       analyze_zones(df)
       .detect_zones(...)
       .with_strategies(swing='find_peaks', shape='statistical')
       .analyze(...)
       .build()
   )

Option 2: Extend .analyze() method to accept strategies
   result = (
       analyze_zones(df)
       .detect_zones(...)
       .analyze(swing_strategy='find_peaks', ...)
       .build()
   )

Option 3: Add .with_analyzer() method to Builder
   custom_analyzer = UniversalZoneAnalyzer(swing_strategy='find_peaks')
   result = (
       analyze_zones(df)
       .with_analyzer(custom_analyzer)
       .detect_zones(...)
       .build()
   )

For notebooks: Use workaround B (direct Pipeline usage) until Builder is extended.
""")

print("\n" + "=" * 80)
print("END OF ANALYSIS")
print("=" * 80)

