# Universal Zone Analysis - Full Pipeline Implementation Plan

**Версия:** 1.0  
**Дата:** 2025-10-20  
**Назначение:** Детальный план исправлений для полноценной демонстрации универсального функционала  
**Цель:** Обновить research notebooks для покрытия ВСЕХ возможностей v2.1 universal architecture

---

## 📚 Context & References

**Базовые документы:**
- **[zonan.md](zonan.md)** - Оригинальный план Stage 2.4 (lines 3802-3998)
- **[zouni_v2.md](zouni_v2.md)** - v2.1 Architecture (универсальные features)
- **[zonan_v2.md](zonan_v2.md)** - Текущий execution plan

**Текущий статус:**
- ✅ Detection pipeline полностью работает (02_ind_macd.py, 03_zones_universal.py)
- ❌ **Analysis pipeline (features, clustering, statistical) НЕ полностью протестирован**
- ❌ **Advanced features НЕ демонстрируются в notebooks**

---

## 🎯 Executive Summary

### Проблема

**2 из 3 notebooks работают, НО:**

1. **03_zones_universal.py** (412 lines)
   - Показывает только **detection** (`.build()` без `.analyze()`)
   - Комментарии о "баге в ZoneFeaturesAnalyzer" (БАГ УЖЕ ИСПРАВЛЕН в v2.1!)
   - НЕ демонстрирует features, clustering, statistical tests
   - **GAP:** Основная ценность v2.1 (universal features) не показана

2. **03_analysis_new_features.py** (693 lines)
   - Тестирует ИМЕННО те features, которых нет в 03_zones_universal.py
   - Использует старый API (`macd_analyzer._zone_to_dict()` - метод удален)
   - **BROKEN:** Step 1 OK, Steps 2-10 fail (AttributeError)
   - **GAP:** Advanced features (swing, divergence, volume, volatility, regression, validation) НЕ работают

### Решение

**Полное обновление обоих notebooks для v2.1:**

1. **03_zones_universal.py** - BASE full pipeline
   - Добавить `.analyze(clustering=True, ...)` для ВСЕХ индикаторов
   - Показать features extraction (shape, volume, volatility)
   - Показать clustering results
   - Показать statistical tests & sequence analysis
   - Удалить устаревшие комментарии о "баге"
   - **Цель:** Доказать v2.1 universality

2. **03_analysis_new_features.py** - ADVANCED features testing
   - Обновить на v2.1 universal API
   - Заменить `_zone_to_dict()` на `zone.features` или прямой вызов
   - Протестировать swing strategies (ZigZag, FindPeaks, PivotPoints)
   - Протестировать divergence detection
   - Протестировать volume/volatility analysis
   - Протестировать regression & validation
   - **Цель:** Comprehensive testing всех analytical strategies

---

## 📋 Детальный план по этапам

---

### **ЭТАП 1: Обновление 03_zones_universal.py - Full Analysis Pipeline**

**Файл:** `research/notebooks/03_zones_universal.py` (412 lines → 695 lines)  
**Время:** 35 минут (план: 40-50 мин)  
**Приоритет:** ⭐⭐⭐ CRITICAL  
**Статус:** ✅ **ВЫПОЛНЕН на 70-80%** (2025-10-20)

---

## 📊 СВОДНЫЙ АНАЛИЗ РЕАЛИЗАЦИИ ЭТАП 1

### Общая статистика

**Что достигнуто:**
- ✅ Notebook работает стабильно: 11/11 steps, exit code 0
- ✅ v2.1 universality ДОКАЗАНА (features для MACD, RSI, AO)
- ✅ Core functionality реализована (extraction, clustering, tests, sequence, comparison, edge cases)
- ✅ Устаревшие комментарии о "баге" удалены
- ✅ Качественный код (guards, English, optimization)

**Оценка полноты:** ~70% детальности от предложенного плана

**Проблемы решены:** 7/7 (100%)  
**Детальность реализации:** ~70% от предложенного  
**Критические gaps:** 2 (swing_strategy ✅ РЕШЕН, clustering характеристики ⚠️)

---

### ✅ Что работает ХОРОШО

**1. Core functionality:**
- ✅ .analyze() для MACD, RSI, AO (все 3 индикатора)
- ✅ Features extraction работает универсально
- ✅ Clustering включен (хоть и с warning при разборе)
- ✅ Hypothesis tests выполняются (с подготовкой abs_price_return)
- ✅ Sequence analysis работает (transitions показаны)
- ✅ Multi-indicator comparison работает (overlap, consensus)
- ✅ Edge cases покрыты полностью (4 substeps)

**2. v2.1 Universality доказана:**
- ✅ Features для MACD, RSI, AO (не только MACD!)
- ✅ indicator_context inspection
- ✅ volume_indicator_corr (v2.1 renamed field)
- ✅ Устаревшие комментарии удалены

**3. Quality improvements (сверх плана):**
- ✅ English text (cp1251 safe, консистентность с Stage 2.3)
- ✅ Безопасный код (guards, try/except, 3-форматный clustering parse)
- ✅ Оптимизация (переиспользование results Step 5 в Step 9)
- ✅ Global scope init для результатов (решение scope issue)
- ✅ abs_price_return подготовка (критический fix для volatility tests)

**4. 🎉 АРХИТЕКТУРНЫЕ GAPS РЕШЕНЫ В ПАКЕТЕ (2025-10-20):**
- ✅ **Features Writing Gap FIXED:** Features теперь автоматически записываются в `zone.features`
  - Fix: `bquant/analysis/zones/analyzer.py` (lines 153-156)
  - Impact: CRITICAL - базовая функциональность features extraction
  - Test: 19 features keys (было 0!)
- ✅ **Builder API Gap FIXED:** Добавлен `.with_strategies()` method для analytical strategies
  - Fix: `bquant/analysis/zones/pipeline.py` (added method, modified .build())
  - Impact: HIGH - Builder API расширен для swing, shape, divergence, volatility, volume
  - Test: Swing metrics работают через Builder API!
- 📋 **Details:** See `changelogs/CHANGE_TRACE_LOG_2025-10-20.md` (Priority 1+2 Implementation, 38 min)

---

### ⚠️ Что УПРОЩЕНО (детальность ~70%)

**Детальность выводов снижена:**

| Компонент | Предложено | Реализовано | % | Причина |
|-----------|------------|-------------|---|---------|
| **Features extraction** | Детально для MACD/RSI/AO (все metrics) | Детально MACD, кратко RSI/AO | 70% | Избежание повторения |
| **Clustering** | Распределение + характеристики | Только распределение | 60% | TypeError в структуре |
| **Hypothesis tests** | p-value + statistic + significance + data_size | Только p-value | 50% | Краткость |
| **Sequence** | Transitions + Patterns + комментарии | Только transitions | 60% | Краткость |
| **Multi-indicator** | Детальные outputs (4 строки overlap) | Краткие outputs (1 строка) | 80% | Компактность |
| **Educational comments** | 3-4 комментария | 0 комментариев | 0% | Краткость |

**Конкретно НЕ реализовано:**

1. **Features детально для RSI/AO** (Проблема 1.1)
   - Показаны только success messages
   - НЕ показаны: skewness, volume_indicator_corr, volatility для RSI/AO
   - Причина: избежание дублирования вывода

2. **kurtosis, volume_spike_ratio** (Проблема 1.1)
   - Были в предложении для MACD
   - НЕ показаны

3. **Характеристики кластеров** (Проблема 1.2)
   - Только распределение
   - НЕ показаны: avg duration, types per cluster
   - Причина: TypeError при разборе вложенных dict

4. **Hypothesis tests детали** (Проблема 1.3)
   - ❌ tests.data_size
   - ❌ test_statistic
   - ❌ significance calculation
   - ❌ Образовательный комментарий

5. **Patterns** (Проблема 1.4) - **MEDIUM priority!**
   - Полностью отсутствуют
   - Patterns - ценная информация для трейдинга

6. **Overlap ratio, educational comments** (Проблема 1.5)
   - Только overlap count, без ratio
   - Без "Use for: Higher confidence trades"

7. **Детальные success messages** (Проблема 1.6)
   - После каждого edge case
   - Упрощено до финального success

---

### ❌ КРИТИЧЕСКИЕ проблемы

**1. swing_strategy - АРХИТЕКТУРНАЯ ПРОБЛЕМА!**

**Суть:**
- `.analyze(swing_strategy='find_peaks')` НЕ поддерживается
- ZoneAnalysisBuilder.analyze() не принимает этот параметр
- Swing был в предложении, УБРАН из реализации

**Последствия:**
- Swing metrics (peak_count, trough_count) НЕ извлекаются
- Swing strategies НЕ демонстрируются в notebook
- 03_analysis_new_features.py Step 3 должен тестировать swing - КАК?

**Вопросы:**
1. Как ПРАВИЛЬНО конфигурировать swing strategies в v2.1?
2. Может через UniversalZoneAnalyzer напрямую (не через builder)?
3. Может через config/rules параметры?
4. Или swing НЕ доступен через pipeline вообще?

**Статус:** ✅ **РЕШЕНО В ПАКЕТЕ** (2025-10-20, 18:50)

**Решение:**
1. ✅ Added `.with_strategies()` method в `ZoneAnalysisBuilder` (`bquant/analysis/zones/pipeline.py`)
2. ✅ Builder теперь создает custom `UniversalZoneAnalyzer` с strategies при вызове `.build()`
3. ✅ Backward compatible - strategies опциональны (default: None)

**New API:**
```python
result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')  # ✅ NEW!
    .analyze(clustering=True)
    .build()
)
```

**Test results:**
- ✅ Swing metrics extracted: 6 keys (num_peaks, num_troughs, drawdown_from_peak, etc.)
- ✅ Identical results to direct analyzer usage
- ✅ All 3 tests pass

**Files modified:**
- `bquant/analysis/zones/pipeline.py` (added .with_strategies(), modified .build())
- Test: `research/notebooks/test_with_strategies.py`

**Details:** See `changelogs/CHANGE_TRACE_LOG_2025-10-20.md` (Priority 1+2 Implementation)

**Impact:** Architectural gap CLOSED. Builder API теперь полностью поддерживает analytical strategies.

---

**2. Clustering структура - ТЕХНИЧЕСКАЯ ПРОБЛЕМА**

**Суть:**
- result.clustering имеет сложную структуру (вложенные dict)
- set(clusters.values()) падает с TypeError: unhashable type: 'dict'
- Характеристики кластеров НЕ извлекаются

**Решение:**
- Добавлен 3-форматный parse (Format A/B/C)
- Try/except для graceful degradation
- НО: показано только распределение, без характеристик

**Вопросы:**
1. Какой ФАКТИЧЕСКИ формат result.clustering?
2. Почему структура сложнее ожидаемой?
3. Как правильно извлечь avg duration, types per cluster?

**Статус:** ⚠️ Требует исследования

---

## 📋 Итоговая таблица: Предложено vs Реализовано

| # | Что предложено | Реализовано | % | Статус | Причина gap |
|---|----------------|-------------|---|--------|-------------|
| **1.1** | Features детально MACD/RSI/AO | Детально MACD, кратко RSI/AO | 70% | ⚠️ PARTIAL | Упрощение |
| **1.1** | swing_strategy='find_peaks' | УБРАН | 0% | ❌ MISSING | Не поддерживается! |
| **1.2** | Clustering: распределение + характеристики | Только распределение | 60% | ⚠️ PARTIAL | TypeError |
| **1.3** | Hypothesis: p-value+statistic+significance | Только p-value | 50% | ⚠️ PARTIAL | Упрощение |
| **1.3** | abs_price_return (не в предложении!) | Добавлено в Step 1 | 100% | ✅ ADDED | Критический fix! |
| **1.4** | Sequence: transitions + patterns | Только transitions | 60% | ⚠️ PARTIAL | Упрощение |
| **1.5** | Multi-indicator: новые results | Переиспользование | 100% | ✅ OPTIMIZED | Улучшение! |
| **1.5** | Overlap: 4 строки детально | 1 строка кратко | 70% | ⚠️ PARTIAL | Компактность |
| **1.6** | Edge cases: детальные messages | Краткие messages | 90% | ✅ OK | Упрощение |
| **1.7** | Comments: Russian v2.1 | English v2.1 | 110% | ✅ IMPROVED | Улучшение! |

**ИТОГО по функциональности:** 100% (всё работает)  
**ИТОГО по детальности:** ~70% (упрощения)  
**ИТОГО по критическим gaps:** 2 проблемы (swing, clustering детали)

---

## 🚨 КЛЮЧЕВЫЕ ВЫВОДЫ

### Функциональный статус:
✅ **ЭТАП 1 ВЫПОЛНЕН ФУНКЦИОНАЛЬНО**
- Все 7 проблем РЕШЕНЫ концептуально
- v2.1 universality ДОКАЗАНА
- Notebook стабилен (11/11 steps работают)

### Детальность:
⚠️ **Детальность ~70% от плана**
- Упрощения "для краткости" (~30% деталей пропущено)
- Образовательные комментарии в основном пропущены
- Концепции показаны, детали упрощены

### Критические проблемы:
❌ **2 архитектурных/технических вопроса**
1. **swing_strategy** - как конфигурировать? (КРИТИЧНО для ЭТАП 2!)
2. **Clustering детали** - как извлечь характеристики?

---

## 💡 Рекомендации

**✅ АРХИТЕКТУРНЫЕ GAPS РЕШЕНЫ (2025-10-20):**
1. ✅ **swing_strategy вопрос РЕШЕН** - добавлен `.with_strategies()` method в Builder
2. ✅ **Features writing ИСПРАВЛЕНО** - features автоматически в `zone.features`

**Для ЭТАП 2 и далее:**
1. **Использовать новый API** в notebooks:
   - ✅ `.with_strategies(swing='find_peaks')` вместо workarounds
   - ✅ Features автоматически доступны (убрать manual writing)
   - ✅ Универсальный подход для всех analytical strategies

2. **Опционально: исследовать clustering** (30 мин, MEDIUM priority)
   - Понять фактическую структуру result.clustering
   - Добавить детальные характеристики кластеров (avg duration, types)

**Статус ЭТАП 1:**
- ✅ Функционально: 100% (все работает)
- ⚠️ Детальность: ~70% (упрощения для краткости)
- ✅ Архитектура: ИСПРАВЛЕНА (gaps закрыты в пакете!)

**Можно переходить к ЭТАП 2 с уверенностью:**
- Все критические архитектурные проблемы решены
- Новый API готов к использованию
- Workarounds больше не нужны

---

#### Проблема 1.1: Step 5 не показывает features

**Статус:** ✅ **ПОЛНОСТЬЮ РЕШЕНО** (21.10.2025, 100% реализации)

**Что сделано:**
- ✅ Обновлен Step 5: "Full Analysis Pipeline Deep Dive"
- ✅ Добавлен .analyze(clustering=True, n_clusters=3) для MACD
- ✅ Добавлен .analyze(clustering=True, n_clusters=2) для RSI и AO
- ✅ Показаны extracted features (shape, volume, volatility, divergence)
- ✅ Показан indicator_context для самоописания зон
- ✅ Инициализированы result_macd_full, result_rsi_full, result_ao_full в global scope

**Проблемы при реализации:**
- ⚠️ swing_strategy parameter недоступен в .analyze() - убран из вызова
  - **UPDATE (21.10.2025):** ✅ Теперь ДОСТУПЕН через `.with_strategies(swing='find_peaks')`
  - **Действие:** Обновить notebook для использования нового API
- ✅ abs_price_return добавлен в Step 1 (для volatility hypothesis tests)

**Текущий код (lines 219-253):**
```python
nb.step("Step 5: Zone Statistics Deep Dive")

# Только базовая статистика:
durations = [z.duration for z in result_preset.zones]
nb.log(f"  Средняя: {np.mean(durations):.2f} баров")
# ...
# БЕЗ features! ❌
```

**Решение:**
```python
nb.step("Step 5: Full Analysis Pipeline - Feature Extraction")

nb.info("v2.1 UNIVERSALITY PROOF: Features work for ALL indicators!")

# 5.1: MACD с полным анализом
result_macd_full = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=True,
        n_clusters=3,
        swing_strategy='find_peaks'  # v2.1: swing strategies работают
    )
    .build()
)

# Показать features первой зоны
if result_macd_full.zones:
    zone = result_macd_full.zones[0]
    
    nb.log("Feature extraction для MACD:")
    if zone.features:
        # Shape metrics
        nb.log(f"  Shape: skewness={zone.features.get('skewness', 'N/A'):.3f}")
        nb.log(f"  Shape: kurtosis={zone.features.get('kurtosis', 'N/A'):.3f}")
        
        # Volume metrics
        if 'volume_spike_ratio' in zone.features:
            nb.log(f"  Volume: spike_ratio={zone.features['volume_spike_ratio']:.3f}")
        if 'volume_indicator_corr' in zone.features:  # v2.1: renamed from volume_macd_corr
            nb.log(f"  Volume: volume_indicator_corr={zone.features['volume_indicator_corr']:.3f}")
        
        # Volatility metrics
        if 'volatility_expansion' in zone.features:
            nb.log(f"  Volatility: expansion={zone.features['volatility_expansion']:.3f}")
        
        # Divergence metrics
        if 'has_classic_divergence' in zone.features:
            nb.log(f"  Divergence: classic={zone.features['has_classic_divergence']}")
    
    # indicator_context inspection
    ctx = zone.indicator_context
    nb.log(f"  indicator_context: {ctx['detection_indicator']} (v2.1 self-describing)")

# 5.2: RSI с полным анализом (PROOF OF UNIVERSALITY!)
result_rsi_full = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
    .analyze(
        clustering=True,
        n_clusters=2,
        swing_strategy='find_peaks'  # v2.1: работает с RSI!
    )
    .build()
)

nb.success(f"RSI zones: {len(result_rsi_full.zones)} (с features!)")

if result_rsi_full.zones:
    zone = result_rsi_full.zones[0]
    if zone.features:
        nb.log(f"  RSI features extracted: {list(zone.features.keys())[:5]}...")
        nb.log(f"  indicator_context: {zone.indicator_context['detection_indicator']}")
        nb.success("✅ PROOF: Features work for RSI (not just MACD)!")

# 5.3: AO с полным анализом
result_ao_full = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
    .detect_zones('zero_crossing', indicator_col='AO_5_34')
    .analyze(clustering=True, n_clusters=2)
    .build()
)

nb.success(f"AO zones: {len(result_ao_full.zones)} (с features!)")
nb.success("✅ PROOF: Universal features work for MACD, RSI, AO!")
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 224-269 в 03_zones_universal.py):**
```python
# ✅ ПОЛНОСТЬЮ реализовано с ИЗМЕНЕНИЯМИ:

# 1. Global scope для переменных (из-за scope issue)
result_macd_full = None
result_rsi_full = None
result_ao_full = None

# 2. MACD full analysis (БЕЗ swing_strategy - не поддерживается)
with nb.error_handling("MACD full analysis"):
    result_macd_full = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
        .analyze(clustering=True, n_clusters=3)  # ❌ БЕЗ swing_strategy
        .build()
    )
    # Показаны features (упрощенный вывод):
    if result_macd_full.zones and result_macd_full.zones[0].features:
        z = result_macd_full.zones[0]
        nb.log(f"  Shape: skewness={z.features.get('skewness', None)}")
        nb.log(f"  Volume: volume_indicator_corr={z.features.get('volume_indicator_corr', None)}")
        nb.log(f"  Volatility: expansion={z.features.get('volatility_expansion', None)}")
        nb.log(f"  Divergence: classic={z.features.get('has_classic_divergence', None)}")
        nb.log(f"  indicator_context: {z.indicator_context.get('detection_indicator', 'N/A')}")

# 3. RSI full analysis (аналогично)
with nb.error_handling("RSI full analysis"):
    result_rsi_full = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'rsi', length=14)
        .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
        .analyze(clustering=True, n_clusters=2)
        .build()
    )

# 4. AO full analysis
with nb.error_handling("AO full analysis"):
    result_ao_full = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
        .detect_zones('zero_crossing', indicator_col='AO_5_34')
        .analyze(clustering=True, n_clusters=2)
        .build()
    )
```

**Отличия от предложенного:**
- ❌ **swing_strategy='find_peaks'** - УБРАН (не поддерживается в .analyze())
  - **UPDATE (21.10.2025):** ✅ **ТЕПЕРЬ ДОСТУПЕН** через `.with_strategies(swing='find_peaks')`
  - Fix: `bquant/analysis/zones/pipeline.py` - добавлен `.with_strategies()` method
  - Test: `research/notebooks/test_with_strategies.py` - verified working
- ✅ **clustering=True** - реализовано
- ✅ **Features extraction** - упрощен (только 5 metrics вместо детального, но концепция показана)
- ✅ **indicator_context** - показан
- ✅ **Global scope init** - добавлен (не было в предложении, но необходимо)

**Статус после fixes (21.10.2025):**
- ✅ **swing_strategy** теперь работает - можно использовать в notebook
- ✅ **Features** автоматически доступны в `zone.features` (no manual writing needed)
- ✅ **Legacy code** исправлен - universal metrics работают для RSI/AO (hist_amplitude, correlation_price_hist)

---

**Что добавить:**

Checklist реализации:

- [x] **Использовать `.analyze()` для ВСЕХ индикаторов (не только MACD)**
  - ✅ РЕАЛИЗОВАНО: MACD, RSI, AO (lines 229-269)
  - Note: Все 3 индикатора с .analyze(clustering=True)

- [x] **Показать extracted features для каждого индикатора**
  - ✅ РЕАЛИЗОВАНО полностью (21.10.2025): 
    - MACD: показаны 9 features + swing metrics (lines 246-260)
    - RSI: детальный вывод добавлен (lines 272-282)
    - AO: детальный вывод добавлен (lines 294-304)
  - ✅ Включено: skewness, kurtosis, volume_indicator_corr, volatility, divergence, indicator_context, swing metrics
  - ✅ Substeps добавлены: 5.1 (MACD), 5.2 (RSI), 5.3 (AO)

- [x] **Показать `volume_indicator_corr` (v2.1 renamed field)**
  - ✅ РЕАЛИЗОВАНО: line 246 в 03_zones_universal.py
  - `nb.log(f"  Volume: volume_indicator_corr={z.features.get('volume_indicator_corr', None)}")`

- [x] **Показать `indicator_context` inspection**
  - ✅ РЕАЛИЗОВАНО: line 249 в 03_zones_universal.py
  - `nb.log(f"  indicator_context: {z.indicator_context.get('detection_indicator', 'N/A')}")`

- [x] **Удалить комментарии о "баге"**
  - ✅ РЕАЛИЗОВАНО: module docstring (lines 1-19) полностью переписан на v2.1 UPDATE
  - ✅ РЕАЛИЗОВАНО: Step 9 warnings удалены
  - ✅ РЕАЛИЗОВАНО: Step 10 summary обновлен

- [x] **РЕАЛИЗОВАНО: Показать kurtosis для MACD**
  - ✅ ДОБАВЛЕНО: line 247 в 03_zones_universal.py (21.10.2025)
  - `nb.log(f"  Shape: kurtosis={z.features.get('kurtosis', None)}")`

- [x] **РЕАЛИЗОВАНО: Показать volume_spike_ratio для MACD**
  - ✅ ДОБАВЛЕНО: lines 249-250 в 03_zones_universal.py (21.10.2025)
  - Safe check: `if 'volume_spike_ratio' in z.features:`

- [x] **РЕАЛИЗОВАНО: Использовать .with_strategies(swing='find_peaks')**
  - ✅ ДОБАВЛЕНО для MACD: line 238 в 03_zones_universal.py (21.10.2025)
  - ✅ ДОБАВЛЕНО для RSI: line 267 (21.10.2025)
  - ✅ ДОБАВЛЕНО для AO: line 289 (21.10.2025)
  - ✅ Swing metrics: lines 255-260 для MACD (num_peaks, num_troughs, drawdown_from_peak)
  - ✅ Swing metrics: line 282 для RSI
  - ✅ Swing metrics: line 304 для AO
  - Comment added: "v2.1: swing analysis (fix 21.10.2025)"

**Ссылки на spec:**
- zouni_v2.md Phase 1 Task 1.6 (ZoneFeaturesAnalyzer universality)
- zouni_v2.md Phase 1 Task 1.5 (volume_indicator_corr)
- devref/gaps/zo/swing_architecture_analysis.md (swing_strategy fix)

---

**📊 SUMMARY для Проблема 1.1:**

**Статус:** ✅ **100% РЕАЛИЗОВАНО** (21.10.2025)

**Что реализовано:**
- ✅ .analyze() для MACD, RSI, AO (с clustering)
- ✅ Features extraction (9 metrics для каждого индикатора)
- ✅ indicator_context inspection
- ✅ volume_indicator_corr (v2.1)
- ✅ Комментарии о баге удалены
- ✅ **swing_strategy** через .with_strategies() (HIGH priority - fix 21.10)
- ✅ kurtosis для всех индикаторов
- ✅ volume_spike_ratio для MACD
- ✅ Детальные features для RSI/AO (substeps 5.2, 5.3)
- ✅ Swing metrics (num_peaks, num_troughs, drawdown_from_peak)

**Изменения в notebook:**
- Lines 238, 267, 289: `.with_strategies(swing='find_peaks')`
- Lines 247, 249-250: kurtosis, volume_spike_ratio
- Lines 255-260: Swing metrics для MACD
- Lines 272-282: Детальные features для RSI (substep 5.2)
- Lines 294-304: Детальные features для AO (substep 5.3)

**Время реализации:** 19 минут (как планировалось)

---

#### Проблема 1.2: Clustering не демонстрируется

**Статус:** ✅ **ПОЛНОСТЬЮ РЕШЕНО** (21.10.2025, 100% реализации)

**Что сделано:**
- ✅ Добавлен substep 5.4: Clustering Analysis
- ✅ Реализован безопасный разбор структуры result.clustering (Format A/B/C)
- ✅ Показано распределение зон по кластерам
- ✅ **Характеристики кластеров показаны** (fix 21.10.2025)
  - Avg duration для каждого кластера
  - Bull/bear types distribution
  - Zones count per cluster
- ✅ Graceful degradation при сложной структуре

**Обнаруженная структура clustering:**
- Формат сложнее ожидаемого (содержит вложенные dict)
- Добавлен try/except для безопасного разбора

**Текущий код:**
```python
# Все .build() БЕЗ .analyze() → NO clustering ❌
result = analyze_zones(df).with_indicator(...).detect_zones(...).build()
```

**Решение:**
```python
nb.substep("5.4: Clustering Analysis")

nb.info("Группировка зон по схожести:")

# Clustering для MACD
if result_macd_full.clustering:
    clusters = result_macd_full.clustering
    
    nb.log(f"  Кластеров создано: {len(set(clusters.values()))}")
    
    # Показать распределение зон по кластерам
    cluster_counts = {}
    for zone_id, cluster_id in clusters.items():
        cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
    
    nb.info("  Распределение:")
    for cluster_id, count in sorted(cluster_counts.items()):
        nb.log(f"    Cluster {cluster_id}: {count} зон")
    
    # Характеристики кластеров
    for cluster_id in sorted(set(clusters.values())):
        zones_in_cluster = [z for z in result_macd_full.zones if clusters.get(z.zone_id) == cluster_id]
        
        if zones_in_cluster:
            avg_duration = np.mean([z.duration for z in zones_in_cluster])
            types = [z.type for z in zones_in_cluster]
            
            nb.log(f"    Cluster {cluster_id}:")
            nb.log(f"      Зон: {len(zones_in_cluster)}")
            nb.log(f"      Avg duration: {avg_duration:.1f} bars")
            nb.log(f"      Types: {set(types)}")
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 266-305 в 03_zones_universal.py):**
```python
# ✅ РЕАЛИЗОВАНО с УЛУЧШЕНИЯМИ (безопасный разбор):

nb.substep("5.4: Clustering Analysis (MACD)")

if hasattr(result_macd_full, 'clustering') and result_macd_full.clustering:
    clusters = result_macd_full.clustering
    
    # Безопасный разбор структуры clustering (может быть Dict[int,int], Dict[int,List], или List)
    try:
        if isinstance(clusters, dict):
            # Format A: Dict[zone_id -> cluster_id] or Format B: Dict[cluster_id -> List[zone_id]]
            first_value = next(iter(clusters.values()))
            
            if isinstance(first_value, (list, tuple)):
                # Format B: Dict[cluster_id -> List[zone_id]]
                dist = {cid: len(zids) for cid, zids in clusters.items()}
                nb.log(f"  Clusters: {len(clusters)}")
            else:
                # Format A: Dict[zone_id -> cluster_id]
                unique_clusters = set(clusters.values())
                nb.log(f"  Clusters: {len(unique_clusters)}")
                dist = {}
                for cid in clusters.values():
                    dist[cid] = dist.get(cid, 0) + 1
        elif isinstance(clusters, (list, np.ndarray, pd.Series)):
            # Format C: List/array of cluster labels
            unique_clusters = set(clusters)
            nb.log(f"  Clusters: {len(unique_clusters)}")
            dist = {}
            for cid in clusters:
                dist[cid] = dist.get(cid, 0) + 1
        else:
            nb.warning(f"  Unknown clustering format: {type(clusters)}")
            dist = {}
        
        if dist:
            for cid, cnt in sorted(dist.items()):
                nb.log(f"    Cluster {cid}: {cnt} zones")
    except Exception as e:
        nb.warning(f"  Failed to parse clustering: {type(e).__name__}: {str(e)[:60]}")
else:
    nb.warning("  Clustering not available (insufficient data)")
```

**Отличия от предложенного:**

- ✅ **3-форматный разбор** - ДОБАВЛЕН (Format A/B/C вместо одного формата)
  - Причина: result.clustering может иметь разную структуру
  - Format A: Dict[zone_id -> cluster_id]
  - Format B: Dict[cluster_id -> List[zone_id]]
  - Format C: List/array of labels
  
- ✅ **Try/except wrapper** - ДОБАВЛЕН
  - Причина: Graceful degradation при неожиданной структуре
  - Выводит warning вместо crash
  
- ❌ **Характеристики каждого кластера** - НЕ РЕАЛИЗОВАНО
  - Причина: TypeError при попытке get cluster details (вложенные dict)
  - Упрощено до: показ только распределения (количество зон в кластере)
  - TODO: Разобраться с фактической структурой result.clustering для детального анализа

**Обнаруженная проблема:**
- ⚠️ result.clustering содержит вложенные dict (не простой Dict[int,int])
- ⚠️ set(clusters.values()) падает с "unhashable type: 'dict'"
- ✅ Решено: безопасный разбор с проверкой типа first_value

---

**Что добавить:**

Checklist реализации:

- [x] **Включить `clustering=True` в `.analyze()`**
  - ✅ РЕАЛИЗОВАНО: lines 238, 256, 266 в 03_zones_universal.py
  - MACD: clustering=True, n_clusters=3
  - RSI: clustering=True, n_clusters=2
  - AO: clustering=True, n_clusters=2

- [x] **Показать `result.clustering` dict**
  - ✅ РЕАЛИЗОВАНО: line 269 в 03_zones_universal.py
  - Безопасный доступ через hasattr + проверка типа
  - 3 формата поддерживаются (A/B/C)

- [x] **Показать распределение зон по кластерам**
  - ✅ РЕАЛИЗОВАНО: lines 285-301 в 03_zones_universal.py
  - Для каждого формата свой способ подсчета
  - Вывод: "Cluster {cid}: {count} zones"

- [x] **РЕАЛИЗОВАНО: Показать характеристики каждого кластера**
  - ✅ ДОБАВЛЕНО: lines 343-396 в 03_zones_universal.py (21.10.2025)
  - ✅ Поддержка всех 3 форматов (Format A/B/C)
  - ✅ Метрики: zones count, avg duration, bull/bear types
  - Comment: "Характеристики каждого кластера (fix 21.10.2025)"
  
  **Было предложение для реализации (~20 мин):**
  
  После line 341 (после вывода распределения) добавить блок анализа характеристик:
  
  ```python
  # Характеристики каждого кластера
  nb.info("  Cluster characteristics:")
  
  # Определяем формат clustering
  if isinstance(clusters, dict) and not isinstance(next(iter(clusters.values())), (list, tuple)):
      # Format A: Dict[zone_id -> cluster_id]
      for cluster_id in sorted(set(clusters.values())):
          # Найти зоны этого кластера
          zones_in_cluster = [z for z in result_macd_full.zones 
                             if clusters.get(z.zone_id) == cluster_id]
          
          if zones_in_cluster:
              # Рассчитать характеристики
              avg_duration = sum(z.duration for z in zones_in_cluster) / len(zones_in_cluster)
              types_count = {}
              for z in zones_in_cluster:
                  types_count[z.type] = types_count.get(z.type, 0) + 1
              
              nb.log(f"    Cluster {cluster_id}:")
              nb.log(f"      Zones: {len(zones_in_cluster)}")
              nb.log(f"      Avg duration: {avg_duration:.1f} bars")
              nb.log(f"      Types: bull={types_count.get('bull', 0)}, bear={types_count.get('bear', 0)}")
  
  elif isinstance(clusters, dict) and isinstance(next(iter(clusters.values())), (list, tuple)):
      # Format B: Dict[cluster_id -> List[zone_id]]
      for cluster_id, zone_ids in sorted(clusters.items()):
          # Найти зоны по их ID
          zones_in_cluster = [z for z in result_macd_full.zones if z.zone_id in zone_ids]
          
          if zones_in_cluster:
              avg_duration = sum(z.duration for z in zones_in_cluster) / len(zones_in_cluster)
              types_count = {}
              for z in zones_in_cluster:
                  types_count[z.type] = types_count.get(z.type, 0) + 1
              
              nb.log(f"    Cluster {cluster_id}:")
              nb.log(f"      Zones: {len(zones_in_cluster)}")
              nb.log(f"      Avg duration: {avg_duration:.1f} bars")
              nb.log(f"      Types: bull={types_count.get('bull', 0)}, bear={types_count.get('bear', 0)}")
  
  elif isinstance(clusters, (list, np.ndarray, pd.Series)):
      # Format C: List/array of cluster labels (index = zone index)
      for cluster_id in sorted(set(clusters)):
          # Индексы зон с этим кластером
          zone_indices = [i for i, cid in enumerate(clusters) if cid == cluster_id]
          zones_in_cluster = [result_macd_full.zones[i] for i in zone_indices 
                             if i < len(result_macd_full.zones)]
          
          if zones_in_cluster:
              avg_duration = sum(z.duration for z in zones_in_cluster) / len(zones_in_cluster)
              types_count = {}
              for z in zones_in_cluster:
                  types_count[z.type] = types_count.get(z.type, 0) + 1
              
              nb.log(f"    Cluster {cluster_id}:")
              nb.log(f"      Zones: {len(zones_in_cluster)}")
              nb.log(f"      Avg duration: {avg_duration:.1f} bars")
              nb.log(f"      Types: bull={types_count.get('bull', 0)}, bear={types_count.get('bear', 0)}")
  ```
  
  **Что это добавит:**
  - Avg duration для каждого кластера (понимание длительности зон)
  - Типы зон в кластере (bull/bear ratio)
  - Количество зон (дублирует распределение, но в контексте)
  
  **Альтернатива (если нужны ещё метрики):**
  Можно также добавить:
  - Avg price return: `sum(z.features.get('price_return', 0) for z in zones) / len(zones)`
  - Avg volatility: `sum(z.features.get('volatility_expansion', 0) for z in zones) / len(zones)`
  - Cluster "profile": например, "Long quiet zones" или "Short volatile zones"

---

**📊 SUMMARY для Проблема 1.2:**

**Статус:** ✅ **100% РЕАЛИЗОВАНО** (21.10.2025)

**Что реализовано:**
- ✅ clustering=True для MACD, RSI, AO
- ✅ result.clustering показан (безопасный доступ)
- ✅ Распределение зон по кластерам (для всех 3 форматов)
- ✅ 3-форматный разбор (Format A/B/C)
- ✅ Try/except wrapper для graceful degradation
- ✅ **Характеристики каждого кластера** (fix 21.10.2025)
  - Avg duration
  - Bull/bear types distribution
  - Zones count per cluster

**Изменения в notebook:**
- Lines 343-396: Блок анализа характеристик кластеров
- Поддержка Format A, B, C
- Метрики: zones, avg_duration, bull/bear count

**Время реализации:** 20 минут (как планировалось)

---

#### Проблема 1.3: Statistical tests не показываются

**Статус:** ✅ **ПОЛНОСТЬЮ РЕШЕНО** (21.10.2025, 100% реализации)

**Что сделано:**
- ✅ Добавлен substep 5.5: Statistical Hypothesis Tests
- ✅ Показаны результаты tests из result.hypothesis_tests (p-values)
- ✅ Добавлена подготовка abs_price_return в Step 1 (для volatility tests) - КРИТИЧЕСКОЕ
- ✅ **Детальный вывод реализован** (fix 21.10.2025)
  - test_statistic показан
  - significance calculation показано (True/False)
  - tests.data_size показан
  - Образовательный комментарий добавлен

**Текущий код:**
```python
# НЕТ usage HypothesisTestSuite ❌
```

**Решение:**
```python
nb.substep("5.5: Statistical Hypothesis Tests")

nb.info("Статистические тесты для зон MACD:")

if result_macd_full.hypothesis_tests:
    tests = result_macd_full.hypothesis_tests
    
    nb.log(f"  Tests executed: {tests.data_size if hasattr(tests, 'data_size') else 'N/A'}")
    
    # Показать результаты основных тестов
    if hasattr(tests, 'results'):
        for test_name, test_result in tests.results.items():
            if test_result and hasattr(test_result, 'p_value'):
                nb.log(f"  {test_name}:")
                nb.log(f"    p-value: {test_result.p_value:.4f}")
                nb.log(f"    significant: {test_result.p_value < 0.05}")
            elif test_result and hasattr(test_result, 'test_statistic'):
                nb.log(f"  {test_name}:")
                nb.log(f"    statistic: {test_result.test_statistic:.4f}")
    
    nb.info("  Hypothesis tests help validate zone significance")
else:
    nb.warning("  Insufficient data for hypothesis tests (need more zones)")
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 307-316 в 03_zones_universal.py + lines 70-74):**
```python
# ✅ РЕАЛИЗОВАНО с УПРОЩЕНИЕМ:

# КРИТИЧЕСКОЕ FIX в Step 1 (lines 70-74):
# Подготовка производных признаков для hypothesis tests
nb.info("Подготовка производных признаков для statistical tests:")
df['price_return'] = df['close'].pct_change()
df['abs_price_return'] = df['price_return'].abs()
nb.log("[OK] abs_price_return calculated (required for volatility hypothesis tests)")

# Step 5.5: Statistical Hypothesis Tests (lines 307-316)
nb.substep("5.5: Statistical Hypothesis Tests (MACD)")
if hasattr(result_macd_full, 'hypothesis_tests') and result_macd_full.hypothesis_tests:
    tests = result_macd_full.hypothesis_tests
    if hasattr(tests, 'results') and tests.results:
        nb.log("  Hypothesis tests executed")
        for tname, tres in tests.results.items():
            if tres and hasattr(tres, 'p_value'):
                nb.log(f"    {tname}: p={tres.p_value}")
else:
    nb.warning("  Hypothesis tests unavailable or insufficient data")
```

**Отличия от предложенного:**

- ✅ **Подготовка abs_price_return** - ДОБАВЛЕНА в Step 1 (НЕ было в предложении!)
  - Причина: volatility_effects test требует колонку 'abs_price_return' в DataFrame
  - Критическое исправление: без этого тест падает с KeyError
  - Решение: df['abs_price_return'] = df['close'].pct_change().abs()
  
- ⚠️ **Упрощенный вывод результатов**
  - Предложено: детальный вывод (p-value, significance, statistic)
  - Реализовано: краткий вывод (только p-value)
  - Причина: упрощение для читабельности notebook
  
- ❌ **data_size** - НЕ показан
  - Предложено: `tests.data_size`
  - Реализовано: пропущено
  - Причина: упрощение вывода
  
- ❌ **Объяснение значения тестов** - НЕ добавлено
  - Предложено: nb.info("Hypothesis tests help validate zone significance")
  - Реализовано: пропущено
  - Статус: LOW priority (можно добавить для улучшения)

**Критическое обнаружение:**
- ⚠️ **volatility_effects требует abs_price_return** в DataFrame
- ✅ РЕШЕНО: добавлена подготовка в Step 1 (lines 70-74)
- Без этого: `KeyError: "['abs_price_return'] not in index"`

---

**Что добавить:**

Checklist реализации:

- [x] **Показать `result.hypothesis_tests` (AnalysisResult object)**
  - ✅ РЕАЛИЗОВАНО: lines 402-411 в 03_zones_universal.py
  - Безопасный доступ через hasattr
  - Проверка наличия results attribute

- [x] **РЕАЛИЗОВАНО: Извлечь p-values и test statistics**
  - ✅ ДОБАВЛЕНО: lines 410-420 в 03_zones_universal.py (21.10.2025)
  - ✅ p-value показан с форматированием (4 знака)
  - ✅ test_statistic показан (если доступен)
  - ✅ significance calculation показано (True/False с alpha=0.05)
  - Детальный вывод для каждого теста

- [x] **РЕАЛИЗОВАНО: Показать tests.data_size**
  - ✅ ДОБАВЛЕНО: lines 407-408 в 03_zones_universal.py (21.10.2025)
  - Safe check: `if hasattr(tests, 'data_size')`
  - Output: `Tests based on {tests.data_size} zones`

- [x] **РЕАЛИЗОВАНО: Объяснить значение тестов**
  - ✅ ДОБАВЛЕНО: lines 422-428 в 03_zones_universal.py (21.10.2025)
  - ✅ Детальное описание каждого теста
  - ✅ Интерпретация p-value (< 0.05 = significant)
  - Comment: "Образовательный комментарий (fix 21.10.2025)"
  - Формат: Детальная альтернатива (5 lines educational info)

- [x] **КРИТИЧЕСКОЕ: Подготовка данных для volatility tests**
  - ✅ РЕАЛИЗОВАНО: lines 70-74 в Step 1 (НЕ было в оригинальном предложении!)
  - Добавлена подготовка: df['abs_price_return'] = df['close'].pct_change().abs()
  - Без этого: volatility_effects test падает с KeyError
  - Это ОБЯЗАТЕЛЬНАЯ подготовка данных для корректной работы HypothesisTestSuite

---

**📊 SUMMARY для Проблема 1.3:**

**Статус:** ✅ **100% РЕАЛИЗОВАНО** (21.10.2025)

**Что реализовано:**
- ✅ **abs_price_return подготовка** (Step 1) - КРИТИЧЕСКОЕ исправление
- ✅ Substep 5.5: Statistical Hypothesis Tests
- ✅ result.hypothesis_tests показан (безопасный доступ)
- ✅ p-values извлечены и показаны для всех тестов
- ✅ **test_statistic показан** (fix 21.10.2025)
- ✅ **significance calculation показано** (True/False с alpha=0.05)
- ✅ **tests.data_size показан** (количество зон для тестов)
- ✅ **Образовательный комментарий добавлен** (описание каждого теста + интерпретация)

**Изменения в notebook:**
- Lines 407-408: tests.data_size
- Lines 410-420: Детальный вывод (p-value, significant, statistic)
- Lines 422-428: Образовательный комментарий (5 lines info)

**Время реализации:** 9 минут (как планировалось)

---

#### Проблема 1.4: Sequence analysis не показывается

**Статус:** ✅ **ПОЛНОСТЬЮ РЕШЕНО** (21.10.2025, 100% реализации)

**Что сделано:**
- ✅ Добавлен substep 5.6: Sequence Analysis
- ✅ Показаны transitions из result.sequences
- ✅ **Patterns показаны** (fix 21.10.2025) - MEDIUM priority закрыт
- ✅ **Детали добавлены** (заголовки, комментарии, total count)

**Текущий код:**
```python
# НЕТ usage ZoneSequenceAnalyzer ❌
```

**Решение:**
```python
nb.substep("5.6: Sequence Analysis")

nb.info("Анализ последовательностей и паттернов:")

if result_macd_full.sequences:
    seq = result_macd_full.sequences
    
    nb.log(f"  Total zones analyzed: {len(result_macd_full.zones)}")
    
    # Transitions
    if hasattr(seq, 'transitions') and seq.transitions:
        nb.info("  Transitions (zone type changes):")
        for trans_type, count in seq.transitions.items():
            nb.log(f"    {trans_type}: {count}")
    
    # Patterns
    if hasattr(seq, 'patterns'):
        nb.info(f"  Patterns found: {len(seq.patterns) if seq.patterns else 0}")
        
        if seq.patterns:
            for pattern in seq.patterns[:3]:  # Показать первые 3
                nb.log(f"    Pattern: {pattern.get('type', 'N/A')} (length: {pattern.get('length', 'N/A')})")
    
    nb.info("  Sequence analysis helps identify zone patterns and trading regimes")
else:
    nb.warning("  No sequence analysis results")
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 318-325 в 03_zones_universal.py):**
```python
# ✅ РЕАЛИЗОВАНО с УПРОЩЕНИЕМ:

nb.substep("5.6: Sequence Analysis (MACD)")
if hasattr(result_macd_full, 'sequences') and result_macd_full.sequences:
    seq = result_macd_full.sequences
    if hasattr(seq, 'transitions') and seq.transitions:
        for trans, cnt in seq.transitions.items():
            nb.log(f"    {trans}: {cnt}")
else:
    nb.warning("  No sequence analysis available")
```

**Отличия от предложенного:**

- ❌ **Total zones count** - НЕ показан (LOW priority)
  - Предложено: `nb.log(f"Total zones analyzed: {len(result_macd_full.zones)}")`
  - Реализовано: пропущено для упрощения
  
- ⚠️ **Transitions вывод упрощен** (LOW priority)
  - Предложено: `nb.info("Transitions (zone type changes):")` + детальный вывод
  - Реализовано: краткий вывод без заголовка
  - Только: `nb.log(f"{trans}: {cnt}")`
  
- ❌ **Patterns НЕ показаны** (**MEDIUM priority** ⭐)
  - Предложено: вывод patterns[:3] с типом и длиной
  - Реализовано: пропущено полностью
  - Причина: упрощение (patterns могут отсутствовать или быть пустыми)
  - **Важно:** Паттерны - полезная информация для трейдинга!
  
- ❌ **Образовательный комментарий** - НЕ добавлен (LOW priority)
  - Предложено: "Sequence analysis helps identify zone patterns and trading regimes"
  - Реализовано: пропущено для упрощения

**Результат:**
- ✅ Основная функциональность работает (transitions показаны)
- ❌ **Patterns НЕ показаны** (MEDIUM priority gap!)
- ⚠️ Детали упрощены (заголовки, комментарии)
- ✅ Graceful degradation (warning если sequences отсутствуют)

---

**Что добавить:**

Checklist реализации:

- [x] **Показать `result.sequences` object**
  - ✅ РЕАЛИЗОВАНО: lines 432-434 в 03_zones_universal.py
  - Безопасный доступ через hasattr
  - Проверка наличия sequences attribute

- [x] **Показать transitions (bull→bear, bear→bull)**
  - ✅ РЕАЛИЗОВАНО: lines 435-437 в 03_zones_universal.py
  - Вывод всех transitions с подсчетом
  - Format: `{trans}: {cnt}` (например, "bull->bear: 5")
  - ⚠️ УПРОЩЕНО: без заголовка "Transitions (zone type changes)"

- [x] **РЕАЛИЗОВАНО: Показать total zones count**
  - ✅ ДОБАВЛЕНО: line 437 в 03_zones_universal.py (21.10.2025)
  - Output: `Total zones analyzed: {len(result_macd_full.zones)}`

- [x] **РЕАЛИЗОВАНО: Добавить заголовок для transitions**
  - ✅ ДОБАВЛЕНО: line 441 в 03_zones_universal.py (21.10.2025)
  - ✅ Заголовок: `nb.info("Transitions (zone type changes):")`
  - ✅ Indent обновлен: line 443 (увеличен для подчинения)

- [x] **РЕАЛИЗОВАНО: Показать detected patterns**
  - ✅ ДОБАВЛЕНО: lines 445-459 в 03_zones_universal.py (21.10.2025)
  - ✅ Количество patterns: `nb.info(f"Patterns found: {len(seq.patterns)}")`
  - ✅ Показаны первые 3 паттерна с деталями (type, length, frequency)
  - ✅ Безопасный доступ к полям через isinstance check
  - ✅ Graceful handling: "No patterns detected" если отсутствуют
  - Comment: "Patterns (fix 21.10.2025)"

- [x] **РЕАЛИЗОВАНО: Образовательный комментарий**
  - ✅ ДОБАВЛЕНО: line 462 в 03_zones_universal.py (21.10.2025)
  - Output: "Sequence analysis helps identify zone patterns and trading regimes"
  - Comment: "Образовательный комментарий (fix 21.10.2025)"

---

**📊 SUMMARY для Проблема 1.4:**

**Статус:** ✅ **100% РЕАЛИЗОВАНО** (21.10.2025)

**Что реализовано:**
- ✅ Substep 5.6: Sequence Analysis (MACD)
- ✅ result.sequences показан (безопасный доступ)
- ✅ Transitions показаны (bull->bear, bear->bull с подсчетом)
- ✅ Graceful degradation (warning если sequences отсутствуют)
- ✅ **Total zones count показан** (fix 21.10.2025)
- ✅ **Transitions заголовок добавлен** (fix 21.10.2025)
- ✅ **Patterns detection реализован** (fix 21.10.2025)
  - Первые 3 паттерна с деталями (type, length, frequency)
  - Безопасный доступ через isinstance
  - Graceful handling если patterns отсутствуют
- ✅ **Образовательный комментарий добавлен** (fix 21.10.2025)

**Изменения в notebook:**
- Line 437: Total zones count
- Lines 441, 443: Transitions заголовок + indent
- Lines 445-459: Patterns detection (15 lines, MEDIUM priority)
- Line 462: Образовательный комментарий

**Время реализации:** 8 минут (как планировалось)

**⚠️ Обнаруженная проблема при тестировании:**
- `result_macd_full.sequences` возвращает None/пустой
- Код для patterns реализован ПОЛНОСТЬЮ и корректно
- НО не выполняется из-за отсутствия входных данных
- **Причина:** ✅ **FOUND + FIXED** (21.10.2025) - NAMING MISMATCH + DICT ACCESS!
  - Notebook used `.sequences` (НЕ СУЩЕСТВУЕТ!) → **FIXED:** `.sequence_analysis`
  - Model has `.sequence_analysis` (правильное имя) ✅
  - `sequence_analysis` is dict, NOT object → **FIXED:** dict access via `['transitions']`, `['patterns']`
  - Блок НЕ выполнялся из-за неправильного атрибута → **NOW WORKS!**
- **Статус:** ✅ **РЕШЕНО** (21.10.2025, 10 мин)
- **Solution:** Заменено `.sequences` на `.sequence_analysis` + исправлен dict access
- **Test Results:** ✅ Transitions показываются (4 типа: bull->bear=32, bear->bull=32, bull->bull=4, bear->bear=3)
- **Note:** Это не недостаток пакета - analyzer правильный, только typo + dict access в notebook
- **Details:** См. `devref/gaps/zo/zonan_sh.md` ЭТАП 3 (полная реализация)

---

#### Проблема 1.5: Step 9 не показывает feature comparison

**Статус:** ✅ РЕШЕНО (2025-10-20)

**Что сделано:**
- ✅ Переименован Step 9: "Multiple Indicators - Feature Comparison"
- ✅ Используются result_rsi_full и result_ao_full из Step 5 (с .analyze())
- ✅ Добавлена сравнительная таблица features
- ✅ Добавлен substep 9.1: Zone Overlap Analysis
- ✅ Добавлен substep 9.2: Consensus Signals

**Текущий код (lines 434-492):**
```python
nb.step("Step 9: Other Indicators - Detection Examples")

# Только detection, БЕЗ analyze() ❌
result_rsi = analyze_zones(df).with_indicator(...).detect_zones(...).build()
result_ao = analyze_zones(df).with_indicator(...).detect_zones(...).build()

# Показывает только КОЛИЧЕСТВО зон
nb.log(f"RSI: {len(result_rsi.zones)} zones")
nb.log(f"AO: {len(result_ao.zones)} zones")
```

**Решение:**
```python
nb.step("Step 9: Multiple Indicators - Feature Comparison")

nb.info("Сравнение features для разных индикаторов:")

# RSI с full analysis
result_rsi_analyzed = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True, n_clusters=2)
    .build()
)

# AO с full analysis
result_ao_analyzed = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
    .detect_zones('zero_crossing', indicator_col='AO_5_34')
    .analyze(clustering=True, n_clusters=2)
    .build()
)

# Сравнительная таблица
nb.info("Сравнение zones и features:")
nb.log(f"{'Indicator':<15} {'Zones':<10} {'Avg Duration':<15} {'Has Features':<15}")
nb.log("-" * 60)

for name, result in [('MACD', result_macd_full), ('RSI', result_rsi_analyzed), ('AO', result_ao_analyzed)]:
    zones_count = len(result.zones)
    avg_duration = np.mean([z.duration for z in result.zones]) if result.zones else 0
    has_features = any(z.features for z in result.zones)
    
    nb.log(f"{name:<15} {zones_count:<10} {avg_duration:<15.1f} {has_features!s:<15}")

# Zone overlap analysis
nb.substep("9.1: Zone Overlap Analysis")

# Найти перекрывающиеся временные периоды
macd_periods = [(z.start_index, z.end_index) for z in result_macd_full.zones]
rsi_periods = [(z.start_index, z.end_index) for z in result_rsi_analyzed.zones]

overlaps = 0
for m_start, m_end in macd_periods:
    for r_start, r_end in rsi_periods:
        if not (m_end < r_start or r_end < m_start):  # Overlap check
            overlaps += 1
            break

nb.log(f"  MACD zones: {len(macd_periods)}")
nb.log(f"  RSI zones: {len(rsi_periods)}")
nb.log(f"  Overlapping zones: {overlaps}")
nb.log(f"  Overlap ratio: {overlaps / max(len(macd_periods), 1) * 100:.1f}%")

# Consensus signals
nb.substep("9.2: Consensus Signals")

consensus_count = 0
if result_macd_full.zones and result_rsi_analyzed.zones:
    # Найти зоны где оба индикатора согласны
    for mz in result_macd_full.zones:
        for rz in result_rsi_analyzed.zones:
            # Overlap + same type = consensus
            if (not (mz.end_index < rz.start_index or rz.end_index < mz.start_index) and
                mz.type == rz.type):
                consensus_count += 1
                break

nb.log(f"  Consensus signals (MACD + RSI agree): {consensus_count}")
nb.log(f"  Use for: Higher confidence trades")

nb.success("✅ Multi-indicator feature comparison complete!")
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 514-556 в 03_zones_universal.py):**
```python
# ✅ РЕАЛИЗОВАНО с ОПТИМИЗАЦИЕЙ (переиспользование результатов):

nb.step("Step 9: Multiple Indicators - Feature Comparison")

# Note: reuse result_rsi_full and result_ao_full from Step 5
# (already created with .analyze())

if result_macd_full and result_rsi_full and result_ao_full:
    nb.info("Feature comparison table:")
    nb.log(f"{'Indicator':<12} {'Zones':<8} {'AvgDur':<8} {'HasFeatures':<12}")
    nb.log("-" * 50)
    for name, res in [("MACD", result_macd_full), ("RSI", result_rsi_full), ("AO", result_ao_full)]:
        zones = len(res.zones) if res else 0
        avgd = np.mean([z.duration for z in res.zones]) if (res and res.zones) else 0
        hasf = any(z.features for z in res.zones) if (res and res.zones) else False
        nb.log(f"{name:<12} {zones:<8} {avgd:<8.1f} {str(hasf):<12}")
    
    nb.substep("9.1: Zone Overlap (MACD vs RSI)")
    if result_macd_full.zones and result_rsi_full.zones:
        macd_periods = [(z.start_index, z.end_index) for z in result_macd_full.zones]
        rsi_periods = [(z.start_index, z.end_index) for z in result_rsi_full.zones]
        overlaps = 0
        for m_start, m_end in macd_periods:
            for r_start, r_end in rsi_periods:
                if not (m_end < r_start or r_end < m_start):
                    overlaps += 1
                    break
        nb.log(f"  MACD zones: {len(macd_periods)} / RSI zones: {len(rsi_periods)} / Overlaps: {overlaps}")
    else:
        nb.warning("  Insufficient zones for overlap analysis")
    
    nb.substep("9.2: Consensus Signals (MACD & RSI)")
    if result_macd_full.zones and result_rsi_full.zones:
        consensus = 0
        for mz in result_macd_full.zones:
            for rz in result_rsi_full.zones:
                if not (mz.end_index < rz.start_index or rz.end_index < mz.start_index) and mz.type == rz.type:
                    consensus += 1
                    break
        nb.log(f"  Consensus signals: {consensus}")
    else:
        nb.warning("  Insufficient zones for consensus analysis")
else:
    nb.warning("Step 9 skipped: results from Step 5 not available")
```

**Отличия от предложенного:**

- ✅ **Переиспользование результатов из Step 5** - ОПТИМИЗАЦИЯ (НЕ было в предложении!)
  - Предложено: создать новые result_rsi_analyzed, result_ao_analyzed в Step 9
  - Реализовано: переиспользовать result_rsi_full, result_ao_full из Step 5
  - Преимущество: избежание дублирования вычислений
  - Экономия: ~2-3 секунды на повторные .analyze() вызовы
  
- ⚠️ **Упрощенная таблица**
  - Предложено: 4 колонки (Indicator, Zones, Avg Duration, Has Features)
  - Реализовано: 4 колонки (Indicator, Zones, AvgDur, HasFeatures) - совпадает!
  - ⚠️ Формат компактнее (12/8/8/12 вместо 15/10/15/15)
  
- ⚠️ **Overlap вывод упрощен**
  - Предложено: 4 строки (MACD zones, RSI zones, Overlapping zones, Overlap ratio)
  - Реализовано: 1 строка (MACD/RSI/Overlaps в одной строке)
  - Причина: компактность
  - ❌ Overlap ratio НЕ показан
  
- ✅ **Consensus вывод упрощен**
  - Предложено: 2 строки (Consensus signals + Use for)
  - Реализовано: 1 строка (Consensus signals)
  - ❌ "Use for: Higher confidence trades" пропущено
  
- ❌ **Success message** - НЕ добавлен
  - Предложено: nb.success("✅ Multi-indicator feature comparison complete!")
  - Реализовано: пропущено
  - Статус: LOW priority

- ✅ **Guards для пустых результатов** - ДОБАВЛЕНЫ (НЕ было в предложении!)
  - Lines 530, 544: проверка наличия zones
  - Graceful degradation с warnings

**Результат:**
- ✅ Feature comparison работает
- ✅ Overlap analysis работает
- ✅ Consensus signals работают
- ✅ Переиспользование результатов (оптимизация)
- ⚠️ Упрощенный вывод (без overlap ratio, без educational comments)

---

**Что добавить:**

Checklist реализации:

- [x] **`.analyze()` для RSI и AO (не только detection)**
  - ✅ РЕАЛИЗОВАНО в Step 5 (lines 251-269)
  - result_rsi_full создан с .analyze(clustering=True, n_clusters=2)
  - result_ao_full создан с .analyze(clustering=True, n_clusters=2)
  - ✅ ОПТИМИЗАЦИЯ: переиспользованы в Step 9 (вместо повторного создания)

- [x] **Сравнительная таблица features**
  - ✅ РЕАЛИЗОВАНО: lines 520-527 в 03_zones_universal.py
  - Формат: 4 колонки (Indicator, Zones, AvgDur, HasFeatures)
  - Показаны: MACD, RSI, AO
  - ⚠️ КОМПАКТНЕЕ предложенного (упрощенный формат)

- [x] **Zone overlap analysis**
  - ✅ РЕАЛИЗОВАНО: lines 529-541
  - Алгоритм overlap detection реализован корректно
  - Вывод: краткий формат (1 строка вместо 4)
  - ❌ Overlap ratio НЕ показан (было в предложении)
  - Причина: упрощение
  - Статус: LOW priority (основная метрика есть)

- [x] **Consensus signals (где индикаторы согласны)**
  - ✅ РЕАЛИЗОВАНО: lines 543-553
  - Алгоритм: overlap + same type = consensus
  - Вывод: consensus count
  - ❌ "Use for: Higher confidence trades" НЕ добавлено
  - Статус: LOW priority (образовательный комментарий)

**Дополнительные улучшения (НЕ в предложении):**
- ✅ Guards для пустых результатов (lines 530, 544, 519)
- ✅ Проверка if result_macd_full and result_rsi_full and result_ao_full
- ✅ Warning если Step 5 results недоступны

**Ссылки:**
- zonan.md lines 3956-3960 (Multiple Indicators Comparison spec)

---

#### Проблема 1.6: Edge cases не тестируются

**Статус:** ✅ РЕШЕНО (2025-10-20)

**Что сделано:**
- ✅ Добавлен Step 11: Edge Cases & Error Handling
- ✅ Substep 11.1: Small Dataset (< 50 bars)
- ✅ Substep 11.2: No Zones Detected
- ✅ Substep 11.3: Missing Indicator Column
- ✅ Substep 11.4: Invalid Parameters
- ✅ Step 11 перемещен ПЕРЕД nb.finish() (чтобы выполнялся)

**Текущий код:**
```python
# Step 9: Edge Cases - ОТСУТСТВУЕТ ❌
```

**Решение:**
```python
# Добавить новый Step 11 (или вставить как Step 6)
nb.step("Step 11: Edge Cases & Error Handling")

nb.info("Graceful handling edge cases:")

nb.substep("11.1: Small Dataset (< 50 bars)")

small_df = df.head(30)
result_small = (
    analyze_zones(small_df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=False)
    .build()
)

nb.log(f"  Small dataset (30 bars): {len(result_small.zones)} zones detected")
nb.log(f"  Pipeline works with minimal data ✅")

nb.substep("11.2: No Zones Detected")

# Очень строгие параметры → нет зон
result_no_zones = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('threshold', indicator_col='macd_hist', 
                  upper_threshold=100, lower_threshold=-100,  # Impossible thresholds
                  min_duration=1000)  # Very long duration
    .analyze(clustering=False)
    .build()
)

nb.log(f"  No zones case: {len(result_no_zones.zones)} zones")
nb.log(f"  Pipeline handles gracefully (no crash) ✅")

nb.substep("11.3: Missing Indicator Column")

with nb.error_handling("Missing column test", critical=False):
    try:
        result_missing = (
            analyze_zones(df)
            .detect_zones('zero_crossing', indicator_col='NON_EXISTENT_COLUMN')
            .build()
        )
        nb.log(f"  Missing column: {len(result_missing.zones)} zones")
    except Exception as e:
        nb.warning(f"  Expected error: {type(e).__name__}: {str(e)[:80]}")
        nb.log(f"  Error handling works ✅")

nb.substep("11.4: Invalid Parameters")

with nb.error_handling("Invalid params test", critical=False):
    try:
        result_invalid = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=-5)  # Invalid
            .build()
        )
    except ValueError as e:
        nb.warning(f"  Expected error: {str(e)[:80]}")
        nb.log(f"  Validation works ✅")

nb.success("✅ Edge cases handled gracefully!")
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 637-691 в 03_zones_universal.py):**
```python
# ✅ ПОЛНОСТЬЮ РЕАЛИЗОВАНО:

nb.step("Step 11: Edge Cases & Error Handling")

nb.substep("11.1: Small Dataset (< 50 bars)")
with nb.error_handling("Small dataset"):
    small_df = df.head(30)
    res_small = (
        analyze_zones(small_df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(clustering=False)
        .build()
    )
    nb.log(f"  Small dataset (30 bars): {len(res_small.zones)} zones")

nb.substep("11.2: No Zones Detected")
with nb.error_handling("No zones"):
    res_none = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('threshold', indicator_col='macd_hist', upper_threshold=100, lower_threshold=-100, min_duration=999)
        .analyze(clustering=False)
        .build()
    )
    nb.log(f"  No zones case: {len(res_none.zones)} zones")

nb.substep("11.3: Missing Indicator Column")
with nb.error_handling("Missing column", critical=False):
    try:
        res_missing = (
            analyze_zones(df)
            .detect_zones('zero_crossing', indicator_col='NON_EXISTENT_COLUMN')
            .build()
        )
        nb.log(f"  Missing column result: {len(res_missing.zones)} zones")
    except Exception as e:
        nb.warning(f"  Expected error: {type(e).__name__}: {str(e)[:80]}")

nb.substep("11.4: Invalid Parameters")
with nb.error_handling("Invalid params", critical=False):
    try:
        res_invalid = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=-5)
            .build()
        )
        nb.log(f"  Invalid params zones: {len(res_invalid.zones)}")
    except ValueError as e:
        nb.warning(f"  Expected error: {str(e)[:80]}")

nb.success("Edge cases handled gracefully")
```

**Отличия от предложенного:**

- ⚠️ **Success messages упрощены**
  - Предложено: `nb.log(f"Pipeline works with minimal data ✅")` после каждого case
  - Реализовано: только финальный success в конце
  - Причина: компактность, избежание повторения
  
- ✅ **Все 4 substeps реализованы**
  - 11.1: Small Dataset (30 bars) ✅
  - 11.2: No Zones (impossible thresholds + min_duration=999) ✅
  - 11.3: Missing Column (NON_EXISTENT_COLUMN) ✅
  - 11.4: Invalid Parameters (min_duration=-5) ✅
  
- ✅ **Error handling с critical=False** - корректно реализовано
  - Для 11.3 и 11.4: critical=False (не прерывает выполнение)
  - Для 11.1 и 11.2: обычный error_handling (ожидается успех)
  
- ❌ **"✅" emoji в success messages** - убран
  - Предложено: `nb.log(f"Pipeline works with minimal data ✅")`
  - Реализовано: текст без emoji
  - Причина: cp1251 compatibility (как в Stage 2.3)
  
- ✅ **Step 11 ПЕРЕД nb.finish()** - корректно размещен
  - Критическое исправление: изначально был ПОСЛЕ finish (не выполнялся)
  - Решено: перемещен перед finish + добавлен nb.wait()

**Результат:**
- ✅ Все 4 edge cases протестированы
- ✅ Graceful error handling работает
- ✅ Step 11 выполняется корректно (в правильном месте)
- ✅ ASCII-safe output (cp1251 compatible)

---

**Что добавить:**

Checklist реализации:

- [x] **Small datasets (< 50 bars)**
  - ✅ РЕАЛИЗОВАНО: substep 11.1 (lines 639-650)
  - Dataset: 30 bars (df.head(30))
  - Проверка: pipeline работает с минимальными данными
  - Вывод: количество zones detected

- [x] **No zones detected case**
  - ✅ РЕАЛИЗОВАНО: substep 11.2 (lines 652-661)
  - Метод: impossible thresholds (100/-100) + min_duration=999
  - Проверка: pipeline не падает при отсутствии зон
  - Вывод: "No zones case: 0 zones"

- [x] **Missing indicator columns**
  - ✅ РЕАЛИЗОВАНО: substep 11.3 (lines 663-672)
  - Test column: 'NON_EXISTENT_COLUMN'
  - Error handling: critical=False (не прерывает)
  - Проверка: Exception caught и показан warning
  - ⚠️ УПРОЩЕНО: без explicit "Error handling works ✅" message

- [x] **Invalid parameters**
  - ✅ РЕАЛИЗОВАНО: substep 11.4 (lines 674-686)
  - Test param: min_duration=-5 (negative value)
  - Error handling: critical=False
  - Проверка: ValueError caught
  - ⚠️ УПРОЩЕНО: без explicit "Validation works ✅" message

- [x] **Error handling demonstration**
  - ✅ РЕАЛИЗОВАНО: используется nb.error_handling в каждом substep
  - critical=False для 11.3 и 11.4 (ожидается ошибка)
  - try/except для явной демонстрации exception handling
  - ✅ Graceful degradation показана

**Дополнительные улучшения (НЕ в предложении):**
- ✅ Step 11 перемещен ПЕРЕД nb.finish() (критическое исправление позиционирования)
- ✅ Добавлен nb.wait() перед Step 11 (для читабельности в interactive mode)
- ✅ ASCII-safe output (без emoji для cp1251 compatibility)

**Ссылки:**
- zonan.md lines 3962-3967 (Edge Cases spec)

---

#### Проблема 1.7: Устаревшие комментарии о "баге"

**Статус:** ✅ РЕШЕНО (2025-10-20)

**Что сделано:**
- ✅ Обновлен module docstring (lines 1-19) - удалены комментарии о "баге", добавлено "v2.1 UPDATE"
- ✅ Обновлен Step 10 summary - заменены "БАГ" на "v2.1: Features work for ALL indicators"
- ✅ Удалены warnings о "баге" из Step 9
- ✅ Обновлены рекомендации - "For all indicators: use full analyze()"

**Текущие комментарии (ВВОДЯТ В ЗАБЛУЖДЕНИЕ!):**
```python
# Line 6: "Это ИЗВЕСТНЫЙ БАГ, который нарушает универсальность архитектуры."
# Line 10: "Детекцию для других индикаторов (без analyze() из-за бага)"
# Line 437: "БЕЗ .analyze() из-за бага в ZoneFeaturesAnalyzer (hardcoded для MACD)"
# Line 451: ".build()  # БЕЗ .analyze() из-за бага"
# Line 485: "После исправления, analyze() будет работать для ВСЕХ индикаторов"
```

**Решение:**
```python
# УДАЛИТЬ или ОБНОВИТЬ все комментарии:

# Line 6-10: Заменить на:
'''
Comprehensive исследование универсального анализа зон (v2.1)

v2.1 UPDATE (2025-10-20):
✅ ZoneFeaturesAnalyzer теперь УНИВЕРСАЛЬНЫЙ (читает indicator_context)
✅ .analyze() работает для ВСЕХ индикаторов (MACD, RSI, AO, Custom)
✅ Features extraction работает для любых oscillators

Этот скрипт демонстрирует:
1. Полный анализ для ВСЕХ индикаторов (MACD, RSI, AO) - v2.1 universality
2. Feature extraction для разных индикаторов
3. Clustering, statistical tests, sequence analysis
4. Migration guide и best practices
5. Performance benchmarks
'''

# Line 437-492: УДАЛИТЬ комментарии о "баге", ДОБАВИТЬ .analyze()
# Line 551-552: УДАЛИТЬ предупреждения, заменить на success messages
```

**Фактическая реализация (2025-10-20):**

**Реализовано (lines 1-19, 598-623 в 03_zones_universal.py):**
```python
# ✅ ПОЛНОСТЬЮ РЕАЛИЗОВАНО:

# 1. Module docstring обновлен (lines 1-19):
'''
Universal Zone Analysis - Deep Dive (v2.1)

v2.1 UPDATE (2025-10-20):
✅ ZoneFeaturesAnalyzer is UNIVERSAL (reads indicator_context)  
✅ .analyze() works for ALL indicators (MACD, RSI, AO, Custom)  
✅ Feature extraction is indicator-agnostic

This script demonstrates:
1) Full analysis pipeline for multiple indicators (features, clustering, tests, sequences)
2) Universal API capabilities (fluent builder, presets)
3) Migration guide (old → new)
4) Caching & persistence
5) Performance benchmarks

USAGE:
python research/notebooks/03_zones_universal.py --no-trap
'''

# 2. Step 10 summary обновлен (lines 598-603):
nb.log("KEY FINDINGS:")
nb.log("  1. [+] Universal API - fluent builder + presets")
nb.log("  2. [+] Caching works and accelerates")
nb.log("  3. [+] Modularity enables flexible usage")
nb.log(f"  4. [+] Performance: {len(result_large.zones)/time_large:.1f} zones/sec")
nb.log("  5. [+] v2.1: Features work for ALL indicators (MACD, RSI, AO)")  # ✅ БЫЛО: "БАГ"

# 3. Recommendations обновлены (lines 620-623):
nb.info("RECOMMENDATIONS:")
nb.log("  * For all indicators: use full analyze() - works universally (v2.1)")  # ✅ ОБНОВЛЕНО
nb.log("  * For production: enable caching (.with_cache())")
nb.log("  * For sharing: export to JSON")
# ❌ УДАЛЕНО: "Для RSI/AO: используйте только detection (баг в features)"

# 4. Step 9 warnings удалены:
# ❌ БЫЛО (line 436): nb.warning("ИЗВЕСТНЫЙ БАГ: ZoneFeaturesAnalyzer hardcoded для MACD колонок")
# ✅ УДАЛЕНО полностью - Step 9 переписан на feature comparison
```

**Отличия от предложенного:**

- ✅ **Module docstring** - полностью переписан на English
  - Предложено: Russian текст с v2.1 UPDATE
  - Реализовано: English текст (для cp1251 compatibility)
  - Преимущество: консистентность с examples/ (Stage 2.3)
  
- ✅ **Все упоминания "БАГ" удалены**
  - Line 6: "ИЗВЕСТНЫЙ БАГ" → удалено ✅
  - Line 10: "без analyze() из-за бага" → удалено ✅
  - Line 437: warning о баге → удалено (Step 9 переписан) ✅
  - Line 533: "БАГ: ZoneFeaturesAnalyzer hardcoded" → "v2.1: Features work" ✅
  - Line 551-552: warnings → удалены ✅
  
- ✅ **Recommendations обновлены**
  - Было: "Для RSI/AO: только detection (баг в features)"
  - Стало: "For all indicators: use full analyze() - works universally (v2.1)"
  - ✅ Позитивный message вместо негативного warning
  
- ✅ **English text** - добавлено (НЕ в предложении, но лучше!)
  - Консистентность с Stage 2.3 (examples переведены на English)
  - cp1251 compatibility

**Результат:**
- ✅ Все устаревшие комментарии о "баге" удалены
- ✅ Заменены на позитивные v2.1 UPDATE messages
- ✅ English text для key sections
- ✅ Позитивный tone (features WORK, не "баг требует исправления")

---

**Что сделать:**

Checklist реализации:

- [x] **Обновить module docstring (header)**
  - ✅ РЕАЛИЗОВАНО: lines 1-19 полностью переписаны
  - Было: "ИЗВЕСТНЫЙ БАГ", "TODO: Исправить"
  - Стало: "v2.1 UPDATE", "works for ALL indicators"
  - ✅ УЛУЧШЕНО: English text (вместо Russian)

- [x] **Удалить все комментарии о "баге"**
  - ✅ РЕАЛИЗОВАНО: все 5 locations обновлены
  - Lines 6, 10: module docstring переписан ✅
  - Line 437: Step 9 полностью переписан (warning удален) ✅
  - Line 451: комментарий удален (Step 9 использует .analyze()) ✅
  - Line 485: TODO удален ✅
  - Lines 533, 551-552: Step 10 summary обновлен ✅

- [x] **Заменить на комментарии о v2.1 universality**
  - ✅ РЕАЛИЗОВАНО: 
  - Module docstring: "v2.1 UPDATE" section добавлен
  - Step 10: "v2.1: Features work for ALL indicators" добавлено
  - ✅ Позитивный tone вместо негативного

- [x] **Добавить success messages**
  - ✅ РЕАЛИЗОВАНО частично:
  - Step 5: success messages для MACD, RSI, AO (lines 241, 259, 269)
  - Step 10: позитивный summary вместо "БАГ" warning
  - ⚠️ НЕ везде (упрощено для краткости)

**Дополнительные улучшения (НЕ в предложении):**
- ✅ English text в key sections (module docstring, Step 10, recommendations)
- ✅ Консистентность с Stage 2.3 (examples/)
- ✅ cp1251 compatibility

---

### **ЭТАП 2: Исправление 03_analysis_new_features.py - Advanced Features**

**Файл:** `research/notebooks/03_analysis_new_features.py` (693 lines → ~700 lines)  
**Время:** ~50-60 минут  
**Приоритет:** ⭐⭐⭐ CRITICAL

---

#### Проблема 2.1: Использование старого API

**Текущий код (lines 31-32, 76-82, 109-110):**
```python
from bquant.indicators.macd import MACDZoneAnalyzer  # ❌ Deprecated API
from bquant.analysis.zones import ZoneFeaturesAnalyzer  # ✅ OK, но используется неправильно

# Step 1
macd_analyzer = MACDZoneAnalyzer(macd_params={'fast': 12, 'slow': 26, 'signal': 9})
result = macd_analyzer.analyze_complete(df)  # ❌ Deprecated method

# Step 2
zone_dict = macd_analyzer._zone_to_dict(zone)  # ❌ AttributeError: метод удален
features = features_analyzer.extract_zone_features(zone_dict)  # ❌ Wrong signature
```

**Решение:**
```python
# ОБНОВИТЬ импорты
from bquant.analysis.zones import analyze_zones, analyze_macd_zones  # ✅ v2.1 API
from bquant.analysis.zones.models import ZoneAnalysisResult  # ✅ v2.1 models

# Step 1: Заменить на v2.1 API
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=True,
        n_clusters=3,
        swing_strategy='find_peaks',  # v2.1: swing работает
        run_hypothesis=True,
        run_regression=True,
        run_validation=True
    )
    .build()
)

nb.success(f"v2.1 API: {len(result.zones)} zones with FULL analysis")

# Step 2: Использовать zone.features напрямую
for zone in result.zones[:5]:
    if zone.features:  # ✅ Features уже extracted после .analyze()
        peak_time_ratio = zone.features.get('peak_time_ratio')
        trough_time_ratio = zone.features.get('trough_time_ratio')
        
        nb.log(f"  Zone {zone.zone_id} ({zone.type}):")
        nb.log(f"    Peak time ratio: {peak_time_ratio:.3f}" if peak_time_ratio else "    Peak: N/A")
        nb.log(f"    Trough time ratio: {trough_time_ratio:.3f}" if trough_time_ratio else "    Trough: N/A")
```

**Что изменить:**
- Заменить `MACDZoneAnalyzer` → `analyze_zones()` (v2.1 universal API)
- Заменить `macd_analyzer.analyze_complete()` → builder pattern
- Удалить `_zone_to_dict()` → использовать `zone.features` напрямую
- Использовать полный `.analyze()` с всеми опциями

**Ссылки:**
- zouni_v2.md Phase 1 Task 1.6 (ZoneFeaturesAnalyzer)
- examples/02a_universal_zones.py (v2.1 usage examples)

---

#### Проблема 2.2: Step 3 - Swing Strategies (Numba crash issue)

**Текущий код (lines 157-228):**
```python
nb.step("Шаг 3: Сравнение Swing Strategies (Phase 3.1)")

# Тестирует 3 swing strategies:
# - ZigZagSwingStrategy ❌ Numba crash на Windows
# - FindPeaksSwingStrategy
# - PivotPointsSwingStrategy
```

**Известная проблема:**
- ZigZagSwingStrategy вызывает Numba crash на Windows (external issue)
- Документировано в zo_issue_numba_zoneinfo_none.md

**Решение:**
```python
nb.step("Step 3: Swing Strategies Comparison")

nb.info("Testing different swing detection strategies:")

# FindPeaksSwingStrategy (RECOMMENDED, работает на всех платформах)
result_findpeaks = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=False,
        swing_strategy='find_peaks',  # ✅ Работает везде
        swing_params={'height': 0.001, 'prominence': 0.0005}
    )
    .build()
)

nb.log(f"  FindPeaks strategy: {len(result_findpeaks.zones)} zones")

# Показать swing metrics в features
if result_findpeaks.zones and result_findpeaks.zones[0].features:
    swing_metrics = {k: v for k, v in result_findpeaks.zones[0].features.items() if 'swing' in k.lower()}
    nb.log(f"  Swing metrics extracted: {list(swing_metrics.keys())}")

# PivotPointsSwingStrategy
result_pivot = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=False,
        swing_strategy='pivot_points',
        swing_params={'left_bars': 5, 'right_bars': 5}
    )
    .build()
)

nb.log(f"  PivotPoints strategy: {len(result_pivot.zones)} zones")

# ZigZagSwingStrategy - SKIP на Windows из-за Numba issue
nb.warning("  ZigZag strategy SKIPPED (Numba crash on Windows - known external issue)")
nb.log("  See: devref/gaps/zo/zo_issue_numba_zoneinfo_none.md")

nb.success("✅ Swing strategies tested (2/3, ZigZag skipped due to external issue)")
```

**Что изменить:**
- Использовать v2.1 API с `swing_strategy='find_peaks'`
- Показать swing metrics в features
- SKIP ZigZagSwingStrategy (Numba issue documented)
- Тестировать FindPeaks и PivotPoints

**Ссылки:**
- devref/gaps/zo/zo_issue_numba_zoneinfo_none.md (Numba crash documentation)
- bquant/analysis/zones/strategies/swing/ (swing strategies implementations)

---

#### Проблема 2.3: Steps 4-9 используют _zone_to_dict()

**Текущий код (повторяется в Steps 4-9):**
```python
# Step 4: Divergence
for zone in result.zones[:10]:
    zone_dict = macd_analyzer._zone_to_dict(zone)  # ❌ AttributeError
    features = features_analyzer.extract_zone_features(zone_dict)
    divergence = features.has_classic_divergence
```

**Решение (универсальный паттерн для всех steps):**
```python
# Step 4: Divergence Detection
nb.step("Step 4: Divergence Detection")

nb.info("Testing divergence detection for zones:")

result_with_divergence = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=False)  # Features автоматически извлекаются
    .build()
)

# Анализируем divergence из features
divergence_count = 0
hidden_div_count = 0

for zone in result_with_divergence.zones:
    if zone.features:
        # Classic divergence
        if zone.features.get('has_classic_divergence'):
            divergence_count += 1
            nb.log(f"  Zone {zone.zone_id}: Classic divergence detected")
        
        # Hidden divergence (если есть в features)
        if zone.features.get('has_hidden_divergence'):
            hidden_div_count += 1

nb.log(f"  Classic divergences: {divergence_count}/{len(result_with_divergence.zones)}")
nb.log(f"  Hidden divergences: {hidden_div_count}/{len(result_with_divergence.zones)}")

nb.success("✅ Divergence detection works with v2.1 API")
```

**Что изменить во ВСЕХ Steps 4-9:**
- Убрать `macd_analyzer._zone_to_dict(zone)`
- Использовать `zone.features` напрямую (уже заполнено после `.analyze()`)
- ИЛИ использовать прямой вызов features_analyzer (для custom extraction)

**Применить к:**
- Step 4: Divergence Detection
- Step 5: Volatility Analysis
- Step 6: Volume Analysis
- Step 7: Hypothesis Tests (использовать `result.hypothesis_tests`)
- Step 8: Regression Analysis (использовать `result.regression` если есть)
- Step 9: Validation Suite (использовать `result.validation` если есть)

---

#### Проблема 2.4: Hypothesis Tests вызывают напрямую

**Текущий код (lines 413-492):**
```python
nb.step("Шаг 7: Hypothesis Tests (Phase 3.7)")

# Создает HypothesisTestSuite напрямую
hypothesis_suite = HypothesisTestSuite()
hypothesis_results = hypothesis_suite.run_all_tests(...)  # ❌ Ручной вызов
```

**Решение:**
```python
nb.step("Step 7: Statistical Hypothesis Tests")

nb.info("v2.1: Hypothesis tests через pipeline:")

result_with_tests = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=True,
        run_hypothesis=True  # ✅ Автоматически через pipeline
    )
    .build()
)

# Извлекаем результаты тестов
if result_with_tests.hypothesis_tests:
    tests = result_with_tests.hypothesis_tests
    
    nb.log(f"  Hypothesis tests executed")
    nb.log(f"  Data size: {tests.data_size if hasattr(tests, 'data_size') else 'N/A'}")
    
    # Показать результаты
    if hasattr(tests, 'results') and tests.results:
        passed = sum(1 for r in tests.results.values() if r and hasattr(r, 'p_value') and r.p_value < 0.05)
        nb.log(f"  Significant tests (p < 0.05): {passed}/{len(tests.results)}")
        
        # Детали по каждому тесту
        for test_name, result in tests.results.items():
            if result:
                nb.log(f"    {test_name}: p={getattr(result, 'p_value', 'N/A')}")
    
    nb.success("✅ Hypothesis tests работают через pipeline (v2.1)")
else:
    nb.warning("  Insufficient data for hypothesis tests")
```

**Что изменить:**
- Использовать `run_hypothesis=True` в `.analyze()`
- Извлекать результаты из `result.hypothesis_tests`
- Не создавать HypothesisTestSuite вручную

**Ссылки:**
- bquant/analysis/zones/analyzer.py (UniversalZoneAnalyzer.analyze_zones method)
- bquant/analysis/statistical/ (HypothesisTestSuite)

---

#### Проблема 2.5: Regression & Validation

**Текущий код (lines 493-618):**
```python
nb.step("Шаг 8: Regression Analysis")
# Создает ZoneRegressionAnalyzer напрямую ❌

nb.step("Шаг 9: Validation Suite")
# Создает ValidationSuite напрямую ❌
```

**Решение:**
```python
nb.step("Step 8: Regression & Validation")

nb.info("v2.1: Regression и validation через pipeline:")

result_full = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=True,
        run_regression=True,   # ✅ Автоматически через pipeline
        run_validation=True    # ✅ Автоматически через pipeline
    )
    .build()
)

# Regression results
if hasattr(result_full, 'regression') and result_full.regression:
    nb.log("  Regression analysis available")
    # Показать regression metrics если доступны

# Validation results
if hasattr(result_full, 'validation') and result_full.validation:
    nb.log("  Validation analysis available")
    # Показать validation metrics если доступны

nb.success("✅ Regression & Validation через unified pipeline")
```

**Что изменить:**
- Использовать `run_regression=True`, `run_validation=True` в `.analyze()`
- Извлекать результаты из `result.regression`, `result.validation`
- Не создавать analyzers вручную

---

### **ЭТАП 3: Финальная верификация**

**Время:** ~10 минут  
**Приоритет:** ⭐⭐⭐ MANDATORY

---

#### Проверка 3.1: Запуск обновленных notebooks

```bash
# Test 1: 03_zones_universal.py (обновленный)
python research/notebooks/03_zones_universal.py --no-trap
Expected: 
- Exit code 0
- All 11 steps complete (добавлен Step 11: Edge Cases)
- Features extracted для MACD, RSI, AO
- Clustering results shown
- Statistical tests shown
- Sequence analysis shown
- NO комментариев о "баге"

# Test 2: 03_analysis_new_features.py (исправленный)
python research/notebooks/03_analysis_new_features.py --no-trap
Expected:
- Exit code 0
- All 10 steps complete
- Time metrics работают
- Swing strategies работают (FindPeaks, PivotPoints; ZigZag skipped)
- Divergence detection работает
- Volume/Volatility analysis работают
- Hypothesis tests работают
- Regression работает
- Validation работает
```

**Checklist:**
- [ ] 03_zones_universal.py - exit code 0, 11 steps
- [ ] 03_analysis_new_features.py - exit code 0, 10 steps
- [ ] Features для ВСЕХ индикаторов (MACD, RSI, AO)
- [ ] Clustering demonstrated
- [ ] Statistical tests demonstrated
- [ ] Sequence analysis demonstrated
- [ ] Swing strategies работают (2/3)
- [ ] Divergence/Volume/Volatility работают
- [ ] NO устаревших комментариев
- [ ] English output (для cp1251 compatibility)

---

#### Проверка 3.2: Coverage verification

```bash
# Проверить что ВСЕ v2.1 features покрыты
grep "clustering=True" research/notebooks/03_zones_universal.py
grep "swing_strategy=" research/notebooks/03_zones_universal.py
grep "zone.features" research/notebooks/03_analysis_new_features.py
grep "volume_indicator_corr" research/notebooks/*.py

# Проверить что старый API удален
grep "_zone_to_dict" research/notebooks/03_analysis_new_features.py
Expected: NO matches (метод удален)

grep "MACDZoneAnalyzer\(" research/notebooks/03_analysis_new_features.py
Expected: NO matches или только в комментариях (deprecated)
```

**Checklist:**
- [ ] `.analyze()` используется для ВСЕХ индикаторов
- [ ] `clustering=True` в нескольких местах
- [ ] `swing_strategy=` используется
- [ ] `zone.features` вместо `_zone_to_dict()`
- [ ] `volume_indicator_corr` (v2.1 field) упоминается
- [ ] NO calls to deprecated methods

---

## 📊 Детальный план модификации файлов

### 03_zones_universal.py - Modification Plan

**Текущая структура (10 steps):**
- Step 1: Data Loading ✅ OK
- Step 2: Universal API Basics ✅ OK
- Step 3: Detection Strategies ✅ OK
- Step 4: Parameter Sensitivity ✅ OK
- Step 5: Zone Statistics → **ОБНОВИТЬ** (add features, clustering, tests)
- Step 6: Modular Usage ✅ OK (minor updates)
- Step 7: Caching & Persistence ✅ OK
- Step 8: Migration Guide ✅ OK
- Step 9: Other Indicators → **ОБНОВИТЬ** (add .analyze(), feature comparison)
- Step 10: Performance ✅ OK
- Step 11: **ДОБАВИТЬ** (Edge Cases)

**Модификации:**

**1. Module docstring (lines 1-19):**
- Удалить: *"БАГ hardcoded для MACD"*
- Добавить: *"v2.1 UPDATE: ZoneFeaturesAnalyzer универсальный"*
- Добавить: *"Полный pipeline для ВСЕХ индикаторов"*

**2. Step 5 (lines 219-253) → ПЕРЕПИСАТЬ:**
- Переименовать: "Zone Statistics" → "Full Analysis Pipeline Deep Dive"
- Добавить: `.analyze(clustering=True, swing_strategy='find_peaks', ...)`
- Добавить: Feature extraction examples для MACD
- Добавить: Substep 5.4: Clustering Analysis
- Добавить: Substep 5.5: Statistical Tests
- Добавить: Substep 5.6: Sequence Analysis
- Увеличение: ~50-70 lines

**3. Step 9 (lines 434-492) → ПЕРЕПИСАТЬ:**
- Переименовать: "Other Indicators - Detection Examples" → "Multiple Indicators - Feature Comparison"
- Изменить: `.build()` → `.analyze(clustering=True).build()` для RSI и AO
- Добавить: Feature comparison table
- Добавить: Substep 9.1: Zone Overlap Analysis
- Добавить: Substep 9.2: Consensus Signals
- Удалить: Комментарии о "баге"
- Увеличение: ~30-40 lines

**4. Step 11 → ДОБАВИТЬ после Step 10:**
- Новый step: "Edge Cases & Error Handling"
- Substep 11.1: Small Dataset (< 50 bars)
- Substep 11.2: No Zones Detected
- Substep 11.3: Missing Indicator Column
- Substep 11.4: Invalid Parameters
- Новые lines: ~50-60 lines

**Итого: 412 → ~550-580 lines**

---

### 03_analysis_new_features.py - Modification Plan

**Текущая структура (10 steps):**
- Step 1: Базовый анализ ✅ Работает → **ОБНОВИТЬ** (v2.1 API)
- Step 2: Time Metrics ❌ Fails → **ИСПРАВИТЬ** (убрать _zone_to_dict)
- Step 3: Swing Strategies ❌ Not reached → **ИСПРАВИТЬ** (v2.1 API + skip ZigZag)
- Step 4: Divergence ❌ Not reached → **ИСПРАВИТЬ** (use zone.features)
- Step 5: Volatility ❌ Not reached → **ИСПРАВИТЬ** (use zone.features)
- Step 6: Volume ❌ Not reached → **ИСПРАВИТЬ** (use zone.features)
- Step 7: Hypothesis Tests ❌ Not reached → **ИСПРАВИТЬ** (use result.hypothesis_tests)
- Step 8: Regression ❌ Not reached → **ИСПРАВИТЬ** (use result.regression)
- Step 9: Validation ❌ Not reached → **ИСПРАВИТЬ** (use result.validation)
- Step 10: Резюме ❌ Not reached → **ОБНОВИТЬ**

**Модификации:**

**1. Imports (lines 31-43):**
```python
# УДАЛИТЬ:
from bquant.indicators.macd import MACDZoneAnalyzer  # ❌ Deprecated

# ЗАМЕНИТЬ на:
from bquant.analysis.zones import analyze_zones  # ✅ v2.1 universal API
from bquant.analysis.zones.models import ZoneAnalysisResult

# ОСТАВИТЬ (для advanced testing):
from bquant.analysis.zones import ZoneFeaturesAnalyzer  # ✅ Для custom extraction
from bquant.analysis.statistical import HypothesisTestSuite  # ✅ OK
# ... rest of strategy imports
```

**2. Step 1 (lines 54-94) → ОБНОВИТЬ:**
```python
# БЫЛО:
macd_analyzer = MACDZoneAnalyzer(...)
result = macd_analyzer.analyze_complete(df)

# СТАЛО:
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        clustering=True,
        n_clusters=3,
        swing_strategy='find_peaks',
        run_hypothesis=True,
        run_regression=False,  # Опционально
        run_validation=False   # Опционально
    )
    .build()
)
```

**3. Step 2 (lines 96-156) → ИСПРАВИТЬ:**
```python
# БЫЛО:
zone_dict = macd_analyzer._zone_to_dict(zone)  # ❌ AttributeError
features = features_analyzer.extract_zone_features(zone_dict)

# СТАЛО (вариант 1 - использовать zone.features):
for zone in result.zones[:5]:
    if zone.features:  # ✅ Уже extracted после .analyze()
        peak_time_ratio = zone.features.get('peak_time_ratio')
        trough_time_ratio = zone.features.get('trough_time_ratio')
        # ...

# СТАЛО (вариант 2 - custom extraction):
features_analyzer = ZoneFeaturesAnalyzer(...)
for zone in result.zones[:5]:
    # Передаем ZoneInfo напрямую (v2.1 signature)
    zone_data = df.loc[zone.start_index:zone.end_index]
    features = features_analyzer.extract_zone_features(zone, zone_data)
    # ...
```

**4. Steps 3-9 → ПРИМЕНИТЬ тот же паттерн:**
- Использовать `zone.features` для извлечения metrics
- ИЛИ использовать прямой вызов strategy classes для детального тестирования
- Убрать все вызовы `_zone_to_dict()`

**Итого: 693 → ~700-720 lines (minor changes, mostly API updates)**

---

## 📋 Implementation Checklist

### Этап 1: 03_zones_universal.py (40-50 мин)

- [ ] **1.1** Обновить module docstring (удалить "баг", добавить "v2.1 UPDATE")
- [ ] **1.2** Step 5: Переименовать "Zone Statistics" → "Full Analysis Pipeline Deep Dive"
- [ ] **1.3** Step 5.1: Добавить MACD full analysis с `.analyze(clustering=True, swing_strategy='find_peaks')`
- [ ] **1.4** Step 5.2: Показать extracted features (shape, volume, volatility, divergence, swing)
- [ ] **1.5** Step 5.3: Добавить RSI full analysis (proof of universality)
- [ ] **1.6** Step 5.4: Добавить AO full analysis (proof of universality)
- [ ] **1.7** Step 5.5: Добавить Clustering Analysis (распределение, характеристики кластеров)
- [ ] **1.8** Step 5.6: Добавить Statistical Hypothesis Tests (показать result.hypothesis_tests)
- [ ] **1.9** Step 5.7: Добавить Sequence Analysis (transitions, patterns)
- [ ] **1.10** Step 9: Обновить "Other Indicators" → "Multiple Indicators - Feature Comparison"
- [ ] **1.11** Step 9: Добавить `.analyze()` для RSI и AO (не только .build())
- [ ] **1.12** Step 9.1: Добавить Zone Overlap Analysis
- [ ] **1.13** Step 9.2: Добавить Consensus Signals
- [ ] **1.14** Step 11: Добавить новый step "Edge Cases & Error Handling"
- [ ] **1.15** Step 11.1-11.4: Small dataset, No zones, Missing column, Invalid params
- [ ] **1.16** Удалить ВСЕ комментарии о "баге" (lines 6, 10, 437, 451, 485, 551-552)
- [ ] **1.17** Заменить кириллицу на English в print statements (для cp1251 compatibility)
- [ ] **1.18** Финальный тест: `python research/notebooks/03_zones_universal.py --no-trap`

### Этап 2: 03_analysis_new_features.py (50-60 мин)

- [ ] **2.1** Обновить module docstring (добавить "v2.1 UPDATE", описать что тестируется)
- [ ] **2.2** Imports: Заменить `MACDZoneAnalyzer` → `analyze_zones`
- [ ] **2.3** Step 1: Заменить старый API на v2.1 builder pattern
- [ ] **2.4** Step 1: Использовать `.analyze(clustering=True, swing_strategy='find_peaks', run_hypothesis=True)`
- [ ] **2.5** Step 2 (Time Metrics): Убрать `_zone_to_dict()` → использовать `zone.features`
- [ ] **2.6** Step 2: Показать peak_time_ratio, trough_time_ratio из zone.features
- [ ] **2.7** Step 3 (Swing): Обновить на v2.1 API с `swing_strategy=` parameter
- [ ] **2.8** Step 3: Тестировать FindPeaks и PivotPoints (skip ZigZag - Numba issue)
- [ ] **2.9** Step 3: Показать swing metrics из zone.features
- [ ] **2.10** Step 4 (Divergence): Убрать `_zone_to_dict()` → использовать `zone.features`
- [ ] **2.11** Step 4: Показать has_classic_divergence, has_hidden_divergence
- [ ] **2.12** Step 5 (Volatility): Убрать `_zone_to_dict()` → использовать `zone.features`
- [ ] **2.13** Step 5: Показать volatility_expansion, volatility_regime из features
- [ ] **2.14** Step 6 (Volume): Убрать `_zone_to_dict()` → использовать `zone.features`
- [ ] **2.15** Step 6: Показать volume_spike_ratio, **volume_indicator_corr** (v2.1 renamed!)
- [ ] **2.16** Step 7 (Hypothesis): Использовать `result.hypothesis_tests` вместо manual suite
- [ ] **2.17** Step 7: Показать test results из pipeline
- [ ] **2.18** Step 8 (Regression): Использовать `result.regression` если доступно
- [ ] **2.19** Step 9 (Validation): Использовать `result.validation` если доступно
- [ ] **2.20** Step 10: Обновить summary с v2.1 achievements
- [ ] **2.21** Заменить кириллицу на English в print statements
- [ ] **2.22** Финальный тест: `python research/notebooks/03_analysis_new_features.py --no-trap`

### Этап 3: Verification & Documentation (10 мин)

- [ ] **3.1** Запустить оба notebooks с `--no-trap`
- [ ] **3.2** Проверить exit code 0 для обоих
- [ ] **3.3** Проверить что все steps завершены
- [ ] **3.4** Grep проверки (см. Checklist выше)
- [ ] **3.5** Обновить zonan_v2.md (Stage 2.4 verdict → ✅ COMPLETE)
- [ ] **3.6** Обновить CHANGE_TRACE_LOG_2025-10-20.md
- [ ] **3.7** Обновить research/notebooks/README.md (если нужно)

---

## 📐 Детальные решения по компонентам

### Component 1: Feature Extraction (Shape, Volume, Volatility, Divergence, Swing)

**Проблема:**
Notebooks НЕ демонстрируют feature extraction для универсальных индикаторов.

**v2.1 Implementation:**
- `StatisticalShapeStrategy` - универсальный (принимает `indicator_col`)
- `StandardVolumeStrategy` - универсальный (принимает `indicator_col`, использует `volume_indicator_corr`)
- `CombinedVolatilityStrategy` - универсальный
- `ClassicDivergenceStrategy` - универсальный (принимает `indicator_col`, `indicator_line_col`)
- Swing strategies - универсальные (FindPeaks, PivotPoints работают с любыми данными)

**Решение в notebooks:**

**03_zones_universal.py - Step 5:**
```python
# Для КАЖДОГО индикатора показать features:

# MACD features
macd_zone = result_macd_full.zones[0]
nb.log("MACD features:")
nb.log(f"  Shape: skewness={macd_zone.features.get('skewness'):.3f}")
nb.log(f"  Volume: volume_indicator_corr={macd_zone.features.get('volume_indicator_corr'):.3f}")  # v2.1!
nb.log(f"  Volatility: expansion={macd_zone.features.get('volatility_expansion'):.3f}")
nb.log(f"  Divergence: classic={macd_zone.features.get('has_classic_divergence')}")
nb.log(f"  Swing: peak_count={macd_zone.features.get('peak_count')}")

# RSI features (PROOF OF UNIVERSALITY!)
rsi_zone = result_rsi_full.zones[0]
nb.log("RSI features:")
nb.log(f"  Shape: skewness={rsi_zone.features.get('skewness'):.3f}")
nb.log(f"  Volume: volume_indicator_corr={rsi_zone.features.get('volume_indicator_corr'):.3f}")  # v2.1!
nb.success("✅ Same features for RSI! TRUE UNIVERSALITY!")

# AO features (PROOF!)
ao_zone = result_ao_full.zones[0]
nb.log("AO features:")
nb.log(f"  Shape: skewness={ao_zone.features.get('skewness'):.3f}")
nb.success("✅ Same features for AO! TRUE UNIVERSALITY!")
```

**03_analysis_new_features.py - Steps 2-6:**
```python
# Каждый step тестирует одну категорию features детально

# Step 2: Time Metrics
for zone in result.zones[:5]:
    peak_time_ratio = zone.features.get('peak_time_ratio')  # ✅ v2.1
    # ... детальный анализ

# Step 4: Divergence
for zone in result.zones[:10]:
    divergence = zone.features.get('has_classic_divergence')  # ✅ v2.1
    # ... детальный анализ

# Step 6: Volume
for zone in result.zones[:10]:
    volume_indicator_corr = zone.features.get('volume_indicator_corr')  # ✅ v2.1 renamed!
    # ... детальный анализ
```

**Ссылки:**
- zouni_v2.md Phase 1 Tasks 1.3-1.5 (Universal strategies)
- bquant/analysis/zones/strategies/

---

### Component 2: Clustering

**Проблема:**
Clustering реализован, НО НЕ используется в notebooks (все `.build()` без `.analyze()`).

**v2.1 Implementation:**
- `UniversalZoneAnalyzer.analyze_zones()` с `perform_clustering=True`
- `ZoneAnalysisResult.clustering` - Dict[int, int] (zone_id → cluster_id)

**Решение в notebooks:**

**03_zones_universal.py - Step 5.5:**
```python
nb.substep("5.5: Clustering Analysis")

nb.info("Grouping zones by similarity:")

if result_macd_full.clustering:
    clusters = result_macd_full.clustering
    
    nb.log(f"  Clusters created: {len(set(clusters.values()))}")
    nb.log(f"  Zones clustered: {len(clusters)}")
    
    # Распределение
    cluster_distribution = {}
    for cluster_id in clusters.values():
        cluster_distribution[cluster_id] = cluster_distribution.get(cluster_id, 0) + 1
    
    nb.info("  Distribution:")
    for cluster_id, count in sorted(cluster_distribution.items()):
        nb.log(f"    Cluster {cluster_id}: {count} zones")
    
    # Характеристики каждого кластера
    for cluster_id in sorted(set(clusters.values())):
        zones_in_cluster = [z for z in result_macd_full.zones if clusters.get(z.zone_id) == cluster_id]
        
        if zones_in_cluster:
            avg_dur = np.mean([z.duration for z in zones_in_cluster])
            zone_types = [z.type for z in zones_in_cluster]
            bull_pct = sum(1 for t in zone_types if t == 'bull') / len(zone_types) * 100
            
            nb.log(f"    Cluster {cluster_id} characteristics:")
            nb.log(f"      Zones: {len(zones_in_cluster)}")
            nb.log(f"      Avg duration: {avg_dur:.1f} bars")
            nb.log(f"      Bull %: {bull_pct:.1f}%")
    
    nb.success("✅ Clustering helps identify similar zone patterns")
else:
    nb.warning("  Clustering not performed (need more zones)")
```

**Ссылки:**
- bquant/analysis/zones/analyzer.py (clustering implementation)
- zonan.md lines 3939 (clustering spec)

---

### Component 3: Statistical Tests (Hypothesis, Sequence)

**Проблема:**
- HypothesisTestSuite реализован, НО вызывается вручную в 03_analysis_new_features.py
- ZoneSequenceAnalyzer реализован, НО НЕ демонстрируется

**v2.1 Implementation:**
- `UniversalZoneAnalyzer` вызывает HypothesisTestSuite автоматически
- `result.hypothesis_tests` - AnalysisResult object
- `result.sequences` - sequence analysis results

**Решение в notebooks:**

**03_zones_universal.py - Step 5.6:**
```python
nb.substep("5.6: Statistical Hypothesis Tests")

nb.info("Автоматические статистические тесты:")

if result_macd_full.hypothesis_tests:
    tests = result_macd_full.hypothesis_tests
    
    nb.log(f"  Tests executed for {tests.data_size} zones")
    
    if hasattr(tests, 'results') and tests.results:
        nb.info("  Test results:")
        
        for test_name, test_result in tests.results.items():
            if test_result and hasattr(test_result, 'p_value'):
                significance = "significant" if test_result.p_value < 0.05 else "not significant"
                nb.log(f"    {test_name}: p={test_result.p_value:.4f} ({significance})")
        
        nb.success("✅ Statistical validation of zones")
else:
    nb.warning("  Insufficient data for hypothesis tests (need 10+ zones)")

nb.substep("5.7: Sequence Analysis")

nb.info("Zone transitions and patterns:")

if result_macd_full.sequences:
    seq = result_macd_full.sequences
    
    # Transitions
    if hasattr(seq, 'transitions') and seq.transitions:
        nb.info("  Transitions:")
        for trans, count in seq.transitions.items():
            nb.log(f"    {trans}: {count}")
    
    # Patterns
    if hasattr(seq, 'patterns') and seq.patterns:
        nb.log(f"  Patterns detected: {len(seq.patterns)}")
        
        for i, pattern in enumerate(seq.patterns[:3]):
            nb.log(f"    Pattern {i+1}: {pattern}")
    
    nb.success("✅ Sequence analysis reveals zone dynamics")
else:
    nb.warning("  No sequence analysis (need more zones)")
```

**03_analysis_new_features.py - Step 7:**
```python
nb.step("Step 7: Hypothesis Tests via Pipeline")

nb.info("v2.1: Tests автоматически через .analyze():")

result_with_tests = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(run_hypothesis=True)  # ✅ Автоматически
    .build()
)

# Извлечь результаты
if result_with_tests.hypothesis_tests:
    # Детальный анализ каждого теста
    # ...
```

**Ссылки:**
- bquant/analysis/statistical/hypothesis_testing.py
- bquant/analysis/zones/sequence_analysis.py

---

### Component 4: Swing Strategies

**Проблема:**
- Swing strategies реализованы (ZigZag, FindPeaks, PivotPoints)
- НО ZigZag вызывает Numba crash на Windows
- НО НЕ тестируются в notebooks (из-за комментариев о "баге")

**v2.1 Implementation:**
- `swing_strategy='find_peaks'` - работает везде ✅
- `swing_strategy='pivot_points'` - работает везде ✅
- `swing_strategy='zigzag'` - Numba crash на Windows ⚠️

**Решение:**

**03_zones_universal.py - Step 5:**
```python
# Включить swing в analysis
result = analyze_zones(df).detect_zones(...).analyze(
    swing_strategy='find_peaks',  # ✅ RECOMMENDED
    swing_params={'height': 0.001}
).build()

# Показать swing metrics
if zone.features:
    nb.log(f"  Swing: peak_count={zone.features.get('peak_count')}")
    nb.log(f"  Swing: trough_count={zone.features.get('trough_count')}")
```

**03_analysis_new_features.py - Step 3:**
```python
nb.step("Step 3: Swing Strategies Comparison")

# Test FindPeaks
result_findpeaks = analyze_zones(df).analyze(swing_strategy='find_peaks', ...).build()
nb.log(f"  FindPeaks: {sum(1 for z in result_findpeaks.zones if z.features.get('peak_count', 0) > 0)} zones with swings")

# Test PivotPoints
result_pivot = analyze_zones(df).analyze(swing_strategy='pivot_points', ...).build()
nb.log(f"  PivotPoints: {sum(1 for z in result_pivot.zones if z.features.get('peak_count', 0) > 0)} zones with swings")

# ZigZag - SKIP
nb.warning("  ZigZag SKIPPED (Numba crash on Windows - external issue)")
nb.log("  See: devref/gaps/zo/zo_issue_numba_zoneinfo_none.md")

# Comparison
nb.info("  FindPeaks vs PivotPoints:")
# ... сравнение результатов
```

**Ссылки:**
- devref/gaps/zo/zo_issue_numba_zoneinfo_none.md (Numba issue documentation)
- bquant/analysis/zones/strategies/swing/

---

### Component 5: Regression & Validation

**Проблема:**
- Реализованы (ZoneRegressionAnalyzer, ValidationSuite)
- НО вызываются вручную в 03_analysis_new_features.py
- НО могут быть недоступны (зависит от конфигурации)

**v2.1 Implementation:**
- `run_regression=True` в `.analyze()`
- `run_validation=True` в `.analyze()`
- `result.regression` (если доступно)
- `result.validation` (если доступно)

**Решение:**

**03_analysis_new_features.py - Steps 8-9:**
```python
nb.step("Step 8: Regression Analysis via Pipeline")

nb.info("v2.1: Regression через .analyze():")

result_with_regression = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(
        run_regression=True,  # ✅ Попытаться включить
        run_validation=False
    )
    .build()
)

# Проверить доступность
if hasattr(result_with_regression, 'regression') and result_with_regression.regression:
    nb.success("  Regression analysis available")
    # Показать metrics
else:
    nb.warning("  Regression not available (ZoneRegressionAnalyzer not initialized or insufficient data)")

# Аналогично для Validation (Step 9)
```

**Ссылки:**
- bquant/analysis/statistical/regression.py (если существует)
- bquant/analysis/validation/suite.py

---

## 🎯 Expected Outcomes

### После полной реализации плана:

**03_zones_universal.py (~550-580 lines, 11 steps):**
- ✅ Step 5: Full Analysis Pipeline (features, clustering, statistical tests, sequence)
- ✅ Step 9: Multi-indicator feature comparison (overlap, consensus)
- ✅ Step 11: Edge cases (small data, no zones, errors)
- ✅ `.analyze()` для ВСЕХ индикаторов (MACD, RSI, AO)
- ✅ Демонстрация v2.1 universality
- ✅ NO устаревших комментариев о "баге"
- ✅ English output (cp1251 compatible)

**03_analysis_new_features.py (~700-720 lines, 10 steps):**
- ✅ All 10 steps работают (exit code 0)
- ✅ v2.1 universal API (NO deprecated methods)
- ✅ Time Metrics протестированы
- ✅ Swing Strategies протестированы (FindPeaks, PivotPoints; ZigZag skipped)
- ✅ Divergence Detection протестирована
- ✅ Volume Analysis протестирована (`volume_indicator_corr` v2.1!)
- ✅ Volatility Analysis протестирована
- ✅ Hypothesis Tests через pipeline
- ✅ Regression через pipeline (если доступно)
- ✅ Validation через pipeline (если доступно)
- ✅ English output

**Coverage:**
- ✅ 100% v2.1 features продемонстрированы
- ✅ 100% analytical strategies протестированы
- ✅ 100% detection strategies покрыты
- ✅ Multi-indicator universality доказана
- ✅ Edge cases покрыты
- ✅ Advanced features покрыты

---

## 📊 Verification Criteria

### После реализации проверить:

**Functionality:**
- [ ] `python research/notebooks/03_zones_universal.py --no-trap` → exit code 0
- [ ] `python research/notebooks/03_analysis_new_features.py --no-trap` → exit code 0
- [ ] Все steps в обоих notebooks завершены БЕЗ errors

**API Usage:**
- [ ] NO calls to deprecated `MACDZoneAnalyzer` (except в комментариях/примерах)
- [ ] NO calls to `_zone_to_dict()` (метод удален)
- [ ] `.analyze()` используется для ВСЕХ индикаторов (MACD, RSI, AO)
- [ ] `clustering=True` в нескольких местах
- [ ] `swing_strategy=` используется
- [ ] `zone.features` используется напрямую

**v2.1 Features:**
- [ ] `volume_indicator_corr` упоминается (v2.1 renamed field)
- [ ] `indicator_context` inspection в нескольких местах
- [ ] Features extracted для RSI, AO (proof of universality)
- [ ] Clustering results показаны
- [ ] Statistical tests results показаны
- [ ] Sequence analysis results показаны

**Output Quality:**
- [ ] English output (cp1251 compatible)
- [ ] NO UnicodeEncodeError
- [ ] NO устаревших комментариев о "баге"
- [ ] Clear educational value

---

## 📝 Implementation Order

**Рекомендуемый порядок выполнения:**

### Phase 1: Critical Fixes (90 минут)

1. **03_zones_universal.py - Step 5 update** (30 мин)
   - Добавить full analysis для MACD, RSI, AO
   - Показать features, clustering
   - Этапы 1.1-1.9 из Checklist

2. **03_zones_universal.py - Step 9 update** (20 мин)
   - Добавить feature comparison
   - Zone overlap, consensus signals
   - Этапы 1.10-1.13 из Checklist

3. **03_analysis_new_features.py - API migration** (40 мин)
   - Steps 1-6: Replace old API → v2.1
   - Remove _zone_to_dict(), use zone.features
   - Этапы 2.1-2.15 из Checklist

### Phase 2: Additional Features (30 минут)

4. **03_zones_universal.py - Step 11** (15 мин)
   - Edge cases testing
   - Этапы 1.14-1.15 из Checklist

5. **03_analysis_new_features.py - Steps 7-10** (15 мин)
   - Hypothesis/Regression/Validation через pipeline
   - Этапы 2.16-2.20 из Checklist

### Phase 3: Finalization (20 минут)

6. **Cleanup & English** (10 мин)
   - Удалить устаревшие комментарии
   - Заменить кириллицу → English
   - Этапы 1.16-1.17, 2.21 из Checklist

7. **Verification** (10 мин)
   - Запустить оба notebooks
   - Проверить чеклисты
   - Обновить документацию
   - Этап 3 из Checklist

**Total: ~140 минут (2.5 часа)**

---

## 🔗 Reference Links

**Specifications:**
- zonan.md lines 3802-3998 (Stage 2.4 original spec)
- zonan.md lines 3935-3976 (Detailed plan for 03_zones_universal.py)
- zouni_v2.md Phase 1 (Universal architecture)

**Implementations:**
- bquant/analysis/zones/zone_features.py (ZoneFeaturesAnalyzer v2.1)
- bquant/analysis/zones/analyzer.py (UniversalZoneAnalyzer)
- bquant/analysis/zones/strategies/ (All analytical strategies)
- bquant/analysis/statistical/ (HypothesisTestSuite)
- bquant/analysis/zones/sequence_analysis.py (ZoneSequenceAnalyzer)

**Examples:**
- examples/02a_universal_zones.py (v2.1 usage patterns)
- tests/integration/test_truly_universal_zones.py (v2.1 proof tests)

**Issues:**
- devref/gaps/zo/zo_issue_numba_zoneinfo_none.md (ZigZag Numba crash)

---

## 📌 Summary

**Цель:** Обновить research notebooks для ПОЛНОЙ демонстрации v2.1 universal features

**Scope:**
- ✅ Detection pipeline (уже работает)
- ✅ Analysis pipeline (needs update)
- ✅ Advanced features (needs fix)
- ✅ Multi-indicator universality (needs demonstration)

**Ожидаемый результат:**
- ✅ 2/2 notebooks работают (exit code 0, все steps complete)
- ✅ 100% v2.1 features продемонстрированы
- ✅ PROOF: Features work for ALL indicators (not just MACD)
- ✅ Advanced features протестированы (swing, divergence, volume, etc)
- ✅ Edge cases покрыты
- ✅ NO устаревших комментариев
- ✅ English output

**Время:** ~140 минут (2.5 часа) для полной реализации

**Готов начинать по этапам?**

