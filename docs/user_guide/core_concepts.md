# Базовые концепции

Страница между [быстрым стартом](quick_start.md) и справочником: из чего состоит анализ
зон и что возвращается в результате.

## Из чего собирается анализ

| Компонент | Что делает | Где описан |
|---|---|---|
| `DataFrame` с OHLCV | исходные котировки, возможно с готовыми индикаторами | [Данные](../api/data/README.md) |
| `IndicatorSpec` | заявка на расчёт: какой индикатор и с какими параметрами | [Pipeline](../api/analysis/pipeline.md) |
| `ZoneDetectionConfig` | стратегия поиска зон и её правила | [Зоны](../api/analysis/zones.md) |
| `UniversalZoneAnalyzer` | признаки зон, гипотезы, последовательности | [Pipeline](../api/analysis/pipeline.md) |
| `ZoneAnalysisResult` | итог: зоны, метрики, служебные данные | [Базовые классы](../api/analysis/base.md) |

Пайплайн **не привязан к MACD**. Основой зон может стать любой индикатор — встроенный,
из внешней библиотеки, свой собственный — или уже посчитанная колонка.

## Поток данных

1. **Данные.** Кадр с `open`, `high`, `low`, `close` и, если есть, `volume`. Время может
   лежать в колонке (`time`, `timestamp`, `date`, `datetime`) или уже в индексе —
   пайплайн приводит к индексу сам и не выдумывает время там, где его нет.
2. **Индикатор.** Либо считаем в пайплайне — тогда колонки называются канонически
   (`macd_12_26_9__hist`) и адресуются **ролью**; либо подаём готовые значения под своими
   именами и адресуемся именем колонки.
3. **Детекция.** Одна из пяти стратегий: `zero_crossing`, `threshold`, `line_crossing`,
   `preloaded`, `combined`.
4. **Анализ.** Признаки зон, гипотезы, при желании — кластеризация, регрессия, валидация.
5. **Результат.** `ZoneAnalysisResult`.

## Роль или имя колонки

Разница определяет, переживёт ли ваш код смену параметров.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

# Индикатор считает пайплайн — есть схема, адресуемся ролью.
by_role = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze()
    .build()
)

print(len(by_role.zones))                                       # 32
print([c for c in by_role.data.columns if c.startswith('macd_')])
# ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']
```

Имя колонки собирается из **фактических параметров вызова**: `fast_period=5` дало бы
`macd_5_26_9__hist`. Поэтому по имени адресуются только там, где схемы нет — то есть
когда колонку принесли вы сами:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

df = get_sample_data('tv_xauusd_1h').head(200).copy()
df['my_hist'] = df['macd'] - df['signal']   # своя колонка, своё имя

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='my_hist')
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(len(result.zones))
print(result.clustering is not None)   # True
```

Во встроенном наборе `tv_xauusd_1h` уже есть колонки `macd` и `signal` — от источника
данных, а не от нашего расчёта. Поэтому гистограмму здесь можно получить вычитанием, не
считая индикатор заново.

## Конфигурация объектами

Билдер `analyze_zones()` — удобная обёртка. Ту же конфигурацию можно собрать классами,
если она приходит, например, из файла:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones.pipeline import (
    IndicatorSpec,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
    ZoneDetectionConfig,
)

config = ZoneAnalysisConfig(
    indicator=IndicatorSpec(
        source='custom',
        name='macd',
        # Имена параметров — те же, что у самого индикатора: `fast_period`, а не `fast`.
        parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
    ),
    zone_detection=ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_role': 'hist'},
    ),
    # Порог длительности — параметр анализа, а не детекции: детекция обязана вернуть
    # полное мощение, иначе соседство зон становится выдумкой.
    min_duration=3,
    perform_clustering=True,
    n_clusters=3,
    run_regression=False,
    run_validation=False,
)

result = ZoneAnalysisPipeline(config).run(get_sample_data('tv_xauusd_1h'))
print(len(result.zones))
```

`parameters` уходит в конструктор индикатора **как есть**, поэтому имена там его
собственные. Словарь `DEFAULT_INDICATORS` из `bquant.core.config` записан в стиле внешних
библиотек (`fast`, `slow`, `signal`) и сюда подставляться не должен — см.
[config](../api/core/config.md).

## Что лежит в `ZoneAnalysisResult`

| Поле | Что это |
|---|---|
| `zones` | найденные зоны: границы, тип, признаки |
| `statistics` | агрегаты: длительность, распределения амплитуд, асимметрия |
| `hypothesis_tests` | результаты статистических тестов |
| `clustering`, `regression_results`, `validation_results` | заполнены, если соответствующий этап включали |
| `data` | кадр, **с которым работал пайплайн** |
| `metadata` | служебное: версия схемы кэша, отчёт фильтра длительности |

Про `data` стоит сказать точнее, потому что это частый источник путаницы: **это не копия
входного кадра.** Пайплайн нормализует индекс (время переезжает из колонки) и добавляет
колонки посчитанного индикатора. Именно этот кадр, а не исходный, нужно передавать в
визуализацию — иначе зоны не совпадут с осью.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_macd_zones

data = get_sample_data('tv_xauusd_1h')
result = analyze_macd_zones(data)

print(type(data.index).__name__, '→', type(result.data.index).__name__)
# RangeIndex → DatetimeIndex
print(len(data.columns), '→', len(result.data.columns))
# 15 → 17
```

## Дальше

- [Zone Analysis](zone_analysis.md) — пайплайн на практике
- [Pipeline API](../api/analysis/pipeline.md) — полный справочник билдера и конфигурации
- [Visualization](../api/visualization/README.md) — как показать `ZoneAnalysisResult`
- [Core Modules](../api/core/README.md) — устройство ядра
