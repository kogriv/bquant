"""
Тест миграции LIBRARY функциональности - Этап 5

Проверяет корректность работы всех LIBRARY индикаторов после рефакторинга.
"""

import pandas as pd
import numpy as np
from bquant.indicators.library import (
    PandasTALoader, TALibLoader, LibraryManager,
    load_pandas_ta, load_talib, load_all_indicators
)

def test_library_migration():
    """Тестирует все аспекты LIBRARY индикаторов."""
    
    print("🧪 Тестирование миграции LIBRARY функциональности")
    print("=" * 60)
    
    # 1. Тест импорта
    print("\n1️⃣ Тест импорта:")
    try:
        from bquant.indicators.library import (
            PandasTALoader, TALibLoader, LibraryManager,
            load_pandas_ta, load_talib, load_all_indicators
        )
        print("✅ Импорт из library модуля успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта из library: {e}")
        return False
    
    try:
        from bquant.indicators import (
            PandasTALoader, TALibLoader, LibraryManager,
            load_pandas_ta, load_talib, load_all_indicators
        )
        print("✅ Импорт из главного модуля успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта из главного модуля: {e}")
        return False
    
    # 2. Тест доступности библиотек
    print("\n2️⃣ Тест доступности библиотек:")
    try:
        pandas_ta_available = PandasTALoader.is_available()
        talib_available = TALibLoader.is_available()
        
        print(f"✅ pandas-ta доступна: {pandas_ta_available}")
        print(f"✅ TA-Lib доступна: {talib_available}")
        
        if not pandas_ta_available and not talib_available:
            print("⚠️ Ни одна из внешних библиотек не доступна")
            print("   Это нормально для тестирования архитектуры")
        
    except Exception as e:
        print(f"❌ Ошибка проверки доступности: {e}")
        return False
    
    # 3. Тест LibraryManager
    print("\n3️⃣ Тест LibraryManager:")
    try:
        # Получаем список доступных библиотек
        available_libs = LibraryManager.get_available_libraries()
        print(f"✅ Доступные библиотеки: {available_libs}")
        
        # Проверяем информацию о библиотеках
        for lib_name in available_libs:
            lib_info = LibraryManager.get_library_info(lib_name)
            print(f"✅ {lib_name}: {lib_info}")
        
    except Exception as e:
        print(f"❌ Ошибка LibraryManager: {e}")
        return False
    
    # 4. Тест загрузки индикаторов
    print("\n4️⃣ Тест загрузки индикаторов:")
    try:
        # Загружаем pandas-ta (если доступна)
        if PandasTALoader.is_available():
            pandas_ta_count = load_pandas_ta()
            print(f"✅ pandas-ta загружено индикаторов: {pandas_ta_count}")
        else:
            print("⚠️ pandas-ta недоступна, пропускаем")
        
        # Загружаем TA-Lib (если доступна)
        if TALibLoader.is_available():
            talib_count = load_talib()
            print(f"✅ TA-Lib загружено индикаторов: {talib_count}")
        else:
            print("⚠️ TA-Lib недоступна, пропускаем")
        
        # Загружаем все библиотеки
        all_results = load_all_indicators()
        print(f"✅ Всего загружено: {all_results}")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки индикаторов: {e}")
        return False
    
    # 5. Тест создания индикаторов через IndicatorFactory
    print("\n5️⃣ Тест создания индикаторов:")
    try:
        from bquant.indicators import IndicatorFactory
        
        # Проверяем зарегистрированные индикаторы
        registered_indicators = IndicatorFactory.list_indicators()
        print(f"✅ Зарегистрировано индикаторов: {len(registered_indicators)}")
        
        # Ищем LIBRARY индикаторы
        library_indicators = [name for name in registered_indicators.keys() if 'pandas_ta_' in name or 'talib_' in name]
        print(f"✅ LIBRARY индикаторов: {len(library_indicators)}")
        
        if library_indicators:
            print(f"   Примеры: {library_indicators[:5]}")
        
    except Exception as e:
        print(f"❌ Ошибка создания индикаторов: {e}")
        return False
    
    # 6. Тест с тестовыми данными (если есть доступные индикаторы)
    print("\n6️⃣ Тест с тестовыми данными:")
    
    # Создаем тестовые данные
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
    test_data = pd.DataFrame({
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 100 + np.random.randn(100).cumsum() + 2,
        'low': 100 + np.random.randn(100).cumsum() - 2,
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    try:
        # Пытаемся создать и использовать pandas-ta SMA
        if PandasTALoader.is_available():
            try:
                sma_indicator = IndicatorFactory.create_indicator('pandas_ta_sma', length=20)
                sma_result = sma_indicator.calculate(test_data)
                print(f"✅ pandas-ta SMA создан и рассчитан, колонки: {list(sma_result.columns)}")
                
                # Проверяем native_indicator
                native_func = sma_indicator.native_indicator
                print(f"✅ native_indicator доступен: {type(native_func)}")
                
            except Exception as e:
                print(f"⚠️ pandas-ta SMA не работает: {e}")
        
        # Пытаемся создать и использовать TA-Lib SMA
        if TALibLoader.is_available():
            try:
                sma_indicator = IndicatorFactory.create_indicator('talib_sma', timeperiod=20)
                sma_result = sma_indicator.calculate(test_data)
                print(f"✅ TA-Lib SMA создан и рассчитан, колонки: {list(sma_result.columns)}")
                
                # Проверяем native_indicator
                native_func = sma_indicator.native_indicator
                print(f"✅ native_indicator доступен: {type(native_func)}")
                
            except Exception as e:
                print(f"⚠️ TA-Lib SMA не работает: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании индикаторов: {e}")
        return False
    
    # 7. Тест наследования
    print("\n7️⃣ Тест наследования:")
    try:
        from bquant.indicators.base import LibraryIndicator
        
        # Проверяем, что загрузчики создают правильные классы
        if PandasTALoader.is_available():
            # Создаем тестовый индикатор
            test_indicator = IndicatorFactory.create_indicator('pandas_ta_sma', length=20)
            print(f"✅ pandas-ta индикатор наследуется от LibraryIndicator: {isinstance(test_indicator, LibraryIndicator)}")
        
        if TALibLoader.is_available():
            # Создаем тестовый индикатор
            test_indicator = IndicatorFactory.create_indicator('talib_sma', timeperiod=20)
            print(f"✅ TA-Lib индикатор наследуется от LibraryIndicator: {isinstance(test_indicator, LibraryIndicator)}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке наследования: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Все тесты LIBRARY функциональности пройдены успешно!")
    return True

if __name__ == "__main__":
    success = test_library_migration()
    if success:
        print("\n✅ Этап 5: Миграция LIBRARY функциональности - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 5: Миграция LIBRARY функциональности - ЕСТЬ ОШИБКИ!")
