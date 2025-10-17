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

### Категория: Indicators & Zone Analysis

#### `02_ind_library.py`
Демонстрация встроенных индикаторов (SMA, EMA, RSI, MACD, Bollinger Bands).

**Темы:**
- Регистрация встроенных индикаторов
- Сравнение различных параметров
- Анализ производительности
- Создание комплексных наборов индикаторов

**Запуск:**
```bash
python research/notebooks/02_ind_library.py --no-trap
```

#### `02_ind_macd.py`
Демонстрация специализированного MACD анализатора.

**Темы:**
- Создание MACD анализаторов с разными параметрами
- Анализ зон (бычьи/медвежьи)
- Статистические тесты и кластеризация
- Детекция сигналов и пересечений
- Визуализация и экспорт результатов

**Запуск:**
```bash
python research/notebooks/02_ind_macd.py --no-trap
```

### Категория: New Features Testing (Phases 3.3-3.8)

#### `03_analysis_new_features.py` ⭐ NEW
**Comprehensive functional testing of new zone analysis features.**

**Phases tested:**
- ✅ Phase 3.3: Time Metrics (peak_time_ratio, trough_time_ratio)
- ✅ Phase 3.1: Swing Strategies (ZigZag, FindPeaks, PivotPoints)
- ✅ Phase 3.4: Divergence Detection (ClassicDivergenceStrategy)
- ✅ Phase 3.5: Volatility Analysis (CombinedVolatilityStrategy)
- ✅ Phase 3.6: Volume Analysis (StandardVolumeStrategy)
- ✅ Phase 3.7: Hypothesis Tests (H4, ADF, H5)
- ✅ Phase 3.8: Regression Analysis (Duration & Return models)
- ✅ Phase 3.8: Validation Suite (Out-of-sample testing)

**Results (XAUUSD 1H, 1000 bars):**
- ✅ All 10 test steps passed
- ✅ 31 zones analyzed in 1.87 sec
- ✅ Duration model: R²=0.721 (excellent)
- ⚠️ Return model: R²=0.107 (needs improvement)
- ✅ ADF test: Stationary (p<0.0001)
- ✅ Volatility regimes: 45% low, 42% high

**Запуск:**
```bash
# Интерактивный режим (с остановками после каждого шага)
python research/notebooks/03_analysis_new_features.py

# Автоматический режим (без остановок)
python research/notebooks/03_analysis_new_features.py --no-trap

# С кастомным логом
python research/notebooks/03_analysis_new_features.py --log my_test.log
```

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
