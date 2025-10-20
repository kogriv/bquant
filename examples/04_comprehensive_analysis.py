#!/usr/bin/env python3
"""
BQuant - Comprehensive Zone Analysis Pipeline

Полный пример использования универсальной архитектуры анализа зон:
1. Загрузка и подготовка данных
2. Расчет индикаторов через IndicatorFactory
3. Детекция зон с разными стратегиями
4. Полный анализ (features, statistics, clustering, sequences)
5. Визуализация результатов
6. Сохранение и загрузка результатов
7. Модульное использование компонентов

Требования:
- BQuant: pip install -e .
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.analysis.zones import (
    analyze_zones,
    UniversalZoneAnalyzer,
    ZoneDetectionRegistry,
    ZoneDetectionConfig
)
from bquant.analysis.zones.presets import analyze_macd_zones
from bquant.indicators import IndicatorFactory


def create_comprehensive_data(rows: int = 500) -> pd.DataFrame:
    """Создание данных с разными рыночными режимами."""
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1H')
    np.random.seed(123)
    
    base = 2000.0
    prices = [base]
    
    for i in range(1, rows):
        # Разные рыночные фазы
        if i < 150:  # Тренд вверх
            trend = 0.003
        elif i < 300:  # Коррекция
            trend = -0.002
        else:  # Боковик
            trend = 0.0005 * np.sin(i / 10)
        
        noise = np.random.normal(0, 0.001)
        new_price = prices[-1] * (1 + trend + noise)
        prices.append(max(new_price, 100))
    
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': np.random.uniform(100000, 500000, rows)
    }, index=dates)


def print_section(title: str):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def main():
    print_section("Comprehensive Zone Analysis Pipeline")
    
    # ========================================================================
    # 1. ПОДГОТОВКА ДАННЫХ
    # ========================================================================
    print_section("1. Подготовка данных")
    
    print("📊 Генерация данных с разными рыночными режимами...")
    df = create_comprehensive_data(rows=500)
    
    print(f"✅ Создано {len(df)} баров")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    print(f"   Диапазон цен: {df['close'].min():.2f} - {df['close'].max():.2f}")
    print(f"   Изменение: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
    
    # ========================================================================
    # 2. ПОЛНЫЙ PIPELINE С КЭШИРОВАНИЕМ
    # ========================================================================
    print_section("2. Полный pipeline: Indicator → Detection → Analysis")
    
    print("Выполнение полного pipeline с автоматическим кэшированием:")
    
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', 
                     indicator_col='macd_hist',
                     min_duration=3)
        .analyze(
            clustering=True,
            n_clusters=3,
            regression=False,  # Опционально
            validation=False   # Опционально
        )
        .with_cache(enable=True, ttl=3600)
        .build()
    )
    
    print(f"✅ Pipeline завершен:")
    print(f"   Зон обнаружено: {len(result.zones)}")
    print(f"   Bull зон: {sum(1 for z in result.zones if z.type == 'bull')}")
    print(f"   Bear зон: {sum(1 for z in result.zones if z.type == 'bear')}")
    print(f"   Кластеризация: {'Да' if result.clustering else 'Нет'}")
    print(f"   Timestamp: {result.metadata['analysis_timestamp']}")
    
    # ========================================================================
    # 3. ДЕТАЛЬНЫЙ АНАЛИЗ РЕЗУЛЬТАТОВ
    # ========================================================================
    print_section("3. Детальный анализ результатов")
    
    print("Статистика зон:")
    print("-" * 40)
    stats = result.statistics
    if 'total_statistics' in stats:
        total = stats['total_statistics']
        print(f"   Всего зон: {total.get('total_zones', 0)}")
        print(f"   Bull ratio: {total.get('bull_ratio', 0):.2%}")
        print(f"   Bear ratio: {total.get('bear_ratio', 0):.2%}")
    
    if 'duration_distribution' in stats:
        dur = stats['duration_distribution']['overall']
        print(f"\n   Длительность зон:")
        print(f"   - Среднее: {dur['mean']:.1f} баров")
        print(f"   - Медиана: {dur['median']:.1f} баров")
        print(f"   - Min/Max: {dur['min']:.0f}/{dur['max']:.0f} баров")
    
    print("\nАнализ последовательностей:")
    print("-" * 40)
    if result.sequence_analysis:
        seq = result.sequence_analysis
        if 'transitions' in seq:
            print(f"   Переходов: {seq['sequence_summary']['total_transitions']}")
            for trans_type, count in seq['transitions'].items():
                print(f"   - {trans_type}: {count}")
    
    print("\nКластеризация:")
    print("-" * 40)
    if result.clustering and 'clusters_analysis' in result.clustering:
        clusters = result.clustering['clusters_analysis']
        for cluster_id, cluster_info in clusters.items():
            print(f"   Кластер {cluster_info['cluster_id']}: "
                  f"{cluster_info['size']} зон, "
                  f"dominant type: {cluster_info.get('dominant_type', 'N/A')}")
    
    # ========================================================================
    # 4. СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
    # ========================================================================
    print_section("4. Сохранение результатов")
    
    print("Сохранение в разных форматах:")
    
    # Создаем директорию results если нет
    os.makedirs('results', exist_ok=True)
    
    # Pickle - полный результат
    result.save('results/comprehensive_analysis.pkl', format='pickle')
    print("   💾 Pickle (полный): results/comprehensive_analysis.pkl")
    
    # JSON - легкий формат без данных
    result.save('results/comprehensive_analysis.json', format='json', include_data=False)
    print("   💾 JSON (без данных): results/comprehensive_analysis.json")
    
    # Parquet - оптимальный формат
    result.save('results/comprehensive_analysis.parquet', format='parquet', compress=True)
    print("   💾 Parquet (сжатый): results/comprehensive_analysis.parquet/")
    
    # ========================================================================
    # 5. МОДУЛЬНОЕ ИСПОЛЬЗОВАНИЕ
    # ========================================================================
    print_section("5. Модульное использование компонентов")
    
    print("Сценарий: Использовать только детекцию зон")
    print("-" * 40)
    
    # Рассчитываем индикатор вручную
    macd_ind = IndicatorFactory.create('custom', 'macd', fast_period=10, slow_period=20, signal_period=5)
    macd_data = macd_ind.calculate(df)
    
    df_with_macd = df.copy()
    for col in macd_data.data.columns:
        df_with_macd[col] = macd_data.data[col]
    
    # Детектируем зоны
    detector = ZoneDetectionRegistry.get('zero_crossing')
    config = ZoneDetectionConfig(
        min_duration=5,
        rules={'indicator_col': 'macd_hist'},
        strategy_name='zero_crossing'
    )
    zones_only = detector.detect_zones(df_with_macd, config)
    
    print(f"   Обнаружено {len(zones_only)} зон (только детекция)")
    print(f"   Можно сохранить и использовать позже")
    
    # Теперь можем проанализировать эти зоны отдельно
    analyzer = UniversalZoneAnalyzer()
    zones_analysis = analyzer.analyze_zones(
        zones_only,
        df_with_macd,
        perform_clustering=False
    )
    
    print(f"   Анализ {len(zones_analysis.zones)} зон завершен")
    
    # ========================================================================
    # 6. СРАВНЕНИЕ РАЗНЫХ ИНДИКАТОРОВ
    # ========================================================================
    print_section("6. Сравнение разных индикаторов")
    
    print("Анализ одних и тех же данных разными индикаторами:")
    print("-" * 40)
    
    # MACD
    result_macd = analyze_macd_zones(df, fast=12, slow=26, signal=9, clustering=False)
    print(f"   MACD: {len(result_macd.zones)} зон")
    
    # RSI
    from bquant.analysis.zones.presets import analyze_rsi_zones
    result_rsi = analyze_rsi_zones(df, period=14, upper_threshold=70, lower_threshold=30, clustering=False)
    print(f"   RSI: {len(result_rsi.zones)} зон")
    
    # AO
    from bquant.analysis.zones.presets import analyze_ao_zones
    result_ao = analyze_ao_zones(df, fast=5, slow=34, clustering=False)
    print(f"   AO: {len(result_ao.zones)} зон")
    
    print("\n   💡 Разные индикаторы находят разные зоны!")
    print("   Используйте несколько индикаторов для подтверждения сигналов")
    
    # ========================================================================
    # 7. ЗАГРУЗКА И ПРОДОЛЖЕНИЕ РАБОТЫ
    # ========================================================================
    print_section("7. Загрузка сохраненных результатов")
    
    print("Загрузка результатов из файла:")
    
    from bquant.analysis.zones.models import ZoneAnalysisResult
    
    # Загружаем из pickle
    loaded_result = ZoneAnalysisResult.load('results/comprehensive_analysis.pkl')
    
    print(f"   ✅ Загружено из файла:")
    print(f"   Зон: {len(loaded_result.zones)}")
    print(f"   Статистика: {'Да' if loaded_result.statistics else 'Нет'}")
    print(f"   Кластеризация: {'Да' if loaded_result.clustering else 'Нет'}")
    
    print("\n   Теперь можно продолжить работу:")
    print("   - Визуализация: loaded_result.visualize('overview')")
    print("   - Дополнительный анализ")
    print("   - Экспорт в другие форматы")
    
    # ========================================================================
    # ИТОГИ
    # ========================================================================
    print_separator("Итоги comprehensive analysis")
    
    print("✅ Выполнено:")
    print("   1. Загрузка данных с разными рыночными режимами")
    print("   2. Полный pipeline: indicator → detection → analysis")
    print("   3. Детальный анализ результатов (статистика, последовательности, кластеры)")
    print("   4. Сохранение в 3 форматах (pickle, JSON, parquet)")
    print("   5. Модульное использование компонентов")
    print("   6. Сравнение разных индикаторов")
    print("   7. Загрузка и продолжение работы")
    
    print("\n🎯 Ключевые возможности:")
    print("   - Универсальность: один API для всех индикаторов")
    print("   - Гибкость: множество стратегий и параметров")
    print("   - Производительность: автоматическое кэширование")
    print("   - Модульность: используйте только нужные компоненты")
    print("   - Персистентность: сохранение и загрузка результатов")
    
    print("\n📚 Дополнительные ресурсы:")
    print("   - examples/02_macd_zone_analysis.py - базовый пример MACD")
    print("   - examples/02a_universal_zones.py - все индикаторы")
    print("   - research/notebooks/03_zones_universal.py - детальное исследование")
    print("   - devref/gaps/zo/zomodul.md - модульное использование")
    print("   - devref/gaps/zo/zonan.md - полная архитектура")
    
    print("\n" + "="*80)


def print_separator(title: str):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
