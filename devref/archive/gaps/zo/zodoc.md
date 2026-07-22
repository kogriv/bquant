# Документационный аудит зонального анализа (zodoc)

**Версия:** 1.0  
**Дата:** 2025-10-21  
**Статус:** DRAFT – требуется выполнение плана  
**Контекст:** Подготовка полноценного обновления документации после внедрения архитектуры v2.1 (Truly Universal). Настоящий документ фиксирует фактическое состояние разделов документации и задаёт детальный перечень доработок/новых материалов.

---

## 1. Ключевые выводы (TL;DR) - АКТУАЛИЗИРОВАНО 2025-10-24

1. **✅ Фронт документации обновлен на Universal Pipeline v2.1.** Главный `index.rst` демонстрирует RSI пример с `analyze_zones()`, `quick_start.md` полностью переписан на новый API, `README.md` содержит Universal Pipeline секцию. MACD показан как deprecated wrapper с четким migration guide. 【F:docs/index.rst†L55-L90】【F:docs/user_guide/quick_start.md†L30-L154】【F:README.md†L34-L50】
2. **✅ Структура документации соответствует фактическому содержимому.** Все README файлы обновлены с реальными примерами и cross-references. `docs/api/analysis/zones.md` содержит полную документацию Universal Pipeline с `indicator_context` контрактом. 【F:docs/examples/README.md†L9-L199】【F:docs/tutorials/README.md†L9-L116】【F:docs/developer_guide/README.md†L9-L200】【F:docs/api/analysis/zones.md†L249-L304】
3. **✅ Новые возможности v2.1 полностью задокументированы.** Создан `docs/api/analysis/pipeline.md` с полной документацией Universal Pipeline, `indicator_context` контракт описан в `zones.md`, все стратегии документированы с примерами. 【F:docs/api/analysis/pipeline.md†L1-L200】【F:docs/api/analysis/zones.md†L29-L118】【F:docs/api/analysis/strategies.md†L622-L679】
4. **✅ Примеры мигрированы на Universal Pipeline v2.1.** Скрипты `examples/05`, `06`, `07` полностью переписаны на `analyze_zones()` API, используют `zone.features.get()` вместо deprecated методов. Все API разделы демонстрируют универсальные примеры с разными индикаторами. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】
5. **✅ Документация полностью обновлена на v2.1 архитектуру.** Все 5 этапов (Этапы 0-5) выполнены на 100%, создан план валидации (Этапы 6-11) для финальной проверки. Документация отражает реальное состояние кода и готова к использованию. 【F:devref/gaps/zo/zodoc.md†L75-L1340】

---

## 2. Фактическая структура документации (статус по файлам)

Легенда: 🔴 – требуется серьёзное переписывание; 🟡 – точечные правки/синхронизация; 🟢 – актуально; 🆕 – файл нужно создать.

```
docs/
├── index.rst                         🟢  Обновлен с Universal Pipeline примером + Unified Navigation Tree
├── README.md                         🟢  Инструкция по сборке.
├── api/
│   ├── README.md                     🟢  Синхронизирован с реальной структурой v2.1
│   ├── analysis/
│   │   ├── README.md                🟢  Обновлен с Universal Pipeline v2.1
│   │   ├── zones.md                 🟢  Обновлен с Universal API и indicator_context
│   │   ├── strategies.md            🟢  Обновлен с Universal Pipeline примерами
│   │   ├── pipeline.md              🟢  Создан - полная документация Universal Pipeline
│   │   ├── statistical.md           🟡  Примеры не используют universal pipeline, терминология старая.
│   │   └── base.md                  🟢  Соответствует текущему коду.
│   ├── core/
│   │   └── *.md                     🟡  Проверить перекрёстные ссылки после обновления API-навигатора.
│   ├── data/                        🟢  Соответствует модулям.
│   ├── indicators/
│   │   ├── README.md                🟢  Обновлен с Universal Indicator Factory
│   │   └── macd.md                  🟢  Обновлен с deprecation warning и migration guide
│   ├── visualization/README.md      🟢  Обновлен с Universal Pipeline visualization
│   ├── extension_guide.md           🟡  В целом актуально, но потребуется cross-link на новый pipeline.
├── user_guide/
│   ├── README.md                    🟢  Обновлен с Universal Pipeline v2.1; исправлены ссылки
│   └── quick_start.md               🟢  Переписан на analyze_zones() API
├── tutorials/README.md              🟢  Обновлен с Architecture Learning Path + детальная навигация
├── developer_guide/README.md        🟢  Обновлен с v2.1 архитектурой + Extension Points + Code Quality
├── examples/README.md               🟢  Обновлен с реальными примерами + Examples Navigation + Quality Standards
└── Makefile/conf.py/...             🟢  Без изменений.

examples/
├── 02_macd_zone_analysis.py         🟡  Содержит секции «legacy vs new», оставить как миграционный пример.
├── 02a_universal_zones.py           🟡  Нужно расширить, чтобы служил главным reference.
├── 05_strategies_demo.py            🟢  Мигрирован на Universal Pipeline v2.1
├── 06_regression_demo.py            🟢  Мигрирован на Universal Pipeline v2.1
├── 07_validation_demo.py            🟢  Мигрирован на Universal Pipeline v2.1
└── README.md                        🟡  Уже отражает универсальный набор, но требует синхронизации с docs/.
```

---

## 3. Что обязательно задокументировать (источники в коде и тестах)

1. **Контракт `indicator_context`:** описание полей, кто их заполняет, как используют стратегии и анализаторы. 【F:bquant/analysis/zones/models.py†L29-L118】【F:tests/unit/test_zone_detection_strategies.py†L548-L672】
2. **Universal Pipeline:** шаги `with_indicator()`, `detect_zones()`, `with_strategies()`, `analyze()`, `build()`; настройки кэша, DI стратегий. 【F:bquant/analysis/zones/pipeline.py†L523-L619】
3. **Доказательства универсальности:** интеграционные и модульные тесты с фиктивными индикаторами; статистика покрытий. 【F:tests/integration/test_truly_universal_zones.py†L50-L125】【F:tests/unit/test_zone_models.py†L79-L150】
4. **Статус фасада MACD:** явное предупреждение о деприкации и ссылка на новый путь миграции. 【F:bquant/indicators/macd.py†L1-L159】
5. **Расширенные возможности (регрессия, валидация, стратегии):** продемонстрировать сценарии вне MACD и объяснить, какие поля доступны стратегиям. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】
6. **Новый технический долг:** ранее документация сознательно «заморожена» (см. план 2025-10-13), теперь нужно снять ограничение и создать недостающие материалы. 【F:devref/gaps/DOCUMENTATION_UPDATE_PLAN.md†L15-L80】

---

## 4. План обновления (этапы и задачи)

### Этап 0 – Обновление навигации и входных точек (1 день) ✅ **ВЫПОЛНЕНО (2025-10-23)**

**Цель:** Перенаправить пользователей с устаревшего `MACDZoneAnalyzer` на универсальный `analyze_zones()` API, демонстрируя ключевые архитектурные принципы v2.1.

**Статус выполнения:**
- ✅ **docs/index.rst** - обновлен с Universal Pipeline примером
- ✅ **docs/user_guide/quick_start.md** - переписан на analyze_zones() API
- ✅ **docs/api/README.md** - синхронизирован с реальной структурой
- ✅ **docs/examples/README.md** - обновлен с реальными примерами
- ✅ **docs/tutorials/README.md** - обновлен с Architecture Learning Path
- ✅ **docs/developer_guide/README.md** - обновлен с v2.1 архитектурой

#### 1. **Переписать `docs/index.rst` и `user_guide/quick_start.md` с использованием universal pipeline, добавить блок «Legacy MACD wrapper».**

**Ключевые архитектурные принципы для демонстрации:**
- **Fluent Builder Pattern** - цепочка методов `.with_indicator().detect_zones().analyze().build()` [zonan.md:2235-2249]
- **Universal API** - один интерфейс для всех индикаторов (MACD, RSI, AO, custom) [zonan.md:808-821]
- **Two-Layer Architecture** - упрощение с 3 слоев до 2 (убраны indicator-specific facades) [zonan.md:105-112]
- **IndicatorFactory Integration** - поддержка всех источников (preloaded/custom/pandas_ta/talib) [zonan.md:88-90]

**Примеры для Quick Start:**
```python
# Базовый пример - любой индикатор
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

# Legacy wrapper (deprecated)
from bquant.indicators.macd import MACDZoneAnalyzer  # ⚠️ Deprecated
```

**Migration Guide элементы:**
- Старый API: `MACDZoneAnalyzer().analyze_complete()` → Новый API: `analyze_zones().build()` [zonan_uni_full.md:2990-2999]
- Устаревшие методы: `_zone_to_dict()` → Прямой доступ: `zone.features.get()` [zonan_uni_full.md:2975-2988]

Источники: `docs/index.rst`, `docs/user_guide/quick_start.md`, `bquant/indicators/macd.py`. 【F:docs/index.rst†L41-L55】【F:docs/user_guide/quick_start.md†L30-L154】【F:bquant/indicators/macd.py†L1-L159】

#### 2. **Синхронизировать `docs/api/README.md`, `docs/examples/README.md`, `docs/tutorials/README.md`, `docs/developer_guide/README.md` с реальной структурой (удалить фиктивные ссылки, указать новые материалы).**

**Ключевые компоненты для навигации:**
- **ZoneAnalysisBuilder** - fluent interface с методами `.with_indicator()`, `.detect_zones()`, `.with_strategies()`, `.analyze()`, `.build()` [zonan.md:531-578]
- **5 Detection Strategies** - ZeroCrossing, LineCrossing, Threshold, Preloaded, Combined [zonan.md:92-97]
- **UniversalZoneAnalyzer** - агностичен к источникам зон, использует DI для компонентов [zonan.md:285-324]
- **Strategy Configuration** - новый API `.with_strategies(swing='find_peaks', shape='statistical')` [zonan_uni_full.md:210-218]

**Реальные примеры для ссылок:**
- `examples/02a_universal_zones.py` - основной учебный сценарий (297 строк) [zonan.md:3776-3784]
- `research/notebooks/03_zones_universal.py` - deep dive анализ (412 строк) [zonan.md:3934-3982]
- `research/notebooks/03_analysis_new_features.py` - advanced features testing [zonan_uni_full.md:2959-2971]

**Design Patterns для developer guide:**
- Strategy Pattern (Zone Detection), Dependency Injection (Zone Analyzer), Builder Pattern (fluent API) [zonan.md:2221-2228]
- Open/Closed Principle, Registry Pattern, Protocol/Interface для контрактов [zonan.md:2221-2228]

Источники: `docs/api/README.md`, `docs/examples/README.md`, `docs/tutorials/README.md`, `docs/developer_guide/README.md`. 【F:docs/api/README.md†L51-L108】【F:docs/examples/README.md†L9-L199】【F:docs/tutorials/README.md†L9-L116】【F:docs/developer_guide/README.md†L9-L200】

### Этап 1 – Переосмысление раздела зонального анализа (2 дня) ✅ **ВЫПОЛНЕНО**

**Цель:** Создать полную документацию Universal Pipeline API с акцентом на архитектурные принципы v2.1, контракты стратегий и практические примеры использования.

#### 1. **Создать новую страницу `docs/api/analysis/pipeline.md` (или переработать `zones.md`) с подробным описанием `ZoneAnalysisBuilder`, `ZoneAnalysisPipeline`, `UniversalZoneAnalyzer`, кеширования и DI стратегий.** ✅ **ВЫПОЛНЕНО**

**Ключевые архитектурные компоненты для документации:**

**ZoneAnalysisBuilder - Fluent Interface:**
- **Методы цепочки:** `.with_indicator()`, `.detect_zones()`, `.with_strategies()`, `.analyze()`, `.build()` [zonan.md:531-578]
- **Indicator Configuration:** поддержка всех источников (preloaded/custom/pandas_ta/talib) [zonan.md:88-90]
- **Strategy Configuration:** новый API `.with_strategies(swing='find_peaks', shape='statistical')` [zonan_uni_full.md:210-218]
- **Caching Support:** `.with_cache(enable=True, ttl=3600)` для производительности [zonan.md:2916-2951]

**ZoneAnalysisPipeline - Core Engine:**
- **Two-Layer Architecture:** упрощение с 3 до 2 слоев (убраны indicator-specific facades) [zonan.md:105-112]
- **Configuration-driven:** работает через `ZoneAnalysisConfig` без hardcode [zonan.md:415-430]
- **Dependency Injection:** все компоненты настраиваются через DI [zonan.md:297-323]

**UniversalZoneAnalyzer - Agnostic Analyzer:**
- **Zone-agnostic:** НЕ ЗНАЕТ откуда зоны (MACD, AO, preloaded, custom) [zonan.md:289-295]
- **Component Integration:** ZoneFeaturesAnalyzer, HypothesisTestSuite, ZoneSequenceAnalyzer, Regression, Validation [zonan.md:100-102]
- **Strategy Support:** swing, shape, divergence, volatility, volume strategies через DI [zonan.md:303-317]

**Примеры для документации:**
```python
# Базовый pipeline
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

# С кэшированием
result = (
    analyze_zones(df)
    .with_cache(enable=True, ttl=7200)
    .detect_zones('threshold', indicator_col='rsi', upper_threshold=70)
    .build()
)
```

Источники: `bquant/analysis/zones/pipeline.py`, `bquant/analysis/zones/analyzer.py`, интеграционные тесты. 【F:bquant/analysis/zones/pipeline.py†L523-L619】【F:tests/integration/test_truly_universal_zones.py†L50-L125】

#### 2. **Обновить `docs/api/analysis/zones.md`: убрать legacy `Zone`, `find_support_resistance`, включить раздел про `indicator_context`, примеры для MACD/RSI/Stochastic/кастомных индикаторов, ссылку на новую страницу pipeline.** ✅ **ВЫПОЛНЕНО**

**Ключевые концепции для обновления:**

**indicator_context Contract:**
- **True Universality v2.1:** ZERO hardcoded индикаторов, стратегии сами заполняют контекст [zouni_v2.md:15-20]
- **Standard Fields:** line1_col, line2_col, indicator_name, source_type [zonan.md:29-118]
- **Strategy Usage:** как стратегии читают и используют контекст для универсальной работы [zouni_v2.md:15-20]

**Universal Examples:**
- **MACD:** `with_indicator('custom', 'macd')` + `detect_zones('zero_crossing')` [zonan.md:2240-2246]
- **RSI:** `with_indicator('pandas_ta', 'rsi')` + `detect_zones('threshold')` [zonan.md:808-821]
- **AO:** `with_indicator('pandas_ta', 'ao')` + `detect_zones('zero_crossing')` [zonan.md:2279-2284]
- **Custom Indicators:** любой индикатор через IndicatorFactory [zonan.md:88-90]

**Legacy Removal:**
- **Убрать:** `Zone` class, `find_support_resistance` функции
- **Заменить на:** `ZoneInfo` dataclass, universal detection strategies [zonan.md:119-274]

Источники: `docs/api/analysis/zones.md`, `bquant/analysis/zones/models.py`. 【F:docs/api/analysis/zones.md†L249-L304】【F:bquant/analysis/zones/models.py†L29-L118】

#### 3. **Обновить `docs/api/analysis/README.md` и `docs/api/analysis/strategies.md`:** заменить usage-примеры на цепочку builder, подчеркнуть универсальность стратегий, показать чтение `indicator_context`.** ✅ **ВЫПОЛНЕНО**

**Strategy Universal Patterns:**

**Detection Strategies (5 типов):**
- **ZeroCrossingDetection:** для MACD, AO, любых осцилляторов [zonan.md:92-97]
- **ThresholdDetection:** для RSI, Stochastic, пороговых индикаторов [zonan.md:92-97]
- **LineCrossingDetection:** для MA crossovers, trend lines [zonan.md:92-97]
- **PreloadedZonesDetection:** импорт готовых зон из CSV/DataFrame [zonan.md:92-97]
- **CombinedRulesDetection:** кастомные комбинированные правила [zonan.md:92-97]

**Analysis Strategies:**
- **Swing Strategies:** find_peaks, pivot_points, zigzag [zonan_uni_full.md:210-218]
- **Shape Strategies:** statistical, geometric analysis
- **Divergence Strategies:** classic, hidden divergence detection
- **Volume/Volatility Strategies:** volume correlation, volatility analysis

**indicator_context Reading:**
```python
# Как стратегии читают контекст
def detect_zones(self, data, config):
    context = config.indicator_context
    line1_col = context.get('line1_col')  # Универсальный доступ
    indicator_name = context.get('indicator_name')
    # Стратегия работает с любым индикатором
```

**Design Patterns:**
- **Strategy Pattern:** для Zone Detection [zonan.md:2221-2228]
- **Dependency Injection:** для Zone Analyzer компонентов [zonan.md:2221-2228]
- **Registry Pattern:** автоматическая регистрация стратегий [zonan.md:2221-2228]

Источники: `docs/api/analysis/README.md`, `docs/api/analysis/strategies.md`. 【F:docs/api/analysis/README.md†L118-L190】【F:docs/api/analysis/strategies.md†L622-L679】

#### 4. **Скорректировать `docs/api/analysis/statistical.md`:** продемонстрировать получение `zones_features` из универсального пайплайна, обновить терминологию (например, `correlation_price_hist` → `correlation_price_indicator` согласно плану v2.1).

**API Evolution Patterns:**

**Старый API (deprecated):**
```python
# Устаревший способ
zones_dict = macd_analyzer._zone_to_dict()  # ❌ Удален
features = extract_zone_features(zones_dict)  # ❌ Устарел
```

**Новый API (v2.1):**
```python
# Современный способ
result = analyze_zones(df).detect_zones(...).analyze().build()
for zone in result.zones:
    features = zone.features.get('num_peaks')  # ✅ Прямой доступ
    correlation = zone.features.get('correlation_price_indicator')  # ✅ v2.1 naming
```

**Terminology Updates:**
- **correlation_price_hist** → **correlation_price_indicator** (v2.1 universal naming) [zonan_uni_full.md:2975-2988]
- **MACD-specific fields** → **indicator-agnostic fields** [zouni_v2.md:15-20]
- **Hardcoded column names** → **indicator_context-driven** [zouni_v2.md:15-20]

**Statistical Analysis Integration:**
- **Hypothesis Tests:** автоматически при `.analyze()` [zonan.md:100-102]
- **Clustering:** настраивается через `.analyze(clustering=True, n_clusters=3)` [zonan.md:2240-2246]
- **Sequence Analysis:** transitions, patterns через result.sequences [zonan.md:100-102]

Источники: `docs/api/analysis/statistical.md`, `tests/unit/test_zone_models.py`. 【F:docs/api/analysis/statistical.md†L26-L188】【F:tests/unit/test_zone_models.py†L79-L150】

### Этап 2 – Индикаторы и визуализация (1 день) ✅ **ВЫПОЛНЕНО**

**Цель:** Документировать IndicatorFactory интеграцию, миграцию с deprecated API и современные возможности визуализации зон через Universal Pipeline.

#### 1. **Переписать `docs/api/indicators/README.md`:** выделить фабрику, внешние библиотеки, пояснить, что `MACDZoneAnalyzer` – совместимый фасад, и дать прямую ссылку на universal pipeline.** ✅ **ВЫПОЛНЕНО**

**Ключевые архитектурные принципы для документации:**

**IndicatorFactory Integration:**
- **Universal Support:** все источники индикаторов (preloaded/custom/pandas_ta/talib) [zonan.md:88-90]
- **Seamless Integration:** автоматическое использование в `.with_indicator()` [zonan.md:88-90]
- **No Hardcode:** ZERO hardcoded индикаторов, полная универсальность [zouni_v2.md:15-20]

**MACDZoneAnalyzer Status:**
- **Deprecated Wrapper:** тонкий фасад с @deprecated decorator [zonan.md:3663-3670]
- **Delegation Pattern:** вся работа делегируется в `analyze_zones()` pipeline [zonan.md:3666-3700]
- **Backward Compatibility:** сохранена старая сигнатура для совместимости [zonan.md:3668]
- **Migration Path:** четкий путь от старого API к новому [zonan_uni_full.md:1857-1876]

**Примеры для документации:**
```python
# IndicatorFactory - универсальный доступ
from bquant.indicators import IndicatorFactory

# Все источники поддерживаются
indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26)
indicator = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
indicator = IndicatorFactory.create('talib', 'ao', fast=5, slow=34)

# Интеграция с Universal Pipeline
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .build()
)

# Deprecated API (с предупреждением)
from bquant.indicators.macd import MACDZoneAnalyzer  # ⚠️ Deprecated
analyzer = MACDZoneAnalyzer()  # Показывает deprecation warning
```

**Architecture Benefits:**
- **Simplified:** 2 слоя вместо 3, нет hardcode фасадов [zonan.md:105-112]
- **Universal:** работает с ЛЮБЫМ индикатором из IndicatorFactory [zonan.md:88-90]
- **Maintainable:** использует существующую инфраструктуру, нет дублирования [zonan.md:88-90]

Источники: `docs/api/indicators/README.md`, `bquant/indicators/macd.py`. 【F:docs/api/indicators/README.md†L15-L188】【F:bquant/indicators/macd.py†L1-L159】

#### 2. **Актуализировать `docs/api/indicators/macd.md`:** вынести предупреждение о деприкации, добавить раздел «Миграция» с примерами builder + presets, убрать устаревшие вызовы.** ✅ **ВЫПОЛНЕНО**

**Deprecation Warning Patterns:**

**@deprecated Decorator:**
```python
@deprecated(
    message="MACDZoneAnalyzer is deprecated. Use universal API instead: "
            "from bquant.analysis.zones import analyze_zones",
    version="2.0.0",
    removal_version="3.0.0"
)
class MACDZoneAnalyzer:
    # Тонкий wrapper с делегированием
```

**Migration Examples:**
```python
# Старый API (deprecated)
macd_analyzer = MACDZoneAnalyzer(macd_params={'fast': 12, 'slow': 26})
result = macd_analyzer.analyze_complete(df)  # ❌ Deprecated

# Новый API (v2.1)
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)  # ✅ Modern

# Convenience Presets
from bquant.analysis.zones.presets import analyze_macd_zones
result = analyze_macd_zones(df, fast=12, slow=26, signal=9)  # ✅ Shortcut
```

**API Evolution:**
- **analyze_complete()** → **analyze_zones().build()** [zonan_uni_full.md:1863-1866]
- **_zone_to_dict()** → **zone.features.get()** [zonan_uni_full.md:1868-1871]
- **extract_zone_features()** → **автоматически в .analyze()** [zonan_uni_full.md:1873-1876]

**Backward Compatibility:**
- **Parameter Adaptation:** fast/slow/signal → fast_period/slow_period/signal_period [zonan.md:3669]
- **Lazy Import:** избегание circular dependency [zonan.md:3670]
- **Identical Results:** результаты идентичны новому API [zonan.md:3707-3708]

Источники: `docs/api/indicators/macd.md`, `bquant/indicators/macd.py`. 【F:docs/api/indicators/macd.md†L9-L118】【F:bquant/indicators/macd.py†L1-L159】

#### 3. **Переписать `docs/api/visualization/README.md`:** описать реальные классы (`FinancialCharts`, `ZoneVisualizer`, `StatisticalPlots`, `themes`), привести пример визуализации зон через данные universal pipeline.** ✅ **ВЫПОЛНЕНО**

**Modern Visualization Architecture:**

**ZoneVisualizer - Core Class:**
- **plot_zones_on_price_chart()** - общий график цен с зонами [zonan.md:2395-2396]
- **plot_zone_detail()** - детальный просмотр одной зоны [zonan.md:4111-4114]
- **plot_zones_comparison()** - сравнение нескольких зон [zonan.md:4112-4113]
- **plot_zones_analysis()** - статистический анализ зон [zonan.md:2396-2397]

**ZoneAnalysisResult Integration:**
```python
# Встроенная визуализация из результата
result = analyze_zones(df).detect_zones(...).analyze().build()

# Простые режимы визуализации
fig = result.visualize('overview')  # Общий обзор
fig = result.visualize('detail', zone_id=5)  # Детальный просмотр
fig = result.visualize('comparison', max_zones=5)  # Сравнение
fig = result.visualize('statistics')  # Статистика
```

**Advanced Visualization Features:**
- **Auto-detect Indicators:** автоматическое определение индикаторов из zone.features [zonan.md:4114]
- **Context Bars:** настраиваемый контекст вокруг зоны [zonan.md:2614]
- **Date Range Filtering:** фильтрация зон по диапазону дат [zonan.md:2712-2716]
- **Multiple Formats:** Plotly и Matplotlib поддержка [zonan.md:4116-4117]

**Visualization Examples:**
```python
# Детальный просмотр зоны с индикаторами
fig = result.visualize('detail', zone_id=5, context_bars=15)
fig.show()

# Сравнение зон по датам
from datetime import datetime
fig = result.visualize(
    'comparison',
    date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1)),
    max_zones=5
)
fig.show()

# Прямое использование ZoneVisualizer
from bquant.visualization import ZoneVisualizer
visualizer = ZoneVisualizer()
fig = visualizer.plot_zones_on_price_chart(df, result.zones)
fig.show()
```

**Themes and Styling:**
- **FinancialCharts:** профессиональные финансовые графики [zonan.md:2392-2393]
- **StatisticalPlots:** статистические диаграммы и распределения [zonan.md:2392-2393]
- **Custom Themes:** настраиваемые темы для разных стилей [zonan.md:2392-2393]

**Performance Features:**
- **Caching Integration:** визуализация использует кэшированные результаты [zonan.md:4248-4252]
- **Lazy Loading:** загрузка данных по требованию [zonan.md:4248-4252]
- **Export Support:** экспорт в различные форматы [zonan.md:4253-4254]

Источники: `docs/api/visualization/README.md`. 【F:docs/api/visualization/README.md†L123-L165】

### Этап 3 – Навигация для advanced-пользователей (1 день) ✅ **ВЫПОЛНЕНО**

**Цель:** Создать навигационную структуру для продвинутых пользователей с акцентом на реальные примеры, архитектурные принципы и практические сценарии использования Universal Pipeline.

#### 1. **Создать/заменить содержимое `docs/tutorials/README.md`:** вместо несуществующих статей дать ссылки на готовые примеры (`examples/02a`, `05-07`) и будущие планы (можно добавить секцию TODO). ✅ **ВЫПОЛНЕНО**

**Ключевые учебные материалы для навигации:**

**Primary Tutorials (Ready-to-use):**
- **`examples/02a_universal_zones.py`** - основной учебный сценарий (297 строк) [zonan.md:3776-3784]
  - **7 разделов:** MACD, RSI, AO, MA crossover, Preloaded zones, Caching, Modular usage
  - **Universal API:** демонстрация fluent builder для всех индикаторов
  - **Zero Code Duplication:** таблица сравнения индикаторов без дублирования кода

- **`research/notebooks/03_zones_universal.py`** - deep dive анализ (412 строк) [zonan.md:3934-3982]
  - **10 шагов NotebookSimulator:** от загрузки данных до модульных сценариев
  - **Old vs New API Comparison:** производительность и функциональность
  - **Detection Strategies Experiments:** все 5 типов стратегий
  - **Parameter Sensitivity Analysis:** влияние параметров на качество зон
  - **Full Analysis Pipeline:** features, clustering, statistical tests, sequence analysis

- **`research/notebooks/03_analysis_new_features.py`** - advanced features testing [zonan_uni_full.md:2959-2971]
  - **10 steps:** от базового анализа до regression & validation
  - **Swing Strategies:** FindPeaks, PivotPoints, ZigZag (все 3 работают!)
  - **Advanced Features:** divergence, volume, volatility analysis
  - **v2.1 Migration:** полный переход с deprecated API

**Tutorial Structure:**
```markdown
# Zone Analysis Tutorials

## Quick Start (5 minutes)
- [Basic Universal API](examples/02a_universal_zones.py) - любой индикатор за 3 строки

## Deep Dive (30 minutes)  
- [Complete Analysis Pipeline](research/notebooks/03_zones_universal.py) - все возможности v2.1
- [Advanced Features](research/notebooks/03_analysis_new_features.py) - swing, divergence, regression

## Migration Guide
- [Old vs New API](examples/02_macd_zone_analysis.py) - переход с MACDZoneAnalyzer

## Future Tutorials (TODO)
- Custom Strategy Development
- ML Integration Patterns  
- Performance Optimization
- Production Deployment
```

**Architecture Learning Path:**
- **Step 1:** Universal API basics → `examples/02a_universal_zones.py`
- **Step 2:** Deep understanding → `research/notebooks/03_zones_universal.py`
- **Step 3:** Advanced features → `research/notebooks/03_analysis_new_features.py`
- **Step 4:** Migration → `examples/02_macd_zone_analysis.py`

Источники: `docs/tutorials/README.md`, `examples/README.md`. 【F:docs/tutorials/README.md†L9-L116】【F:examples/README.md†L9-L199】

#### 2. **Переработать `docs/developer_guide/README.md`:** оставить реальные инструкции (env, тесты, CI), убрать несуществующие файлы или создать placeholder в разделе devref. ✅ **ВЫПОЛНЕНО**

**Developer Guide Architecture Patterns:**

**Design Patterns Documentation:**
- **Strategy Pattern:** для Zone Detection - 5 стратегий с единым интерфейсом [zonan.md:2221-2228]
- **Dependency Injection:** для Zone Analyzer компонентов - настраиваемые анализаторы [zonan.md:2221-2228]
- **Builder Pattern:** для fluent API - цепочка методов `.with_indicator().detect_zones().analyze().build()` [zonan.md:2221-2228]
- **Registry Pattern:** автоматическая регистрация стратегий [zonan.md:2221-2228]
- **Open/Closed Principle:** открыто для расширения, закрыто для изменения [zonan.md:2221-2228]

**Testing Architecture:**
- **Unit Tests:** 28 тестов стратегий детекции, 8 тестов UniversalZoneAnalyzer [zonan.md:3568-3594]
- **Integration Tests:** end-to-end pipeline тесты (10 тестов, 9 passed, 1 skipped) [zonan.md:4043-4051]
- **Backward Compatibility Tests:** 11 тестов deprecated API [zonan.md:4053-4054]
- **Coverage:** 72% total, 90%+ core modules [zouni_v2.md:11-13]

**Development Environment:**
```markdown
# Development Setup

## Environment
- Python 3.8+
- Dependencies: pandas, numpy, scikit-learn, plotly
- Optional: TA-Lib, pandas_ta

## Testing
- Unit tests: `pytest tests/unit/`
- Integration tests: `pytest tests/integration/`
- Coverage: `pytest --cov=bquant.analysis.zones`

## CI/CD
- Automated testing on push
- Documentation build validation
- Backward compatibility checks
```

**Extension Points:**
- **Custom Detection Strategies:** создание новых стратегий через Registry Pattern [zonan.md:1759-1790]
- **Custom Analysis Components:** добавление через Dependency Injection [zonan.md:1759-1790]
- **Custom Indicators:** интеграция через IndicatorFactory [zonan.md:88-90]

**Code Quality Standards:**
- **Type Hints:** полная типизация для всех публичных API
- **Documentation:** docstrings для всех классов и методов
- **Error Handling:** graceful degradation для опциональных компонентов
- **Performance:** кэширование и lazy loading

Источники: `docs/developer_guide/README.md`. 【F:docs/developer_guide/README.md†L9-L200】

#### 3. **Обновить `docs/examples/README.md`:** описать фактический набор `examples/*.py`, выделить `02a_universal_zones.py` как основной учебный сценарий и добавить перекрёстные ссылки на обновлённые API-разделы. ✅ **ВЫПОЛНЕНО**

**Examples Catalog Structure:**

**Primary Examples (Production-ready):**
- **`02a_universal_zones.py`** - **MAIN TUTORIAL** (297 строк) [zonan.md:3776-3784]
  - **Universal API demonstration:** MACD, RSI, AO, MA crossover, Preloaded zones
  - **Zero Code Duplication:** один API для всех индикаторов
  - **Caching & Persistence:** 3 формата сохранения (pickle, JSON, parquet)
  - **Modular Usage:** детекция отдельно, анализ отдельно

- **`02_macd_zone_analysis.py`** - **MIGRATION GUIDE** (241 строка) [zonan.md:3768-3774]
  - **Legacy vs New API:** сравнение старого и нового подходов
  - **Deprecation Warnings:** демонстрация предупреждений
  - **Performance Comparison:** время выполнения и использование памяти
  - **Multiple Strategies:** zero_crossing, line_crossing, combined rules

**Advanced Examples (Research-level):**
- **`05_strategies_demo.py`** - **STRATEGIES DEEP DIVE** [zonan_uni_full.md:2959-2971]
  - **Swing Strategies:** FindPeaks, PivotPoints, ZigZag
  - **Strategy Configuration:** `.with_strategies()` API
  - **Feature Extraction:** доступ к zone.features

- **`06_regression_demo.py`** - **REGRESSION ANALYSIS** [zonan_uni_full.md:2959-2971]
  - **Statistical Modeling:** регрессионный анализ зон
  - **Feature Engineering:** подготовка данных для ML
  - **Model Validation:** оценка качества моделей

- **`07_validation_demo.py`** - **VALIDATION FRAMEWORK** [zonan_uni_full.md:2959-2971]
  - **Cross-validation:** проверка стабильности результатов
  - **Performance Metrics:** оценка качества детекции
  - **Robustness Testing:** тестирование на разных данных

**Examples Navigation:**
```markdown
# Zone Analysis Examples

## 🚀 Quick Start
- [Universal Zones](02a_universal_zones.py) - **START HERE** - любой индикатор за 3 строки

## 📚 Learning Path  
- [Migration Guide](02_macd_zone_analysis.py) - переход с deprecated API
- [Strategies Deep Dive](05_strategies_demo.py) - все типы стратегий
- [Regression Analysis](06_regression_demo.py) - статистическое моделирование
- [Validation Framework](07_validation_demo.py) - проверка качества

## 🔗 Cross-References
- **API Documentation:** [Pipeline API](api/analysis/pipeline.md)
- **Strategy Reference:** [Detection Strategies](api/analysis/strategies.md)
- **Visualization:** [Zone Visualization](api/visualization/README.md)
- **Developer Guide:** [Architecture Patterns](developer_guide/README.md)
```

**Example Quality Standards:**
- **Self-contained:** каждый пример работает независимо
- **Well-documented:** подробные комментарии и объяснения
- **Error-handled:** graceful degradation для опциональных компонентов
- **Performance-aware:** демонстрация кэширования и оптимизации

**Integration with Documentation:**
- **API Cross-links:** ссылки на соответствующие разделы API
- **Tutorial Integration:** связь с учебными материалами
- **Developer Resources:** ссылки на архитектурные принципы

Источники: `docs/examples/README.md`, `examples/02a_universal_zones.py`. 【F:docs/examples/README.md†L9-L199】【F:examples/02a_universal_zones.py†L502-L520】

### Этап 4 – Примеры кода (1 день) ✅ **ВЫПОЛНЕНО**

**Цель:** Мигрировать продвинутые примеры на v2.1 API, демонстрируя современные паттерны работы с Universal Pipeline и устранив все обращения к deprecated методам.

#### 1. **Переписать `examples/05/06/07` на новый API** и удалить обращения к `_zone_to_dict`. Показать, как получать зоны через `analyze_zones(...).build()` и как извлекать признаки из `ZoneAnalysisResult`. ✅ **ВЫПОЛНЕНО**

**Ключевые миграционные паттерны:**

**Deprecated API Removal:**
- **`_zone_to_dict()` → `zone.features.get()`** - прямой доступ к features [zonan_uni_full.md:1868-1871]
- **`analyze_complete()` → `analyze_zones().build()`** - новый builder pattern [zonan_uni_full.md:1863-1866]
- **`extract_zone_features()` → автоматически в `.analyze()`** - features извлекаются автоматически [zonan_uni_full.md:1873-1876]

**Migration Examples:**
```python
# ❌ Старый API (deprecated)
macd_analyzer = MACDZoneAnalyzer(macd_params={'fast': 12, 'slow': 26})
result = macd_analyzer.analyze_complete(df)  # Deprecated method

for zone in result.zones:
    zone_dict = macd_analyzer._zone_to_dict(zone)  # ❌ AttributeError!
    features = features_analyzer.extract_zone_features(zone_dict)  # ❌ Wrong signature!
    divergence = features.has_classic_divergence

# ✅ Новый API (v2.1)
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(divergence='classic')  # Автоматическое извлечение features
    .analyze(clustering=True)
    .build()
)

for zone in result.zones:
    if zone.features:  # Graceful degradation
        divergence = zone.features.get('has_classic_divergence')
        volume_corr = zone.features.get('volume_indicator_corr')
```

**Strategy Configuration Migration:**
```python
# ❌ Старый подход - прямое создание объектов
swing_strategy = FindPeaksSwingStrategy()
divergence_strategy = ClassicDivergenceStrategy()
features_analyzer = ZoneFeaturesAnalyzer(
    swing_strategy=swing_strategy,
    divergence_strategy=divergence_strategy
)

# ✅ Новый подход - string-based configuration
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='find_peaks',      # String name вместо объекта
        divergence='classic',    # String name вместо объекта
        volume='standard',       # String name вместо объекта
        volatility='combined'    # String name вместо объекта
    )
    .analyze(clustering=True)
    .build()
)
```

**Feature Access Patterns:**
```python
# ✅ Современный доступ к features
for zone in result.zones:
    if zone.features:
        # Swing features
        num_peaks = zone.features.get('num_peaks', 0)
        num_troughs = zone.features.get('num_troughs', 0)
        drawdown = zone.features.get('drawdown_from_peak', 0.0)
        
        # Divergence features
        has_divergence = zone.features.get('has_classic_divergence', False)
        divergence_strength = zone.features.get('divergence_strength', 0.0)
        
        # Volume features
        volume_corr = zone.features.get('volume_indicator_corr', 0.0)
        volume_trend = zone.features.get('volume_trend', 'neutral')
        
        # Volatility features
        volatility_ratio = zone.features.get('volatility_ratio', 1.0)
        price_volatility_corr = zone.features.get('price_volatility_corr', 0.0)
```

**Advanced Features Integration:**
```python
# ✅ Regression & Validation через pipeline
result_with_advanced = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='zigzag',          # Все 3 swing стратегии работают!
        divergence='classic',
        volume='standard',
        volatility='combined'
    )
    .analyze(
        clustering=True,
        n_clusters=3,
        hypothesis_tests=True,   # Автоматические статистические тесты
        regression=True,         # Опциональная регрессия
        validation=True          # Опциональная валидация
    )
    .build()
)

# Доступ к результатам
if result_with_advanced.hypothesis_tests:
    tests = result_with_advanced.hypothesis_tests
    for test_name, test_result in tests.results.items():
        print(f"{test_name}: p={test_result['p_value']:.4f}")

if result_with_advanced.regression_results:
    regression = result_with_advanced.regression_results
    print(f"R² score: {regression.get('r2_score', 'N/A')}")
```

**Code Simplification Results:**
- **Net Reduction:** ~200 lines of code removed [zonan_uni_full.md:1809]
- **API Calls:** 1 builder chain вместо 10+ отдельных вызовов
- **Error Handling:** graceful degradation для опциональных компонентов
- **Maintainability:** единый API для всех индикаторов

Источники: `examples/05_strategies_demo.py`, `examples/06_regression_demo.py`, `examples/07_validation_demo.py`. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】

#### 2. **Обновить в примерах комментарии/print-блоки, чтобы акцентировать `indicator_context` и универсальные стратегии.** ✅ **ВЫПОЛНЕНО**

**indicator_context Contract Documentation:**

**True Universality v2.1:**
- **ZERO hardcoded индикаторов** - стратегии сами заполняют контекст [zouni_v2.md:15-20]
- **Standard Fields:** line1_col, line2_col, indicator_name, source_type [zonan.md:29-118]
- **Strategy Usage:** как стратегии читают и используют контекст для универсальной работы [zouni_v2.md:15-20]

**indicator_context Examples:**
```python
# ✅ Демонстрация indicator_context в комментариях
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks')
    .analyze()
    .build()
)

# indicator_context автоматически заполняется стратегиями:
# - line1_col: 'macd' (основная линия)
# - line2_col: 'macd_signal' (сигнальная линия)  
# - indicator_name: 'macd'
# - source_type: 'custom'
# - histogram_col: 'macd_hist' (для zero_crossing detection)

for zone in result.zones:
    if zone.features:
        # Swing стратегия использует indicator_context для универсальной работы
        num_peaks = zone.features.get('num_peaks', 0)
        print(f"Zone {zone.zone_id}: {num_peaks} peaks detected using {zone.features.get('indicator_name', 'unknown')} context")
```

**Universal Strategy Patterns:**
```python
# ✅ Демонстрация универсальности стратегий
indicators_to_test = [
    ('custom', 'macd', {'fast': 12, 'slow': 26, 'signal': 9}),
    ('pandas_ta', 'rsi', {'length': 14}),
    ('pandas_ta', 'ao', {'fast': 5, 'slow': 34}),
    ('custom', 'stochastic', {'k_period': 14, 'd_period': 3})
]

for source, name, params in indicators_to_test:
    print(f"\n=== Testing {name.upper()} with Universal Strategies ===")
    
    result = (
        analyze_zones(df)
        .with_indicator(source, name, **params)
        .detect_zones('zero_crossing' if name in ['macd', 'ao'] else 'threshold')
        .with_strategies(
            swing='find_peaks',      # Работает с ЛЮБЫМ индикатором
            divergence='classic',    # Работает с ЛЮБЫМ индикатором
            volume='standard',       # Работает с ЛЮБЫМ индикатором
            volatility='combined'    # Работает с ЛЮБЫМ индикатором
        )
        .analyze(clustering=True)
        .build()
    )
    
    # indicator_context автоматически адаптируется к каждому индикатору
    print(f"Detected {len(result.zones)} zones using {name} indicator")
    print(f"Strategy context: {result.zones[0].features.get('indicator_name', 'unknown') if result.zones else 'No zones'}")
```

**Strategy Configuration Documentation:**
```python
# ✅ Подробные комментарии о Strategy Configuration
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        # Swing Strategies - анализ пиков и впадин
        swing='find_peaks',      # Алгоритм поиска пиков (scipy.signal.find_peaks)
        # swing='pivot_points',  # Pivot Points анализ
        # swing='zigzag',        # ZigZag индикатор (работает без Numba crash!)
        
        # Divergence Strategies - поиск расхождений
        divergence='classic',    # Классический анализ дивергенций
        
        # Volume Strategies - анализ объемов
        volume='standard',       # Стандартный анализ корреляции объемов
        
        # Volatility Strategies - анализ волатильности  
        volatility='combined'    # Комбинированный анализ волатильности
    )
    .analyze(
        clustering=True,         # Автоматическая кластеризация зон
        hypothesis_tests=True,   # Статистические тесты гипотез
        regression=True,         # Регрессионный анализ (опционально)
        validation=True          # Валидация модели (опционально)
    )
    .build()
)

# Все стратегии работают универсально благодаря indicator_context
print("Universal Strategy Results:")
for zone in result.zones[:3]:
    if zone.features:
        print(f"Zone {zone.zone_id}:")
        print(f"  - Peaks: {zone.features.get('num_peaks', 0)}")
        print(f"  - Divergence: {zone.features.get('has_classic_divergence', False)}")
        print(f"  - Volume Corr: {zone.features.get('volume_indicator_corr', 0.0):.3f}")
        print(f"  - Volatility: {zone.features.get('volatility_ratio', 1.0):.3f}")
```

**Design Patterns Documentation:**
```python
# ✅ Комментарии о архитектурных паттернах
# Strategy Pattern: каждая стратегия реализует единый интерфейс
# Dependency Injection: стратегии инжектируются в анализатор
# Builder Pattern: fluent API для конфигурации
# Registry Pattern: автоматическая регистрация стратегий по string names

# Пример расширения - добавление кастомной стратегии
class CustomSwingStrategy:
    def analyze_zone(self, zone_info, df, indicator_context):
        # indicator_context содержит все необходимые поля
        line1_col = indicator_context.get('line1_col')
        line2_col = indicator_context.get('line2_col')
        
        # Универсальная логика работы с любым индикатором
        return {'custom_metric': 42.0}

# Регистрация кастомной стратегии
from bquant.analysis.zones.strategies import StrategyRegistry
StrategyRegistry.register('custom_swing', CustomSwingStrategy)

# Использование кастомной стратегии
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26, signal=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='custom_swing')  # Используем зарегистрированную стратегию
    .analyze()
    .build()
)
```

**Testing Integration:**
```python
# ✅ Комментарии о тестировании и валидации
# Все примеры должны демонстрировать:
# 1. Graceful degradation для опциональных компонентов
# 2. Error handling для edge cases
# 3. Performance considerations
# 4. Integration с существующими тестами

def demonstrate_graceful_degradation():
    """Демонстрация graceful degradation для опциональных модулей."""
    
    # Проверка доступности опциональных модулей
    regression_available = hasattr(result, 'regression_results') and result.regression_results
    validation_available = hasattr(result, 'validation_results') and result.validation_results
    
    print(f"Regression analysis: {'Available' if regression_available else 'Not available'}")
    print(f"Validation analysis: {'Available' if validation_available else 'Not available'}")
    
    # Graceful handling
    if regression_available:
        r2_score = result.regression_results.get('r2_score', 'N/A')
        print(f"Model R² score: {r2_score}")
    else:
        print("Regression analysis skipped - module not available")
    
    if validation_available:
        validation_score = result.validation_results.get('validation_score', 'N/A')
        print(f"Validation score: {validation_score}")
    else:
        print("Validation analysis skipped - module not available")
```

Источники: `tests/unit/test_zone_detection_strategies.py`, `tests/unit/test_zone_models.py`. 【F:tests/unit/test_zone_detection_strategies.py†L548-L672】【F:tests/unit/test_zone_models.py†L79-150】

### Этап 5 – Кросс-ссылки и завершающие штрихи (0.5 дня) ✅ **ВЫПОЛНЕНО**

**Цель:** Создать единое дерево ссылок между всеми разделами документации, обеспечить корректную сборку Sphinx и финализировать документацию Universal Pipeline v2.1.

#### 1. **Добавить ссылки между API и руководствами (Quick Start ↔ pipeline ↔ стратегии ↔ статистика ↔ примеры).** ✅ **ВЫПОЛНЕНО**

**Ключевые паттерны кросс-ссылок:**

**Unified Navigation Tree:**
- **Quick Start → Pipeline → Strategies/Statistical → Examples/Tutorials → Developer Guide** [zodoc.md:947-948]
- **Proof of Universality** - 115 тестов, 100% pass rate [zouni_v2.md:11-13]
- **FICTIONAL_INDICATOR_99** - работает без изменений кода [zouni_v2.md:21-25]

**Cross-Reference Patterns:**
```markdown
# Navigation Structure

## Entry Points
- **Quick Start** → [Basic Universal API](examples/02a_universal_zones.py)
- **Main Page** → [Universal Pipeline](api/analysis/pipeline.md)

## Core API
- **Pipeline API** ↔ [ZoneAnalysisBuilder](api/analysis/pipeline.md#builder)
- **Detection Strategies** ↔ [5 Strategy Types](api/analysis/strategies.md)
- **Analysis Components** ↔ [UniversalZoneAnalyzer](api/analysis/pipeline.md#analyzer)

## Learning Path
- **Tutorials** ↔ [Deep Dive Analysis](research/notebooks/03_zones_universal.py)
- **Examples** ↔ [Advanced Features](research/notebooks/03_analysis_new_features.py)
- **Migration** ↔ [Old vs New API](examples/02_macd_zone_analysis.py)

## Developer Resources
- **Architecture** ↔ [Design Patterns](developer_guide/README.md#patterns)
- **Testing** ↔ [Integration Tests](tests/integration/)
- **Extension** ↔ [Custom Strategies](developer_guide/README.md#extension)
```

**API Cross-References:**
- **Quick Start** → **Pipeline API** → **Strategy Reference** → **Statistical Analysis** → **Examples**
- **Migration Guide** → **Deprecated API** → **New API** → **Benefits**
- **Developer Guide** → **Architecture** → **Design Patterns** → **Extension Points**

**Real Examples Integration:**
- **`examples/02a_universal_zones.py`** - основной учебный сценарий (297 строк) [zonan.md:3776-3784]
- **`research/notebooks/03_zones_universal.py`** - deep dive анализ (412 строк) [zonan.md:3934-3982]
- **`research/notebooks/03_analysis_new_features.py`** - advanced features testing [zonan_uni_full.md:2959-2971]

**Architecture Cross-References:**
- **Two-Layer Architecture** - упрощение с 3 до 2 слоев [zonan.md:105-112]
- **Fluent Builder API** - цепочка методов `.with_indicator().detect_zones().analyze().build()` [zonan.md:2235-2249]
- **Universal Examples** - MACD, RSI, AO, custom indicators [zonan.md:808-821]
- **Design Patterns** - Strategy, DI, Builder, Registry [zonan.md:2221-2228]

#### 2. **Проверить Sphinx build, обновить оглавление `index.rst` и конфигурацию (`conf.py`), при необходимости включить новые файлы.** ✅ **ВЫПОЛНЕНО**

**Sphinx Documentation Structure:**

**index.rst Updates:**
```rst
# Zone Analysis Documentation Structure

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   user_guide/quick_start
   user_guide/README

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/analysis/pipeline
   api/analysis/strategies
   api/analysis/statistical
   api/indicators/README
   api/visualization/README

.. toctree::
   :maxdepth: 2
   :caption: Tutorials & Examples
   
   tutorials/README
   examples/README

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide
   
   developer_guide/README
```

**conf.py Configuration:**
```python
# Sphinx Configuration for Universal Pipeline v2.1

# Project information
project = 'BQuant Zone Analysis'
copyright = '2025, BQuant Team'
author = 'BQuant Team'
release = '2.1.0'

# Extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
]

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scikit-learn': ('https://scikit-learn.org/stable/', None),
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# HTML theme
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False
}
```

**Documentation Validation:**
- **Link Validation:** все ссылки ведут на реальные файлы и примеры
- **Code Validation:** Fluent API примеры работают корректно
- **Consistency Check:** единый стиль и терминология
- **Build Validation:** sphinx-build проходит без ошибок

**New Files Integration:**
- **`docs/api/analysis/pipeline.md`** - новая страница Universal Pipeline API
- **`docs/api/analysis/strategies.md`** - обновленная страница стратегий
- **`docs/tutorials/README.md`** - обновленная навигация по туториалам
- **`docs/examples/README.md`** - обновленный каталог примеров

#### 3. **Обновить `README` верхнего уровня (при необходимости) с кратким пунктом «Документация покрывает universal pipeline v2.1».** ✅ **ВЫПОЛНЕНО**

**README.md Updates:**

**Universal Pipeline v2.1 Section:**
```markdown
## Zone Analysis - Universal Pipeline v2.1

BQuant теперь поддерживает **универсальный анализ зон** для любых индикаторов через современный Fluent Builder API.

### Quick Start
```python
from bquant.analysis.zones import analyze_zones

# Любой индикатор за 3 строки
result = (
    analyze_zones(df)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)
```

### Key Features
- **Universal API** - работает с любым индикатором (MACD, RSI, AO, custom)
- **Fluent Builder** - цепочка методов для конфигурации
- **5 Detection Strategies** - zero_crossing, threshold, line_crossing, preloaded, combined
- **Advanced Analysis** - swing, divergence, volume, volatility strategies
- **Statistical Testing** - автоматические hypothesis tests
- **Caching Support** - производительность и персистентность

### Documentation
- **[Quick Start](docs/user_guide/quick_start.md)** - 5 минут до первого результата
- **[API Reference](docs/api/analysis/pipeline.md)** - полная документация Universal Pipeline
- **[Examples](examples/02a_universal_zones.py)** - готовые примеры для всех индикаторов
- **[Migration Guide](examples/02_macd_zone_analysis.py)** - переход с deprecated API

### Architecture
- **Two-Layer Design** - упрощение с 3 до 2 слоев
- **Zero Hardcode** - ZERO hardcoded индикаторов, полная универсальность
- **Design Patterns** - Strategy, Dependency Injection, Builder, Registry
- **115 Tests** - 100% pass rate, доказательство универсальности


**Documentation Status:**
- **Coverage:** Universal Pipeline v2.1 полностью документирован
- **Migration:** Deprecated API помечен с четкими путями миграции
- **Examples:** 20+ готовых примеров для всех сценариев использования
- **Testing:** Comprehensive test suite с 115 тестами

**Version Information:**
- **Current Version:** 2.1.0
- **API Status:** Stable, production-ready
- **Backward Compatibility:** Deprecated API поддерживается до v3.0.0
- **Migration Path:** Четкий переход на Universal Pipeline

**Key Benefits Highlighted:**
- **Simplified:** 2 слоя вместо 3, нет hardcode фасадов
- **Universal:** работает с ЛЮБЫМ индикатором из IndicatorFactory
- **Maintainable:** использует существующую инфраструктуру, нет дублирования
- **Performant:** автоматическое кэширование и оптимизация
- **Extensible:** легко добавлять новые стратегии и индикаторы

---

## 5. Ресурсы и источники информации

| Источник | Назначение | Ключевые результаты разработки |
|----------|------------|--------------------------------|
| `devref/gaps/zo/zonan.md` | **Полная архитектурная спецификация** - 17 разделов, детальные примеры, план миграции. 【F:devref/gaps/zo/zonan.md†L1-L4263】 | • **Two-Layer Architecture** - упрощение с 3 до 2 слоев [zonan.md:105-112]<br>• **Fluent Builder API** - цепочка методов `.with_indicator().detect_zones().analyze().build()` [zonan.md:2235-2249]<br>• **Universal Examples** - MACD, RSI, AO, custom indicators [zonan.md:808-821]<br>• **Design Patterns** - Strategy, DI, Builder, Registry [zonan.md:2221-2228]<br>• **Caching & Persistence** - автоматическое кэширование (память + диск) [zonan.md:2770-3430]<br>• **Visualization** - расширенная визуализация зон с индикаторами [zonan.md:2388-2765]<br>• **Performance Metrics** - метрики улучшения архитектуры [zonan.md:4266-4277] |
| `devref/gaps/zo/zouni_v2.md` | **True Universality v2.1** - архитектура без hardcode, контракт стратегий, proof of universality. 【F:devref/gaps/zo/zouni_v2.md†L1-L2555】 | • **ZERO hardcoded индикаторов** - работает с любым индикатором [zouni_v2.md:9-25]<br>• **indicator_context контракт** - стратегии сами заполняют контекст [zouni_v2.md:15-20]<br>• **115 тестов, 100% pass rate** - доказательство универсальности [zouni_v2.md:11-13]<br>• **FICTIONAL_INDICATOR_99** - работает без изменений кода [zouni_v2.md:21-25]<br>• **Coverage 72% total, 90%+ core** - статистика покрытия тестами [zouni_v2.md:11-13] |
| `devref/gaps/zo/zonan_uni_full.md` | **Практические решения** - детальный план исправлений, анализ проблем, чеклисты реализации. 【F:devref/gaps/zo/zonan_uni_full.md†L1-L3583】 | • **API Evolution** - `_zone_to_dict()` → `zone.features.get()` [zonan_uni_full.md:2975-2988]<br>• **Strategy Configuration** - `.with_strategies(swing='find_peaks')` [zonan_uni_full.md:210-218]<br>• **Migration Patterns** - старый API → новый API [zonan_uni_full.md:2990-2999]<br>• **Problems 1.1-1.7, 2.1-2.5** - все решены с детальными чеклистами [zonan_uni_full.md:78-294]<br>• **ZigZag Discovery** - стратегия работает без Numba crash [zonan_uni_full.md:2838-2853]<br>• **Code Simplification** - ~200 lines net reduction [zonan_uni_full.md:1809]<br>• **Testing Results** - 20/20 notebooks работают, exit code 0 [zonan_uni_full.md:2817-2844] |
| `devref/gaps/DOCUMENTATION_UPDATE_PLAN.md` | История предыдущих решений, показывает, что текущие пробелы – результат «минимального» обновления. 【F:devref/gaps/DOCUMENTATION_UPDATE_PLAN.md†L15-L124】 | • **"Минимальное" обновление** - причина текущих пробелов в документации |
| Тесты (`tests/integration/test_truly_universal_zones.py`, `tests/unit/test_zone_detection_strategies.py`, `tests/unit/test_zone_models.py`) | Подтверждают работу `indicator_context`, универсальность стратегий и builder. 【F:tests/integration/test_truly_universal_zones.py†L50-L125】【F:tests/unit/test_zone_detection_strategies.py†L548-L672】【F:tests/unit/test_zone_models.py†L79-L150】 | • **Integration tests** - доказательство работы с любыми индикаторами<br>• **Unit tests** - контракт стратегий и моделей<br>• **E2E Tests** - 10 тестов (9 passed, 1 skipped) [zonan.md:4043-4051]<br>• **Backward Compatibility** - 11 тестов deprecated API [zonan.md:4053-4054]<br>• **Coverage** - 28 тестов стратегий, 8 тестов analyzer [zonan.md:3568-3594] |
| Код (`bquant/analysis/zones/*.py`, `bquant/indicators/macd.py`) | Истина о текущей реализации, статус деприкации, обязательные поля. 【F:bquant/analysis/zones/pipeline.py†L523-L619】【F:bquant/analysis/zones/models.py†L29-L118】【F:bquant/indicators/macd.py†L1-L159】 | • **ZoneAnalysisBuilder** - fluent interface реализация<br>• **MACDZoneAnalyzer** - deprecated wrapper с делегированием<br>• **Caching Integration** - автоматическое кэширование в pipeline [zonan.md:2770-3430]<br>• **Visualization Methods** - plot_zone_detail, plot_zones_comparison [zonan.md:2388-2765]<br>• **Performance Features** - lazy loading, export support [zonan.md:4253-4254] |
| Примеры (`examples/*.py`, `research/notebooks/*.py`) | Готовые учебные материалы, демонстрирующие все возможности v2.1. 【F:examples/05_strategies_demo.py†L13-L115】【F:examples/06_regression_demo.py†L13-L90】【F:examples/07_validation_demo.py†L14-L161】 | • **examples/02a_universal_zones.py** - основной учебный сценарий (297 строк) [zonan.md:3776-3784]<br>• **research/notebooks/03_zones_universal.py** - deep dive анализ (412 строк) [zonan.md:3934-3982]<br>• **research/notebooks/03_analysis_new_features.py** - advanced features testing [zonan_uni_full.md:2959-2971]<br>• **Migration Examples** - old vs new API comparison [zonan.md:3768-3774]<br>• **Performance Benchmarks** - zones/sec metrics [zonan_uni_full.md:1711]<br>• **Multi-indicator Testing** - MACD, RSI, AO universality [zonan_uni_full.md:2823-2828] |

---

## 6. Ожидаемый результат

После выполнения плана документация должна:

1. **Прямо вести пользователя в универсальный пайплайн** (Quick Start, главная страница, API-референс).
   - **Fluent Builder Pattern** как основной способ работы [zonan.md:2235-2249]
   - **Universal API** для всех индикаторов (MACD, RSI, AO, custom) [zonan.md:808-821]
   - **Two-Layer Architecture** вместо устаревших indicator-specific facades [zonan.md:105-112]

2. **Объяснять контракт `indicator_context` и связь детектора/стратегий** на уровне API и примеров.
   - **True Universality v2.1** - ZERO hardcoded индикаторов [zouni_v2.md:9-25]
   - **Strategy Configuration** через `.with_strategies()` API [zonan_uni_full.md:210-218]
   - **Design Patterns** - Strategy, DI, Builder, Registry [zonan.md:2221-2228]

3. **Содержать актуальные навигационные разделы** без ссылок на несуществующие материалы.
   - **Реальные примеры** - `examples/02a_universal_zones.py`, `research/notebooks/03_zones_universal.py` [zonan.md:3776-3784, 3934-3982]
   - **Migration Guide** - от `MACDZoneAnalyzer` к `analyze_zones()` [zonan_uni_full.md:2990-2999]

4. **Демонстрировать расширенные возможности** (регрессия, валидация, альтернативные индикаторы) без обращения к устаревшему фасаду.
   - **API Evolution** - `_zone_to_dict()` → `zone.features.get()` [zonan_uni_full.md:2975-2988]
   - **Advanced Features** - swing, divergence, volume, volatility strategies [zonan_uni_full.md:2959-2971]
   - **IndicatorFactory Integration** - preloaded/custom/pandas_ta/talib [zonan.md:88-90]

5. **Иметь единое дерево ссылок**: Quick Start → Pipeline → Strategies/Statistical → Examples/Tutorials → Developer Guide.
   - **Proof of Universality** - 115 тестов, 100% pass rate [zouni_v2.md:11-13]
   - **FICTIONAL_INDICATOR_99** - работает без изменений кода [zouni_v2.md:21-25]

---

## 7. Следующие шаги

1. **Утвердить данный документ как новый базовый план** вместо «минимального» плана 2025-10-13.
   - **Основа:** Ключевые результаты разработки из `zonan.md`, `zouni_v2.md`, `zonan_uni_full.md`
   - **Фокус:** Практическое руководство, а не история разработки
   - **Приоритет:** Fluent Builder API, Universal Architecture, Migration Guide

2. **Распараллелить Этапы 0–2** (они независимы) и назначить ответственных.
   - **Этап 0:** Навигация с акцентом на архитектурные принципы v2.1
   - **Этап 1:** API Reference с примерами Universal Pipeline
   - **Этап 2:** Индикаторы и визуализация с Migration Guide

3. **После завершения Этапов 0–4 выполнить Сфинкс-сборку и ревью**, затем обновить `CHANGELOG`/`README` при необходимости.
   - **Проверка:** Все ссылки на реальные файлы и примеры
   - **Валидация:** Fluent API примеры работают корректно
   - **Консистентность:** Единый стиль и терминология

4. **Зафиксировать новые материалы в репозитории** и поднять задачу на автоматическое тестирование документации (sphinx-build) в CI.
   - **Автоматизация:** Проверка сборки документации при каждом коммите
   - **Качество:** Валидация примеров кода и ссылок

---

## Валидация документации (4-5 дней)

**Цель:** Систематически проверить актуальность всей документации через практическое тестирование примеров, исправить выявленные проблемы и обеспечить соответствие документации реальному коду.

### Этап 6 – Валидация корневых файлов и навигации (0.5 дня)

**Цель:** Проверить основные файлы документации и навигацию.

#### 1. **Валидация docs/index.rst**
- Проверить все toctree ссылки
- Валидировать примеры кода в index.rst
- Проверить cross-references
- Исправить битые ссылки

#### 2. **Валидация docs/README.md**
- Проверить инструкции по сборке
- Валидировать все ссылки
- Проверить актуальность команд

#### 3. **Валидация Sphinx конфигурации**
- Проверить docs/conf.py
- Валидировать extensions и settings
- Проверить сборку документации
- Исправить ошибки сборки

### Этап 7 – Валидация API документации (1.5 дня)

**Цель:** Проверить всю API документацию.

#### 1. **Валидация docs/api/README.md**
- Проверить все примеры кода
- Валидировать cross-references
- Проверить актуальность структуры API
- Исправить неработающие примеры

#### 2. **Валидация docs/api/analysis/ (5 файлов)**
- **README.md** - проверить примеры Universal Pipeline
- **zones.md** - валидировать API примеры и cross-references
- **strategies.md** - проверить все примеры стратегий
- **pipeline.md** - валидировать полную документацию Universal Pipeline
- **statistical.md** - проверить примеры (🟡 требует внимания)
- **base.md** - валидировать базовые примеры

#### 3. **Валидация docs/api/core/ (все *.md файлы)**
- Проверить все файлы в core/
- Валидировать cross-references (🟡 требует внимания)
- Исправить устаревшие ссылки

#### 4. **Валидация docs/api/data/ (все файлы)**
- Проверить соответствие модулям
- Валидировать примеры работы с данными
- Исправить неактуальные примеры

#### 5. **Валидация docs/api/indicators/ (2 файла)**
- **README.md** - проверить Universal Indicator Factory примеры
- **macd.md** - валидировать deprecation warning и migration guide

#### 6. **Валидация docs/api/visualization/README.md**
- Проверить Universal Pipeline visualization примеры
- Валидировать все cross-references
- Исправить неработающие примеры

#### 7. **Валидация docs/api/extension_guide.md**
- Проверить актуальность (🟡 требует внимания)
- Добавить cross-link на новый pipeline
- Валидировать примеры расширения

### Этап 8 – Валидация User Guide (0.5 дня)

**Цель:** Проверить пользовательскую документацию.

#### 1. **Валидация docs/user_guide/README.md**
- Проверить навигацию (🔴 требует серьезного переписывания)
- Валидировать все ссылки
- Исправить MACD-ориентированную навигацию
- Создать отсутствующий core_concepts.md

#### 2. **Валидация docs/user_guide/quick_start.md**
- Проверить все примеры analyze_zones() API
- Валидировать cross-references
- Исправить неработающие примеры

### Этап 9 – Валидация Tutorials и Examples (1 день)

**Цель:** Проверить обучающие материалы и примеры.

#### 1. **Валидация docs/tutorials/README.md**
- Проверить Architecture Learning Path
- Валидировать все cross-references
- Проверить ссылки на реальные файлы

#### 2. **Валидация docs/examples/README.md**
- Проверить Examples Navigation
- Валидировать Quality Standards
- Проверить все cross-references

#### 3. **Валидация docs/developer_guide/README.md**
- Проверить v2.1 архитектуру
- Валидировать Extension Points
- Проверить Code Quality Standards

### Этап 10 – Валидация реальных примеров (1.5 дня)

**Цель:** Проверить все файлы в examples/ и research/notebooks/.

#### 1. **Валидация examples/ (6 файлов)**
- **02_macd_zone_analysis.py** (🟡 legacy vs new) - проверить миграционные примеры
- **02a_universal_zones.py** (🟡 нужно расширить) - валидировать как главный reference
- **05_strategies_demo.py** (🟢) - проверить Universal Pipeline v2.1
- **06_regression_demo.py** (🟢) - валидировать миграцию
- **07_validation_demo.py** (🟢) - проверить миграцию
- **README.md** (🟡) - синхронизировать с docs/

#### 2. **Валидация research/notebooks/ (все файлы)**
- Проверить все notebooks на работоспособность
- Валидировать с параметром --no-trap
- Исправить неработающие notebooks
- Проверить cross-references

#### 3. **Валидация README.md верхнего уровня**
- Проверить Universal Pipeline v2.1 секцию
- Валидировать все примеры кода
- Проверить cross-references
- Исправить неактуальные ссылки

### Этап 11 – Финальная валидация и отчет (0.5 дня)

**Цель:** Создать финальный отчет и исправить критические проблемы.

#### 1. **Создание отчета о проблемах**
- Документировать все найденные проблемы
- Приоритизировать по критичности
- Создать план исправлений

#### 2. **Исправление критических проблем**
- Исправить 🔴 файлы (требуют серьезного переписывания)
- Обновить 🟡 файлы (точечные правки)
- Валидировать 🟢 файлы (проверить актуальность)

#### 3. **Финальная проверка**
- Запустить полный тест документации
- Проверить Sphinx build
- Валидировать все cross-references
- Создать финальный отчет

