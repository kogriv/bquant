'''
Демонстрация работы загрузчика данных bquant.data.loader

Этот скрипт показывает, как использовать различные функции для загрузки данных:
1.  Работа с встроенными sample-данными.
2.  Загрузка "сырых" CSV-файлов из директории data/row.
3.  Использование конфигурационных хелперов для гибкой загрузки.
'''

from pathlib import Path
import pandas as pd
import json
import logging

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')


from bquant.core.nb import NotebookSimulator
from bquant.core.config import get_data_dir, set_data_dir, reset_directories_to_defaults
from bquant.data.loader import (
    load_ohlcv_data,
    load_symbol_data,
    load_xauusd_data,
    load_all_data_files,
    get_data_info,
    get_available_symbols,
    get_available_timeframes
)
from bquant.data.samples import (
    get_sample_data,
    list_datasets,
    get_dataset_info
)

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Настройка логирования для демонстрации (единый API)
# Используем профиль 'research' для скрытия технических деталей
# from bquant.core.logging_config import setup_logging
# setup_logging(profile='research')

# Инициализируем симулятор. Описание берется как первый аргумент.
nb = NotebookSimulator("Демонстрация работы модуля bquant.data.loader")

# --- Шаг 1: Работа с встроенными данными (bquant.data.samples) ---
nb.step("Шаг 1: Работа с встроенными sample-данными")

nb.info("API bquant.data.samples - это самый простой способ получить данные для тестов и примеров.")

with nb.error_handling("Listing available datasets"):
    nb.info("-"*60)
    nb.info("1.1. list_datasets() - Список доступных встроенных датасетов:")
    all_datasets = list_datasets()
    nb.log(json.dumps(all_datasets, indent=2, ensure_ascii=False))

with nb.error_handling("Getting dataset info"):
    nb.info("-"*60)
    nb.info("1.2. get_dataset_info('tv_xauusd_1h') - Получение информации о конкретном датасете (tv_xauusd_1h):")
    info = get_dataset_info('tv_xauusd_1h')
    nb.log(json.dumps(info, indent=2, ensure_ascii=False))

with nb.error_handling("Loading TradingView sample data"):
    nb.info("-"*60)
    nb.info("1.3. get_sample_data('tv_xauusd_1h') - Загрузка встроенного датасета 'tv_xauusd_1h' как DataFrame:")
    df_sample_tv = get_sample_data('tv_xauusd_1h')
    nb.log(df_sample_tv.head().to_string())

with nb.error_handling("Loading MetaTrader sample data"):
    nb.info("-"*60)
    nb.info("1.4. get_sample_data('mt_xauusd_m15') - Загрузка встроенного датасета 'mt_xauusd_m15' и просмотр информации о нем:")
    df_sample_mt = get_sample_data('mt_xauusd_m15')
    nb.log(json.dumps(get_data_info(df_sample_mt), indent=2, ensure_ascii=False, default=str))

nb.wait()

# --- Шаг 2: Загрузка сырых CSV файлов с помощью load_ohlcv_data ---
nb.step("Шаг 2: Загрузка сырых CSV файлов напрямую")

nb.info("Функция load_ohlcv_data() является основной и может загружать CSV файлы, " 
        "автоматически определяя их формат (OANDA/TradingView или MetaTrader).")

raw_data_path = get_data_dir() / 'row'
nb.info(f"Путь к директории с сырыми данными: {raw_data_path}")

# 2.1. Загрузка файла формата MetaTrader (XAUUSDH1.csv)
mt_file_path = raw_data_path / 'XAUUSDH1.csv'
nb.info(f"2.1. Загружаем файл MetaTrader: {mt_file_path}")
if mt_file_path.exists():
    with nb.error_handling("Loading raw MetaTrader file"):
        df_raw_mt = load_ohlcv_data(mt_file_path, symbol="XAUUSD", timeframe="H1")
        nb.log(df_raw_mt.head().to_string())
        nb.log(json.dumps(get_data_info(df_raw_mt), indent=2, default=str))
else:
    nb.error(f"Файл не найден: {mt_file_path}")

# 2.2. Загрузка файла формата TradingView (OANDA_XAUUSD, 60.csv)
tv_file_path = raw_data_path / 'OANDA_XAUUSD, 60.csv'
nb.info(f"2.2. Загружаем файл TradingView: {tv_file_path}")
if tv_file_path.exists():
    with nb.error_handling("Loading raw TradingView file"):
        df_raw_tv = load_ohlcv_data(tv_file_path, symbol="XAUUSD", timeframe="1h")
        nb.log(df_raw_tv.head().to_string())
        nb.log(json.dumps(get_data_info(df_raw_tv), indent=2, default=str))
else:
    nb.error(f"Файл не найден: {tv_file_path}")

nb.wait()

# --- Шаг 3: Использование конфигурационных хелперов ---
nb.step("Шаг 3: Использование конфигурационных хелперов для гибкой загрузки")

nb.info("Функция load_symbol_data() использует config.py для поиска файлов. "
        "По умолчанию она ищет в /data. Мы временно изменим путь на /data/row, "
        "чтобы продемонстрировать гибкость системы конфигурации.")

available_raw_files = sorted(p.name for p in raw_data_path.glob('*.csv'))

if not available_raw_files:
    nb.warning("В каталоге data/row отсутствуют CSV-файлы. Демонстрация конфигурационных хелперов пропущена.")
else:
    nb.info(f"Обнаружены файлы: {available_raw_files}")

    original_data_dir = get_data_dir()
    nb.info(f"Текущая директория данных: {original_data_dir}")

    set_data_dir(raw_data_path)
    nb.info(f"Временно изменили директорию данных на: {get_data_dir()}")

    try:
        if mt_file_path.exists():
            with nb.error_handling("Loading with load_symbol_data helper"):
                nb.info("3.1. Теперь load_symbol_data сможет найти файлы в data/row")
                df_helper_mt = load_symbol_data("XAUUSD", "1h", data_source='metatrader')
                nb.info("Загрузка XAUUSD 1h (metatrader) через хелпер:")
                nb.log(df_helper_mt.head().to_string())
        else:
            nb.warning(f"Файл {mt_file_path} не найден. Пропускаем демонстрацию load_symbol_data().")

        if tv_file_path.exists():
            with nb.error_handling("Loading with load_xauusd_data convenience function"):
                nb.info("3.1.1. Использование convenience функции load_xauusd_data для быстрой загрузки:")
                df_xauusd_convenience = load_xauusd_data("1h")
                nb.log(f"Загружено через load_xauusd_data('1h'): {len(df_xauusd_convenience)} строк")
                nb.log("Первые 3 строки:")
                nb.log(df_xauusd_convenience.head(3).to_string())
        else:
            nb.warning(f"Файл {tv_file_path} не найден. Пропускаем демонстрацию load_xauusd_data().")

        with nb.error_handling("Getting available symbols and timeframes"):
            nb.info("3.2. Получение списка доступных символов и таймфреймов из новой директории:")
            available_symbols = get_available_symbols()
            available_timeframes = get_available_timeframes('XAUUSD')
            nb.log(f"Доступные символы: {available_symbols}")
            nb.log(f"Доступные таймфреймы для XAUUSD: {available_timeframes}")

        with nb.error_handling("Loading all data files from directory"):
            nb.info("3.3. Загрузка всех файлов из директории data/row:")
            all_data = load_all_data_files()
            nb.log(f"Загружено {len(all_data)} наборов данных:")
            for name, df in all_data.items():
                nb.log(f"  - {name}: {len(df)} строк")
    finally:
        reset_directories_to_defaults()
        nb.info(f"Вернули директорию данных к значению по умолчанию: {get_data_dir()}")

nb.finish()
