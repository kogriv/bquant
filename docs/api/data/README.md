# Data Modules - Модули данных BQuant

## 📚 Обзор

Data модули обеспечивают работу с финансовыми данными: загрузку, обработку, валидацию и управление sample данными.

## 🗂️ Модули

### 📥 [bquant.data.loader](loader.md) - Загрузка данных
- **load_ohlcv_data()** - Загрузка OHLCV данных из файлов
- **load_tradingview_data()** - Загрузка данных TradingView
- **load_metatrader_data()** - Загрузка данных MetaTrader
- **DataLoader** - Универсальный загрузчик данных

### 🔄 [bquant.data.processor](processor.md) - Обработка данных
- **clean_ohlcv_data()** - Очистка OHLCV данных
- **prepare_data_for_analysis()** - Подготовка данных для анализа
- **resample_data()** - Изменение временного интервала
- **DataProcessor** - Процессор данных

### ✅ [bquant.data.validator](validator.md) - Валидация данных
- **validate_ohlcv_data()** - Валидация OHLCV данных
- **check_data_integrity()** - Проверка целостности данных
- **DataValidator** - Валидатор данных

### 📊 [bquant.data.samples](samples.md) - Sample данные
- **get_sample_data()** - Получение sample данных
- **list_dataset_names()** - Список доступных datasets
- **get_dataset_info()** - Информация о dataset
- **SampleDataManager** - Управление sample данными

### 📋 [bquant.data.schemas](schemas.md) - Схемы данных
- **OHLCVRecord** - Схема OHLCV записи
- **DataSourceConfig** - Конфигурация источника данных
- **ValidationResult** - Результат валидации
- **DataSchema** - Схема данных

## 🔍 Быстрый поиск

### По функциональности

#### Загрузка данных
- `load_ohlcv_data()` - Загрузка OHLCV из файла
- `load_tradingview_data()` - Загрузка из TradingView
- `load_metatrader_data()` - Загрузка из MetaTrader
- `DataLoader.load()` - Универсальная загрузка

#### Обработка данных
- `clean_ohlcv_data()` - Очистка данных
- `prepare_data_for_analysis()` - Подготовка к анализу
- `resample_data()` - Изменение интервала
- `remove_outliers()` - Удаление выбросов

#### Валидация данных
- `validate_ohlcv_data()` - Валидация OHLCV
- `check_data_integrity()` - Проверка целостности
- `validate_dataframe()` - Валидация DataFrame
- `check_missing_values()` - Проверка пропусков

#### Sample данные
- `get_sample_data()` - Получение sample данных
- `list_dataset_names()` - Список datasets
- `get_dataset_info()` - Информация о dataset
- `convert_to_dataframe()` - Конвертация в DataFrame

### По типу

#### 🏗️ Классы
- `DataLoader` - Загрузчик данных
- `DataProcessor` - Процессор данных
- `DataValidator` - Валидатор данных
- `SampleDataManager` - Менеджер sample данных

#### 🔧 Функции
- `load_ohlcv_data()` - Загрузка OHLCV
- `clean_ohlcv_data()` - Очистка данных
- `validate_ohlcv_data()` - Валидация данных
- `get_sample_data()` - Получение sample данных

#### 📋 Типы данных
- `OHLCVRecord` - Запись OHLCV
- `DataSourceConfig` - Конфигурация источника
- `ValidationResult` - Результат валидации
- `DataSchema` - Схема данных

## 💡 Примеры использования

### Загрузка данных

```python
from bquant.data.loader import load_ohlcv_data, load_tradingview_data

# Загрузка из CSV файла
data = load_ohlcv_data('data.csv', 
                       date_column='time',
                       ohlcv_columns=['open', 'high', 'low', 'close', 'volume'])

# Загрузка из TradingView
tv_data = load_tradingview_data('XAUUSD', '1h', period='1M')

# Загрузка из MetaTrader
mt_data = load_metatrader_data('XAUUSD', 'M15', start_date='2024-01-01')
```

### Обработка данных

```python
from bquant.data.processor import clean_ohlcv_data, prepare_data_for_analysis

# Очистка данных
clean_data = clean_ohlcv_data(data, 
                             remove_outliers=True,
                             fill_missing='forward')

# Подготовка для анализа
analysis_data = prepare_data_for_analysis(clean_data,
                                         add_technical_features=True,
                                         normalize=True)

# Изменение временного интервала
hourly_data = resample_data(data, '1H')
daily_data = resample_data(data, '1D')
```

### Валидация данных

```python
from bquant.data.validator import validate_ohlcv_data, check_data_integrity

# Валидация OHLCV данных
validation_result = validate_ohlcv_data(data)

if not validation_result.is_valid:
    print(f"Validation errors: {validation_result.errors}")
    print(f"Warnings: {validation_result.warnings}")

# Проверка целостности
integrity_check = check_data_integrity(data)
print(f"Data integrity: {integrity_check.is_valid}")
```

### Sample данные

```python
from bquant.data.samples import get_sample_data, list_dataset_names, get_dataset_info

# Получение списка доступных datasets
datasets = list_dataset_names()
print(f"Available datasets: {datasets}")

# Получение информации о dataset
info = get_dataset_info('tv_xauusd_1h')
print(f"Dataset info: {info}")

# Загрузка sample данных
data = get_sample_data('tv_xauusd_1h')
print(f"Loaded {len(data)} records")

# Конвертация в DataFrame
df = convert_to_dataframe(data)
print(f"DataFrame shape: {df.shape}")
```

### Работа с DataLoader

```python
from bquant.data.loader import DataLoader

# Создание загрузчика
loader = DataLoader()

# Настройка параметров
loader.set_source('csv')
loader.set_columns(date_col='time', 
                   ohlcv_cols=['open', 'high', 'low', 'close', 'volume'])

# Загрузка данных
data = loader.load('data.csv')

# Проверка загруженных данных
print(f"Data shape: {data.shape}")
print(f"Columns: {data.columns.tolist()}")
```

### Работа с DataProcessor

```python
from bquant.data.processor import DataProcessor

# Создание процессора
processor = DataProcessor()

# Настройка параметров обработки
processor.set_cleaning_options(remove_outliers=True, 
                              fill_missing='forward',
                              min_volume=0)

# Обработка данных
processed_data = processor.process(data)

# Получение статистики обработки
stats = processor.get_processing_stats()
print(f"Processing stats: {stats}")
```

### Работа с DataValidator

```python
from bquant.data.validator import DataValidator

# Создание валидатора
validator = DataValidator()

# Настройка правил валидации
validator.set_validation_rules(
    check_ohlcv_consistency=True,
    check_volume_positive=True,
    check_date_order=True,
    min_records=100
)

# Валидация данных
result = validator.validate(data)

# Анализ результатов
if result.is_valid:
    print("Data is valid!")
else:
    print(f"Validation failed: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

## 🔗 Связанные разделы

- **[Core Modules](../core/)** - Базовые модули
- **[Indicators](../indicators/)** - Технические индикаторы
- **[Analysis](../analysis/)** - Аналитические модули
- **[Visualization](../visualization/)** - Модули визуализации

## 📖 Детальная документация

- **[Loader Module](loader.md)** - Подробная документация загрузки данных
- **[Processor Module](processor.md)** - Документация обработки данных
- **[Validator Module](validator.md)** - Документация валидации данных
- **[Samples Module](samples.md)** - Документация sample данных
- **[Schemas Module](schemas.md)** - Документация схем данных

---

**Следующий раздел:** [Indicators](../indicators/) 📈
