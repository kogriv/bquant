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

### Источники данных о статусе

- **2025-10-22:** детальная проверка и описание исправлений из плана `devref/gaps/zo/zonan.md` (версия v7.1).【F:devref/gaps/zo/zonan.md†L3820-L3898】
- **2025-10-27:** повторный запуск `00_logging_demo.py` с параметром `--no-trap` подтвердил успешную работу после актуализации импортов (см. таблицу ниже).【59e534†L1-L104】
- **2025-10-27:** проверка `01_data.py` с параметром `--no-trap`; скрипт завершается с кодом 0, но сигнализирует об отсутствии тестового CSV в `data/raw` (см. примечания).【9472e4†L1-L24】
- **2025-10-27:** прогон `01_data_loader.py` с параметром `--no-trap`; скрипт успешно завершается, однако шаги работы с локальными CSV пропущены из-за отсутствия файлов в `data/row`.【eaccd4†L1-L92】
- **2025-10-27:** повторный запуск `01_data_processor.py` с параметром `--no-trap`; выполнение успешно, но фиксируются `FutureWarning` и `PerformanceWarning` от pandas при заполнении пропусков и создании лагов.【2ee9f3†L1-L129】

### Быстрая сводка (проверка 2025-10-27)

- ✅ `00_logging_demo.py` проходит полный сценарий демонстрации: расчёт MACD и анализ зон завершаются успешно, остаются только информационные предупреждения о недоступности TA-Lib.【59e534†L1-L104】
- ⚠️ `01_data.py` завершается без исключений, однако в разделе демонстрации загрузки отсутствует CSV-файл `XAUUSDH1.csv`; шаг отмечается как `[FAIL]`, но выполнение продолжается и финальный код возврата равен 0.【9472e4†L1-L24】
- ⚠️ `01_data_loader.py` покрывает работу с sample-данными, но демонстрация загрузки локальных CSV пропускается: каталог `data/row` пустой, поэтому шаг 3 логирует предупреждение и завершает сценарий без исключений.【eaccd4†L55-L92】
- ⚠️ `01_data_processor.py` завершает сценарий с кодом 0; pandas выводит `FutureWarning` и `PerformanceWarning` во время заполнения пропусков и создания лаговых признаков, но все шаги завершаются успешно.【2ee9f3†L17-L129】
- Остальные скрипты ещё не перепроверялись после ревизии 2025-10-22; статусы в таблице ниже отражают данные из документации и требуют подтверждения фактическими запусками.

### Сводка по категориям (по отчёту 2025-10-22)

| Категория | Работают | Не работают | Неполные | Итого |
|-----------|----------|-------------|----------|-------|
| Data Processing | 6/6 (100%) ✅ | 0/6 | 0/6 | 6 |
| Indicators | 7/7 (100%) ✅ | 0/7 | 0/7 | 7 |
| Analysis | 6/6 (100%) ✅ | 0/6 | 0/6 | 6 |
| Utilities | 1/1 (100%) ✅ | 0/1 | 0/1 | 1 |
| **ИТОГО** | **20/20 (100%) 🎉** | **0/20 (0%)** | **0/20 (0%)** | **20** |

> ℹ️ Фактические прогоны 2025-10-27 уже проведены для `00_logging_demo.py`, `01_data.py`, `01_data_loader.py` и `01_data_processor.py`; остальные записи ожидают подтверждения актуальности повторными запусками.

### Детальная таблица

| # | Скрипт | Категория | Статус | Примечания |
|---|--------|-----------|--------|------------|
| 1 | `00_logging_demo.py` | Data | ✅ Работает (2025-10-27) | Exit code 0; расчёт MACD и анализ зон выполняются, TA-Lib остаётся опциональным (предупреждения).【59e534†L1-L104】 |
| 2 | `01_data.py` | Data | ⚠️ Работает с предупреждением (2025-10-27) | Exit code 0, отсутствует пример CSV `XAUUSDH1.csv`, поэтому шаг 2.1 помечен как `[FAIL]`, остальной функционал завершается успешно.【9472e4†L1-L24】 |
| 3 | `01_data_loader.py` | Data | ⚠️ Работает с предупреждением (2025-10-27) | Exit code 0; sample-данные загружаются, но каталог `data/row` пустой, поэтому демонстрация хелперов пропущена.【eaccd4†L55-L92】 |
| 4 | `01_data_processor.py` | Data | ⚠️ Работает с предупреждениями (2025-10-27) | Exit code 0; pandas сообщает `FutureWarning`/`PerformanceWarning` при заполнении пропусков и создании лагов, функциональность завершает все шаги.【2ee9f3†L17-L129】 |
| 5 | `01_data_schemas.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3834-L3834】 |
| 6 | `01_data_validator.py` | Data | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3835-L3835】 |
| 7 | `02_ind_base.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3836-L3836】 |
| 8 | `02_ind_calculators.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3837-L3837】 |
| 9 | `02_ind_factory.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3838-L3838】 |
| 10 | `02_ind_lib.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, talib unavailable (OK)【F:devref/gaps/zo/zonan.md†L3839-L3839】 |
| 11 | `02_ind_library.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3840-L3840】 |
| 12 | `02_ind_macd.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, отступы исправлены【F:devref/gaps/zo/zonan.md†L3841-L3841】 |
| 13 | `02_ind_types.py` | Indicators | ✅ Работает (2025-10-22) | Exit code 0, эмодзи заменены【F:devref/gaps/zo/zonan.md†L3842-L3842】 |
| 14 | `03_analysis_base.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи【F:devref/gaps/zo/zonan.md†L3843-L3843】 |
| 15 | `03_analysis_new_features.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, v2.1 migrated (ЭТАП 2)【F:devref/gaps/zo/zonan.md†L3844-L3844】 |
| 16 | `03_analysis_statistical.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи【F:devref/gaps/zo/zonan.md†L3845-L3845】 |
| 17 | `03_analysis_zones.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи【F:devref/gaps/zo/zonan.md†L3846-L3846】 |
| 18 | `03_zones.py` | Analysis | 🔁 Заменен (2025-10-22) | Заменен на 03_zones_universal.py【F:devref/gaps/zo/zonan.md†L3847-L3847】 |
| 18a | `03_zones_universal.py` | Analysis | ✅ Работает (2025-10-22) | Exit code 0, 11 шагов, v2.1 (ЭТАП 1)【F:devref/gaps/zo/zonan.md†L3848-L3848】 |
| 19 | `bq.py` | Utilities | ✅ Работает (2025-10-22) | Exit code 0, нет эмодзи【F:devref/gaps/zo/zonan.md†L3849-L3849】 |

### Категории и ключевые моменты

#### Data Processing
Все шесть скриптов прошли перезапуск после очистки от проблем с отступами и эмодзи. `01_data.py` и `01_data_processor.py` теперь корректно работают на Windows и Linux.【F:devref/gaps/zo/zonan.md†L3820-L3898】 Повторная проверка `01_data.py` 2025-10-27 подтвердила успешное завершение сценария без исключений, хотя демонстрационный CSV `XAUUSDH1.csv` отсутствует и шаг загрузки помечается как `[FAIL]` в логе.【9472e4†L1-L24】 `01_data_loader.py` демонстрирует API загрузки: sample-данные доступны, но шаги с локальными CSV пропускаются, поскольку `data/row` пустой, — сценарий завершается с кодом 0 и фиксирует предупреждение.【eaccd4†L55-L92】 `00_logging_demo.py` используется как пример конфигурации логирования; после обновления импортов MACD повторный запуск 2025-10-27 подтверждает успешное выполнение всех этапов.【59e534†L1-L104】
Повторная проверка `01_data_processor.py` 2025-10-27 завершилась успешно: функциональные шаги охватывают весь пайплайн подготовки данных, однако pandas сообщает `FutureWarning` и `PerformanceWarning` во время заполнения пропусков и генерации лагов.【2ee9f3†L17-L129】

#### Indicators
Вся линейка файлов `02_ind_*` синхронизирована с универсальным API индикаторов. Скрипты демонстрируют различные уровни абстракции (базовые классы, калькуляторы, фабрика, типы). `02_ind_macd.py` и `02_ind_library.py` включают обновленные примеры миграции и успешно завершаются.【F:devref/gaps/zo/zonan.md†L3836-L3842】

#### Analysis
Ключевые исследовательские сценарии анализа зон и новых возможностей полностью совместимы с архитектурой v2.1. `03_analysis_new_features.py` завершает полный прогон тестов новых возможностей, `03_analysis_zones.py` служит рабочей исторической справкой, а `03_zones_universal.py` — основное руководство по универсальному анализу зон. Файл `03_zones.py` окончательно заменен новой версией и не используется.【F:devref/gaps/zo/zonan.md†L3843-L3848】

#### Utilities
`bq.py` остается универсальной точкой входа для демонстрации возможностей пакета и успешно проходит проверку без дополнительных настроек.【F:devref/gaps/zo/zonan.md†L3849-L3849】

### Выявленные проблемы 2025-10-27

- При запуске без предварительной установки пакета в окружение требуется добавить корневую директорию в `PYTHONPATH`, иначе возникает `ModuleNotFoundError: No module named 'bquant'`.【b99ea2†L1-L5】
- Отсутствие локальной библиотеки TA-Lib вызывает многочисленные информационные предупреждения, но не прерывает выполнение скрипта.【f4fd13†L1-L97】【59e534†L1-L104】
- В директории `data/row` нет CSV-файлов: демонстрационные шаги загрузки с диска и конфигурационные хелперы сообщают предупреждения, но сценарий `01_data_loader.py` завершается успешно.【eaccd4†L55-L92】
- `01_data_processor.py` сообщает `FutureWarning` и `PerformanceWarning` от pandas при заполнении пропусков и создании лагов; сообщения не влияют на успешное завершение сценария.【2ee9f3†L17-L129】

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
PYTHONPATH=. python my_script.py

# Автоматический (CI/CD)
PYTHONPATH=. python my_script.py --no-trap

# Кастомный лог
PYTHONPATH=. python my_script.py --log output/my_research.log

# Автоматический + кастомный лог
PYTHONPATH=. python my_script.py --no-trap --log output/my_research.log
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
