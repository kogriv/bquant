# Стратегии метрик зон — `bquant.analysis.zones.strategies`

Пять семейств метрик, каждое подключается отдельно и считает своё. Стратегии
индикатор-агностичны: колонка, по которой считать, приходит параметром, а не зашита
в код.

| Семейство | Что измеряет | Имя в реестре → класс | Метрик |
|---|---|---|---|
| swing | колебания внутри зоны: ралли, откаты, их амплитуды и скорости | `zigzag` → `ZigZagSwingStrategy`<br>`find_peaks` → `FindPeaksSwingStrategy`<br>`pivot_points` → `PivotPointsSwingStrategy` | 23 |
| shape | форму осциллятора в зоне: асимметрию, эксцесс, гладкость | `statistical` → `StatisticalShapeStrategy` | 3 |
| divergence | расхождения цены и осциллятора | `classic` → `ClassicDivergenceStrategy` | 4 |
| volatility | волатильность: полосы Боллинджера и ATR | `combined` → `CombinedVolatilityStrategy` | 10 |
| volume | объём относительно фона и его связь с осциллятором | `standard` → `StandardVolumeStrategy` | 4 |

Классы экспортируются из `bquant.analysis.zones.strategies`; в коде их обычно не
называют — стратегия выбирается именем, а имя разрешает реестр.

Список не переписывайте отсюда — спрашивайте у реестра:

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

print(StrategyRegistry.get_registry_stats())
# {'swing': 3, 'divergence': 1, 'shape': 1, 'volume': 1, 'volatility': 1, 'total': 7}
```

## Как подключить

Обычный путь — билдер: имена семейств совпадают с именами параметров.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='line')
    .with_strategies(swing='zigzag', shape='statistical', volatility='combined')
    .analyze()
    .build()
)

metadata = result.zones[0].features['metadata']
print(sorted(k for k in metadata if k.endswith('_metrics')))
# ['shape_metrics', 'swing_metrics', 'volatility_metrics']
```

Ни одно семейство, кроме свингов и формы, по умолчанию не включено: считать всё подряд
дороже, а половина метрик требует данных, которых может не быть (объём, ATR).

## Как задать свои параметры

Реестр отдаёт **готовый экземпляр**, а не класс, и параметры принимает сам:

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

strategy = StrategyRegistry.get_swing_strategy('zigzag', legs=3, deviation=0.008)

print(strategy)
# ZigZagSwingStrategy(legs=3, deviation=0.008)
```

Тот же результат через фабрику из конфигурации — она принимает имя, словарь или готовый
экземпляр:

```python
from bquant.core.config import create_swing_strategy

print(create_swing_strategy('find_peaks'))
# FindPeaksSwingStrategy(prominence=None, distance=5, min_amplitude_pct=0.02, prominence_warmup=200)

print(create_swing_strategy({'type': 'zigzag', 'params': {'legs': 4, 'deviation': 0.01}}))
# ZigZagSwingStrategy(legs=4, deviation=0.01)
```

Для свингов есть третий путь и обычно он лучше двух первых —
[пресеты](../../user_guide/swing_strategies.md): согласованные наборы порогов сразу для
трёх стратегий, `narrow_zone` (по умолчанию) и `wide_zone`.

## Протоколы

Своя стратегия обязана реализовать протокол своего семейства — этого достаточно,
наследование не требуется.

| Семейство | Метод | Возвращает |
|---|---|---|
| swing | `calculate(zone_data, ...)`, `calculate_global(...)`, `aggregate_for_zone(...)`, `config_hash()` | `SwingMetrics` |
| shape | `calculate_shape(zone_data, indicator_col)` | `ShapeMetrics` |
| divergence | `calculate_divergence(zone_data, indicator_col, ...)` | `DivergenceMetrics` |
| volatility | `calculate_volatility(zone_data)` | `VolatilityMetrics` |
| volume | `calculate_volume(zone_data, indicator_col, ...)` | `VolumeMetrics` |

У всех есть `get_metadata()` — имя, описание, параметры и то, что стратегия считает.
Пошаговая инструкция по написанию своей — [Extension Guide](../extension_guide.md).

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

meta = StrategyRegistry.get_shape_strategy('statistical').get_metadata()

print(meta['name'])
print(meta['params'])
# Statistical
# {'calculate_smoothness': True, 'bias_correction': True}
```

## Свинги

**Что считают.** Пивоты внутри зоны и производные от них величины: сколько было ралли и
откатов, какой амплитуды, за сколько баров, с какой скоростью.

| Стратегия | Идея | Параметры по умолчанию |
|---|---|---|
| `zigzag` | фильтр движений по проценту отклонения | `legs=10`, `deviation=0.05` |
| `find_peaks` | локальные экстремумы по проминенции | `prominence=None`, `distance=5`, `min_amplitude_pct=0.02`, `prominence_warmup=200` |
| `pivot_points` | классический N-баровый пивот | `left_bars=2`, `right_bars=2`, `min_amplitude_pct=0.015` |

Значения выше — конструкторские; пресет их перекрывает, и именно пресет определяет,
найдётся ли хоть что-нибудь. Разбор и таблица покрытия —
[свинг-стратегии](../../user_guide/swing_strategies.md).

**23 поля `SwingMetrics`:**

```
num_swings, rally_count, drop_count
avg_rally_pct, avg_drop_pct, max_rally_pct, max_drop_pct, min_rally_pct, min_drop_pct
rally_to_drop_ratio, duration_symmetry
rally_amplitude_std, drop_amplitude_std, rally_amplitude_median, drop_amplitude_median
avg_rally_duration_bars, avg_drop_duration_bars, max_rally_duration_bars, max_drop_duration_bars
avg_rally_speed_pct_per_bar, avg_drop_speed_pct_per_bar,
max_rally_speed_pct_per_bar, max_drop_speed_pct_per_bar
```

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='line')
    .with_strategies(swing='zigzag')
    .analyze()
    .build()
)

longest = max(result.zones, key=lambda zone: zone.duration)
swing = longest.features['metadata']['swing_metrics']

print(swing['num_swings'], round(swing['avg_rally_pct'], 3), round(swing['avg_drop_pct'], 3))
# 21 0.49 0.595
```

## Форма

**Что считает.** Асимметрию, эксцесс и гладкость ряда осциллятора внутри зоны — то есть
где был импульс (в начале или в конце) и насколько он рваный.

`statistical`: `calculate_smoothness=True`, `bias_correction=True`.
Поля: `hist_skewness`, `hist_kurtosis`, `hist_smoothness`.

Имена полей исторические — читаются как «характеристики ряда», а не «характеристики
гистограммы MACD»: считаются они по тому ряду, по которому размечена зона, каким бы
индикатором он ни был.

## Дивергенции

**Что считает.** Расхождения направления цены и осциллятора.

`classic`: `min_peak_distance=5`, `min_divergence_strength=0.01`.
Поля: `divergence_type` (`none` / `regular` / `hidden` / `mixed`), `divergence_count`,
`divergence_strength`, `divergence_direction` (`bullish` / `bearish` / `none`).

## Волатильность

**Что считает.** Полосы Боллинджера и ATR внутри зоны, плюс сводный балл 0–10 и его
словесный режим.

`combined`: `bb_length=20`, `bb_std=2.0`, `touch_threshold=0.01`.

| Поле | Тип | Смысл |
|---|---|---|
| `bollinger_width_pct` | `float \| None` | средняя ширина полос, % от средней линии |
| `bollinger_width_std` | `float \| None` | разброс ширины; требует **двух** наполненных окон |
| `bollinger_squeeze_ratio` | `float \| None` | текущая ширина к средней |
| `bollinger_upper_touches`, `bollinger_lower_touches` | `int \| None` | касания полос |
| `atr_normalized_range` | `float` | размах зоны в ATR |
| `atr_trend` | `str` | `increasing` / `decreasing` / `stable` |
| `avg_atr` | `float` | средний ATR |
| `volatility_score` | `float \| None` | сводный балл 0–10 |
| `volatility_regime` | `str \| None` | `low` / `medium` / `high` / `extreme` |

**`None` здесь означает «не измерено», а не ноль.** У зоны короче окна Боллинджера полос
не существует, и балл, который на две трети складывается из боллинджеровских компонент,
тоже отсутствует — вместе со своим режимом. ATR-часть при этом измерена. До 2026-08-31
вместо отсутствия подставлялись нули со `squeeze_ratio: 1.0`, то есть правдоподобное
измерение вместо признания (`devref/gaps/metrics/g37_…`).

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='line')
    .with_strategies(volatility='combined')
    .analyze()
    .build()
)

short = min((z for z in result.zones if z.duration >= 3), key=lambda z: z.duration)
metrics = short.features['metadata']['volatility_metrics']

print(short.duration, metrics['bollinger_width_pct'], metrics['volatility_regime'])
print(round(metrics['avg_atr'], 2))
# 3 None None
# 14.28
```

## Объём

**Что считает.** Объём зоны относительно фона и его связь с осциллятором.

`standard`: `baseline_window=50`, `correlation_min_periods=3`.
Поля: `volume_zone_ratio`, `volume_at_entry_change`, `volume_indicator_corr`,
`avg_volume_zone` — все `Optional`, потому что колонки `volume` может не быть вовсе.

`volume_indicator_corr` называется так с 2026-08: раньше поле звалось
`volume_macd_corr`, и имя одного индикатора стояло в универсальной метрике.

## Сравнить стратегии между собой

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

for name in ('zigzag', 'find_peaks', 'pivot_points'):
    result = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_role='line')
        .with_strategies(swing=name)
        .analyze()
        .build()
    )
    coverage = result.metadata['swing_coverage']
    print(f"{name:<13} {coverage['zones_with_swings']}/{coverage['zones']}")
# zigzag        29/32
# find_peaks    20/32
# pivot_points  23/32
```

Сравнивать стратегии по числу найденных свингов имеет смысл только при одинаковых
порогах: `swing_coverage` показывает, у скольких зон улов вообще непустой, и первым делом
смотреть надо туда.

## Дальше

| | |
|---|---|
| [Свинг-стратегии](../../user_guide/swing_strategies.md) | пресеты, адаптивные пороги, покрытие |
| [Структура результата](../../user_guide/zone_analysis_result.md) | где лежат метрики в результате |
| [Pipeline API](pipeline.md) | как включать стратегии |
| [Extension Guide](../extension_guide.md) | как написать свою |
