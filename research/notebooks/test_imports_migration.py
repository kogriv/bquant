"""
Тест миграции импортов - Этап 7

Проверяет корректность работы всех импортов после обновления
структуры модуля indicators.
"""

def test_imports_migration():
    """Тестирует все аспекты миграции импортов."""
    
    print("🧪 Тестирование миграции импортов - Этап 7")
    print("=" * 60)
    
    # 1. Тест импорта базовых классов
    print("\n1️⃣ Тест импорта базовых классов:")
    try:
        from bquant.indicators import (
            IndicatorSource,
            IndicatorConfig,
            IndicatorResult,
            BaseIndicator,
            PreloadedIndicator,
            CustomIndicator,
            LibraryIndicator,
            IndicatorFactory
        )
        print("✅ Все базовые классы импортированы успешно")
        
        # Проверяем, что классы действительно доступны
        print(f"   IndicatorSource: {IndicatorSource}")
        print(f"   BaseIndicator: {BaseIndicator}")
        print(f"   IndicatorFactory: {IndicatorFactory}")
        
    except Exception as e:
        print(f"❌ Ошибка импорта базовых классов: {e}")
        return False
    
    # 2. Тест импорта PRELOADED индикаторов
    print("\n2️⃣ Тест импорта PRELOADED индикаторов:")
    try:
        from bquant.indicators import MACDPreloadedIndicator
        print("✅ MACDPreloadedIndicator импортирован успешно")
        print(f"   Класс: {MACDPreloadedIndicator}")
        
    except Exception as e:
        print(f"❌ Ошибка импорта PRELOADED индикаторов: {e}")
        return False
    
    # 3. Тест импорта CUSTOM индикаторов
    print("\n3️⃣ Тест импорта CUSTOM индикаторов:")
    try:
        from bquant.indicators import (
            SimpleMovingAverage,
            ExponentialMovingAverage,
            RelativeStrengthIndex,
            MACD,
            BollingerBands
        )
        print("✅ Все CUSTOM индикаторы импортированы успешно")
        
        # Проверяем, что классы действительно доступны
        print(f"   SimpleMovingAverage: {SimpleMovingAverage}")
        print(f"   ExponentialMovingAverage: {ExponentialMovingAverage}")
        print(f"   RelativeStrengthIndex: {RelativeStrengthIndex}")
        print(f"   MACD: {MACD}")
        print(f"   BollingerBands: {BollingerBands}")
        
    except Exception as e:
        print(f"❌ Ошибка импорта CUSTOM индикаторов: {e}")
        return False
    
    # 4. Тест импорта LIBRARY модулей
    print("\n4️⃣ Тест импорта LIBRARY модулей:")
    try:
        from bquant.indicators import (
            PandasTALoader,
            TALibLoader,
            LibraryManager,
            load_pandas_ta,
            load_talib,
            load_all_indicators
        )
        print("✅ Все LIBRARY модули импортированы успешно")
        
        # Проверяем, что классы и функции действительно доступны
        print(f"   PandasTALoader: {PandasTALoader}")
        print(f"   TALibLoader: {TALibLoader}")
        print(f"   LibraryManager: {LibraryManager}")
        print(f"   load_pandas_ta: {load_pandas_ta}")
        print(f"   load_talib: {load_talib}")
        print(f"   load_all_indicators: {load_all_indicators}")
        
    except Exception as e:
        print(f"❌ Ошибка импорта LIBRARY модулей: {e}")
        return False
    
    # 5. Тест авторегистрации индикаторов
    print("\n5️⃣ Тест авторегистрации индикаторов:")
    try:
        from bquant.indicators import IndicatorFactory
        
        # Проверяем, что индикаторы зарегистрированы
        all_indicators = IndicatorFactory.list_indicators()
        print(f"✅ Всего зарегистрированных индикаторов: {len(all_indicators)}")
        
        # Проверяем наличие основных индикаторов
        expected_indicators = ['sma', 'ema', 'rsi', 'macd', 'bbands', 'macd_preloaded']
        for indicator in expected_indicators:
            if indicator in all_indicators:
                print(f"   ✅ {indicator} зарегистрирован")
            else:
                print(f"   ❌ {indicator} НЕ зарегистрирован")
        
        # Проверяем источники индикаторов
        preloaded_count = len(IndicatorFactory.get_indicators_by_source('preloaded'))
        custom_count = len(IndicatorFactory.get_indicators_by_source('custom'))
        library_count = len(IndicatorFactory.get_indicators_by_source('library'))
        
        print(f"   PRELOADED: {preloaded_count}")
        print(f"   CUSTOM: {custom_count}")
        print(f"   LIBRARY: {library_count}")
        
    except Exception as e:
        print(f"❌ Ошибка проверки авторегистрации: {e}")
        return False
    
    # 6. Тест создания индикаторов через IndicatorFactory
    print("\n6️⃣ Тест создания индикаторов через IndicatorFactory:")
    try:
        # Создаем тестовые данные
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        test_data = pd.DataFrame({
            'close': 100 + np.random.randn(50).cumsum(),
            'macd': np.random.randn(50).cumsum(),
            'signal': np.random.randn(50).cumsum()
        }, index=dates)
        
        # Тестируем создание PRELOADED индикатора
        macd_preloaded = IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal'])
        print(f"✅ PRELOADED MACD создан: {type(macd_preloaded).__name__}")
        
        # Тестируем создание CUSTOM индикатора
        sma_custom = IndicatorFactory.create('custom', 'sma', period=20)
        print(f"✅ CUSTOM SMA создан: {type(sma_custom).__name__}")
        
        # Проверяем работу индикаторов
        result_preloaded = macd_preloaded.calculate(test_data)
        result_custom = sma_custom.calculate(test_data)
        
        print(f"   PRELOADED результат: {len(result_preloaded.data.columns)} колонок")
        print(f"   CUSTOM результат: {len(result_custom.data.columns)} колонок")
        
    except Exception as e:
        print(f"❌ Ошибка создания индикаторов: {e}")
        return False
    
    # 7. Тест импорта из подмодулей
    print("\n7️⃣ Тест импорта из подмодулей:")
    try:
        # Тест импорта из preloaded
        from bquant.indicators.preloaded.macd import MACDPreloadedIndicator as MACDPreloadedDirect
        print("✅ Прямой импорт из preloaded.macd работает")
        
        # Тест импорта из custom
        from bquant.indicators.custom.sma import SimpleMovingAverage as SMADirect
        print("✅ Прямой импорт из custom.sma работает")
        
        # Тест импорта из library
        from bquant.indicators.library.manager import LibraryManager as LibraryManagerDirect
        print("✅ Прямой импорт из library.manager работает")
        
    except Exception as e:
        print(f"❌ Ошибка прямого импорта из подмодулей: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Все тесты миграции импортов пройдены успешно!")
    return True


if __name__ == "__main__":
    success = test_imports_migration()
    if success:
        print("\n✅ Этап 7: Обновление импортов и экспортов - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 7: Обновление импортов и экспортов - ЕСТЬ ОШИБКИ!")
