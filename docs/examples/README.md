# Примеры

Одиннадцать исполняемых скриптов в каталоге `examples/` репозитория. Каждый
самодостаточен: данные — встроенные сэмплы или синтетика, внешних файлов нет. Ниже — что
показывает каждый и с какого начинать; описания сверены с докстрингами скриптов.

## Какой открыть первым

| Сценарий | Скрипт |
|---|---|
| впервые вижу пайплайн зон | `02_macd_zone_analysis.py` |
| хочу тот же конвейер на другом индикаторе | `02a_universal_zones.py` |
| мне нужны метрики внутри зон | `05_strategies_demo.py`, `08_macd_swing_analysis.py` |
| мне нужны графики | `09_zones_visualization_demo.py` |

## Все скрипты

| Скрипт | Что показывает |
|---|---|
| `01_basic_indicators.py` | `IndicatorFactory`: SMA, RSI, MACD, Bollinger из `custom` и `pandas_ta`; синтетические OHLCV-данные |
| `02_macd_zone_analysis.py` | MACD-зоны четырьмя способами: пресет `analyze_macd_zones()`, билдер `analyze_zones()`, разные стратегии детекции, компоненты по отдельности; базовая визуализация |
| `02a_universal_zones.py` | один конвейер для MACD, RSI, AO, пересечения скользящих, Stochastic, кастомного индикатора и preloaded-зон; кэш, сохранение в pickle/JSON/parquet |
| `03_data_processing.py` | загрузка из CSV и сэмплов, очистка, валидация схемы, производные признаки, сохранение в `outputs/` |
| `04_comprehensive_analysis.py` | полный путь: подготовка → индикаторы → детекция → анализ → визуализация → сохранение/загрузка результата |
| `05_strategies_demo.py` | `.with_strategies(...)`: swing, shape, divergence, volatility, volume; чтение `zone.features` |
| `06_regression_demo.py` | признаки зон из пайплайна (`swing='find_peaks'`, `shape='statistical'`) → линейная регрессия `sklearn` на них, важность признаков, второй индикатор для сравнения |
| `07_validation_demo.py` | та же линейная модель на признаках зон, проверенная out-of-sample и walk-forward |
| `08_macd_swing_analysis.py` | свинг-метрики **внутри** зон через `zone.features['metadata']['swing_metrics']` — только встроенными средствами |
| `09_zones_visualization_demo.py` | четыре режима визуализации зон (overview, detail, comparison, statistics) и их настройки |
| `zone_analysis_global_swings.py` | `per_zone` против `global` для свингов: покрытие, число колебаний, список пивотов |

Исследовательские скрипты в `research/notebooks/` — другой жанр: пошаговые прогоны в
стиле ноутбука ([NotebookSimulator](../api/core/nb.md)), запускаются с `--no-trap`.

## Как запускать

```bash
git clone https://github.com/kogriv/bquant.git
cd bquant
pip install -e .

python examples/02_macd_zone_analysis.py
```

Скрипты добавляют корень репозитория в `sys.path`, поэтому работают и без установки — из
клона. Без дисплея ставьте `MPLBACKEND=Agg`: иначе `plt.show()` в конце некоторых скриптов
ждёт окна. Скрипты, пишущие артефакты, кладут их в `outputs/`.

## Тот же код в три строки

Два самодостаточных фрагмента из скриптов — чтобы не открывать файл ради идеи.

**Любой индикатор — одна цепочка** (`02a_universal_zones.py`):

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14',   # колонка создаётся pandas-ta
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

print(f"Найдено зон: {len(result.zones)}")
print(result.statistics['total_statistics']['zones_by_type'])
# Найдено зон: 64
# {'neutral': 32, 'oversold': 18, 'overbought': 14}
```

**Метрики внутри зон и гипотезы** (`05_strategies_demo.py`):

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(
        swing='find_peaks',      # колебания внутри зоны
        divergence='classic',    # дивергенции цена/индикатор
        volume='standard',       # объём
        volatility='combined',   # волатильность
    )
    .analyze(clustering=True)
    .build()
)

tests = result.hypothesis_tests.results['tests']
for name, test in tests.items():
    print(f"{name}: p={test['p_value']:.4f}")
```

## Куда дальше

- [Tutorials](../tutorials/README.md) — те же сценарии короче и с пояснениями.
- [Справочник пайплайна](../api/analysis/pipeline.md) и
  [стратегии детекции](../api/analysis/strategies.md).
- [Визуализация зон](../api/visualization/zones.md).
