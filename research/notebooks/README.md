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

### Статус актуальности (проверка 2025-10-22)

**Легенда:**
- ✅ **Работает** — скрипт успешно проходит прогон `--no-trap`
- 🔁 **Заменен** — файл удален или перенесен в обновленную версию

### Сводка по категориям

| Категория | Работают | Не работают | Неполные | Итого |
|-----------|----------|-------------|----------|-------|
| Data Processing | 6/6 (100%) ✅ | 0/6 | 0/6 | 6 |
| Indicators | 7/7 (100%) ✅ | 0/7 | 0/7 | 7 |
| Analysis | 6/6 (100%) ✅ | 0/6 | 0/6 | 6 |
| Utilities | 1/1 (100%) ✅ | 0/1 | 0/1 | 1 |
| **ИТОГО** | **20/20 (100%) 🎉** | **0/20 (0%)** | **0/20 (0%)** | **20** |

### Детальная таблица

| # | Скрипт | Категория | Статус | Примечания |
|---|--------|-----------|--------|------------|
| 1 | `00_logging_demo.py` | Data | ✅ Работает (2025-10-22) | Exit code 0 |
| 2 | `01_data.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, исправлены отступы |
| 3 | `01_data_loader.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, все тесты OK |
| 4 | `01_data_processor.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 5 | `01_data_schemas.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 6 | `01_data_validator.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 7 | `02_ind_base.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 8 | `02_ind_calculators.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 9 | `02_ind_factory.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 10 | `02_ind_lib.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, talib unavailable (OK) |
| 11 | `02_ind_library.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 12 | `02_ind_macd.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, отступы исправлены |
| 13 | `02_ind_types.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены |
| 14 | `03_analysis_base.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |
| 15 | `03_analysis_new_features.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, v2.1 migrated (ЭТАП 2) |
| 16 | `03_analysis_statistical.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |
| 17 | `03_analysis_zones.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |
| 18 | `03_zones.py` | Analysis | 🔁 Заменен (2025-10-22) | Заменен на 03_zones_universal.py |
| 18a | `03_zones_universal.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, 11 шагов, v2.1 (ЭТАП 1) |
| 19 | `bq.py` | Utilities | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи |

### Категории и ключевые моменты

#### Data Processing
Все шесть скриптов прошли перезапуск после очистки от проблем с отступами и эмодзи. `01_data.py` и `01_data_processor.py` теперь корректно работают на Windows и Linux, а `00_logging_demo.py` служит эталонным примером настройки логирования.

#### Indicators
Вся линейка файлов `02_ind_*` синхронизирована с универсальным API индикаторов. Скрипты демонстрируют различные уровни абстракции (базовые классы, калькуляторы, фабрика, типы). `02_ind_macd.py` и `02_ind_library.py` включают обновленные примеры миграции и успешно завершаются.

#### Analysis
Ключевые исследовательские сценарии анализа зон и новых возможностей полностью совместимы с архитектурой v2.1. `03_analysis_new_features.py` завершает полный прогон тестов новых возможностей, `03_analysis_zones.py` служит рабочей исторической справкой, а `03_zones_universal.py` — основное руководство по универсальному анализу зон. Файл `03_zones.py` окончательно заменен новой версией и не используется.

#### Utilities
`bq.py` остается универсальной точкой входа для демонстрации возможностей пакета и успешно проходит проверку без дополнительных настроек.

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

## 📊 Сводка проверки актуальности (2025-10-22)

**Проверка:** 20 скриптов с `--no-trap`

- ✅ Исправлено: 12 файлов (очистка от эмодзи, корректировка отступов, миграция API)
- 🔁 Заменено: `03_zones.py` → `03_zones_universal.py`
- 🎯 Результат: все скрипты завершаются с exit code 0, совместимы с API v2.1 и ASCII-safe

**Ключевые обновления:**
- `02_ind_macd.py` — детальный migration guide на универсальный API
- `03_analysis_new_features.py` — полная миграция на v2.1 API (этап 2)
- `03_zones_universal.py` — основной сценарий универсального анализа зон (11 шагов)

**Исторические материалы и ограничения:**
- `03_analysis_zones.py` — рабочий reference по прежней архитектуре
- `03_zones.py` — удален, информация перенесена в `03_zones_universal.py`
- `ZoneFeaturesAnalyzer` для RSI/AO все еще требует доработки (используется только детекция)

## 📊 Доступные sample данные

```python
from bquant.data.samples import list_available_samples, get_sample_data

# Список доступных
samples = list_available_samples()

# Загрузка
data = get_sample_data('tv_xauusd_1h')  # 1000 bars, XAUUSD 1H
```

---

**См. также:**
- Testing plan: `devref/gaps/TESTING_BEFORE_REFACTORING.md`
- Coverage: `devref/gaps/testing_coverage_analysis.md`
- Changelog: `changelogs/CHANGE_TRACE_LOG_2025-10-14.md`
