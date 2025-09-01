#!/usr/bin/env python3
"""
Демонстрация LoggingConfigurator Fluent API BQuant

Этот скрипт показывает, как использовать Fluent API для сложных конфигураций:
- Базовые preset'ы с профилями
- Модульная настройка через цепочку методов
- Исключения и переопределения
- Комбинирование различных подходов
"""

from bquant.core.logging_config import LoggingConfigurator
from bquant.core.nb import NotebookSimulator

def demo_basic_presets():
    """Демонстрация базовых preset'ов"""
    print(f"\n{'='*60}")
    print("🎯 БАЗОВЫЕ PRESET'Ы")
    print(f"{'='*60}")
    
    # Notebook preset с research профилем
    print("📱 Notebook preset с research профилем:")
    configurator = LoggingConfigurator()
    configurator.preset('notebook', 'research').apply()
    
    nb = NotebookSimulator("Демо notebook preset")
    nb.info("Настройка: notebook + research профиль")
    
    # Development preset с focused профилем
    print("\n🔧 Development preset с focused профилем:")
    configurator = LoggingConfigurator()
    configurator.preset('development', 'focused').apply()
    
    nb = NotebookSimulator("Демо development preset")
    nb.info("Настройка: development + focused профиль")
    
    # Production preset с critical профилем
    print("\n🚀 Production preset с critical профилем:")
    configurator = LoggingConfigurator()
    configurator.preset('production', 'critical').apply()
    
    nb = NotebookSimulator("Демо production preset")
    nb.info("Настройка: production + critical профиль")

def demo_module_configuration():
    """Демонстрация модульной конфигурации"""
    print(f"\n{'='*60}")
    print("🔧 МОДУЛЬНАЯ КОНФИГУРАЦИЯ")
    print(f"{'='*60}")
    
    # Настройка отдельных модулей
    print("📊 Настройка модулей через цепочку методов:")
    configurator = (
        LoggingConfigurator()
            .preset('development', 'focused')           # Базовый preset
            .module('bquant.data')                     # Настройка data модуля
                .console('WARNING')                    # WARNING+ в консоль
                .file('DEBUG')                         # DEBUG+ в файл
            .module('bquant.indicators')               # Настройка indicators
                .console('ERROR')                      # ERROR+ в консоль
                .file('INFO')                          # INFO+ в файл
            .apply()                                   # Применить настройки
    )
    
    nb = NotebookSimulator("Демо модульной конфигурации")
    nb.info("Настройка: data модули - WARNING+, indicators - ERROR+")
    
    # Демонстрация работы настроенных модулей
    from bquant.data.loader import load_ohlcv_data
    from bquant.indicators.macd import calculate_macd
    
    nb.step("Тестирование data модуля (WARNING+)")
    try:
        load_ohlcv_data('test.csv', 'XAUUSD', '1h')
    except Exception as e:
        nb.warning(f"Data модуль: {e}")
    
    nb.step("Тестирование indicators модуля (ERROR+)")
    try:
        import pandas as pd
        test_data = pd.DataFrame({'close': [100, 101, 102]})
        calculate_macd(test_data)
        nb.success("Indicators модуль: расчет успешен")
    except Exception as e:
        nb.error(f"Indicators модуль: {e}")

def demo_exceptions_and_overrides():
    """Демонстрация исключений и переопределений"""
    print(f"\n{'='*60}")
    print("⚡ ИСКЛЮЧЕНИЯ И ПЕРЕОПРЕДЕЛЕНИЯ")
    print(f"{'='*60}")
    
    # Сложная конфигурация с исключениями
    print("🎭 Сложная конфигурация с исключениями:")
    configurator = (
        LoggingConfigurator()
            .preset('notebook', 'research')            # Базовый preset
            .module('bquant.analysis')                 # Переопределение analysis
                .console('DEBUG')                      # DEBUG+ в консоль
                .file('DEBUG')                         # DEBUG+ в файл
            .exception('bquant.data.loader', 'INFO')   # Исключение для loader
            .exception('bquant.core.nb', 'INFO')       # NotebookSimulator всегда видим
            .apply()                                   # Применить настройки
    )
    
    nb = NotebookSimulator("Демо исключений и переопределений")
    nb.info("Настройка: research профиль + analysis DEBUG + loader INFO")
    
    # Демонстрация работы с исключениями
    from bquant.data.loader import load_ohlcv_data
    from bquant.analysis.zones import find_support_resistance
    
    nb.step("Data loader с исключением (INFO+)")
    try:
        load_ohlcv_data('test.csv', 'XAUUSD', '1h')
    except Exception as e:
        nb.info(f"Loader с исключением: {e}")
    
    nb.step("Analysis zones с переопределением (DEBUG+)")
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
        nb.success("Zones с переопределением: анализ завершен")
    except Exception as e:
        nb.info(f"Zones с переопределением: {e}")

def demo_advanced_patterns():
    """Демонстрация продвинутых паттернов"""
    print(f"\n{'='*60}")
    print("🚀 ПРОДВИНУТЫЕ ПАТТЕРНЫ")
    print(f"{'='*60}")
    
    # Паттерн "разные уровни для разных сценариев"
    print("🎨 Паттерн 'разные уровни для разных сценариев':")
    configurator = (
        LoggingConfigurator()
            .preset('development', 'clean')             # Базовый preset
            .module('bquant.core')                     # Core модули - детально
                .console('DEBUG')
                .file('DEBUG')
            .module('bquant.data')                     # Data модули - тихо
                .console('ERROR')
                .file('WARNING')
            .module('bquant.indicators')               # Indicators - средне
                .console('WARNING')
                .file('INFO')
            .module('bquant.analysis')                 # Analysis - детально
                .console('INFO')
                .file('DEBUG')
            .exception('bquant.data.loader', 'WARNING') # Loader - немного громче
            .apply()
    )
    
    nb = NotebookSimulator("Демо продвинутых паттернов")
    nb.info("Настройка: дифференцированные уровни для разных типов модулей")
    
    # Демонстрация дифференцированного логирования
    from bquant.data.loader import load_ohlcv_data
    from bquant.indicators.macd import calculate_macd
    from bquant.analysis.zones import find_support_resistance
    
    nb.step("Тестирование дифференцированного логирования")
    
    # Data loader - ERROR (тихо)
    try:
        load_ohlcv_data('test.csv', 'XAUUSD', '1h')
    except Exception as e:
        nb.error(f"Data loader ERROR: {e}")
    
    # Indicators MACD - WARNING (средне)
    try:
        import pandas as pd
        test_data = pd.DataFrame({'close': [100, 101, 102]})
        calculate_macd(test_data)
        nb.success("MACD WARNING: расчет завершен")
    except Exception as e:
        nb.warning(f"MACD WARNING: {e}")
    
    # Analysis zones - INFO (детально)
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
        nb.success("Zones INFO: анализ завершен")
    except Exception as e:
        nb.info(f"Zones INFO: {e}")

def main():
    """Основная функция демонстрации"""
    print("🚀 ДЕМОНСТРАЦИЯ LOGGINGCONFIGURATOR FLUENT API BQUANT")
    print("=" * 60)
    
    # Демонстрация различных возможностей
    demo_basic_presets()
    demo_module_configuration()
    demo_exceptions_and_overrides()
    demo_advanced_patterns()
    
    print(f"\n{'='*60}")
    print("🎉 ДЕМОНСТРАЦИЯ FLUENT API ЗАВЕРШЕНА")
    print("=" * 60)
    print("💡 Теперь вы можете создавать сложные конфигурации через цепочку методов!")
    print("📚 Подробности в документации: docs/api/core/logging.md")

if __name__ == "__main__":
    main()
