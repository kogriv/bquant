# Справочник API

Карта модулей пакета. Практическая сторона — в [руководстве пользователя](../user_guide/README.md);
здесь описано, что где лежит и как называется.

## Карта модулей

| Модуль | О чём | Страница |
|---|---|---|
| `bquant.analysis.zones` | пайплайн анализа зон, детекция, модели, пресеты | [пайплайн](analysis/pipeline.md) · [зоны](analysis/zones.md) |
| `bquant.analysis.zones.strategies` | метрики зон: swing, shape, divergence, volatility, volume | [стратегии](analysis/strategies.md) |
| `bquant.analysis.statistical` | проверка гипотез, распределения, регрессия | [статистика](analysis/statistical.md) |
| `bquant.analysis` | базовые классы анализа, реестр видов анализа | [база](analysis/base.md) · [обзор](analysis/README.md) |
| `bquant.indicators` | фабрика, встроенные индикаторы, внешние библиотеки | [обзор](indicators/README.md) |
| `bquant.indicators.base` | `BaseIndicator`, `IndicatorFactory`, `IndicatorConfig` | [база](indicators/base.md) · [фабрика](indicators/factory.md) |
| `bquant.indicators.custom` | реализации внутри пакета: SMA, EMA, RSI, MACD, Bollinger | [встроенные](indicators/custom.md) |
| `bquant.indicators.preloaded` | индикаторы поверх уже посчитанных колонок | [preloaded](indicators/preloaded.md) |
| `bquant.indicators.library` | pandas-ta и TA-Lib через `LibraryManager` | [менеджер библиотек](indicators/library_manager.md) |
| `bquant.data.loader` | чтение OHLCV из файлов | [загрузка](data/loader.md) |
| `bquant.data.processor` | подготовка кадра, нормализация индекса | [обработка](data/processor.md) |
| `bquant.data.validator` | проверки качества данных | [валидация](data/validator.md) |
| `bquant.data.samples` | встроенные наборы данных | [наборы](data/samples.md) |
| `bquant.data.schemas` | описания структур данных | [схемы](data/schemas.md) |
| `bquant.core.config` | конфигурация, таймфреймы, пресеты свингов | [config](core/config.md) |
| `bquant.core.cache` | двухуровневый кэш | [кэширование](../user_guide/caching.md) |
| `bquant.core.logging_config` | настройка логирования | [логирование](core/logging.md) |
| `bquant.core.nb` | `NotebookSimulator` для исследовательских скриптов | [nb](core/nb.md) |
| `bquant.core.performance` | замер и мониторинг производительности | [производительность](core/performance.md) |
| `bquant.core.exceptions` | иерархия исключений | [исключения](core/exceptions.md) |
| `bquant.core.utils` | вспомогательные функции | [утилиты](core/utils.md) |
| `bquant.visualization.charts` | финансовые графики | [визуализация](visualization/README.md) |
| `bquant.visualization.zones` | графики зон | [зоны на графике](visualization/zones.md) |
| `bquant.visualization.statistical` | статистические графики | [визуализация](visualization/README.md) |
| `bquant.visualization.themes` | пять тем оформления | [визуализация](visualization/README.md) |

Модулей `bquant.indicators.macd`, `bquant.indicators.factory` и
`bquant.indicators.library_manager` **не существует**: MACD-индикатор живёт в
`custom`/`preloaded`, фабрика — в `base`, менеджер библиотек — в пакете `library`.
Страницы справочника названы по предмету, а не по файлу.

## Размер поверхности — спросите у пакета

Числа вроде «столько-то классов» устаревают быстрее, чем их успевают исправить, поэтому
здесь не число, а способ его получить:

```python
from bquant.indicators import IndicatorFactory

catalogue = IndicatorFactory.list_indicators()

print(len(catalogue))                                    # 164
print(sorted({source for source in catalogue.values()}))  # ['custom', 'library', 'preloaded']
```

На сегодня это 158 индикаторов из `pandas-ta`, 5 собственных (`sma`, `ema`, `rsi`,
`macd`, `bbands`) и 1 preloaded. TA-Lib добавляет свои, если библиотека установлена.

## С чего начать

| Задача | Точка входа |
|---|---|
| проанализировать зоны | `analyze_zones(df)` → [пайплайн](analysis/pipeline.md) |
| то же для MACD одной строкой | `analyze_macd_zones(df)` |
| загрузить свои данные | `load_ohlcv_data(path)` → [загрузка](data/loader.md) |
| взять встроенные данные | `get_sample_data('tv_xauusd_1h')` → [наборы](data/samples.md) |
| посчитать индикатор | `IndicatorFactory.create(...)` → [фабрика](indicators/factory.md) |
| построить график | `FinancialCharts()` → [визуализация](visualization/README.md) |
| написать свою стратегию | [Extension Guide](extension_guide.md) |

## Пример: от данных до зон

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='line')
    .with_strategies(swing='zigzag', shape='statistical')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(len(result.zones), result.metadata['swing_coverage']['zones_with_swings'])
# 32 29
```

Второе число — сколько зон получили хотя бы один свинг. Смотреть на него стоит всегда:
пустые свинг-метрики выглядят так же, как честно измеренное отсутствие движения.

## Индикатор поверх уже посчитанных колонок

Когда значения индикатора пришли вместе с данными, считать их заново не нужно:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.indicators.preloaded import MACDPreloadedIndicator

data = get_sample_data('tv_xauusd_1h')

print(MACDPreloadedIndicator().calculate(data).data.columns.tolist())
# ['macd', 'signal']

result = (
    analyze_zones(data)
    .with_indicator('preloaded', 'macd_preloaded')
    .detect_zones('zero_crossing', indicator_role='line')
    .analyze(clustering=False)
    .build()
)

print(len(result.zones))   # 30
```

Тридцать зон, а не тридцать две: колонка `macd` пришла из набора данных и посчитана не
теми параметрами, что наш `custom.macd`.

## Что удалено

Замены для имён, которых больше нет:

| Было | Стало | Когда |
|---|---|---|
| `MACDZoneAnalyzer` | `analyze_zones()` или пресет `analyze_macd_zones()` | 0.0.5 |
| `MACDZoneAnalyzer.analyze_complete()` | `.analyze().build()` | 0.0.5 |
| `_zone_to_dict()` | `zone.features` | 0.0.5 |
| `bquant.ml` | — (обе публичные функции только поднимали `NotImplementedError`) | 0.0.7 |
| `IndicatorConfig` из `bquant.analysis.zones` | `IndicatorSpec` — заявка на расчёт, не описание посчитанного | 2026-08-24 |

Пакет не держит переходных периодов: переименование доводится до конца в одном
изменении, а `CHANGELOG.md` называет замену для каждого сломанного имени.

## Дальше

| | |
|---|---|
| [Руководство пользователя](../user_guide/README.md) | как этим пользоваться |
| [Extension Guide](extension_guide.md) | как добавить свою стратегию или индикатор |
| [Руководство разработчика](../developer_guide/README.md) | как устроено внутри |
