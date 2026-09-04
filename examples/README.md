# BQuant Examples

Исполняемые примеры. Каждый самодостаточен — встроенные сэмплы или синтетические данные,
внешних файлов нет. Разбор каждого скрипта и самодостаточные фрагменты — в документации:
`docs/examples/README.md` (на сайте — раздел «Примеры»).

## Запуск

```bash
pip install -e .            # из клона; или pip install bquant
python examples/02_macd_zone_analysis.py
```

Скрипты добавляют корень репозитория в `sys.path` и работают из клона без установки.
Без дисплея — `MPLBACKEND=Agg`, иначе `plt.show()` ждёт окна. Артефакты пишутся в `outputs/`.

## С чего начать

1. `02_macd_zone_analysis.py` — пресет `analyze_macd_zones()`, билдер `analyze_zones()`,
   стратегии детекции, компоненты по отдельности.
2. `02a_universal_zones.py` — тот же конвейер для RSI, AO, скользящих, Stochastic,
   кастомного индикатора и preloaded-зон.
3. `05_strategies_demo.py` — метрики внутри зон (`.with_strategies(...)`).
4. `09_zones_visualization_demo.py` — четыре режима визуализации.

## Все скрипты

| Скрипт | Тема |
|---|---|
| `01_basic_indicators.py` | индикаторы через `IndicatorFactory` |
| `02_macd_zone_analysis.py` | MACD-зоны: пресет, билдер, стратегии, компоненты |
| `02a_universal_zones.py` | один конвейер для любого индикатора; кэш и сохранение |
| `03_data_processing.py` | загрузка, очистка, валидация, производные признаки |
| `04_comprehensive_analysis.py` | полный путь от данных до сохранённого результата |
| `05_strategies_demo.py` | swing / shape / divergence / volatility / volume |
| `06_regression_demo.py` | линейная регрессия `sklearn` на признаках зон |
| `07_validation_demo.py` | out-of-sample и walk-forward проверка модели на признаках зон |
| `08_macd_swing_analysis.py` | свинг-метрики внутри зон |
| `09_zones_visualization_demo.py` | визуализация зон |
| `zone_analysis_global_swings.py` | свинги `per_zone` против `global` |

## Минимум, который нужен всем

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True)
    .build()
)
print(len(result.zones))   # 77
```

Пресеты для частых случаев — `analyze_macd_zones`, `analyze_rsi_zones`, `analyze_ao_zones`,
`analyze_preloaded_zones` в `bquant.analysis.zones.presets`. Кэш результатов включён по
умолчанию.

Требования: Python 3.12+. Исследовательские скрипты — в `research/notebooks/`
(запускать с `--no-trap`).
