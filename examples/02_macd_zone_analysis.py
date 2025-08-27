#!/usr/bin/env python3
"""
BQuant - Расширенный анализ зон MACD

Этот пример демонстрирует:
1. Использование MACDZoneAnalyzer для определения зон
2. Расчет признаков зон и их интерпретацию
3. Статистическое тестирование торговых гипотез
4. Кластеризацию зон по форме
5. Анализ последовательностей зон
6. Визуализацию результатов

Требования:
- Установленный BQuant пакет: pip install -e .
- Данные в формате OHLCV
- Дополнительно: matplotlib для визуализации (опционально)
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Добавляем путь к BQuant для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.indicators.macd import (
    MACDZoneAnalyzer, ZoneAnalysisResult, ZoneInfo,
    create_macd_analyzer, analyze_macd_zones
)
from bquant.core.config import get_indicator_params, get_analysis_params


def create_trending_data(rows: int = 500, symbol: str = "EURUSD") -> pd.DataFrame:
    """
    Создание данных с выраженными трендовыми движениями для MACD анализа.
    
    Args:
        rows: Количество строк данных
        symbol: Символ инструмента
        
    Returns:
        DataFrame с OHLCV данными с четкими трендами
    """
    print(f"📊 Создание трендовых данных для {symbol} ({rows} баров)...")
    
    # Генерируем временной ряд
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1H')
    np.random.seed(123)  # Для воспроизводимости трендовых данных
    
    base_price = 1.1000  # EUR/USD
    prices = [base_price]
    
    # Создаем циклические тренды для четких MACD зон
    for i in range(1, rows):
        # Основной тренд - синусоида с разными периодами
        long_trend = 0.002 * np.sin(i / 80)  # Долгосрочный тренд
        medium_trend = 0.001 * np.sin(i / 30)  # Среднесрочный тренд
        short_noise = np.random.normal(0, 0.0005)  # Короткий шум
        
        # Добавляем моменты "пробоев" для четких сигналов
        if i % 120 == 0:
            breakthrough = 0.003 * (1 if np.random.random() > 0.5 else -1)
        else:
            breakthrough = 0
        
        total_change = long_trend + medium_trend + short_noise + breakthrough
        new_price = prices[-1] * (1 + total_change)
        prices.append(max(new_price, 0.5))  # Минимальная цена
    
    # Создаем OHLCV структуру
    data = []
    for i, close_price in enumerate(prices):
        if i == 0:
            open_price = close_price
        else:
            open_price = prices[i-1]
        
        # Реалистичные high/low
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
    
    df = pd.DataFrame(data, index=dates)
    print(f"✅ Создано {len(df)} баров с трендовыми движениями")
    print(f"   Период: {df.index[0]} - {df.index[-1]}")
    print(f"   Ценовой диапазон: {df['close'].min():.4f} - {df['close'].max():.4f}")
    print(f"   Общее изменение: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
    
    return df


def demonstrate_macd_zone_analysis():
    """Демонстрация полного анализа зон MACD."""
    
    print("🚀 BQuant - Расширенный анализ зон MACD")
    print("=" * 70)
    
    # 1. Создаем данные с выраженными трендами
    data = create_trending_data(400, "EURUSD")
    
    # 2. Создаем MACD анализатор
    print(f"\n⚙️ Инициализация MACD анализатора:")
    
    # Получаем параметры из конфигурации
    macd_params = get_indicator_params('macd')
    zone_params = get_analysis_params('zone_analysis')
    
    print(f"   📊 Параметры MACD: {macd_params}")
    print(f"   🎯 Параметры зон: {zone_params}")
    
    # Создаем анализатор
    analyzer = MACDZoneAnalyzer(macd_params, zone_params)
    print(f"   ✅ MACDZoneAnalyzer инициализирован")
    
    # 3. Выполняем полный анализ
    print(f"\n🔬 Выполнение полного анализа зон:")
    
    try:
        result = analyzer.analyze_complete(
            data, 
            perform_clustering=True, 
            n_clusters=3
        )
        
        print(f"   ✅ Анализ завершен успешно")
        print(f"   📊 Найдено зон: {len(result.zones)}")
        print(f"   🧪 Проведено гипотез: {len(result.hypothesis_tests)}")
        print(f"   🎯 Кластеризация: {'Да' if result.clustering else 'Нет'}")
        
    except Exception as e:
        print(f"   ❌ Ошибка анализа: {e}")
        return None
    
    # 4. Анализ найденных зон
    print(f"\n📊 Анализ обнаруженных зон:")
    
    if not result.zones:
        print("   ⚠️ Зоны не найдены")
        return result
    
    # Статистика по типам зон
    bull_zones = [z for z in result.zones if z.type == 'bull']
    bear_zones = [z for z in result.zones if z.type == 'bear']
    
    print(f"   🐂 Бычьих зон: {len(bull_zones)}")
    print(f"   🐻 Медвежьих зон: {len(bear_zones)}")
    print(f"   ⚖️ Соотношение bull/bear: {len(bull_zones)}/{len(bear_zones)}")
    
    # Анализ длительности зон
    durations = [zone.duration for zone in result.zones]
    if durations:
        print(f"   📏 Длительность зон:")
        print(f"      Средняя: {np.mean(durations):.1f} баров")
        print(f"      Медиана: {np.median(durations):.1f} баров")
        print(f"      Мин/Макс: {min(durations)}/{max(durations)} баров")
    
    # Детальный анализ первых 3 зон
    print(f"\n🔍 Детальный анализ первых зон:")
    
    for i, zone in enumerate(result.zones[:3]):
        print(f"\n   🏷️ Зона #{zone.zone_id} ({zone.type.upper()}):")
        print(f"      ⏱️ Период: {zone.start_time} - {zone.end_time}")
        print(f"      📏 Длительность: {zone.duration} баров")
        
        if zone.features:
            features = zone.features
            print(f"      💰 Ценовая доходность: {features['price_return']:.4f} ({features['price_return']*100:.2f}%)")
            print(f"      📈 MACD амплитуда: {features['macd_amplitude']:.6f}")
            print(f"      📊 Гистограмма амплитуда: {features['hist_amplitude']:.6f}")
            
            if 'price_hist_corr' in features:
                corr_str = f"{features['price_hist_corr']:.3f}"
                print(f"      🔗 Корреляция цена-гистограмма: {corr_str}")
            
            # Специфичные метрики для типа зоны
            if zone.type == 'bull' and 'drawdown_from_peak' in features:
                dd = features['drawdown_from_peak']
                print(f"      📉 Просадка от пика: {dd:.4f} ({dd*100:.2f}%)")
            elif zone.type == 'bear' and 'rally_from_trough' in features:
                rally = features['rally_from_trough']
                print(f"      📈 Отскок от дна: {rally:.4f} ({rally*100:.2f}%)")
    
    # 5. Статистические тесты гипотез
    print(f"\n🧪 Результаты статистических тестов:")
    
    if result.hypothesis_tests:
        for test_name, test_result in result.hypothesis_tests.items():
            significance = "✅ Значим" if test_result['significant'] else "❌ Не значим"
            p_val = test_result.get('p_value', 'N/A')
            
            print(f"\n   📋 {test_name}:")
            print(f"      📄 Описание: {test_result['description']}")
            print(f"      📊 Результат: {significance}")
            if p_val != 'N/A':
                print(f"      🎯 P-value: {p_val:.4f}")
            
            # Дополнительные детали для конкретных тестов
            if 'long_zones_avg_return' in test_result:
                print(f"      📈 Средняя доходность длинных зон: {test_result['long_zones_avg_return']:.4f}")
                print(f"      📉 Средняя доходность коротких зон: {test_result['short_zones_avg_return']:.4f}")
            
            if 'correlation' in test_result:
                print(f"      🔗 Корреляция: {test_result['correlation']:.4f}")
    else:
        print("   ⚠️ Статистические тесты не проведены (недостаточно данных)")
    
    # 6. Анализ последовательностей зон
    print(f"\n🔄 Анализ последовательностей зон:")
    
    if result.sequence_analysis and result.sequence_analysis['total_transitions'] > 0:
        seq_analysis = result.sequence_analysis
        print(f"   📊 Всего переходов: {seq_analysis['total_transitions']}")
        
        for transition, probability in seq_analysis['transition_probabilities'].items():
            count = seq_analysis['transitions'][transition]
            print(f"   📈 {transition}: {count} раз ({probability:.1%})")
    else:
        print("   ⚠️ Недостаточно зон для анализа последовательностей")
    
    # 7. Результаты кластеризации
    print(f"\n🎯 Результаты кластеризации зон:")
    
    if result.clustering:
        clustering = result.clustering
        n_clusters = clustering['n_clusters']
        features_used = clustering['features_used']
        
        print(f"   📊 Количество кластеров: {n_clusters}")
        print(f"   🔧 Использованные признаки: {', '.join(features_used)}")
        
        for cluster_name, cluster_info in clustering['cluster_analysis'].items():
            print(f"\n   🏷️ {cluster_name.upper()}:")
            print(f"      📊 Размер: {cluster_info['size']} зон")
            print(f"      ⏱️ Средняя длительность: {cluster_info['avg_duration']:.1f} баров")
            print(f"      💰 Средняя доходность: {cluster_info['avg_price_return']:.4f}")
            print(f"      🐂 Доля бычьих зон: {cluster_info['bull_ratio']:.1%}")
    else:
        print("   ⚠️ Кластеризация не выполнена")
    
    # 8. Общая статистика распределения
    print(f"\n📊 Общая статистика распределения:")
    
    if result.statistics:
        stats = result.statistics
        print(f"   📈 Всего зон: {stats['total_zones']}")
        print(f"   🐂 Бычьих зон: {stats['bull_zones']}")
        print(f"   🐻 Медвежьих зон: {stats['bear_zones']}")
        print(f"   ⚖️ Соотношение быков: {stats['bull_ratio']:.1%}")
        
        if 'bull_duration_mean' in stats:
            print(f"   ⏱️ Средняя длительность бычьих зон: {stats['bull_duration_mean']:.1f} баров")
        if 'bear_duration_mean' in stats:
            print(f"   ⏱️ Средняя длительность медвежьих зон: {stats['bear_duration_mean']:.1f} баров")
        
        if 'bull_price_return_mean' in stats:
            bull_ret = stats['bull_price_return_mean']
            print(f"   💰 Средняя доходность бычьих зон: {bull_ret:.4f} ({bull_ret*100:.2f}%)")
        if 'bear_price_return_mean' in stats:
            bear_ret = stats['bear_price_return_mean']
            print(f"   💰 Средняя доходность медвежьих зон: {bear_ret:.4f} ({bear_ret*100:.2f}%)")
    
    # 9. Метаданные анализа
    print(f"\n📋 Метаданные анализа:")
    
    if result.metadata:
        meta = result.metadata
        print(f"   🕐 Время анализа: {meta.get('analysis_timestamp', 'N/A')}")
        print(f"   📊 Период данных: {meta.get('data_period', {}).get('start', 'N/A')} - {meta.get('data_period', {}).get('end', 'N/A')}")
        print(f"   📈 Всего баров: {meta.get('data_period', {}).get('total_bars', 'N/A')}")
        print(f"   ⚙️ Параметры MACD: {meta.get('macd_params', 'N/A')}")
        print(f"   🎯 Параметры зон: {meta.get('zone_params', 'N/A')}")
    
    return result


def demonstrate_convenience_functions():
    """Демонстрация удобных функций для быстрого анализа."""
    
    print(f"\n🛠️ Демонстрация convenience функций:")
    print("-" * 50)
    
    # Создаем тестовые данные
    data = create_trending_data(300, "GBPUSD")
    
    # 1. Быстрое создание анализатора
    print(f"\n1️⃣ Использование create_macd_analyzer():")
    
    analyzer = create_macd_analyzer(
        macd_params={'fast': 10, 'slow': 21, 'signal': 7},
        zone_params={'min_duration': 3}
    )
    print(f"   ✅ Анализатор создан с кастомными параметрами")
    
    # 2. One-shot анализ
    print(f"\n2️⃣ Использование analyze_macd_zones():")
    
    try:
        result = analyze_macd_zones(
            data,
            macd_params={'fast': 8, 'slow': 17, 'signal': 5},
            perform_clustering=False  # Отключаем кластеризацию для скорости
        )
        
        print(f"   ✅ One-shot анализ завершен")
        print(f"   📊 Найдено зон: {len(result.zones)}")
        print(f"   🧪 Проведено тестов: {len(result.hypothesis_tests)}")
        
        # Краткий отчет
        if result.zones:
            bull_count = sum(1 for z in result.zones if z.type == 'bull')
            bear_count = len(result.zones) - bull_count
            print(f"   🐂 Бычьих зон: {bull_count}")
            print(f"   🐻 Медвежьих зон: {bear_count}")
            
    except Exception as e:
        print(f"   ❌ Ошибка one-shot анализа: {e}")


def save_analysis_results(result: ZoneAnalysisResult, filename_prefix: str = "macd_analysis"):
    """Сохранение результатов анализа в файлы."""
    
    print(f"\n💾 Сохранение результатов анализа:")
    
    try:
        # Сохраняем данные зон
        if result.zones:
            zones_data = []
            for zone in result.zones:
                zone_record = {
                    'zone_id': zone.zone_id,
                    'type': zone.type,
                    'start_time': zone.start_time,
                    'end_time': zone.end_time,
                    'duration': zone.duration,
                    'start_idx': zone.start_idx,
                    'end_idx': zone.end_idx
                }
                
                # Добавляем признаки если есть
                if zone.features:
                    zone_record.update(zone.features)
                
                zones_data.append(zone_record)
            
            zones_df = pd.DataFrame(zones_data)
            zones_file = f"examples/{filename_prefix}_zones.csv"
            zones_df.to_csv(zones_file, index=False)
            print(f"   ✅ Данные зон сохранены: {zones_file}")
            print(f"      📊 Зон: {len(zones_df)}, колонок: {len(zones_df.columns)}")
        
        # Сохраняем статистики
        if result.statistics:
            stats_file = f"examples/{filename_prefix}_statistics.csv"
            stats_df = pd.DataFrame([result.statistics])
            stats_df.to_csv(stats_file, index=False)
            print(f"   ✅ Статистики сохранены: {stats_file}")
        
        # Сохраняем результаты гипотез
        if result.hypothesis_tests:
            tests_file = f"examples/{filename_prefix}_hypothesis_tests.csv"
            tests_df = pd.DataFrame(result.hypothesis_tests).T
            tests_df.to_csv(tests_file)
            print(f"   ✅ Результаты тестов сохранены: {tests_file}")
        
        # Сохраняем результаты кластеризации
        if result.clustering:
            clustering_file = f"examples/{filename_prefix}_clustering.csv"
            clustering_df = pd.DataFrame(result.clustering['cluster_analysis']).T
            clustering_df.to_csv(clustering_file)
            print(f"   ✅ Результаты кластеризации сохранены: {clustering_file}")
        
    except Exception as e:
        print(f"   ❌ Ошибка сохранения: {e}")


if __name__ == "__main__":
    try:
        # Основная демонстрация
        main_result = demonstrate_macd_zone_analysis()
        
        # Демонстрация convenience функций
        demonstrate_convenience_functions()
        
        # Сохранение результатов
        if main_result:
            save_analysis_results(main_result, "comprehensive_macd")
        
        print(f"\n🎉 Демонстрация MACD анализа завершена!")
        print(f"\n💡 Ключевые возможности:")
        print(f"   ✓ Автоматическое определение зон MACD")
        print(f"   ✓ Расчет 20+ признаков для каждой зоны")
        print(f"   ✓ Статистическое тестирование торговых гипотез")
        print(f"   ✓ Кластеризация зон по форме")
        print(f"   ✓ Анализ последовательностей зон")
        print(f"   ✓ Экспорт результатов в CSV")
        
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
