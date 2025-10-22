from pathlib import Path
import pandas as pd
import numpy as np

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.core.config import get_data_dir, set_data_dir, reset_directories_to_defaults
from bquant.data.samples import get_sample_data

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация создания MACD через IndicatorFactory")

nb.step("Создание MACD через IndicatorFactory")

# Загружаем тестовые данные
df_sample_tv = get_sample_data('tv_xauusd_1h')
nb.log(f"Загружены тестовые данные: {len(df_sample_tv)} строк")

nb.wait()

# Демонстрация разных способов создания MACD через фабрику
nb.substep("Способы создания MACD через фабрику")

from bquant.indicators import IndicatorFactory, IndicatorSource

# 1. Создание PRELOADED MACD
nb.info("1. PRELOADED MACD:")
macd_preloaded = IndicatorFactory.create('preloaded', 'macd_preloaded')
nb.log(f"Created: {macd_preloaded.name}")
nb.log(f"Type: {type(macd_preloaded)}")
nb.log(f"Source: {macd_preloaded.config.source}")

# 2. Создание CUSTOM MACD
nb.info("2. CUSTOM MACD:")
macd_custom = IndicatorFactory.create('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
nb.log(f"Created: {macd_custom.name}")
nb.log(f"Type: {type(macd_custom)}")
nb.log(f"Source: {macd_custom.config.source}")

# 3. Попытка создания LIBRARY MACD (pandas_ta)
nb.info("3. LIBRARY MACD (pandas_ta):")
try:
    macd_library = IndicatorFactory.create('pandas_ta', 'pandas_ta_macd', fast=12, slow=26, signal=9)
    nb.log(f"Created: {macd_library.name}")
    nb.log(f"Type: {type(macd_library)}")
    nb.log(f"Source: {macd_library.config.source}")
    library_available = True
except Exception as e:
    nb.log(f"Failed to create pandas_ta MACD: {e}")
    nb.log("pandas_ta MACD not available, will skip this part")
    library_available = False

nb.wait()

# Демонстрация доступных методов объектов
nb.substep("Доступные методы созданных объектов")

# PRELOADED MACD методы
nb.info("PRELOADED MACD методы:")
nb.log(f"name: {macd_preloaded.name}")
nb.log(f"config: {macd_preloaded.config}")
nb.log(f"get_default_columns(): {macd_preloaded.get_default_columns()}")
nb.log(f"get_info(): {macd_preloaded.get_info()}")

# CUSTOM MACD методы
nb.info("CUSTOM MACD методы:")
nb.log(f"name: {macd_custom.name}")
nb.log(f"config: {macd_custom.config}")
nb.log(f"get_default_columns(): {macd_custom.get_default_columns()}")
nb.log(f"get_info(): {macd_custom.get_info()}")

# LIBRARY MACD методы (если доступен)
if library_available:
    nb.info("LIBRARY MACD методы:")
    nb.log(f"name: {macd_library.name}")
    nb.log(f"config: {macd_library.config}")
    try:
        nb.log(f"get_default_columns(): {macd_library.get_default_columns()}")
    except NotImplementedError:
        nb.log("get_default_columns(): [метод не реализован в этом классе]")
    try:
        nb.log(f"get_info(): {macd_library.get_info()}")
    except NotImplementedError:
        nb.log("get_info(): [метод не реализован в этом классе]")

nb.wait()

# Расчет индикаторов
nb.substep("Расчет MACD индикаторов")

# PRELOADED
nb.info("Calculating PRELOADED MACD:")
macd_preloaded_result = macd_preloaded.calculate(df_sample_tv)
nb.log(f"Result columns: {list(macd_preloaded_result.data.columns)}")
nb.log(f"Result rows: {len(macd_preloaded_result.data)}")
nb.log(f"Metadata: {macd_preloaded_result.metadata}")

# CUSTOM
nb.info("Calculating CUSTOM MACD:")
macd_custom_result = macd_custom.calculate(df_sample_tv)
nb.log(f"Result columns: {list(macd_custom_result.data.columns)}")
nb.log(f"Result rows: {len(macd_custom_result.data)}")
nb.log(f"Metadata: {macd_custom_result.metadata}")

# LIBRARY (если доступен)
if library_available:
    nb.info("Calculating LIBRARY MACD:")
    macd_library_result = macd_library.calculate(df_sample_tv)
    
    # Проверяем тип результата
    if hasattr(macd_library_result, 'data'):
        # Это IndicatorResult
        nb.log(f"Result columns: {list(macd_library_result.data.columns)}")
        nb.log(f"Result rows: {len(macd_library_result.data)}")
        nb.log(f"Metadata: {macd_library_result.metadata}")
    else:
        # Это DataFrame
        nb.log(f"Result columns: {list(macd_library_result.columns)}")
        nb.log(f"Result rows: {len(macd_library_result)}")
        nb.log("Metadata: [не доступен для DataFrame результата]")

nb.wait()

# Сравнение результатов
nb.substep("Сравнение результатов MACD")

# Создаем сводную таблицу
comparison_df = pd.DataFrame()

# Добавляем данные
if 'macd' in macd_preloaded_result.data.columns:
    comparison_df['PRELOADED_MACD'] = macd_preloaded_result.data['macd']
if 'macd' in macd_custom_result.data.columns:
    comparison_df['CUSTOM_MACD'] = macd_custom_result.data['macd']
if library_available:
    # Проверяем тип результата и извлекаем данные
    if hasattr(macd_library_result, 'data'):
        # Это IndicatorResult
        library_data = macd_library_result.data
    else:
        # Это DataFrame
        library_data = macd_library_result
    
    # Ищем колонку с MACD данными
    macd_col = None
    for col in library_data.columns:
        if 'macd' in col.lower() and 'signal' not in col.lower() and 'hist' not in col.lower():
            macd_col = col
            break
    
    if macd_col:
        comparison_df['LIBRARY_MACD'] = library_data[macd_col]

# Показываем последние значения
nb.log("MACD Values Comparison (last 10 values):")
nb.log(comparison_df.tail(10).to_string())

# Статистика
nb.info("MACD Statistics:")
for col in comparison_df.columns:
    values = comparison_df[col].dropna()
    if len(values) > 0:
        nb.log(f"{col}: count={len(values)}, min={values.min():.6f}, max={values.max():.6f}, mean={values.mean():.6f}")

nb.wait()

# Демонстрация методов анализа (если доступны)
nb.substep("Методы анализа индикаторов")

# Проверяем доступные методы анализа
if hasattr(macd_preloaded, 'validate_data'):
    nb.info("PRELOADED validate_data method:")
    is_valid = macd_preloaded.validate_data(df_sample_tv)
    nb.log(f"Data validation: {is_valid}")

if hasattr(macd_custom, 'validate_data'):
    nb.info("CUSTOM validate_data method:")
    is_valid = macd_custom.validate_data(df_sample_tv)
    nb.log(f"Data validation: {is_valid}")

if library_available and hasattr(macd_library, 'validate_data'):
    nb.info("LIBRARY validate_data method:")
    is_valid = macd_library.validate_data(df_sample_tv)
    nb.log(f"Data validation: {is_valid}")

# Проверяем методы анализа трендов
if hasattr(macd_preloaded, 'is_trending_up'):
    nb.info("PRELOADED trend analysis:")
    trending_up = macd_preloaded.is_trending_up(df_sample_tv, column='macd')
    trending_down = macd_preloaded.is_trending_down(df_sample_tv, column='macd')
    nb.log(f"Trending up: {trending_up}, Trending down: {trending_down}")

if hasattr(macd_custom, 'is_trending_up'):
    nb.info("CUSTOM trend analysis:")
    trending_up = macd_custom.is_trending_up(df_sample_tv, column='macd')
    trending_down = macd_custom.is_trending_down(df_sample_tv, column='macd')
    nb.log(f"Trending up: {trending_up}, Trending down: {trending_down}")

if library_available and hasattr(macd_library, 'is_trending_up'):
    nb.info("LIBRARY trend analysis:")
    trending_up = macd_library.is_trending_up(df_sample_tv, column='macd')
    trending_down = macd_library.is_trending_down(df_sample_tv, column='macd')
    nb.log(f"Trending up: {trending_up}, Trending down: {trending_down}")

nb.wait()

# Заключение
nb.step("Заключение")

nb.info("Показаны способы создания MACD через IndicatorFactory:")
nb.info("[OK] PRELOADED - готовые данные")
nb.info("[OK] CUSTOM - собственная реализация")
if library_available:
    nb.info("[OK] LIBRARY - внешние библиотеки (pandas_ta)")
else:
    nb.info("[!] LIBRARY - pandas_ta недоступен")

nb.info("Демонстрированы доступные методы:")
nb.info("• name, config - основные свойства")
nb.info("• get_default_columns(), get_info() - информация об индикаторе")
nb.info("• calculate() - расчет значений")
nb.info("• validate_data() - валидация данных")
nb.info("• is_trending_up/down() - анализ трендов")

nb.log("Скрипт готов для копирования фрагментов кода!")
