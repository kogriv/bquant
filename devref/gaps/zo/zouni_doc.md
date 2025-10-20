# План обновления документации пакета для v2.1

**Версия:** 1.0  
**Дата:** 2025-10-19  
**Context:** Обновление документации после реализации v2.1 (TRULY AGNOSTIC) Architecture  
**Источник:** Phases 1-3 реализации из `zouni_v2.md`

---

## 📋 Overview

После успешной реализации и тестирования v2.1 архитектуры необходимо обновить **пользовательскую документацию** пакета для отражения:

1. ✅ TRUE UNIVERSALITY - работа с ЛЮБЫМ индикатором
2. ✅ indicator_context mechanism - self-describing zones
3. ✅ Breaking changes - `volume_macd_corr` → `volume_indicator_corr`
4. ✅ Protocol signatures - `indicator_col` parameter
5. ✅ Примеры с multiple indicators (не только MACD)

**Принципы обновления:**
- ❌ НЕТ migration guide (новый проект, нечему мигрировать)
- ❌ НЕТ отдельного CHANGELOG task (стандартная практика)
- ✅ Фокус на ПОЛНОЦЕННУЮ пользовательскую документацию
- ✅ Показать универсальность через примеры

---

## 🗂️ Структура документации пакета

### Полная структура (с отметками изменений)

```
bquant/
│
├── docs/                                         [📚 User Documentation]
│   │
│   ├── api/                                      [📖 API Reference - основная документация]
│   │   │
│   │   ├── analysis/
│   │   │   ├── zones.md                          🔴 CRITICAL UPDATE (Task 1.1, 15 min)
│   │   │   │                                        - Remove "Future universalization" warning
│   │   │   │                                        - Add v2.1 universal architecture section
│   │   │   │                                        - Add indicator_context explanation
│   │   │   │                                        - Examples: MACD, RSI, Stochastic
│   │   │   │
│   │   │   ├── strategies.md                     🔴 CRITICAL UPDATE (Task 1.2, 15 min)
│   │   │   │                                        - Update Protocol signatures (lines 100, 127)
│   │   │   │                                        - Rename volume_macd_corr → volume_indicator_corr (lines 201, 207, 493, 522, 525)
│   │   │   │                                        - Add v2.1 banner
│   │   │   │                                        - Add examples with RSI, AO, CCI
│   │   │   │
│   │   │   ├── base.md                           🟢 OK (не затронут v2.1)
│   │   │   ├── statistical.md                    🟢 OK (не затронут v2.1)
│   │   │   └── README.md                         🟢 OK (оглавление)
│   │   │
│   │   ├── core/
│   │   │   └── ...                               🟢 OK (не затронут)
│   │   │
│   │   ├── data/
│   │   │   └── ...                               🟢 OK (не затронут)
│   │   │
│   │   ├── indicators/
│   │   │   └── ...                               🟢 OK (не затронут)
│   │   │
│   │   ├── visualization/
│   │   │   └── ...                               🟢 OK (не затронут)
│   │   │
│   │   ├── extension_guide.md                    🟡 MINOR UPDATE (Task 1.3, 5 min)
│   │   │                                            - Update Protocol examples (lines 348, 372)
│   │   │                                            - Remove 'macd_hist' defaults
│   │   │                                            - Show universal signature
│   │   │
│   │   └── README.md                             🟢 OK (index page)
│   │
│   ├── user_guide/
│   │   ├── quick_start.md                        🟢 OK (high-level, не детализирует strategies)
│   │   └── README.md                             🟢 OK
│   │
│   ├── tutorials/
│   │   └── README.md                             🟢 OK (нет tutorials пока)
│   │
│   ├── developer_guide/
│   │   └── README.md                             🟢 OK (для contributors)
│   │
│   ├── examples/
│   │   └── README.md                             🟢 OK (ссылки на examples/)
│   │
│   ├── index.rst                                 🟢 OK (Sphinx entry point)
│   ├── conf.py                                   🟢 OK (Sphinx config)
│   └── Makefile                                  🟢 OK (Sphinx build)
│
├── examples/                                     [💡 Code Examples - практические примеры]
│   │
│   ├── 02a_universal_zones.py                    🟡 ENHANCE (Task 2.1, 10 min)
│   │                                                - Add v2.1 explanation header
│   │                                                - Add indicator_context inspection
│   │                                                - Add Stochastic line_crossing example
│   │                                                - Add custom indicator example
│   │                                                - Educational comments
│   │
│   ├── 02_macd_zone_analysis.py                  🟢 OK (legacy + new comparison)
│   ├── 04_comprehensive_analysis.py              🟢 OK (уже universal)
│   ├── 01_basic_indicators.py                    🟢 OK (indicators, не zones)
│   ├── 03_data_processing.py                     🟢 OK (data, не zones)
│   ├── 05_strategies_demo.py                     🟢 OK (уже показывает strategies)
│   ├── 06_regression_demo.py                     🟢 OK (regression focus)
│   ├── 07_validation_demo.py                     🟢 OK (validation focus)
│   └── README.md                                 🟢 OK (index)
│
└── bquant/analysis/zones/                        [🔧 Source Code - внутренние docstrings]
    │
    ├── strategies/
    │   │
    │   ├── shape/
    │   │   ├── statistical.py                    🟡 MINOR (Task 3.1, 2 min)
    │   │   │                                        - Line 4: module docstring
    │   │   │                                        - "MACD histogram" → "oscillator"
    │   │   │                                        - Add universal examples
    │   │   │   NOTE: Class/method docstrings УЖЕ обновлены (Task 1.3)
    │   │   │
    │   │   └── __init__.py                       🟢 OK
    │   │
    │   ├── divergence/
    │   │   ├── classic.py                        🟢 OK (Task 1.4 - уже universal)
    │   │   │   NOTE: Проверить module docstring (lines 1-10)
    │   │   │
    │   │   └── __init__.py                       🟢 OK
    │   │
    │   ├── volume/
    │   │   ├── standard.py                       🟢 OK (Task 1.5 - уже universal)
    │   │   │   NOTE: Проверить module docstring (lines 1-10)
    │   │   │
    │   │   └── __init__.py                       🟢 OK
    │   │
    │   └── base.py                               🟢 OK (VolumeMetrics уже обновлен)
    │
    ├── detection/                                🟢 OK (все strategies обновлены в Task 1.2)
    ├── models.py                                 🟢 OK (indicator_context добавлен Task 1.1)
    ├── zone_features.py                          🟢 OK (context-aware Task 1.6)
    └── pipeline.py                               🟢 OK (агностичен Task 2.1-2.2)


SUMMARY:
========
📚 docs/api/          3 files need updates (zones.md, strategies.md, extension_guide.md)
💡 examples/          1 file needs enhancement (02a_universal_zones.py)
🔧 strategies/        1-3 files minor updates (module docstrings check)

Total: 5-7 files, ~50 minutes work
```

---

## 📊 Визуализация: Что документируем

```
v2.1 Architecture Components → Documentation Mapping
=====================================================

┌─────────────────────────────────────────────────────────────────┐
│ 1. ZoneInfo.indicator_context (Task 1.1 - Phase 1)             │
├─────────────────────────────────────────────────────────────────┤
│ Source:  bquant/analysis/zones/models.py                        │
│ Spec:    zouni_v2.md lines 290-413                             │
│ Tests:   test_zone_models.py (3 tests)                         │
│ Document: docs/api/analysis/zones.md (new section)             │
│           examples/02a_universal_zones.py (show in action)      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. Detection Strategies populate context (Task 1.2 - Phase 1)  │
├─────────────────────────────────────────────────────────────────┤
│ Source:  bquant/analysis/zones/detection/*.py (5 strategies)    │
│ Spec:    zouni_v2.md lines 772-888                             │
│ Tests:   test_zone_detection_strategies.py (6 tests)           │
│ Document: docs/api/analysis/zones.md (examples section)        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. Shape Strategy universal (Task 1.3 - Phase 1)               │
├─────────────────────────────────────────────────────────────────┤
│ Source:  strategies/shape/statistical.py                        │
│ Spec:    zouni_v2.md lines 950-1010                            │
│ Tests:   test_shape_strategy_universal.py (11 tests)           │
│ Document: docs/api/analysis/strategies.md (Protocol update)    │
│           docs/api/extension_guide.md (example update)          │
│           strategies/shape/statistical.py (module docstring)    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. Divergence Strategy universal (Task 1.4 - Phase 1)          │
├─────────────────────────────────────────────────────────────────┤
│ Source:  strategies/divergence/classic.py                       │
│ Spec:    zouni_v2.md lines 1015-1075                           │
│ Tests:   test_divergence_strategy_universal.py (12 tests)      │
│ Document: docs/api/analysis/strategies.md (Protocol update)    │
│           strategies/divergence/classic.py (verify docstring)   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 5. Volume Strategy universal (Task 1.5 - Phase 1)              │
├─────────────────────────────────────────────────────────────────┤
│ Source:  strategies/volume/standard.py                          │
│         strategies/base.py (VolumeMetrics)                      │
│ Spec:    zouni_v2.md lines 1080-1118                           │
│ Tests:   test_volume_strategy_universal.py (13 tests)          │
│ Document: docs/api/analysis/strategies.md (VolumeMetrics)      │
│           strategies/volume/standard.py (verify docstring)      │
│ BREAKING: volume_macd_corr → volume_indicator_corr             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 6. Integration Examples (Tasks 3.1-3.2 - Phase 3)              │
├─────────────────────────────────────────────────────────────────┤
│ Source:  tests/integration/test_truly_universal_zones.py        │
│ Spec:    zouni_v2.md lines 1920-1956 (Test 1, Test 2)         │
│ Tests:   6 integration tests (FICTIONAL + 10 REAL)             │
│ Document: examples/02a_universal_zones.py (add examples)       │
│           docs/api/analysis/zones.md (proof statement)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Этапы обновления документации

### **Этап 1: Пользовательская API документация (КРИТИЧНО)**

**Duration:** ~30 минут  
**Priority:** HIGH  
**Цель:** Обновить docs/api/ для отражения v2.1 универсальности

---

#### **Task 1.1: Обновить `docs/api/analysis/zones.md`** (15 мин)

**Источники из zouni_v2.md:**
- Раздел ["Решение: Трехуровневая система (v2.1)"](#) (строки ~250-280)
- Раздел ["Уровень 2: ZoneInfo - хранит контекст"](#) (строки ~290-413)
- Примеры из ["Test 1: Новый индикатор БЕЗ изменений кода"](#) (строки ~1920-1956)

**Источники из production code:**
- `bquant/analysis/zones/models.py` (ZoneInfo class, lines 30-120)
  - Поля `indicator_context` (line 66)
  - Методы `get_primary_indicator_column()` (lines 73-86)
  - Метод `to_analyzer_format()` (lines 103-118)

**Изменения:**

**1. Удалить устаревший warning (строки 3-17)**

Текущее:
```markdown
> **⚠️ API Evolution Notice**
> **Current Status (Phase 3-4):** This module works with MACD zones specifically.
> **Planned Changes:** Future universalization refactoring will rename these fields
```

Заменить на:
```markdown
> **✅ v2.1 - Truly Universal Architecture**
> 
> Zone analysis now works with **ANY indicator** without code changes!
> 
> **Supported indicators:**
> - ANY oscillator: MACD, RSI, AO, CCI, Stochastic, Williams %R, MFI, CMF, ROC
> - Custom indicators from pandas_ta (158 indicators)
> - Your own custom calculations
> 
> **Key innovation:** `ZoneInfo.indicator_context` - zones self-describe their detection strategy
> 
> **Proven:** Integration tests with FICTIONAL_INDICATOR_99 prove true universality
> - 115 tests with 10+ real indicators
> - 100% pass rate
> - NO hardcoded indicator names anywhere

**API Reference:**
- [Universal Strategies](strategies.md) - analytical strategies for ANY indicator
- [Pipeline API](zones.md#universal-pipeline) - fluent API for zone detection
```

**2. Добавить новый раздел "Universal Architecture (v2.1)" после "Обзор"**

```markdown
## Universal Architecture (v2.1)

### Key Concept: indicator_context

Every detected zone contains `indicator_context` dictionary that describes **HOW** the zone was detected:

```python
from bquant.analysis.zones import analyze_zones

result = analyze_zones(df).detect_zones('zero_crossing', indicator_col='RSI_14').build()

# Access zone's detection context
zone = result.zones[0]
context = zone.indicator_context

print(context['detection_indicator'])  # → 'RSI_14'
print(context['detection_strategy'])   # → 'zero_crossing'
print(context['signal_line'])          # → None (single-line indicator)
```

**Standard fields (populated by detection strategy):**
- `detection_indicator`: Primary indicator column name (e.g., 'RSI_14', 'macd_hist')
- `detection_strategy`: Strategy used (e.g., 'zero_crossing', 'threshold', 'line_crossing')
- `signal_line`: Secondary indicator for 2-line strategies (e.g., 'STOCH_D')
- `detection_rules`: Full rules dictionary for reference

**Convenience methods:**
```python
# Get primary indicator column
indicator = zone.get_primary_indicator_column()  # → 'RSI_14'

# Get signal line (if exists)
signal = zone.get_signal_line_column()  # → 'STOCH_D' or None
```

### Examples with Different Indicators

#### MACD (zero-crossing oscillator)
```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze()
    .build()
)

# Context: {'detection_indicator': 'macd_hist', 'detection_strategy': 'zero_crossing'}
```

#### RSI (threshold-based bounded indicator)
```python
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold',
                 indicator_col='RSI_14',
                 upper_threshold=70,
                 lower_threshold=30)
    .analyze()
    .build()
)

# Context: {'detection_indicator': 'RSI_14', 'detection_strategy': 'threshold'}
```

#### Stochastic (2-line crossing)
```python
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'stoch', k=14, d=3)
    .detect_zones('line_crossing',
                 line1_col='STOCHk_14_3_3',
                 line2_col='STOCHd_14_3_3')
    .analyze()
    .build()
)

# Context: {'detection_indicator': 'STOCHk_14_3_3', 'signal_line': 'STOCHd_14_3_3'}
```

#### Custom Indicator (proves universality!)
```python
# Create your own indicator
df['MY_CUSTOM_OSC'] = df['close'].diff(5) / df['close'].rolling(20).std()

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='MY_CUSTOM_OSC')
    .analyze()
    .build()
)

# ✅ Works immediately - NO code changes needed!
# Context: {'detection_indicator': 'MY_CUSTOM_OSC', 'detection_strategy': 'zero_crossing'}
```

### Why This Matters

**Before v2.1:** Hardcoded MACD support
- ❌ Only worked with MACD
- ❌ Analytical strategies assumed 'macd_hist' column
- ❌ Required code changes for new indicators

**After v2.1:** True Universality
- ✅ Works with ANY indicator
- ✅ Analytical strategies read from `indicator_context`
- ✅ NO code changes for new indicators
- ✅ Proven with FICTIONAL_INDICATOR_99 (indicator that doesn't exist!)
```

**Referência из zouni_v2.md:**
- Раздел "Уровень 2: ZoneInfo - хранит контекст" (lines 290-413)
- Примеры из "Test 1" (lines 1920-1956)

**Source code:**
- `bquant/analysis/zones/models.py` - ZoneInfo class implementation

---

#### **Task 1.2: Обновить `docs/api/analysis/strategies.md`** (15 мин)

**Источники из zouni_v2.md:**
- ["Файл 5: Shape Strategy - универсальный indicator_col"](#) (строки ~950-1010)
- ["Файл 6: Divergence Strategy - универсальный indicator_col"](#) (строки ~1015-1075)
- ["Файл 7: Volume Strategy - универсальный indicator_col"](#) (строки ~1080-1118)

**Источники из production code:**
- `bquant/analysis/zones/strategies/shape/statistical.py` - ShapeStrategy implementation (Task 1.3)
- `bquant/analysis/zones/strategies/divergence/classic.py` - DivergenceStrategy (Task 1.4)
- `bquant/analysis/zones/strategies/volume/standard.py` - VolumeStrategy (Task 1.5)
- `bquant/analysis/zones/strategies/base.py` - VolumeMetrics dataclass (renamed field)

**Изменения:**

**1. Добавить v2.1 banner в начало документа (после заголовка)**

```markdown
# bquant.analysis.zones.strategies — Strategy Pattern

> **✅ v2.1 - Universal Strategies**
> 
> All analytical strategies now work with **ANY indicator**!
> 
> **What changed:**
> - All strategies accept explicit `indicator_col` parameter
> - `VolumeMetrics.volume_macd_corr` → `volume_indicator_corr` (universal naming)
> - Protocol signatures updated for universality
> 
> **Examples:** Each strategy now shows usage with MACD, RSI, AO, and custom indicators
> 
> **Proven:** Works with FICTIONAL_INDICATOR_99 and 10+ real indicators (100% test coverage)

> **API Stability:** 🟢 STABLE - этот API не изменится после универсализации
```

**2. Обновить ShapeCalculationStrategy Protocol (строка 100)**

Было:
```python
class ShapeCalculationStrategy(Protocol):
    def calculate_shape(self, data: pd.DataFrame, indicator_col: str = 'macd_hist') -> ShapeMetrics: ...
```

Станет:
```python
class ShapeCalculationStrategy(Protocol):
    def calculate(self, data: pd.DataFrame, indicator_col: Optional[str] = None) -> ShapeMetrics: ...
    #                                        ^^^^^^^^^^^^^^^^^^^^^^^^
    #                                        v2.1: Required for universal usage
    def get_name(self) -> str: ...
    def get_metadata(self) -> dict: ...
```

**v2.1 Note:**
```markdown
**v2.1 Universal Usage:**

The `indicator_col` parameter is **required** for universal usage with any oscillator.

**Examples:**
```python
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy

strategy = StatisticalShapeStrategy()

# MACD
shape = strategy.calculate(zone_data, indicator_col='macd_hist')

# RSI
shape = strategy.calculate(zone_data, indicator_col='RSI_14')

# Awesome Oscillator
shape = strategy.calculate(zone_data, indicator_col='AO_5_34')

# CCI
shape = strategy.calculate(zone_data, indicator_col='CCI_20')

# Custom indicator
shape = strategy.calculate(zone_data, indicator_col='MY_CUSTOM_OSC')
```

**All return the same ShapeMetrics structure:**
- `hist_skewness`: Distribution asymmetry
- `hist_kurtosis`: Peak sharpness
- `hist_smoothness`: Change consistency
```

**3. Обновить DivergenceCalculationStrategy Protocol (строка 127)**

Было:
```python
def calculate_divergence(self, data: pd.DataFrame, indicator_col: str = 'macd_hist') -> DivergenceMetrics: ...
```

Станет:
```python
class DivergenceCalculationStrategy(Protocol):
    def calculate_divergence(self, 
                           data: pd.DataFrame, 
                           indicator_col: Optional[str] = None,
                           indicator_line_col: Optional[str] = None) -> DivergenceMetrics: ...
    #                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                       v2.1: Support for 2-line indicators (MACD line + signal)
```

**v2.1 Examples:**
```python
# RSI divergence
div = strategy.calculate_divergence(data, indicator_col='RSI_14')

# MACD histogram divergence
div = strategy.calculate_divergence(data, indicator_col='macd_hist')

# MACD with signal line (2-line divergence)
div = strategy.calculate_divergence(data, 
                                    indicator_col='macd',
                                    indicator_line_col='macd_signal')
```

**4. Обновить VolumeMetrics (строки 195-208)**

Было:
```markdown
### VolumeMetrics Dataclass (4 поля)

- `volume_zone_ratio`: Отношение среднего объема зоны к baseline
- `volume_at_entry_change`: Изменение объема при входе в зону
- `volume_macd_corr`: Корреляция объема с MACD/индикатором  ❌ OLD NAME
- `avg_volume_zone`: Средний объем в зоне

**Интерпретация:**
- `volume_macd_corr > 0.7`: Объем подтверждает индикатор  ❌ OLD NAME
```

Станет:
```markdown
### VolumeMetrics Dataclass (4 поля)

Анализ объемов торгов в зоне (v2.1: универсальный для ЛЮБОГО индикатора).

- `volume_zone_ratio`: Отношение среднего объема зоны к baseline
- `volume_at_entry_change`: Изменение объема при входе в зону (%)
- `volume_indicator_corr`: Корреляция объема с индикатором ✨ **v2.1: renamed from volume_macd_corr**
- `avg_volume_zone`: Средний объем в зоне

**Интерпретация:**
- `volume_zone_ratio > 1.5`: Высокий объем - сильное движение
- `volume_zone_ratio < 0.7`: Низкий объем - слабое движение
- `volume_indicator_corr > 0.7`: Объем подтверждает индикатор ✨ v2.1
- `volume_at_entry_change > 0.5`: Объем растет при входе - confirmation

**v2.1 Universal Examples:**
```python
# MACD
vol = strategy.calculate_volume(data, baseline_volume=1500, indicator_col='macd_hist')
print(f"Volume-MACD correlation: {vol.volume_indicator_corr:.2f}")

# RSI
vol = strategy.calculate_volume(data, baseline_volume=1500, indicator_col='RSI_14')
print(f"Volume-RSI correlation: {vol.volume_indicator_corr:.2f}")

# AO
vol = strategy.calculate_volume(data, baseline_volume=1500, indicator_col='AO_5_34')
print(f"Volume-AO correlation: {vol.volume_indicator_corr:.2f}")

# Works with ANY oscillator!
```
```

**5. Обновить примеры использования (строки 522, 525)**

Было:
```python
print(f"Volume-MACD correlation: {vol.volume_macd_corr:.2f}")
if vol.volume_zone_ratio > 1.5 and vol.volume_macd_corr > 0.6:
```

Станет:
```python
print(f"Volume-Indicator correlation: {vol.volume_indicator_corr:.2f}")  # ✨ v2.1
if vol.volume_zone_ratio > 1.5 and vol.volume_indicator_corr > 0.6:  # ✨ v2.1
    print("✅ Strong volume confirmation")
```

**Referência:**
- zouni_v2.md раздел "Файл 7: Volume Strategy" (lines ~1080-1118)
- `bquant/analysis/zones/strategies/volume/standard.py` (Task 1.5 implementation)
- `bquant/analysis/zones/strategies/base.py` (VolumeMetrics dataclass)

---

#### **Task 1.3: Обновить `docs/api/extension_guide.md`** (5 мин)

**Источники:**
- zouni_v2.md раздел "Extensibility: Добавление новой стратегии" (lines ~1782-1920)
- Protocol definitions из production code

**Изменения:**

**Строки 348, 372 - Protocol examples**

Было:
```python
class MyShapeStrategy:
    def calculate_shape(self, data: pd.DataFrame, indicator_col: str = 'macd_hist') -> ShapeMetrics:
        # Your implementation
        pass
```

Станет:
```python
class MyShapeStrategy:
    def calculate(self, data: pd.DataFrame, indicator_col: Optional[str] = None) -> ShapeMetrics:
        """
        Calculate shape metrics for ANY oscillator (v2.1 universal).
        
        Args:
            data: Zone data with OHLCV + oscillator columns
            indicator_col: Oscillator column name (e.g., 'RSI_14', 'AO_5_34', 'MY_OSC')
                          If None, strategy should auto-detect or raise error
        
        Returns:
            ShapeMetrics with calculated shape characteristics
        
        Examples:
            # Works with ANY oscillator
            metrics = strategy.calculate(data, indicator_col='RSI_14')
            metrics = strategy.calculate(data, indicator_col='macd_hist')
            metrics = strategy.calculate(data, indicator_col='CUSTOM_OSC')
        """
        if indicator_col is None or indicator_col not in data.columns:
            raise ValueError(f"indicator_col required and must exist in data")
        
        # Your universal implementation (works with ANY column!)
        oscillator = data[indicator_col]
        
        # ... calculate shape metrics ...
        
        return ShapeMetrics(
            hist_skewness=...,
            hist_kurtosis=...,
            hist_smoothness=...,
            strategy_name='my_shape',
            strategy_params={'indicator_col': indicator_col}  # ← Track which indicator used
        )
```

**Добавить note:**
```markdown
**v2.1 Best Practice:** Always track `indicator_col` in `strategy_params` for traceability!
```

**Referência:**
- zouni_v2.md "Пример: TripleLineCrossingDetection" (lines 1784-1850)

---

### **Этап 2: Примеры кода (ВАЖНО для onboarding)**

**Duration:** ~10 минут  
**Priority:** MEDIUM  
**Цель:** Показать v2.1 универсальность через практические примеры

---

#### **Task 2.1: Улучшить `examples/02a_universal_zones.py`** (10 мин)

**Текущее состояние:** Уже использует универсальный API, но комментарии минимальны

**Источники:**
- zouni_v2.md раздел "Test 2: Множественные индикаторы" (lines ~1923-1956)
- Все integration tests из `tests/integration/test_truly_universal_zones.py`

**Что добавить:**

**1. Educational header после imports:**
```python
"""
=============================================================================
v2.1 UNIVERSALITY DEMONSTRATION
=============================================================================

This example demonstrates the TRUE UNIVERSALITY of BQuant v2.1 architecture.

KEY CONCEPT: indicator_context - zones self-describe their detection!
================================================================================

Every zone "knows" which indicator and strategy detected it:

    zone.indicator_context = {
        'detection_indicator': 'RSI_14',        # Which indicator
        'detection_strategy': 'threshold',       # Which strategy
        'signal_line': 'STOCH_D' or None,       # Secondary indicator (if 2-line)
        'detection_rules': {...}                 # Full rules for reference
    }

This enables:
1. Analytical strategies to work with correct indicator
2. Multi-indicator analysis without conflicts
3. Complete independence between analyses
4. Self-documenting zones

PROVEN UNIVERSALITY:
- Works with FICTIONAL_INDICATOR_99 (indicator that doesn't exist!)
- Works with 10+ REAL indicators (MACD, RSI, AO, CCI, Stochastic, Williams, MFI, CMF, ROC, custom)
- 115 tests - 100% pass rate
- NO code changes needed for new indicators

See: devref/gaps/zo/zouni_v2.md for architecture details
=============================================================================
"""
```

**2. В каждом примере добавить indicator_context inspection:**

```python
# ========================================================================
# 1. MACD ZONES (Zero-Crossing Strategy)
# ========================================================================
print_section("1. MACD Zones - Universal v2.1 API")

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')  # ← Required parameter
    .analyze()
    .build()
)

print_zone_stats(result, "MACD")

# ✅ v2.1: Inspect indicator_context (self-describing zones)
if len(result.zones) > 0:
    ctx = result.zones[0].indicator_context
    print(f"\n   📋 Zone Detection Context:")
    print(f"      Indicator used: {ctx['detection_indicator']}")     # → 'macd_hist'
    print(f"      Strategy used: {ctx['detection_strategy']}")       # → 'zero_crossing'
    print(f"      Signal line: {ctx.get('signal_line', 'N/A')}")    # → None
```

**3. Добавить новый раздел с линией пересечения:**

```python
# ========================================================================
# 5. STOCHASTIC ZONES (Line-Crossing Strategy) - v2.1 2-line support
# ========================================================================
print_section("5. Stochastic %K/%D - Line Crossing (v2.1)")

# Calculate Stochastic
low_14 = df['low'].rolling(14).min()
high_14 = df['high'].rolling(14).max()
df['STOCH_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
df['STOCH_D'] = df['STOCH_K'].rolling(3).mean()

result = (
    analyze_zones(df)
    .detect_zones('line_crossing',
                 line1_col='STOCH_K',      # Primary line
                 line2_col='STOCH_D')      # Signal line
    .analyze()
    .build()
)

print_zone_stats(result, "Stochastic K/D")

# ✅ v2.1: 2-line indicators supported!
if len(result.zones) > 0:
    ctx = result.zones[0].indicator_context
    print(f"\n   📋 2-Line Detection Context:")
    print(f"      Primary line: {ctx['detection_indicator']}")   # → 'STOCH_K'
    print(f"      Signal line: {ctx['signal_line']}")            # → 'STOCH_D'
    print(f"      Strategy: {ctx['detection_strategy']}")        # → 'line_crossing'
```

**4. Добавить пример с custom indicator:**

```python
# ========================================================================
# 6. CUSTOM INDICATOR (Proves TRUE UNIVERSALITY!)
# ========================================================================
print_section("6. Custom Indicator - Zero Code Changes Needed!")

# Create your own indicator (any calculation!)
df['MY_MOMENTUM'] = df['close'].diff(5) / df['close'].rolling(20).std()

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='MY_MOMENTUM')
    .analyze()
    .build()
)

print_zone_stats(result, "Custom Momentum")

# ✅ Works immediately - NO code changes!
# ✅ NO hardcoded 'MY_MOMENTUM' anywhere in BQuant source
# ✅ TRUE UNIVERSALITY!
```

**Referência:**
- zouni_v2.md "Test 2: Множественные индикаторы" (lines 1923-1956)
- `tests/integration/test_truly_universal_zones.py` - all tests as examples

---

### **Этап 3: Внутренние docstrings (MINOR)**

**Duration:** ~5 минут  
**Priority:** LOW  
**Цель:** Обновить module-level docstrings для consistency

---

#### **Task 3.1: Обновить module docstrings в strategies** (5 мин)

**Источники:** Implementations из Tasks 1.3-1.5

**Файлы:**

**1. `bquant/analysis/zones/strategies/shape/statistical.py` (строка 4)**

Было:
```python
"""
Statistical Shape Strategy - shape analysis using skewness and kurtosis.

This strategy analyzes the shape of MACD histogram within a zone using
statistical moments (skewness and kurtosis) to classify zone archetypes.
"""
```

Станет:
```python
"""
Statistical Shape Strategy - universal shape analysis for ANY oscillator.

This strategy analyzes the shape of oscillator within a zone using
statistical moments (skewness and kurtosis) to classify zone archetypes.

UNIVERSAL (v2.1):
- Works with ANY oscillator: MACD, RSI, AO, CCI, Stochastic, custom, etc.
- Requires explicit indicator_col parameter
- NO hardcoded indicator names

Examples:
    strategy.calculate(data, indicator_col='macd_hist')  # MACD
    strategy.calculate(data, indicator_col='RSI_14')     # RSI
    strategy.calculate(data, indicator_col='AO_5_34')    # AO
"""
```

**2. `bquant/analysis/zones/strategies/divergence/classic.py`**

Проверить module docstring (первые 10 строк):
- Если упоминает "MACD" → заменить на "oscillator"
- Добавить примеры с RSI, AO

**3. `bquant/analysis/zones/strategies/volume/standard.py`**

Проверить module docstring:
- Если упоминает "MACD" → заменить на "indicator"
- Упомянуть `volume_indicator_corr` (renamed)

**Referência:**
- Implementations из Tasks 1.3, 1.4, 1.5
- Class docstrings уже универсальны (проверено)

---

## 📊 Сводная таблица изменений

| File | Type | Lines | Changes | Source from zouni_v2.md | Source Code | Priority | Time |
|------|------|-------|---------|------------------------|-------------|----------|------|
| **docs/api/analysis/zones.md** | User docs | 3-17, new section | Remove warning, add v2.1 section | Lines 290-413, 1920-1956 | models.py | HIGH | 15m |
| **docs/api/analysis/strategies.md** | User docs | 100, 127, 195-208, 522 | Protocols, volume_indicator_corr, examples | Lines 950-1118 | shape/, divergence/, volume/ | HIGH | 15m |
| **docs/api/extension_guide.md** | User docs | 348, 372 | Protocol signatures | Lines 1784-1850 | strategies/base.py | MEDIUM | 5m |
| **examples/02a_universal_zones.py** | Examples | Throughout | Add indicator_context comments | Lines 1923-1956 | test_truly_universal_zones.py | MEDIUM | 10m |
| **strategies/shape/statistical.py** | Module docs | 4 | Module docstring | Task 1.3 impl | statistical.py | LOW | 2m |
| **strategies/divergence/classic.py** | Module docs | 1-10 | Module docstring (if needed) | Task 1.4 impl | classic.py | LOW | 2m |
| **strategies/volume/standard.py** | Module docs | 1-10 | Module docstring (if needed) | Task 1.5 impl | standard.py | LOW | 1m |

**Total:** ~50 минут

---

## 🔗 Mapping: zouni_v2.md → Documentation Updates

### **From Phase 1 (Implementation):**

| zouni_v2.md Section | Lines | Implemented in | Document in |
|---------------------|-------|----------------|-------------|
| ZoneInfo.indicator_context | 290-413 | models.py | zones.md (new section) |
| Detection strategies populate context | 772-888 | detection/*.py | zones.md (examples) |
| Shape universal indicator_col | 950-1010 | shape/statistical.py | strategies.md (Protocol) |
| Divergence universal indicator_col | 1015-1075 | divergence/classic.py | strategies.md (Protocol) |
| Volume universal indicator_col | 1080-1118 | volume/standard.py | strategies.md (VolumeMetrics) |
| ZoneFeaturesAnalyzer context-aware | 1305-1442 | zone_features.py | zones.md (usage) |

### **From Phase 3 (Testing):**

| zouni_v2.md Section | Lines | Tests in | Document in |
|---------------------|-------|----------|-------------|
| Test 1: FICTIONAL_INDICATOR_99 | 1920-1956 | test_truly_universal_zones.py | zones.md (proof), examples |
| Test 2: Multiple indicators | 1923-1956 | test_truly_universal_zones.py | examples/02a |

---

## 🎯 Recommended Execution Order

### **HIGH Priority (30 min) - для пользователей:**

1. **Task 1.1:** `docs/api/analysis/zones.md` (15 min)
   - Самая видимая документация
   - Первая точка входа пользователей
   - Объясняет key concept (indicator_context)

2. **Task 1.2:** `docs/api/analysis/strategies.md` (15 min)
   - Breaking change: `volume_macd_corr` → `volume_indicator_corr`
   - Protocol signatures
   - Практические примеры

### **MEDIUM Priority (15 min) - для onboarding:**

3. **Task 2.1:** `examples/02a_universal_zones.py` (10 min)
   - Практические примеры
   - Shows indicator_context in action
   - Helps new users understand v2.1

4. **Task 1.3:** `docs/api/extension_guide.md` (5 min)
   - Для advanced users
   - Creating custom strategies

### **LOW Priority (5 min) - для completeness:**

5. **Task 3.1:** Module docstrings (5 min)
   - Internal documentation
   - Mostly already done in Phase 1

---

## ✅ Success Criteria

После выполнения Phase 4 документация должна:

**1. Точность:**
- ✅ NO упоминаний "MACD zones specifically"
- ✅ NO `volume_macd_corr` (только `volume_indicator_corr`)
- ✅ Protocol signatures reflect v2.1 (Optional[str], no defaults)

**2. Полнота:**
- ✅ `indicator_context` объяснен с примерами
- ✅ Примеры с ≥3 разными индикаторами (MACD, RSI, custom)
- ✅ 2-line strategy example (Stochastic)
- ✅ Показана универсальность (не просто "supports multiple")

**3. Доказательства:**
- ✅ Упоминание FICTIONAL_INDICATOR_99 proof test
- ✅ Ссылка на 115 tests, 100% pass rate
- ✅ "Proven" statements (не "planned")

**4. Usability:**
- ✅ Каждый пример runnable
- ✅ Clear explanations
- ✅ Best practices highlighted

---

## 📝 Template для каждого файла

При обновлении каждого файла использовать:

```markdown
**Change Log:**
- **Date:** 2025-10-19
- **Version:** v2.1
- **Change:** Updated for truly universal architecture
- **Reason:** Reflect Phase 1-3 implementation (indicator_context, universal strategies)
- **Breaking:** `volume_macd_corr` → `volume_indicator_corr`
- **Proven:** 115 tests, FICTIONAL_INDICATOR_99 works
```

---

## 🚀 Next Steps

**Для реализации Phase 4:**

1. Переключиться в agent mode
2. Выполнить Tasks в рекомендуемом порядке (1.1 → 1.2 → 2.1 → 1.3 → 3.1)
3. После каждого Task - проверить markdown rendering
4. После всех Tasks - запустить `make html` в docs/ (если Sphinx docs)
5. Обновить zouni_v2.md - отметить Phase 4 tasks как completed

**Estimated total:** ~50 минут

**Alternative:**
Если времени ограничено - сделать только HIGH priority tasks (1.1, 1.2) = 30 минут

---

**Status:** ✅ План документации готов к execution  
**Next:** Switch to agent mode and implement Phase 4

