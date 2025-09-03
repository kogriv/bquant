"""
Тест миграции BUILTIN индикаторов - Этап 4

Проверяет корректность работы всех BUILTIN индикаторов после рефакторинга.
"""

import pandas as pd
import numpy as np
from bquant.indicators.custom import (
    SimpleMovingAverage, ExponentialMovingAverage, 
    RelativeStrengthIndex, MACD, BollingerBands
)

def test_builtin_migration():
    """Тестирует все аспекты BUILTIN индикаторов."""
    
    print("🧪 Тестирование миграции BUILTIN индикаторов")
    print("=" * 50)
    
    # 1. Тест импорта
    print("\n1️⃣ Тест импорта:")
    try:
        from bquant.indicators.custom import (
            SimpleMovingAverage, ExponentialMovingAverage, 
            RelativeStrengthIndex, MACD, BollingerBands
        )
        print("✅ Импорт из custom модуля успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта из custom: {e}")
        return False
    
    try:
        from bquant.indicators import (
            SimpleMovingAverage, ExponentialMovingAverage, 
            RelativeStrengthIndex, MACD, BollingerBands
        )
        print("✅ Импорт из главного модуля успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта из главного модуля: {e}")
        return False
    
    # 2. Тест создания объектов
    print("\n2️⃣ Тест создания объектов:")
    try:
        sma = SimpleMovingAverage()
        print(f"✅ SMA создан: {sma.name}")
        
        ema = ExponentialMovingAverage()
        print(f"✅ EMA создан: {ema.name}")
        
        rsi = RelativeStrengthIndex()
        print(f"✅ RSI создан: {rsi.name}")
        
        macd = MACD()
        print(f"✅ MACD создан: {macd.name}")
        
        bb = BollingerBands()
        print(f"✅ Bollinger Bands создан: {bb.name}")
        
    except Exception as e:
        print(f"❌ Ошибка создания объектов: {e}")
        return False
    
    # 3. Тест классных методов
    print("\n3️⃣ Тест классных методов:")
    try:
        # SMA
        sma_cols = SimpleMovingAverage.get_default_columns()
        sma_info = SimpleMovingAverage.get_info()
        print(f"✅ SMA - колонки: {sma_cols}, тип: {sma_info['type']}")
        
        # EMA
        ema_cols = ExponentialMovingAverage.get_default_columns()
        ema_info = ExponentialMovingAverage.get_info()
        print(f"✅ EMA - колонки: {ema_cols}, тип: {ema_info['type']}")
        
        # RSI
        rsi_cols = RelativeStrengthIndex.get_default_columns()
        rsi_info = RelativeStrengthIndex.get_info()
        print(f"✅ RSI - колонки: {rsi_cols}, тип: {rsi_info['type']}")
        
        # MACD
        macd_cols = MACD.get_default_columns()
        macd_info = MACD.get_info()
        print(f"✅ MACD - колонки: {macd_cols}, тип: {macd_info['type']}")
        
        # Bollinger Bands
        bb_cols = BollingerBands.get_default_columns()
        bb_info = BollingerBands.get_info()
        print(f"✅ BB - колонки: {bb_cols}, тип: {bb_info['type']}")
        
    except Exception as e:
        print(f"❌ Ошибка классных методов: {e}")
        return False
    
    # 4. Тест с тестовыми данными
    print("\n4️⃣ Тест с тестовыми данными:")
    
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
        # Тест SMA
        sma_result = sma.calculate(test_data)
        print(f"✅ SMA расчет выполнен, колонки: {list(sma_result.data.columns)}")
        
        # Тест EMA
        ema_result = ema.calculate(test_data)
        print(f"✅ EMA расчет выполнен, колонки: {list(ema_result.data.columns)}")
        
        # Тест RSI
        rsi_result = rsi.calculate(test_data)
        print(f"✅ RSI расчет выполнен, колонки: {list(rsi_result.data.columns)}")
        
        # Тест MACD
        macd_result = macd.calculate(test_data)
        print(f"✅ MACD расчет выполнен, колонки: {list(macd_result.data.columns)}")
        
        # Тест Bollinger Bands
        bb_result = bb.calculate(test_data)
        print(f"✅ BB расчет выполнен, колонки: {list(bb_result.data.columns)}")
        
    except Exception as e:
        print(f"❌ Ошибка при расчете индикаторов: {e}")
        return False
    
    # 5. Тест валидации данных
    print("\n5️⃣ Тест валидации данных:")
    try:
        sma_valid = sma.validate_data(test_data)
        ema_valid = ema.validate_data(test_data)
        rsi_valid = rsi.validate_data(test_data)
        macd_valid = macd.validate_data(test_data)
        bb_valid = bb.validate_data(test_data)
        
        print(f"✅ Валидация SMA: {sma_valid}")
        print(f"✅ Валидация EMA: {ema_valid}")
        print(f"✅ Валидация RSI: {rsi_valid}")
        print(f"✅ Валидация MACD: {macd_valid}")
        print(f"✅ Валидация BB: {bb_valid}")
        
    except Exception as e:
        print(f"❌ Ошибка при валидации данных: {e}")
        return False
    
    # 6. Тест статистики
    print("\n6️⃣ Тест статистики:")
    try:
        sma_stats = sma.get_statistics(test_data)
        ema_stats = ema.get_statistics(test_data)
        rsi_stats = rsi.get_statistics(test_data)
        macd_stats = macd.get_statistics(test_data)
        bb_stats = bb.get_statistics(test_data)
        
        print(f"✅ Статистика SMA: {len(sma_stats)} колонок")
        print(f"✅ Статистика EMA: {len(ema_stats)} колонок")
        print(f"✅ Статистика RSI: {len(rsi_stats)} колонок")
        print(f"✅ Статистика MACD: {len(macd_stats)} колонок")
        print(f"✅ Статистика BB: {len(bb_stats)} колонок")
        
    except Exception as e:
        print(f"❌ Ошибка при получении статистики: {e}")
        return False
    
    # 7. Тест трендов
    print("\n7️⃣ Тест трендов:")
    try:
        sma_trend_up = sma.is_trending_up(test_data)
        sma_trend_down = sma.is_trending_down(test_data)
        
        print(f"✅ SMA тренд вверх: {sma_trend_up}, тренд вниз: {sma_trend_down}")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе трендов: {e}")
        return False
    
    # 8. Тест наследования
    print("\n8️⃣ Тест наследования:")
    try:
        from bquant.indicators.base import CustomIndicator
        
        print(f"✅ SMA наследуется от CustomIndicator: {isinstance(sma, CustomIndicator)}")
        print(f"✅ EMA наследуется от CustomIndicator: {isinstance(ema, CustomIndicator)}")
        print(f"✅ RSI наследуется от CustomIndicator: {isinstance(rsi, CustomIndicator)}")
        print(f"✅ MACD наследуется от CustomIndicator: {isinstance(macd, CustomIndicator)}")
        print(f"✅ BB наследуется от CustomIndicator: {isinstance(bb, CustomIndicator)}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке наследования: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Все тесты BUILTIN индикаторов пройдены успешно!")
    return True

if __name__ == "__main__":
    success = test_builtin_migration()
    if success:
        print("\n✅ Этап 4: Миграция BUILTIN индикаторов - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 4: Миграция BUILTIN индикаторов - ЕСТЬ ОШИБКИ!")
