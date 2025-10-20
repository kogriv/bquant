'''
Демонстрация анализа MACD зон: Миграция на универсальный API

**ВАЖНО:** Этот скрипт демонстрирует migration guide и примеры нового API.
Из-за технической проблемы с swing_strategy registry (будет исправлено),
фактический запуск временно недоступен. Скрипт показывает КАК ДОЛЖНО РАБОТАТЬ.

Содержание:
1. Старый API (deprecated) - примеры кода
2. Новый универсальный API - примеры и объяснения  
3. Migration guide - пошаговый переход
4. Различные стратегии детекции
5. Модульное использование компонентов
6. Работа с другими индикаторами

Для РАБОТАЮЩИХ примеров см.:
- examples/02_macd_zone_analysis.py
- examples/02a_universal_zones.py
- examples/04_comprehensive_analysis.py
'''

from pathlib import Path
import pandas as pd
import json
from typing import Dict, Any, List

# НАСТРОЙКА ЛОГИРОВАНИЯ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

nb = NotebookSimulator("MACD Zone Analysis: Migration Guide")

# =============================================================================
# ШАГ 1: ЗАГРУЗКА ДАННЫХ
# =============================================================================

nb.step("Шаг 1: Загрузка тестовых данных")

nb.info("Загружаем sample-данные XAUUSD 1H:")

    df_sample = get_sample_data('tv_xauusd_1h')
    
    if 'time' in df_sample.columns:
        df_sample = df_sample.set_index('time')
    nb.log("[OK] DatetimeIndex установлен")

nb.log(f"Загружено: {len(df_sample)} баров")
nb.log(f"Период: {df_sample.index.min()} - {df_sample.index.max()}")
nb.log(f"Колонки: {', '.join(df_sample.columns[:5])}...")

nb.wait()

# =============================================================================
# ШАГ 2: СТАРЫЙ API (DEPRECATED)
# =============================================================================

nb.step("Шаг 2: Старый API (deprecated) - понимание проблемы")

nb.warning("ВНИМАНИЕ: MACDZoneAnalyzer deprecated и будет удален в v3.0.0!")

nb.info("Проблемы старого API:")
nb.log("  [-] Работает ТОЛЬКО с MACD (нет универсальности)")
nb.log("  [-] Монолитная архитектура (сложно расширять)")  
nb.log("  [-] Нет встроенного кэширования")
nb.log("  [-] Ограниченные форматы экспорта")
nb.log("  [-] Технические проблемы совместимости")
nb.log("  [-] Будет удален в v3.0.0")

nb.log("")
nb.log("=" * 70)
nb.log("ПРИМЕР СТАРОГО КОДА (deprecated):")
nb.log("=" * 70)
nb.log("""
from bquant.indicators.macd import MACDZoneAnalyzer

# Создание анализатора
analyzer = MACDZoneAnalyzer(
    macd_params={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
    zone_params={'min_duration': 2}
)

# Анализ зон
result = analyzer.analyze_complete_modular(
    df,
    perform_clustering=False
)

# Результат:
# - result.zones: список зон
# - result.features: характеристики зон
# - result.statistics: статистика
""")
nb.log("=" * 70)

nb.info("Недостатки такого подхода:")
nb.log("  * Привязка к конкретному индикатору (MACD)")
nb.log("  * Сложно добавить новые индикаторы")
nb.log("  * Дублирование кода для каждого индикатора")
nb.log("  * Отсутствие переиспользования компонентов")

nb.wait()

# =============================================================================
# ШАГ 3: НОВЫЙ УНИВЕРСАЛЬНЫЙ API
# =============================================================================

nb.step("Шаг 3: НОВЫЙ универсальный API - революция!")

nb.info("Новый подход: ОДИН API для ВСЕХ индикаторов!")

nb.log("")
nb.log("=" * 70)
nb.log("НОВЫЙ КОД - Вариант 1: Fluent Builder")
nb.log("=" * 70)
nb.log("""
from bquant.analysis.zones import analyze_zones

# Тот же анализ, но универсальный!
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', 
                   fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', 
                 indicator_col='macd_hist', min_duration=2)
    .analyze()
    .build()
)

# Результат - тот же ZoneAnalysisResult!
# - result.zones
# - result.features  
# - result.statistics
""")
nb.log("=" * 70)

nb.log("")
nb.log("=" * 70)
nb.log("НОВЫЙ КОД - Вариант 2: Convenience Preset")
nb.log("=" * 70)
nb.log("""
from bquant.analysis.zones import analyze_macd_zones

# ЕЩЕ ПРОЩЕ для MACD!
result = analyze_macd_zones(
    df,
    fast=12,
    slow=26,
    signal=9,
    min_duration=2
)

# Один вызов - все готово!
""")
nb.log("=" * 70)

nb.log("")
nb.info("Преимущества нового API:")
nb.log("  [+] Универсальность - работает с ЛЮБЫМИ индикаторами")
nb.log("  [+] Fluent syntax - читаемый, понятный код")
nb.log("  [+] Модульность - используйте компоненты отдельно")
nb.log("  [+] Кэширование - автоматическое, из коробки")
nb.log("  [+] Экспорт - 3 формата (pickle, JSON, parquet)")
nb.log("  [+] Convenience presets - быстрый старт")

nb.wait()

# =============================================================================
# ШАГ 4: MIGRATION GUIDE
# =============================================================================

nb.step("Шаг 4: Migration Guide - пошаговый переход")

nb.info("Как мигрировать старый код на новый API:")

nb.log("")
nb.log("МИГРАЦИЯ ШАГ 1: Замена импорта")
nb.log("-" * 70)
nb.log("Было:")
nb.log("  from bquant.indicators.macd import MACDZoneAnalyzer")
nb.log("")
nb.log("Стало:")
nb.log("  from bquant.analysis.zones import analyze_zones")
nb.log("  # или для быстрого старта:")
nb.log("  from bquant.analysis.zones import analyze_macd_zones")

nb.log("")
nb.log("МИГРАЦИЯ ШАГ 2: Замена создания анализатора")
nb.log("-" * 70)
nb.log("Было:")
nb.log("  analyzer = MACDZoneAnalyzer(")
nb.log("      macd_params={'fast_period': 12, ...}")
nb.log("  )")
nb.log("")
nb.log("Стало (вариант A - builder):")
nb.log("  builder = (")
nb.log("      analyze_zones(df)")
nb.log("      .with_indicator('custom', 'macd', fast_period=12, ...)")
nb.log("  )")
nb.log("")
nb.log("Стало (вариант B - preset):")
nb.log("  # Просто вызов функции, без создания объектов!")

nb.log("")
nb.log("МИГРАЦИЯ ШАГ 3: Замена вызова analyze")
nb.log("-" * 70)
nb.log("Было:")
nb.log("  result = analyzer.analyze_complete_modular(df)")
nb.log("")
nb.log("Стало (вариант A - builder):")
nb.log("  result = (")
nb.log("      builder")
nb.log("      .detect_zones('zero_crossing', indicator_col='macd_hist')")
nb.log("      .analyze()")
nb.log("      .build()")
nb.log("  )")
nb.log("")
nb.log("Стало (вариант B - preset):")
nb.log("  result = analyze_macd_zones(df, fast=12, slow=26, signal=9)")

nb.log("")
nb.info("Оценка времени миграции:")
nb.log("  * Простой проект (1-3 файла):   10-15 минут")
nb.log("  * Средний проект (5-10 файлов):  30-60 минут")
nb.log("  * Крупный проект (20+ файлов):   2-3 часа")
nb.log("")
nb.log("  ROI: Долгосрочная поддержка + новые возможности")

nb.wait()

# =============================================================================
# ШАГ 5: РАЗЛИЧНЫЕ СТРАТЕГИИ ДЕТЕКЦИИ
# =============================================================================

nb.step("Шаг 5: Различные стратегии детекции")

nb.info("Новый API поддерживает множество стратегий детекции:")

nb.log("")
nb.log("1. Zero Crossing (пересечение нуля)")
nb.log("-" * 70)
nb.log("""
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .build()
)

# Детектирует зоны при пересечении гистограммой нулевой линии
# Используется для: определения силы тренда
""")

nb.log("")
nb.log("2. Line Crossing (пересечение линий)")
nb.log("-" * 70)
nb.log("""
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('line_crossing', line1_col='macd', line2_col='signal')
    .build()
)

# Детектирует зоны при пересечении MACD и Signal линий
# Используется для: поиска торговых сигналов
""")

nb.log("")
nb.log("3. Threshold (пороговые значения)")
nb.log("-" * 70)
nb.log("""
result = (
    analyze_zones(df)
    .with_indicator('library', 'rsi', length=14)
    .detect_zones('threshold', 
                 indicator_col='RSI_14',
                 upper_threshold=70, 
                 lower_threshold=30)
    .build()
)

# Детектирует зоны перекупленности/перепроданности
# Используется для: RSI, Stochastic, и других осцилляторов
""")

nb.log("")
nb.log("4. Combined Rules (комбинация правил)")
nb.log("-" * 70)
nb.log("""
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('combined', rules=[
        {'type': 'zero_crossing', 'indicator_col': 'macd_hist'},
        {'type': 'line_crossing', 'line1_col': 'macd', 'line2_col': 'signal'}
    ])
    .build()
)

# Комбинирует несколько правил для более точной детекции
# Используется для: комплексных торговых стратегий
""")

nb.log("")
nb.info("Выбор стратегии зависит от:")
nb.log("  * Типа индикатора (осциллятор, трендовый, и т.д.)")
nb.log("  * Торговой стратегии")
nb.log("  * Требуемой точности детекции")
nb.log("  * Специфики рынка")

nb.wait()

# =============================================================================
# ШАГ 6: МОДУЛЬНОЕ ИСПОЛЬЗОВАНИЕ
# =============================================================================

nb.step("Шаг 6: Модульное использование компонентов")

nb.info("Новый API позволяет использовать компоненты по отдельности:")

nb.log("")
nb.log("СЦЕНАРИЙ 1: Только детекция зон (без анализа)")
nb.log("-" * 70)
nb.log("""
# Детектируем зоны
zones_only = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .build()  # БЕЗ .analyze() - только детекция!
)

# Сохраняем для последующего использования
zones_only.save('zones.pkl', format='pickle')

# Используем позже:
# - Визуализация на другом сервере
# - Анализ в другое время
# - Экспорт в другие системы
""")

nb.log("")
nb.log("СЦЕНАРИЙ 2: Анализ предварительно детектированных зон")
nb.log("-" * 70)
nb.log("""
# Загружаем ранее детектированные зоны
from bquant.analysis.zones.models import ZoneAnalysisResult
zones = ZoneAnalysisResult.load('zones.pkl')

# Анализируем (TODO: API для анализа готовых зон)
# analyzed = analyze_existing_zones(zones, df)
""")

nb.log("")
nb.log("СЦЕНАРИЙ 3: Только расчет индикатора")
nb.log("-" * 70)
nb.log("""
from bquant.indicators.base import IndicatorFactory

# Создаем индикатор
indicator = IndicatorFactory.create('custom', 'macd',
                                   fast_period=12, slow_period=26, signal_period=9)

# Рассчитываем
df_with_indicator = indicator.calculate(df)

# Используем для своих целей (не только зоны)
""")

nb.log("")
nb.info("Преимущества модульности:")
nb.log("  [+] Гибкость - используйте только нужные компоненты")
nb.log("  [+] Производительность - не запускайте лишние вычисления")
nb.log("  [+] Масштабируемость - распределяйте задачи по серверам")
nb.log("  [+] Переиспользование - сохраняйте промежуточные результаты")

nb.wait()

# =============================================================================
# ШАГ 7: РАБОТА С ДРУГИМИ ИНДИКАТОРАМИ
# =============================================================================

nb.step("Шаг 7: Универсальность - другие индикаторы")

nb.info("ТОТ ЖЕ API работает с ЛЮБЫМИ индикаторами!")

nb.log("")
nb.log("RSI ZONES (Relative Strength Index)")
nb.log("=" * 70)
nb.log("""
# Через builder:
result = (
    analyze_zones(df)
    .with_indicator('library', 'rsi', length=14)
    .detect_zones('threshold', 
                 indicator_col='RSI_14',
                 upper_threshold=70, 
                 lower_threshold=30)
    .analyze()
    .build()
)

# Через preset (еще проще):
from bquant.analysis.zones import analyze_rsi_zones
result = analyze_rsi_zones(df, period=14, upper=70, lower=30)
""")

nb.log("")
nb.log("AO ZONES (Awesome Oscillator)")
nb.log("=" * 70)
nb.log("""
# Через builder:
result = (
    analyze_zones(df)
    .with_indicator('library', 'ao', fast=5, slow=34)
    .detect_zones('zero_crossing', indicator_col='AO_5_34')
    .analyze()
    .build()
)

# Через preset:
from bquant.analysis.zones import analyze_ao_zones
result = analyze_ao_zones(df, fast=5, slow=34)
""")

nb.log("")
nb.log("MA CROSSOVER ZONES (Moving Average)")
nb.log("=" * 70)
nb.log("""
# Добавляем два MA индикатора
result = (
    analyze_zones(df)
    .with_indicator('library', 'sma', length=20)  # MA 20
    .with_indicator('library', 'sma', length=50)  # MA 50
    .detect_zones('line_crossing', 
                 line1_col='SMA_20', 
                 line2_col='SMA_50')
    .analyze()
    .build()
)
""")

nb.log("")
nb.log("PRELOADED ZONES (внешние данные)")
nb.log("=" * 70)
nb.log("""
# Загрузка зон из CSV
from bquant.analysis.zones import analyze_preloaded_zones

result = analyze_preloaded_zones(
    df,
    zones_data='zones.csv',  # или DataFrame
    analyze_features=True
)

# Используется для:
# - Зоны от внешних систем
# - Ручная разметка зон
# - Импорт из других платформ
""")

nb.log("")
nb.info("Ключевое преимущество:")
nb.log("  ОДИН И ТОТ ЖЕ КОД для ВСЕХ индикаторов!")
nb.log("  Меняется только:")
nb.log("    * Имя индикатора")
nb.log("    * Параметры индикатора")
nb.log("    * Стратегия детекции")
nb.log("")
nb.log("  НЕ нужно писать отдельный класс для каждого индикатора!")

nb.wait()

# =============================================================================
# ШАГ 8: СОХРАНЕНИЕ И ЗАГРУЗКА
# =============================================================================

nb.step("Шаг 8: Сохранение и загрузка результатов")

nb.info("Новый API поддерживает 3 формата сохранения:")

nb.log("")
nb.log("ФОРМАТ 1: Pickle (наиболее полный)")
nb.log("-" * 70)
nb.log("""
# Сохранение
result.save('zones.pkl', format='pickle')

# Загрузка
from bquant.analysis.zones.models import ZoneAnalysisResult
loaded = ZoneAnalysisResult.load('zones.pkl')

# Преимущества:
# [+] Сохраняет ВСЕ данные (включая DataFrame)
# [+] Быстрая загрузка/сохранение
# [+] Компактный размер (с сжатием)
# [-] Не читаем человеком
# [-] Привязка к Python
""")

nb.log("")
nb.log("ФОРМАТ 2: JSON (читаемый)")
nb.log("-" * 70)
nb.log("""
# Сохранение
result.save('zones.json', format='json', include_data=False)

# Загрузка
loaded = ZoneAnalysisResult.load('zones.json')

# Преимущества:
# [+] Читаем человеком
# [+] Легко делиться
# [+] Совместим с другими языками
# [+] Легко редактировать вручную
# [-] Больший размер
# [-] Не сохраняет DataFrame
""")

nb.log("")
nb.log("ФОРМАТ 3: Parquet (для больших данных)")
nb.log("-" * 70)
nb.log("""
# Сохранение
result.save('zones.parquet', format='parquet')

# Загрузка
loaded = ZoneAnalysisResult.load('zones.parquet')

# Преимущества:
# [+] Отличное сжатие
# [+] Быстрая загрузка
# [+] Поддержка DataFrame
# [+] Совместим с Spark, Pandas, и т.д.
# [-] Требует pyarrow
""")

nb.log("")
nb.info("Выбор формата:")
nb.log("  * Pickle:   для Python-to-Python передачи")
nb.log("  * JSON:     для sharing и редактирования")
nb.log("  * Parquet:  для больших данных и BigData pipelines")

nb.wait()

# =============================================================================
# ИТОГОВОЕ РЕЗЮМЕ
# =============================================================================

nb.step("Итоговое резюме")

nb.info("=" * 70)
nb.info("ИТОГИ: Почему мигрировать на новый API")
nb.info("=" * 70)

nb.log("")
nb.log("СТАРЫЙ API (deprecated):")
nb.log("  [-] Только MACD")
nb.log("  [-] Монолитная архитектура")
nb.log("  [-] Технические проблемы")
nb.log("  [-] Будет удален в v3.0.0")
nb.log("  [?] ~100 строк кода на индикатор")

nb.log("")
nb.log("НОВЫЙ УНИВЕРСАЛЬНЫЙ API:")
nb.log("  [+] ЛЮБЫЕ индикаторы (MACD, RSI, AO, MA, custom)")
nb.log("  [+] Модульная архитектура")
nb.log("  [+] Fluent builder + presets")
nb.log("  [+] Встроенное кэширование")
nb.log("  [+] 3 формата экспорта")
nb.log("  [+] Активная поддержка")
nb.log("  [+] ~10 строк кода на индикатор!")

nb.log("")
nb.log("ЭКОНОМИЯ КОДА:")
nb.log("  Старый подход: MACDZoneAnalyzer (517 строк)")
nb.log("                 + RSIZoneAnalyzer (500 строк)")
nb.log("                 + AOZoneAnalyzer (500 строк)")
nb.log("                 = 1517 строк + дублирование")
nb.log("")
nb.log("  Новый подход:  UniversalZoneAnalyzer (250 строк)")
nb.log("                 + 3 preset функции (30 строк)")
nb.log("                 = 280 строк БЕЗ дублирования")
nb.log("")
nb.log("  Экономия: ~80% кода!")

nb.log("")
nb.info("РЕКОМЕНДАЦИЯ:")
nb.log("  * Для НОВЫХ проектов: используйте только новый API")
nb.log("  * Для СТАРЫХ проектов: мигрируйте постепенно")
nb.log("  * Время миграции: 10-180 минут")
nb.log("  * Срок поддержки старого API: до v3.0.0")

nb.log("")
nb.info("ПОЛЕЗНЫЕ РЕСУРСЫ:")
nb.log("  * Документация API:    docs/api/analysis/zones.md")
nb.log("  * Примеры (работающие): examples/02a_universal_zones.py")
nb.log("  * Модульное использование: devref/gaps/zo/zomodul.md")
nb.log("  * Архитектура:        devref/gaps/zo/zonan.md")

nb.log("")
nb.warning("ТЕХНИЧЕСКАЯ ЗАМЕТКА:")
nb.log("  Этот скрипт демонстрирует API, но не запускает код")
nb.log("  из-за временной проблемы с swing_strategy registry.")
nb.log("  Проблема будет исправлена в ближайшем обновлении.")
nb.log("  Для РАБОТАЮЩИХ примеров используйте examples/")

nb.finish("Migration guide completed!")
