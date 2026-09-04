# Tutorial: MACD zones — базовый pipeline и визуализация

## 🎯 Цели
- Собрать базовый конвейер `analyze_zones()` и получить `ZoneAnalysisResult`
- Прочитать из результата то, что нужно чаще всего: зоны, их контекст, статистику
- Построить обзорную, детальную и статистическую визуализацию

Все блоки самодостаточны — каждый можно скопировать и запустить целиком.

## 📥 Данные
Встроенный датасет `tv_xauusd_1h` ([описание](../api/data/samples.md)): 1000 часовых
баров XAUUSD, время лежит в колонке `time`. Пайплайн сам переносит его в индекс.

```python
from bquant.data.samples import get_sample_data

raw = get_sample_data('tv_xauusd_1h')
print(raw.shape, list(raw.columns[:6]))
# (1000, 15) ['time', 'open', 'high', 'low', 'close', 'volume']
```

## 🛠️ Шаг 1. Сборка pipeline
Три обязательные стадии: откуда индикатор, как резать на зоны, что считать.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Всего зон: {len(result.zones)}")
print(f"Первые 3 типа зон: {[z.type for z in result.zones[:3]]}")
# Всего зон: 77
# Первые 3 типа зон: ['bull', 'bear', 'bull']
```

| Метод | Что делает |
|---|---|
| `with_indicator` | считает MACD и добавляет его колонки к данным |
| `detect_zones` | режет ряд по знаку гистограммы (`indicator_role='hist'` — роль, а не имя колонки) |
| `analyze` | признаки зон, статистика, гипотезы; `clustering=True` — ещё и кластеризация |
| `build` | исполняет конвейер и возвращает `ZoneAnalysisResult` |

Первые 33 бара — прогрев индикатора, они не принадлежат ни одной зоне.

## 🔎 Шаг 2. Чтение результата
`indicator_context` зоны говорит, чем и по какой колонке её нашли; `statistics` —
словарь распределений, а не плоский список чисел.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

first = result.zones[0]
print(first.indicator_context['detection_strategy'], first.indicator_context['detection_indicator'])
# zero_crossing macd_12_26_9__hist

print(result.statistics['total_statistics']['zones_by_type'])
# {'bull': 39, 'bear': 38}

duration = result.statistics['duration_distribution']['overall']
print(f"длительность: среднее {duration['mean']:.1f}, медиана {duration['median']:.0f}, максимум {duration['max']:.0f}")
# длительность: среднее 12.6, медиана 11, максимум 39

print(result.clustering['clustering_summary']['n_clusters'], result.metadata['swing_coverage'])
# 3 {'strategy': 'ZigZagSwingStrategy', 'zones': 77, 'zones_with_swings': 70}
```

Ключи `statistics`: `total_statistics`, `duration_distribution`, `return_distribution`,
`line_amplitude_distribution`, `oscillator_amplitude_distribution`, `additional_metrics`.
Полный разбор объекта — в [справочнике результата](../user_guide/zone_analysis_result.md).

## 📈 Шаг 3. Визуализация
`result.visualize(mode, ...)` возвращает фигуру Plotly. В интерактивной сессии —
`fig.show()`; в скрипте — `write_html()` / `write_image()`.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

overview = result.visualize('overview', title='MACD Zones Overview')      # все зоны на цене
detail = result.visualize('detail', zone_id=0, context_bars=20)           # одна зона с контекстом
stats = result.visualize('statistics')                                    # распределения

overview.write_html('macd_overview.html')
print(type(overview).__name__, len(overview.data))
# Figure 1
```

Что рисуется в каждом режиме и как его настроить — в
[справочнике визуализации зон](../api/visualization/zones.md).

## ✅ Практика
1. **Короткие зоны.** По умолчанию (`min_duration=1`) зоны мостят ряд без пропусков.
   `.analyze(min_duration=N)` не удаляет короткие зоны из `result.zones`, а выводит их
   из агрегатов и говорит об этом в `result.metadata['duration_filter']` — иначе
   соседство зон в анализе последовательностей перестало бы быть соседством.
2. **Контекст индикатора.** `zone.indicator_context` хранит стратегию, колонку и правила
   детекции — сохраняйте его вместе с результатом, если перезапускаете конвейер с разными
   настройками.
3. **Кэш.** `.with_cache(enable=True, ttl=3600)` в любом месте цепочки; повторный `build()`
   с теми же данными и настройками читает результат из кэша. Подробнее —
   [кэширование](../user_guide/caching.md).
4. **Артефакты.** `result.save('macd_result.pkl')` — и графики можно строить без пересчёта
   (`ZoneAnalysisResult.load`). Форматы `pickle`, `json`, `parquet`.

## 🚀 Что дальше
- [RSI zones](rsi_strategy_switching.md) — другой индикатор и смена стратегии детекции.
- `.with_strategies(swing=..., shape=..., divergence=...)` — метрики внутри зоны; см.
  [свинг-стратегии](../user_guide/swing_strategies.md).
- `examples/02_macd_zone_analysis.py` — тот же конвейер через пресет `analyze_macd_zones()`
  и по частям.
