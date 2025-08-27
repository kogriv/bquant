"""
Тесты для структуры модуля анализа BQuant

Проверяют корректность импортов, базовой функциональности и архитектуры модуля анализа.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

# BQuant imports
from bquant.analysis import (
    AnalysisResult,
    BaseAnalyzer,
    get_available_analyzers,
    create_analyzer,
    SUPPORTED_ANALYSIS_TYPES
)


class TestAnalysisStructure:
    """Тесты структуры модуля анализа."""
    
    def test_analysis_imports(self):
        """Тест импорта основных модулей анализа."""
        # Проверяем основные импорты
        from bquant.analysis import statistical
        from bquant.analysis import zones
        from bquant.analysis import technical
        from bquant.analysis import chart
        from bquant.analysis import candlestick
        from bquant.analysis import timeseries
        
        assert statistical is not None
        assert zones is not None
        assert technical is not None
        assert chart is not None
        assert candlestick is not None
        assert timeseries is not None
    
    def test_analysis_result_creation(self):
        """Тест создания AnalysisResult."""
        results = {'test_metric': 42, 'test_value': 3.14}
        metadata = {'analyzer': 'TestAnalyzer', 'version': '1.0'}
        
        analysis_result = AnalysisResult(
            analysis_type='test',
            results=results,
            data_size=100,
            metadata=metadata
        )
        
        assert analysis_result.analysis_type == 'test'
        assert analysis_result.results == results
        assert analysis_result.data_size == 100
        assert analysis_result.metadata == metadata
        assert isinstance(analysis_result.timestamp, datetime)
    
    def test_analysis_result_to_dict(self):
        """Тест конвертации AnalysisResult в словарь."""
        results = {'metric1': 1, 'metric2': 2}
        
        analysis_result = AnalysisResult(
            analysis_type='test',
            results=results,
            data_size=50
        )
        
        result_dict = analysis_result.to_dict()
        
        assert 'analysis_type' in result_dict
        assert 'timestamp' in result_dict
        assert 'data_size' in result_dict
        assert 'results' in result_dict
        assert 'metadata' in result_dict
        
        assert result_dict['analysis_type'] == 'test'
        assert result_dict['data_size'] == 50
        assert result_dict['results'] == results
    
    def test_base_analyzer_creation(self):
        """Тест создания базового анализатора."""
        config = {'param1': 'value1', 'param2': 42}
        
        analyzer = BaseAnalyzer('TestAnalyzer', config)
        
        assert analyzer.name == 'TestAnalyzer'
        assert analyzer.config == config
        assert analyzer.logger is not None
    
    def test_base_analyzer_data_validation(self):
        """Тест валидации данных в базовом анализаторе."""
        analyzer = BaseAnalyzer('TestAnalyzer')
        
        # Пустые данные
        empty_df = pd.DataFrame()
        assert not analyzer.validate_data(empty_df)
        
        # None данные
        assert not analyzer.validate_data(None)
        
        # Недостаточно данных
        small_df = pd.DataFrame({'a': [1, 2]})
        analyzer.config['min_data_points'] = 10
        assert not analyzer.validate_data(small_df)
        
        # Корректные данные
        good_df = pd.DataFrame({'a': range(20)})
        assert analyzer.validate_data(good_df)
    
    def test_base_analyzer_prepare_data(self):
        """Тест подготовки данных в базовом анализаторе."""
        analyzer = BaseAnalyzer('TestAnalyzer')
        
        # Создаем тестовые данные
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            'value': range(10),
            'timestamp': dates
        })
        data.set_index('timestamp', inplace=True)
        
        # Перемешиваем данные
        shuffled_data = data.sample(frac=1)
        
        prepared_data = analyzer.prepare_data(shuffled_data)
        
        # Проверяем, что данные отсортированы
        assert prepared_data.index.equals(data.index)
        assert len(prepared_data) == len(data)
    
    def test_supported_analysis_types(self):
        """Тест поддерживаемых типов анализа."""
        assert isinstance(SUPPORTED_ANALYSIS_TYPES, dict)
        
        expected_types = ['statistical', 'zones', 'technical', 'chart', 'candlestick', 'timeseries']
        for analysis_type in expected_types:
            assert analysis_type in SUPPORTED_ANALYSIS_TYPES
            assert isinstance(SUPPORTED_ANALYSIS_TYPES[analysis_type], str)
    
    def test_get_available_analyzers(self):
        """Тест получения списка доступных анализаторов."""
        analyzers = get_available_analyzers()
        
        assert isinstance(analyzers, dict)
        assert len(analyzers) > 0
        
        # Проверяем, что есть базовые анализаторы
        assert 'statistical' in analyzers
        assert 'zone' in analyzers
    
    def test_create_analyzer_factory(self):
        """Тест фабрики создания анализаторов."""
        # Тест создания поддерживаемого анализатора
        analyzer = create_analyzer('statistical', param1='value1')
        
        assert isinstance(analyzer, BaseAnalyzer)
        assert analyzer.name == 'statistical'
        assert 'param1' in analyzer.config
        
        # Тест создания неподдерживаемого анализатора
        with pytest.raises(ValueError, match="Unsupported analyzer type"):
            create_analyzer('unsupported_type')


class TestStatisticalAnalysis:
    """Тесты статистического анализа."""
    
    def test_statistical_analyzer_import(self):
        """Тест импорта статистического анализатора."""
        from bquant.analysis.statistical import StatisticalAnalyzer
        from bquant.analysis.statistical import get_statistical_analyzers
        
        assert StatisticalAnalyzer is not None
        assert callable(get_statistical_analyzers)
    
    def test_statistical_analyzer_creation(self):
        """Тест создания статистического анализатора."""
        from bquant.analysis.statistical import StatisticalAnalyzer
        
        analyzer = StatisticalAnalyzer({'alpha': 0.01})
        
        assert analyzer.name == 'StatisticalAnalyzer'
        assert analyzer.default_alpha == 0.01
        assert hasattr(analyzer, 'min_sample_size')
    
    def test_statistical_quick_functions(self):
        """Тест быстрых функций статистического анализа."""
        from bquant.analysis.statistical import quick_stats, test_normality
        
        # Создаем тестовые данные
        np.random.seed(42)
        normal_data = pd.Series(np.random.normal(0, 1, 100))
        
        # Тест быстрых статистик
        stats = quick_stats(normal_data)
        assert isinstance(stats, dict)
        assert 'mean' in stats
        assert 'std' in stats
        assert 'count' in stats
        
        # Тест нормальности
        is_normal = test_normality(normal_data)
        assert isinstance(is_normal, bool)


class TestZoneAnalysis:
    """Тесты анализа зон."""
    
    def test_zone_analyzer_import(self):
        """Тест импорта анализатора зон."""
        from bquant.analysis.zones import Zone, ZoneAnalyzer
        from bquant.analysis.zones import get_zone_analyzers
        
        assert Zone is not None
        assert ZoneAnalyzer is not None
        assert callable(get_zone_analyzers)
    
    def test_zone_creation(self):
        """Тест создания зоны."""
        from bquant.analysis.zones import Zone
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        
        zone = Zone(
            zone_id='test_zone_1',
            zone_type='support',
            start_time=start_time,
            end_time=end_time,
            start_price=100.0,
            end_price=102.0,
            strength=0.8,
            confidence=0.9
        )
        
        assert zone.zone_id == 'test_zone_1'
        assert zone.zone_type == 'support'
        assert zone.duration == timedelta(hours=2)
        assert zone.price_range == 2.0
        assert zone.mid_price == 101.0
    
    def test_zone_to_dict(self):
        """Тест конвертации зоны в словарь."""
        from bquant.analysis.zones import Zone
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        zone = Zone(
            zone_id='test_zone',
            zone_type='resistance',
            start_time=start_time,
            end_time=end_time,
            start_price=200.0,
            end_price=205.0
        )
        
        zone_dict = zone.to_dict()
        
        assert isinstance(zone_dict, dict)
        assert 'zone_id' in zone_dict
        assert 'zone_type' in zone_dict
        assert 'start_time' in zone_dict
        assert 'end_time' in zone_dict
        assert 'duration_hours' in zone_dict
        assert 'price_range' in zone_dict
        assert 'mid_price' in zone_dict
    
    def test_zone_analyzer_creation(self):
        """Тест создания анализатора зон."""
        from bquant.analysis.zones import ZoneAnalyzer
        
        config = {
            'min_zone_duration': 3,
            'min_strength_threshold': 0.4,
            'min_confidence_threshold': 0.6
        }
        
        analyzer = ZoneAnalyzer(config)
        
        assert analyzer.name == 'ZoneAnalyzer'
        assert analyzer.min_zone_duration == 3
        assert analyzer.min_strength_threshold == 0.4
        assert analyzer.min_confidence_threshold == 0.6


class TestStubModules:
    """Тесты заглушек модулей анализа."""
    
    def test_technical_analyzer_stub(self):
        """Тест заглушки технического анализатора."""
        from bquant.analysis.technical import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer()
        
        # Создаем тестовые данные
        data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        result = analyzer.analyze(data)
        
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == 'technical'
        assert 'status' in result.results
        assert result.results['status'] == 'stub_implementation'
    
    def test_chart_analyzer_stub(self):
        """Тест заглушки анализатора графиков."""
        from bquant.analysis.chart import ChartAnalyzer
        
        analyzer = ChartAnalyzer()
        
        data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103]
        })
        
        result = analyzer.analyze(data)
        
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == 'chart'
        assert result.results['status'] == 'stub_implementation'
    
    def test_candlestick_analyzer_stub(self):
        """Тест заглушки анализатора свечей."""
        from bquant.analysis.candlestick import CandlestickAnalyzer
        
        analyzer = CandlestickAnalyzer()
        
        data = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102]
        })
        
        result = analyzer.analyze(data)
        
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == 'candlestick'
        assert result.results['status'] == 'stub_implementation'
    
    def test_timeseries_analyzer_stub(self):
        """Тест заглушки анализатора временных рядов."""
        from bquant.analysis.timeseries import TimeseriesAnalyzer
        
        analyzer = TimeseriesAnalyzer()
        
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        data = pd.DataFrame({
            'value': [100, 101, 102, 103, 104]
        }, index=dates)
        
        result = analyzer.analyze(data)
        
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == 'timeseries'
        assert result.results['status'] == 'stub_implementation'


def create_test_ohlcv_data(rows: int = 100) -> pd.DataFrame:
    """
    Создает тестовые OHLCV данные.
    
    Args:
        rows: Количество строк данных
    
    Returns:
        DataFrame с OHLCV данными
    """
    np.random.seed(42)
    
    dates = pd.date_range('2024-01-01', periods=rows, freq='H')
    
    # Генерируем цены с небольшой волатильностью
    base_price = 100.0
    price_changes = np.random.normal(0, 0.01, rows)
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))
    
    data = []
    for i, (timestamp, close) in enumerate(zip(dates, prices)):
        # Генерируем OHLC
        volatility = 0.005
        high = close * (1 + abs(np.random.normal(0, volatility)))
        low = close * (1 - abs(np.random.normal(0, volatility)))
        
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1] * (1 + np.random.normal(0, volatility * 0.5))
        
        # Корректируем OHLC
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = abs(np.random.normal(10000, 2000))
        
        data.append({
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': int(volume)
        })
    
    df = pd.DataFrame(data, index=dates)
    return df


class TestIntegrationAnalysis:
    """Интеграционные тесты анализа."""
    
    @pytest.fixture
    def test_data(self):
        """Создание тестовых данных."""
        return create_test_ohlcv_data(100)
    
    def test_statistical_analysis_integration(self, test_data):
        """Интеграционный тест статистического анализа."""
        from bquant.analysis.statistical import StatisticalAnalyzer
        
        analyzer = StatisticalAnalyzer()
        result = analyzer.analyze(test_data)
        
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == 'statistical'
        assert len(result.results) > 0
        assert result.data_size == len(test_data)
        
        # Проверяем, что анализ включает все числовые колонки
        numeric_columns = test_data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            assert col in result.results
            assert 'descriptive' in result.results[col]
            assert 'normality' in result.results[col]
    
    def test_zone_analysis_integration(self, test_data):
        """Интеграционный тест анализа зон."""
        from bquant.analysis.zones import ZoneAnalyzer
        
        analyzer = ZoneAnalyzer({'min_zone_duration': 2})
        result = analyzer.analyze(test_data)
        
        assert isinstance(result, AnalysisResult)
        assert result.analysis_type == 'zones'
        assert 'zones' in result.results
        assert 'zone_count' in result.results['zones']
        assert result.data_size == len(test_data)
    
    def test_analysis_result_save_csv(self, test_data, tmp_path):
        """Тест сохранения результатов анализа в CSV."""
        from bquant.analysis.statistical import StatisticalAnalyzer
        
        analyzer = StatisticalAnalyzer()
        result = analyzer.analyze(test_data)
        
        # Сохраняем результаты
        csv_path = tmp_path / "analysis_results.csv"
        result.save_to_csv(str(csv_path))
        
        # Проверяем, что файл создан
        assert csv_path.exists()
        
        # Читаем файл и проверяем содержимое
        saved_data = pd.read_csv(csv_path)
        assert len(saved_data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
