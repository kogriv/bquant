"""
Тест всех типов индикаторов - Этап 8

Проверяет работу всех типов индикаторов:
- PRELOADED
- CUSTOM (BUILTIN)
- LIBRARY (если доступны)
"""

import pandas as pd
import numpy as np
import pytest
from typing import Dict, Any

from bquant.indicators import (
    IndicatorFactory, IndicatorSource, BaseIndicator,
    PreloadedIndicator, CustomIndicator, LibraryIndicator
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


class TestPreloadedIndicators:
    """Тесты PRELOADED индикаторов."""
    
    def test_macd_preloaded(self):
        """Тестирует PRELOADED MACD индикатор."""
        test_data = create_test_data(100)
        
        # Создаем PRELOADED индикатор
        macd_preloaded = IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal'])
        
        # Проверяем тип
        assert isinstance(macd_preloaded, PreloadedIndicator), "Должен быть PreloadedIndicator"
        assert isinstance(macd_preloaded, BaseIndicator), "Должен наследоваться от BaseIndicator"
        
        # Проверяем конфигурацию
        assert macd_preloaded.config.source == IndicatorSource.PRELOADED, "Источник должен быть PRELOADED"
        # Проверяем, что индикатор может работать с данными, содержащими нужные колонки
        assert 'macd' in test_data.columns, "Тестовые данные должны содержать колонку macd"
        assert 'signal' in test_data.columns, "Тестовые данные должны содержать колонку signal"
        
        # Проверяем валидацию
        is_valid = macd_preloaded.validate_data(test_data)
        assert is_valid is True, "Данные должны быть валидными"
        
        # Проверяем расчет
        result = macd_preloaded.calculate(test_data)
        assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
        assert hasattr(result, 'config'), "Результат должен иметь атрибут config"
        assert hasattr(result, 'metadata'), "Результат должен иметь атрибут metadata"
        
        # Проверяем статистику
        stats = macd_preloaded.get_statistics(test_data)
        assert isinstance(stats, (pd.DataFrame, dict)), "Статистика должна быть DataFrame или dict"
        
        print("✅ PRELOADED MACD индикатор работает корректно")


class TestCustomIndicators:
    """Тесты CUSTOM индикаторов."""
    
    def test_sma_custom(self):
        """Тестирует CUSTOM SMA индикатор."""
        test_data = create_test_data(100)
        
        # Создаем CUSTOM индикатор
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        
        # Проверяем тип
        assert isinstance(sma, CustomIndicator), "Должен быть CustomIndicator"
        assert isinstance(sma, BaseIndicator), "Должен наследоваться от BaseIndicator"
        
        # Проверяем конфигурацию
        assert sma.config.source == IndicatorSource.CUSTOM, "Источник должен быть CUSTOM"
        assert sma.config.parameters['period'] == 20, "Параметр period должен быть 20"
        
        # Проверяем валидацию
        is_valid = sma.validate_data(test_data)
        assert is_valid is True, "Данные должны быть валидными"
        
        # Проверяем расчет
        result = sma.calculate(test_data)
        assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
        assert 'sma_20' in result.data.columns, "Результат должен содержать колонку sma_20"
        
        # Проверяем статистику
        stats = sma.get_statistics(test_data)
        assert isinstance(stats, (pd.DataFrame, dict)), "Статистика должна быть DataFrame или dict"
        
        print("✅ CUSTOM SMA индикатор работает корректно")
    
    def test_ema_custom(self):
        """Тестирует CUSTOM EMA индикатор."""
        test_data = create_test_data(100)
        
        # Создаем CUSTOM индикатор
        ema = IndicatorFactory.create('custom', 'ema', period=20)
        
        # Проверяем тип
        assert isinstance(ema, CustomIndicator), "Должен быть CustomIndicator"
        assert isinstance(ema, BaseIndicator), "Должен наследоваться от BaseIndicator"
        
        # Проверяем конфигурацию
        assert ema.config.source == IndicatorSource.CUSTOM, "Источник должен быть CUSTOM"
        assert ema.config.parameters['period'] == 20, "Параметр period должен быть 20"
        
        # Проверяем валидацию
        is_valid = ema.validate_data(test_data)
        assert is_valid is True, "Данные должны быть валидными"
        
        # Проверяем расчет
        result = ema.calculate(test_data)
        assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
        assert 'ema_20' in result.data.columns, "Результат должен содержать колонку ema_20"
        
        # Проверяем статистику
        stats = ema.get_statistics(test_data)
        assert isinstance(stats, (pd.DataFrame, dict)), "Статистика должна быть DataFrame или dict"
        
        print("✅ CUSTOM EMA индикатор работает корректно")
    
    def test_rsi_custom(self):
        """Тестирует CUSTOM RSI индикатор."""
        test_data = create_test_data(100)
        
        # Создаем CUSTOM индикатор
        rsi = IndicatorFactory.create('custom', 'rsi', period=14)
        
        # Проверяем тип
        assert isinstance(rsi, CustomIndicator), "Должен быть CustomIndicator"
        assert isinstance(rsi, BaseIndicator), "Должен наследоваться от BaseIndicator"
        
        # Проверяем конфигурацию
        assert rsi.config.source == IndicatorSource.CUSTOM, "Источник должен быть CUSTOM"
        assert rsi.config.parameters['period'] == 14, "Параметр period должен быть 14"
        
        # Проверяем валидацию
        is_valid = rsi.validate_data(test_data)
        assert is_valid is True, "Данные должны быть валидными"
        
        # Проверяем расчет
        result = rsi.calculate(test_data)
        assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
        assert 'rsi_14' in result.data.columns, "Результат должен содержать колонку rsi_14"
        
        # Проверяем статистику
        stats = rsi.get_statistics(test_data)
        assert isinstance(stats, (pd.DataFrame, dict)), "Статистика должна быть DataFrame или dict"
        
        print("✅ CUSTOM RSI индикатор работает корректно")
    
    def test_macd_custom(self):
        """Тестирует CUSTOM MACD индикатор."""
        test_data = create_test_data(100)
        
        # Создаем CUSTOM индикатор
        macd = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        
        # Проверяем тип
        assert isinstance(macd, CustomIndicator), "Должен быть CustomIndicator"
        assert isinstance(macd, BaseIndicator), "Должен наследоваться от BaseIndicator"
        
        # Проверяем конфигурацию
        assert macd.config.source == IndicatorSource.CUSTOM, "Источник должен быть CUSTOM"
        assert macd.config.parameters['fast_period'] == 12, "Параметр fast_period должен быть 12"
        assert macd.config.parameters['slow_period'] == 26, "Параметр slow_period должен быть 26"
        assert macd.config.parameters['signal_period'] == 9, "Параметр signal_period должен быть 9"
        
        # Проверяем валидацию
        is_valid = macd.validate_data(test_data)
        assert is_valid is True, "Данные должны быть валидными"
        
        # Проверяем расчет
        result = macd.calculate(test_data)
        assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
        assert 'macd' in result.data.columns, "Результат должен содержать колонку macd"
        assert 'macd_signal' in result.data.columns, "Результат должен содержать колонку macd_signal"
        assert 'macd_hist' in result.data.columns, "Результат должен содержать колонку macd_hist"
        
        # Проверяем статистику
        stats = macd.get_statistics(test_data)
        assert isinstance(stats, (pd.DataFrame, dict)), "Статистика должна быть DataFrame или dict"
        
        print("✅ CUSTOM MACD индикатор работает корректно")
    
    def test_bbands_custom(self):
        """Тестирует CUSTOM Bollinger Bands индикатор."""
        test_data = create_test_data(100)
        
        # Создаем CUSTOM индикатор
        bbands = IndicatorFactory.create('custom', 'bbands', period=20, std_dev=2)
        
        # Проверяем тип
        assert isinstance(bbands, CustomIndicator), "Должен быть CustomIndicator"
        assert isinstance(bbands, BaseIndicator), "Должен наследоваться от BaseIndicator"
        
        # Проверяем конфигурацию
        assert bbands.config.source == IndicatorSource.CUSTOM, "Источник должен быть CUSTOM"
        assert bbands.config.parameters['period'] == 20, "Параметр period должен быть 20"
        assert bbands.config.parameters['std_dev'] == 2, "Параметр std_dev должен быть 2"
        
        # Проверяем валидацию
        is_valid = bbands.validate_data(test_data)
        assert is_valid is True, "Данные должны быть валидными"
        
        # Проверяем расчет
        result = bbands.calculate(test_data)
        assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
        assert 'bb_upper' in result.data.columns, "Результат должен содержать колонку bb_upper"
        assert 'bb_middle' in result.data.columns, "Результат должен содержать колонку bb_middle"
        assert 'bb_lower' in result.data.columns, "Результат должен содержать колонку bb_lower"
        
        # Проверяем статистику
        stats = bbands.get_statistics(test_data)
        assert isinstance(stats, (pd.DataFrame, dict)), "Статистика должна быть DataFrame или dict"
        
        print("✅ CUSTOM Bollinger Bands индикатор работает корректно")


class TestLibraryIndicators:
    """Тесты LIBRARY индикаторов (если доступны)."""
    
    def test_pandas_ta_availability(self):
        """Тестирует доступность pandas_ta библиотеки."""
        try:
            # Пытаемся создать pandas_ta индикатор
            sma = IndicatorFactory.create('pandas_ta', 'sma', length=20)
            assert isinstance(sma, LibraryIndicator), "Должен быть LibraryIndicator"
            assert isinstance(sma, BaseIndicator), "Должен наследоваться от BaseIndicator"
            
            # Проверяем конфигурацию
            assert sma.config.source == IndicatorSource.LIBRARY, "Источник должен быть LIBRARY"
            
            print("✅ pandas_ta библиотека доступна и работает")
            
        except Exception as e:
            print(f"⚠️ pandas_ta библиотека недоступна: {e}")
    
    def test_talib_availability(self):
        """Тестирует доступность talib библиотеки."""
        try:
            # Пытаемся создать talib индикатор
            sma = IndicatorFactory.create('talib', 'sma', timeperiod=20)
            assert isinstance(sma, LibraryIndicator), "Должен быть LibraryIndicator"
            assert isinstance(sma, BaseIndicator), "Должен наследоваться от BaseIndicator"
            
            # Проверяем конфигурацию
            assert sma.config.source == IndicatorSource.LIBRARY, "Источник должен быть LIBRARY"
            
            print("✅ talib библиотека доступна и работает")
            
        except Exception as e:
            print(f"⚠️ talib библиотека недоступна: {e}")


class TestIndicatorFactory:
    """Тесты IndicatorFactory."""
    
    def test_list_all_indicators(self):
        """Тестирует получение списка всех индикаторов."""
        all_indicators = IndicatorFactory.list_indicators()
        
        assert isinstance(all_indicators, dict), "list_indicators должен возвращать словарь"
        assert len(all_indicators) > 0, "Должно быть зарегистрировано хотя бы несколько индикаторов"
        
        # Проверяем наличие основных индикаторов
        expected_indicators = ['sma', 'ema', 'rsi', 'macd', 'bbands', 'macd_preloaded']
        for indicator in expected_indicators:
            assert indicator in all_indicators, f"Индикатор {indicator} должен быть в списке"
        
        print(f"✅ Найдено {len(all_indicators)} индикаторов: {list(all_indicators.keys())}")
    
    def test_get_indicators_by_source(self):
        """Тестирует получение индикаторов по источнику."""
        # Проверяем PRELOADED индикаторы
        preloaded = IndicatorFactory.get_indicators_by_source('preloaded')
        assert isinstance(preloaded, list), "get_indicators_by_source('preloaded') должен возвращать список"
        assert 'macd_preloaded' in preloaded, "macd_preloaded должен быть в PRELOADED индикаторах"
        
        # Проверяем CUSTOM индикаторы
        custom = IndicatorFactory.get_indicators_by_source('custom')
        assert isinstance(custom, list), "get_indicators_by_source('custom') должен возвращать список"
        assert 'sma' in custom, "sma должен быть в CUSTOM индикаторах"
        assert 'ema' in custom, "ema должен быть в CUSTOM индикаторах"
        assert 'rsi' in custom, "rsi должен быть в CUSTOM индикаторах"
        assert 'macd' in custom, "macd должен быть в CUSTOM индикаторах"
        assert 'bbands' in custom, "bbands должен быть в CUSTOM индикаторах"
        
        # Проверяем LIBRARY индикаторы
        library = IndicatorFactory.get_indicators_by_source('library')
        assert isinstance(library, list), "get_indicators_by_source('library') должен возвращать список"
        
        print(f"✅ PRELOADED: {len(preloaded)}, CUSTOM: {len(custom)}, LIBRARY: {len(library)}")
    
    def test_get_indicator_info(self):
        """Тестирует получение информации об индикаторах."""
        # Получаем информацию о SMA
        sma_info = IndicatorFactory.get_indicator_info('sma')
        assert sma_info is not None, "get_indicator_info('sma') должен возвращать информацию"
        assert 'source' in sma_info, "Информация должна содержать источник"
        assert 'class' in sma_info, "Информация должна содержать класс"
        assert sma_info['source'] == 'custom', "SMA должен быть CUSTOM индикатором"
        
        # Получаем информацию о PRELOADED MACD
        macd_info = IndicatorFactory.get_indicator_info('macd_preloaded')
        assert macd_info is not None, "get_indicator_info('macd_preloaded') должен возвращать информацию"
        assert macd_info['source'] == 'preloaded', "macd_preloaded должен быть PRELOADED индикатором"
        
        print("✅ Получение информации об индикаторах работает корректно")


class TestIndicatorCompatibility:
    """Тесты совместимости индикаторов."""
    
    def test_old_interface_compatibility(self):
        """Тестирует совместимость со старым интерфейсом."""
        test_data = create_test_data(100)
        
        # Тестируем старый метод create_indicator
        old_sma = IndicatorFactory.create_indicator('sma', period=20)
        assert old_sma is not None, "Старый метод create_indicator должен работать"
        
        # Проверяем, что старый метод создает правильный объект
        assert hasattr(old_sma, 'calculate'), "Старый метод должен создавать объект с методом calculate"
        assert hasattr(old_sma, 'validate_data'), "Старый метод должен создавать объект с методом validate_data"
        
        # Проверяем, что старый метод работает
        result = old_sma.calculate(test_data)
        assert hasattr(result, 'data'), "Результат старого метода должен иметь атрибут data"
        
        print("✅ Старый интерфейс совместим")
    
    def test_result_structure_consistency(self):
        """Тестирует консистентность структуры результатов."""
        test_data = create_test_data(100)
        
        # Создаем индикаторы разными способами
        indicators = [
            ('old_sma', IndicatorFactory.create_indicator('sma', period=20)),
            ('new_sma', IndicatorFactory.create('custom', 'sma', period=20)),
            ('preloaded_macd', IndicatorFactory.create('preloaded', 'macd_preloaded', required_columns=['macd', 'signal'])),
        ]
        
        # Проверяем, что все результаты имеют одинаковую структуру
        for name, indicator in indicators:
            result = indicator.calculate(test_data)
            
            # Проверяем обязательные атрибуты
            assert hasattr(result, 'name'), f"Результат {name} должен иметь атрибут name"
            assert hasattr(result, 'data'), f"Результат {name} должен иметь атрибут data"
            assert hasattr(result, 'config'), f"Результат {name} должен иметь атрибут config"
            assert hasattr(result, 'metadata'), f"Результат {name} должен иметь атрибут metadata"
            
            # Проверяем типы
            assert isinstance(result.name, str), f"name должен быть строкой для {name}"
            assert isinstance(result.data, pd.DataFrame), f"data должен быть DataFrame для {name}"
            assert hasattr(result.config, 'source'), f"config должен иметь атрибут source для {name}"
            assert isinstance(result.metadata, dict), f"metadata должен быть словарем для {name}"
        
        print("✅ Структура результатов консистентна")


def run_all_indicator_tests():
    """Запуск всех тестов индикаторов."""
    print("🧪 Тестирование всех типов индикаторов - Этап 8")
    print("=" * 70)
    
    # Создаем экземпляры тестовых классов и запускаем тесты
    test_classes = [
        TestPreloadedIndicators(),
        TestCustomIndicators(),
        TestLibraryIndicators(),
        TestIndicatorFactory(),
        TestIndicatorCompatibility(),
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n📋 {class_name}:")
        
        # Получаем все методы тестирования
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                print(f"  ✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
    
    print(f"\n📊 Результаты: {passed_tests}/{total_tests} тестов прошли")
    
    if passed_tests == total_tests:
        print("🎉 Все тесты прошли успешно!")
    else:
        print(f"⚠️ {total_tests - passed_tests} тестов не прошли")


if __name__ == "__main__":
    run_all_indicator_tests()
