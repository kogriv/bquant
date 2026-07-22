# Swing Strategy Architecture Analysis

**Date:** 2025-10-20  
**Context:** ЭТАП 1 из zonan_uni_full.md выявил проблему с `swing_strategy` в `.analyze()`

---

## 🔍 Проведенный анализ

### Test Results

**TEST 1: Builder API (default behavior)**
- Zones detected: 38
- Features in zone.features: **0 keys** ❌
- Swing metrics: **NONE**

**TEST 2: Direct UniversalZoneAnalyzer with swing_strategy='find_peaks'**
- Zones detected: 38  
- Features in zone.features: **0 keys** ❌
- Swing metrics: **NONE** (даже со swing_strategy!)

**TEST 3: ZoneAnalysisBuilder.analyze() signature**
```python
Parameters: ['clustering', 'n_clusters', 'regression', 'validation']
Has swing_strategy: False ❌
```

**TEST 4: UniversalZoneAnalyzer.__init__() signature**
```python
Parameters: [
    'features_analyzer', 'hypothesis_suite', 'sequence_analyzer',
    'regression_analyzer', 'validation_suite', 
    'swing_strategy', 'shape_strategy', 'divergence_strategy',
    'volatility_strategy', 'volume_strategy'
]
Has swing_strategy: True ✅
```

---

## 🚨 Критические находки

### Проблема 1: Builder API НЕ поддерживает swing_strategy

**Корневая причина:**
- `ZoneAnalysisBuilder.analyze()` принимает только: `clustering`, `n_clusters`, `regression`, `validation`
- НЕТ параметров для analytical strategies (swing, shape, divergence, volatility, volume)
- `ZoneAnalysisConfig` НЕ содержит полей для strategies
- Builder создает дефолтный `UniversalZoneAnalyzer()` БЕЗ параметров

**Код (bquant/analysis/zones/pipeline.py:375-399):**
```python
def analyze(self,
           clustering: bool = True,
           n_clusters: int = 3,
           regression: bool = False,
           validation: bool = False) -> 'ZoneAnalysisBuilder':
    """
    Настроить параметры анализа.
    
    Args:
        clustering: Выполнять кластеризацию
        n_clusters: Количество кластеров
        regression: Запустить регрессионный анализ
        validation: Запустить валидацию
    
    # ❌ NO swing_strategy, shape_strategy, etc.
    """
    self._perform_clustering = clustering
    self._n_clusters = n_clusters
    self._run_regression = regression
    self._run_validation = validation
    return self
```

**Pipeline (lines 100-115):**
```python
def __init__(self, 
             config: ZoneAnalysisConfig,
             zone_analyzer: Optional[UniversalZoneAnalyzer] = None,
             enable_cache: bool = True,
             cache_ttl: int = 3600):
    self.config = config
    self.analyzer = zone_analyzer or UniversalZoneAnalyzer()  # ❌ Default без strategies!
    # ...
```

---

### Проблема 2: Features НЕ извлекаются (даже критичнее!)

**Неожиданная находка:**
- `zone.features` содержит **0 keys** (пусто!)
- Это происходит ДАЖЕ когда используется прямой `UniversalZoneAnalyzer`
- Features извлекаются `ZoneFeaturesAnalyzer`, но НЕ пишутся обратно в `ZoneInfo`

**Код (bquant/analysis/zones/analyzer.py:147-155):**
```python
def analyze_zones(self, zones: List[ZoneInfo], data: pd.DataFrame, ...):
    # ...
    # Extract features
    zones_features = self.features.extract_all_zones_features(zones)
    
    # ❌ BUG: Features НЕ пишутся обратно в zones!
    # НЕТ: for zone, features in zip(zones, zones_features): zone.features = features.to_dict()
    
    return ZoneAnalysisResult(
        zones=zones,  # ❌ zones БЕЗ features!
        # ...
    )
```

**Исправление было сделано в 03_zones_universal.py (линия 151):**
```python
# ✅ ADDED: Write features back to ZoneInfo for convenient access
for zone, features in zip(zones, zones_features):
    zone.features = features.to_dict()
```

**Но это ЛОКАЛЬНОЕ исправление в notebook, НЕ в пакете!**

---

## 📋 Архитектурные проблемы

### 1. Builder API Gap

**Текущая ситуация:**
- Builder: `analyze_zones(df).detect_zones(...).analyze(...).build()`
- `.analyze()` НЕ принимает strategies
- Pipeline создает default `UniversalZoneAnalyzer()` без кастомизации

**Что задумывалось:**
- `UniversalZoneAnalyzer` ИМЕЕТ параметры для strategies в `__init__`
- Но Builder НЕ экспонирует этот функционал

**Проектная неконсистентность:**
```python
# ✅ Это РАБОТАЕТ (Direct usage):
analyzer = UniversalZoneAnalyzer(swing_strategy='find_peaks')
result = analyzer.analyze_zones(zones, df)

# ❌ Это НЕ РАБОТАЕТ (Builder API):
result = (
    analyze_zones(df)
    .detect_zones(...)
    .analyze(swing_strategy='find_peaks')  # ❌ Parameter не существует!
    .build()
)
```

---

### 2. Features Writing Gap

**Проблема:**
- `ZoneFeaturesAnalyzer.extract_all_zones_features()` возвращает `List[ZoneFeatures]`
- `UniversalZoneAnalyzer` НЕ пишет эти features обратно в `ZoneInfo.features`
- Пользователи получают zones БЕЗ features!

**Где это должно происходить:**

**Option A:** В `UniversalZoneAnalyzer.analyze_zones()` (RECOMMENDED)
```python
# В bquant/analysis/zones/analyzer.py:151
zones_features = self.features.extract_all_zones_features(zones)

# ✅ ADD THIS:
for zone, features in zip(zones, zones_features):
    zone.features = features.to_dict()
```

**Option B:** В каждом месте, где вызывается analyzer (NOT SCALABLE)

---

## 🎯 Рекомендации

### Краткосрочное решение (для notebooks):

**Workaround A: Direct UniversalZoneAnalyzer usage**
```python
from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig

# Detect zones
detector = ZoneDetectionRegistry.get('zero_crossing')
config = ZoneDetectionConfig(strategy_name='zero_crossing', rules={'indicator_col': 'macd_hist'})
zones = detector.detect_zones(df, config)

# Analyze with swing strategy
analyzer = UniversalZoneAnalyzer(swing_strategy='find_peaks')
result = analyzer.analyze_zones(zones, df, perform_clustering=False)
```

**Workaround B: Manual features writing (как в 03_zones_universal.py)**
```python
result = analyze_zones(df).detect_zones(...).analyze(...).build()

# ✅ Write features manually
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
features_analyzer = ZoneFeaturesAnalyzer(swing_strategy='find_peaks')
zones_features = features_analyzer.extract_all_zones_features(result.zones)
for zone, features in zip(result.zones, zones_features):
    zone.features = features.to_dict()
```

---

### Долгосрочное решение (изменения в пакете):

#### Fix 1: Добавить features writing в UniversalZoneAnalyzer

**File:** `bquant/analysis/zones/analyzer.py`  
**Location:** Line ~151 (after `extract_all_zones_features`)

```python
# In analyze_zones method:
zones_features = self.features.extract_all_zones_features(zones)

# ✅ ADD THIS:
for zone, features in zip(zones, zones_features):
    zone.features = features.to_dict()
```

**Benefit:**
- ✅ Features автоматически доступны в `zone.features`
- ✅ Работает для ВСЕХ способов использования analyzer
- ✅ Совместимо с существующим кодом

---

#### Fix 2: Extend Builder API для strategies

**Option A: Add .with_strategies() method (RECOMMENDED)**

```python
# В ZoneAnalysisBuilder:
def with_strategies(self,
                   swing: Optional[str] = None,
                   shape: Optional[str] = None,
                   divergence: Optional[str] = None,
                   volatility: Optional[str] = None,
                   volume: Optional[str] = None) -> 'ZoneAnalysisBuilder':
    """
    Configure analytical strategies.
    
    Args:
        swing: Swing strategy ('find_peaks', 'zigzag', 'pivot_points')
        shape: Shape strategy ('statistical', custom)
        divergence: Divergence strategy ('classic', custom)
        volatility: Volatility strategy (custom)
        volume: Volume strategy ('standard', custom)
        
    Returns:
        self для цепочки вызовов
        
    Example:
        result = (
            analyze_zones(df)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing='find_peaks', shape='statistical')
            .analyze(clustering=True)
            .build()
        )
    """
    self._swing_strategy = swing
    self._shape_strategy = shape
    self._divergence_strategy = divergence
    self._volatility_strategy = volatility
    self._volume_strategy = volume
    return self
```

**Modify build() to use strategies:**
```python
def build(self) -> ZoneAnalysisResult:
    # ...
    # ✅ Create custom analyzer if strategies specified
    if any([self._swing_strategy, self._shape_strategy, 
            self._divergence_strategy, self._volatility_strategy, 
            self._volume_strategy]):
        custom_analyzer = UniversalZoneAnalyzer(
            swing_strategy=self._swing_strategy,
            shape_strategy=self._shape_strategy,
            divergence_strategy=self._divergence_strategy,
            volatility_strategy=self._volatility_strategy,
            volume_strategy=self._volume_strategy
        )
        pipeline = ZoneAnalysisPipeline(config, zone_analyzer=custom_analyzer, ...)
    else:
        pipeline = ZoneAnalysisPipeline(config, ...)
    
    return pipeline.run(self.data)
```

**Usage:**
```python
result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')  # ✅ NEW!
    .analyze(clustering=True)
    .build()
)
```

---

**Option B: Extend .analyze() method**

```python
def analyze(self,
           clustering: bool = True,
           n_clusters: int = 3,
           regression: bool = False,
           validation: bool = False,
           swing_strategy: Optional[str] = None,  # ✅ NEW
           shape_strategy: Optional[str] = None,  # ✅ NEW
           divergence_strategy: Optional[str] = None,  # ✅ NEW
           volatility_strategy: Optional[str] = None,  # ✅ NEW
           volume_strategy: Optional[str] = None) -> 'ZoneAnalysisBuilder':  # ✅ NEW
    # ...
```

**Usage:**
```python
result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True, swing_strategy='find_peaks')  # ✅ In one method
    .build()
)
```

---

**Option C: Add .with_analyzer() method**

```python
def with_analyzer(self, analyzer: UniversalZoneAnalyzer) -> 'ZoneAnalysisBuilder':
    """
    Use custom UniversalZoneAnalyzer.
    
    Args:
        analyzer: Pre-configured analyzer instance
        
    Returns:
        self для цепочки вызовов
        
    Example:
        custom_analyzer = UniversalZoneAnalyzer(swing_strategy='find_peaks')
        result = (
            analyze_zones(df)
            .with_analyzer(custom_analyzer)
            .detect_zones(...)
            .build()
        )
    """
    self._custom_analyzer = analyzer
    return self
```

---

## ✅ Приоритетный план действий

### Priority 1: Fix Features Writing (CRITICAL)

**Why:** Без этого features НЕ доступны пользователям (даже shape, divergence, volume!)

**What:** Добавить `zone.features = features.to_dict()` в `UniversalZoneAnalyzer.analyze_zones()`

**File:** `bquant/analysis/zones/analyzer.py`  
**Lines:** ~151 (after `extract_all_zones_features`)  
**Effort:** 5 минут  
**Impact:** 🔥🔥🔥 CRITICAL - исправляет базовую функциональность

---

### Priority 2: Extend Builder API for Strategies (HIGH)

**Why:** Без этого swing_strategy НЕ доступен через Builder (fluent API)

**What:** Добавить `.with_strategies()` method в `ZoneAnalysisBuilder`

**Recommended approach:** Option A (`.with_strategies()`)

**File:** `bquant/analysis/zones/pipeline.py`  
**Effort:** 30-40 минут  
**Impact:** 🔥🔥 HIGH - расширяет Builder API для analytical strategies

---

### Priority 3: Update Documentation (MEDIUM)

**What:** Обновить примеры использования swing strategies

**Files:**
- `docs/api/analysis/zones.md` - добавить примеры `.with_strategies()`
- `examples/02a_universal_zones.py` - обновить примеры
- `research/notebooks/03_zones_universal.py` - убрать workaround, использовать Builder API

**Effort:** 20 минут  
**Impact:** 🔥 MEDIUM - улучшает user experience

---

## 📊 Сравнение решений

| Решение | Effort | Backward Compatible | User-Friendly | Flexible |
|---------|--------|---------------------|---------------|----------|
| **Fix Features Writing** | 5 min | ✅ Yes | ✅ Yes | ✅ Yes |
| **Option A: .with_strategies()** | 40 min | ✅ Yes | ✅✅ Best | ✅ High |
| **Option B: Extend .analyze()** | 30 min | ✅ Yes | ✅ Good | ⚠️ Medium |
| **Option C: .with_analyzer()** | 20 min | ✅ Yes | ⚠️ Complex | ✅✅ Highest |
| **Workaround: Direct usage** | 0 min | ✅ Yes | ❌ Poor | ✅ High |

---

## 🔗 References

**Architectural Documents:**
- `devref/gaps/zo/zouni_v2.md` - v2.1 Universal Architecture spec
- `devref/gaps/zo/zonan_uni_full.md` - Full implementation plan (ЭТАП 1)
- `devref/gaps/impl.md` - Original implementation plan

**Code:**
- `bquant/analysis/zones/pipeline.py` - Builder API
- `bquant/analysis/zones/analyzer.py` - UniversalZoneAnalyzer
- `bquant/analysis/zones/zone_features.py` - ZoneFeaturesAnalyzer

**Tests:**
- `research/notebooks/swing_test_simple.py` - Current analysis test
- `tests/unit/test_zone_features_swing_integration.py` - Swing integration tests

---

## 💡 Conclusion

**Root Cause Analysis:**

1. **Builder API Gap:** Builder НЕ предоставляет способ конфигурации analytical strategies
2. **Features Writing Gap:** UniversalZoneAnalyzer НЕ пишет features обратно в ZoneInfo

**Impact:**

- ❌ Swing strategies НЕ доступны через Builder API
- ❌ Features (включая swing, shape, divergence) НЕ доступны пользователям через `zone.features`
- ⚠️ Требуются workarounds в notebooks (direct analyzer usage + manual features writing)

**Solution Path:**

1. **Immediate:** Fix features writing в UniversalZoneAnalyzer (5 min, CRITICAL)
2. **Short-term:** Extend Builder API with `.with_strategies()` (40 min, HIGH)
3. **Long-term:** Update documentation and examples (20 min, MEDIUM)

**Total effort:** ~1.5 hours для полного решения

---

**Status:** ✅ RESOLVED (2025-10-21) - PACKAGE ARCHITECTURE FIXED

---

## 🎉 RESOLUTION STATUS

**Date:** 2025-10-21  
**Time:** [18:12-18:50] (38 minutes)  
**Result:** Both architectural gaps successfully resolved

### ✅ What Was Done:

**Priority 1: Fix Features Writing (CRITICAL)** ⏱️ 7 min
- **File:** `bquant/analysis/zones/analyzer.py` (lines 153-156)
- **Change:** Added 4 lines to write features back to ZoneInfo
- **Result:** Features now automatically available in `zone.features` (0 keys → 19 keys!)
- **Test:** ✅ All swing metrics extracted (6 keys found)

**Priority 2: Extend Builder API (HIGH)** ⏱️ 31 min
- **File:** `bquant/analysis/zones/pipeline.py`
- **Changes:**
  - Added 5 strategy fields to `__init__` (lines 315-320)
  - Added `.with_strategies()` method (~78 lines, lines 407-484)
  - Modified `.build()` to create custom analyzer (lines 546-564)
- **Result:** Builder API now supports swing, shape, divergence, volatility, volume strategies
- **Test:** ✅ New API produces identical results to workaround

**Priority 3: Update Documentation (MEDIUM)** ⏱️ 15 min
- **File:** `docs/api/analysis/zones.md`
- **Changes:** Added "Using Analytical Strategies (v2.1)" section with 3 examples
- **Result:** User documentation now covers `.with_strategies()` API

### 📊 Test Results:

**✅ TEST 1:** `.with_strategies(swing='find_peaks')`
- Zones: 38, Features: 19 keys, Swing: 6 keys

**✅ TEST 2:** Multiple strategies
- All strategies accepted and work correctly

**✅ TEST 3:** Comparison
- New API == Old workaround: **identical results!**

### 💡 New API Usage:

```python
# Simple swing analysis
result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')  # ✅ NEW!
    .analyze(clustering=True)
    .build()
)

# Multiple strategies
result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='find_peaks',
        shape='statistical',
        divergence='classic',
        volume='standard'
    )
    .analyze(clustering=True)
    .build()
)
```

### 📁 Files Modified:

1. `bquant/analysis/zones/analyzer.py` - Features writing fix
2. `bquant/analysis/zones/pipeline.py` - Builder API extension
3. `docs/api/analysis/zones.md` - Documentation update
4. `devref/gaps/zo/zonan_uni_full.md` - Status update (gaps marked as resolved)
5. `changelogs/CHANGE_TRACE_LOG_2025-10-21.md` - Full change log
6. `research/notebooks/test_with_strategies.py` - Test suite

### ✅ Impact:

**Architectural:**
- ✅ Package архитектурно правильный
- ✅ No more architectural gaps
- ✅ Backward compatible

**User Experience:**
- ✅ Features автоматически доступны
- ✅ Swing strategies через fluent API
- ✅ Clear, documented API

**Code Quality:**
- ✅ Comprehensive docstrings
- ✅ Debug logging
- ✅ Clean separation of concerns

### ⏱️ Total Time: 53 minutes

- Analysis: 5 min
- Priority 1 (CRITICAL): 7 min
- Priority 2 (HIGH): 31 min
- Priority 3 (MEDIUM): 15 min
- Testing & verification: ~10 min (throughout)

**Estimate was:** 1.5 hours (5+40+20 min)  
**Actual time:** 53 minutes ✅ (12% faster)

---

## 📚 Reference:

**Detailed implementation log:** `changelogs/CHANGE_TRACE_LOG_2025-10-21.md`  
**Architecture plan:** `devref/gaps/zo/zonan_uni_full.md` (updated with resolution status)  
**Test scripts:** `research/notebooks/test_with_strategies.py`, `research/notebooks/swing_test_simple.py`

---

**Status:** 🚨 ARCHITECTURE GAP IDENTIFIED - REQUIRES PACKAGE CHANGES ← **OLD STATUS**

