#!/usr/bin/env python3
"""
BQuant Testing

Тестирование функций
- загрузки, обработки и валидации данных из модуля `bquant.data`.
- индикаторов и их вычисления.
Имитация работы ноутбука с пошаговым выполнением используя NotebookSimulator API.

"""

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


# Инициализируем симулятор. Описание берется как первый аргумент.
nb = NotebookSimulator("Демонстрация работы модуля bquant.data.loader")

nb.step("Определение рабочей директории, получение списка доступных символов и таймфреймов")

nb.info("API bquant.data.loader - это основной модуль для загрузки данных.")

with nb.error_handling("Listing available data directory"):
    nb.info("-"*60)
    nb.info("1.1. get_data_dir() - Текущая рабочая директория:")
    nb.log(get_data_dir())

with nb.error_handling("Setting data directory"):
    nb.info("-"*60)
    nb.info("1.2. set_data_dir() - Установка рабочей директории:")
    raw_data_path = get_data_dir() / "raw"
    set_data_dir(raw_data_path)
    nb.log(get_data_dir())

mt_file_path = raw_data_path / 'XAUUSDH1.csv'
nb.info(f"2.1. Загружаем файл MetaTrader: {mt_file_path}")
if mt_file_path.exists():
    with nb.error_handling("Loading raw MetaTrader file"):
        df_raw_mt = load_ohlcv_data(mt_file_path, symbol="XAUUSD", timeframe="H1")
        nb.log(df_raw_mt.head().to_string())
        nb.log(json.dumps(get_data_info(df_raw_mt), indent=2, default=str))
    else:
    nb.error(f"Файл не найден: {mt_file_path}")

with nb.error_handling("Listing available symbols"):
    nb.info("-"*60)
    nb.info("1.2. get_available_symbols() - Список доступных символов:")
    symbols = get_available_symbols()
    nb.log(json.dumps(symbols, indent=2, ensure_ascii=False))

with nb.error_handling("Listing available timeframes"):
    nb.info("-"*60)
    nb.info("1.3. get_available_timeframes() - Список доступных таймфреймов:")
    timeframes = get_available_timeframes("XAUUSD")
    nb.log(json.dumps(timeframes, indent=2, ensure_ascii=False))
    
    nb.wait()