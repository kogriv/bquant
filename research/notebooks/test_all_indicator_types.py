"""
Тест всех типов индикаторов - Этап 8

Проверяет работу всех типов индикаторов:
- PRELOADED
- CUSTOM (BUILTIN)
- LIBRARY (если доступны)
"""

import pandas as pd
import numpy as np

def test_all_indicator_types():
    """Тестирует все типы индикаторов."""
    
    print("🧪 Тестирование всех типов индикаторов - Этап 8")
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
    
    # 1. Тест PRELOADED индикаторов
    print("\n1️⃣ Тест PRELOADED индикаторов:")
    if not test_preloaded_indicators(test_data):
        return False
    
    # 2. Тест CUSTOM (BUILTIN) индикаторов
    print("\n2️⃣ Тест CUSTOM (BUILTIN) индикаторов:")
    if not test_custom_indicators(test_data):
        return False
    
    # 3. Тест LIBRARY индикаторов (если доступны)
    print("\n3️⃣ Тест LIBRARY индикаторов:")
    if not test_library_indicators(test_data):
        return False
    
    # 4. Тест интеграции всех типов
    print("\n4️⃣ Тест интеграции всех типов:")
    if not test_integration(test_data):
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Все тесты типов индикаторов пройдены успешно!")
    return True


def test_preloaded_indicators(test_data: pd.DataFrame) -> bool:
    """Тестирует PRELOADED индикаторы."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ PRELOADED индикаторы:")
        
        # Создаем MACD PRELOADED
        macd_preloaded = IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal'])
        print(f"      MACD PRELOADED: {type(macd_preloaded).__name__}")
        
        # Проверяем работу
        result = macd_preloaded.calculate(test_data)
        print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
        
        # Проверяем статистику
        stats = macd_preloaded.get_statistics(test_data)
        print(f"        ✅ Статистика: {len(stats)} колонок")
        
        # Проверяем тренды
        trending_up = macd_preloaded.is_trending_up(test_data, column='macd')
        trending_down = macd_preloaded.is_trending_down(test_data, column='macd')
        print(f"        ✅ Тренды: up={trending_up}, down={trending_down}")
        
        # Проверяем пересечения
        crossovers = macd_preloaded.get_crossovers(test_data)
        print(f"        ✅ Пересечения: {len(crossovers['bullish'])} бычьих, {len(crossovers['bearish'])} медвежьих")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования PRELOADED: {e}")
        return False


def test_custom_indicators(test_data: pd.DataFrame) -> bool:
    """Тестирует CUSTOM (BUILTIN) индикаторы."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ CUSTOM (BUILTIN) индикаторы:")
        
        # Тестируем SMA
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        print(f"      SMA(20): {type(sma).__name__}")
        
        result = sma.calculate(test_data)
        print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
        
        stats = sma.get_statistics(test_data)
        print(f"        ✅ Статистика: {len(stats)} колонок")
        
        # Тестируем EMA
        ema = IndicatorFactory.create('custom', 'ema', period=20)
        print(f"      EMA(20): {type(ema).__name__}")
        
        result = ema.calculate(test_data)
        print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
        
        # Тестируем RSI
        rsi = IndicatorFactory.create('custom', 'rsi', period=14)
        print(f"      RSI(14): {type(rsi).__name__}")
        
        result = rsi.calculate(test_data)
        print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
        
        # Тестируем MACD
        macd = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        print(f"      MACD(12,26,9): {type(macd).__name__}")
        
        result = macd.calculate(test_data)
        print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
        
        # Тестируем Bollinger Bands
        bb = IndicatorFactory.create('custom', 'bbands', period=20, std_dev=2.0)
        print(f"      Bollinger Bands(20,2.0): {type(bb).__name__}")
        
        result = bb.calculate(test_data)
        print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования CUSTOM: {e}")
        return False


def test_library_indicators(test_data: pd.DataFrame) -> bool:
    """Тестирует LIBRARY индикаторы (если доступны)."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ LIBRARY индикаторы:")
        
        # Пытаемся создать pandas-ta индикаторы
        try:
            sma_pandas_ta = IndicatorFactory.create('pandas_ta', 'sma', length=20)
            print(f"      pandas-ta SMA(20): {type(sma_pandas_ta).__name__}")
            
            result = sma_pandas_ta.calculate(test_data)
            print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
            
            # Проверяем доступ к нативному индикатору
            if hasattr(sma_pandas_ta, 'native_indicator'):
                print(f"        ✅ Нативный индикатор: {type(sma_pandas_ta.native_indicator).__name__}")
            
        except Exception as e:
            print(f"      ⚠️ pandas-ta SMA недоступен: {e}")
        
        # Пытаемся создать TA-Lib индикаторы
        try:
            sma_talib = IndicatorFactory.create('talib', 'sma', timeperiod=20)
            print(f"      TA-Lib SMA(20): {type(sma_talib).__name__}")
            
            result = sma_talib.calculate(test_data)
            print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
            
            # Проверяем доступ к нативному индикатору
            if hasattr(sma_talib, 'native_indicator'):
                print(f"        ✅ Нативный индикатор: {type(sma_talib.native_indicator).__name__}")
            
        except Exception as e:
            print(f"      ⚠️ TA-Lib SMA недоступен: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования LIBRARY: {e}")
        return False


def test_integration(test_data: pd.DataFrame) -> bool:
    """Тестирует интеграцию всех типов индикаторов."""
    
    try:
        from bquant.indicators import IndicatorFactory
        
        print("   ✅ Интеграция всех типов:")
        
        # Создаем индикаторы всех типов
        indicators = {
            'PRELOADED': IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal']),
            'CUSTOM_SMA': IndicatorFactory.create('custom', 'sma', period=20),
            'CUSTOM_EMA': IndicatorFactory.create('custom', 'ema', period=20),
            'CUSTOM_RSI': IndicatorFactory.create('custom', 'rsi', period=14),
        }
        
        # Пытаемся добавить LIBRARY индикаторы
        try:
            indicators['LIBRARY_PANDAS_TA'] = IndicatorFactory.create('pandas_ta', 'sma', length=20)
        except:
            pass
        
        try:
            indicators['LIBRARY_TALIB'] = IndicatorFactory.create('talib', 'sma', timeperiod=20)
        except:
            pass
        
        print(f"      Всего индикаторов для тестирования: {len(indicators)}")
        
        # Тестируем единообразный интерфейс
        for name, indicator in indicators.items():
            print(f"      {name}: {type(indicator).__name__}")
            
            # Все должны уметь валидировать данные
            is_valid = indicator.validate_data(test_data)
            print(f"        ✅ Валидация: {is_valid}")
            
            # Все должны уметь рассчитывать
            result = indicator.calculate(test_data)
            print(f"        ✅ Расчет: {len(result.data.columns)} колонок")
            
            # Все должны уметь давать статистику
            stats = indicator.get_statistics(test_data)
            print(f"        ✅ Статистика: {len(stats)} колонок")
            
            # Проверяем, что результат имеет правильную структуру
            assert hasattr(result, 'data'), f"Результат {name} должен иметь атрибут data"
            assert hasattr(result, 'config'), f"Результат {name} должен иметь атрибут config"
            assert hasattr(result, 'metadata'), f"Результат {name} должен иметь атрибут metadata"
        
        # Тестируем получение информации через IndicatorFactory
        print("      Информация через IndicatorFactory:")
        all_indicators = IndicatorFactory.list_indicators()
        print(f"        ✅ Всего зарегистрированных: {len(all_indicators)}")
        
        for source in ['preloaded', 'custom', 'library']:
            indicators_by_source = IndicatorFactory.get_indicators_by_source(source)
            print(f"        ✅ {source}: {len(indicators_by_source)} индикаторов")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка тестирования интеграции: {e}")
        return False


if __name__ == "__main__":
    success = test_all_indicator_types()
    if success:
        print("\n✅ Этап 8: Тестирование всех типов индикаторов - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 8: Тестирование всех типов индикаторов - ЕСТЬ ОШИБКИ!")
