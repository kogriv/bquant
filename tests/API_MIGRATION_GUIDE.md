# API Migration Guide: Phase 1 Analysis Results

## Problem Summary

**70 ERROR tests** fail with:
```python
AttributeError: 'MACDZoneAnalyzer' object has no attribute 'identify_zones'
```

## Root Cause

`MACDZoneAnalyzer.identify_zones()` method was **removed** during refactoring to universal zone analysis architecture. The class is now a thin wrapper that only provides:
- `analyze_complete()` 
- `analyze_complete_modular()`

## Old API (DEPRECATED & BROKEN)

```python
from bquant.indicators.macd import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()
zones = analyzer.identify_zones(df)  # ❌ DOES NOT EXIST
```

## New API (Recommended)

### Option 1: Universal Zone Analysis (Best Practice)
```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

zones = result.zones  # List[ZoneInfo]
```

### Option 2: Use analyze_complete_modular (Backward Compatible)
```python
from bquant.indicators.macd import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete_modular(df)  # ✅ Returns ZoneAnalysisResult
zones = result.zones  # List[ZoneInfo]
```

### Option 3: Use Preset Function (Simplest)
```python
from bquant.analysis.zones import analyze_macd_zones

result = analyze_macd_zones(df, clustering=True)
zones = result.zones
```

## Return Type Changes

### Old (identify_zones)
```python
zones: List[ZoneInfo]  # Just list of zones
```

### New (analyze_complete_modular)
```python
result: ZoneAnalysisResult  # Comprehensive result object
result.zones: List[ZoneInfo]  # Access zones via .zones
result.statistics: dict
result.features: Optional[ZoneFeatures]
result.sequence_analysis: Optional[TransitionAnalysis]
```

## Test Fixture Migration Pattern

### Before (BROKEN):
```python
@pytest.fixture(scope="class")
def sample_zones(self):
    df = get_sample_data('tv_xauusd_1h')
    analyzer = MACDZoneAnalyzer()
    zones = analyzer.identify_zones(df)  # ❌ BROKEN
    return zones
```

### After (FIXED - Option 1):
```python
@pytest.fixture(scope="class")
def sample_zones(self):
    df = get_sample_data('tv_xauusd_1h')
    analyzer = MACDZoneAnalyzer()
    result = analyzer.analyze_complete_modular(df)  # ✅ WORKS
    return result.zones
```

### After (FIXED - Option 2):
```python
@pytest.fixture(scope="class")
def sample_zones(self):
    df = get_sample_data('tv_xauusd_1h')
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd')
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .build()
    )
    return result.zones
```

### After (FIXED - Option 3):
```python
@pytest.fixture(scope="class")
def sample_zones(self):
    from bquant.analysis.zones import analyze_macd_zones
    df = get_sample_data('tv_xauusd_1h')
    result = analyze_macd_zones(df)
    return result.zones
```

## Affected Test Files

All files use the same broken pattern in fixtures:

1. `test_zone_features_swing_integration.py` - 5 tests
2. `test_zone_features_volume_integration.py` - 5 tests
3. `test_zone_features_volatility_integration.py` - 5 tests
4. `test_zone_features_divergence_integration.py` - 3 tests
5. `test_zone_features_shape_integration.py` - 4 tests
6. Plus ~48 other integration tests

**Common pattern:** All have `sample_zones` fixture at line 18-22 using `identify_zones()`

## Recommended Fix Strategy

**Use Option 1 (analyze_complete_modular)** for minimal changes:

1. Replace line 22 in all affected test files:
   ```python
   # OLD:
   zones = analyzer.identify_zones(df)
   
   # NEW:
   result = analyzer.analyze_complete_modular(df)
   zones = result.zones
   ```

2. Optional: Add `macd_hist` column if needed (line 25-26):
   ```python
   # This code may still be needed depending on test:
   for zone in zones:
       if 'macd_hist' not in zone.data.columns:
           zone.data['macd_hist'] = zone.data['macd'] - zone.data['signal']
   ```

## Implementation Plan

### Step 1: Update Fixtures (Bulk Change)
Update all `sample_zones` fixtures in 5+ test files with same pattern.

### Step 2: Verify Zone Data Structure
Check if zones have required columns (macd_hist, etc.)

### Step 3: Run Tests
```bash
pytest tests/unit/test_zone_features_*_integration.py -v
```

### Step 4: Fix Any Remaining Issues
Handle edge cases if result structure differs from expectations.

## Key Insights

1. **Method removed, not renamed** - `identify_zones()` completely gone
2. **Wrapper pattern** - `MACDZoneAnalyzer` now delegates to universal pipeline
3. **Return type changed** - Now returns `ZoneAnalysisResult` not `List[ZoneInfo]`
4. **Same fix for all 70 tests** - All use identical broken pattern
5. **Minimal code change** - Just change 2 lines per fixture

## Verification

After fix, verify:
```python
from bquant.indicators.macd import MACDZoneAnalyzer
print(dir(MACDZoneAnalyzer))
# Should show: ['analyze_complete', 'analyze_complete_modular']
# Should NOT show: 'identify_zones'
```

## Phase 1 Completion Checklist

- [x] Task 1.1: Inspect failing test files ✅
- [x] Task 1.2: Review MACDZoneAnalyzer API ✅
- [x] Task 1.3: Identify replacement method ✅ `analyze_complete_modular()`
- [x] Task 1.4: Document migration guide ✅ This file

---

**Next Phase:** Phase 2 - Apply fixes to all 70 ERROR tests
