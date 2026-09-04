# Tutorial: собственные правила — стратегия `combined`

## 🎯 Цели
- Задать зоны списком условий с логикой AND/OR
- Назвать типы зон через `zone_type_map` и понять, как с ним взаимодействует `zone_types`
- Отладить правила отдельно от пайплайна

Все блоки самодостаточны.

## 🛠️ Шаг 1. Условия
Условие — функция, получающая кадр **с уже посчитанным индикатором** и возвращающая
булеву серию. Колонка индикатора названа канонически: слаг идентичности плюс роль.

```python
def macd_positive(frame):
    return frame['macd_12_26_9__hist'] > 0

def price_above_sma(frame):
    sma_50 = frame['close'].rolling(50, min_periods=1).mean()
    return frame['close'] > sma_50

conditions = [macd_positive, price_above_sma]
```

## 🏗️ Шаг 2. Pipeline
`zone_type_map` даёт имена веткам `True`/`False`; `zone_types` затем **фильтрует** зоны по
этим именам. Здесь интересна только подтверждённая ветка.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

def macd_positive(frame):
    return frame['macd_12_26_9__hist'] > 0

def price_above_sma(frame):
    return frame['close'] > frame['close'].rolling(50, min_periods=1).mean()

combined_result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones(
        'combined',
        conditions=[macd_positive, price_above_sma],
        logic='AND',
        zone_type_map={True: 'bull_confirmed', False: 'filtered_out'},
        zone_types=['bull_confirmed'],
    )
    .analyze(clustering=False, min_duration=3)
    .build()
)

ctx = combined_result.zones[0].indicator_context
print(f"Zones detected: {len(combined_result.zones)}")
print(ctx['logic'], ctx['num_conditions'])
print(combined_result.statistics['total_statistics']['zones_by_type'])
# Zones detected: 36
# AND 2
# {'bull_confirmed': 24}
```

36 зон найдено, 24 в статистике: `min_duration=3` вывел из агрегатов 12 коротких, сами
зоны остались в `result.zones` (см. `metadata['duration_filter']`).

## 🔍 Шаг 3. Отладка правил вне пайплайна
Стратегию можно позвать напрямую на `combined_result.data` — кадре с индикатором — и
крутить логику без пересчёта.

```python
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.detection import ZoneDetectionConfig, ZoneDetectionRegistry
from bquant.data.samples import get_sample_data

def macd_positive(frame):
    return frame['macd_12_26_9__hist'] > 0

def price_above_sma(frame):
    return frame['close'] > frame['close'].rolling(50, min_periods=1).mean()

conditions = [macd_positive, price_above_sma]
pipeline_df = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('combined', conditions=conditions, logic='AND')
    .analyze(clustering=False)
    .build()
).data

config = ZoneDetectionConfig(
    strategy_name='combined',
    zone_types=None,                       # None = не фильтровать, отдать обе ветки
    rules={
        'conditions': conditions,
        'logic': 'OR',
        'zone_type_map': {True: 'bull_bias', False: 'neutral'},
    },
)
manual_zones = ZoneDetectionRegistry.get('combined').detect_zones(pipeline_df, config)
print(f"OR: {len(manual_zones)} zones, bull_bias = {sum(z.type == 'bull_bias' for z in manual_zones)}")
# OR: 70 zones, bull_bias = 35
```

**Ловушка:** `zone_types` применяется **после** `zone_type_map`. Если в фильтре стоят
имена из одной карты (`bull_confirmed`), а карта даёт другие (`bull_bias`), результат —
ноль зон без единой ошибки. Имена в двух местах должны совпадать, либо `zone_types=None`.

## ✅ Практика
1. **Тяжёлые условия** — считайте `rolling`/`ema` один раз и держите как колонку кадра, а не
   пересчитывайте в каждой функции.
2. **Ветка `False`** — давайте ей имя в `zone_type_map`, чтобы видеть, что именно
   отфильтровано; по умолчанию ветки называются `active`/`inactive`.
3. **Проверка условия по отдельности** — `condition(pipeline_df).value_counts()` до сборки
   конвейера.
4. **Логика OR** — для «любой из сигналов»; AND — для подтверждения одним другого.
5. **Контекст** — `indicator_context` зоны хранит `logic`, `num_conditions` и
   `zone_type_map`; сами функции туда не попадают, поэтому конфигурация с условиями
   не сериализуется в JSON — храните её кодом.

## 🚀 Что дальше
- [Preloaded zones](preloaded_zones_workflow.md) — зоны из внешней разметки и сравнение с
  автоматической детекцией.
- `.analyze(regression=True)` — регрессия на признаках ваших зон; см.
  [справочник пайплайна](../api/analysis/pipeline.md).
