#!/usr/bin/env python3
"""
Демонстрация анализа зон bquant.analysis.zones

Этот скрипт демонстрирует работу с модулем анализа зон:
- Zone - базовый класс для представления зон
- ZoneAnalyzer - базовый анализатор зон
- ZoneFeaturesAnalyzer - анализ характеристик зон
- ZoneSequenceAnalyzer - анализ последовательностей и кластеризация зон

Запуск: python 03_analysis_zones.py [--no-trap]
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем путь к корню проекта для импорта bquant
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bquant.core.nb import NotebookSimulator
from bquant.analysis.zones import (
    Zone,
    ZoneAnalyzer
)
from bquant.analysis.zones.zone_features import (
    ZoneFeatures,
    ZoneFeaturesAnalyzer
)
from bquant.analysis.zones.sequence_analysis import (
    TransitionAnalysis,
    ClusterAnalysis,
    ZoneSequenceAnalyzer
)

# Создаем экземпляр NotebookSimulator
nb = NotebookSimulator(
    description="Изучаем анализ зон, их характеристик и последовательностей"
)

# --- Шаг 1: Инициализация и обзор ---
nb.step("Шаг 1: Инициализация и обзор")

nb.info("Изучаем модуль анализа зон bquant.analysis.zones")
nb.log("Доступные компоненты:")
nb.log("  - Zone - базовый класс для представления зон")
nb.log("  - ZoneAnalyzer - базовый анализатор зон")
nb.log("  - ZoneFeatures - характеристики зон")
nb.log("  - ZoneFeaturesAnalyzer - анализ характеристик зон")
nb.log("  - ZoneSequenceAnalyzer - анализ последовательностей и кластеризация")

# Создаем тестовые данные
np.random.seed(42)  # Для воспроизводимости
nb.log("\nСоздание тестовых данных...")

# Создаем OHLCV данные с различными характеристиками
dates = pd.date_range('2024-01-01', periods=300, freq='H')
returns = np.random.randn(300) * 0.02  # 2% волатильность
prices = 100 * np.exp(np.cumsum(returns))  # Логарифмические доходности

test_data = pd.DataFrame({
    'open': prices * (1 + np.random.randn(300) * 0.001),
    'high': prices * (1 + np.abs(np.random.randn(300) * 0.005)),
    'low': prices * (1 - np.abs(np.random.randn(300) * 0.005)),
    'close': prices,
    'volume': np.random.randint(1000, 10000, 300)
}, index=dates)

# Добавляем производные показатели
test_data['returns'] = test_data['close'].pct_change()
test_data['volatility'] = test_data['returns'].rolling(20).std()
test_data['price_range'] = (test_data['high'] - test_data['low']) / test_data['close']

nb.log(f"Создан тестовый датасет: {test_data.shape}")
nb.log(f"Колонки: {list(test_data.columns)}")
nb.log(f"Период: {test_data.index[0]} - {test_data.index[-1]}")

nb.wait()

# --- Шаг 2: Создание базовых зон ---
nb.step("Шаг 2: Создание базовых зон")

nb.info("Создаем и настраиваем различные типы зон")

with nb.error_handling("Creating basic zones"):
    # Создаем зоны различных типов
    zones = []
    
    # Бычьи зоны (восходящий тренд)
    for i in range(5):
        start_time = test_data.index[i * 60]
        end_time = test_data.index[min((i + 1) * 60 - 1, len(test_data) - 1)]
        start_price = test_data.loc[start_time, 'close']
        end_price = test_data.loc[end_time, 'close']
        
        zone = Zone(
            zone_id=f"bull_zone_{i}",
            zone_type="bull",
            start_time=start_time,
            end_time=end_time,
            start_price=start_price,
            end_price=end_price,
            strength=0.7 + np.random.random() * 0.3,  # 0.7-1.0
            confidence=0.8 + np.random.random() * 0.2,  # 0.8-1.0
            metadata={
                'volume_avg': test_data.loc[start_time:end_time, 'volume'].mean(),
                'volatility_avg': test_data.loc[start_time:end_time, 'volatility'].mean(),
                'trend_consistency': np.random.random() * 0.3 + 0.7
            }
        )
        zones.append(zone)
    
    # Медвежьи зоны (нисходящий тренд)
    for i in range(5):
        start_time = test_data.index[150 + i * 30]
        end_time = test_data.index[min(150 + (i + 1) * 30 - 1, len(test_data) - 1)]
        start_price = test_data.loc[start_time, 'close']
        end_price = test_data.loc[end_time, 'close']
        
        zone = Zone(
            zone_id=f"bear_zone_{i}",
            zone_type="bear",
            start_time=start_time,
            end_time=end_time,
            start_price=start_price,
            end_price=end_price,
            strength=0.6 + np.random.random() * 0.4,  # 0.6-1.0
            confidence=0.7 + np.random.random() * 0.3,  # 0.7-1.0
            metadata={
                'volume_avg': test_data.loc[start_time:end_time, 'volume'].mean(),
                'volatility_avg': test_data.loc[start_time:end_time, 'volatility'].mean(),
                'trend_consistency': np.random.random() * 0.4 + 0.6
            }
        )
        zones.append(zone)
    
    # Нейтральные зоны (боковой тренд)
    for i in range(3):
        start_time = test_data.index[100 + i * 40]
        end_time = test_data.index[min(100 + (i + 1) * 40 - 1, len(test_data) - 1)]
        start_price = test_data.loc[start_time, 'close']
        end_price = test_data.loc[start_time, 'close'] * (1 + np.random.randn() * 0.01)
        
        zone = Zone(
            zone_id=f"neutral_zone_{i}",
            zone_type="neutral",
            start_time=start_time,
            end_time=end_time,
            start_price=start_price,
            end_price=end_price,
            strength=0.3 + np.random.random() * 0.4,  # 0.3-0.7
            confidence=0.5 + np.random.random() * 0.3,  # 0.5-0.8
            metadata={
                'volume_avg': test_data.loc[start_time:end_time, 'volume'].mean(),
                'volatility_avg': test_data.loc[start_time:end_time, 'volatility'].mean(),
                'trend_consistency': np.random.random() * 0.5 + 0.3
            }
        )
        zones.append(zone)
    
    nb.log(f"Создано {len(zones)} зон:")
    nb.log(f"  - Бычьи зоны: {len([z for z in zones if z.zone_type == 'bull'])}")
    nb.log(f"  - Медвежьи зоны: {len([z for z in zones if z.zone_type == 'bear'])}")
    nb.log(f"  - Нейтральные зоны: {len([z for z in zones if z.zone_type == 'neutral'])}")

nb.wait()

# --- Шаг 3: Анализ базовых свойств зон ---
nb.step("Шаг 3: Анализ базовых свойств зон")

nb.info("Анализируем базовые свойства созданных зон")

with nb.error_handling("Analyzing basic zone properties"):
    nb.log("3.1. Анализ длительности зон:")
    
    durations = []
    price_ranges = []
    strengths = []
    confidences = []
    
    for zone in zones:
        duration = zone.duration
        price_range = zone.price_range
        mid_price = zone.mid_price
        
        durations.append(duration)
        price_ranges.append(price_range)
        strengths.append(zone.strength)
        confidences.append(zone.confidence)
        
        nb.log(f"  - {zone.zone_id} ({zone.zone_type}):")
        nb.log(f"    * Длительность: {duration}")
        nb.log(f"    * Диапазон цен: {price_range:.4f}")
        nb.log(f"    * Средняя цена: {mid_price:.4f}")
        nb.log(f"    * Сила: {zone.strength:.3f}")
        nb.log(f"    * Уверенность: {zone.confidence:.3f}")
    
    nb.log(f"\n3.2. Сводная статистика:")
    nb.log(f"  - Средняя длительность: {np.mean(durations)}")
    nb.log(f"  - Средний диапазон цен: {np.mean(price_ranges):.4f}")
    nb.log(f"  - Средняя сила: {np.mean(strengths):.3f}")
    nb.log(f"  - Средняя уверенность: {np.mean(confidences):.3f}")

nb.wait()

# --- Шаг 4: Создание ZoneAnalyzer ---
nb.step("Шаг 4: Создание ZoneAnalyzer")

nb.info("Создаем и настраиваем анализатор зон")

with nb.error_handling("Creating ZoneAnalyzer"):
    # Создаем анализатор с настройками
    analyzer_config = {
        'min_zone_duration': 10,  # Минимальная длительность зоны в часах
        'max_zone_duration': 100,  # Максимальная длительность зоны в часах
        'min_price_change': 0.001,  # Минимальное изменение цены (0.1%)
        'enable_volume_analysis': True,
        'enable_volatility_analysis': True
    }
    
    zone_analyzer = ZoneAnalyzer(config=analyzer_config)
    
    nb.log(f"Создан анализатор зон:")
    nb.log(f"  - Имя: {zone_analyzer.name}")
    nb.log(f"  - Конфигурация: {zone_analyzer.config}")
    nb.log(f"  - Минимальная длительность: {zone_analyzer.min_zone_duration} часов")

nb.wait()

# --- Шаг 5: Анализ характеристик зон ---
nb.step("Шаг 5: Анализ характеристик зон")

nb.info("Анализируем детальные характеристики зон с помощью ZoneFeaturesAnalyzer")

with nb.error_handling("Analyzing zone features"):
    # Создаем анализатор характеристик
    features_analyzer = ZoneFeaturesAnalyzer()
    
    nb.log("5.1. Создание характеристик зон:")
    
    zone_features_list = []
    for zone in zones:
        # Получаем данные для зоны
        zone_data = test_data.loc[zone.start_time:zone.end_time]
        
        if len(zone_data) > 0:
            # Создаем характеристики зоны
            features = ZoneFeatures(
                zone_id=zone.zone_id,
                zone_type=zone.zone_type,
                duration=zone.duration,
                start_price=zone.start_price,
                end_price=zone.end_price,
                price_return=(zone.end_price - zone.start_price) / zone.start_price,
                macd_amplitude=0.0,  # Заглушка для демонстрации
                hist_amplitude=0.0,  # Заглушка для демонстрации
                price_range_pct=zone.price_range / zone.mid_price * 100,
                metadata={
                    'volume_avg': zone_data['volume'].mean(),
                    'volume_std': zone_data['volume'].std(),
                    'volatility_avg': zone_data['volatility'].mean() if 'volatility' in zone_data.columns else 0,
                    'volatility_std': zone_data['volatility'].std() if 'volatility' in zone_data.columns else 0,
                    'price_momentum': zone_data['returns'].mean() if 'returns' in zone_data.columns else 0,
                    'price_acceleration': zone_data['returns'].diff().mean() if 'returns' in zone_data.columns else 0
                }
            )
            zone_features_list.append(features)
    
    nb.log(f"  - Создано характеристик: {len(zone_features_list)}")
    
    # Анализируем характеристики по типам зон
    nb.log("\n5.2. Анализ характеристик по типам зон:")
    
    for zone_type in ['bull', 'bear', 'neutral']:
        type_features = [f for f in zone_features_list if f.zone_type == zone_type]
        
        if type_features:
            nb.log(f"  - {zone_type.upper()} зоны ({len(type_features)}):")
            
            avg_duration = np.mean([f.duration for f in type_features])
            avg_return = np.mean([f.price_return for f in type_features])
            avg_volatility = np.mean([f.metadata.get('volatility_avg', 0) for f in type_features])
            avg_volume = np.mean([f.metadata.get('volume_avg', 0) for f in type_features])
            
            nb.log(f"    * Средняя длительность: {avg_duration}")
            nb.log(f"    * Средняя доходность: {avg_return:.4f}")
            nb.log(f"    * Средняя волатильность: {avg_volatility:.4f}")
            nb.log(f"    * Средний объем: {avg_volume:.0f}")

nb.wait()

# --- Шаг 6: Анализ последовательностей зон ---
nb.step("Шаг 6: Анализ последовательностей зон")

nb.info("Анализируем последовательности и переходы между зонами")

with nb.error_handling("Analyzing zone sequences"):
    # Создаем анализатор последовательностей
    sequence_analyzer = ZoneSequenceAnalyzer()
    
    nb.log("6.1. Анализ переходов между зонами:")
    
    # Сортируем зоны по времени
    sorted_zones = sorted(zones, key=lambda z: z.start_time)
    
    # Анализируем переходы
    transitions = []
    for i in range(len(sorted_zones) - 1):
        current_zone = sorted_zones[i]
        next_zone = sorted_zones[i + 1]
        
        transition = {
            'from_type': current_zone.zone_type,
            'to_type': next_zone.zone_type,
            'duration_before': current_zone.duration,
            'duration_after': next_zone.duration,
            'price_change_before': (current_zone.end_price - current_zone.start_price) / current_zone.start_price,
            'price_change_after': (next_zone.end_price - next_zone.start_price) / next_zone.start_price
        }
        transitions.append(transition)
    
    nb.log(f"  - Проанализировано переходов: {len(transitions)}")
    
    # Анализируем типы переходов
    nb.log("\n6.2. Статистика переходов:")
    
    transition_counts = {}
    for transition in transitions:
        transition_key = f"{transition['from_type']} → {transition['to_type']}"
        if transition_key not in transition_counts:
            transition_counts[transition_key] = 0
        transition_counts[transition_key] += 1
    
    for transition_type, count in transition_counts.items():
        nb.log(f"  - {transition_type}: {count} раз")
    
    # Анализируем характеристики переходов
    nb.log("\n6.3. Характеристики переходов:")
    
    for from_type in ['bull', 'bear', 'neutral']:
        for to_type in ['bull', 'bear', 'neutral']:
            relevant_transitions = [t for t in transitions if t['from_type'] == from_type and t['to_type'] == to_type]
            
            if relevant_transitions:
                avg_duration_before = np.mean([t['duration_before'] for t in relevant_transitions])
                avg_duration_after = np.mean([t['duration_after'] for t in relevant_transitions])
                avg_return_before = np.mean([t['price_change_before'] for t in relevant_transitions])
                avg_return_after = np.mean([t['price_change_after'] for t in relevant_transitions])
                
                nb.log(f"  - {from_type} → {to_type}:")
                nb.log(f"    * Средняя длительность до: {avg_duration_before}")
                nb.log(f"    * Средняя длительность после: {avg_duration_after}")
                nb.log(f"    * Средняя доходность до: {avg_return_before:.4f}")
                nb.log(f"    * Средняя доходность после: {avg_return_after:.4f}")

nb.wait()

# --- Шаг 7: Кластеризация зон ---
nb.step("Шаг 7: Кластеризация зон")

nb.info("Выполняем кластеризацию зон по их характеристикам")

with nb.error_handling("Clustering zones"):
    nb.log("7.1. Подготовка данных для кластеризации:")
    
    # Создаем матрицу признаков для кластеризации
    if zone_features_list:
        feature_matrix = []
        zone_ids = []
        
        for features in zone_features_list:
            feature_vector = [
                features.duration,
                features.price_return,
                features.price_range_pct,
                features.metadata.get('volume_avg', 0),
                features.metadata.get('volatility_avg', 0),
                features.metadata.get('price_momentum', 0),
                features.metadata.get('price_acceleration', 0)
            ]
            feature_matrix.append(feature_vector)
            zone_ids.append(features.zone_id)
        
        feature_matrix = np.array(feature_matrix)
        
        nb.log(f"  - Матрица признаков: {feature_matrix.shape}")
        nb.log(f"  - Признаки: длительность, доходность, диапазон цен, объем, волатильность, импульс, ускорение")
        
        # Простая кластеризация по типам зон
        nb.log("\n7.2. Кластеризация по типам зон:")
        
        cluster_results = {}
        for zone_type in ['bull', 'bear', 'neutral']:
            type_indices = [i for i, features in enumerate(zone_features_list) if features.zone_type == zone_type]
            
            if type_indices:
                cluster_data = feature_matrix[type_indices]
                cluster_ids = [zone_ids[i] for i in type_indices]
                
                # Вычисляем центроид кластера
                centroid = np.mean(cluster_data, axis=0)
                
                # Характеристики кластера
                cluster_size = len(cluster_data)
                avg_duration = np.mean(cluster_data[:, 0])
                avg_return = np.mean(cluster_data[:, 1])
                avg_volatility = np.mean(cluster_data[:, 4])
                
                cluster_results[zone_type] = ClusterAnalysis(
                    cluster_id=f"cluster_{zone_type}",
                    size=cluster_size,
                    centroid=centroid.tolist(),
                    characteristics={
                        'avg_duration': avg_duration,
                        'avg_return': avg_return,
                        'avg_volatility': avg_volatility,
                        'zone_ids': cluster_ids
                    },
                    dominant_type=zone_type,
                    avg_duration=avg_duration,
                    avg_return=avg_return
                )
                
                nb.log(f"  - Кластер {zone_type.upper()}:")
                nb.log(f"    * Размер: {cluster_size} зон")
                nb.log(f"    * Средняя длительность: {avg_duration}")
                nb.log(f"    * Средняя доходность: {avg_return:.4f}")
                nb.log(f"    * Средняя волатильность: {avg_volatility:.4f}")
                nb.log(f"    * Зоны: {', '.join(cluster_ids[:3])}{'...' if len(cluster_ids) > 3 else ''}")

nb.wait()

# --- Шаг 8: Создание ZoneAnalyzer ---
nb.step("Шаг 8: Создание ZoneAnalyzer")

nb.info("Создаем и тестируем основной анализатор зон")

with nb.error_handling("Creating and testing ZoneAnalyzer"):
    # Создаем анализатор с настройками
    analyzer_config = {
        'min_zone_duration': 5,
        'max_zone_duration': 200,
        'min_price_change': 0.0005,
        'enable_volume_analysis': True,
        'enable_volatility_analysis': True,
        'enable_sequence_analysis': True
    }
    
    main_zone_analyzer = ZoneAnalyzer(config=analyzer_config)
    
    nb.log(f"Создан основной анализатор зон:")
    nb.log(f"  - Имя: {main_zone_analyzer.name}")
    nb.log(f"  - Конфигурация: {main_zone_analyzer.config}")
    
    # Тестируем валидацию данных
    nb.log("\n8.1. Тестирование валидации данных:")
    
    valid_result = main_zone_analyzer.validate_data(test_data)
    nb.log(f"  - Валидность данных: {valid_result}")
    
    # Тестируем подготовку данных
    nb.log("\n8.2. Тестирование подготовки данных:")
    
    prepared_data = main_zone_analyzer.prepare_data(test_data)
    nb.log(f"  - Подготовленные данные: {prepared_data.shape}")
    nb.log(f"  - Отсортированы по времени: {prepared_data.index.is_monotonic_increasing}")

nb.wait()

# --- Шаг 9: Интеграция всех анализов ---
nb.step("Шаг 9: Интеграция всех анализов")

nb.info("Интегрируем все результаты анализа зон")

with nb.error_handling("Integrating all zone analyses"):
    nb.log("9.1. Сводка по типам зон:")
    
    zone_summary = {}
    for zone_type in ['bull', 'bear', 'neutral']:
        type_zones = [z for z in zones if z.zone_type == zone_type]
        type_features = [f for f in zone_features_list if f.zone_type == zone_type]
        
        if type_zones:
            zone_summary[zone_type] = {
                'count': len(type_zones),
                'avg_duration': np.mean([z.duration for z in type_zones]),
                'avg_strength': np.mean([z.strength for z in type_zones]),
                'avg_confidence': np.mean([z.confidence for z in type_zones]),
                'avg_price_return': np.mean([f.price_return for f in type_features]) if type_features else 0,
                'avg_volatility': np.mean([f.metadata.get('volatility_avg', 0) for f in type_features]) if type_features else 0
            }
    
    for zone_type, summary in zone_summary.items():
        nb.log(f"  - {zone_type.upper()} зоны:")
        nb.log(f"    * Количество: {summary['count']}")
        nb.log(f"    * Средняя длительность: {summary['avg_duration']}")
        nb.log(f"    * Средняя сила: {summary['avg_strength']:.3f}")
        nb.log(f"    * Средняя уверенность: {summary['avg_confidence']:.3f}")
        nb.log(f"    * Средняя доходность: {summary['avg_price_return']:.4f}")
        nb.log(f"    * Средняя волатильность: {summary['avg_volatility']:.4f}")
    
    nb.log("\n9.2. Анализ переходов:")
    
    transition_summary = {}
    for transition_type, count in transition_counts.items():
        relevant_transitions = [t for t in transitions if f"{t['from_type']} → {t['to_type']}" == transition_type]
        
        if relevant_transitions:
            avg_duration_before = np.mean([t['duration_before'] for t in relevant_transitions])
            avg_duration_after = np.mean([t['duration_after'] for t in relevant_transitions])
            avg_return_before = np.mean([t['price_change_before'] for t in relevant_transitions])
            avg_return_after = np.mean([t['price_change_after'] for t in relevant_transitions])
            
            transition_summary[transition_type] = {
                'count': count,
                'avg_duration_before': avg_duration_before,
                'avg_duration_after': avg_duration_after,
                'avg_return_before': avg_return_before,
                'avg_return_after': avg_return_after
            }
    
    for transition_type, summary in transition_summary.items():
        nb.log(f"  - {transition_type}:")
        nb.log(f"    * Количество: {summary['count']}")
        nb.log(f"    * Средняя длительность до: {summary['avg_duration_before']}")
        nb.log(f"    * Средняя длительность после: {summary['avg_duration_after']}")
        nb.log(f"    * Средняя доходность до: {summary['avg_return_before']:.4f}")
        nb.log(f"    * Средняя доходность после: {summary['avg_return_after']:.4f}")

nb.wait()

# --- Шаг 10: Экспорт результатов анализа ---
nb.step("Шаг 10: Экспорт результатов анализа")

nb.info("Экспортируем все результаты анализа зон")

with nb.error_handling("Exporting zone analysis results"):
    # Создаем сводный отчет
    nb.log("10.1. Создание сводного отчета:")
    
    summary_report = {
        'analysis_timestamp': datetime.now().isoformat(),
        'data_summary': {
            'total_observations': len(test_data),
            'time_period': f"{test_data.index[0]} - {test_data.index[-1]}",
            'columns_analyzed': list(test_data.select_dtypes(include=[np.number]).columns)
        },
        'zone_summary': zone_summary,
        'transition_summary': transition_summary,
        'cluster_summary': {
            zone_type: {
                'size': cluster_results[zone_type].size,
                'avg_duration': cluster_results[zone_type].avg_duration,
                'avg_return': cluster_results[zone_type].avg_return
            } for zone_type in cluster_results.keys()
        }
    }
    
    nb.log(f"  - Сводный отчет создан")
    nb.log(f"  - Анализировано зон: {len(zones)}")
    nb.log(f"  - Проанализировано переходов: {len(transitions)}")
    nb.log(f"  - Создано кластеров: {len(cluster_results)}")
    
    # Экспорт результатов
    nb.log("\n10.2. Экспорт результатов:")
    
    try:
        # Экспорт сводного отчета в JSON
        import json
        json_filename = "zone_analysis_report.json"

        # Конвертируем numpy и time-like типы в сериализуемые значения для JSON
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if isinstance(obj, (timedelta, pd.Timedelta, np.timedelta64)):
                # Timedelta -> строка формата "X days HH:MM:SS"
                return str(pd.Timedelta(obj))
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Рекурсивно конвертируем все значения
        def clean_dict(d):
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [clean_dict(v) for v in d]
            else:
                return convert_numpy(d)
        
        clean_summary = clean_dict(summary_report)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(clean_summary, f, indent=2, ensure_ascii=False)
        
        nb.log(f"  - JSON отчет: {json_filename}")
        nb.log(f"  - Размер файла: {os.path.getsize(json_filename)} байт")
        
        # Экспорт характеристик зон в CSV
        csv_filename = "zone_features_analysis.csv"
        
        # Создаем DataFrame с характеристиками зон
        features_data = []
        for features in zone_features_list:
            features_data.append({
                'zone_id': features.zone_id,
                'zone_type': features.zone_type,
                'duration': str(features.duration),
                'price_return': features.price_return,
                'price_range_pct': features.price_range_pct,
                'volume_avg': features.metadata.get('volume_avg', 0),
                'volatility_avg': features.metadata.get('volatility_avg', 0),
                'price_momentum': features.metadata.get('price_momentum', 0),
                'price_acceleration': features.metadata.get('price_acceleration', 0)
            })
        
        features_df = pd.DataFrame(features_data)
        features_df.to_csv(csv_filename, index=False)
        
        nb.log(f"  - CSV характеристики: {csv_filename}")
        nb.log(f"  - Размер файла: {os.path.getsize(csv_filename)} байт")
        
        # Показываем содержимое CSV
        nb.log("  - Содержимое CSV:")
        nb.log(str(features_df.head()))
        
        # Удаляем тестовые файлы
        os.remove(json_filename)
        os.remove(csv_filename)
        nb.log(f"  - Тестовые файлы удалены")
        
    except Exception as e:
        nb.log(f"  - Ошибка экспорта: {str(e)}")

nb.wait()

# --- Завершение ---
nb.step("Завершение")

nb.info("Демонстрация анализа зон bquant.analysis.zones завершена")
nb.log("Изучены:")
nb.log("  ✓ Zone - базовый класс для представления зон")
nb.log("  ✓ ZoneAnalyzer - базовый анализатор зон")
nb.log("  ✓ ZoneFeatures - детальные характеристики зон")
nb.log("  ✓ ZoneFeaturesAnalyzer - анализ характеристик зон")
nb.log("  ✓ ZoneSequenceAnalyzer - анализ последовательностей и кластеризация")
nb.log("  ✓ Анализ переходов между зонами")
nb.log("  ✓ Кластеризация зон по характеристикам")
nb.log("  ✓ Экспорт результатов анализа")

nb.log("\nГотово к созданию скриптов для других модулей анализа!")

# Завершаем работу
nb.finish()
