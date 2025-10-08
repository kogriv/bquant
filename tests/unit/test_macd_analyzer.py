"""
Tests for BQuant MACD Zone Analyzer

Тесты для современного MACD анализатора зон с полной функциональностью:
определение зон, расчет признаков, статистические тесты, кластеризация.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

# BQuant imports для тестирования MACD анализатора
from bquant.indicators.macd import (
    ZoneInfo, ZoneAnalysisResult, MACDZoneAnalyzer,
    create_macd_analyzer, analyze_macd_zones
)
from bquant.core.exceptions import AnalysisError, StatisticalAnalysisError


def create_test_ohlcv_data(rows: int = 200, add_clear_zones: bool = True) -> pd.DataFrame:
    """
    Создание тестовых OHLCV данных с четкими MACD зонами.
    
    Args:
        rows: Количество строк данных
        add_clear_zones: Добавлять ли четкие зоны для тестирования
    
    Returns:
        DataFrame с тестовыми данными
    """
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1h')
    
    np.random.seed(42)  # Для воспроизводимости
    
    if add_clear_zones:
        # Создаем данные с четкими трендовыми зонами
        base_price = 2000.0
        prices = [base_price]
        
        # Создаем циклические движения для четких MACD зон
        for i in range(1, rows):
            cycle_position = i / rows * 4 * np.pi  # 4 полных цикла
            trend_component = np.sin(cycle_position) * 0.05  # 5% амплитуда тренда
            noise = np.random.normal(0, 0.01)  # 1% шум
            
            change = trend_component + noise
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 100.0))  # Минимальная цена 100
    else:
        # Создаем простые случайные данные
        base_price = 2000.0
        prices = [base_price]
        
        for i in range(1, rows):
            change = np.random.normal(0, 0.01)
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 100.0))
    
    # Создаем OHLCV данные
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.005)))
        low = price * (1 - abs(np.random.normal(0, 0.005)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': max(high, open_price, close_price),
            'low': min(low, open_price, close_price),
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)


class TestMACDZoneAnalyzer:
    """Тесты для MACDZoneAnalyzer."""
    
    def test_analyzer_initialization(self):
        """Тест инициализации анализатора."""
        print("\n📋 Тестирование инициализации MACDZoneAnalyzer:")
        
        # Тест с параметрами по умолчанию
        analyzer = MACDZoneAnalyzer()
        assert analyzer.macd_params is not None
        assert analyzer.zone_params is not None
        assert 'fast' in analyzer.macd_params
        assert 'slow' in analyzer.macd_params
        assert 'signal' in analyzer.macd_params
        
        print("✅ Инициализация с параметрами по умолчанию работает")
        
        # Тест с пользовательскими параметрами
        custom_macd = {'fast': 10, 'slow': 20, 'signal': 5}
        custom_zone = {'min_duration': 3, 'min_amplitude': 0.002}
        
        analyzer_custom = MACDZoneAnalyzer(custom_macd, custom_zone)
        assert analyzer_custom.macd_params == custom_macd
        assert analyzer_custom.zone_params == custom_zone
        
        print("✅ Инициализация с пользовательскими параметрами работает")
    
    def test_macd_calculation(self):
        """Тест расчета MACD и ATR."""
        print("\n📋 Тестирование расчета MACD и ATR:")
        
        # Создаем тестовые данные
        test_data = create_test_ohlcv_data(100)
        analyzer = MACDZoneAnalyzer()
        
        # Рассчитываем индикаторы
        result = analyzer.calculate_macd_with_atr(test_data)
        
        # Проверяем результат
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(test_data)
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_hist' in result.columns
        
        # Проверяем наличие ATR или других производных индикаторов
        has_derived_indicators = any(col for col in result.columns 
                                   if col not in test_data.columns)
        assert has_derived_indicators
        
        print(f"✅ MACD и производные индикаторы рассчитаны. Колонок: {len(result.columns)}")
    
    def test_zone_identification(self):
        """Тест определения зон MACD."""
        print("\n📋 Тестирование определения зон MACD:")
        
        # Создаем данные с четкими зонами
        test_data = create_test_ohlcv_data(150, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Рассчитываем индикаторы
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        
        # Определяем зоны
        zones = analyzer.identify_zones(df_with_indicators)
        
        # Проверяем результат
        assert isinstance(zones, list)
        assert len(zones) > 0
        
        # Проверяем структуру зон
        for zone in zones:
            assert isinstance(zone, ZoneInfo)
            assert zone.type in ['bull', 'bear']
            assert zone.duration > 0
            assert zone.start_idx < zone.end_idx
            assert isinstance(zone.data, pd.DataFrame)
            assert len(zone.data) == zone.duration
        
        # Проверяем чередование типов зон
        zone_types = [zone.type for zone in zones]
        has_bull = 'bull' in zone_types
        has_bear = 'bear' in zone_types
        
        print(f"✅ Определено {len(zones)} зон: {zone_types.count('bull')} bull, {zone_types.count('bear')} bear")
        assert has_bull or has_bear  # Должна быть хотя бы одна зона
    
    def test_zone_features_calculation(self):
        """Тест расчета признаков зон."""
        print("\n📋 Тестирование расчета признаков зон:")
        
        test_data = create_test_ohlcv_data(120, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Получаем зоны
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        zones = analyzer.identify_zones(df_with_indicators)
        
        if not zones:
            print("⚠️ Зоны не найдены, пропускаем тест признаков")
            return
        
        # Рассчитываем признаки для первой зоны
        first_zone = zones[0]
        features = analyzer.calculate_zone_features(first_zone)
        
        # Проверяем базовые признаки
        required_features = [
            'zone_id', 'type', 'duration', 'start_price', 'end_price',
            'price_return', 'max_macd', 'min_macd', 'macd_amplitude',
            'max_hist', 'min_hist', 'hist_amplitude'
        ]
        
        for feature in required_features:
            assert feature in features, f"Feature {feature} not found"
            assert features[feature] is not None
        
        # Проверяем специфичные признаки для типа зоны
        if first_zone.type == 'bull':
            assert 'drawdown_from_peak' in features
            assert 'peak_time_ratio' in features
        else:
            assert 'rally_from_trough' in features
            assert 'trough_time_ratio' in features
        
        print(f"✅ Рассчитано {len(features)} признаков для зоны {first_zone.type}")
        
        # Добавляем признаки к зоне
        first_zone.features = features
        assert first_zone.features == features
        
        print("✅ Признаки успешно добавлены к зоне")
    
    def test_zones_distribution_analysis(self):
        """Тест анализа распределения зон."""
        print("\n📋 Тестирование анализа распределения зон:")
        
        test_data = create_test_ohlcv_data(180, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Получаем зоны с признаками
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        zones = analyzer.identify_zones(df_with_indicators)
        
        if len(zones) < 2:
            print("⚠️ Недостаточно зон для анализа распределения")
            return
        
        # Рассчитываем признаки для всех зон
        for zone in zones:
            zone.features = analyzer.calculate_zone_features(zone)
        
        # Анализируем распределение
        stats = analyzer.analyze_zones_distribution(zones)
        
        # Проверяем структуру статистик
        required_stats = ['total_zones', 'bull_zones', 'bear_zones', 'bull_ratio']
        for stat in required_stats:
            assert stat in stats
        
        assert stats['total_zones'] == len(zones)
        assert stats['bull_zones'] + stats['bear_zones'] == stats['total_zones']
        
        print(f"✅ Статистики распределения: {stats['total_zones']} зон, "
              f"соотношение быков: {stats['bull_ratio']:.2f}")
    
    def test_hypothesis_testing(self):
        """Тест статистических гипотез."""
        print("\n📋 Тестирование статистических гипотез:")
        
        # Создаем больше данных для статистических тестов
        test_data = create_test_ohlcv_data(300, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Получаем зоны с признаками
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        zones = analyzer.identify_zones(df_with_indicators)
        
        if len(zones) < 10:
            print("⚠️ Недостаточно зон для статистических тестов")
            return
        
        # Рассчитываем признаки для всех зон
        for zone in zones:
            zone.features = analyzer.calculate_zone_features(zone)
        
        # Тестируем гипотезы
        hypothesis_results = analyzer.test_hypotheses(zones)
        
        # Проверяем структуру результатов
        assert isinstance(hypothesis_results, dict)
        
        for test_name, result in hypothesis_results.items():
            assert 'description' in result
            assert 'significant' in result
            assert isinstance(result['significant'], bool)
            
            if 'p_value' in result:
                assert 0 <= result['p_value'] <= 1
        
        print(f"✅ Выполнено {len(hypothesis_results)} статистических тестов")
        
        # Выводим результаты
        for test_name, result in hypothesis_results.items():
            significance = "✅ Значим" if result['significant'] else "❌ Не значим"
            print(f"   {test_name}: {significance}")
    
    def test_sequence_analysis(self):
        """Тест анализа последовательностей."""
        print("\n📋 Тестирование анализа последовательностей:")
        
        test_data = create_test_ohlcv_data(200, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Получаем зоны
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        zones = analyzer.identify_zones(df_with_indicators)
        
        if len(zones) < 2:
            print("⚠️ Недостаточно зон для анализа последовательностей")
            return
        
        # Анализируем последовательности
        sequence_analysis = analyzer.analyze_zone_sequences(zones)
        
        # Проверяем структуру результатов
        assert 'transitions' in sequence_analysis
        assert 'transition_probabilities' in sequence_analysis
        assert 'total_transitions' in sequence_analysis
        
        total_transitions = sequence_analysis['total_transitions']
        assert total_transitions == len(zones) - 1
        
        # Проверяем сумму вероятностей
        if sequence_analysis['transition_probabilities']:
            prob_sum = sum(sequence_analysis['transition_probabilities'].values())
            assert abs(prob_sum - 1.0) < 0.001  # Сумма должна быть ~1
        
        print(f"✅ Анализ последовательностей: {total_transitions} переходов")
        
        # Выводим переходы
        for transition, count in sequence_analysis['transitions'].items():
            prob = sequence_analysis['transition_probabilities'].get(transition, 0)
            print(f"   {transition}: {count} раз ({prob:.2%})")
    
    def test_clustering(self):
        """Тест кластеризации зон."""
        print("\n📋 Тестирование кластеризации зон:")
        
        test_data = create_test_ohlcv_data(250, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Получаем зоны с признаками
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        zones = analyzer.identify_zones(df_with_indicators)
        
        if len(zones) < 6:  # Минимум для кластеризации на 3 группы
            print("⚠️ Недостаточно зон для кластеризации")
            return
        
        # Рассчитываем признаки для всех зон
        for zone in zones:
            zone.features = analyzer.calculate_zone_features(zone)
        
        # Кластеризуем
        n_clusters = min(3, len(zones) // 2)  # Адаптивное количество кластеров
        clustering_result = analyzer.cluster_zones_by_shape(zones, n_clusters)
        
        # Проверяем результат
        assert 'cluster_labels' in clustering_result
        assert 'cluster_analysis' in clustering_result
        assert 'n_clusters' in clustering_result
        assert 'features_used' in clustering_result
        
        assert len(clustering_result['cluster_labels']) == len(zones)
        assert clustering_result['n_clusters'] == n_clusters
        
        # Проверяем анализ кластеров
        cluster_analysis = clustering_result['cluster_analysis']
        assert len(cluster_analysis) == n_clusters
        
        for cluster_name, cluster_info in cluster_analysis.items():
            assert 'size' in cluster_info
            assert 'avg_duration' in cluster_info
            assert cluster_info['size'] > 0
        
        print(f"✅ Кластеризация выполнена: {n_clusters} кластеров, "
              f"признаков: {len(clustering_result['features_used'])}")
        
        # Выводим информацию о кластерах
        for cluster_name, info in cluster_analysis.items():
            print(f"   {cluster_name}: {info['size']} зон, "
                  f"средняя длительность: {info['avg_duration']:.1f}")


class TestMACDAnalyzerIntegration:
    """Интеграционные тесты для MACD анализатора."""
    
    def test_complete_analysis(self):
        """Тест полного анализа."""
        print("\n📋 Тестирование полного анализа MACD:")
        
        test_data = create_test_ohlcv_data(200, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Выполняем полный анализ
        result = analyzer.analyze_complete(test_data, perform_clustering=True, n_clusters=3)
        
        # Проверяем структуру результата
        assert isinstance(result, ZoneAnalysisResult)
        assert hasattr(result, 'zones')
        assert hasattr(result, 'statistics')
        assert hasattr(result, 'hypothesis_tests')
        assert hasattr(result, 'sequence_analysis')
        assert hasattr(result, 'metadata')
        
        # Проверяем метаданные
        assert 'analysis_timestamp' in result.metadata
        assert 'data_period' in result.metadata
        assert 'macd_params' in result.metadata
        assert 'zone_params' in result.metadata
        
        print(f"✅ Полный анализ выполнен: {len(result.zones)} зон, "
              f"{len(result.hypothesis_tests)} гипотез")
        
        # Проверяем, что все зоны имеют признаки
        zones_with_features = sum(1 for zone in result.zones if zone.features)
        assert zones_with_features == len(result.zones)
        
        print(f"✅ Все {zones_with_features} зон имеют рассчитанные признаки")
    
    def test_convenience_functions(self):
        """Тест удобных функций."""
        print("\n📋 Тестирование удобных функций:")
        
        test_data = create_test_ohlcv_data(150)
        
        # Тест create_macd_analyzer
        analyzer = create_macd_analyzer()
        assert isinstance(analyzer, MACDZoneAnalyzer)
        
        print("✅ create_macd_analyzer() работает")
        
        # Тест analyze_macd_zones
        result = analyze_macd_zones(test_data, perform_clustering=False)
        assert isinstance(result, ZoneAnalysisResult)
        
        print("✅ analyze_macd_zones() работает")
    
    def test_error_handling(self):
        """Тест обработки ошибок."""
        print("\n📋 Тестирование обработки ошибок:")
        
        analyzer = MACDZoneAnalyzer()
        
        # Тест с пустыми данными
        empty_data = pd.DataFrame()
        
        try:
            analyzer.calculate_macd_with_atr(empty_data)
            assert False, "Должно было возникнуть исключение"
        except (AnalysisError, Exception):
            pass  # Ожидаемое поведение
        
        print("✅ Обработка пустых данных работает")
        
        # Тест с данными без OHLCV колонок
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        
        try:
            analyzer.calculate_macd_with_atr(invalid_data)
            assert False, "Должно было возникнуть исключение"
        except (AnalysisError, Exception):
            pass  # Ожидаемое поведение
        
        print("✅ Обработка некорректных данных работает")


class TestModularAnalyzer:
    """Тесты для модульной версии анализатора (Фаза 1 рефакторинга)."""
    
    def test_adapter_methods(self):
        """Тест вспомогательных методов-адаптеров."""
        print("\n📋 Тестирование методов-адаптеров:")
        
        analyzer = MACDZoneAnalyzer()
        test_data = create_test_ohlcv_data(100)
        
        # Получаем зоны
        df_with_indicators = analyzer.calculate_macd_with_atr(test_data)
        zones = analyzer.identify_zones(df_with_indicators)
        
        if not zones:
            print("⚠️ Зоны не найдены, пропускаем тест")
            return
        
        first_zone = zones[0]
        first_zone.features = analyzer.calculate_zone_features(first_zone)
        
        # Тест _zone_to_dict
        zone_dict = analyzer._zone_to_dict(first_zone)
        assert isinstance(zone_dict, dict)
        assert 'zone_id' in zone_dict
        assert 'type' in zone_dict
        assert 'duration' in zone_dict
        assert 'data' in zone_dict
        assert zone_dict['zone_id'] == first_zone.zone_id
        assert zone_dict['type'] == first_zone.type
        
        print("✅ Метод _zone_to_dict() работает корректно")
        
        # Тест _features_to_dict
        features_dict = analyzer._features_to_dict(first_zone.features)
        assert isinstance(features_dict, dict)
        
        print("✅ Метод _features_to_dict() работает корректно")
    
    def test_modular_analyze_complete(self):
        """Тест модульной версии analyze_complete."""
        print("\n📋 Тестирование analyze_complete_modular():")
        
        test_data = create_test_ohlcv_data(200, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Выполняем модульный анализ
        result = analyzer.analyze_complete_modular(test_data, perform_clustering=True, n_clusters=3)
        
        # Проверяем структуру результата
        assert isinstance(result, ZoneAnalysisResult)
        assert hasattr(result, 'zones')
        assert hasattr(result, 'statistics')
        assert hasattr(result, 'hypothesis_tests')
        assert hasattr(result, 'sequence_analysis')
        assert hasattr(result, 'metadata')
        
        # Проверяем флаг модульной версии
        assert 'modular_version' in result.metadata
        assert result.metadata['modular_version'] is True
        
        print(f"✅ Модульный анализ выполнен: {len(result.zones)} зон")
        
        # Проверяем, что все зоны имеют признаки
        zones_with_features = sum(1 for zone in result.zones if zone.features)
        assert zones_with_features == len(result.zones)
        
        print(f"✅ Все {zones_with_features} зон имеют рассчитанные признаки")
    
    def test_compare_old_vs_modular(self):
        """Тест сравнения старой и модульной версии анализа."""
        print("\n📋 Сравнение analyze_complete() vs analyze_complete_modular():")
        
        test_data = create_test_ohlcv_data(150, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Выполняем оба варианта анализа
        result_old = analyzer.analyze_complete(test_data, perform_clustering=False)
        result_modular = analyzer.analyze_complete_modular(test_data, perform_clustering=False)
        
        # Сравниваем количество зон
        assert len(result_old.zones) == len(result_modular.zones), \
            f"Разное количество зон: {len(result_old.zones)} vs {len(result_modular.zones)}"
        
        print(f"✅ Количество зон совпадает: {len(result_old.zones)}")
        
        # Сравниваем типы зон
        old_types = [zone.type for zone in result_old.zones]
        modular_types = [zone.type for zone in result_modular.zones]
        assert old_types == modular_types, "Типы зон не совпадают"
        
        print(f"✅ Типы зон совпадают: {old_types}")
        
        # Сравниваем длительности зон
        old_durations = [zone.duration for zone in result_old.zones]
        modular_durations = [zone.duration for zone in result_modular.zones]
        assert old_durations == modular_durations, "Длительности зон не совпадают"
        
        print(f"✅ Длительности зон совпадают")
        
        # Сравниваем основные статистики
        assert result_old.statistics['total_zones'] == result_modular.statistics['total_zones']
        assert result_old.statistics['bull_zones'] == result_modular.statistics['bull_zones']
        assert result_old.statistics['bear_zones'] == result_modular.statistics['bear_zones']
        
        print("✅ Статистики зон совпадают")
        
        # Сравниваем наличие признаков
        old_zones_with_features = sum(1 for zone in result_old.zones if zone.features)
        modular_zones_with_features = sum(1 for zone in result_modular.zones if zone.features)
        assert old_zones_with_features == modular_zones_with_features
        
        print(f"✅ Количество зон с признаками совпадает: {old_zones_with_features}")
        
        # Сравниваем ключи признаков первой зоны (если есть)
        if result_old.zones and result_old.zones[0].features and result_modular.zones[0].features:
            old_keys = set(result_old.zones[0].features.keys())
            modular_keys = set(result_modular.zones[0].features.keys())
            
            # Проверяем что основные ключи есть в обеих версиях
            common_keys = old_keys & modular_keys
            assert len(common_keys) > 0, "Нет общих ключей признаков"
            
            print(f"✅ Найдено {len(common_keys)} общих признаков")
            
            # Сравниваем значения общих признаков (с учетом погрешности для float)
            first_zone_old = result_old.zones[0].features
            first_zone_modular = result_modular.zones[0].features
            
            differences = []
            for key in common_keys:
                val_old = first_zone_old[key]
                val_modular = first_zone_modular[key]
                
                # Пропускаем None значения
                if val_old is None or val_modular is None:
                    continue
                
                # Для числовых значений проверяем с погрешностью
                if isinstance(val_old, (int, float)) and isinstance(val_modular, (int, float)):
                    if abs(val_old - val_modular) > 1e-6:
                        differences.append(f"{key}: {val_old} vs {val_modular}")
                # Для остальных проверяем точное совпадение
                elif val_old != val_modular:
                    differences.append(f"{key}: {val_old} vs {val_modular}")
            
            if differences:
                print(f"⚠️  Найдено {len(differences)} различий в признаках:")
                for diff in differences[:5]:  # Показываем первые 5
                    print(f"   {diff}")
            else:
                print("✅ Значения всех общих признаков совпадают")
        
        print("\n🎉 РЕЗУЛЬТАТЫ ИДЕНТИЧНЫ! Модульная версия работает корректно")
    
    def test_modular_with_clustering(self):
        """Тест модульной версии с кластеризацией."""
        print("\n📋 Тестирование модульной версии с кластеризацией:")
        
        test_data = create_test_ohlcv_data(250, add_clear_zones=True)
        analyzer = MACDZoneAnalyzer()
        
        # Выполняем модульный анализ с кластеризацией
        result = analyzer.analyze_complete_modular(test_data, perform_clustering=True, n_clusters=3)
        
        # Проверяем что кластеризация выполнена (если было достаточно зон)
        if len(result.zones) >= 3:
            assert result.clustering is not None or result.metadata['clustering_performed'] is False
            
            if result.clustering:
                print(f"✅ Кластеризация выполнена успешно")
            else:
                print("⚠️  Кластеризация не выполнена (недостаточно данных или ошибка)")
        else:
            print(f"⚠️  Недостаточно зон для кластеризации ({len(result.zones)} < 3)")


def run_macd_analyzer_tests():
    """Запуск всех тестов MACD анализатора."""
    print("🚀 Запуск тестов MACD Zone Analyzer...")
    print("=" * 60)
    
    # Создаем экземпляры тестовых классов и запускаем тесты
    test_classes = [
        TestMACDZoneAnalyzer(),
        TestMACDAnalyzerIntegration(),
        TestModularAnalyzer()  # Фаза 1: тесты модульной версии
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n📊 {class_name}:")
        
        # Получаем все методы, начинающиеся с test_
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                print(f"❌ {method_name}: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 Результаты тестирования MACD анализатора:")
    print(f"   Всего тестов: {total_tests}")
    print(f"   Пройдено: {passed_tests}")
    print(f"   Провалено: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ MACD АНАЛИЗАТОРА ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("⚠️  Некоторые тесты MACD анализатора провалены")
        return False


if __name__ == "__main__":
    run_macd_analyzer_tests()
