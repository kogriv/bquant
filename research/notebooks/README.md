# BQuant Research Notebooks

Jupyter ноутбуки и Python-скрипты для исследований и анализа с использованием BQuant.

## 📓 Notebook-Style Scripts API

Для исследовательских задач, требующих версионирования и возможности запуска в CI/CD, в проекте используется подход "notebook-style" Python-скриптов. Они сочетают интерактивность Jupyter с надежностью обычных скриптов.

**Функциональность перенесена в основной пакет BQuant:**

➡️ **[API Documentation: bquant.core.nb](../../docs/api/core/nb.md)** - Полная документация API

### Быстрый старт

```python
from bquant.core.nb import NotebookSimulator

# Одна строка - всё настроено автоматически!
nb = NotebookSimulator("My Analysis Script")

# Пошаговое выполнение
nb.step("Data Loading")
# код загрузки данных
nb.success("Data loaded successfully")
nb.wait()

nb.step("Analysis")
# код анализа
nb.success("Analysis completed")
nb.wait()

nb.finish()
```

### Преимущества нового API

- **Нулевой boilerplate код** - одна строка инициализации
- **Автоопределение параметров** - имя скрипта, лог файл, аргументы CLI
- **Встроенная обработка ошибок** - контекстные менеджеры для критических операций  
- **Богатое форматирование** - эмодзи, разделители, структурированный вывод
- **Автоматическое логирование** - консоль + файл без дополнительной настройки

## 📓 Доступные скрипты

### Статус актуальности (проверка 2025-10-18)

**Легенда:**
- ✅ **Актуален** - скрипт работает с текущей версией пакета
- ⚠️ **Требует обновления** - скрипт работает, но использует deprecated API
- ❌ **Неактуален** - скрипт не работает, требует переработки
- 🔨 **В разработке** - неполный/черновой скрипт

### Категория: Data Loading & Processing ✅

#### `01_data_loader.py` ✅
Демонстрация загрузки данных через `bquant.data.loader`.

**Статус:** ✅ **Полностью актуален** (проверено 2025-10-18)

**Темы:**
- API `bquant.data.samples` - встроенные наборы данных
- Загрузка CSV файлов (OANDA/TradingView, MetaTrader)
- Автоматическая загрузка через `load_symbol_data`
- Convenience функции (`load_xauusd_data`)

**Запуск:**
```bash
python research/notebooks/01_data_loader.py --no-trap
```

**Результат:** Все шаги выполнены успешно, 4 набора данных загружены.

---

### Категория: Indicators & Zone Analysis

#### `02_ind_library.py` ✅
Демонстрация встроенных индикаторов (SMA, EMA, RSI, MACD, Bollinger Bands).

**Статус:** ✅ **Актуален** (индикаторы не изменились)

**Темы:**
- Регистрация встроенных индикаторов
- Сравнение различных параметров
- Анализ производительности
- Создание комплексных наборов индикаторов

**Запуск:**
```bash
python research/notebooks/02_ind_library.py --no-trap
```

#### `02_ind_macd.py` ✅
**Миграция на универсальный API** - обновлен 2025-10-18

**Статус:** ✅ **Полностью актуален** (обновлен в Stage 2.4)

**Содержание (262 строки):**
- Загрузка данных
- Понимание проблем старого API (deprecated)
- Новый универсальный API (fluent builder + preset)
- Migration guide с примерами кода
- Различные стратегии детекции
- Модульное использование
- Сохранение/загрузка результатов

**Ключевые темы:**
- Old vs New API comparison
- Fluent builder vs Convenience preset
- Migration guide (пошаговый переход)
- Работа с другими индикаторами

**Запуск:**
```bash
python research/notebooks/02_ind_macd.py --no-trap
```

**Результат:** ✅ Все 8 шагов выполнены успешно (проверено 2025-10-18)

#### `03_analysis_zones.py` ❌
**Старый** скрипт работы с базовыми классами Zone/ZoneAnalyzer.

**Статус:** ❌ **Неактуален** (проверено 2025-10-18)

**Проблемы:**
1. Использует старые классы `Zone`, `ZoneAnalyzer`
2. Использует старый `ZoneFeaturesAnalyzer` с непереносимой инициализацией
3. Несовместим с новой универсальной архитектурой

**Ошибка:** `ValueError: Unknown swing strategy: zigzag. Available: []`

**Решение:** Сохранить для исторической справки, не обновлять.

**Причина:** Этот скрипт демонстрирует старую архитектуру, которая была заменена универсальной системой. Документирован в git history.

---

---

### Категория: Universal Zone Analysis ⭐ NEW

#### `03_zones_universal.py` ✅
**Comprehensive исследование универсального анализа зон** - создан 2025-10-18

**Статус:** ✅ **Полностью работает** (создан в Stage 2.4)

**Содержание (412 строк, 10 шагов):**
1. Data Loading & Preparation
2. Universal API Basics (builder + preset)
3. Detection Strategies for MACD (zero crossing, line crossing)
4. Parameter Sensitivity Analysis (MACD periods, min_duration)
5. Indicator Comparison (MACD, RSI, AO)
6. Modular Usage Scenarios
7. Caching & Persistence
8. Migration Guide (code examples)
9. Code Templates (detection + save, custom strategies, batch processing)
10. Performance Benchmarks & Summary

**Ключевые темы:**
- Полное тестирование универсального API
- Сравнение стратегий детекции
- Анализ чувствительности параметров
- Кэширование и производительность
- Migration guide с готовыми шаблонами кода

**Запуск:**
```bash
python research/notebooks/03_zones_universal.py --no-trap
```

**Результаты (XAUUSD 1H, 1000 bars):**
- ✅ Все 10 шагов выполнены успешно
- ✅ 72 MACD зоны детектированы
- ✅ Протестированы 3 индикатора (MACD, RSI, AO)
- ✅ Протестированы 2 стратегии детекции
- ✅ 7 параметрических вариаций
- ✅ Кэширование работает
- ✅ Производительность: ~14K зон/сек

**ВАЖНО:** Выявлен баг - `ZoneFeaturesAnalyzer` hardcoded для MACD колонок. Для RSI/AO работает только detection (без analyze()).

**См. также:**
- Examples: `examples/02a_universal_zones.py`
- Modularity: `devref/gaps/zo/zomodul.md`

---

### Категория: New Features Testing (Phases 3.3-3.8)

#### `03_analysis_new_features.py` ❌
**Комплексное тестирование новых возможностей анализа зон (Phases 3.3-3.8).**

**Статус:** ❌ **Требует обновления** (проверено 2025-10-18)

**Проблемы:**
1. Использует deprecated `MACDZoneAnalyzer`
2. Обращается к внутренним методам `_zone_to_dict()`, которые удалены
3. Работает с новым универсальным API только частично (Step 1 работает)

**Ошибка:** `AttributeError: 'MACDZoneAnalyzer' object has no attribute '_zone_to_dict'`

**Phases tested (частично работают):**
- ✅ Phase 1: Data preparation + Universal zone analysis (работает)
- ❌ Phase 3.3: Time Metrics (требует обновления)
- ❌ Phase 3.1: Swing Strategies (требует обновления)
- ❌ Phase 3.4-3.8: Остальные фазы (требуют обновления)

**Запланировано:** Обновление в Stage 2.4 с использованием только нового универсального API.

**Временная альтернатива:** Используйте `examples/04_comprehensive_analysis.py` для демонстрации полного анализа.

**Исходные результаты (до рефакторинга, XAUUSD 1H, 1000 bars):**
- ✅ 31 zone analyzed in 1.87 sec
- ✅ Duration model: R²=0.721 (excellent)
- ⚠️ Return model: R²=0.107 (needs improvement)
- ✅ ADF test: Stationary (p<0.0001)

**См. также:**
- Test results: `output/test_final_success.log`
- Coverage analysis: `devref/gaps/testing_coverage_analysis.md`
- Testing plan: `devref/gaps/TESTING_BEFORE_REFACTORING.md`

---

### Категория: Planned (Week 2-3)

#### `04_trading_scenarios.py` (TODO - High Priority)
Real trading scenarios testing.

**Planned topics:**
- Divergence-based entry points
- Volatility-based position sizing
- Pattern recognition and backtesting
- Strategy performance evaluation

#### `05_edge_cases.py` (TODO - High Priority)
Edge cases and stress testing.

**Planned topics:**
- Small datasets (20, 50, 100 bars)
- Extreme markets (strong trend, flat, high volatility)
- Missing data handling
- Performance stress tests

#### `06_model_optimization.py` (TODO - Medium Priority)
Model improvement and optimization.

**Planned topics:**
- Return model improvement
- Feature selection and engineering
- Cross-validation
- Model comparison

---

## 🚀 Quick Start для новых скриптов

### Шаблон нового research скрипта:

```python
'''
Название и описание исследования.
'''

from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data

# Инициализация
nb = NotebookSimulator("My Research Script")

# Шаг 1
nb.step("Step 1: Data Loading")
data = get_sample_data('tv_xauusd_1h')
nb.success(f"Loaded {len(data)} bars")
nb.wait()

# Шаг 2
nb.step("Step 2: Analysis")
# ваш код анализа
nb.wait()

# Финиш
nb.finish()
```

### Запуск с различными опциями:

```bash
# Интерактивный (по умолчанию)
python my_script.py

# Автоматический (CI/CD)
python my_script.py --no-trap

# Кастомный лог
python my_script.py --log output/my_research.log

# Автоматический + кастомный лог
python my_script.py --no-trap --log output/my_research.log
```

---

## 📊 Сводка проверки актуальности (2025-10-18)

### Результаты проверки research/notebooks

**Проверено:** 19 скриптов с `--no-trap` (первичная проверка)  
**После Stage 2.4:**  
**Работают:** 15/19 (79%) ⬆️ +2  
**Не работают:** 4/19 (21%) ⬇️ -2  
**Удалено:** 1 (03_zones.py - неполный черновик)

| # | Скрипт | Статус | Проблема | Решение |
|---|--------|--------|----------|---------|
| 1 | `00_logging_demo.py` | ✅ Работает | - | Актуален |
| 2 | `01_data.py` | ❌ Не работает | IndentationError (line 23) | Исправить отступы |
| 3 | `01_data_loader.py` | ✅ Работает | - | Актуален |
| 4 | `01_data_processor.py` | ❌ Не работает | UnicodeEncodeError (эмодзи) | Удалить эмодзи |
| 5 | `01_data_schemas.py` | ✅ Работает | - | Актуален |
| 6 | `01_data_validator.py` | ✅ Работает | - | Актуален |
| 7 | `02_ind_base.py` | ✅ Работает | - | Актуален |
| 8 | `02_ind_calculators.py` | ✅ Работает | - | Актуален |
| 9 | `02_ind_factory.py` | ✅ Работает | - | Актуален |
| 10 | `02_ind_lib.py` | ✅ Работает | talib unavailable (ожидаемо) | Актуален |
| 11 | `02_ind_library.py` | ✅ Работает | - | Актуален |
| 12 | `02_ind_macd.py` | ✅ Работает | - | **Обновлен Stage 2.4** |
| 13 | `02_ind_types.py` | ✅ Работает | - | Актуален |
| 14 | `03_analysis_base.py` | ✅ Работает | - | Актуален |
| 15 | `03_analysis_new_features.py` | ❌ Частично | `_zone_to_dict()` removed | Требует обновления |
| 16 | `03_analysis_statistical.py` | ✅ Работает | - | Актуален |
| 17 | `03_analysis_zones.py` | ❌ Не работает | Старые Zone классы | Сохранить для истории |
| 18 | `03_zones_universal.py` | ✅ Работает | - | **Создан Stage 2.4** |
| 19 | `bq.py` | ✅ Работает | - | Актуален |

### Категоризация скриптов по назначению

**📊 Data Processing (6 скриптов):**
- ✅ `00_logging_demo.py` - демонстрация системы логирования
- ❌ `01_data.py` - обзор работы с данными (IndentationError)
- ✅ `01_data_loader.py` - загрузка данных
- ❌ `01_data_processor.py` - обработка данных (UnicodeEncodeError)
- ✅ `01_data_schemas.py` - валидация схем
- ✅ `01_data_validator.py` - валидация данных

**📈 Indicators (7 скриптов):**
- ✅ `02_ind_base.py` - базовая архитектура индикаторов
- ✅ `02_ind_calculators.py` - вычисление индикаторов
- ✅ `02_ind_factory.py` - фабрика индикаторов
- ✅ `02_ind_lib.py` - работа с библиотеками
- ✅ `02_ind_library.py` - встроенные индикаторы
- ✅ `02_ind_macd.py` - MACD migration guide ⭐ **Обновлен Stage 2.4**
- ✅ `02_ind_types.py` - типы индикаторов

**🔬 Analysis (5 скриптов):**
- ✅ `03_analysis_base.py` - базовая архитектура анализа
- ❌ `03_analysis_new_features.py` - тесты новых фич (частично работает)
- ✅ `03_analysis_statistical.py` - статистический анализ
- ❌ `03_analysis_zones.py` - анализ зон (старая архитектура, сохранен для истории)
- ✅ `03_zones_universal.py` - universal zone analysis ⭐ **Создан Stage 2.4**

**🔧 Utilities (1 скрипт):**
- ✅ `bq.py` - общая демонстрация пакета

### Приоритеты для Stage 2.4 (Research Notebooks)

**✅ Выполнено в Stage 2.4 (2025-10-18):**
1. ✅ **Обновить `02_ind_macd.py`** → Migration guide (262 строки, 8 шагов) - РАБОТАЕТ
2. ✅ **Создать `03_zones_universal.py`** → Comprehensive test (412 строк, 10 шагов) - РАБОТАЕТ
3. ✅ **Удалить `03_zones.py`** → Удален (неполный черновик)

**Оставшиеся задачи (опционально):**

**Medium Priority (не блокируют работу):**
4. ⚠️ **Исправить `01_data.py`** → IndentationError (line 23) - технический баг
5. ⚠️ **Исправить `01_data_processor.py`** → UnicodeEncodeError (эмодзи) - технический баг
6. ⚠️ **Обновить `03_analysis_new_features.py`** → Переписать Step 2-10 на новый API

**Keep as-is (исторические/reference):**
7. 📚 **Сохранить `03_analysis_zones.py`** → Для исторической справки

**Выявленные баги (требуют отдельного исправления):**
- 🐛 **`ZoneFeaturesAnalyzer` hardcoded для MACD** → Нарушает универсальность, требует рефакторинга
- 🐛 **`HypothesisTestSuite` expects 'type' column** → Несоответствие схем данных
- 🐛 **RSI/AO presets вызывают analyze()** → Падают из-за бага выше, требуют отключения analyze()

### Рекомендации

**Для пользователей (актуальные примеры):**
- 🚀 **Примеры (examples/)** - для quick start и публичных демо:
  - `02_macd_zone_analysis.py` - migration guide (old → new API)
  - `02a_universal_zones.py` - универсальный API для всех индикаторов
  - `04_comprehensive_analysis.py` - полный pipeline анализа
  
- 📚 **Research (research/notebooks/)** - для глубокого изучения:
  - `02_ind_macd.py` ⭐ - migration guide с examples
  - `03_zones_universal.py` ⭐ - comprehensive тест нового API (10 шагов)

**Для разработчиков:**
- ✅ **Stage 2.4 ЗАВЕРШЕН** (2025-10-18):
  - Обновлен `02_ind_macd.py` (729→262 строки, migration guide)
  - Создан `03_zones_universal.py` (412 строк, 10 шагов comprehensive test)
  - Удален `03_zones.py` (неполный черновик)
- 🐛 **Выявлены баги** в ZoneFeaturesAnalyzer (hardcoded MACD columns)
- 📚 **Историческ reference:** `03_analysis_zones.py` сохранен для истории

---

## 📊 Доступные sample данные

```python
from bquant.data.samples import list_available_samples, get_sample_data

# Список доступных
samples = list_available_samples()

# Загрузка
data = get_sample_data('tv_xauusd_1h')  # 1000 bars, XAUUSD 1H
```

---

## 📈 Testing Progress

### Week 1: Базовое тестирование ✅
- [x] Day 1: Functional testing (03_analysis_new_features.py)
- [ ] Day 2-3: Trading scenarios testing (04_trading_scenarios.py)
- [ ] Day 4-5: Edge cases testing (05_edge_cases.py)

### Week 2: Продвинутое тестирование ⏳
- [ ] Model optimization
- [ ] Multiple instruments
- [ ] Performance profiling

### Week 3: Анализ и решение ⏳
- [ ] Results summary
- [ ] Refactoring decision (final)
- [ ] Action plan

**Current status:** Week 1 Day 1 ✅ COMPLETE

---

**См. также:**
- Testing plan: `devref/gaps/TESTING_BEFORE_REFACTORING.md`
- Coverage: `devref/gaps/testing_coverage_analysis.md`
- Changelog: `changelogs/CHANGE_TRACE_LOG_2025-10-14.md`
