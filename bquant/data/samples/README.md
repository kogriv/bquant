# BQuant Sample Data (module README)

Этот README предназначен для разработчиков и указывает на каноническую документацию sample‑данных.

- Основная документация по sample‑данным: `docs/api/data/samples.md`
- Пользовательские примеры, API, структура данных и workflow обновления — в `docs/api/data/samples.md`.

Быстрые ссылки по API (см. полный справочник в docs):
- `from bquant.data.samples import get_sample_data, list_datasets, get_dataset_info`
- `from bquant.data.samples import get_sample_preview, get_data_statistics, compare_sample_datasets`

Примечание: подробные описания датасетов, команды обновления данных и интеграционные примеры с индикаторами/визуализацией перенесены в `docs/api/data/samples.md` для исключения дублирования.
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
- **Лицензия:** Open data, свободно для исследований и образования
- **Disclaimer:** Только для демонстрации. Не для production торговли
- **Источники:** TradingView (OANDA), MetaTrader

### Технические детали
- **Формат хранения:** Embedded Python структуры (List[Dict])
- **Кодировка:** UTF-8 для TradingView, Windows-1251 для MetaTrader
- **Размер в памяти:** ~1-2 MB при загрузке в DataFrame
- **Числовые типы:** float для всех числовых значений, None для NaN

### Ограничения
- Фиксированное количество записей (1,000 на датасет)
- Только XAUUSD данные в текущей версии
- Статические данные (обновляются вручную)

## 🔄 Обновление данных

Для обновления sample данных используйте скрипт:

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

## 🎯 Примеры применения

### 1. Быстрое прототипирование
```python
from bquant.data.samples import get_sample_data

# Быстро получаем данные для экспериментов
df = get_sample_data('tv_xauusd_1h')
print(f"Latest price: {df['close'].iloc[-1]}")
```

### 2. Обучение и документация
```python
# Примеры в документации
data = get_sample_data('mt_xauusd_m15')
example_result = some_bquant_function(data)
```

### 3. Unit тестирование
```python
def test_indicator():
    data = get_sample_data('tv_xauusd_1h')
    result = calculate_some_indicator(data)
    assert len(result) == 1000
```

### 4. Демонстрации и презентации
```python
# Наглядные примеры для презентаций
from bquant.data.samples import print_datasets_info
print_datasets_info()  # Красивый вывод информации
```

---

**Обновлено:** 2025-08-25  
**Версия BQuant:** 1.0.0-dev  
**Общий размер:** ~750 KB (2 датасета)
