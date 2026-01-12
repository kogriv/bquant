# Tutorial: Кастомные правила (Пример 8) — CombinedRulesDetection

## 🎯 Цели
- Повторить Пример 8: Комбинированные правила (см. документацию)
- Сконфигурировать стратегию `CombinedRulesDetection` с логикой AND/OR
- Научиться управлять типами зон и контекстом детекции

## 🔧 Предварительные требования
- Данные с рассчитанным индикатором (в примере рассчитываем MACD внутри pipeline)
- Понимание булевых условий и логики работы `conditions`

## 📥 Подготовка данных
```python
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')
```

## 🛠️ Шаг 1. Формулируем правила
`CombinedRulesDetection` принимает список функций, каждая из которых возвращает булеву серию. Логика объединения задаётся параметром `logic` (AND/OR).

```python
def macd_positive(frame):
    return frame['macd_hist'] > 0

def price_above_sma(frame):
    sma_50 = frame['close'].rolling(50, min_periods=1).mean()
    return frame['close'] > sma_50

conditions = [macd_positive, price_above_sma]
```

## 🏗️ Шаг 2. Конфигурация pipeline
Перед детекцией рассчитаем MACD через `with_indicator`. В `zone_type_map` укажем, что только `True`-ветка интересует как `bull_confirmed`.

```python
from bquant.analysis.zones import analyze_zones

combined_result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones(
        'combined',
        conditions=conditions,
        logic='AND',
        zone_type_map={True: 'bull_confirmed', False: 'filtered_out'},
        zone_types=['bull_confirmed'],
        min_duration=3
    )
    .analyze(clustering=False)
    .build()
)

print(f"Zones detected: {len(combined_result.zones)}")
ctx = combined_result.zones[0].indicator_context
print(ctx['logic'], ctx['num_conditions'])
```

## 🔍 Шаг 3. Отладка правил
Если правил много, удобно протестировать стратегию отдельно через `ZoneDetectionConfig`.

```python
from bquant.analysis.zones.detection import ZoneDetectionConfig, ZoneDetectionRegistry

pipeline_df = combined_result.data  # DataFrame с MACD и вспомогательными колонками
config = ZoneDetectionConfig(
    strategy_name='combined',
    min_duration=3,
    zone_types=['bull_confirmed', 'filtered_out'],
    rules={
        'conditions': conditions,
        'logic': 'OR',
        'zone_type_map': {True: 'bull_bias', False: 'neutral'}
    }
)

strategy = ZoneDetectionRegistry.get('combined')
manual_zones = strategy.detect_zones(pipeline_df, config)
print(f"Zones with OR logic: {sum(z.type == 'bull_bias' for z in manual_zones)}")
```

## 📊 Анализ и визуализация
```python
viz = combined_result.visualize('overview', title='Combined Rules Zones')
viz.show()

stats = combined_result.statistics
print(stats['zone_distribution'])
```

## ✅ Лучшие практики
1. **Предрасчёт Series** — вынесите `rolling`/`ema` вне функций, если условия тяжёлые.
2. **Зона по умолчанию** — задавайте `zone_type_map` для `False`, чтобы понимать, почему участки были отфильтрованы.
3. **Отладка условий** — сохраняйте промежуточный DataFrame и проверяйте `condition(frame).value_counts()`.
4. **Логика OR** — используйте для «alert»-сценариев, когда нужно реагировать на любую из комбинаций.
5. **Интеграция с аналитикой** — `indicator_context` автоматически сохраняет `logic` и `num_conditions`, что облегчает отчётность.

## 🚀 Что дальше
- Добавьте условие на объём/волатильность и протестируйте через `manual_zones`.
- Комбинируйте с `ZoneFeaturesAnalyzer` для построения регрессии на кастомных зонах.
- Встраивайте стратегии в `ZoneAnalysisPipeline`, сохраняя конфигурации в YAML/JSON.
