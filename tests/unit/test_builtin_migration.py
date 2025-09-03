"""
Тесты для проверки миграции builtin индикаторов.

Проверяет корректность работы builtin индикаторов после рефакторинга.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.indicators import (
    SimpleMovingAverage, ExponentialMovingAverage,
    RelativeStrengthIndex, MACD, BollingerBands
)


class TestBuiltinIndicatorsMigration:
    """Тесты для проверки миграции builtin индикаторов."""
    
    def test_sma_import_and_creation(self):
        """Тест импорта и создания SMA."""
        try:
            from bquant.indicators.custom import SimpleMovingAverage
            assert SimpleMovingAverage is not None
            
            # Создаем индикатор
            sma = SimpleMovingAverage(period=20)
            assert sma.name == "sma"
            assert sma.period == 20
            
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать SMA: {e}")
    
    def test_ema_import_and_creation(self):
        """Тест импорта и создания EMA."""
        try:
            from bquant.indicators.custom import ExponentialMovingAverage
            assert ExponentialMovingAverage is not None
            
            # Создаем индикатор
            ema = ExponentialMovingAverage(period=20)
            assert ema.name == "ema"
            assert ema.period == 20
            
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать EMA: {e}")
    
    def test_rsi_import_and_creation(self):
        """Тест импорта и создания RSI."""
        try:
            from bquant.indicators.custom import RelativeStrengthIndex
            assert RelativeStrengthIndex is not None
            
            # Создаем индикатор
            rsi = RelativeStrengthIndex(period=14)
            assert rsi.name == "rsi"
            assert rsi.period == 14
            
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать RSI: {e}")
    
    def test_macd_import_and_creation(self):
        """Тест импорта и создания MACD."""
        try:
            from bquant.indicators.custom import MACD
            assert MACD is not None
            
            # Создаем индикатор
            macd = MACD(fast_period=12, slow_period=26, signal_period=9)
            assert macd.name == "macd"
            assert macd.fast_period == 12
            assert macd.slow_period == 26
            assert macd.signal_period == 9
            
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать MACD: {e}")
    
    def test_bbands_import_and_creation(self):
        """Тест импорта и создания Bollinger Bands."""
        try:
            from bquant.indicators.custom import BollingerBands
            assert BollingerBands is not None
            
            # Создаем индикатор
            bbands = BollingerBands(period=20, std_dev=2.0)
            assert bbands.name == "bbands"
            assert bbands.period == 20
            assert bbands.std_dev == 2.0
            
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать Bollinger Bands: {e}")
    
    def test_sma_calculation(self):
        """Тест расчета SMA."""
        sma = SimpleMovingAverage(period=5)
        
        # Создаем тестовые данные
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        
        # Вычисляем результат
        result = sma.calculate(test_data)
        
        # Проверяем результат
        assert result is not None
        assert hasattr(result, 'data')
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == len(test_data)
        assert 'sma_5' in result.data.columns
        
        # Проверяем, что первые 4 значения NaN (недостаточно данных для SMA с периодом 5)
        assert pd.isna(result.data['sma_5'].iloc[0:4]).all()
        
        # Проверяем, что 5-е значение вычислено
        assert not pd.isna(result.data['sma_5'].iloc[4])
    
    def test_ema_calculation(self):
        """Тест расчета EMA."""
        ema = ExponentialMovingAverage(period=5)
        
        # Создаем тестовые данные
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        
        # Вычисляем результат
        result = ema.calculate(test_data)
        
        # Проверяем результат
        assert result is not None
        assert hasattr(result, 'data')
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == len(test_data)
        assert 'ema_5' in result.data.columns
        
        # Проверяем, что все значения вычислены (EMA не имеет NaN в начале)
        assert not result.data['ema_5'].isna().all()
    
    def test_rsi_calculation(self):
        """Тест расчета RSI."""
        rsi = RelativeStrengthIndex(period=5)
        
        # Создаем тестовые данные
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        
        # Вычисляем результат
        result = rsi.calculate(test_data)
        
        # Проверяем результат
        assert result is not None
        assert hasattr(result, 'data')
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == len(test_data)
        assert 'rsi_5' in result.data.columns
        
        # Проверяем, что RSI находится в диапазоне [0, 100]
        rsi_values = result.data['rsi_5'].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()
    
    def test_macd_calculation(self):
        """Тест расчета MACD."""
        macd = MACD(fast_period=5, slow_period=10, signal_period=3)
        
        # Создаем тестовые данные
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]
        })
        
        # Вычисляем результат
        result = macd.calculate(test_data)
        
        # Проверяем результат
        assert result is not None
        assert hasattr(result, 'data')
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == len(test_data)
        
        # Проверяем наличие колонок MACD
        assert 'macd' in result.data.columns
        assert 'macd_signal' in result.data.columns
        assert 'macd_hist' in result.data.columns
    
    def test_bbands_calculation(self):
        """Тест расчета Bollinger Bands."""
        bbands = BollingerBands(period=5, std_dev=2.0)
        
        # Создаем тестовые данные
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        
        # Вычисляем результат
        result = bbands.calculate(test_data)
        
        # Проверяем результат
        assert result is not None
        assert hasattr(result, 'data')
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == len(test_data)
        
        # Проверяем наличие колонок Bollinger Bands
        assert 'bb_upper' in result.data.columns
        assert 'bb_middle' in result.data.columns
        assert 'bb_lower' in result.data.columns
    
    def test_indicator_factory_registration(self):
        """Тест регистрации индикаторов в фабрике."""
        from bquant.indicators import IndicatorFactory
        
        # Проверяем, что builtin индикаторы зарегистрированы
        available_indicators = IndicatorFactory.list_indicators()
        
        # Проверяем наличие основных индикаторов
        assert 'sma' in available_indicators
        assert 'ema' in available_indicators
        assert 'rsi' in available_indicators
        assert 'macd' in available_indicators
        assert 'bbands' in available_indicators
    
    def test_indicator_factory_creation(self):
        """Тест создания индикаторов через фабрику."""
        from bquant.indicators import IndicatorFactory
        
        # Создаем индикаторы через фабрику
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        ema = IndicatorFactory.create('custom', 'ema', period=20)
        rsi = IndicatorFactory.create('custom', 'rsi', period=14)
        
        # Проверяем, что индикаторы созданы
        assert sma is not None
        assert ema is not None
        assert rsi is not None
        
        # Проверяем типы
        assert isinstance(sma, SimpleMovingAverage)
        assert isinstance(ema, ExponentialMovingAverage)
        assert isinstance(rsi, RelativeStrengthIndex)
    
    def test_indicator_methods_consistency(self):
        """Тест консистентности методов индикаторов."""
        # Создаем индикаторы
        sma = SimpleMovingAverage(period=20)
        ema = ExponentialMovingAverage(period=20)
        rsi = RelativeStrengthIndex(period=14)
        
        # Проверяем, что все индикаторы имеют одинаковый интерфейс
        common_methods = [
            'calculate', 'validate_data', 'get_statistics',
            'get_required_columns', 'get_output_columns',
            'get_description', 'get_info'
        ]
        
        for indicator in [sma, ema, rsi]:
            for method in common_methods:
                assert hasattr(indicator, method), f"Индикатор {indicator.__class__.__name__} не имеет метода {method}"
    
    def test_data_validation_consistency(self):
        """Тест консистентности валидации данных."""
        # Создаем индикаторы
        sma = SimpleMovingAverage(period=20)
        ema = ExponentialMovingAverage(period=20)
        
        # Валидные данные
        valid_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                      110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120]
        })
        
        # Проверяем валидацию
        assert sma.validate_data(valid_data) is True
        assert ema.validate_data(valid_data) is True
        
        # Невалидные данные
        invalid_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104]
        })
        
        # Проверяем, что валидация отклоняет невалидные данные
        assert sma.validate_data(invalid_data) is False
        assert ema.validate_data(invalid_data) is False
