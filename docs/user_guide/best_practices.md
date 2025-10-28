# Best Practices анализа зон BQuant

Руководство собирает проверенные приемы для работы с универсальным пайплайном анализа зон и модульными компонентами. Материал основан на практиках из `devref/gaps/zo/zomodul.md`, но адаптирован для повседневного использования аналитиками и разработчиками.

## Когда выбирать полный пайплайн, а когда модульные шаги

**Используйте `analyze_zones(...).build()` если:**

- нужен стандартный end-to-end анализ без кастомизаций;
- выполняется разовый запуск и нет необходимости сохранять промежуточные артефакты;
- важна минимальная точка входа: одна функция возвращает `ZoneAnalysisResult`.

**Выбирайте модульный подход (компоненты `IndicatorFactory`, `ZoneDetectionStrategy`, `UniversalZoneAnalyzer` и т.д.), когда:**

- требуется остановиться на промежуточном этапе (например, только детекция зон);
- нужно переиспользовать результаты на множестве инструментов или таймфреймов;
- в проекте присутствует кастомная логика, которую удобнее встроить между шагами пайплайна;
- зоны поступают из внешних источников (preloaded) и нужно анализировать их без пересчета индикаторов;
- строится ML/статистика поверх признаков зон, а не полный отчет.

## Рекомендуемая структура артефактов

Поддерживайте единообразную иерархию для сохранения результатов:

```
results/
├── {instrument}_{timeframe}/
│   ├── 01_indicator_data.parquet       # Данные с индикаторами
│   ├── 02_zones.pkl                    # Объекты ZoneInfo
│   ├── 02_zones.csv                    # Легкая мета-информация о зонах
│   ├── 03_features.csv                 # Признаки зон
│   ├── 04_statistics.json              # Распределения и агрегации
│   ├── 05_hypotheses.json              # Гипотезы и p-value
│   ├── 06_sequence.json                # Переходы зон
│   ├── 07_clustering.json              # Результаты кластеризации
│   ├── 08_regression.json              # Модели прогноза (если нужны)
│   ├── full_analysis.pkl               # Полный ZoneAnalysisResult
│   ├── summary.json                    # Краткая сводка
│   └── visualizations/
│       ├── overview.html
│       ├── zone_3_detail.html
│       └── zones_comparison.html
```

Такая структура облегчает повторное использование и позволяет быстро найти нужный артефакт независимо от выбранного подхода.

## Паттерны переиспользования

### Detect Once, Analyze Many

```python
import pickle

# 1. Детектируем зоны один раз
zones = detector.detect_zones(df, config)
with open("zones.pkl", "wb") as f:
    pickle.dump(zones, f)

# 2. Пробуем разные варианты анализа
for n_clusters in [2, 3, 4, 5]:
    analyzer = UniversalZoneAnalyzer()
    result = analyzer.analyze_zones(zones, df, n_clusters=n_clusters)
    result.save(f"analysis_clusters_{n_clusters}.pkl")
```

### Extract Once, Use Everywhere

```python
zones_features = features_analyzer.extract_all_zones_features(zones)
features_df = pd.DataFrame([zf.to_dict() for zf in zones_features])
features_df.to_csv("features.csv", index=False)

# Далее файл можно передать в ML, статистику или BI.
```

### Incremental Analysis

```python
# День 1: детекция
zones = detect_zones(...)
save(zones, "zones_day1.pkl")

# День 2: признаки
zones = load("zones_day1.pkl")
features = extract_features(zones)
save(features, "features_day2.csv")

# День 3: статистика
features = load("features_day2.csv")
statistics = analyze_statistics(features)
save(statistics, "stats_day3.json")

# День 4: финальный отчет
zones = load("zones_day1.pkl")
result = full_analysis(zones, df)
result.save("final_report.pkl")
```

## Управление версиями результатов

```python
import os
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

zones_file = f"results/zones_{timestamp}.pkl"
with open(zones_file, "wb") as f:
    pickle.dump(zones, f)

analysis_file = f"results/analysis_{timestamp}.pkl"
result.save(analysis_file)

# Обновляем "последние" ссылки для интеграций
os.symlink(zones_file, "results/zones_latest.pkl")
os.symlink(analysis_file, "results/analysis_latest.pkl")
```

В проекте, где пайплайн запускается по расписанию, симлинки или алиасы на «последнюю» версию значительно упрощают автоматизацию.

## Интеграция с внешними системами

- **Экспорт в MT5 / cTrader** — храните зоны в CSV с полями `start_time`, `end_time`, `type`, `start_bar`, `end_bar`. Функцию экспорта можно адаптировать из `PreloadedZonesDetection`.
- **Импорт внешних зон** — подайте DataFrame с нужными колонками в `PreloadedZonesDetection` и продолжите анализ с шага UniversalZoneAnalyzer.
- **Совместимость с ML-пайплайнами** — сериализуйте признаки в `features.csv` и подключайте их к существующим моделям без дополнительных преобразований.

## Связанные материалы

- [Zone Analysis Guide](zone_analysis.md) — описание полного пайплайна и архитектуры.
- [MIGRATION_v2.md](../MIGRATION_v2.md) — пошаговая миграция со старого `MACDZoneAnalyzer` на новый pipeline.
- [`devref/gaps/zo/zomodul.md`](../../devref/gaps/zo/zomodul.md) — подробные инженерные сценарии модульного использования.
