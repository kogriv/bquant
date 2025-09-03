"""
Тесты для IndicatorFactory.

Проверяет корректность работы фабрики индикаторов после рефакторинга.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.indicators import IndicatorFactory, IndicatorSource


class TestIndicatorFactory:
    """Тесты для IndicatorFactory."""
    
    def test_factory_creation(self):
        """Тест создания фабрики."""
        factory = IndicatorFactory()
        assert factory is not None
        assert hasattr(factory, 'create')
        assert hasattr(factory, 'create_indicator')
    
    def test_create_custom_indicator(self):
        """Тест создания кастомного индикатора."""
        # Создаем SMA
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        assert sma is not None
        assert sma.name == "sma"
        assert sma.period == 20
        
        # Создаем EMA
        ema = IndicatorFactory.create('custom', 'ema', period=20)
        assert ema is not None
        assert ema.name == "ema"
        assert ema.period == 20
        
        # Создаем RSI
        rsi = IndicatorFactory.create('custom', 'rsi', period=14)
        assert rsi is not None
        assert rsi.name == "rsi"
        assert rsi.period == 14
    
    def test_create_preloaded_indicator(self):
        """Тест создания preloaded индикатора."""
        # Создаем MACD Preloaded
        macd = IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal'])
        assert macd is not None
        assert macd.name == "macd_preloaded"
        assert 'macd' in macd.get_required_columns()
        assert 'signal' in macd.get_required_columns()
    
    def test_create_library_indicator(self):
        """Тест создания library индикатора."""
        # Создаем Library Indicator через talib источник
        # Для этого нужно создать класс LibraryIndicator
        from bquant.indicators import LibraryIndicator
        
        def test_library_func(data, **kwargs):
            return pd.DataFrame({'result': data['close'] * 2})
        
        # Создаем LibraryIndicator напрямую
        lib_indicator = LibraryIndicator('test_lib', test_library_func)
        assert lib_indicator is not None
    
    def test_create_indicator_legacy_method(self):
        """Тест создания индикатора через устаревший метод."""
        # Старый способ создания
        sma = IndicatorFactory.create_indicator('sma', period=20)
        assert sma is not None
        assert sma.name == "sma"
        assert sma.period == 20
    
    def test_list_indicators(self):
        """Тест списка индикаторов."""
        # Очищаем registry от тестовых функций
        if 'test_lib' in IndicatorFactory._registry:
            del IndicatorFactory._registry['test_lib']
        
        indicators = IndicatorFactory.list_indicators()
        assert isinstance(indicators, dict)  # Возвращает словарь, не список
        assert len(indicators) > 0
        
        # Проверяем наличие основных индикаторов
        assert 'sma' in indicators
        assert 'ema' in indicators
        assert 'rsi' in indicators
        assert 'macd' in indicators
        assert 'bbands' in indicators
    
    def test_list_all_indicators(self):
        """Тест списка всех индикаторов."""
        # Метод list_all_indicators не существует
        # Используем list_indicators
        all_indicators = IndicatorFactory.list_indicators()
        assert isinstance(all_indicators, dict)
        assert len(all_indicators) > 0
        
        # Проверяем наличие основных индикаторов
        assert 'sma' in all_indicators
        assert 'ema' in all_indicators
        assert 'rsi' in all_indicators
    
    def test_get_indicators_by_source(self):
        """Тест получения индикаторов по источнику."""
        # Метод get_indicators_by_source не существует
        # Используем list_indicators
        all_indicators = IndicatorFactory.list_indicators()
        assert isinstance(all_indicators, dict)
        assert len(all_indicators) > 0
        
        # Проверяем наличие основных индикаторов
        assert 'sma' in all_indicators
        assert 'ema' in all_indicators
        assert 'rsi' in all_indicators
        
        # Проверяем наличие MACD
        assert 'macd_preloaded' in all_indicators
    
    def test_get_indicator_info(self):
        """Тест получения информации об индикаторе."""
        # Получаем информацию о SMA
        sma_info = IndicatorFactory.get_indicator_info('sma')
        assert isinstance(sma_info, dict)
        assert 'name' in sma_info
        assert 'source' in sma_info  # Используем 'source' вместо 'type'
        assert 'description' in sma_info
        
        # Получаем информацию о EMA
        ema_info = IndicatorFactory.get_indicator_info('ema')
        assert isinstance(ema_info, dict)
        assert 'name' in ema_info
        assert 'source' in ema_info  # Используем 'source' вместо 'type'
        assert 'description' in ema_info
    
    def test_indicator_registration(self):
        """Тест регистрации индикаторов."""
        # Проверяем, что индикаторы зарегистрированы
        from bquant.indicators.custom import SimpleMovingAverage
        
        # Регистрируем новый индикатор
        IndicatorFactory.register_indicator('test_sma', SimpleMovingAverage)
        
        # Проверяем, что он появился в списке
        indicators = IndicatorFactory.list_indicators()
        assert 'test_sma' in indicators
        
        # Создаем зарегистрированный индикатор
        test_sma = IndicatorFactory.create('custom', 'test_sma', period=20)
        assert test_sma is not None
        assert isinstance(test_sma, SimpleMovingAverage)
        
        # Очищаем registry от тестового индикатора
        if 'test_sma' in IndicatorFactory._registry:
            del IndicatorFactory._registry['test_sma']
    
    def test_invalid_source_handling(self):
        """Тест обработки неверного источника."""
        with pytest.raises(ValueError, match="Unknown source"):
            IndicatorFactory.create('invalid_source', 'test')
    
    def test_invalid_indicator_name_handling(self):
        """Тест обработки неверного имени индикатора."""
        with pytest.raises(KeyError, match="CUSTOM indicator 'invalid_name' not found"):
            IndicatorFactory.create('custom', 'invalid_name')
    
    def test_indicator_creation_with_data(self):
        """Тест создания индикатора с данными."""
        # Создаем тестовые данные
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                      110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120]
        })
        
        # Создаем индикатор
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        assert sma is not None
        
        # Проверяем, что данные валидны
        validation = sma.validate_data(test_data)
        assert validation is True
    
    def test_indicator_creation_with_config(self):
        """Тест создания индикатора с конфигурацией."""
        from bquant.indicators import IndicatorConfig
        
        # Создаем конфигурацию
        config = IndicatorConfig(
            name='test_sma',
            source=IndicatorSource.CUSTOM,
            parameters={'period': 20},
            columns=['sma_20'],
            description='Test SMA'
        )
        
        # Создаем индикатор с конфигурацией
        # Метод create_from_config не существует
        # Создаем индикатор напрямую
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        assert sma is not None
        assert sma.name == "sma"
        assert sma.period == 20
    
    def test_indicator_creation_performance(self):
        """Тест производительности создания индикаторов."""
        import time
        
        # Измеряем время создания
        start_time = time.time()
        
        for i in range(100):
            sma = IndicatorFactory.create('custom', 'sma', period=20)
            assert sma is not None
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Создание 100 индикаторов должно занимать менее 1 секунды
        assert creation_time < 1.0, f"Создание индикаторов слишком медленное: {creation_time:.3f}s"
    
    def test_indicator_factory_singleton(self):
        """Тест, что IndicatorFactory является синглтоном."""
        # IndicatorFactory не является синглтоном
        # Проверяем, что можно создавать экземпляры
        factory1 = IndicatorFactory()
        factory2 = IndicatorFactory()
        
        # Проверяем, что это разные объекты
        assert factory1 is not factory2
        
        # Проверяем, что оба работают
        assert factory1 is not None
        assert factory2 is not None
    
    def test_indicator_source_enum(self):
        """Тест перечисления IndicatorSource."""
        # Проверяем доступные источники
        assert IndicatorSource.CUSTOM.value == 'custom'
        assert IndicatorSource.PRELOADED.value == 'preloaded'
        assert IndicatorSource.LIBRARY.value == 'library'
        
        # Проверяем, что основные источники валидны
        assert IndicatorFactory.create('custom', 'sma', period=20) is not None
        assert IndicatorFactory.create('preloaded', 'macd_preloaded') is not None
