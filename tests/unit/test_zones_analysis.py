"""
Тесты для модулей анализа зон BQuant

Проверяют корректность переноса и адаптации функций анализа зон из оригинального проекта.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

# BQuant imports
from bquant.analysis.zones import (
    Zone,
    ZoneAnalyzer,
    find_support_resistance
)

# Импорты для расширенного анализа зон
try:
    from bquant.analysis.zones.zone_features import (
        ZoneFeatures,
        ZoneFeaturesAnalyzer,
        analyze_zones_distribution,
        extract_zone_features
    )
    zone_features_available = True
except ImportError:
    zone_features_available = False

try:
    from bquant.analysis.zones.sequence_analysis import (
        TransitionAnalysis,
        ClusterAnalysis,
        ZoneSequenceAnalyzer,
        create_zone_sequence_analysis,
        cluster_zone_shapes
    )
    sequence_analysis_available = True
except ImportError:
    sequence_analysis_available = False

from bquant.core.exceptions import AnalysisError


def create_test_ohlcv_data(n_periods: int = 100, seed: int = 42) -> pd.DataFrame:
    """
    Создает тестовые OHLCV данные с некоторыми трендами и паттернами.
    
    Args:
        n_periods: Количество периодов
        seed: Семя для генератора случайных чисел
    
    Returns:
        DataFrame с OHLCV данными
    """
    np.random.seed(seed)
    
    # Создаем временные индексы
    timestamps = pd.date_range('2024-01-01', periods=n_periods, freq='1H')
    
    # Создаем базовую цену с трендом
    base_price = 2000
    trend = np.linspace(0, 200, n_periods)  # Восходящий тренд
    noise = np.random.normal(0, 10, n_periods)  # Случайный шум
    
    close_prices = base_price + trend + noise
    
    # Создаем OHLC на основе close
    high_offset = np.random.uniform(5, 20, n_periods)
    low_offset = np.random.uniform(5, 20, n_periods)
    open_offset = np.random.uniform(-10, 10, n_periods)
    
    data = pd.DataFrame({
        'open': close_prices + open_offset,
        'high': close_prices + high_offset,
        'low': close_prices - low_offset,
        'close': close_prices,
        'volume': np.random.uniform(1000, 10000, n_periods)
    }, index=timestamps)
    
    # Добавляем MACD данные (имитируем расчет)
    data['macd'] = np.random.normal(0, 5, n_periods)
    data['macd_signal'] = data['macd'].rolling(9).mean()
    data['macd_hist'] = data['macd'] - data['macd_signal']
    
    # Добавляем ATR данные
    data['atr'] = np.random.uniform(10, 30, n_periods)
    
    return data


def create_test_zone_info(zone_type: str = 'bull', duration: int = 20) -> Dict[str, Any]:
    """
    Создает тестовую информацию о зоне.
    
    Args:
        zone_type: Тип зоны ('bull' или 'bear')
        duration: Длительность зоны
    
    Returns:
        Словарь с информацией о зоне
    """
    data = create_test_ohlcv_data(duration)
    
    return {
        'zone_id': f'test_{zone_type}_zone',
        'type': zone_type,
        'duration': duration,
        'data': data
    }


class TestBasicZoneAnalyzer:
    """Тесты базового анализатора зон."""
    
    @pytest.fixture
    def analyzer(self):
        """Создание базового анализатора."""
        return ZoneAnalyzer()
    
    @pytest.fixture
    def test_data(self):
        """Создание тестовых данных."""
        return create_test_ohlcv_data(100)
    
    def test_analyzer_initialization(self, analyzer):
        """Тест инициализации анализатора."""
        assert analyzer.min_zone_duration > 0
        assert analyzer.min_strength_threshold >= 0
        assert analyzer.min_confidence_threshold >= 0
    
    def test_find_support_resistance(self, analyzer, test_data):
        """Тест поиска уровней поддержки и сопротивления."""
        zones = analyzer.identify_support_resistance(test_data, window=10, min_touches=2)
        
        assert isinstance(zones, list)
        # Может быть пустым если нет достаточных паттернов
        for zone in zones:
            assert isinstance(zone, Zone)
            assert zone.zone_type in ['support', 'resistance']
            assert zone.strength >= 0 and zone.strength <= 1
            assert zone.confidence >= 0 and zone.confidence <= 1
    
    def test_convenience_function(self, test_data):
        """Тест удобной функции поиска."""
        zones = find_support_resistance(test_data, window=10, min_touches=2)
        
        assert isinstance(zones, list)
        for zone in zones:
            assert isinstance(zone, Zone)
    
    def test_zone_properties(self):
        """Тест свойств объекта Zone."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        
        zone = Zone(
            zone_id='test_zone',
            zone_type='support',
            start_time=start_time,
            end_time=end_time,
            start_price=2000.0,
            end_price=2010.0,
            strength=0.8,
            confidence=0.7
        )
        
        assert zone.duration.total_seconds() == 2 * 3600  # 2 часа
        assert zone.price_range == 10.0
        assert zone.mid_price == 2005.0
        
        zone_dict = zone.to_dict()
        assert isinstance(zone_dict, dict)
        assert 'zone_id' in zone_dict
        assert 'duration_hours' in zone_dict


@pytest.mark.skipif(not zone_features_available, reason="Zone features module not available")
class TestZoneFeaturesAnalyzer:
    """Тесты анализатора характеристик зон."""
    
    @pytest.fixture
    def analyzer(self):
        """Создание анализатора характеристик зон."""
        return ZoneFeaturesAnalyzer(min_duration=5, min_amplitude=0.001)
    
    @pytest.fixture
    def test_zone_info(self):
        """Создание тестовой информации о зоне."""
        return create_test_zone_info('bull', 20)
    
    def test_analyzer_initialization(self, analyzer):
        """Тест инициализации анализатора."""
        assert analyzer.min_duration == 5
        assert analyzer.min_amplitude == 0.001
    
    def test_extract_zone_features(self, analyzer, test_zone_info):
        """Тест извлечения характеристик зоны."""
        features = analyzer.extract_zone_features(test_zone_info)
        
        assert isinstance(features, ZoneFeatures)
        assert features.zone_id == 'test_bull_zone'
        assert features.zone_type == 'bull'
        assert features.duration == 20
        assert isinstance(features.start_price, float)
        assert isinstance(features.end_price, float)
        assert isinstance(features.price_return, float)
        assert isinstance(features.macd_amplitude, float)
        assert isinstance(features.hist_amplitude, float)
        assert isinstance(features.price_range_pct, float)
    
    def test_zone_features_to_dict(self, analyzer, test_zone_info):
        """Тест конвертации характеристик в словарь."""
        features = analyzer.extract_zone_features(test_zone_info)
        features_dict = features.to_dict()
        
        assert isinstance(features_dict, dict)
        assert 'zone_id' in features_dict
        assert 'zone_type' in features_dict
        assert 'duration' in features_dict
        assert 'price_return' in features_dict
    
    def test_analyze_zones_distribution(self, analyzer):
        """Тест анализа распределения зон."""
        # Создаем несколько тестовых зон
        zones_features = []
        for i in range(10):
            zone_type = 'bull' if i % 2 == 0 else 'bear'
            zone_info = create_test_zone_info(zone_type, 15 + i)
            features = analyzer.extract_zone_features(zone_info)
            zones_features.append(features)
        
        analysis_result = analyzer.analyze_zones_distribution(zones_features)
        
        assert analysis_result.analysis_type == 'zones_distribution'
        assert 'total_statistics' in analysis_result.results
        assert 'duration_distribution' in analysis_result.results
        assert 'return_distribution' in analysis_result.results
        
        total_stats = analysis_result.results['total_statistics']
        assert total_stats['total_zones'] == 10
        assert total_stats['bull_zones_count'] == 5
        assert total_stats['bear_zones_count'] == 5
    
    def test_convenience_functions(self):
        """Тест удобных функций."""
        # Тест extract_zone_features
        zone_info = create_test_zone_info('bear', 15)
        features_dict = extract_zone_features(zone_info)
        
        assert isinstance(features_dict, dict)
        assert features_dict['zone_type'] == 'bear'
        assert features_dict['duration'] == 15
        
        # Тест analyze_zones_distribution
        zones_features = [features_dict]
        distribution = analyze_zones_distribution(zones_features)
        
        assert isinstance(distribution, dict)
        assert 'total_statistics' in distribution
    
    def test_error_handling(self, analyzer):
        """Тест обработки ошибок."""
        # Тест с недостаточной длительностью
        short_zone_info = create_test_zone_info('bull', 2)  # Меньше min_duration=5
        
        with pytest.raises(AnalysisError):
            analyzer.extract_zone_features(short_zone_info)
        
        # Тест с пустым списком зон
        with pytest.raises(AnalysisError):
            analyzer.analyze_zones_distribution([])


@pytest.mark.skipif(not sequence_analysis_available, reason="Sequence analysis module not available")
class TestZoneSequenceAnalyzer:
    """Тесты анализатора последовательностей зон."""
    
    @pytest.fixture
    def analyzer(self):
        """Создание анализатора последовательностей."""
        return ZoneSequenceAnalyzer(min_sequence_length=3)
    
    @pytest.fixture
    def test_zones_sequence(self):
        """Создание тестовой последовательности зон."""
        zones_features = []
        zone_types = ['bull', 'bear', 'bull', 'bull', 'bear', 'bear', 'bull']
        
        for i, zone_type in enumerate(zone_types):
            zone_info = create_test_zone_info(zone_type, 10 + i)
            if zone_features_available:
                analyzer = ZoneFeaturesAnalyzer()
                features = analyzer.extract_zone_features(zone_info)
                zones_features.append(features)
            else:
                # Fallback к словарям
                features_dict = {
                    'zone_id': f'zone_{i}',
                    'zone_type': zone_type,
                    'duration': 10 + i,
                    'price_return': np.random.normal(0, 0.1),
                    'macd_amplitude': np.random.uniform(1, 10),
                    'hist_amplitude': np.random.uniform(0.5, 5),
                    'price_range_pct': np.random.uniform(0.01, 0.1)
                }
                zones_features.append(features_dict)
        
        return zones_features
    
    def test_analyzer_initialization(self, analyzer):
        """Тест инициализации анализатора."""
        assert analyzer.min_sequence_length == 3
    
    def test_analyze_zone_transitions(self, analyzer, test_zones_sequence):
        """Тест анализа переходов между зонами."""
        analysis_result = analyzer.analyze_zone_transitions(test_zones_sequence)
        
        assert analysis_result.analysis_type == 'zone_transitions'
        assert 'sequence_summary' in analysis_result.results
        assert 'transitions' in analysis_result.results
        assert 'transition_probabilities' in analysis_result.results
        
        sequence_summary = analysis_result.results['sequence_summary']
        assert sequence_summary['total_zones'] == 7
        assert sequence_summary['total_transitions'] == 6
        
        transitions = analysis_result.results['transitions']
        assert isinstance(transitions, dict)
        assert sum(transitions.values()) == 6  # Общее количество переходов
    
    def test_cluster_zones(self, analyzer, test_zones_sequence):
        """Тест кластеризации зон."""
        analysis_result = analyzer.cluster_zones(test_zones_sequence, n_clusters=3)
        
        assert analysis_result.analysis_type == 'zone_clustering'
        assert 'clustering_summary' in analysis_result.results
        assert 'cluster_labels' in analysis_result.results
        assert 'clusters_analysis' in analysis_result.results
        
        clustering_summary = analysis_result.results['clustering_summary']
        assert clustering_summary['n_clusters'] == 3
        assert clustering_summary['total_zones'] == 7
        
        cluster_labels = analysis_result.results['cluster_labels']
        assert len(cluster_labels) == 7
        assert all(0 <= label < 3 for label in cluster_labels)
    
    def test_convenience_functions(self, test_zones_sequence):
        """Тест удобных функций."""
        # Тест create_zone_sequence_analysis
        transitions_analysis = create_zone_sequence_analysis(test_zones_sequence)
        
        assert isinstance(transitions_analysis, dict)
        assert 'sequence_summary' in transitions_analysis
        assert 'transitions' in transitions_analysis
        
        # Тест cluster_zone_shapes
        clustering_result = cluster_zone_shapes(test_zones_sequence, n_clusters=2)
        
        assert isinstance(clustering_result, dict)
        assert 'clustering_summary' in clustering_result
        assert 'cluster_labels' in clustering_result
    
    def test_error_handling(self, analyzer):
        """Тест обработки ошибок."""
        # Тест с недостаточным количеством зон
        short_sequence = [{'zone_type': 'bull'}, {'zone_type': 'bear'}]
        
        with pytest.raises(AnalysisError):
            analyzer.analyze_zone_transitions(short_sequence)
        
        # Тест кластеризации с недостаточным количеством зон
        with pytest.raises(AnalysisError):
            analyzer.cluster_zones([{'zone_type': 'bull'}], n_clusters=3)


class TestIntegrationZonesAnalysis:
    """Интеграционные тесты анализа зон."""
    
    def test_basic_zones_workflow(self):
        """Тест базового workflow анализа зон."""
        # Создаем тестовые данные
        data = create_test_ohlcv_data(50)
        
        # Ищем зоны поддержки и сопротивления
        zones = find_support_resistance(data, window=5, min_touches=1)
        
        # Проверяем, что функция работает без ошибок
        assert isinstance(zones, list)
        for zone in zones:
            assert isinstance(zone, Zone)
    
    @pytest.mark.skipif(not zone_features_available, reason="Zone features module not available")
    def test_zone_features_workflow(self):
        """Тест workflow анализа характеристик зон."""
        # Создаем несколько тестовых зон
        zones_features = []
        for i in range(5):
            zone_type = 'bull' if i % 2 == 0 else 'bear'
            zone_info = create_test_zone_info(zone_type, 10 + i * 2)
            features_dict = extract_zone_features(zone_info)
            zones_features.append(features_dict)
        
        # Анализируем распределение
        distribution = analyze_zones_distribution(zones_features)
        
        # Проверяем результаты
        assert isinstance(distribution, dict)
        assert distribution['total_statistics']['total_zones'] == 5
    
    @pytest.mark.skipif(not sequence_analysis_available, reason="Sequence analysis module not available")
    def test_sequence_analysis_workflow(self):
        """Тест workflow анализа последовательностей."""
        # Создаем тестовую последовательность
        zones_features = []
        zone_types = ['bull', 'bear', 'bull', 'bear']
        
        for i, zone_type in enumerate(zone_types):
            features_dict = {
                'zone_type': zone_type,
                'duration': 10 + i,
                'price_return': np.random.normal(0, 0.1),
                'macd_amplitude': np.random.uniform(1, 5),
                'hist_amplitude': np.random.uniform(0.5, 2),
                'price_range_pct': np.random.uniform(0.01, 0.05)
            }
            zones_features.append(features_dict)
        
        # Анализируем переходы
        transitions = create_zone_sequence_analysis(zones_features)
        
        # Проверяем результаты
        assert isinstance(transitions, dict)
        assert transitions['sequence_summary']['total_zones'] == 4
        assert transitions['sequence_summary']['total_transitions'] == 3
        
        # Анализируем кластеры
        clusters = cluster_zone_shapes(zones_features, n_clusters=2)
        
        # Проверяем результаты
        assert isinstance(clusters, dict)
        assert len(clusters['cluster_labels']) == 4
    
    @pytest.mark.skipif(not (zone_features_available and sequence_analysis_available), 
                       reason="Both zone analysis modules required")
    def test_complete_zones_analysis_workflow(self):
        """Тест полного workflow анализа зон."""
        # 1. Создаем OHLCV данные
        data = create_test_ohlcv_data(30)
        
        # 2. Ищем базовые зоны
        zones = find_support_resistance(data, window=5, min_touches=1)
        
        # 3. Создаем MACD зоны для анализа характеристик
        macd_zones_info = []
        for i in range(6):
            zone_type = 'bull' if i % 2 == 0 else 'bear'
            zone_info = create_test_zone_info(zone_type, 8 + i)
            macd_zones_info.append(zone_info)
        
        # 4. Извлекаем характеристики зон
        zones_features = []
        for zone_info in macd_zones_info:
            features_dict = extract_zone_features(zone_info)
            zones_features.append(features_dict)
        
        # 5. Анализируем распределение
        distribution = analyze_zones_distribution(zones_features)
        
        # 6. Анализируем последовательности
        transitions = create_zone_sequence_analysis(zones_features)
        
        # 7. Кластеризуем зоны
        clusters = cluster_zone_shapes(zones_features, n_clusters=2)
        
        # Проверяем, что все этапы выполнились успешно
        assert isinstance(zones, list)
        assert isinstance(distribution, dict)
        assert isinstance(transitions, dict)
        assert isinstance(clusters, dict)
        
        # Проверяем согласованность данных
        assert distribution['total_statistics']['total_zones'] == 6
        assert transitions['sequence_summary']['total_zones'] == 6
        assert len(clusters['cluster_labels']) == 6


class TestErrorHandlingAndEdgeCases:
    """Тесты обработки ошибок и крайних случаев."""
    
    def test_empty_data(self):
        """Тест с пустыми данными."""
        empty_data = pd.DataFrame()
        
        # Базовый анализатор
        zones = find_support_resistance(empty_data)
        assert zones == []
    
    def test_insufficient_data(self):
        """Тест с недостаточным количеством данных."""
        small_data = create_test_ohlcv_data(5)
        
        # Базовый анализатор с большим окном
        zones = find_support_resistance(small_data, window=10)
        assert zones == []  # Должен вернуть пустой список
    
    @pytest.mark.skipif(not zone_features_available, reason="Zone features module not available")
    def test_invalid_zone_info(self):
        """Тест с некорректной информацией о зоне."""
        analyzer = ZoneFeaturesAnalyzer()
        
        # Отсутствует обязательное поле
        invalid_zone_info = {
            'zone_id': 'test',
            # 'type': отсутствует
            'duration': 10,
            'data': create_test_ohlcv_data(10)
        }
        
        with pytest.raises((KeyError, AnalysisError)):
            analyzer.extract_zone_features(invalid_zone_info)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
