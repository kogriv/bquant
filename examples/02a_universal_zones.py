#!/usr/bin/env python3
"""
BQuant - Universal Zone Analysis: One API for All Indicators

Демонстрирует мощь универсальной архитектуры анализа зон.

КЛЮЧЕВАЯ ИДЕЯ: Один и тот же API работает для ВСЕХ индикаторов!
- MACD, RSI, AO, Stochastic, любой кастомный индикатор
- Разные стратегии детекции (zero_crossing, threshold, line_crossing, preloaded, combined)
- Полный набор анализа (features, statistics, clustering, sequences)

Разделы:
1. MACD zones (zero-crossing strategy)
2. RSI zones (threshold strategy)
3. AO zones (zero-crossing strategy)
4. MA crossover zones (line-crossing strategy)
5. Stochastic zones (2-line crossing) - v2.1
6. Custom indicator (proves universality!) - v2.1
7. Preloaded zones (external data)
8. Кэширование и персистентное хранение
9. Модульное использование

Требования:
- BQuant: pip install -e .
"""

import sys
import os
import pandas as pd
import numpy as np
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.presets import (
    analyze_macd_zones,
    analyze_rsi_zones,
    analyze_ao_zones
)
from bquant.data.samples import get_sample_data

"""
=============================================================================
v2.1 UNIVERSALITY DEMONSTRATION
=============================================================================

This example demonstrates the TRUE UNIVERSALITY of BQuant v2.1 architecture.

KEY CONCEPT: indicator_context - zones self-describe their detection!
=============================================================================

Every zone "knows" which indicator and strategy detected it:

    zone.indicator_context = {
        'detection_indicator': 'RSI_14',        # Which indicator
        'detection_strategy': 'threshold',       # Which strategy
        'signal_line': 'STOCH_D' or None,       # Secondary indicator (if 2-line)
        'detection_rules': {...}                 # Full rules for reference
    }

This enables:
1. Analytical strategies to work with correct indicator
2. Multi-indicator analysis without conflicts
3. Complete independence between analyses
4. Self-documenting zones

PROVEN UNIVERSALITY:
- Works with FICTIONAL_INDICATOR_99 (indicator that doesn't exist!)
- Works with 10+ REAL indicators (MACD, RSI, AO, CCI, Stochastic, Williams, MFI, CMF, ROC, custom)
- 115 tests - 100% pass rate
- NO code changes needed for new indicators

See: devref/gaps/zo/zouni_v2.md for architecture details
=============================================================================
"""


def prepare_sample_data() -> pd.DataFrame:
    """
    Загрузка встроенных sample данных BQuant с подготовкой для zone analysis.
    
    Uses built-in BQuant sample data instead of generating synthetic data.
    This ensures consistency with other examples and tests.
    """
    # Load built-in sample data
    df = get_sample_data()
    
    # v2.1: Prepare abs_price_return for volatility hypothesis tests
    df['price_return'] = df['close'].pct_change()
    df['abs_price_return'] = df['price_return'].abs()
    
    return df


def print_section(title: str):
    """Красивый заголовок раздела."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_zone_stats(result, indicator_name: str):
    """Вывод статистики по зонам."""
    print(f"[OK] {indicator_name} - Анализ завершен:")
    print(f"   Зон: {len(result.zones)}")
    
    if len(result.zones) > 0:
        types = {}
        for z in result.zones:
            types[z.type] = types.get(z.type, 0) + 1
        
        for zone_type, count in types.items():
            print(f"   - {zone_type}: {count}")
        
        avg_duration = sum(z.duration for z in result.zones) / len(result.zones)
        print(f"   Средняя длительность: {avg_duration:.1f} баров")


def main():
    print_section("Universal Zone Analysis - One API for All Indicators")
    
    # Load built-in sample data
    print("[DATA] Loading BQuant sample data...")
    df = prepare_sample_data()
    print(f"[OK] Loaded {len(df)} bars")
    print(f"   Period: {df.index[0]} - {df.index[-1]}")
    print(f"   Columns: {len(df.columns)}\n")
    
    # ========================================================================
    # 1. MACD ZONES
    # ========================================================================
    print_section("1. MACD Zones - Zero Crossing Strategy")
    
    print("Через fluent API:")
    result_macd = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1: NEW API!
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    print_zone_stats(result_macd, "MACD")
    
    # [v2.1] Inspect indicator_context (self-describing zones)
    if len(result_macd.zones) > 0:
        ctx = result_macd.zones[0].indicator_context
        print(f"\n   [INFO] Zone Detection Context:")
        print(f"      Indicator used: {ctx['detection_indicator']}")     # -> 'macd_hist'
        print(f"      Strategy used: {ctx['detection_strategy']}")       # -> 'zero_crossing'
        print(f"      Signal line: {ctx.get('signal_line', 'N/A')}")    # -> None
        
        # [v2.1] Show extracted features
        features = result_macd.zones[0].features
        print(f"\n   [INFO] Extracted Features (v2.1):")
        print(f"      Shape: skewness={features.get('skewness', 'N/A')}")
        print(f"      Shape: kurtosis={features.get('kurtosis', 'N/A')}")
        print(f"      Swing: num_peaks={features.get('num_peaks', 'N/A')}")
        print(f"      Swing: num_troughs={features.get('num_troughs', 'N/A')}")
        print(f"      Volume: volume_indicator_corr={features.get('volume_indicator_corr', 'N/A')}")
    
    print("\nЧерез preset (короче):")
    result_macd_preset = analyze_macd_zones(df, fast=12, slow=26, signal=9)
    print(f"   Зон через preset: {len(result_macd_preset.zones)}")
    
    # ========================================================================
    # 2. RSI ZONES
    # ========================================================================
    print_section("2. RSI Zones - Threshold Strategy")
    
    print("Определение зон перекупленности/перепроданности:")
    result_rsi = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'rsi', length=14)
        .detect_zones('threshold',
                     indicator_col='RSI_14',
                     upper_threshold=70,
                     lower_threshold=30)
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1: NEW API!
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_rsi, "RSI")
    
    # [v2.1] Threshold strategy also uses indicator_context
    if len(result_rsi.zones) > 0:
        ctx = result_rsi.zones[0].indicator_context
        print(f"\n   [INFO] Zone Detection Context:")
        print(f"      Indicator used: {ctx['detection_indicator']}")     # -> 'RSI_14'
        print(f"      Strategy used: {ctx['detection_strategy']}")       # -> 'threshold'
        print(f"      Thresholds: upper={ctx['detection_rules']['upper_threshold']}, lower={ctx['detection_rules']['lower_threshold']}")
        
        # [v2.1] Show features for RSI zones too
        features = result_rsi.zones[0].features
        print(f"\n   [INFO] Features work for ANY indicator:")
        print(f"      Shape: skewness={features.get('skewness', 'N/A')}")
        print(f"      Swing: num_peaks={features.get('num_peaks', 'N/A')}")
    
    print("\nЧерез preset:")
    result_rsi_preset = analyze_rsi_zones(df, period=14, upper_threshold=70, lower_threshold=30)
    print(f"   Зон через preset: {len(result_rsi_preset.zones)}")
    
    # ========================================================================
    # 3. AWESOME OSCILLATOR ZONES
    # ========================================================================
    print_section("3. Awesome Oscillator Zones - Zero Crossing Strategy")
    
    print("Та же стратегия, что и MACD, но другой индикатор:")
    result_ao = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
        .detect_zones('zero_crossing', indicator_col='AO_5_34')
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1: NEW API!
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_ao, "AO")
    
    # [v2.1] Same zero_crossing strategy, different indicator!
    if len(result_ao.zones) > 0:
        ctx = result_ao.zones[0].indicator_context
        print(f"\n   [INFO] Zone Detection Context:")
        print(f"      Indicator used: {ctx['detection_indicator']}")     # -> 'AO_5_34'
        print(f"      Strategy used: {ctx['detection_strategy']}")       # -> 'zero_crossing'
        print(f"      (Same strategy as MACD, different indicator!)")
    
    print("\nЧерез preset:")
    result_ao_preset = analyze_ao_zones(df, fast=5, slow=34)
    print(f"   Зон через preset: {len(result_ao_preset.zones)}")
    
    # ========================================================================
    # 4. MA CROSSOVER ZONES
    # ========================================================================
    print_section("4. Moving Average Crossover - Line Crossing Strategy")
    
    print("Зоны на основе пересечения двух скользящих средних:")
    
    # Сначала рассчитаем MA (или они уже в данных)
    df_with_ma = df.copy()
    df_with_ma['sma_fast'] = df['close'].rolling(10).mean()
    df_with_ma['sma_slow'] = df['close'].rolling(30).mean()
    
    result_ma = (
        analyze_zones(df_with_ma)
        .detect_zones('line_crossing',
                     line1_col='sma_fast',
                     line2_col='sma_slow')
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_ma, "MA Crossover")
    
    # [v2.1] Line crossing with 2 lines tracked!
    if len(result_ma.zones) > 0:
        ctx = result_ma.zones[0].indicator_context
        print(f"\n   [INFO] 2-Line Detection Context:")
        print(f"      Primary line: {ctx['detection_indicator']}")    # -> 'sma_fast'
        print(f"      Signal line: {ctx['signal_line']}")             # -> 'sma_slow'
        print(f"      Strategy: {ctx['detection_strategy']}")         # -> 'line_crossing'
    
    # ========================================================================
    # 5. STOCHASTIC ZONES - v2.1 2-line Support
    # ========================================================================
    print_section("5. Stochastic %K/%D - Line Crossing (v2.1)")
    
    print("Зоны на основе пересечения линий Stochastic:")
    
    # Calculate Stochastic
    df_stoch = df.copy()
    low_14 = df_stoch['low'].rolling(14).min()
    high_14 = df_stoch['high'].rolling(14).max()
    df_stoch['STOCH_K'] = 100 * (df_stoch['close'] - low_14) / (high_14 - low_14)
    df_stoch['STOCH_D'] = df_stoch['STOCH_K'].rolling(3).mean()
    
    result_stoch = (
        analyze_zones(df_stoch)
        .detect_zones('line_crossing',
                     line1_col='STOCH_K',      # Primary line
                     line2_col='STOCH_D')      # Signal line
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1: NEW API!
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_stoch, "Stochastic K/D")
    
    # [v2.1] 2-line indicators fully supported!
    if len(result_stoch.zones) > 0:
        ctx = result_stoch.zones[0].indicator_context
        print(f"\n   [INFO] 2-Line Oscillator Context:")
        print(f"      Primary line: {ctx['detection_indicator']}")   # -> 'STOCH_K'
        print(f"      Signal line: {ctx['signal_line']}")            # -> 'STOCH_D'
        print(f"      Strategy: {ctx['detection_strategy']}")        # -> 'line_crossing'
        print(f"      (Zones detected when %K crosses %D)")
    
    # ========================================================================
    # 6. CUSTOM INDICATOR - Proves TRUE UNIVERSALITY!
    # ========================================================================
    print_section("6. Custom Indicator - Zero Code Changes Needed!")
    
    print("Creating a custom momentum indicator (any calculation!):")
    
    # Create your own indicator (any calculation!)
    df_custom = df.copy()
    df_custom['MY_MOMENTUM'] = df_custom['close'].diff(5) / df_custom['close'].rolling(20).std()
    
    result_custom = (
        analyze_zones(df_custom)
        .detect_zones('zero_crossing', indicator_col='MY_MOMENTUM')
        .with_strategies(swing='find_peaks', shape='statistical')  # v2.1: Works with custom too!
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_custom, "Custom Momentum")
    
    # [v2.1] Works immediately - NO code changes!
    if len(result_custom.zones) > 0:
        ctx = result_custom.zones[0].indicator_context
        print(f"\n   [INFO] Custom Indicator Context:")
        print(f"      Indicator used: {ctx['detection_indicator']}")   # -> 'MY_MOMENTUM'
        print(f"      Strategy used: {ctx['detection_strategy']}")     # -> 'zero_crossing'
        print(f"\n   [*] NO hardcoded 'MY_MOMENTUM' anywhere in BQuant source!")
        print(f"   [*] TRUE UNIVERSALITY - works with ANY indicator!")
        
        # [v2.1] Features + strategies work for custom indicators too!
        features = result_custom.zones[0].features
        print(f"\n   [INFO] Features + Strategies = Universal:")
        print(f"      Shape: skewness={features.get('skewness', 'N/A')}")
        print(f"      Swing: num_peaks={features.get('num_peaks', 'N/A')}")
        print(f"      (All strategies work with your custom indicator!)")
    
    # ========================================================================
    # 7. PRELOADED ZONES
    # ========================================================================
    print_section("7. Preloaded Zones - External Data")
    
    print("Анализ зон из внешнего источника (CSV, Excel, database):")
    
    # Создадим пример зон
    zones_external = pd.DataFrame({
        'zone_id': [0, 1, 2],
        'start_time': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 10:00:00',
            '2024-01-02 00:00:00'
        ]),
        'end_time': pd.to_datetime([
            '2024-01-01 09:00:00',
            '2024-01-01 23:00:00',
            '2024-01-02 12:00:00'
        ]),
        'type': ['bull', 'bear', 'bull']
    })
    
    # Сохраним во временный CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        zones_external.to_csv(f.name, index=False)
        csv_path = f.name
    
    result_preloaded = (
        analyze_zones(df)
        .detect_zones('preloaded', zones_data=csv_path)
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_preloaded, "Preloaded")
    
    os.remove(csv_path)  # Cleanup
    
    # ========================================================================
    # 8. КЭШИРОВАНИЕ И ПЕРСИСТЕНТНОЕ ХРАНЕНИЕ
    # ========================================================================
    print_section("8. Кэширование и персистентное хранение")
    
    print("Автоматическое кэширование результатов:")
    print("-" * 40)
    
    # Первый вызов - кэш пропуск
    print("Первый запуск (cache miss)...")
    result_cached_1 = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_cache(enable=True, ttl=3600)
        .build()
    )
    print(f"   Зон: {len(result_cached_1.zones)}")
    
    # Второй вызов - кэш hit (те же данные и параметры)
    print("\nВторой запуск (cache hit)...")
    result_cached_2 = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_cache(enable=True, ttl=3600)
        .build()
    )
    print(f"   Зон: {len(result_cached_2.zones)} (загружено из кэша)")
    
    print("\nСохранение результатов:")
    print("-" * 40)
    
    # Pickle (быстро, все данные)
    result_macd.save('results/macd_zones.pkl', format='pickle')
    print("   [SAVE] Pickle: results/macd_zones.pkl")
    
    # JSON (читаемо, без DataFrame)
    result_macd.save('results/macd_zones.json', format='json', include_data=False)
    print("   [SAVE] JSON: results/macd_zones.json")
    
    # Parquet (компактно, все данные)
    result_macd.save('results/macd_zones.parquet', format='parquet', compress=True)
    print("   [SAVE] Parquet: results/macd_zones.parquet/")
    
    print("\nЗагрузка результатов:")
    print("-" * 40)
    
    from bquant.analysis.zones.models import ZoneAnalysisResult
    
    loaded = ZoneAnalysisResult.load('results/macd_zones.pkl')
    print(f"   [OK] Загружено из pickle: {len(loaded.zones)} зон")
    
    # ========================================================================
    # 8.1. CLUSTERING DEMONSTRATION
    # ========================================================================
    print_section("8.1. Clustering Analysis (v2.1)")
    
    print("Демонстрация кластеризации зон (MACD):")
    print("-" * 40)
    
    if hasattr(result_macd, 'clustering') and result_macd.clustering:
        print(f"   Clusters found: {len(set(result_macd.clustering.values()))}")
        
        # Count zones per cluster
        from collections import Counter
        cluster_counts = Counter(result_macd.clustering.values())
        for cluster_id, count in sorted(cluster_counts.items()):
            print(f"   - Cluster {cluster_id}: {count} zones")
        
        print("\n   [INFO] Clustering groups similar zones together")
        print("   Use for: Pattern recognition, regime detection")
    else:
        print("   [INFO] Clustering enabled with .analyze(clustering=True, n_clusters=3)")
    
    # ========================================================================
    # 8.2. STATISTICAL HYPOTHESIS TESTS
    # ========================================================================
    print_section("8.2. Statistical Hypothesis Tests (v2.1)")
    
    print("Статистические тесты для зон (MACD):")
    print("-" * 40)
    
    if hasattr(result_macd, 'hypothesis_tests') and result_macd.hypothesis_tests:
        tests = result_macd.hypothesis_tests
        print(f"   Tests based on {tests.data_size} zones")
        print("\n   Key tests (p < 0.05 = significant):")
        
        for test_name, test_result in tests.results.items():
            p_value = test_result.get('p_value', 'N/A')
            significant = test_result.get('significant', False)
            status = "[SIGNIFICANT]" if significant else "[not significant]"
            print(f"   - {test_name}: p={p_value:.4f if isinstance(p_value, float) else p_value} {status}")
        
        print("\n   [INFO] Hypothesis tests validate zone patterns")
        print("   Use for: Strategy validation, pattern confirmation")
    else:
        print("   [INFO] Hypothesis tests run automatically with .analyze()")
    
    # ========================================================================
    # 9. МОДУЛЬНОЕ ИСПОЛЬЗОВАНИЕ
    # ========================================================================
    print_section("9. Модульное использование")
    
    print("Пример 1: Только детекция (без анализа):")
    print("-" * 40)
    
    from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
    from bquant.indicators import IndicatorFactory
    
    # Рассчитать RSI
    rsi_ind = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
    rsi_data = rsi_ind.calculate(df)
    
    df_with_rsi = df.copy()
    for col in rsi_data.data.columns:
        df_with_rsi[col] = rsi_data.data[col]
    
    # Детектировать зоны
    detector = ZoneDetectionRegistry.get('threshold')
    config = ZoneDetectionConfig(
        min_duration=2,
        rules={'indicator_col': 'RSI_14', 'upper_threshold': 70, 'lower_threshold': 30},
        strategy_name='threshold'
    )
    zones_only = detector.detect_zones(df_with_rsi, config)
    
    print(f"   Обнаружено {len(zones_only)} RSI зон (только детекция, без анализа)")
    
    print("\nПример 2: Только анализ готовых зон:")
    print("-" * 40)
    
    from bquant.analysis.zones import UniversalZoneAnalyzer
    
    analyzer = UniversalZoneAnalyzer()
    result_only_analysis = analyzer.analyze_zones(
        zones_only,
        df_with_rsi,
        perform_clustering=False
    )
    
    print(f"   Проанализировано {len(result_only_analysis.zones)} зон")
    print(f"   Статистика: {list(result_only_analysis.statistics.keys())[:3]}...")
    
    # ========================================================================
    # ИТОГИ
    # ========================================================================
    print_section("Итоги")
    
    print("[TARGET] Универсальная архитектура = ZERO дублирования кода:")
    print("-" * 40)
    print(f"{'Индикатор':<20} {'Зон обнаружено':<20} {'Строк кода':<20}")
    print("-" * 60)
    print(f"{'MACD':<20} {len(result_macd.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'RSI':<20} {len(result_rsi.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'AO':<20} {len(result_ao.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'MA Crossover':<20} {len(result_ma.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'Stochastic K/D':<20} {len(result_stoch.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'Custom Momentum':<20} {len(result_custom.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'Preloaded':<20} {len(result_preloaded.zones):<20} {'5-10 (builder)':<20}")
    
    print("\n[OK] Universal approach advantages:")
    print("   1. Same code for all indicators")
    print("   2. New indicators - 0 lines of new code!")
    print("   3. Consistent results structure")
    print("   4. Easy to compare different indicators")
    print("   5. Modularity - use only needed parts")
    
    print("\n[DOCS] Next steps:")
    print("   - Experiment with indicator parameters")
    print("   - Try different detection strategies")
    print("   - Create your custom strategies")
    print("   - See docs/developer_guide/zone_detection_strategies.md")
    
    print("\n[LINKS] References:")
    print("   - Documentation: docs/api/analysis/zones.md")
    print("   - Modular usage: devref/gaps/zo/zomodul.md")
    print("   - Architecture: devref/gaps/zo/zonan.md")


if __name__ == "__main__":
    main()

