# Core Concepts — Базовые концепции BQuant

## 🎯 Назначение раздела

Этот раздел связывает быстрый старт с подробной документацией и объясняет, как устроен Universal Zone Analysis Pipeline v2.1. Вы узнаете, какие компоненты участвуют в анализе зон, как подготавливаются данные и какие результаты возвращаются пользователю.

## 🧱 Ключевые составляющие Universal Pipeline

| Компонент | Что делает | Где описан |
|-----------|------------|------------|
| **DataFrame с OHLCV** | Исходные котировки и готовые индикаторы | [Data Management](../api/data/README.md) |
| **IndicatorConfig** | Описание источника и параметров индикатора | [Indicators](../api/indicators/README.md) |
| **ZoneDetectionConfig** | Стратегия поиска зон и её правила | [Analysis / Zones](../api/analysis/zones.md) |
| **UniversalZoneAnalyzer** | Извлекает признаки, гипотезы, последовательности | [Analysis / pipeline](../api/analysis/pipeline.md) |
| **ZoneAnalysisResult** | Итоговый объект с зонами, метриками и сервисными данными | [Analysis / base](../api/analysis/base.md) |

> ℹ️ Universal Pipeline не привязан к MACD. Любой индикатор (включая пользовательский) или готовый столбец может стать основой для зон при корректной конфигурации `ZoneDetectionConfig`.

## 🔄 Поток данных и контрольные точки

1. **Подготовка данных** — убедитесь, что DataFrame содержит столбцы `time`, `open`, `high`, `low`, `close`, `volume` и дополнительные индикаторы.
2. **Настройка индикатора** — либо рассчитываем индикатор в пайплайне, либо подаем готовые значения (например, `macd_hist`).
3. **Выбор стратегии детекции** — `zero_crossing`, `threshold`, `line_crossing`, `preloaded` или `combined`.
4. **Анализ зон** — UniversalZoneAnalyzer рассчитывает признаки, гипотезы и (по необходимости) регрессию, валидацию и кластеризацию.
5. **Интерпретация результата** — объект `ZoneAnalysisResult` содержит списки зон, статистику, отчеты по стратегиям и вспомогательные данные для визуализации.

## ⚙️ Конфигурация пайплайна через классы

Следующий пример повторяет структуру документации и показывает, из каких элементов собирается pipeline.

```python
from bquant.analysis.zones.pipeline import IndicatorConfig, ZoneDetectionConfig, ZoneAnalysisConfig

config = ZoneAnalysisConfig(
    indicator=IndicatorConfig(
        source='custom',
        name='macd',
        params={'fast': 12, 'slow': 26, 'signal': 9}
    ),
    zone_detection=ZoneDetectionConfig(
        strategy_name='zero_crossing',
        rules={'indicator_col': 'macd_hist'},
        min_duration=3
    ),
    perform_clustering=True,
    n_clusters=3,
    run_regression=False,
    run_validation=False
)

print(config.zone_detection.strategy_name)
print(config.indicator.name)
```

## 🚀 Минимальный анализ зон на готовых данных

В sample-данных `tv_xauusd_1h` уже присутствуют столбцы `macd` и `signal`, поэтому гистограмму можно получить вычитанием. Это избавляет от повторного расчета индикатора и демонстрирует, как документация рекомендует работать с готовыми колонками.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

df = get_sample_data('tv_xauusd_1h').head(200).copy()
df['macd_hist'] = df['macd'] - df['signal']  # В документации делаем явную оговорку

result = (
    analyze_zones(df)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(len(result.zones))
print(sorted(result.statistics.keys())[:3])
print(result.clustering is not None)
```

### Что важно знать о `ZoneAnalysisResult`

- `zones` — список обнаруженных зон с временными границами, типом и метаданными.
- `statistics` — агрегированные метрики (длительность, распределение амплитуд, асимметрия и т.д.).
- `hypothesis_tests` — результаты гипотез (подходят для отчетов и автоматической валидации).
- `clustering`, `regression_results`, `validation_results` — присутствуют, если вы включили соответствующие этапы.
- `data` — копия исходного DataFrame (можно отключить через параметры сохранения).

## 📎 Что почитать дальше

- [Quick Start](quick_start.md) — если хотите сразу применить пайплайн к своим данным.
- [Core Modules](../api/core/README.md) — архитектура ядра и сервисные компоненты.
- [Analysis / pipeline](../api/analysis/pipeline.md) — полный справочник по конфигурации и расширениям.
- [Visualization](../api/visualization/README.md) — способы представить результаты `ZoneAnalysisResult`.
