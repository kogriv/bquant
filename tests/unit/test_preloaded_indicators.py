"""
Тесты для PRELOADED индикаторов.

Проверяет корректность работы MACDPreloadedIndicator после рефакторинга.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.indicators import MACDPreloadedIndicator


class TestMACDPreloadedIndicator:
    """Тесты для MACDPreloadedIndicator."""
    
    def test_import_from_preloaded_module(self):
        """Тест импорта из preloaded модуля."""
        try:
            from bquant.indicators.preloaded import MACDPreloadedIndicator
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из preloaded модуля: {e}")
    
    def test_import_from_main_module(self):
        """Тест импорта из главного модуля."""
        try:
            from bquant.indicators import MACDPreloadedIndicator
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из главного модуля: {e}")
    
    def test_default_object_creation(self):
        """Тест создания объекта по умолчанию."""
        macd_default = MACDPreloadedIndicator()
        assert macd_default.name == "macd_preloaded"
        assert isinstance(macd_default.get_default_columns(), list)
    
    def test_custom_columns_object_creation(self):
        """Тест создания объекта с кастомными колонками."""
        macd_custom = MACDPreloadedIndicator(required_columns=['macd', 'signal', 'histogram'])
        assert macd_custom.name == "macd_preloaded"
        assert macd_custom.get_required_columns() == ['macd', 'signal']
    
    def test_class_methods(self):
        """Тест классных методов."""
        default_cols = MACDPreloadedIndicator.get_default_columns()
        assert isinstance(default_cols, list)
        assert len(default_cols) > 0
        
        info = MACDPreloadedIndicator.get_info()
        assert 'name' in info
        assert 'type' in info
        assert 'description' in info
    
    def test_data_validation(self):
        """Тест валидации данных."""
        macd_default = MACDPreloadedIndicator()
        
        # Валидные данные
        valid_data = pd.DataFrame({
            'macd': [1.0, 1.1, 1.2, 1.3, 1.4],
            'signal': [0.9, 1.0, 1.1, 1.2, 1.3],
            'histogram': [0.1, 0.1, 0.1, 0.1, 0.1]
        })
        
        validation = macd_default.validate_data(valid_data)
        assert validation is True
    
    def test_calculation(self):
        """Тест расчета."""
        macd_default = MACDPreloadedIndicator()
        
        test_data = pd.DataFrame({
            'macd': [1.0, 1.1, 1.2, 1.3, 1.4],
            'signal': [0.9, 1.0, 1.1, 1.2, 1.3],
            'histogram': [0.1, 0.1, 0.1, 0.1, 0.1]
        })
        
        result = macd_default.calculate(test_data)
        assert hasattr(result, 'data')
        assert len(result.data) == len(test_data)
    
    def test_statistics(self):
        """Тест получения статистики."""
        macd_default = MACDPreloadedIndicator()
        
        test_data = pd.DataFrame({
            'macd': [1.0, 1.1, 1.2, 1.3, 1.4],
            'signal': [0.9, 1.0, 1.1, 1.2, 1.3],
            'histogram': [0.1, 0.1, 0.1, 0.1, 0.1]
        })
        
        stats = macd_default.get_statistics(test_data)
        assert isinstance(stats, dict)
        assert len(stats) > 0
    
    def test_trend_detection(self):
        """Тест определения трендов."""
        macd_default = MACDPreloadedIndicator()
        
        test_data = pd.DataFrame({
            'macd': [1.0, 1.1, 1.2, 1.3, 1.4],
            'signal': [0.9, 1.0, 1.1, 1.2, 1.3],
            'histogram': [0.1, 0.1, 0.1, 0.1, 0.1]
        })
        
        trend_up = macd_default.is_trending_up(test_data)
        trend_down = macd_default.is_trending_down(test_data)
        
        assert isinstance(trend_up, (bool, np.bool_))
        assert isinstance(trend_down, (bool, np.bool_))
    
    def test_crossovers(self):
        """Тест определения пересечений."""
        macd_default = MACDPreloadedIndicator()
        
        test_data = pd.DataFrame({
            'macd': [1.0, 1.1, 1.2, 1.3, 1.4],
            'signal': [0.9, 1.0, 1.1, 1.2, 1.3],
            'histogram': [0.1, 0.1, 0.1, 0.1, 0.1]
        })
        
        crossovers = macd_default.get_crossovers(test_data)
        assert 'bullish_crossovers' in crossovers
        assert 'bearish_crossovers' in crossovers
        assert isinstance(crossovers['bullish_crossovers'], (int, np.integer))
        assert isinstance(crossovers['bearish_crossovers'], (int, np.integer))
