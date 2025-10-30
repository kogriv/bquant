#!/usr/bin/env python3
import os

# =============================================================================
# Примечание: ранее здесь использовались env-переменные для подавления шума
# внешних библиотек. После внедрения quiet-init на уровне пакета они не требуются.
# Блок оставлен как справочный комментарий.
# =============================================================================
"""
Хардкодные варианты конфигурации логирования BQuant

Этот скрипт содержит все варианты конфигурации в виде готового кода.
Для тестирования конкретного варианта - раскомментируйте нужный блок,
остальные оставьте закомментированными.

Все варианты готовы для копирования в ваш код!
"""

from bquant.core.logging_config import setup_logging, LoggingConfigurator
import logging
from bquant.indicators.calculators import calculate_macd

import pandas as pd
import numpy as np

# =============================================================================
# 🚀 ФУНКЦИЯ ДЛЯ ДЕМОНСТРАЦИИ ЛОГИРОВАНИЯ
# =============================================================================

def demo_logging_behavior():
    """Демонстрирует различные уровни логирования"""
    # logger = logging.getLogger(__name__)
    logger = logging.getLogger('bquant')
    
    logger.info("=== ДЕМОНСТРАЦИЯ РАЗЛИЧНЫХ УРОВНЕЙ ЛОГИРОВАНИЯ ===")
    
    # 1. Загрузка данных (обычно INFO уровень)
    logger.info("1. Загрузка тестовых данных")
    try:
        from bquant.data.loader import load_ohlcv_data
        data = load_ohlcv_data('nonexistent_file.csv', 'XAUUSD', '1h')
        logger.info("Данные загружены успешно")
    except Exception as e:
        logger.warning(f"Предупреждение при загрузке: {e}")
    
    # 2. Расчет индикаторов (обычно INFO уровень)
    logger.info("2. Расчет MACD")
    try:
        # Создаем тестовые данные
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        test_data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        }, index=dates)
        
        macd_result = calculate_macd(test_data)
        logger.info("MACD рассчитан успешно")
    except Exception as e:
        logger.error(f"Ошибка расчета MACD: {e}")
    
    # 3. Анализ зон (обычно INFO уровень)
    logger.info("3. Анализ зон")
    try:
        # Создаем тестовые OHLCV данные
        test_ohlcv = pd.DataFrame({
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 101,
            'low': np.random.randn(100).cumsum() + 99,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)

        from bquant.analysis.zones import find_support_resistance
        zones_result = find_support_resistance(test_ohlcv)
        logger.info(f"Анализ зон завершен, найдено {len(zones_result)} зон")
    except Exception as e:
        logger.error(f"Ошибка анализа зон: {e}")
    
    # 4. Искусственные сообщения для демонстрации уровней
    logger.info("4. Демонстрация уровней логирования")
    
    # DEBUG сообщение (видно только при DEBUG+)
    logger.debug("DEBUG сообщение: детальная информация для отладки")
    
    # INFO сообщение (видно при INFO+)
    logger.info("INFO сообщение: общая информация о процессе")
    
    # WARNING сообщение (видно при WARNING+)
    logger.warning("WARNING сообщение: предупреждение о потенциальной проблеме")
    
    # ERROR сообщение (видно при ERROR+)
    logger.error("ERROR сообщение: ошибка, требующая внимания")
    
    logger.info("Демонстрация завершена!")

# =============================================================================
# 🎯 ВАРИАНТ 1: ПРОСТЫЕ ПРОФИЛИ
# =============================================================================

# =============================================================================
# ВАРИАНТ 1A: RESEARCH ПРОФИЛЬ (скрывает технические детали)
# "research": {
#         "description": "Для research скриптов - скрыть технические детали",
#         "modules_config": {
#             "bquant.data": {"console": "WARNING", "file": "INFO"},
#             "bquant.data.loader": {"console": "WARNING", "file": "INFO"},
#             "bquant.data.processor": {"console": "WARNING", "file": "INFO"},
#             "bquant.data.validator": {"console": "WARNING", "file": "INFO"},
#             "bquant.indicators": {"console": "WARNING", "file": "INFO"}, 
#             "bquant.analysis": {"console": "INFO", "file": "INFO"}
#         }
# =============================================================================
# setup_logging(profile='research')
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 1B: CLEAN ПРОФИЛЬ (минимальный вывод)
# "clean": {
#         "description": "Минимум шума - только ошибки в консоль",
#         "modules_config": {
#             "bquant.data": {"console": "ERROR", "file": "INFO"},
#             "bquant.indicators": {"console": "ERROR", "file": "INFO"},
#             "bquant.analysis": {"console": "ERROR", "file": "INFO"}
#         }
# =============================================================================
# setup_logging(profile='clean')
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 1C: DEBUG ПРОФИЛЬ (максимальная детализация)
# "debug": {
#         "description": "Все детали для отладки",
#         "modules_config": {
#             "bquant": {"console": "DEBUG", "file": "DEBUG"}
#         }
# =============================================================================
# setup_logging(profile='debug')
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 1D: VERBOSE ПРОФИЛЬ (DEBUG везде)
# "verbose": {
#         "description": "Максимум информации везде",
#         "modules_config": {
#             "bquant": {"console": "DEBUG", "file": "DEBUG"}
#         }
# =============================================================================
# setup_logging(profile='verbose')
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 1E: FOCUSED ПРОФИЛЬ (DEBUG для core, INFO для остальных)
# "focused": {
#         "description": "Детали только для core, остальное - стандартно",
#         "modules_config": {
#             "bquant.core": {"console": "DEBUG", "file": "DEBUG"},
#             "bquant.data": {"console": "INFO", "file": "DEBUG"},
#             "bquant.indicators": {"console": "INFO", "file": "DEBUG"}
#         }
# =============================================================================
# setup_logging(profile='focused')
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 1F: CRITICAL ПРОФИЛЬ (только критические события)
# "critical": {
#         "description": "Только критические события",
#         "modules_config": {
#             "bquant": {"console": "ERROR", "file": "ERROR"}
#         }
# =============================================================================
# setup_logging(profile='critical')
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 1G: AUDIT ПРОФИЛЬ (полное логирование в файл, минимум в консоль)
# "audit": {
#         "description": "Полный аудит в файл, минимум в консоль",
#         "modules_config": {
#             "bquant": {"console": "ERROR", "file": "INFO"}
#         }
# =============================================================================
# setup_logging(profile='audit')
# demo_logging_behavior()

# =============================================================================
# 🎯 ВАРИАНТ 2: МОДУЛЬНЫЕ НАСТРОЙКИ
# =============================================================================

# =============================================================================
# ВАРИАНТ 2A: DATA МОДУЛИ ТИХИЕ, ANALYSIS ИНФОРМАТИВНЫЙ
# =============================================================================
# setup_logging(
#     modules_config={
#         'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
#         'bquant.indicators': {'console': 'WARNING', 'file': 'INFO'},
#         'bquant.analysis': {'console': 'INFO', 'file': 'INFO'}
#     }
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 2B: CORE В DEBUG, ОСТАЛЬНЫЕ В INFO
# =============================================================================
# setup_logging(
#     modules_config={
#         'bquant.core': {'console': 'DEBUG', 'file': 'DEBUG'},
#         'bquant.data': {'console': 'INFO', 'file': 'INFO'},
#         'bquant.indicators': {'console': 'INFO', 'file': 'INFO'},
#         'bquant.analysis': {'console': 'INFO', 'file': 'INFO'}
#     }
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 2C: ТОЧНАЯ НАСТРОЙКА ДЛЯ КОНКРЕТНЫХ ПОДМОДУЛЕЙ
# =============================================================================
# setup_logging(
#     modules_config={
#         'bquant.data.loader': {'console': 'WARNING', 'file': 'DEBUG'},
#         'bquant.data.processor': {'console': 'INFO', 'file': 'INFO'},
#         'bquant.analysis.zones': {'console': 'DEBUG', 'file': 'DEBUG'},
#         'bquant.analysis.candlestick': {'console': 'INFO', 'file': 'INFO'}
#     }
# )
# demo_logging_behavior()

# =============================================================================
# 🎯 ВАРИАНТ 3: ПРОФИЛИ С ИСКЛЮЧЕНИЯМИ
# =============================================================================

# =============================================================================
# ВАРИАНТ 3A: RESEARCH ПРОФИЛЬ + LOADER В DEBUG
# =============================================================================
# setup_logging(
#     profile='research',
#     exceptions={
#         'bquant.data.loader': 'DEBUG',
#         'bquant.core.nb': 'INFO'
#     }
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 3B: CLEAN ПРОФИЛЬ + ANALYSIS В INFO
# =============================================================================
# setup_logging(
#     profile='clean',
#     exceptions={
#         'bquant.analysis': 'INFO',
#         'bquant.core.nb': 'INFO'
#     }
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 3C: CRITICAL ПРОФИЛЬ + LOADER В WARNING
# =============================================================================
# setup_logging(
#     profile='critical',
#     exceptions={
#         'bquant.data.loader': 'WARNING',
#         'bquant.core.nb': 'INFO'
#     }
# )
# demo_logging_behavior()

# =============================================================================
# 🎯 ВАРИАНТ 4: FLUENT API КОНФИГУРАЦИИ
# =============================================================================

# =============================================================================
# ВАРИАНТ 4A (АКТИВНЫЙ): NOTEBOOK QUIET — профиль 'clean' без env-трюков
# =============================================================================
setup_logging(
    profile='clean',
    exceptions={
        'bquant.core.nb': 'INFO'  # Базовые сообщения NotebookSimulator видны
    }
)
demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 4B: DEVELOPMENT + FOCUSED + DATA WARNING
# =============================================================================
# configurator = (
#     LoggingConfigurator()
#         .preset('development', 'focused')
#         .module('bquant.data').console('WARNING').file('INFO')
#         .apply()
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 4C: PRODUCTION + AUDIT + NB INFO
# =============================================================================
# configurator = (
#     LoggingConfigurator()
#         .preset('production', 'audit')
#         .exception('bquant.core.nb', 'INFO')
#         .apply()
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 4D: СЛОЖНАЯ КОНФИГУРАЦИЯ С МОДУЛЯМИ И ИСКЛЮЧЕНИЯМИ
# =============================================================================
# configurator = (
#     LoggingConfigurator()
#         .preset('development', 'clean')
#         .module('bquant.core').console('DEBUG').file('DEBUG')
#         .module('bquant.data').console('ERROR').file('WARNING')
#         .module('bquant.indicators').console('WARNING').file('INFO')
#         .module('bquant.analysis').console('INFO').file('DEBUG')
#         .exception('bquant.data.loader', 'WARNING')
#         .apply()
# )
# demo_logging_behavior()

# =============================================================================
# 🎯 ДОБАВЛЕНО: ВАРИАНТ 4E: QUIET ДЛЯ NOTEBOOK (МИНИМУМ В КОНСОЛЬ)
# =============================================================================
# Цель: настроить очень тихий режим для ноутбуков, чтобы не видеть простыню логов,
# но при этом сохранить запись подробностей в файл (по умолчанию file_level=INFO).
# Два подхода ниже — используйте ЛЮБОЙ ОДИН, раскомментировав блок.

# --- Подход A: Один вызов через profile='clean' + точечные исключения ---
# setup_logging(
#     profile='clean',
#     exceptions={
#         'bquant.core.nb': 'INFO'  # оставить видимым базовый вывод NotebookSimulator
#     }
# )
# demo_logging_behavior()

# --- Подход B: Fluent API — preset 'notebook' + глобальное приглушение ---
configurator = (
    LoggingConfigurator()
        .preset('notebook', 'research')  # базовый research-профиль для ноутбуков
        .module('bquant').console('ERROR')  # глобально: в консоль только ошибки
        .exception('bquant.core.nb', 'INFO')  # NotebookSimulator: базовые сообщения видим
        .apply()
)
demo_logging_behavior()

# =============================================================================
# 🎯 ВАРИАНТ 5: КАСТОМНЫЕ НАСТРОЙКИ
# =============================================================================

# =============================================================================
# ВАРИАНТ 5A: РАЗНЫЕ УРОВНИ ДЛЯ КОНСОЛИ И ФАЙЛА
# =============================================================================
# setup_logging(
#     console_level='WARNING',
#     file_level='DEBUG',
#     log_to_file=True
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 5B: ТОЛЬКО ФАЙЛОВОЕ ЛОГИРОВАНИЕ
# =============================================================================
# setup_logging(
#     console_enabled=False,
#     file_level='INFO',
#     log_to_file=True
# )
# demo_logging_behavior()

# =============================================================================
# ВАРИАНТ 5C: ТОЛЬКО КОНСОЛЬНОЕ ЛОГИРОВАНИЕ
# =============================================================================
# setup_logging(
#     console_level='INFO',
#     log_to_file=False
# )
# demo_logging_behavior()

# =============================================================================
# 💡 ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ
# =============================================================================
"""
КАК ИСПОЛЬЗОВАТЬ ЭТОТ СКРИПТ:

1. ДЛЯ ТЕСТИРОВАНИЯ КОНКРЕТНОГО ВАРИАНТА:
   - Закомментируйте текущий активный вариант (setup_logging(profile='clean'))
   - Раскомментируйте нужный вам вариант
   - Запустите скрипт

2. ДЛЯ КОПИРОВАНИЯ В ВАШ КОД:
   - Скопируйте нужный блок конфигурации
   - Уберите комментарии
   - Вставьте в начало вашего скрипта ДО импорта модулей

3. ПОРЯДОК НАСТРОЙКИ:
   - Сначала настройка логирования
   - Потом импорт модулей
   - Потом основной код

4. ПРИМЕР ИСПОЛЬЗОВАНИЯ:
   # Скопируйте нужную конфигурацию сюда
   setup_logging(profile='research')
   
   # Теперь импортируйте модули
   from bquant.data.loader import load_ohlcv_data
   
   # Ваш код...
"""
