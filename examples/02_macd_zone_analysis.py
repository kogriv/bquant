#!/usr/bin/env python3
"""
BQuant - MACD Zone Analysis: Old vs New Approach

Этот пример демонстрирует миграцию на новую универсальную архитектуру анализа зон.

Разделы:
1. [!] Deprecated подход (MACDZoneAnalyzer) - для backward compatibility
2. [OK] Новый универсальный подход (analyze_zones) - RECOMMENDED
3. Разные стратегии детекции зон
4. Модульное использование компонентов
5. Базовая визуализация результатов

Требования:
- Установленный BQuant: pip install -e .
- Данные в формате OHLCV
"""

import sys
import os
import pandas as pd
import numpy as np

# Добавляем путь к BQuant
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)  # Для чистого вывода


def create_sample_data(rows: int = 500) -> pd.DataFrame:
    """Создание трендовых данных для MACD анализа."""
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1H')
    np.random.seed(123)
    
    base_price = 1.1000
    prices = [base_price]
    
    for i in range(1, rows):
        long_trend = 0.002 * np.sin(i / 80)
        medium_trend = 0.001 * np.sin(i / 30)
        short_noise = np.random.normal(0, 0.0005)
        
        if i % 120 == 0:
            breakthrough = 0.003 * (1 if np.random.random() > 0.5 else -1)
        else:
            breakthrough = 0
        
        total_change = long_trend + medium_trend + short_noise + breakthrough
        new_price = prices[-1] * (1 + total_change)
        prices.append(max(new_price, 0.5))
    
    data = []
    for i, close_price in enumerate(prices):
        open_price = prices[i-1] if i > 0 else close_price
        high = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.0003)))
        low = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.0003)))
        volume = np.random.randint(100000, 500000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)


def print_separator(title: str):
    """Печать разделителя."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def main():
    print_separator("MACD Zone Analysis - Old vs New Approach")
    
    # Генерация данных
    print("[*] Generating data...")
    df = create_sample_data(rows=500)
    print(f"[OK] Created {len(df)} bars (period: {df.index[0]} - {df.index[-1]})")
    
    # ========================================================================
    # РАЗДЕЛ 1: [!] DEPRECATED ПОДХОД (для backward compatibility)
    # ========================================================================
    print_separator("1. [!] Deprecated подход (MACDZoneAnalyzer)")
    
    print("[!] WARNING: Этот подход устарел и будет удален в v3.0.0")
    print("   Используется только для backward compatibility\n")
    
    from bquant.indicators.macd import MACDZoneAnalyzer
    
    # Старый способ - через класс
    analyzer_old = MACDZoneAnalyzer(
        macd_params={'fast': 12, 'slow': 26, 'signal': 9},
        zone_params={'min_duration': 2}
    )
    
    result_old = analyzer_old.analyze_complete(df, perform_clustering=True, n_clusters=3)
    
    print(f"[OK] Analysis complete (old approach):")
    print(f"   - Zones found: {len(result_old.zones)}")
    print(f"   - Bull zones: {sum(1 for z in result_old.zones if z.type == 'bull')}")
    print(f"   - Bear zones: {sum(1 for z in result_old.zones if z.type == 'bear')}")
    
    # ========================================================================
    # РАЗДЕЛ 2: [OK] НОВЫЙ УНИВЕРСАЛЬНЫЙ ПОДХОД (RECOMMENDED)
    # ========================================================================
    print_separator("2. [OK] Новый универсальный подход (RECOMMENDED)")
    
    from bquant.analysis.zones import analyze_zones
    
    print("Способ 1: Fluent API (builder pattern)")
    print("-" * 40)
    
    result_new = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    
    print(f"[OK] Analysis complete (new approach):")
    print(f"   - Zones found: {len(result_new.zones)}")
    print(f"   - Bull zones: {sum(1 for z in result_new.zones if z.type == 'bull')}")
    print(f"   - Bear zones: {sum(1 for z in result_new.zones if z.type == 'bear')}")
    print(f"   - Clustering: {'Yes' if result_new.clustering else 'No'}")
    
    print("\nMethod 2: Convenience preset (even simpler)")
    print("-" * 40)
    
    from bquant.analysis.zones.presets import analyze_macd_zones
    
    result_preset = analyze_macd_zones(
        df, 
        fast=12, slow=26, signal=9,
        min_duration=2,
        clustering=True
    )
    
    print(f"[OK] Analysis via preset:")
    print(f"   - Zones found: {len(result_preset.zones)}")
    
    # ========================================================================
    # РАЗДЕЛ 3: РАЗНЫЕ СТРАТЕГИИ ДЕТЕКЦИИ
    # ========================================================================
    print_separator("3. Разные стратегии детекции MACD зон")
    
    print("Стратегия 1: Zero Crossing (пересечение нуля)")
    print("-" * 40)
    
    result_zero = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(clustering=False)
        .build()
    )
    print(f"   Зон: {len(result_zero.zones)}")
    
    print("\nСтратегия 2: Line Crossing (пересечение MACD и сигнальной линии)")
    print("-" * 40)
    
    result_line = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('line_crossing', 
                     line1_col='macd',
                     line2_col='macd_signal')
        .analyze(clustering=False)
        .build()
    )
    print(f"   Зон: {len(result_line.zones)}")
    
    print("\nСтратегия 3: Combined Rules (комбинация условий)")
    print("-" * 40)
    
    # Combined strategy требует условия (callable functions), а не стратегии
    # Note: кэширование отключено, так как lambda functions не JSON serializable
    result_combined = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('combined',
                     conditions=[
                         lambda d: d['macd_hist'] > 0,  # Условие 1: гистограмма положительная
                         lambda d: d['macd_hist'].abs() > 0.005  # Условие 2: сильный сигнал
                     ],
                     logic='AND')  # Обе условия должны быть True
        .with_cache(enable=False)  # Отключаем кэширование (lambda не serializable)
        .analyze(clustering=False)
        .build()
    )
    print(f"   Зон: {len(result_combined.zones)} (где обе условия выполнены)")
    
    # ========================================================================
    # РАЗДЕЛ 4: МОДУЛЬНОЕ ИСПОЛЬЗОВАНИЕ
    # ========================================================================
    print_separator("4. Модульное использование компонентов")
    
    print("Сценарий 1: Только детекция зон (без полного анализа)")
    print("-" * 40)
    
    from bquant.indicators import IndicatorFactory
    from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
    
    # Шаг 1: Рассчитать индикатор
    macd_indicator = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    macd_result = macd_indicator.calculate(df)
    
    df_with_macd = df.copy()
    for col in macd_result.data.columns:
        df_with_macd[col] = macd_result.data[col]
    
    # Шаг 2: Детекция зон
    detector = ZoneDetectionRegistry.get('zero_crossing')
    config = ZoneDetectionConfig(
        min_duration=2,
        rules={'indicator_col': 'macd_hist'},
        strategy_name='zero_crossing'
    )
    zones = detector.detect_zones(df_with_macd, config)
    
    print(f"   Обнаружено {len(zones)} зон")
    print(f"   Первая зона: {zones[0].type}, длительность: {zones[0].duration} баров")
    
    # Можно сохранить зоны для дальнейшего использования
    import pickle
    with open('macd_zones.pkl', 'wb') as f:
        pickle.dump(zones, f)
    print(f"   [SAVE] Зоны сохранены в macd_zones.pkl")
    
    print("\nСценарий 2: Анализ готовых зон (без детекции)")
    print("-" * 40)
    
    from bquant.analysis.zones import UniversalZoneAnalyzer
    
    # Загружаем зоны
    with open('macd_zones.pkl', 'rb') as f:
        loaded_zones = pickle.load(f)
    
    # Анализируем
    analyzer = UniversalZoneAnalyzer()
    result_modular = analyzer.analyze_zones(
        loaded_zones, 
        df_with_macd,
        perform_clustering=True,
        n_clusters=3
    )
    
    print(f"   Проанализировано {len(result_modular.zones)} зон")
    print(f"   Кластеров: {3 if result_modular.clustering else 0}")
    
    # Cleanup
    os.remove('macd_zones.pkl')
    
    # ========================================================================
    # РАЗДЕЛ 5: БАЗОВАЯ ВИЗУАЛИЗАЦИЯ
    # ========================================================================
    print_separator("5. Визуализация результатов")
    
    print("Сохранение результатов для дальнейшего использования:")
    print("-" * 40)
    
    # Сохранение в разных форматах
    result_new.save('macd_analysis_full.pkl', format='pickle', include_data=True)
    print("   [SAVE] Полный результат: macd_analysis_full.pkl")
    
    result_new.save('macd_analysis_light.json', format='json', include_data=False)
    print("   [SAVE] Легкий результат (без данных): macd_analysis_light.json")
    
    print("\nВизуализация через ZoneAnalysisResult.visualize():")
    print("-" * 40)
    print("   Для визуализации используйте:")
    print("   result.visualize('overview')  # Общий график с зонами")
    print("   result.visualize('detail', zone_id=0)  # Детальный график зоны")
    print("   result.visualize('comparison', zone_ids=[0, 1, 2])  # Сравнение зон")
    print("   result.visualize('statistics')  # Статистические графики")
    
    # Cleanup
    os.remove('macd_analysis_full.pkl')
    os.remove('macd_analysis_light.json')
    
    # ========================================================================
    # ИТОГИ
    # ========================================================================
    print_separator("Итоги анализа")
    
    print("Сравнение подходов:")
    print("-" * 40)
    print(f"{'Метрика':<30} {'Старый API':<15} {'Новый API':<15}")
    print("-" * 60)
    print(f"{'Количество зон':<30} {len(result_old.zones):<15} {len(result_new.zones):<15}")
    print(f"{'Bull зоны':<30} {sum(1 for z in result_old.zones if z.type == 'bull'):<15} {sum(1 for z in result_new.zones if z.type == 'bull'):<15}")
    print(f"{'Bear зоны':<30} {sum(1 for z in result_old.zones if z.type == 'bear'):<15} {sum(1 for z in result_new.zones if z.type == 'bear'):<15}")
    
    print("\n[OK] Ключевые преимущества нового подхода:")
    print("   1. Универсальность - один API для всех индикаторов")
    print("   2. Гибкость - множество стратегий детекции")
    print("   3. Модульность - можно использовать компоненты отдельно")
    print("   4. Кэширование - автоматическое сохранение результатов")
    print("   5. Расширяемость - легко добавлять новые стратегии")
    
    print("\n[DOCS] Additional examples:")
    print("   - examples/02a_universal_zones.py - universal API for different indicators")
    print("   - examples/04_comprehensive_analysis.py - full pipeline with visualization")
    print("   - research/notebooks/03_zones_universal.py - detailed research")
    
    print("\n[TARGET] Recommendation for new projects:")
    print("   Use the new universal API:")
    print("   from bquant.analysis.zones import analyze_zones")
    print("   result = analyze_zones(df).with_indicator(...).detect_zones(...).build()")


if __name__ == "__main__":
    main()
