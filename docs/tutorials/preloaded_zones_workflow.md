# Tutorial: Preloaded зоны — внешняя разметка

## 🎯 Цели
- Подать в конвейер зоны, размеченные снаружи (эксперт, другая система), и получить по ним
  тот же анализ, что и по автоматическим
- Разобрать формат входа и допуск по времени
- Сравнить разметку с автоматической детекцией

Все блоки самодостаточны: зоны строятся на часах самого сэмпла, внешний файл не нужен.

## 📥 Формат входа
`zones_data` — путь к CSV или `DataFrame`. Обязательны четыре колонки:

| Колонка | Тип | Описание |
|---|---|---|
| `zone_id` | int | идентификатор |
| `type` | str | тип зоны — любое имя (`bull`, `bear`, `support`, …) |
| `start_time` | datetime | начало |
| `end_time` | datetime | конец |

Колонка `indicator`, если есть, попадает в `indicator_context['detection_indicator']`.

```csv
zone_id,type,start_time,end_time,indicator
0,bull,2025-06-18T05:00:00+07:00,2025-06-19T22:00:00+07:00,expert
1,bear,2025-06-30T23:00:00+07:00,2025-07-02T07:00:00+07:00,expert
```

**Границы — метки времени в часах данных, не позиции.** Пайплайн ставит время на индекс
сам, а зоны приходят в координатах вызывающего; целые числа вместо дат отклоняются сразу:
`ValueError: zones_data['start_time'] has dtype int64, but the data is indexed by time …`.
У встроенных сэмплов время лежит в колонке `time` — берите метки оттуда.

## 🛠️ Шаг 1. Pipeline с готовыми зонами
Индикатор не нужен: зоны уже есть, конвейер только считает по ним признаки и статистику.

```python
import pandas as pd
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')
t = df['time']
expert_zones = pd.DataFrame({
    'zone_id': [0, 1, 2],
    'type': ['bull', 'bear', 'bull'],
    'start_time': [t.iloc[100], t.iloc[300], t.iloc[600]],
    'end_time': [t.iloc[140], t.iloc[330], t.iloc[650]],
    'indicator': ['expert'] * 3,
})

preloaded_result = (
    analyze_zones(df)
    .detect_zones('preloaded', zones_data=expert_zones, time_tolerance='5min')
    .analyze(clustering=False)
    .build()
)

zone = preloaded_result.zones[0]
print(f"Loaded zones: {len(preloaded_result.zones)}, durations: {[z.duration for z in preloaded_result.zones]}")
print(zone.indicator_context['source'], zone.indicator_context['detection_indicator'])
print(zone.start_time, '→', zone.end_time, '|', len(zone.data), 'bars')
# Loaded zones: 3, durations: [41, 31, 51]
# external expert
# 2025-06-18 05:00:00+07:00 → 2025-06-19 22:00:00+07:00 | 41 bars
```

То же одной строкой — пресет `analyze_preloaded_zones(df, expert_zones)` из
`bquant.analysis.zones.presets`; путь к CSV передаётся туда же вместо `DataFrame`.

Если нужны только зоны, без анализа, — `load_preloaded_zones(path, df)` из
`bquant.analysis.zones.detection` возвращает список `ZoneInfo` из файла:

```python
import pandas as pd
from bquant.analysis.zones.detection import load_preloaded_zones
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')
t = df['time']
pd.DataFrame({
    'zone_id': [0, 1, 2],
    'type': ['bull', 'bear', 'bull'],
    'start_time': [t.iloc[100], t.iloc[300], t.iloc[600]],
    'end_time': [t.iloc[140], t.iloc[330], t.iloc[650]],
}).to_csv('expert_zones.csv', index=False)

zones = load_preloaded_zones('expert_zones.csv', df)
print(len(zones), [z.duration for z in zones], type(zones[0]).__name__)
# 3 [41, 31, 51] ZoneInfo
```

`time_tolerance` — насколько далеко от объявленной границы может стоять ближайший бар:
граница **снапится** к нему, зона от этого не растёт. С `'2h'` те же три зоны дают те же
41, 31 и 51 бар; метка `07:20` на часовой сетке с `'30min'` ложится на бар `07:00`, а с
`'1min'` зона пропускается с предупреждением. До 2026-09-05 допуск расширял окно с обеих
сторон, и `'2h'` давал 44, 35 и 54 бара (G57). Объявленные границы лежат в
`zone.indicator_context['declared_start_time']`/`['declared_end_time']`; `start_time`/
`end_time` зоны — бары, которые в неё попали. Зоны сортируются по началу; пересечение
двух зон, `end < start` или повтор `zone_id` — `ValueError` по имени.

## ♻️ Шаг 2. Разметка против автоматической детекции
Обе стороны проходят один и тот же анализ, поэтому их статистику можно ставить рядом.

```python
import pandas as pd
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.presets import analyze_preloaded_zones
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')
t = df['time']
expert_zones = pd.DataFrame({
    'zone_id': [0, 1, 2],
    'type': ['bull', 'bear', 'bull'],
    'start_time': [t.iloc[100], t.iloc[300], t.iloc[600]],
    'end_time': [t.iloc[140], t.iloc[330], t.iloc[650]],
})

expert = analyze_preloaded_zones(df, expert_zones, clustering=False)
automatic = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=False)
    .build()
)

for name, result in [('expert', expert), ('automatic', automatic)]:
    stats = result.statistics
    print(f"{name:9} zones={len(result.zones):2} {stats['total_statistics']['zones_by_type']} "
          f"mean duration={stats['duration_distribution']['overall']['mean']:.1f} "
          f"mean return={stats['return_distribution']['overall']['mean']:+.4f}")
# expert    zones= 3 {'bull': 2, 'bear': 1} mean duration=41.0 mean return=+0.0071
# automatic zones=77 {'bull': 39, 'bear': 38} mean duration=12.6 mean return=-0.0000
```

Три экспертные зоны здесь — иллюстрация формата, а не разметка; на трёх точках
статистика не говорит ничего. Смысл блока — что обе стороны сравниваются одними ключами.

## 📊 Визуализация
`preloaded_result.visualize('overview', title='Expert zones')` и
`visualize('detail', zone_id=0)` работают так же, как для автоматических зон
([MACD tutorial](macd_basic_pipeline.md), шаг 3). Если зона на графике короче ожидаемой —
смотрите `time_tolerance` и число строк в `zone.data`.

## ✅ Практика
1. **Проверяйте колонки до запуска** — отсутствующие названы в `ValueError`.
2. **Держите исходную разметку рядом с результатом** — `result.save(...)` сохраняет зоны,
   но не файл, из которого они пришли.
3. **`DataFrame` вместо пути** — если зоны приходят из базы или сервиса, передавайте кадр
   напрямую, минуя CSV.
4. **`indicator` в разметке** — заполняйте: это единственная колонка, которая переезжает
   в контекст зоны и позволяет потом отличить источники.

## 🚀 Что дальше
- `.with_strategies(swing='zigzag')` на preloaded-зонах — свинг-метрики внутри чужой
  разметки; см. [свинг-стратегии](../user_guide/swing_strategies.md).
- `examples/02a_universal_zones.py`, раздел preloaded — тот же путь в исполняемом скрипте.
