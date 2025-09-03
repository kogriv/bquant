"""
Тесты валидации архитектуры индикаторов - Этап 8

Комплексное тестирование всей архитектуры, включая:
- Наследование и полиморфизм
- Единообразный интерфейс
- Совместимость с существующим кодом
- Производительность и надежность
"""

import time
import pandas as pd
import numpy as np
import pytest
from typing import List, Dict, Any

from bquant.indicators import (
    BaseIndicator, PreloadedIndicator, CustomIndicator, LibraryIndicator,
    IndicatorFactory, IndicatorSource
)


def create_test_data(rows: int = 100) -> pd.DataFrame:
    """Создание тестовых данных."""
    dates = pd.date_range('2024-01-01', periods=rows, freq='D')
    np.random.seed(42)
    
    test_data = pd.DataFrame({
        'open': 100 + np.random.randn(rows).cumsum(),
        'high': 100 + np.random.randn(rows).cumsum() + 2,
        'low': 100 + np.random.randn(rows).cumsum() - 2,
        'close': 100 + np.random.randn(rows).cumsum(),
        'volume': np.random.randint(1000, 10000, rows),
        'macd': np.random.randn(rows).cumsum(),
        'signal': np.random.randn(rows).cumsum()
    }, index=dates)
    
    return test_data


class TestArchitectureInheritance:
    """Тесты архитектуры наследования."""
    
    def test_inheritance_hierarchy(self):
        """Тестирует правильность архитектуры наследования."""
        # Проверяем иерархию наследования
        assert issubclass(PreloadedIndicator, BaseIndicator), "PreloadedIndicator должен наследоваться от BaseIndicator"
        assert issubclass(CustomIndicator, BaseIndicator), "CustomIndicator должен наследоваться от BaseIndicator"
        assert issubclass(LibraryIndicator, BaseIndicator), "LibraryIndicator должен наследоваться от BaseIndicator"
        
        # Проверяем, что это разные классы
        assert PreloadedIndicator != CustomIndicator, "PreloadedIndicator и CustomIndicator должны быть разными классами"
        assert CustomIndicator != LibraryIndicator, "CustomIndicator и LibraryIndicator должны быть разными классами"
        assert PreloadedIndicator != LibraryIndicator, "PreloadedIndicator и LibraryIndicator должны быть разными классами"
    
    def test_abstract_methods(self):
        """Тестирует наличие абстрактных методов."""
        # Проверяем, что BaseIndicator имеет абстрактный метод calculate
        assert hasattr(BaseIndicator, 'calculate'), "BaseIndicator должен иметь метод calculate"
        
        # Проверяем, что CustomIndicator имеет специфичные методы
        assert hasattr(CustomIndicator, 'get_output_columns'), "CustomIndicator должен иметь метод get_output_columns"
        assert hasattr(CustomIndicator, 'get_description'), "CustomIndicator должен иметь метод get_description"


class TestUnifiedInterface:
    """Тесты единообразного интерфейса."""
    
    def test_common_methods(self):
        """Тестирует наличие общих методов у всех типов индикаторов."""
        # Создаем индикаторы разных типов
        preloaded = IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal'])
        custom_sma = IndicatorFactory.create('custom', 'sma', period=20)
        custom_ema = IndicatorFactory.create('custom', 'ema', period=20)
        
        indicators = {
            'preloaded': preloaded,
            'custom_sma': custom_sma,
            'custom_ema': custom_ema,
        }
        
        # Проверяем наличие общих методов
        common_methods = ['calculate', 'validate_data', 'get_statistics', 'get_required_columns']
        for name, indicator in indicators.items():
            for method in common_methods:
                assert hasattr(indicator, method), f"Индикатор {name} должен иметь метод {method}"
    
    def test_interface_consistency(self):
        """Тестирует консистентность интерфейса."""
        # Все индикаторы должны иметь одинаковый базовый интерфейс
        preloaded = IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal'])
        custom = IndicatorFactory.create('custom', 'sma', period=20)
        
        assert hasattr(preloaded, 'calculate'), "Все индикаторы должны иметь метод calculate"
        assert hasattr(custom, 'calculate'), "Все индикаторы должны иметь метод calculate"
        assert hasattr(preloaded, 'validate_data'), "Все индикаторы должны иметь метод validate_data"
        assert hasattr(custom, 'validate_data'), "Все индикаторы должны иметь метод validate_data"


class TestPolymorphism:
    """Тесты полиморфизма."""
    
    def test_polymorphic_behavior(self):
        """Тестирует полиморфизм - одинаковое поведение разных типов индикаторов."""
        test_data = create_test_data(100)
        
        # Создаем индикаторы разных типов
        indicators = [
            IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal']),
            IndicatorFactory.create('custom', 'sma', period=20),
            IndicatorFactory.create('custom', 'ema', period=20),
        ]
        
        # Тестируем одинаковое поведение
        for i, indicator in enumerate(indicators):
            # Все должны уметь валидировать данные
            is_valid = indicator.validate_data(test_data)
            assert isinstance(is_valid, bool), f"validate_data должен возвращать bool для индикатора {i+1}"
            
            # Все должны уметь рассчитывать
            result = indicator.calculate(test_data)
            assert hasattr(result, 'data'), f"Результат индикатора {i+1} должен иметь атрибут data"
            assert hasattr(result, 'config'), f"Результат индикатора {i+1} должен иметь атрибут config"
            assert hasattr(result, 'metadata'), f"Результат индикатора {i+1} должен иметь атрибут metadata"
            
            # Все должны уметь давать статистику
            stats = indicator.get_statistics(test_data)
            assert isinstance(stats, (pd.DataFrame, dict)), f"get_statistics должен возвращать DataFrame или dict для индикатора {i+1}"


class TestPerformance:
    """Тесты производительности."""
    
    def test_calculation_performance(self):
        """Тестирует производительность расчета индикаторов."""
        test_data = create_test_data(100)
        
        # Создаем индикаторы для тестирования
        indicators = [
            ('preloaded_macd', IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal'])),
            ('custom_sma', IndicatorFactory.create('custom', 'sma', period=20)),
            ('custom_ema', IndicatorFactory.create('custom', 'ema', period=20)),
        ]
        
        # Тестируем производительность расчета
        for name, indicator in indicators:
            # Замеряем время расчета
            start_time = time.time()
            result = indicator.calculate(test_data)
            calc_time = time.time() - start_time
            
            # Проверяем, что время выполнения разумное
            assert calc_time < 1.0, f"Расчет {name} занимает слишком много времени: {calc_time} сек"
            
            # Замеряем время валидации
            start_time = time.time()
            is_valid = indicator.validate_data(test_data)
            valid_time = time.time() - start_time
            
            assert valid_time < 0.1, f"Валидация {name} занимает слишком много времени: {valid_time} сек"
            
            # Замеряем время статистики
            start_time = time.time()
            stats = indicator.get_statistics(test_data)
            stats_time = time.time() - start_time
            
            assert stats_time < 0.1, f"Статистика {name} занимает слишком много времени: {stats_time} сек"


class TestCompatibility:
    """Тесты совместимости."""
    
    def test_backward_compatibility(self):
        """Тестирует обратную совместимость."""
        test_data = create_test_data(100)
        
        # Тестируем старый метод create_indicator (должен работать)
        old_sma = IndicatorFactory.create_indicator('sma', period=20)
        assert old_sma is not None, "Старый метод create_indicator должен работать"
        
        # Проверяем, что старый метод создает правильный объект
        assert hasattr(old_sma, 'calculate'), "Старый метод должен создавать объект с методом calculate"
        assert hasattr(old_sma, 'validate_data'), "Старый метод должен создавать объект с методом validate_data"
        
        # Проверяем, что старый метод работает
        result = old_sma.calculate(test_data)
        assert hasattr(result, 'data'), "Результат старого метода должен иметь атрибут data"
    
    def test_result_compatibility(self):
        """Тестирует совместимость результатов."""
        test_data = create_test_data(100)
        
        # Создаем индикаторы старым и новым способом
        old_sma = IndicatorFactory.create_indicator('sma', period=20)
        new_sma = IndicatorFactory.create('custom', 'sma', period=20)
        
        # Рассчитываем результаты
        old_result = old_sma.calculate(test_data)
        new_result = new_sma.calculate(test_data)
        
        # Проверяем, что результаты имеют одинаковую структуру
        assert old_result.data.shape == new_result.data.shape, "Результаты должны иметь одинаковую форму"
        assert list(old_result.data.columns) == list(new_result.data.columns), "Названия колонок должны совпадать"
        
        # Проверяем, что данные не пустые
        assert len(old_result.data) > 0, "Старый результат не должен быть пустым"
        assert len(new_result.data) > 0, "Новый результат не должен быть пустым"


class TestErrorHandling:
    """Тесты обработки ошибок."""
    
    def test_unknown_source(self):
        """Тестирует обработку неизвестного источника."""
        with pytest.raises(ValueError):
            IndicatorFactory.create('unknown', 'sma')
    
    def test_unknown_indicator(self):
        """Тестирует обработку неизвестного индикатора."""
        with pytest.raises(KeyError):
            IndicatorFactory.create('custom', 'unknown_indicator')
    
    def test_invalid_parameters(self):
        """Тестирует обработку неправильных параметров."""
        # Индикатор должен корректно обрабатывать лишние параметры
        try:
            IndicatorFactory.create('custom', 'sma', period=20, invalid_param='value')
        except Exception as e:
            # Ошибка должна быть понятной
            assert 'invalid_param' in str(e) or 'unexpected' in str(e)


class TestExtensibility:
    """Тесты расширяемости архитектуры."""
    
    def test_indicator_listing(self):
        """Тестирует получение информации о всех индикаторах."""
        all_indicators = IndicatorFactory.list_indicators()
        assert isinstance(all_indicators, dict), "list_indicators должен возвращать словарь"
        assert len(all_indicators) > 0, "Должно быть зарегистрировано хотя бы несколько индикаторов"
        
        # Проверяем группировку по источникам
        sources = ['preloaded', 'custom', 'library']
        for source in sources:
            indicators = IndicatorFactory.get_indicators_by_source(source)
            assert isinstance(indicators, list), f"get_indicators_by_source('{source}') должен возвращать список"
    
    def test_indicator_info(self):
        """Тестирует получение детальной информации об индикаторах."""
        if 'sma' in IndicatorFactory.list_indicators():
            info = IndicatorFactory.get_indicator_info('sma')
            assert info is not None, "get_indicator_info должен возвращать информацию"
            assert 'source' in info, "Информация должна содержать источник"
            assert 'class' in info, "Информация должна содержать класс"
    
    def test_parameter_flexibility(self):
        """Тестирует гибкость параметров."""
        # Проверяем, что можно создавать индикаторы с разными параметрами
        sma_10 = IndicatorFactory.create('custom', 'sma', period=10)
        sma_50 = IndicatorFactory.create('custom', 'sma', period=50)
        
        assert sma_10.config.parameters['period'] == 10, "Параметр period должен быть 10"
        assert sma_50.config.parameters['period'] == 50, "Параметр period должен быть 50"


class TestIntegration:
    """Тесты интеграции всех типов индикаторов."""
    
    def test_all_indicator_types_integration(self):
        """Тестирует интеграцию всех типов индикаторов."""
        test_data = create_test_data(100)
        
        # Создаем индикаторы всех типов
        indicators = {
            'PRELOADED': IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal']),
            'CUSTOM_SMA': IndicatorFactory.create('custom', 'sma', period=20),
            'CUSTOM_EMA': IndicatorFactory.create('custom', 'ema', period=20),
            'CUSTOM_RSI': IndicatorFactory.create('custom', 'rsi', period=14),
        }
        
        # Пытаемся добавить LIBRARY индикаторы (если доступны)
        try:
            indicators['LIBRARY_PANDAS_TA'] = IndicatorFactory.create('pandas_ta', 'sma', length=20)
        except:
            pass
        
        try:
            indicators['LIBRARY_TALIB'] = IndicatorFactory.create('talib', 'sma', timeperiod=20)
        except:
            pass
        
        # Тестируем единообразный интерфейс
        for name, indicator in indicators.items():
            # Все должны уметь валидировать данные
            is_valid = indicator.validate_data(test_data)
            assert isinstance(is_valid, bool), f"Валидация {name} должна возвращать bool"
            
            # Все должны уметь рассчитывать
            result = indicator.calculate(test_data)
            assert hasattr(result, 'data'), f"Результат {name} должен иметь атрибут data"
            assert hasattr(result, 'config'), f"Результат {name} должен иметь атрибут config"
            assert hasattr(result, 'metadata'), f"Результат {name} должен иметь атрибут metadata"
            
            # Все должны уметь давать статистику
            stats = indicator.get_statistics(test_data)
            assert isinstance(stats, (pd.DataFrame, dict)), f"Статистика {name} должна быть DataFrame или dict"
    
    def test_indicator_factory_integration(self):
        """Тестирует интеграцию через IndicatorFactory."""
        # Проверяем, что можно получить информацию о всех индикаторах
        all_indicators = IndicatorFactory.list_indicators()
        assert len(all_indicators) > 0, "Должно быть зарегистрировано хотя бы несколько индикаторов"
        
        # Проверяем группировку по источникам
        for source in ['preloaded', 'custom', 'library']:
            indicators = IndicatorFactory.get_indicators_by_source(source)
            assert isinstance(indicators, list), f"Источник {source} должен возвращать список"
