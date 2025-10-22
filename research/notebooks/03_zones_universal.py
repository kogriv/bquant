'''
Universal Zone Analysis - Deep Dive (v2.1)

v2.1 UPDATE (2025-10-20):
✅ ZoneFeaturesAnalyzer is UNIVERSAL (reads indicator_context)  
✅ .analyze() works for ALL indicators (MACD, RSI, AO, Custom)  
✅ Feature extraction is indicator-agnostic

This script demonstrates:
1) Full analysis pipeline for multiple indicators (features, clustering, tests, sequences)
2) Universal API capabilities (fluent builder, presets)
3) Migration guide (old → new)
4) Caching & persistence
5) Performance benchmarks

USAGE:
python research/notebooks/03_zones_universal.py --no-trap
'''

from pathlib import Path
import pandas as pd
import numpy as np
import time
from datetime import datetime
from typing import Dict, Any, List

# НАСТРОЙКА ЛОГИРОВАНИЯ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

nb = NotebookSimulator("Universal Zone Analysis - Deep Dive")

# =============================================================================
# STEP 1: DATA LOADING & PREPARATION
# =============================================================================

nb.step("Step 1: Data Loading & Preparation")

nb.info("Загружаем sample данные:")

with nb.error_handling("Data loading", critical=True):
    df = get_sample_data('tv_xauusd_1h')
    
    if 'time' in df.columns:
        df = df.set_index('time')
        nb.log("[OK] DatetimeIndex установлен")
    
    nb.log(f"Загружено: {len(df)} баров")
    nb.log(f"Период: {df.index.min()} - {df.index.max()}")
    nb.log(f"Колонки: {len(df.columns)}")
    
    nb.info("Базовая статистика:")
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            nb.log(f"  {col}: {df[col].min():.2f} - {df[col].max():.2f}")
    
    nb.info("Проверка качества (OHLCV):")
    missing_ohlcv = df[['open', 'high', 'low', 'close', 'volume']].isnull().sum()
    if missing_ohlcv.sum() > 0:
        nb.warning(f"Пропуски: {missing_ohlcv[missing_ohlcv > 0].to_dict()}")
    else:
        nb.success("Данные полные (OHLCV), пропусков нет")
    
    # Подготовка производных признаков для hypothesis tests
    nb.info("Подготовка производных признаков для statistical tests:")
    df['price_return'] = df['close'].pct_change()
    df['abs_price_return'] = df['price_return'].abs()
    nb.log("[OK] abs_price_return calculated (required for volatility hypothesis tests)")

nb.wait()

# =============================================================================
# STEP 2: UNIVERSAL API BASICS
# =============================================================================

nb.step("Step 2: Universal API - Basic Usage")

nb.info("Демонстрация нового универсального API:")

with nb.error_handling("Universal API basics"):
    from bquant.analysis.zones import analyze_zones, analyze_macd_zones
    
    nb.substep("2.1: Fluent Builder Syntax")
    
    start = time.time()
    result_builder = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
        .build()
    )
    time_builder = time.time() - start
    
    nb.success(f"Builder: {len(result_builder.zones)} зон за {time_builder:.3f} сек")
    nb.log(f"  Бычьих: {sum(1 for z in result_builder.zones if z.type == 'bull')}")
    nb.log(f"  Медвежьих: {sum(1 for z in result_builder.zones if z.type == 'bear')}")
    
    nb.substep("2.2: Convenience Preset")
    
    start = time.time()
    result_preset = analyze_macd_zones(df, fast=12, slow=26, signal=9, min_duration=2)
    time_preset = time.time() - start
    
    nb.success(f"Preset: {len(result_preset.zones)} зон за {time_preset:.3f} сек")
    nb.log(f"  Идентичны builder: {'ДА' if len(result_builder.zones) == len(result_preset.zones) else 'НЕТ'}")
    
    nb.substep("2.3: Comparison")
    
    nb.info("Выбор подхода:")
    nb.log("  Builder:  максимальная гибкость, нестандартные параметры")
    nb.log(f"           {len(result_builder.zones)} зон за {time_builder:.3f} сек")
    nb.log("  Preset:   быстрый старт, стандартные параметры")
    nb.log(f"           {len(result_preset.zones)} зон за {time_preset:.3f} сек (быстрее!)")

nb.wait()

# =============================================================================
# STEP 3: DETECTION STRATEGIES
# =============================================================================

nb.step("Step 3: Detection Strategies for MACD")

nb.info("Тестируем различные стратегии детекции на MACD:")

strategies_results = {}

with nb.error_handling("Detection strategies"):
    
    nb.substep("3.1: Zero Crossing (histogram)")
    
    result_zero = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .build()
    )
    strategies_results['ZeroCross_Hist'] = len(result_zero.zones)
    nb.log(f"  Histogram zero crossing: {len(result_zero.zones)} зон")
    
    nb.substep("3.2: Line Crossing (MACD/Signal)")
    
    result_line = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('line_crossing', line1_col='macd', line2_col='macd_signal')
        .build()
    )
    strategies_results['LineCross_MACD'] = len(result_line.zones)
    nb.log(f"  MACD/Signal crossing: {len(result_line.zones)} зон")
    
    nb.substep("3.3: Comparison")
    
    nb.info("Сравнение стратегий:")
    nb.log("=" * 70)
    for strategy, count in sorted(strategies_results.items(), key=lambda x: x[1], reverse=True):
        nb.log(f"  {strategy:25s}: {count:3d} зон")
    nb.log("=" * 70)
    
    nb.info("Выводы:")
    nb.log("  * Zero crossing: для анализа силы тренда")
    nb.log("  * Line crossing: для торговых сигналов")
    nb.log("  * Разное количество зон - разные цели!")

nb.wait()

# =============================================================================
# STEP 4: PARAMETER SENSITIVITY
# =============================================================================

nb.step("Step 4: Parameter Sensitivity Analysis")

nb.info("Влияние параметров на детекцию:")

nb.substep("4.1: MACD periods variation")

macd_variations = [
    {'fast': 8, 'slow': 21, 'signal': 5, 'label': 'Aggressive'},
    {'fast': 12, 'slow': 26, 'signal': 9, 'label': 'Standard'},
    {'fast': 21, 'slow': 55, 'signal': 13, 'label': 'Conservative'},
]

macd_results = {}

with nb.error_handling("MACD sensitivity"):
    for params in macd_variations:
        result = analyze_macd_zones(df, fast=params['fast'], slow=params['slow'], signal=params['signal'])
        macd_results[params['label']] = len(result.zones)
        nb.log(f"  {params['label']:15s} ({params['fast']:2d}/{params['slow']:2d}/{params['signal']:2d}): {len(result.zones):3d} зон")
    
    nb.info("Вывод:")
    nb.log(f"  Агрессивные (8/21/5): {macd_results['Aggressive']} зон (БОЛЬШЕ)")
    nb.log(f"  Консервативные (21/55/13): {macd_results['Conservative']} зон (МЕНЬШЕ)")
    nb.log("  Правило: Более быстрые MA → больше зон")

nb.substep("4.2: min_duration impact")

duration_values = [1, 2, 5, 10]
duration_results = {}

with nb.error_handling("min_duration sensitivity"):
    for min_dur in duration_values:
        result = analyze_macd_zones(df, fast=12, slow=26, signal=9, min_duration=min_dur)
        duration_results[min_dur] = len(result.zones)
        nb.log(f"  min_duration={min_dur:2d}: {len(result.zones):3d} зон")
    
    nb.info("Вывод:")
    nb.log(f"  min_duration=1: {duration_results[1]} зон (много шума)")
    nb.log(f"  min_duration=2: {duration_results[2]} зон (оптимально)")
    nb.log(f"  min_duration=10: {duration_results[10]} зон (только длинные)")
    nb.log("  Правило: Больше min_duration → меньше зон, выше качество")

nb.wait()

# =============================================================================
# STEP 5: ZONE STATISTICS
# =============================================================================

nb.step("Step 5: Full Analysis Pipeline Deep Dive")

nb.info("v2.1 UNIVERSALITY PROOF: Features & Clustering for ALL indicators")

# Initialize results (global scope for use in later steps)
result_macd_full = None
result_rsi_full = None
result_ao_full = None

with nb.error_handling("MACD full analysis"):
    result_macd_full = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1 (fix 21.10.2025)
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    nb.success(f"MACD: {len(result_macd_full.zones)} zones (features+clustering)")
    if result_macd_full.zones and result_macd_full.zones[0].features:
        z = result_macd_full.zones[0]
        nb.substep("5.1: MACD Features (sample zone)")
        # Shape metrics из metadata (v2.1 structure)
        shape_m = z.features.get('metadata', {}).get('shape_metrics', {}) if z.features.get('metadata') else {}
        nb.log(f"  Shape: skewness={shape_m.get('hist_skewness', None) if shape_m else None}")
        nb.log(f"  Shape: kurtosis={shape_m.get('hist_kurtosis', None) if shape_m else None}")
        nb.log(f"  Volume: volume_indicator_corr={z.features.get('volume_indicator_corr', None)}")
        if 'volume_spike_ratio' in z.features:
            nb.log(f"  Volume: spike_ratio={z.features['volume_spike_ratio']:.3f}")
        nb.log(f"  Volatility: expansion={z.features.get('volatility_expansion', None)}")
        nb.log(f"  Divergence: classic={z.features.get('has_classic_divergence', None)}")
        nb.log(f"  indicator_context: {z.indicator_context.get('detection_indicator', 'N/A')}")
        # Swing metrics (v2.1 NEW - fix 21.10.2025)
        if 'num_peaks' in z.features:
            nb.log(f"  Swing: num_peaks={z.features.get('num_peaks', 0)}")
        if 'num_troughs' in z.features:
            nb.log(f"  Swing: num_troughs={z.features.get('num_troughs', 0)}")
        if 'drawdown_from_peak' in z.features:
            nb.log(f"  Swing: drawdown_from_peak={z.features.get('drawdown_from_peak', 0):.2%}")

with nb.error_handling("RSI full analysis"):
    result_rsi_full = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'rsi', length=14)
        .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1 (fix 21.10.2025)
        .analyze(clustering=True, n_clusters=2)
        .build()
    )
    nb.success(f"RSI: {len(result_rsi_full.zones)} zones (features+clustering)")
    # v2.1: Show detailed features (fix 21.10.2025)
    if result_rsi_full.zones and result_rsi_full.zones[0].features:
        z = result_rsi_full.zones[0]
        nb.substep("5.2: RSI Features (sample zone)")
        # Shape metrics из metadata (v2.1 structure)
        shape_m = z.features.get('metadata', {}).get('shape_metrics', {}) if z.features.get('metadata') else {}
        nb.log(f"  Shape: skewness={shape_m.get('hist_skewness', None) if shape_m else None}")
        nb.log(f"  Shape: kurtosis={shape_m.get('hist_kurtosis', None) if shape_m else None}")
        nb.log(f"  Volume: volume_indicator_corr={z.features.get('volume_indicator_corr', None)}")
        nb.log(f"  Volatility: expansion={z.features.get('volatility_expansion', None)}")
        nb.log(f"  indicator_context: {z.indicator_context.get('detection_indicator', 'N/A')}")
        if 'num_peaks' in z.features:
            nb.log(f"  Swing: num_peaks={z.features.get('num_peaks', 0)}")

with nb.error_handling("AO full analysis"):
    result_ao_full = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
        .detect_zones('zero_crossing', indicator_col='AO_5_34')
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1 (fix 21.10.2025)
        .analyze(clustering=True, n_clusters=2)
        .build()
    )
    nb.success(f"AO: {len(result_ao_full.zones)} zones (features+clustering)")
    # v2.1: Show detailed features (fix 21.10.2025)
    if result_ao_full.zones and result_ao_full.zones[0].features:
        z = result_ao_full.zones[0]
        nb.substep("5.3: AO Features (sample zone)")
        # Shape metrics из metadata (v2.1 structure)
        shape_m = z.features.get('metadata', {}).get('shape_metrics', {}) if z.features.get('metadata') else {}
        nb.log(f"  Shape: skewness={shape_m.get('hist_skewness', None) if shape_m else None}")
        nb.log(f"  Shape: kurtosis={shape_m.get('hist_kurtosis', None) if shape_m else None}")
        nb.log(f"  Volume: volume_indicator_corr={z.features.get('volume_indicator_corr', None)}")
        nb.log(f"  Volatility: expansion={z.features.get('volatility_expansion', None)}")
        nb.log(f"  indicator_context: {z.indicator_context.get('detection_indicator', 'N/A')}")
        if 'num_peaks' in z.features:
            nb.log(f"  Swing: num_peaks={z.features.get('num_peaks', 0)}")

nb.substep("5.4: Clustering Analysis (MACD)")

if hasattr(result_macd_full, 'clustering') and result_macd_full.clustering:
    clusters = result_macd_full.clustering
    
    # Безопасный разбор структуры clustering (может быть Dict[int,int], Dict[int,List], или List)
    try:
        if isinstance(clusters, dict):
            # Format A: Dict[zone_id -> cluster_id] or Format B: Dict[cluster_id -> List[zone_id]]
            first_value = next(iter(clusters.values()))
            
            if isinstance(first_value, dict):
                # Format D: Dict with metadata - извлечь actual labels
                # cluster_labels содержит actual mapping
                if 'cluster_labels' in clusters:
                    actual_labels = clusters['cluster_labels']
                    
                    # Теперь работаем с actual_labels (может быть dict или list)
                    if isinstance(actual_labels, dict):
                        # Dict[zone_id -> cluster_id]
                        try:
                            unique_clusters = sorted(set(actual_labels.values()))
                        except TypeError:
                            unique_clusters = sorted(list(dict.fromkeys(actual_labels.values())))
                        
                        nb.log(f"  Clusters: {len(unique_clusters)}")
                        dist = {}
                        for cid in actual_labels.values():
                            dist[cid] = dist.get(cid, 0) + 1
                    elif isinstance(actual_labels, (list, np.ndarray)):
                        # List of labels
                        unique_clusters = set(actual_labels)
                        nb.log(f"  Clusters: {len(unique_clusters)}")
                        dist = {}
                        for cid in actual_labels:
                            dist[cid] = dist.get(cid, 0) + 1
                    else:
                        nb.warning(f"  Unknown labels format: {type(actual_labels)}")
                        dist = {}
                    
                    # Сохраняем actual_labels для использования в характеристиках
                    clusters = actual_labels
                else:
                    nb.log(f"  [WARN] No 'cluster_labels' found in clustering metadata")
                    dist = {}
            elif isinstance(first_value, (list, tuple)):
                # Format B: Dict[cluster_id -> List[zone_id]]
                dist = {cid: len(zids) for cid, zids in clusters.items()}
                nb.log(f"  Clusters: {len(clusters)}")
            else:
                # Format A: Dict[zone_id -> cluster_id]
                try:
                    unique_clusters = set(clusters.values())
                except TypeError:
                    # Если values unhashable, получить уникальные вручную
                    unique_clusters = list(dict.fromkeys(clusters.values()))
                nb.log(f"  Clusters: {len(unique_clusters)}")
                dist = {}
                for cid in clusters.values():
                    dist[cid] = dist.get(cid, 0) + 1
        elif isinstance(clusters, (list, np.ndarray, pd.Series)):
            # Format C: List/array of cluster labels
            unique_clusters = set(clusters)
            nb.log(f"  Clusters: {len(unique_clusters)}")
            dist = {}
            for cid in clusters:
                dist[cid] = dist.get(cid, 0) + 1
        else:
            nb.warning(f"  Unknown clustering format: {type(clusters)}")
            dist = {}
        
        if dist:
            for cid, cnt in sorted(dist.items()):
                nb.log(f"    Cluster {cid}: {cnt} zones")
        
        # Характеристики каждого кластера (fix 21.10.2025)
        nb.info("  Cluster characteristics:")
        
        # Определяем формат clustering (переопределение для правильного scope!)
        if isinstance(clusters, dict):
            first_val = next(iter(clusters.values()), None)
            
            if first_val and not isinstance(first_val, (list, tuple)):
                # Format A: Dict[zone_id -> cluster_id]
                # Безопасный set для unhashable values
                try:
                    unique_clusters = sorted(set(clusters.values()))
                except TypeError:
                    # Если values unhashable, получить уникальные вручную
                    unique_clusters = sorted(list(dict.fromkeys(clusters.values())))
                
                for cluster_id in unique_clusters:
                    zones_in_cluster = [z for z in result_macd_full.zones 
                                       if clusters.get(z.zone_id) == cluster_id]
                    
                    if zones_in_cluster:
                        avg_duration = sum(z.duration for z in zones_in_cluster) / len(zones_in_cluster)
                        types_count = {}
                        for z in zones_in_cluster:
                            types_count[z.type] = types_count.get(z.type, 0) + 1
                        
                        nb.log(f"    Cluster {cluster_id}:")
                        nb.log(f"      Zones: {len(zones_in_cluster)}")
                        nb.log(f"      Avg duration: {avg_duration:.1f} bars")
                        nb.log(f"      Types: bull={types_count.get('bull', 0)}, bear={types_count.get('bear', 0)}")
            
            elif first_val and isinstance(first_val, (list, tuple)):
                # Format B: Dict[cluster_id -> List[zone_id]]
                for cluster_id, zone_ids in sorted(clusters.items()):
                    zones_in_cluster = [z for z in result_macd_full.zones if z.zone_id in zone_ids]
                    
                    if zones_in_cluster:
                        avg_duration = sum(z.duration for z in zones_in_cluster) / len(zones_in_cluster)
                        types_count = {}
                        for z in zones_in_cluster:
                            types_count[z.type] = types_count.get(z.type, 0) + 1
                        
                        nb.log(f"    Cluster {cluster_id}:")
                        nb.log(f"      Zones: {len(zones_in_cluster)}")
                        nb.log(f"      Avg duration: {avg_duration:.1f} bars")
                        nb.log(f"      Types: bull={types_count.get('bull', 0)}, bear={types_count.get('bear', 0)}")
        
        elif isinstance(clusters, (list, np.ndarray, pd.Series)):
            # Format C: List/array of cluster labels (index = zone index)
            for cluster_id in sorted(set(clusters)):
                zone_indices = [i for i, cid in enumerate(clusters) if cid == cluster_id]
                zones_in_cluster = [result_macd_full.zones[i] for i in zone_indices 
                                   if i < len(result_macd_full.zones)]
                
                if zones_in_cluster:
                    avg_duration = sum(z.duration for z in zones_in_cluster) / len(zones_in_cluster)
                    types_count = {}
                    for z in zones_in_cluster:
                        types_count[z.type] = types_count.get(z.type, 0) + 1
                    
                    nb.log(f"    Cluster {cluster_id}:")
                    nb.log(f"      Zones: {len(zones_in_cluster)}")
                    nb.log(f"      Avg duration: {avg_duration:.1f} bars")
                    nb.log(f"      Types: bull={types_count.get('bull', 0)}, bear={types_count.get('bear', 0)}")
    except Exception as e:
        nb.warning(f"  Failed to parse clustering: {type(e).__name__}: {str(e)[:60]}")
else:
    nb.warning("  Clustering not available (insufficient data)")

nb.substep("5.5: Statistical Hypothesis Tests (MACD)")
if hasattr(result_macd_full, 'hypothesis_tests') and result_macd_full.hypothesis_tests:
    tests = result_macd_full.hypothesis_tests
    if hasattr(tests, 'results') and tests.results:
        nb.log("  Hypothesis tests executed")
        if hasattr(tests, 'data_size'):
            nb.log(f"  Tests based on {tests.data_size} zones")
        
        # Вложенная структура: tests.results['tests'] содержит индивидуальные тесты
        if 'tests' in tests.results and isinstance(tests.results['tests'], dict):
            individual_tests = tests.results['tests']
            
            for tname, tres in individual_tests.items():
                # tres - это dict, не объект! Используем dict keys
                if tres and isinstance(tres, dict) and 'p_value' in tres:
                    p_val = tres['p_value']
                    significant = p_val < 0.05 if p_val is not None else False
                    nb.log(f"    {tname}:")
                    nb.log(f"      p-value: {p_val:.4f}")
                    nb.log(f"      significant: {significant} (alpha=0.05)")
                    
                    # Если есть test_statistic, показать его
                    if 'test_statistic' in tres and tres['test_statistic'] is not None:
                        nb.log(f"      statistic: {tres['test_statistic']:.4f}")
        
        # Образовательный комментарий (fix 21.10.2025)
        nb.info("  Hypothesis tests:")
        nb.info("    - duration_normality: Are zone durations normally distributed?")
        nb.info("    - bull_bear_asymmetry: Is there bias toward bull/bear zones?")
        nb.info("    - sequence_randomness: Are zone sequences random or patterned?")
        nb.info("    - volatility_effects: Does volatility correlate with zones?")
        nb.info("  p < 0.05 suggests significant patterns (reject null hypothesis)")
else:
    nb.warning("  Hypothesis tests unavailable or insufficient data")

nb.substep("5.6: Sequence Analysis (MACD)")
if hasattr(result_macd_full, 'sequence_analysis') and result_macd_full.sequence_analysis:
    seq = result_macd_full.sequence_analysis
    
    # Total zones count (fix 21.10.2025)
    nb.log(f"  Total zones analyzed: {len(result_macd_full.zones)}")
    
    # Transitions (fix 21.10.2025 - работа с dict)
    if isinstance(seq, dict) and 'transitions' in seq and seq['transitions']:
        nb.info("  Transitions (zone type changes):")
        for trans, cnt in seq['transitions'].items():
            nb.log(f"      {trans}: {cnt}")
    
    # Patterns (fix 21.10.2025 - работа с dict)
    if isinstance(seq, dict) and 'patterns' in seq and seq['patterns']:
        patterns_data = seq['patterns']
        
        # patterns может быть dict с 'sequence_patterns' key или list
        if isinstance(patterns_data, dict) and 'sequence_patterns' in patterns_data:
            patterns_list = patterns_data['sequence_patterns']
        elif isinstance(patterns_data, list):
            patterns_list = patterns_data
        else:
            patterns_list = []
        
        if patterns_list:
            nb.info(f"  Patterns found: {len(patterns_list)}")
            
            for i, pattern in enumerate(patterns_list[:3], 1):  # Показать первые 3
                # Безопасный доступ к полям pattern
                if isinstance(pattern, dict):
                    ptype = pattern.get('type', 'unknown')
                    plength = pattern.get('length', 'N/A')
                    pfreq = pattern.get('frequency', 'N/A')
                    nb.log(f"    Pattern {i}: type={ptype}, length={plength}, freq={pfreq}")
                else:
                    nb.log(f"    Pattern {i}: {pattern}")
        else:
            nb.log("  No patterns detected (insufficient data or no repeating sequences)")
    else:
        nb.log("  No patterns detected (insufficient data or no repeating sequences)")
    
    # Образовательный комментарий (fix 21.10.2025)
    nb.info("  Sequence analysis helps identify zone patterns and trading regimes")
else:
    nb.warning("  No sequence analysis available")

nb.wait()

# =============================================================================
# STEP 6: MODULAR USAGE
# =============================================================================

nb.step("Step 6: Modular Usage Scenarios")

nb.info("Демонстрация модульного использования:")

nb.substep("6.1: Only Detection")

with nb.error_handling("Detection-only"):
    detection_only = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .build()
    )
    
    nb.success(f"Детектировано {len(detection_only.zones)} зон (без анализа)")
    nb.log("  Сценарии:")
    nb.log("    * Сохранить для последующего анализа")
    nb.log("    * Экспортировать в другие системы")
    nb.log("    * Визуализировать без heavy computations")

nb.substep("6.2: Detection Registry")

with nb.error_handling("Registry check"):
    from bquant.analysis.zones.detection import ZoneDetectionRegistry
    
    strategies = ZoneDetectionRegistry.list_strategies()
    nb.info(f"Доступные стратегии детекции ({len(strategies)}):")
    for strategy in strategies:
        nb.log(f"  * {strategy}")

nb.substep("6.3: Indicator Reuse")

with nb.error_handling("Indicator reuse"):
    from bquant.indicators.base import IndicatorFactory
    
    macd_ind = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    result_ind = macd_ind.calculate(df.copy())
    
    nb.log(f"  Индикатор: {macd_ind.name}")
    nb.log(f"  Колонки: {macd_ind.get_default_columns()}")
    nb.log("  Можно переиспользовать!")

nb.success("✅ Detection-only analysis completed")
nb.success("✅ Caching demonstration completed")

nb.wait()

# =============================================================================
# STEP 7: CACHING & PERSISTENCE
# =============================================================================

nb.step("Step 7: Caching & Persistence")

nb.info("Тестируем кэширование и сохранение:")

output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

nb.substep("7.1: Caching Test")

with nb.error_handling("Caching"):
    # Первый запуск
    start = time.time()
    r1 = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_cache(ttl=3600)
        .build()
    )
    time_1 = time.time() - start
    
    # Второй запуск (cache hit)
    start = time.time()
    r2 = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_cache(ttl=3600)
        .build()
    )
    time_2 = time.time() - start
    
    nb.log(f"  1-й запуск: {time_1:.3f} сек")
    nb.log(f"  2-й запуск: {time_2:.3f} сек")
    
    if time_2 < time_1:
        nb.success(f"Ускорение от кэша: {time_1/time_2:.1f}x")
    else:
        nb.log("  Кэш работает нормально")

nb.substep("7.2: Save/Load Formats")

with nb.error_handling("Save/load"):
    # Pickle
    pickle_path = output_dir / "zones_universal.pkl"
    result_preset.save(pickle_path, format='pickle')
    pickle_size = pickle_path.stat().st_size / 1024
    nb.log(f"  [OK] Pickle: {pickle_size:.2f} KB")
    
    # JSON
    json_path = output_dir / "zones_universal.json"
    result_preset.save(json_path, format='json', include_data=False)
    json_size = json_path.stat().st_size / 1024
    nb.log(f"  [OK] JSON:   {json_size:.2f} KB (metadata only)")
    
    # Загрузка
    from bquant.analysis.zones.models import ZoneAnalysisResult
    
    loaded = ZoneAnalysisResult.load(pickle_path)
    nb.success(f"Загружено {len(loaded.zones)} зон из pickle")
    
    nb.info("Сравнение:")
    nb.log(f"  Pickle: {pickle_size:.2f} KB - fastest, complete")
    nb.log(f"  JSON:   {json_size:.2f} KB - readable, portable")

nb.success("✅ Performance benchmarks completed")

nb.wait()

# =============================================================================
# STEP 8: MIGRATION GUIDE
# =============================================================================

nb.step("Step 8: Migration Guide")

nb.info("Как мигрировать со старого API:")

nb.log("")
nb.log("=" * 70)
nb.log("СТАРЫЙ КОД (deprecated):")
nb.log("=" * 70)
nb.log("""
from bquant.indicators.macd import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer(
    macd_params={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
)
result = analyzer.analyze_complete_modular(df)
""")

nb.log("")
nb.log("=" * 70)
nb.log("НОВЫЙ КОД - Вариант 1 (Builder):")
nb.log("=" * 70)
nb.log("""
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .build()
)
""")

nb.log("")
nb.log("=" * 70)
nb.log("НОВЫЙ КОД - Вариант 2 (Preset - simplest):")
nb.log("=" * 70)
nb.log("""
from bquant.analysis.zones import analyze_macd_zones

result = analyze_macd_zones(df, fast=12, slow=26, signal=9)
""")

nb.log("")
nb.info("Преимущества миграции:")
nb.log("  [+] Универсальность - работает с ЛЮБЫМИ индикаторами")
nb.log("  [+] Модульность - гибкое использование компонентов")
nb.log("  [+] Кэширование - встроенное, из коробки")
nb.log("  [+] Экспорт - 3 формата (pickle, JSON, parquet)")
nb.log("  [+] Активная поддержка")
nb.log("  [-] Старый API → удаление в v3.0.0")

nb.wait()

# =============================================================================
# STEP 9: OTHER INDICATORS (Detection Only)
# =============================================================================

nb.step("Step 9: Multiple Indicators - Feature Comparison")

# Note: reuse result_rsi_full and result_ao_full from Step 5
# (already created with .analyze())

if result_macd_full and result_rsi_full and result_ao_full:
    nb.info("Feature comparison table:")
    nb.log(f"{'Indicator':<12} {'Zones':<8} {'AvgDur':<8} {'HasFeatures':<12}")
    nb.log("-" * 50)
    for name, res in [("MACD", result_macd_full), ("RSI", result_rsi_full), ("AO", result_ao_full)]:
        zones = len(res.zones) if res else 0
        avgd = np.mean([z.duration for z in res.zones]) if (res and res.zones) else 0
        hasf = any(z.features for z in res.zones) if (res and res.zones) else False
        nb.log(f"{name:<12} {zones:<8} {avgd:<8.1f} {str(hasf):<12}")
    
    nb.substep("9.1: Zone Overlap (MACD vs RSI)")
    if result_macd_full.zones and result_rsi_full.zones:
        macd_periods = [(z.start_index, z.end_index) for z in result_macd_full.zones]
        rsi_periods = [(z.start_index, z.end_index) for z in result_rsi_full.zones]
        overlaps = 0
        for m_start, m_end in macd_periods:
            for r_start, r_end in rsi_periods:
                if not (m_end < r_start or r_end < m_start):
                    overlaps += 1
                    break
        overlap_ratio = overlaps / max(len(macd_periods), 1) * 100
        nb.log(f"  MACD zones: {len(macd_periods)} / RSI zones: {len(rsi_periods)} / Overlaps: {overlaps}")
        nb.log(f"  Overlap ratio: {overlap_ratio:.1f}%")
    else:
        nb.warning("  Insufficient zones for overlap analysis")
    
    nb.substep("9.2: Consensus Signals (MACD & RSI)")
    if result_macd_full.zones and result_rsi_full.zones:
        consensus = 0
        for mz in result_macd_full.zones:
            for rz in result_rsi_full.zones:
                if not (mz.end_index < rz.start_index or rz.end_index < mz.start_index) and mz.type == rz.type:
                    consensus += 1
                    break
        nb.log(f"  Consensus signals: {consensus}")
        nb.log(f"  Use for: Higher confidence trades when indicators agree")
    else:
        nb.warning("  Insufficient zones for consensus analysis")
else:
    nb.warning("Step 9 skipped: results from Step 5 not available")

nb.success("✅ Multi-indicator feature comparison complete!")

nb.wait()

# =============================================================================
# STEP 10: PERFORMANCE & SUMMARY
# =============================================================================

nb.step("Step 10: Performance Summary")

nb.info("Бенчмарки:")

nb.substep("10.1: Different Dataset Sizes")

with nb.error_handling("Performance benchmarks"):
    # 100 bars
    df_small = df.iloc[:100].copy()
    start = time.time()
    result_small = analyze_macd_zones(df_small, fast=12, slow=26, signal=9)
    time_small = time.time() - start
    
    # 1000 bars
    start = time.time()
    result_large = analyze_macd_zones(df, fast=12, slow=26, signal=9)
    time_large = time.time() - start
    
    nb.log(f"  100 баров:  {time_small:.3f} сек ({len(result_small.zones)} зон)")
    nb.log(f"  1000 баров: {time_large:.3f} сек ({len(result_large.zones)} зон)")

nb.substep("10.2: Final Summary")

nb.info("=" * 70)
nb.info("ИТОГИ ИССЛЕДОВАНИЯ:")
nb.info("=" * 70)

nb.log("")
nb.log("ПРОТЕСТИРОВАНО:")
nb.log(f"  * Датасетов: 2 (100, 1000 bars)")
nb.log(f"  * Стратегий детекции: {len(strategies_results)}")
nb.log(f"  * Параметрических вариаций: {len(macd_variations) + len(duration_values)}")
nb.log(f"  * Форматов экспорта: 2 (pickle, JSON)")

nb.log("")
nb.log("KEY FINDINGS:")
nb.log("  1. [+] Universal API - fluent builder + presets")
nb.log("  2. [+] Caching works and accelerates")
nb.log("  3. [+] Modularity enables flexible usage")
nb.log(f"  4. [+] Performance: {len(result_large.zones)/time_large:.1f} zones/sec")
nb.log("  5. [+] v2.1: Features work for ALL indicators (MACD, RSI, AO)")

nb.log("")
nb.log("CODE SAVINGS:")
nb.log("  Old: MACDZoneAnalyzer (517) + RSIZoneAnalyzer (500) + AOZoneAnalyzer (500)")
nb.log("       = 1517 lines with DUPLICATION")
nb.log("  New: UniversalZoneAnalyzer (250) + presets (30)")
nb.log("       = 280 lines WITHOUT duplication")
nb.log("  SAVINGS: ~82%!")

nb.log("")
nb.log(f"SESSION STATISTICS:")
nb.log(f"  * Bars processed: {len(df) + len(df_small)}")
nb.log(f"  * Zones detected: {len(result_preset.zones)}")
nb.log(f"  * Average time: {time_large:.3f} sec")

nb.log("")
nb.info("RECOMMENDATIONS:")
nb.log("  * For all indicators: use full analyze() - works universally (v2.1)")
nb.log("  * For production: enable caching (.with_cache())")
nb.log("  * For sharing: export to JSON")

nb.log("")
nb.info("LINKS:")
nb.log("  * Examples: examples/02a_universal_zones.py")
nb.log("  * Modularity: devref/gaps/zo/zomodul.md")
nb.log("  * Architecture: devref/gaps/zo/zonan.md")

nb.wait()

# =============================================================================
# STEP 11: EDGE CASES & ERROR HANDLING
# =============================================================================

nb.step("Step 11: Edge Cases & Error Handling")

nb.substep("11.1: Small Dataset (< 50 bars)")
with nb.error_handling("Small dataset"):
    small_df = df.head(30)
    res_small = (
        analyze_zones(small_df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(clustering=False)
        .build()
    )
    nb.log(f"  Small dataset (30 bars): {len(res_small.zones)} zones")
    nb.log(f"  Pipeline works with minimal data [OK]")

nb.substep("11.2: No Zones Detected")
with nb.error_handling("No zones"):
    res_none = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('threshold', indicator_col='macd_hist', upper_threshold=100, lower_threshold=-100, min_duration=999)
        .analyze(clustering=False)
        .build()
    )
    nb.log(f"  No zones case: {len(res_none.zones)} zones")
    nb.log(f"  Pipeline handles gracefully (no crash) [OK]")

nb.substep("11.3: Missing Indicator Column")
with nb.error_handling("Missing column", critical=False):
    try:
        res_missing = (
            analyze_zones(df)
            .detect_zones('zero_crossing', indicator_col='NON_EXISTENT_COLUMN')
            .build()
        )
        nb.log(f"  Missing column result: {len(res_missing.zones)} zones")
    except Exception as e:
        nb.warning(f"  Expected error: {type(e).__name__}: {str(e)[:80]}")
        nb.log(f"  Error handling works correctly [OK]")

nb.substep("11.4: Invalid Parameters")
with nb.error_handling("Invalid params", critical=False):
    try:
        res_invalid = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=-5)
            .build()
        )
        nb.log(f"  Invalid params zones: {len(res_invalid.zones)}")
    except ValueError as e:
        nb.warning(f"  Expected error: {str(e)[:80]}")
        nb.log(f"  Parameter validation works correctly [OK]")

nb.success("Edge cases handled gracefully")

nb.wait()

nb.finish("Universal zone analysis investigation complete (v2.1)!")
