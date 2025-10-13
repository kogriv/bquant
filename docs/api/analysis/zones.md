# bquant.analysis.zones — Анализ зон

> **⚠️ API Evolution Notice**
> 
> **Current Status (Phase 3-4):** This module works with MACD zones specifically.
> Some field names are MACD-specific (e.g., `macd_amplitude`, `hist_amplitude`).
> 
> **Planned Changes:** Future universalization refactoring will rename these fields
> to be indicator-agnostic (e.g., `indicator_amplitude`, `signal_amplitude`).
> 
> **Timeline:** After 2-3 weeks testing period based on real usage.
> 
> **For now:** 
> - ✅ Current API is stable and fully functional
> - ✅ All examples work as-is
> - ✅ Strategy Pattern components are already universal (see `strategies.md`)
> - 📚 See `devref/gaps/UNIVERSAL_ZONE_ANALYSIS.md` for universalization plan

## Обзор

Инструменты работы с торговыми зонами: поддержка/сопротивление, признаки зон, последовательности и кластеризация.

### New in Phase 3 (v0.X.X)

**Major extensions:**
- ✨ **Strategy Pattern** for extensible metrics (8 strategies implemented)
- ✨ **67 total metrics** (was: 12 base metrics)
- ✨ **Swing analysis:** 23 metrics via 3 strategies (ZigZag, FindPeaks, PivotPoints)
- ✨ **Shape analysis:** 3 metrics via StatisticalShapeStrategy
- ✨ **Divergence detection:** 4 metrics via ClassicDivergenceStrategy
- ✨ **Volatility assessment:** 10 metrics via CombinedVolatilityStrategy
- ✨ **Volume analysis:** 4 metrics via StandardVolumeStrategy
- ✨ **Time metrics:** 2 metrics (peak_time_ratio, trough_time_ratio)

**Documentation:**
- **Strategy Pattern:** See [strategies.md](strategies.md) (🟢 stable API - won't change)
- **All 8 strategies:** See [strategies.md](strategies.md) (🟢 stable API)
- **ZoneFeatures fields:** See below (🟡 may change - field names will be renamed)

## Классы и функции

- Базовые сущности:
  - `Zone`: модель зоны (id, type, times, prices, strength, confidence, metadata)
  - `ZoneAnalyzer`:
    - `identify_support_resistance(data, window=20, min_touches=2) -> List[Zone]`
    - `analyze_zone_breaks(data, zones) -> Dict`
    - `analyze(data, window=20, min_touches=2) -> AnalysisResult`
  - Утилита: `find_support_resistance(data, window=20, min_touches=2) -> List[Zone]`

- Признаки зон (`zone_features`):
  - `ZoneFeatures` — dataclass характеристик
  - `ZoneFeaturesAnalyzer`:
    - `extract_zone_features(zone_info) -> ZoneFeatures`
    - `analyze_zones_distribution(zones_features) -> AnalysisResult`
    - `get_zone_features_summary(zones_features) -> Dict`
  - Утилиты:
    - `analyze_zones_distribution(zones_features, ...) -> Dict`
    - `extract_zone_features(zone_info, ...) -> Dict`

- Последовательности (`sequence_analysis`):
  - `TransitionAnalysis`, `ClusterAnalysis`
  - `ZoneSequenceAnalyzer`:
    - `analyze_zone_transitions(zones_features) -> AnalysisResult`
    - `cluster_zones(zones_features, n_clusters=3, features_to_use=None) -> AnalysisResult`
  - Утилиты:
    - `create_zone_sequence_analysis(zones_features, min_sequence_length=3) -> Dict`
    - `cluster_zone_shapes(zones_features, n_clusters=3) -> Dict`

## Примеры

Поддержка/сопротивление:
```python
from bquant.analysis.zones import find_support_resistance

zones = find_support_resistance(data, window=20, min_touches=2)
print(len(zones))
```

Извлечение признаков:
```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

zfa = ZoneFeaturesAnalyzer()
zone_features = zfa.extract_zone_features({'type':'bull', 'data': zone_df})
print(zone_features.to_dict())
```

Анализ последовательностей:
```python
from bquant.analysis.zones import ZoneSequenceAnalyzer

zsa = ZoneSequenceAnalyzer(min_sequence_length=3)
res = zsa.analyze_zone_transitions(zones_features)
print(res.results['transition_probabilities'])
```

## См. также

- [База анализа](base.md)
- [Статистический анализ](statistical.md)
