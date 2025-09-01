#!/usr/bin/env python3
"""
Быстрый старт с логированием BQuant

Этот скрипт содержит готовые заготовки для различных сценариев:
- Простые профили для быстрого старта
- Базовые модульные настройки
- Готовые конфигурации для типовых задач
"""

from bquant.core.logging_config import setup_logging, LoggingConfigurator
from bquant.core.nb import NotebookSimulator

# =============================================================================
# 🚀 ГОТОВЫЕ ЗАГОТОВКИ ДЛЯ БЫСТРОГО СТАРТА
# =============================================================================

def quick_research_setup():
    """Быстрая настройка для research скриптов"""
    setup_logging(profile='research')
    return "✅ Research профиль: WARNING+ в консоль, INFO+ в файл"

def quick_development_setup():
    """Быстрая настройка для development"""
    setup_logging(profile='verbose')
    return "✅ Verbose профиль: DEBUG+ везде для максимальной детализации"

def quick_production_setup():
    """Быстрая настройка для production"""
    setup_logging(profile='critical')
    return "✅ Critical профиль: только ERROR+ сообщения"

def quick_clean_setup():
    """Быстрая настройка для тихих сценариев"""
    setup_logging(profile='clean')
    return "✅ Clean профиль: ERROR+ в консоль, INFO+ в файл"

# =============================================================================
# 🔧 ГОТОВЫЕ МОДУЛЬНЫЕ НАСТРОЙКИ
# =============================================================================

def data_modules_quiet():
    """Тихая настройка для data модулей"""
    setup_logging(
        modules_config={
            'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
            'bquant.indicators': {'console': 'WARNING', 'file': 'INFO'},
            'bquant.analysis': {'console': 'INFO', 'file': 'INFO'}
        }
    )
    return "✅ Data модули тихие, analysis информативный"

def core_debug_others_info():
    """DEBUG для core, INFO для остальных"""
    setup_logging(
        modules_config={
            'bquant.core': {'console': 'DEBUG', 'file': 'DEBUG'},
            'bquant.data': {'console': 'INFO', 'file': 'INFO'},
            'bquant.indicators': {'console': 'INFO', 'file': 'INFO'},
            'bquant.analysis': {'console': 'INFO', 'file': 'INFO'}
        }
    )
    return "✅ Core модули в DEBUG, остальные в INFO"

def custom_data_analysis():
    """Кастомная настройка для data и analysis"""
    setup_logging(
        modules_config={
            'bquant.data.loader': {'console': 'WARNING', 'file': 'DEBUG'},
            'bquant.data.processor': {'console': 'INFO', 'file': 'INFO'},
            'bquant.analysis.zones': {'console': 'DEBUG', 'file': 'DEBUG'},
            'bquant.analysis.candlestick': {'console': 'INFO', 'file': 'INFO'}
        }
    )
    return "✅ Точная настройка для конкретных подмодулей"

# =============================================================================
# 🎭 ГОТОВЫЕ КОМБИНАЦИИ С ИСКЛЮЧЕНИЯМИ
# =============================================================================

def research_with_loader_debug():
    """Research профиль + loader в DEBUG"""
    setup_logging(
        profile='research',
        exceptions={
            'bquant.data.loader': 'DEBUG',
            'bquant.core.nb': 'INFO'
        }
    )
    return "✅ Research профиль + loader в DEBUG + nb всегда видим"

def clean_with_analysis_info():
    """Clean профиль + analysis в INFO"""
    setup_logging(
        profile='clean',
        exceptions={
            'bquant.analysis': 'INFO',
            'bquant.core.nb': 'INFO'
        }
    )
    return "✅ Clean профиль + analysis в INFO + nb всегда видим"

def critical_with_loader_warning():
    """Critical профиль + loader в WARNING"""
    setup_logging(
        profile='critical',
        exceptions={
            'bquant.data.loader': 'WARNING',
            'bquant.core.nb': 'INFO'
        }
    )
    return "✅ Critical профиль + loader в WARNING + nb всегда видим"

# =============================================================================
# 🚀 ГОТОВЫЕ FLUENT API КОНФИГУРАЦИИ
# =============================================================================

def fluent_notebook_research():
    """Fluent API для notebook с research профилем"""
    configurator = (
        LoggingConfigurator()
            .preset('notebook', 'research')
            .exception('bquant.data.loader', 'INFO')
            .apply()
    )
    return "✅ Fluent API: notebook + research + loader INFO"

def fluent_development_focused():
    """Fluent API для development с focused профилем"""
    configurator = (
        LoggingConfigurator()
            .preset('development', 'focused')
            .module('bquant.data').console('WARNING').file('INFO')
            .apply()
    )
    return "✅ Fluent API: development + focused + data WARNING"

def fluent_production_audit():
    """Fluent API для production с audit профилем"""
    configurator = (
        LoggingConfigurator()
            .preset('production', 'audit')
            .exception('bquant.core.nb', 'INFO')
            .apply()
    )
    return "✅ Fluent API: production + audit + nb INFO"

# =============================================================================
# 📋 ДЕМОНСТРАЦИЯ ВСЕХ ЗАГОТОВОК
# =============================================================================

def demo_all_quick_starts():
    """Демонстрация всех готовых заготовок"""
    nb = NotebookSimulator("Демо готовых заготовок")
    
    print("🚀 ГОТОВЫЕ ЗАГОТОВКИ ДЛЯ БЫСТРОГО СТАРТА")
    print("=" * 60)
    
    # Простые профили
    nb.step("Простые профили")
    print(quick_research_setup())
    print(quick_development_setup())
    print(quick_production_setup())
    print(quick_clean_setup())
    
    # Модульные настройки
    nb.step("Модульные настройки")
    print(data_modules_quiet())
    print(core_debug_others_info())
    print(custom_data_analysis())
    
    # Комбинации с исключениями
    nb.step("Комбинации с исключениями")
    print(research_with_loader_debug())
    print(clean_with_analysis_info())
    print(critical_with_loader_warning())
    
    # Fluent API
    nb.step("Fluent API конфигурации")
    print(fluent_notebook_research())
    print(fluent_development_focused())
    print(fluent_production_audit())
    
    nb.success("Все заготовки продемонстрированы!")

def main():
    """Основная функция"""
    print("🚀 БЫСТРЫЙ СТАРТ С ЛОГИРОВАНИЕМ BQUANT")
    print("=" * 60)
    print("💡 Этот скрипт содержит готовые заготовки для различных сценариев")
    print("📋 Скопируйте нужную функцию в ваш код и используйте!")
    print("=" * 60)
    
    demo_all_quick_starts()
    
    print(f"\n{'='*60}")
    print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)
    print("💡 Теперь у вас есть готовые заготовки для быстрого старта!")
    print("📚 Подробности в документации: docs/api/core/logging.md")

if __name__ == "__main__":
    main()
