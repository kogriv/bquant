#!/usr/bin/env python3
"""
Демонстрация модульной настройки логирования BQuant

Этот скрипт показывает, как настроить логирование для конкретных модулей:
- Точный контроль по модулям через modules_config
- Исключения для конкретных логгеров через exceptions
- Комбинирование профилей с модульными настройками
"""

from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator

def demo_basic_modules():
    """Демонстрация базовой модульной настройки"""
    print(f"\n{'='*60}")
    print("🔧 БАЗОВАЯ МОДУЛЬНАЯ НАСТРОЙКА")
    print(f"{'='*60}")
    
    # Настройка логирования для конкретных модулей
    setup_logging(
        modules_config={
            'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
            'bquant.indicators': {'console': 'ERROR', 'file': 'DEBUG'},
            'bquant.analysis': {'console': 'INFO', 'file': 'DEBUG'}
        }
    )
    
    nb = NotebookSimulator("Демо модульной настройки")
    nb.info("Настройка: data модули - WARNING+, indicators - ERROR+, analysis - INFO+")
    
    # Демонстрация работы модулей
    from bquant.data.loader import load_ohlcv_data
    # Модуль `indicators/macd.py` удалён вместе с MACDZoneAnalyzer (0.0.5);
    # функция живёт в `calculators`.
    from bquant.indicators.calculators import calculate_macd
    from bquant.analysis.zones import find_support_resistance
    
    nb.step("Тестирование data модуля (должен показывать только WARNING+)")
    try:
        load_ohlcv_data('test.csv', 'XAUUSD', '1h')
    except Exception as e:
        nb.warning(f"Data модуль: {e}")
    
    nb.step("Тестирование indicators модуля (должен показывать только ERROR+)")
    try:
        import pandas as pd
        test_data = pd.DataFrame({'close': [100, 101, 102]})
        calculate_macd(test_data)
        nb.success("Indicators модуль: расчет успешен")
    except Exception as e:
        nb.error(f"Indicators модуль: {e}")
    
    nb.step("Тестирование analysis модуля (должен показывать INFO+)")
    try:
        # Создаем тестовые OHLCV данные
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        test_ohlcv = pd.DataFrame({
            'open': [100] * 50,
            'high': [101] * 50,
            'low': [99] * 50,
            'close': [100] * 50,
            'volume': [1000] * 50
        }, index=dates)
        
        find_support_resistance(test_ohlcv)
        nb.success("Analysis модуль: анализ завершен")
    except Exception as e:
        nb.error(f"Analysis модуль: {e}")

def demo_profile_with_exceptions():
    """Демонстрация профиля с исключениями"""
    print(f"\n{'='*60}")
    print("⚡ ПРОФИЛЬ С ИСКЛЮЧЕНИЯМИ")
    print(f"{'='*60}")
    
    # Используем research профиль, но с исключениями
    setup_logging(
        profile='research',
        exceptions={
            'bquant.data.loader': 'INFO',      # Показать детали загрузки
            'bquant.analysis.zones': 'DEBUG',  # Отладка анализа зон
            'bquant.core.nb': 'INFO'           # NotebookSimulator всегда видим
        }
    )
    
    nb = NotebookSimulator("Демо профиля с исключениями")
    nb.info("Настройка: research профиль + исключения для loader и zones")
    
    # Демонстрация работы с исключениями
    from bquant.data.loader import load_ohlcv_data
    from bquant.analysis.zones import find_support_resistance
    
    nb.step("Data loader с исключением (должен показывать INFO+)")
    try:
        load_ohlcv_data('test.csv', 'XAUUSD', '1h')
    except Exception as e:
        nb.warning(f"Loader с исключением: {e}")
    
    nb.step("Analysis zones с исключением (должен показывать DEBUG+)")
    try:
        import pandas as pd
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        test_ohlcv = pd.DataFrame({
            'open': [100] * 50,
            'high': [101] * 50,
            'low': [99] * 50,
            'close': [100] * 50,
            'volume': [1000] * 50
        }, index=dates)
        
        find_support_resistance(test_ohlcv)
        nb.success("Zones с исключением: анализ завершен")
    except Exception as e:
        nb.error(f"Zones с исключением: {e}")

def demo_complex_modules():
    """Демонстрация сложной модульной настройки"""
    print(f"\n{'='*60}")
    print("🎯 СЛОЖНАЯ МОДУЛЬНАЯ НАСТРОЙКА")
    print(f"{'='*60}")
    
    # Сложная настройка с точным контролем
    setup_logging(
        modules_config={
            'bquant.data.loader': {'console': 'DEBUG', 'file': 'DEBUG'},
            'bquant.data.processor': {'console': 'WARNING', 'file': 'INFO'},
            'bquant.data.validator': {'console': 'ERROR', 'file': 'WARNING'},
            'bquant.indicators.macd': {'console': 'INFO', 'file': 'DEBUG'},
            'bquant.indicators.rsi': {'console': 'WARNING', 'file': 'INFO'},
            'bquant.analysis.zones': {'console': 'DEBUG', 'file': 'DEBUG'},
            'bquant.analysis.candlestick': {'console': 'INFO', 'file': 'INFO'}
        }
    )
    
    nb = NotebookSimulator("Демо сложной модульной настройки")
    nb.info("Настройка: точный контроль каждого подмодуля")
    
    # Демонстрация работы подмодулей
    from bquant.data.loader import load_ohlcv_data
    # Модуль `indicators/macd.py` удалён вместе с MACDZoneAnalyzer (0.0.5);
    # функция живёт в `calculators`.
    from bquant.indicators.calculators import calculate_macd
    from bquant.analysis.zones import find_support_resistance
    
    nb.step("Тестирование различных уровней логирования")
    
    # Data loader - DEBUG (максимальная детализация)
    try:
        load_ohlcv_data('test.csv', 'XAUUSD', '1h')
    except Exception as e:
        nb.info(f"Loader DEBUG: {e}")
    
    # Indicators MACD - INFO (стандартная детализация)
    try:
        import pandas as pd
        test_data = pd.DataFrame({'close': [100, 101, 102]})
        calculate_macd(test_data)
        nb.success("MACD INFO: расчет завершен")
    except Exception as e:
        nb.info(f"MACD INFO: {e}")
    
    # Analysis zones - DEBUG (максимальная детализация)
    try:
        dates = pd.date_range('2024-01-01', periods=50, freq='D')
        test_ohlcv = pd.DataFrame({
            'open': [100] * 50,
            'high': [101] * 50,
            'low': [99] * 50,
            'close': [100] * 50,
            'volume': [1000] * 50
        }, index=dates)
        
        find_support_resistance(test_ohlcv)
        nb.success("Zones DEBUG: анализ завершен")
    except Exception as e:
        nb.info(f"Zones DEBUG: {e}")

def main():
    """Основная функция демонстрации"""
    print("🚀 ДЕМОНСТРАЦИЯ МОДУЛЬНОЙ НАСТРОЙКИ ЛОГИРОВАНИЯ BQUANT")
    print("=" * 60)
    
    # Демонстрация различных подходов
    demo_basic_modules()
    demo_profile_with_exceptions()
    demo_complex_modules()
    
    print(f"\n{'='*60}")
    print("🎉 ДЕМОНСТРАЦИЯ МОДУЛЬНОЙ НАСТРОЙКИ ЗАВЕРШЕНА")
    print("=" * 60)
    print("💡 Теперь вы можете точно настроить логирование для каждого модуля!")
    print("📚 Подробности в документации: docs/api/core/logging.md")

if __name__ == "__main__":
    main()
