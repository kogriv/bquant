# Data Modules - Модули данных BQuant

## 📚 Обзор

Data модули обеспечивают работу с финансовыми данными: загрузку, обработку, валидацию и управление sample данными.

## 🗂️ Модули

### 📥 [bquant.data.loader](loader.md) — Загрузка данных
- `load_ohlcv_data()` — загрузка OHLCV из CSV с автопарсингом дат
- `load_symbol_data()` — загрузка по символу и таймфрейму через config
- `load_xauusd_data()` — быстрая загрузка данных XAUUSD
- `load_all_data_files()` — загрузка всех CSV из `DATA_DIR` (без рекурсии)
- `get_data_info()` — информация о загруженных данных
- `get_available_symbols()` / `get_available_timeframes()` — доступные символы/таймфреймы

### 🔄 [bquant.data.processor](processor.md) — Обработка данных
- `clean_ohlcv_data()` — очистка данных с удалением выбросов
- `remove_price_outliers()` — удаление ценовых выбросов
- `calculate_derived_indicators()` — расчет производных индикаторов
- `resample_ohlcv()` — изменение временного интервала
- `normalize_prices()` — нормализация цен
- `detect_market_sessions()` — определение торговых сессий
- `add_technical_features()` — добавление технических признаков
- `create_lagged_features()` — генерация лаговых признаков
- `prepare_data_for_analysis()` — комплексная подготовка для анализа

### ✅ [bquant.data.validator](validator.md) — Валидация данных
- `validate_ohlcv_data()` — валидация OHLCV с детальными проверками
- `validate_data_completeness()` — проверка полноты данных
- `validate_price_consistency()` — проверка логической связности цен
- `validate_time_series_continuity()` — проверка непрерывности временных рядов
- `validate_statistical_properties()` — проверка статистических свойств

### 📊 [bquant.data.samples](samples.md) — Sample данные
- `get_sample_data()` — получение embedded данных в pandas/dict формате
- `list_datasets()` / `list_dataset_names()` — список доступных датасетов
- `get_dataset_info()` — детальная информация о датасете
- `validate_dataset()` — валидация целостности датасета
- `get_sample_preview()` — предварительный просмотр данных
- `find_datasets()` — поиск по критериям (symbol, timeframe, source)
- `compare_sample_datasets()` — сравнение датасетов
- `get_data_statistics()` — статистика по датасету
- `convert_to_dataframe()` / `convert_to_list_of_dicts()` — конвертация формата
- `load_sample_data` — алиас `get_sample_data` (обратная совместимость)
- `SampleDataGenerator` — генератор embedded данных

### 📋 [bquant.data.schemas](schemas.md) — Схемы данных
- `OHLCVRecord` — Dataclass для OHLCV записи с валидацией
- `DataSourceConfig` — конфигурация источника данных
- `ValidationResult` — результат валидации (как структура данных)
- `DataSchema` / `OHLCVSchema` / `IndicatorSchema` — базовые схемы
- Предопределенные схемы: `OHLCV_SCHEMA`, `MACD_SCHEMA`, `RSI_SCHEMA`
- `get_schema()` / `validate_with_schema()` — функции работы со схемами (пока stub)

## 🔍 Быстрый поиск

### По функциональности

#### Загрузка данных
- `load_ohlcv_data()` — Загрузка OHLCV из файла
- `load_symbol_data()` — Загрузка по символу/таймфрейму
- `load_xauusd_data()` — Быстрый хелпер для XAUUSD
- `load_all_data_files()` — Пакетная загрузка CSV из `DATA_DIR`

#### Обработка данных
- `clean_ohlcv_data()` — Очистка данных
- `prepare_data_for_analysis()` — Подготовка к анализу
- `resample_ohlcv()` — Изменение интервала
- `remove_price_outliers()` — Удаление выбросов
- `calculate_derived_indicators()` — Производные индикаторы
- `normalize_prices()` — Нормализация цен
- `detect_market_sessions()` — Сессии
- `add_technical_features()` — Техпризнаки
- `create_lagged_features()` — Лаги

#### Валидация данных
- `validate_ohlcv_data()` — Валидация OHLCV
- `validate_data_completeness()` — Полнота
- `validate_price_consistency()` — Логика цен
- `validate_time_series_continuity()` — Непрерывность ряда
- `validate_statistical_properties()` — Статистика

#### Sample данные
- `get_sample_data()` — Получение sample данных
- `list_datasets()` / `list_dataset_names()` — Список datasets
- `get_dataset_info()` — Информация о dataset
- `get_data_statistics()` — Статистика по датасету
- `convert_to_dataframe()` / `convert_to_list_of_dicts()` — Конвертация формата

### По типу

#### 🏗️ Классы/структуры
- `OHLCVRecord`, `DataSourceConfig`, `ValidationResult`, `SampleDataGenerator`

#### 🔧 Функции
- `load_ohlcv_data()`, `clean_ohlcv_data()`, `validate_ohlcv_data()`, `get_sample_data()`

#### 📋 Типы данных
- `DataSchema`, `OHLCVSchema`, `IndicatorSchema`, предопределенные `OHLCV_SCHEMA/MACD_SCHEMA/RSI_SCHEMA`

## 💡 Примеры использования

### Загрузка данных

```python
from bquant.data.loader import load_ohlcv_data, load_symbol_data, load_xauusd_data

# Загрузка из CSV файла (с указанием контекста)
data = load_ohlcv_data('data.csv', symbol='XAUUSD', timeframe='1H')

# Загрузка по символу/таймфрейму через конфиг
tv_data = load_symbol_data('XAUUSD', '1H', data_source='tradingview', quote_provider='oanda')

# Быстрая загрузка XAUUSD
xau = load_xauusd_data('1H')
```

### Обработка данных

```python
from bquant.data.processor import (
    clean_ohlcv_data, prepare_data_for_analysis, resample_ohlcv,
    remove_price_outliers
)

# Очистка данных
clean_data = clean_ohlcv_data(data, remove_outliers=True, fill_method='forward')

# Подготовка для анализа
analysis_data = prepare_data_for_analysis(clean_data, add_tech_features=True, normalize=True)

# Изменение временного интервала
hourly_data = resample_ohlcv(data, '1H')
daily_data = resample_ohlcv(data, '1D')
```

### Валидация данных

```python
from bquant.data.validator import (
    validate_ohlcv_data, validate_data_completeness
)

# Валидация OHLCV данных
validation_result = validate_ohlcv_data(data)

if not validation_result['is_valid']:
    print(f"Validation errors: {validation_result['issues']}")
    print(f"Warnings: {validation_result['warnings']}")

# Проверка полноты
completeness = validate_data_completeness(data)
print(f"Data completeness: {completeness['is_complete']}")
```

### Sample данные

```python
from bquant.data.samples import (
    get_sample_data, list_datasets, list_dataset_names, get_dataset_info,
    convert_to_dataframe, convert_to_list_of_dicts, get_data_statistics
)

# Список доступных datasets
datasets_summary = list_datasets()
names = list_dataset_names()

# Информация о датасете
info = get_dataset_info('tv_xauusd_1h')

# Загрузка sample данных (по умолчанию DataFrame)
df = get_sample_data('tv_xauusd_1h')

# Загрузка как список словарей и конвертация в DataFrame
data_list = get_sample_data('tv_xauusd_1h', format='dict')
df2 = convert_to_dataframe(data_list, 'tv_xauusd_1h')

# Обратная конвертация
data_list2 = convert_to_list_of_dicts(df, 'tv_xauusd_1h')

# Статистика по данным
stats = get_data_statistics('tv_xauusd_1h')
```

### Генератор Sample данных

```python
from bquant.data.samples import SampleDataGenerator

generator = SampleDataGenerator()
# generator.generate_all()  # создаст embedded-файлы согласно конфигурации
```

## Логирование {#logging}

Data модули используют контекстное логирование с техническими деталями загрузки и обработки данных. При использовании с NotebookSimulator может возникать дублирование сообщений.

**Настройка для research скриптов:**
```python
import logging

# Скрыть технические логи data модулей
logging.getLogger('bquant.data').setLevel(logging.WARNING)
```

**См. подробности:** [Управление логированием](../core/logging.md#управление-логированием-в-многомодульных-проектах)

## 🔗 Связанные разделы

- **[Core Modules](../core/README.md)** — Базовые модули
- **[Indicators](../indicators/README.md)** — Технические индикаторы
- **[Analysis](../analysis/README.md)** — Аналитические модули
- **[Visualization](../visualization/README.md)** — Модули визуализации

## 📖 Детальная документация

- Loader: loader.md — загрузка данных (файлы, символ/таймфрейм, списки доступных)
- Processor: processor.md — очистка, ресемплинг, производные индикаторы
- Validator: validator.md — комплексная валидация, полнота, логика цен, непрерывность
- Schemas: schemas.md — схемы данных и предопределённые схемы
- Samples: samples.md — API sample‑данных (структура, функции, примеры)

---

**Следующий раздел:** [Indicators](../indicators/README.md) 📈
