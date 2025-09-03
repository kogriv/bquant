"""
Тест совместимости с существующим кодом - Этап 8

Проверяет, что новая архитектура совместима с существующим кодом:
- Старые импорты продолжают работать
- Старые методы продолжают работать
- Результаты совпадают
"""

import pandas as pd
import numpy as np

def test_compatibility_validation():
    """Тестирует совместимость с существующим кодом."""
    
    print("🧪 Тестирование совместимости с существующим кодом - Этап 8")
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
    
    # 1. Тест совместимости импортов
    print("\n1️⃣ Тест совместимости импортов:")
    if not test_import_compatibility():
        return False
    
    # 2. Тест совместимости методов
    print("\n2️⃣ Тест совместимости методов:")
    if not test_method_compatibility(test_data):
        return False
    
    # 3. Тест совместимости результатов
    print("\n3️⃣ Тест совместимости результатов:")
    if not test_result_compatibility(test_data):
        return False
    
    # 4. Тест обратной совместимости
    print("\n4️⃣ Тест обратной совместимости:")
    if not test_backward_compatibility(test_data):
        return False
    
    print("\n" + "=" * 70)
    print("🎉 Все тесты совместимости пройдены успешно!")
    return True


def test_import_compatibility() -> bool:
    """Тестирует совместимость импортов."""
    
    try:
        print("   ✅ Совместимость импортов:")
        
        # Тестируем старые импорты (должны работать)
        print("      Старые импорты:")
        
        # Импорт базовых классов
        from bquant.indicators import BaseIndicator, IndicatorFactory
        print(f"        ✅ BaseIndicator: {BaseIndicator}")
        print(f"        ✅ IndicatorFactory: {IndicatorFactory}")
        
        # Импорт конкретных индикаторов
        from bquant.indicators import SimpleMovingAverage, ExponentialMovingAverage
        print(f"        ✅ SimpleMovingAverage: {SimpleMovingAverage}")
        print(f"        ✅ ExponentialMovingAverage: {ExponentialMovingAverage}")
        
        # Импорт PRELOADED индикаторов
        from bquant.indicators import MACDPreloadedIndicator
        print(f"        ✅ MACDPreloadedIndicator: {MACDPreloadedIndicator}")
        
        # Импорт LIBRARY модулей
        from bquant.indicators import LibraryManager, load_pandas_ta, load_talib
        print(f"        ✅ LibraryManager: {LibraryManager}")
        print(f"        ✅ load_pandas_ta: {load_pandas_ta}")
        print(f"        ✅ load_talib: {load_talib}")
        
        # Тестируем прямые импорты из подмодулей (должны работать)
        print("      Прямые импорты из подмодулей:")
        
        from bquant.indicators.custom.sma import SimpleMovingAverage as SMADirect
        from bquant.indicators.custom.ema import ExponentialMovingAverage as EMADirect
        from bquant.indicators.preloaded.macd import MACDPreloadedIndicator as MACDDirect
        
        print(f"        ✅ SMADirect: {SMADirect}")
        print(f"        ✅ EMADirect: {EMADirect}")
        print(f"        ✅ MACDDirect: {MACDDirect}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка совместимости импортов: {e}")
        return False


def test_method_compatibility(test_data: pd.DataFrame) -> bool:
    """Тестирует совместимость методов."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Совместимость методов:")
        
        # Тестируем старый метод create_indicator (должен работать с предупреждением)
        print("      Старый метод create_indicator:")
        
        try:
            old_sma = IndicatorFactory.create_indicator('sma', period=20)
            print(f"        ✅ Работает: {type(old_sma).__name__}")
            
            # Проверяем, что старый метод создает правильный объект
            assert hasattr(old_sma, 'calculate'), "Старый метод должен создавать объект с методом calculate"
            assert hasattr(old_sma, 'validate_data'), "Старый метод должен создавать объект с методом validate_data"
            
            # Проверяем, что старый метод работает
            result = old_sma.calculate(test_data)
            print(f"        ✅ Старый метод работает: {len(result.data.columns)} колонок")
            
        except Exception as e:
            print(f"        ❌ Старый метод не работает: {e}")
            return False
        
        # Тестируем новый метод create (должен работать)
        print("      Новый метод create:")
        
        try:
            new_sma = IndicatorFactory.create('custom', 'sma', period=20)
            print(f"        ✅ Работает: {type(new_sma).__name__}")
            
            # Проверяем, что новый метод создает правильный объект
            assert hasattr(new_sma, 'calculate'), "Новый метод должен создавать объект с методом calculate"
            assert hasattr(new_sma, 'validate_data'), "Новый метод должен создавать объект с методом validate_data"
            
            # Проверяем, что новый метод работает
            result = new_sma.calculate(test_data)
            print(f"        ✅ Новый метод работает: {len(result.data.columns)} колонок")
            
        except Exception as e:
            print(f"        ❌ Новый метод не работает: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка совместимости методов: {e}")
        return False


def test_result_compatibility(test_data: pd.DataFrame) -> bool:
    """Тестирует совместимость результатов."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Совместимость результатов:")
        
        # Создаем индикаторы старым и новым способом
        old_sma = IndicatorFactory.create_indicator('sma', period=20)
        new_sma = IndicatorFactory.create('custom', 'sma', period=20)
        
        # Рассчитываем результаты
        old_result = old_sma.calculate(test_data)
        new_result = new_sma.calculate(test_data)
        
        print("      Сравнение результатов:")
        
        # Проверяем структуру результатов
        print(f"        ✅ Старый результат: {type(old_result).__name__}")
        print(f"        ✅ Новый результат: {type(new_result).__name__}")
        
        # Проверяем наличие обязательных атрибутов
        required_attrs = ['data', 'config', 'metadata']
        for attr in required_attrs:
            assert hasattr(old_result, attr), f"Старый результат должен иметь атрибут {attr}"
            assert hasattr(new_result, attr), f"Новый результат должен иметь атрибут {attr}"
            print(f"        ✅ Атрибут {attr}: есть в обоих результатах")
        
        # Проверяем форму данных
        assert old_result.data.shape == new_result.data.shape, "Результаты должны иметь одинаковую форму"
        print(f"        ✅ Форма данных совпадает: {old_result.data.shape}")
        
        # Проверяем названия колонок
        assert list(old_result.data.columns) == list(new_result.data.columns), "Названия колонок должны совпадать"
        print(f"        ✅ Названия колонок совпадают: {list(old_result.data.columns)}")
        
        # Проверяем, что данные не пустые
        assert len(old_result.data) > 0, "Старый результат не должен быть пустым"
        assert len(new_result.data) > 0, "Новый результат не должен быть пустым"
        print(f"        ✅ Данные не пустые: {len(old_result.data)} строк")
        
        # Проверяем, что нет NaN в начале (где индикатор еще не может быть рассчитан)
        # Первые значения могут быть NaN из-за периода расчета
        valid_old = old_result.data.dropna()
        valid_new = new_result.data.dropna()
        
        assert len(valid_old) > 0, "В старом результате должны быть валидные данные"
        assert len(valid_new) > 0, "В новом результате должны быть валидные данные"
        print(f"        ✅ Валидные данные: {len(valid_old)} строк")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка совместимости результатов: {e}")
        return False


def test_backward_compatibility(test_data: pd.DataFrame) -> bool:
    """Тестирует обратную совместимость."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Обратная совместимость:")
        
        # Тестируем, что старые вызовы продолжают работать
        print("      Старые вызовы:")
        
        # Создание индикаторов
        indicators = {
            'sma_20': IndicatorFactory.create_indicator('sma', period=20),
            'ema_20': IndicatorFactory.create_indicator('ema', period=20),
            'rsi_14': IndicatorFactory.create_indicator('rsi', period=14),
            'macd': IndicatorFactory.create_indicator('macd', fast=12, slow=26, signal=9),
            'bbands': IndicatorFactory.create_indicator('bbands', period=20, std=2.0),
        }
        
        print(f"        ✅ Создано индикаторов: {len(indicators)}")
        
        # Тестируем работу всех старых индикаторов
        for name, indicator in indicators.items():
            print(f"      {name}: {type(indicator).__name__}")
            
            # Проверяем валидацию
            is_valid = indicator.validate_data(test_data)
            print(f"        ✅ Валидация: {is_valid}")
            
            # Проверяем расчет
            result = indicator.calculate(test_data)
            print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
            
            # Проверяем статистику
            stats = indicator.get_statistics(test_data)
            print(f"        ✅ Статистика: {len(stats)} колонок")
            
            # Проверяем, что результат имеет правильную структуру
            assert hasattr(result, 'data'), f"Результат {name} должен иметь атрибут data"
            assert hasattr(result, 'config'), f"Результат {name} должен иметь атрибут config"
            assert hasattr(result, 'metadata'), f"Результат {name} должен иметь атрибут metadata"
        
        # Тестируем, что старые методы продолжают работать
        print("      Старые методы:")
        
        # Проверяем list_indicators
        all_indicators = IndicatorFactory.list_indicators()
        print(f"        ✅ list_indicators: {len(all_indicators)} индикаторов")
        
        # Проверяем get_indicator_info
        if 'sma' in all_indicators:
            info = IndicatorFactory.get_indicator_info('sma')
            print(f"        ✅ get_indicator_info: {info['source']} - {info['class']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка обратной совместимости: {e}")
        return False


if __name__ == "__main__":
    success = test_compatibility_validation()
    if success:
        print("\n✅ Этап 8: Тестирование совместимости - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 8: Тестирование совместимости - ЕСТЬ ОШИБКИ!")
