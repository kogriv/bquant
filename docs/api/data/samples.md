# BQuant Sample Data

Встроенные тестовые данные для демонстрации возможностей BQuant и разработки примеров.

## 📊 Доступные датасеты

### TradingView XAUUSD 1H (`tv_xauusd_1h`)
- Источник: TradingView via OANDA
- Символ: XAUUSD (золото)
- Таймфрейм: 1 час
- Записей: 1,000
- Размер: ~540 KB
- Период: Июнь-Август 2025
- Колонки: time, OHLCV, volume, accumulation_distribution, MACD, signal, RSI, RSI-based MA, regular bullish/bearish signals

### MetaTrader XAUUSD M15 (`mt_xauusd_m15`)
- Источник: MetaTrader
- Символ: XAUUSD (золото)
- Таймфрейм: 15 минут
- Записей: 1,000
- Размер: ~210 KB
- Период: Май 2025
- Колонки: time, OHLCV, volume, spread

## 🚀 Быстрый старт

```python
from bquant.data.samples import get_sample_data, list_datasets

# Получить список всех датасетов
datasets = list_datasets()
for dataset in datasets:
    print(f"{dataset['title']}: {dataset['rows']} rows")

# Загрузить данные как pandas DataFrame
df = get_sample_data('tv_xauusd_1h')
print(df.head())
print(f"Shape: {df.shape}")

# Загрузить данные как список словарей
data = get_sample_data('tv_xauusd_1h', format='dict')
print(f"Records: {len(data)}")
print(f"Columns: {list(data[0].keys())}")
```

## 📋 API функции

### Основные функции

#### `get_sample_data(dataset_name, format='pandas')`
Загружает sample данные в указанном формате.

- Параметры: `dataset_name` — `'tv_xauusd_1h'` или `'mt_xauusd_m15'`; `format` — `'pandas'|'dataframe'` либо `'dict'|'list'`.
- Возвращает: `pandas.DataFrame` или `List[Dict[str, Any]]`.

```python
# Как DataFrame (по умолчанию)
df = get_sample_data('tv_xauusd_1h')

# Как список словарей
data = get_sample_data('tv_xauusd_1h', format='dict')
```

#### `list_datasets()`
Возвращает список всех доступных датасетов с основной информацией.

```python
datasets = list_datasets()
# [{'name': 'tv_xauusd_1h', 'title': 'TradingView XAUUSD 1H', ...}, ...]
```

#### `get_dataset_info(dataset_name)`
Возвращает детальную информацию о конкретном датасете.

```python
info = get_dataset_info('tv_xauusd_1h')
print(info['columns'])  # Список колонок
print(info['period_start'])  # Начало периода
```

#### `validate_dataset(dataset_name)`
Валидирует целостность и корректность данных.

```python
result = validate_dataset('tv_xauusd_1h')
if result['is_valid']:
    print("✅ Dataset is valid")
else:
    print("❌ Errors:", result['errors'])
```

### Дополнительные функции

#### `get_sample_preview(dataset_name, n=5)`
Возвращает первые n записей для предварительного просмотра.

```python
preview = get_sample_preview('tv_xauusd_1h', 3)
for record in preview:
    print(f"Time: {record['time']}, Close: {record['close']}")
```

#### `find_datasets(symbol=None, timeframe=None, source=None)`
Находит датасеты по заданным критериям.

```python
# Все датасеты для XAUUSD
xauusd_data = find_datasets(symbol='XAUUSD')

# Все часовые данные
hourly_data = find_datasets(timeframe='1h')

# Все данные от TradingView
tv_data = find_datasets(source='TradingView')
```

#### `compare_sample_datasets(dataset1, dataset2)`
Сравнивает два датасета.

```python
comparison = compare_sample_datasets('tv_xauusd_1h', 'mt_xauusd_m15')
print(f"Common columns: {comparison['common_columns']}")
print(f"Dataset 1 unique: {comparison['unique_columns']['tv_xauusd_1h']}")
```

#### `print_sample_data_status()`
Выводит статус всех sample данных.

```python
print_sample_data_status()
# 🎯 BQuant Sample Data Status
# ================================
# 📊 TradingView XAUUSD 1H (tv_xauusd_1h)
# ...
```

## 🔧 Интеграция с BQuant

### С индикаторами

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones

# Загружаем данные
data = get_sample_data('tv_xauusd_1h')

# Анализ MACD-зон через универсальный пайплайн
result = analyze_macd_zones(data)

print(f"Found {len(result.zones)} MACD zones")
```

### С визуализацией

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts

# Загружаем данные
data = get_sample_data('tv_xauusd_1h')

# Создаем график
charts = FinancialCharts()
fig = charts.create_candlestick_chart(data, title="Sample XAUUSD Data")
fig.show()
```

### С анализом

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones
from bquant.analysis.statistical import run_all_hypothesis_tests
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer

# Загружаем данные
data = get_sample_data('tv_xauusd_1h')

# Анализируем MACD зоны через универсальный пайплайн
result = analyze_macd_zones(data)

# Статистические тесты
features = ZoneFeaturesAnalyzer().extract_all_zones_features(result.zones)
zones_features = [feature.to_dict() for feature in features]
test_results = run_all_hypothesis_tests(zones_features)
for test_name, outcome in test_results["tests"].items():
    print(f"{test_name}: p-value = {outcome['p_value']:.4f}")
```

## 📁 Структура данных

### TradingView данные (`tv_xauusd_1h`)

```python
{
    'time': '2025-06-11T20:00:00+07:00',
    'open': 3336.94,
    'high': 3344.77,
    'low': 3327.95,
    'close': 3330.0,
    'volume': 54323.0,
    'accumulation_distribution': 6642770.32110492,
    'macd': 1.9401445111593605,
    'signal': 2.76537114439529,
    'rsi': 47.8275212676637,
    'rsi_based_ma': 55.23196702366443,
    'regular_bullish': None,
    'regular_bullish_label': '',
    'regular_bearish': None,
    'regular_bearish_label': ''
}
```

### MetaTrader данные (`mt_xauusd_m15`)

```python
{
    'time': '2025-05-20T02:00:00',
    'open': 2425.15,
    'high': 2425.79,
    'low': 2424.85,
    'close': 2425.56,
    'volume': 7.0,
    'spread': 4.0
}
```

## ⚠️ Важные замечания

### Лицензия и использование
- Лицензия: Open data, свободно для исследований и образования
- Disclaimer: Только для демонстрации. Не для production торговли
- Источники: TradingView (OANDA), MetaTrader

### Технические детали
- Формат хранения: Embedded Python структуры (List[Dict])
- Кодировка: UTF-8 для TradingView, Windows-1251 для MetaTrader
- Размер в памяти: ~1-2 MB при загрузке в DataFrame
- Числовые типы: float для всех числовых значений, None для NaN

### Ограничения
- Фиксированное количество записей (1,000 на датасет)
- Только XAUUSD данные в текущей версии
- Статические данные (обновляются вручную)

## 🔄 Обновление данных

```bash
# Обновить все датасеты
python scripts/data/extract_samples.py --extract-all

# Обновить конкретный датасет
python scripts/data/extract_samples.py --dataset tv_xauusd_1h

# Проверить доступность источников
python scripts/data/extract_samples.py --validate-sources
```

## 🧪 Тестирование

```python
# Валидация всех датасетов
from bquant.data.samples import validate_dataset, list_dataset_names

for dataset_name in list_dataset_names():
    result = validate_dataset(dataset_name)
    if result['is_valid']:
        print(f"✅ {dataset_name}: Valid")
    else:
        print(f"❌ {dataset_name}: {result['errors']}")

# Общий статус
from bquant.data.samples import print_sample_data_status
print_sample_data_status()
```

---

Обновлено: 2025-08-25  
Версия BQuant: 1.0.0-dev  
Общий размер: ~750 KB (2 датасета)

