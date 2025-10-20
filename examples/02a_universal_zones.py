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
5. Preloaded zones (external data)
6. Кэширование и персистентное хранение
7. Модульное использование

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


def create_sample_data(rows: int = 300) -> pd.DataFrame:
    """Создание образцов данных с трендами и осцилляциями."""
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1H')
    np.random.seed(42)
    
    base = 100.0
    prices = [base]
    
    for i in range(1, rows):
        # Циклический тренд + шум
        trend = 15 * np.sin(i / 40)
        noise = np.random.normal(0, 0.5)
        new_price = prices[-1] + trend/10 + noise
        prices.append(max(new_price, 50))  # Минимум 50
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.995 for p in prices],
        'close': prices,
        'volume': np.random.uniform(1000, 5000, rows)
    }, index=dates)


def print_section(title: str):
    """Красивый заголовок раздела."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_zone_stats(result, indicator_name: str):
    """Вывод статистики по зонам."""
    print(f"✅ {indicator_name} - Анализ завершен:")
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
    
    # Генерация данных
    print("📊 Генерация данных...")
    df = create_sample_data(rows=300)
    print(f"✅ Создано {len(df)} баров\n")
    
    # ========================================================================
    # 1. MACD ZONES
    # ========================================================================
    print_section("1. MACD Zones - Zero Crossing Strategy")
    
    print("Через fluent API:")
    result_macd = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    print_zone_stats(result_macd, "MACD")
    
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
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_rsi, "RSI")
    
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
        .analyze(clustering=False)
        .build()
    )
    print_zone_stats(result_ao, "AO")
    
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
    
    # ========================================================================
    # 5. PRELOADED ZONES
    # ========================================================================
    print_section("5. Preloaded Zones - External Data")
    
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
    # 6. КЭШИРОВАНИЕ И ПЕРСИСТЕНТНОЕ ХРАНЕНИЕ
    # ========================================================================
    print_section("6. Кэширование и персистентное хранение")
    
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
    print("   💾 Pickle: results/macd_zones.pkl")
    
    # JSON (читаемо, без DataFrame)
    result_macd.save('results/macd_zones.json', format='json', include_data=False)
    print("   💾 JSON: results/macd_zones.json")
    
    # Parquet (компактно, все данные)
    result_macd.save('results/macd_zones.parquet', format='parquet', compress=True)
    print("   💾 Parquet: results/macd_zones.parquet/")
    
    print("\nЗагрузка результатов:")
    print("-" * 40)
    
    from bquant.analysis.zones.models import ZoneAnalysisResult
    
    loaded = ZoneAnalysisResult.load('results/macd_zones.pkl')
    print(f"   ✅ Загружено из pickle: {len(loaded.zones)} зон")
    
    # ========================================================================
    # 7. МОДУЛЬНОЕ ИСПОЛЬЗОВАНИЕ
    # ========================================================================
    print_section("7. Модульное использование")
    
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
    
    print("🎯 Универсальная архитектура = ZERO дублирования кода:")
    print("-" * 40)
    print(f"{'Индикатор':<20} {'Зон обнаружено':<20} {'Строк кода':<20}")
    print("-" * 60)
    print(f"{'MACD':<20} {len(result_macd.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'RSI':<20} {len(result_rsi.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'AO':<20} {len(result_ao.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'MA Crossover':<20} {len(result_ma.zones):<20} {'5-10 (builder)':<20}")
    print(f"{'Preloaded':<20} {len(result_preloaded.zones):<20} {'5-10 (builder)':<20}")
    
    print("\n✅ Преимущества универсального подхода:")
    print("   1. Один и тот же код для всех индикаторов")
    print("   2. Новые индикаторы - 0 строк нового кода!")
    print("   3. Консистентная структура результатов")
    print("   4. Легко сравнивать разные индикаторы")
    print("   5. Модульность - используйте только нужные части")
    
    print("\n📚 Следующие шаги:")
    print("   - Экспериментируйте с параметрами индикаторов")
    print("   - Пробуйте разные стратегии детекции")
    print("   - Создавайте свои кастомные стратегии")
    print("   - См. docs/developer_guide/zone_detection_strategies.md")
    
    print("\n🔗 Ссылки:")
    print("   - Документация: docs/api/analysis/zones.md")
    print("   - Модульное использование: devref/gaps/zo/zomodul.md")
    print("   - Архитектура: devref/gaps/zo/zonan.md")


if __name__ == "__main__":
    main()

