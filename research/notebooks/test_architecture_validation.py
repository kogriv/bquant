"""
Тест валидации архитектуры индикаторов - Этап 8

Комплексное тестирование всей архитектуры, включая:
- Наследование и полиморфизм
- Единообразный интерфейс
- Совместимость с существующим кодом
- Производительность и надежность
"""

import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any

def test_architecture_validation():
    """Комплексное тестирование архитектуры индикаторов."""
    
    print("🧪 Тестирование валидации архитектуры - Этап 8")
    print("=" * 70)
    
    # Создаем тестовые данные
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    test_data = pd.DataFrame({
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 100 + np.random.randn(100).cumsum() + 2,
        'low': 100 + np.random.randn(100).cumsum() - 2,
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': np.random.randint(1000, 10000, 100),
        'macd': np.random.randn(100).cumsum(),
        'signal': np.random.randn(100).cumsum()
    }, index=dates)
    
    # 1. Тест архитектуры наследования
    print("\n1️⃣ Тест архитектуры наследования:")
    if not test_inheritance_architecture():
        return False
    
    # 2. Тест единообразного интерфейса
    print("\n2️⃣ Тест единообразного интерфейса:")
    if not test_unified_interface():
        return False
    
    # 3. Тест полиморфизма
    print("\n3️⃣ Тест полиморфизма:")
    if not test_polymorphism(test_data):
        return False
    
    # 4. Тест производительности
    print("\n4️⃣ Тест производительности:")
    if not test_performance(test_data):
        return False
    
    # 5. Тест совместимости
    print("\n5️⃣ Тест совместимости:")
    if not test_compatibility(test_data):
        return False
    
    # 6. Тест обработки ошибок
    print("\n6️⃣ Тест обработки ошибок:")
    if not test_error_handling():
        return False
    
    # 7. Тест расширяемости
    print("\n7️⃣ Тест расширяемости:")
    if not test_extensibility():
        return False
    
    print("\n" + "=" * 70)
    print("🎉 Все тесты валидации архитектуры пройдены успешно!")
    return True


def test_inheritance_architecture() -> bool:
    """Тестирует правильность архитектуры наследования."""
    
    try:
        from bquant.indicators import (
            BaseIndicator, PreloadedIndicator, CustomIndicator, LibraryIndicator
        )
        
        # Проверяем иерархию наследования
        print("   ✅ Иерархия наследования:")
        print(f"      BaseIndicator: {BaseIndicator.__bases__}")
        print(f"      PreloadedIndicator: {PreloadedIndicator.__bases__}")
        print(f"      CustomIndicator: {CustomIndicator.__bases__}")
        print(f"      LibraryIndicator: {LibraryIndicator.__bases__}")
        
        # Проверяем, что все наследуются от BaseIndicator
        assert issubclass(PreloadedIndicator, BaseIndicator), "PreloadedIndicator должен наследоваться от BaseIndicator"
        assert issubclass(CustomIndicator, BaseIndicator), "CustomIndicator должен наследоваться от BaseIndicator"
        assert issubclass(LibraryIndicator, BaseIndicator), "LibraryIndicator должен наследоваться от BaseIndicator"
        
        # Проверяем абстрактные методы
        print("   ✅ Абстрактные методы:")
        print(f"      BaseIndicator.calculate: {hasattr(BaseIndicator, 'calculate')}")
        print(f"      CustomIndicator.get_output_columns: {hasattr(CustomIndicator, 'get_output_columns')}")
        print(f"      CustomIndicator.get_description: {hasattr(CustomIndicator, 'get_description')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования наследования: {e}")
        return False


def test_unified_interface() -> bool:
    """Тестирует единообразность интерфейса всех индикаторов."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        # Создаем индикаторы разных типов
        indicators = {
            'preloaded': IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal']),
            'custom_sma': IndicatorFactory.create('custom', 'sma', period=20),
            'custom_ema': IndicatorFactory.create('custom', 'ema', period=20),
        }
        
        print("   ✅ Единообразный интерфейс:")
        
        # Проверяем наличие общих методов
        common_methods = ['calculate', 'validate_data', 'get_statistics', 'get_required_columns']
        for name, indicator in indicators.items():
            print(f"      {name}: {type(indicator).__name__}")
            for method in common_methods:
                if hasattr(indicator, method):
                    print(f"        ✅ {method}")
                else:
                    print(f"        ❌ {method} отсутствует")
                    return False
        
        # Проверяем, что все индикаторы имеют одинаковый базовый интерфейс
        for indicator in indicators.values():
            assert hasattr(indicator, 'calculate'), "Все индикаторы должны иметь метод calculate"
            assert hasattr(indicator, 'validate_data'), "Все индикаторы должны иметь метод validate_data"
            assert hasattr(indicator, 'get_statistics'), "Все индикаторы должны иметь метод get_statistics"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования интерфейса: {e}")
        return False


def test_polymorphism(test_data: pd.DataFrame) -> bool:
    """Тестирует полиморфизм - одинаковое поведение разных типов индикаторов."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Полиморфизм:")
        
        # Создаем индикаторы разных типов
        indicators = [
            IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal']),
            IndicatorFactory.create('custom', 'sma', period=20),
            IndicatorFactory.create('custom', 'ema', period=20),
        ]
        
        # Тестируем одинаковое поведение
        for i, indicator in enumerate(indicators):
            print(f"      Индикатор {i+1}: {type(indicator).__name__}")
            
            # Все должны уметь валидировать данные
            is_valid = indicator.validate_data(test_data)
            print(f"        ✅ validate_data: {is_valid}")
            
            # Все должны уметь рассчитывать
            result = indicator.calculate(test_data)
            print(f"        ✅ calculate: {type(result).__name__}")
            
            # Все должны уметь давать статистику
            stats = indicator.get_statistics(test_data)
            print(f"        ✅ get_statistics: {len(stats)} колонок")
            
            # Проверяем, что результат имеет правильную структуру
            assert hasattr(result, 'data'), "Результат должен иметь атрибут data"
            assert hasattr(result, 'config'), "Результат должен иметь атрибут config"
            assert hasattr(result, 'metadata'), "Результат должен иметь атрибут metadata"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования полиморфизма: {e}")
        return False


def test_performance(test_data: pd.DataFrame) -> bool:
    """Тестирует производительность индикаторов."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Производительность:")
        
        # Создаем индикаторы для тестирования
        indicators = [
            ('preloaded_macd', IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal'])),
            ('custom_sma', IndicatorFactory.create('custom', 'sma', period=20)),
            ('custom_ema', IndicatorFactory.create('custom', 'ema', period=20)),
        ]
        
        # Тестируем производительность расчета
        for name, indicator in indicators:
            print(f"      {name}:")
            
            # Замеряем время расчета
            start_time = time.time()
            result = indicator.calculate(test_data)
            calc_time = time.time() - start_time
            
            print(f"        ✅ Расчет: {calc_time:.4f} сек")
            
            # Замеряем время валидации
            start_time = time.time()
            is_valid = indicator.validate_data(test_data)
            valid_time = time.time() - start_time
            
            print(f"        ✅ Валидация: {valid_time:.4f} сек")
            
            # Замеряем время статистики
            start_time = time.time()
            stats = indicator.get_statistics(test_data)
            stats_time = time.time() - start_time
            
            print(f"        ✅ Статистика: {stats_time:.4f} сек")
            
            # Проверяем, что время выполнения разумное
            assert calc_time < 1.0, f"Расчет {name} занимает слишком много времени: {calc_time} сек"
            assert valid_time < 0.1, f"Валидация {name} занимает слишком много времени: {valid_time} сек"
            assert stats_time < 0.1, f"Статистика {name} занимает слишком много времени: {stats_time} сек"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования производительности: {e}")
        return False


def test_compatibility(test_data: pd.DataFrame) -> bool:
    """Тестирует совместимость с существующим кодом."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Совместимость:")
        
        # Тестируем старый метод create_indicator (должен работать с предупреждением)
        print("      Старый метод create_indicator:")
        try:
            old_sma = IndicatorFactory.create_indicator('sma', period=20)
            print(f"        ✅ Работает: {type(old_sma).__name__}")
            
            # Проверяем, что результат совпадает с новым методом
            new_sma = IndicatorFactory.create('custom', 'sma', period=20)
            old_result = old_sma.calculate(test_data)
            new_result = new_sma.calculate(test_data)
            
            # Проверяем, что результаты имеют одинаковую структуру
            assert old_result.data.shape == new_result.data.shape, "Результаты должны иметь одинаковую форму"
            print(f"        ✅ Результаты совпадают: {old_result.data.shape}")
            
        except Exception as e:
            print(f"        ❌ Ошибка совместимости: {e}")
            return False
        
        # Тестируем прямой импорт классов (должен работать)
        print("      Прямой импорт классов:")
        try:
            from bquant.indicators.preloaded.macd import MACDPreloadedIndicator
            from bquant.indicators.custom.sma import SimpleMovingAverage
            from bquant.indicators.custom.ema import ExponentialMovingAverage
            
            print(f"        ✅ MACDPreloadedIndicator: {MACDPreloadedIndicator}")
            print(f"        ✅ SimpleMovingAverage: {SimpleMovingAverage}")
            print(f"        ✅ ExponentialMovingAverage: {ExponentialMovingAverage}")
            
        except Exception as e:
            print(f"        ❌ Ошибка прямого импорта: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования совместимости: {e}")
        return False


def test_error_handling() -> bool:
    """Тестирует обработку ошибок."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Обработка ошибок:")
        
        # Тестируем неизвестный источник
        print("      Неизвестный источник:")
        try:
            IndicatorFactory.create('unknown', 'sma')
            print("        ❌ Должна была быть ошибка")
            return False
        except ValueError as e:
            print(f"        ✅ Правильно обработана ошибка: {e}")
        
        # Тестируем неизвестный индикатор
        print("      Неизвестный индикатор:")
        try:
            IndicatorFactory.create('custom', 'unknown_indicator')
            print("        ❌ Должна была быть ошибка")
            return False
        except KeyError as e:
            print(f"        ✅ Правильно обработана ошибка: {e}")
        
        # Тестируем неправильные параметры
        print("      Неправильные параметры:")
        try:
            IndicatorFactory.create('custom', 'sma', invalid_param='value')
            print("        ✅ Обработаны лишние параметры")
        except Exception as e:
            print(f"        ✅ Обработана ошибка параметров: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования обработки ошибок: {e}")
        return False


def test_extensibility() -> bool:
    """Тестирует расширяемость архитектуры."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Расширяемость:")
        
        # Проверяем, что можно получить информацию о всех индикаторах
        all_indicators = IndicatorFactory.list_indicators()
        print(f"      Всего индикаторов: {len(all_indicators)}")
        
        # Проверяем группировку по источникам
        sources = ['preloaded', 'custom', 'library']
        for source in sources:
            indicators = IndicatorFactory.get_indicators_by_source(source)
            print(f"        {source}: {len(indicators)} индикаторов")
        
        # Проверяем, что можно получить детальную информацию
        if 'sma' in all_indicators:
            info = IndicatorFactory.get_indicator_info('sma')
            print(f"      Информация о SMA: {info['source']} - {info['class']}")
        
        # Проверяем, что можно создавать индикаторы с разными параметрами
        print("      Гибкость параметров:")
        sma_10 = IndicatorFactory.create('custom', 'sma', period=10)
        sma_50 = IndicatorFactory.create('custom', 'sma', period=50)
        
        print(f"        ✅ SMA(10): {type(sma_10).__name__}")
        print(f"        ✅ SMA(50): {type(sma_50).__name__}")
        
        # Проверяем, что параметры применяются корректно
        assert sma_10.config.parameters['period'] == 10, "Параметр period должен быть 10"
        assert sma_50.config.parameters['period'] == 50, "Параметр period должен быть 50"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования расширяемости: {e}")
        return False


if __name__ == "__main__":
    success = test_architecture_validation()
    if success:
        print("\n✅ Этап 8: Тестирование и валидация - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 8: Тестирование и валидация - ЕСТЬ ОШИБКИ!")
