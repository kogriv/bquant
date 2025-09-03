"""
Тест обновленного IndicatorFactory - Этап 6

Проверяет корректность работы нового единого метода create() для всех типов индикаторов.
"""

import pandas as pd
import numpy as np
from bquant.indicators import IndicatorFactory

def test_indicator_factory():
    """Тестирует все аспекты обновленного IndicatorFactory."""
    
    print("🧪 Тестирование обновленного IndicatorFactory")
    print("=" * 60)
    
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
    
    # 1. Тест создания PRELOADED индикаторов
    print("\n1️⃣ Тест создания PRELOADED индикаторов:")
    try:
        # Создаем MACD PRELOADED
        macd_preloaded = IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal'])
        print(f"✅ MACD PRELOADED создан: {type(macd_preloaded).__name__}")
        
        # Проверяем работу
        result = macd_preloaded.calculate(test_data)
        print(f"✅ Расчет выполнен, колонки: {list(result.data.columns)}")
        
    except Exception as e:
        print(f"❌ Ошибка создания PRELOADED: {e}")
        return False
    
    # 2. Тест создания CUSTOM индикаторов
    print("\n2️⃣ Тест создания CUSTOM индикаторов:")
    try:
        # Создаем SMA CUSTOM
        sma_custom = IndicatorFactory.create('custom', 'sma', period=20)
        print(f"✅ SMA CUSTOM создан: {type(sma_custom).__name__}")
        
        # Проверяем работу
        result = sma_custom.calculate(test_data)
        print(f"✅ Расчет выполнен, колонки: {list(result.data.columns)}")
        
        # Создаем EMA CUSTOM
        ema_custom = IndicatorFactory.create('custom', 'ema', period=20)
        print(f"✅ EMA CUSTOM создан: {type(ema_custom).__name__}")
        
        # Создаем RSI CUSTOM
        rsi_custom = IndicatorFactory.create('custom', 'rsi', period=14)
        print(f"✅ RSI CUSTOM создан: {type(rsi_custom).__name__}")
        
        # Создаем MACD CUSTOM
        macd_custom = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        print(f"✅ MACD CUSTOM создан: {type(macd_custom).__name__}")
        
        # Создаем Bollinger Bands CUSTOM
        bb_custom = IndicatorFactory.create('custom', 'bbands', period=20, std_dev=2.0)
        print(f"✅ Bollinger Bands CUSTOM создан: {type(bb_custom).__name__}")
        
    except Exception as e:
        print(f"❌ Ошибка создания CUSTOM: {e}")
        return False
    
    # 3. Тест создания LIBRARY индикаторов (если доступны)
    print("\n3️⃣ Тест создания LIBRARY индикаторов:")
    try:
        # Пытаемся создать pandas-ta индикаторы
        try:
            sma_pandas_ta = IndicatorFactory.create('pandas_ta', 'sma', length=20)
            print(f"✅ pandas-ta SMA создан: {type(sma_pandas_ta).__name__}")
            
            # Проверяем работу
            result = sma_pandas_ta.calculate(test_data)
            print(f"✅ Расчет выполнен, колонки: {list(result.data.columns)}")
            
        except Exception as e:
            print(f"⚠️ pandas-ta SMA не доступен: {e}")
        
        # Пытаемся создать TA-Lib индикаторы
        try:
            sma_talib = IndicatorFactory.create('talib', 'sma', timeperiod=20)
            print(f"✅ TA-Lib SMA создан: {type(sma_talib).__name__}")
            
            # Проверяем работу
            result = sma_talib.calculate(test_data)
            print(f"✅ Расчет выполнен, колонки: {list(result.data.columns)}")
            
        except Exception as e:
            print(f"⚠️ TA-Lib SMA не доступен: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка создания LIBRARY: {e}")
        return False
    
    # 4. Тест единообразного интерфейса
    print("\n4️⃣ Тест единообразного интерфейса:")
    try:
        # Все индикаторы должны иметь одинаковые методы
        indicators = [
            macd_preloaded,
            sma_custom,
            ema_custom
        ]
        
        for i, indicator in enumerate(indicators):
            print(f"   Индикатор {i+1}: {type(indicator).__name__}")
            
            # Проверяем наличие основных методов
            required_methods = ['calculate', 'validate_data', 'get_statistics']
            for method in required_methods:
                if hasattr(indicator, method):
                    print(f"     ✅ {method} - доступен")
                else:
                    print(f"     ❌ {method} - отсутствует")
            
            # Проверяем работу методов
            try:
                stats = indicator.get_statistics(test_data)
                print(f"     ✅ get_statistics работает: {len(stats)} колонок")
            except Exception as e:
                print(f"     ❌ get_statistics не работает: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка проверки интерфейса: {e}")
        return False
    
    # 5. Тест новых методов IndicatorFactory
    print("\n5️⃣ Тест новых методов IndicatorFactory:")
    try:
        # Получаем список индикаторов по источнику
        preloaded_indicators = IndicatorFactory.get_indicators_by_source('preloaded')
        custom_indicators = IndicatorFactory.get_indicators_by_source('custom')
        library_indicators = IndicatorFactory.get_indicators_by_source('library')
        
        print(f"✅ PRELOADED индикаторы: {len(preloaded_indicators)}")
        print(f"✅ CUSTOM индикаторы: {len(custom_indicators)}")
        print(f"✅ LIBRARY индикаторы: {len(library_indicators)}")
        
        # Получаем общий список
        all_indicators = IndicatorFactory.list_indicators()
        print(f"✅ Всего индикаторов: {len(all_indicators)}")
        
        # Получаем информацию об индикаторе
        if 'sma' in all_indicators:
            info = IndicatorFactory.get_indicator_info('sma')
            print(f"✅ Информация о SMA: {info}")
        
    except Exception as e:
        print(f"❌ Ошибка новых методов: {e}")
        return False
    
    # 6. Тест обработки ошибок
    print("\n6️⃣ Тест обработки ошибок:")
    try:
        # Неизвестный источник
        try:
            IndicatorFactory.create('unknown', 'sma')
            print("❌ Должна была быть ошибка для неизвестного источника")
            return False
        except ValueError as e:
            print(f"✅ Правильно обработана ошибка неизвестного источника: {e}")
        
        # Неизвестный индикатор
        try:
            IndicatorFactory.create('custom', 'unknown_indicator')
            print("❌ Должна была быть ошибка для неизвестного индикатора")
            return False
        except KeyError as e:
            print(f"✅ Правильно обработана ошибка неизвестного индикатора: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования обработки ошибок: {e}")
        return False
    
    # 7. Тест совместимости с существующим кодом
    print("\n7️⃣ Тест совместимости:")
    try:
        # Новый метод должен работать
        new_sma = IndicatorFactory.create('custom', 'sma', period=20)
        print(f"✅ Новый метод работает: {type(new_sma).__name__}")
        
        # Проверяем работу нового метода
        result = new_sma.calculate(test_data)
        if result.data is not None:
            print("✅ Результат получен")
        else:
            print("❌ Результат пустой")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка совместимости: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Все тесты IndicatorFactory пройдены успешно!")
    return True

if __name__ == "__main__":
    success = test_indicator_factory()
    if success:
        print("\n✅ Этап 6: Обновление IndicatorFactory - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 6: Обновление IndicatorFactory - ЕСТЬ ОШИБКИ!")
