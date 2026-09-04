# Tutorial: RSI zones — смена стратегии детекции

## 🎯 Цели
- Построить зоны RSI по порогам 70/30 (`threshold`)
- Переключиться на `line_crossing` — RSI против его сглаженной версии — **без пересчёта
  индикатора**
- Сравнить, что даёт каждая стратегия на одном и том же ряду

Все блоки самодостаточны.

## 📥 Данные
Встроенный `tv_xauusd_1h`. RSI считаем через `pandas_ta` — он ставится зависимостью,
колонка называется `RSI_14`. (TA-Lib — опциональная библиотека; без неё источник `'talib'`
недоступен, и фабрика скажет об этом прямо.)

## 🛠️ Шаг 1. Пороговая стратегия
`threshold` делит ряд на три типа зон: выше верхнего порога, ниже нижнего, между ними.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

rsi_threshold = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

print(f"Threshold zones: {len(rsi_threshold.zones)}")
print(rsi_threshold.statistics['total_statistics']['zones_by_type'])
print(rsi_threshold.zones[0].indicator_context['thresholds'])
# Threshold zones: 64
# {'neutral': 32, 'oversold': 18, 'overbought': 14}
# {'upper': 70, 'lower': 30}
```

## ♻️ Шаг 2. Переключение на `line_crossing`
`result.data` — кадр с уже посчитанным RSI (и временем в индексе). Добавим к нему
сигнальную линию и запустим конвейер **только с детекцией**: индикатор не пересчитывается.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

rsi_threshold = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

rsi_data = rsi_threshold.data.copy()
rsi_data['RSI_signal'] = rsi_data['RSI_14'].rolling(5, min_periods=1).mean()

rsi_line = (
    analyze_zones(rsi_data)
    .detect_zones('line_crossing', line1_col='RSI_14', line2_col='RSI_signal')
    .analyze(clustering=True, min_duration=3)
    .build()
)

ctx = rsi_line.zones[0].indicator_context
print(f"Line-crossing zones: {len(rsi_line.zones)}")
print(ctx['detection_strategy'], ctx['signal_line'])
print({k: v for k, v in rsi_line.metadata['duration_filter'].items() if k != 'excluded_zone_ids'})
# Line-crossing zones: 300
# line_crossing RSI_signal
# {'min_duration': 3, 'zones_analysed': 154, 'zones_excluded': 146, 'bars_excluded': 200, 'zones_unmeasured': 0}
```

RSI пересекает свою пятибарную среднюю часто — 300 зон против 64. `min_duration=3` не
удаляет короткие зоны, а выводит их из агрегатов: в статистике остаётся 154, и
`metadata['duration_filter']` называет, сколько и каких исключено.

## 📊 Шаг 3. Сравнение
Стратегии дают зоны разной природы, поэтому сравнивать надо распределения, а не счётчики.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

rsi_threshold = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)
rsi_data = rsi_threshold.data.copy()
rsi_data['RSI_signal'] = rsi_data['RSI_14'].rolling(5, min_periods=1).mean()
rsi_line = (
    analyze_zones(rsi_data)
    .detect_zones('line_crossing', line1_col='RSI_14', line2_col='RSI_signal')
    .analyze(clustering=True, min_duration=3)
    .build()
)

for name, result in [('threshold', rsi_threshold), ('line_crossing', rsi_line)]:
    duration = result.statistics['duration_distribution']['overall']
    print(f"{name:14} типы={result.statistics['total_statistics']['zones_by_type']} "
          f"длительность: среднее {duration['mean']:.1f}, медиана {duration['median']:.0f}, максимум {duration['max']:.0f}")
# threshold      типы={'neutral': 32, 'oversold': 18, 'overbought': 14} длительность: среднее 15.6, медиана 3, максимум 159
# line_crossing  типы={'bear': 79, 'bull': 75} длительность: среднее 5.2, медиана 4, максимум 13
```

Пороговые зоны — редкие и длинные (`neutral` может тянуться 159 баров), зоны пересечения —
частые и короткие (не длиннее 13). Какая из них «правильная», зависит от вопроса: первая
про экстремумы, вторая про смену наклона.

Визуально: `rsi_threshold.visualize('overview', title='RSI threshold')` и то же для
`rsi_line` — см. [MACD tutorial](macd_basic_pipeline.md), шаг 3.

## ✅ Практика
1. **Переиспользуйте `result.data`** — в нём индикатор уже посчитан и время уже в индексе;
   любой перезапуск с другой стратегией стартует с него.
2. **Ширина сигнальной линии** (`rolling(N)`) регулирует чувствительность `line_crossing`:
   чем шире, тем меньше пересечений.
3. **`indicator_context`** каждой зоны хранит стратегию, колонки и пороги — этого достаточно,
   чтобы восстановить, как зона была получена.

## 🚀 Что дальше
- [Combined rules](combined_rules_detection.md) — зоны по собственным условиям.
- `examples/02a_universal_zones.py` — RSI, AO, Stochastic и другие индикаторы в одном
  конвейере.
