# bquant.indicators.macd — MACD и анализ зон

## Обзор

Современный анализатор зон MACD: расчёт индикаторов, идентификация зон (bull/bear), извлечение признаков, статистика, гипотезы, последовательности, кластеризация.

## Классы

- `ZoneInfo`: информация о зоне (type, start_time/end_time, duration, data, features)
- `ZoneAnalysisResult`: итог анализа (zones, statistics, hypothesis_tests, clustering, sequence_analysis, metadata)
- `MACDZoneAnalyzer`:
  - `calculate_macd_with_atr(df) -> DataFrame`
  - `identify_zones(df) -> List[ZoneInfo]`
  - `calculate_zone_features(zone) -> Dict`
  - `analyze_zones_distribution(zones) -> Dict`
  - `test_hypotheses(zones) -> Dict`
  - `analyze_zone_sequences(zones) -> Dict`
  - `cluster_zones_by_shape(zones, n_clusters) -> Dict`
  - `analyze_complete(df, perform_clustering=True, n_clusters=3) -> ZoneAnalysisResult`

## Вспомогательные функции

- `create_macd_analyzer(macd_params=None, zone_params=None) -> MACDZoneAnalyzer`
- `analyze_macd_zones(df, macd_params=None, zone_params=None, perform_clustering=True, n_clusters=3) -> ZoneAnalysisResult`

## Примеры

Полный анализ:
```python
from bquant.indicators.macd import MACDZoneAnalyzer

an = MACDZoneAnalyzer()
res = an.analyze_complete(df)
print(len(res.zones), res.statistics.keys())
```

Просмотр зон и признаков:
```python
for z in res.zones:
    print(z.type, z.start_time, z.end_time, z.duration)
    if z.features:
        print(z.features['macd_amplitude'], z.features['price_return'])
```

Сценарий с удобной функцией:
```python
from bquant.indicators.macd import analyze_macd_zones
res = analyze_macd_zones(df, perform_clustering=False)
```

## Замечания

- Для больших датасетов применяется ускоренная NumPy-реализация MACD (`OptimizedIndicators.macd`).
- ATR и производные индикаторы добавляются через `data.processor.calculate_derived_indicators`.

## См. также

- [База индикаторов](base.md)
- [Фабрика и библиотека](factory.md)
