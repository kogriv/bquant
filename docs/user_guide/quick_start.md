# Быстрый старт

## Установка

```bash
pip install bquant
```

Python 3.12+. Из исходников — `git clone` и `pip install -e .`.

Проверка:

```python
import bquant

print(bquant.__version__)
```

## Первый анализ

Всё, что нужно для примеров, лежит внутри пакета — внешние файлы не понадобятся.

### 1. Данные

```python
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

print(len(data))                                        # 1000
print(data['time'].iloc[0], '→', data['time'].iloc[-1])
# 2025-06-11 20:00:00+07:00 → 2025-08-12 13:00:00+07:00
```

Время здесь лежит **в колонке** `time`, а не в индексе. Пайплайн разбирается с этим сам:
он переносит время на индекс на входе, поэтому границы зон приходят временами. Класть
время на индекс вручную не нужно.

### 2. Зоны

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

print(len(result.zones))   # 64
```

Индикатор адресуется **ролью** (`indicator_role='value'`), а не именем колонки: имя
зависит от библиотеки и параметров вызова, роль — нет.

### 3. Что получилось

```python
from collections import Counter

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze()
    .build()
)

print(Counter(zone.type for zone in result.zones))
# Counter({'neutral': 32, 'oversold': 18, 'overbought': 14})

zone = result.zones[0]
print(zone.type, zone.start_time, '→', zone.end_time, zone.duration)
# overbought 2025-06-11 21:00:00+07:00 → 2025-06-12 13:00:00+07:00 16
```

**Словарь типов зон следует за индикатором.** У RSI это `overbought` / `neutral` /
`oversold`, у MACD — `bull` / `bear`. Не предполагайте `bull`/`bear`: для осциллятора,
у которого нет направления, такого деления не существует.

То же распределение считает и сам пайплайн: `result.statistics['total_statistics']`
содержит `zones_by_type` и `ratios_by_type` по фактически встреченным типам. Поля
`bull_zones_count`/`bull_ratio` появляются там только у словаря, который эти типы
содержит, — у RSI их не будет, и это верно: такого деления у него не существует.

### 4. MACD в одну строку

```python
from bquant.analysis.zones import analyze_macd_zones
from bquant.data.samples import get_sample_data

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))

print(len(result.zones))   # 32
```

Пресет — тот же пайплайн с заранее выбранными индикатором и стратегией детекции.
Границу он проводит **по знаку линии MACD** (`zone_basis='line'`), а не по
гистограмме: гистограмма меняет знак чаще, и по ней тех же данных выходит 83 зоны
вместо 32. Переключается параметром: `analyze_macd_zones(data, zone_basis='histogram')`.

### 5. Статистические тесты

Считаются вместе с зонами, если не отключить:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))

tests = result.hypothesis_tests.results['tests']
print(len(tests))          # 7
print(sorted(tests)[:3])   # ['contrast_asymmetry', 'correlation_drawdown', 'duration_stationarity']
```

Тест, которому не хватило данных, возвращает `error` вместо `p_value` и **называет
причину**. Это отказ по существу, а не сбой:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))

for name, outcome in result.hypothesis_tests.results['tests'].items():
    if 'p_value' in outcome:
        print(f"{name}: p={outcome['p_value']:.4f}")
    else:
        print(f"{name}: не посчитан — {outcome.get('error')}")
```

### 6. Внешние индикаторы

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager

data = get_sample_data('tv_xauusd_1h')

LibraryManager.load_all_libraries()
rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)

print(rsi.calculate(data).data.columns.tolist())   # ['RSI_14']
```

Подробности — [LibraryManager](../api/indicators/library_manager.md).

### 7. График

```python
import plotly.io as pio

from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts

pio.renderers.default = 'json'   # безопасный renderer для среды без браузера

data = get_sample_data('tv_xauusd_1h')
figure = FinancialCharts().create_candlestick_chart(data, title='XAUUSD 1H')

print(type(figure).__name__)   # Figure
```

Готовую картинку с зонами быстрее получить из командной строки:

```bash
bquant analyze tv_xauusd_1h --indicator rsi -o zones.html
```

## Если что-то не работает

```python
import bquant
from bquant.data.samples import list_dataset_names

print(bquant.__version__)
print(list_dataset_names())   # ['tv_xauusd_1h', 'mt_xauusd_m15']
```

Если версия и наборы данных на месте, а результат всё равно неожиданный, —
[заведите issue](https://github.com/kogriv/bquant/issues) с воспроизведением.

## Дальше

| | |
|---|---|
| [Core Concepts](core_concepts.md) | из чего состоит анализ зон |
| [Zone Analysis](zone_analysis.md) | подробно про пайплайн на практике |
| [Pipeline API](../api/analysis/pipeline.md) | справочник билдера |
| [Стратегии](../api/analysis/strategies.md) | swing, shape, divergence, volatility, volume |
| [CLI](cli.md) | то же самое из командной строки |
| [Примеры](../examples/README.md) | разбор готовых скриптов |
