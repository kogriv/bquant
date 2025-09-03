"""
Тест миграции PRELOADED индикаторов - Этап 3

Проверяет корректность работы MACDPreloadedIndicator после рефакторинга.
"""

import pandas as pd
import numpy as np
from bquant.indicators import MACDPreloadedIndicator

def test_preloaded_migration():
    """Тестирует все аспекты PRELOADED индикаторов."""
    
    print("🧪 Тестирование миграции PRELOADED индикаторов")
    print("=" * 50)
    
    # 1. Тест импорта
    print("\n1️⃣ Тест импорта:")
    try:
        from bquant.indicators.preloaded import MACDPreloadedIndicator
        print("✅ Импорт из preloaded модуля успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта из preloaded: {e}")
        return False
    
    try:
        from bquant.indicators import MACDPreloadedIndicator
        print("✅ Импорт из главного модуля успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта из главного модуля: {e}")
        return False
    
    # 2. Тест создания объекта
    print("\n2️⃣ Тест создания объекта:")
    try:
        macd_default = MACDPreloadedIndicator()
        print(f"✅ Объект по умолчанию создан: {macd_default.name}")
        print(f"   Колонки по умолчанию: {macd_default.get_default_columns()}")
    except Exception as e:
        print(f"❌ Ошибка создания объекта по умолчанию: {e}")
        return False
    
    try:
        macd_custom = MACDPreloadedIndicator(required_columns=['macd', 'signal', 'histogram'])
        print(f"✅ Объект с кастомными колонками создан: {macd_custom.name}")
        print(f"   Кастомные колонки: {macd_custom.get_required_columns()}")
    except Exception as e:
        print(f"❌ Ошибка создания объекта с кастомными колонками: {e}")
        return False
    
    # 3. Тест классных методов
    print("\n3️⃣ Тест классных методов:")
    try:
        default_cols = MACDPreloadedIndicator.get_default_columns()
        print(f"✅ get_default_columns(): {default_cols}")
        
        info = MACDPreloadedIndicator.get_info()
        print(f"✅ get_info() - название: {info['name']}")
        print(f"   Тип: {info['type']}")
        print(f"   Описание: {info['description'][:50]}...")
    except Exception as e:
        print(f"❌ Ошибка классных методов: {e}")
        return False
    
    # 4. Тест с тестовыми данными
    print("\n4️⃣ Тест с тестовыми данными:")
    
    # Создаем тестовые данные
    test_data = pd.DataFrame({
        'macd': [1.0, 1.1, 1.2, 1.3, 1.4],
        'signal': [0.9, 1.0, 1.1, 1.2, 1.3],
        'histogram': [0.1, 0.1, 0.1, 0.1, 0.1]
    })
    
    try:
        # Тест валидации
        validation = macd_default.validate_data(test_data)
        print(f"✅ Валидация данных: {validation}")
        
        # Тест расчета
        result = macd_default.calculate(test_data)
        print(f"✅ Расчет выполнен, колонки: {list(result.data.columns)}")
        print(f"   Количество строк: {len(result.data)}")
        
        # Тест статистики
        stats = macd_default.get_statistics(test_data)
        print(f"✅ Статистика получена для колонок: {list(stats.keys())}")
        
        # Тест трендов
        trend_up = macd_default.is_trending_up(test_data)
        trend_down = macd_default.is_trending_down(test_data)
        print(f"✅ Тренд вверх: {trend_up}, Тренд вниз: {trend_down}")
        
        # Тест пересечений
        crossovers = macd_default.get_crossovers(test_data)
        print(f"✅ Пересечения: {crossovers['bullish_crossovers']} бычьих, {crossovers['bearish_crossovers']} медвежьих")
        
    except Exception as e:
        print(f"❌ Ошибка при работе с данными: {e}")
        return False
    
    # 5. Тест с данными без histogram
    print("\n5️⃣ Тест с данными без histogram:")
    try:
        data_no_hist = test_data[['macd', 'signal']]
        validation_no_hist = macd_default.validate_data(data_no_hist)
        print(f"✅ Валидация данных без histogram: {validation_no_hist}")
        
        result_no_hist = macd_default.calculate(data_no_hist)
        print(f"✅ Расчет без histogram, колонки: {list(result_no_hist.data.columns)}")
        
    except Exception as e:
        print(f"❌ Ошибка при работе с данными без histogram: {e}")
        return False
    
    # 6. Тест с кастомными колонками
    print("\n6️⃣ Тест с кастомными колонками:")
    try:
        macd_only = MACDPreloadedIndicator(required_columns=['macd'])
        validation_macd_only = macd_only.validate_data(test_data)
        print(f"✅ Валидация только MACD: {validation_macd_only}")
        
        result_macd_only = macd_only.calculate(test_data)
        print(f"✅ Расчет только MACD, колонки: {list(result_macd_only.data.columns)}")
        
    except Exception as e:
        print(f"❌ Ошибка при работе с кастомными колонками: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Все тесты PRELOADED индикаторов пройдены успешно!")
    return True

if __name__ == "__main__":
    success = test_preloaded_migration()
    if success:
        print("\n✅ Этап 3: Миграция PRELOADED индикаторов - ЗАВЕРШЕН УСПЕШНО!")
    else:
        print("\n❌ Этап 3: Миграция PRELOADED индикаторов - ЕСТЬ ОШИБКИ!")
