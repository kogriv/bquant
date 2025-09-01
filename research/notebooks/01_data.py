#!/usr/bin/env python3
"""
01. BQuant Data Module Testing (New Simple API)

Тестирование функций загрузки, обработки и валидации данных из модуля `bquant.data`.
Имитация работы ноутбука с пошаговым выполнением используя новый NotebookSimulator API.

План тестирования:
1. Настройка окружения - импорты и установка директории данных
2. Тестирование loader - загрузка CSV файлов  
3. Обзор доступных данных - символы и таймфреймы
"""

import sys
from pathlib import Path

# Добавляем путь к пакету bquant (если запускаем из notebooks директории)
project_root = Path.cwd().parent.parent if Path.cwd().name == 'notebooks' else Path.cwd()
if (project_root / 'bquant').exists():
    sys.path.insert(0, str(project_root))

# Импорт нового простого API
from bquant.core.nb import NotebookSimulator

def main():
    """Основная функция скрипта."""
    
    # ========================================================================
    # SETUP: Создание NotebookSimulator - ВСЁ АВТОМАТИЧЕСКИ!
    # ========================================================================
    
    # Одна строка - и всё настроено: парсинг аргументов, логирование, заголовок!
    nb = NotebookSimulator("BQuant Data Module Testing")
    
    # ========================================================================
    # STEP 0: Настройка окружения
    # ========================================================================
    
    nb.step("Environment Setup")
    
    nb.info(f"Project root: {project_root}")
    nb.info(f"Python path: {sys.path[0]}")
    
    # Проверка доступности pandas
    with nb.error_handling("Pandas import check"):
        import pandas as pd
        nb.info(f"Pandas version: {pd.__version__}")
    
    nb.wait()
    
    # ========================================================================
    # STEP 1: Настройка логирования BQuant
    # ========================================================================
    
    nb.step("BQuant Logging Setup")
    
    with nb.error_handling("BQuant logging setup"):
        from bquant.core.logging_config import setup_logging
        
        # Настраиваем логирование для BQuant
        bquant_logger = setup_logging(profile='research')
        nb.success("BQuant logging configured: WARNING+ to console, INFO+ to file")
    
    nb.wait()
    
    # ========================================================================
    # STEP 2: Импорты модулей BQuant
    # ========================================================================
    
    nb.step("BQuant Module Imports")
    
    try:
        from bquant.core.config import get_data_dir, set_data_dir, PROJECT_ROOT
        from bquant.data.loader import (
            load_ohlcv_data, get_data_info, 
            get_available_symbols, get_available_timeframes
        )
        
        nb.success("BQuant modules imported successfully")
        
    except ImportError as e:
        nb.error(f"Import error: {e}")
        nb.error("Make sure all dependencies are installed")
        nb.cleanup_and_exit(1)
    
    nb.wait()
    
    # ========================================================================
    # STEP 3: Установка директории данных
    # ========================================================================
    
    nb.step("Data Directory Setup")
    
    nb.info(f"Current data dir: {get_data_dir()}")
    
    # Устанавливаем data/row как рабочую директорию
    raw_data_path = PROJECT_ROOT / "data" / "row"
    set_data_dir(raw_data_path)
    
    nb.success(f"New data directory: {get_data_dir()}")
    nb.success(f"Directory exists: {get_data_dir().exists()}")
    
    # Проверяем содержимое
    if get_data_dir().exists():
        csv_files = list(get_data_dir().glob("*.csv"))
        nb.section_header(f"Found {len(csv_files)} CSV files")
        for csv_file in csv_files:
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            nb.data_info(csv_file.name, f"{size_mb:.2f} MB")
    else:
        nb.error("Directory not found!")
        nb.error("Please check if data/row directory exists with CSV files")
    
    nb.wait()
    
    # ========================================================================
    # STEP 4: Тестирование загрузки OANDA файла
    # ========================================================================
    
    nb.step("Test OANDA CSV Loading")
    
    nb.substep("Test 1: Loading OANDA_XAUUSD, 60.csv")
    
    oanda_file = get_data_dir() / "OANDA_XAUUSD, 60.csv"
    nb.info(f"File path: {oanda_file}")
    nb.info(f"File exists: {oanda_file.exists()}")
    
    oanda_data = None
    if oanda_file.exists():
        with nb.error_handling("OANDA data loading"):
            # Загружаем данные с контекстом
            oanda_data = load_ohlcv_data(
                oanda_file, 
                symbol='XAUUSD', 
                timeframe='1h',
                validate_data=True
            )
            
            nb.success("Data loaded successfully!")
            nb.data_info("Shape", oanda_data.shape)
            nb.data_info("Columns", list(oanda_data.columns))
            nb.data_info("Date range", f"{oanda_data.index.min()} to {oanda_data.index.max()}")
            
            # Показываем первые 3 строки
            nb.section_header("First 3 rows")
            nb.log(str(oanda_data.head(3)))
            
            # Получаем информацию о данных
            data_info = get_data_info(oanda_data)
            nb.section_header("Data Info")
            nb.data_info("Rows", data_info['rows'])
            nb.data_info("Memory usage", f"{data_info['memory_usage_mb']:.2f} MB")
            nb.data_info("Missing values", data_info['missing_values'])
    else:
        nb.error("OANDA file not found")
    
    nb.wait()
    
    # ========================================================================
    # STEP 5: Тестирование загрузки MetaTrader файла
    # ========================================================================
    
    nb.step("Test MetaTrader CSV Loading")
    
    nb.substep("Test 2: Loading XAUUSDH1.csv")
    
    mt_file = get_data_dir() / "XAUUSDH1.csv"
    nb.info(f"File path: {mt_file}")
    nb.info(f"File exists: {mt_file.exists()}")
    
    mt_data = None
    if mt_file.exists():
        with nb.error_handling("MetaTrader data loading"):
            # Загружаем данные MetaTrader формата
            mt_data = load_ohlcv_data(
                mt_file,
                symbol='XAUUSD',
                timeframe='1h',
                validate_data=True
            )
            
            nb.success("Data loaded successfully!")
            nb.data_info("Shape", mt_data.shape)
            nb.data_info("Columns", list(mt_data.columns))
            nb.data_info("Date range", f"{mt_data.index.min()} to {mt_data.index.max()}")
            
            # Показываем первые 3 строки
            nb.section_header("First 3 rows")
            nb.log(str(mt_data.head(3)))
            
            # Информация о данных
            mt_info = get_data_info(mt_data)
            nb.section_header("Data Info")
            nb.data_info("Rows", mt_info['rows'])
            nb.data_info("Memory usage", f"{mt_info['memory_usage_mb']:.2f} MB")
            nb.data_info("Missing values", mt_info['missing_values'])
    else:
        nb.error("MetaTrader file not found")
    
    nb.wait()
    
    # ========================================================================
    # STEP 6: Сравнение источников данных
    # ========================================================================
    
    nb.step("Data Sources Comparison")
    
    nb.substep("Test 3: Comparing Data Sources")
    
    if oanda_data is not None and mt_data is not None:
        nb.section_header("Data Comparison")
        nb.data_info("OANDA shape", oanda_data.shape)
        nb.data_info("MetaTrader shape", mt_data.shape)
        
        # Сравниваем колонки
        oanda_cols = set(oanda_data.columns)
        mt_cols = set(mt_data.columns)
        common_cols = oanda_cols.intersection(mt_cols)
        
        nb.section_header("Columns Comparison")
        nb.data_info("Common columns", sorted(common_cols))
        nb.data_info("OANDA only", sorted(oanda_cols - mt_cols))
        nb.data_info("MetaTrader only", sorted(mt_cols - oanda_cols))
        
        # Сравниваем временные диапазоны
        if not oanda_data.index.empty and not mt_data.index.empty:
            nb.section_header("Time Ranges")
            nb.data_info("OANDA", f"{oanda_data.index.min()} to {oanda_data.index.max()}")
            nb.data_info("MetaTrader", f"{mt_data.index.min()} to {mt_data.index.max()}")
            
            # Базовая статистика по ценам закрытия
            if 'close' in common_cols:
                nb.section_header("Close Price Statistics")
                nb.data_info("OANDA - Mean", f"{oanda_data['close'].mean():.2f}")
                nb.data_info("OANDA - Std", f"{oanda_data['close'].std():.2f}")
                nb.data_info("MetaTrader - Mean", f"{mt_data['close'].mean():.2f}")
                nb.data_info("MetaTrader - Std", f"{mt_data['close'].std():.2f}")
    else:
        nb.warning("Cannot compare - one or both datasets not loaded")
        if oanda_data is not None:
            nb.success("OANDA data is available")
        if mt_data is not None:
            nb.success("MetaTrader data is available")
    
    nb.wait()
    
    # ========================================================================
    # STEP 7: Обзор доступных данных
    # ========================================================================
    
    nb.step("Available Data Overview")
    
    nb.substep("Test 4: Data Overview")
    
    with nb.error_handling("Data overview analysis"):
        # Получаем список доступных символов и таймфреймов
        available_symbols = get_available_symbols(get_data_dir())
        nb.info(f"Available symbols: {available_symbols}")
        
        if available_symbols:
            nb.section_header("Symbol Details")
            for symbol in available_symbols:
                timeframes = get_available_timeframes(symbol, get_data_dir())
                nb.data_info(symbol, timeframes)
        else:
            nb.error("No symbols detected in data directory")
        
        csv_files_count = len(list(get_data_dir().glob('*.csv')))
        nb.data_info("Total CSV files in directory", csv_files_count)
    
    nb.wait()
    
    # ========================================================================
    # STEP 8: Резюме тестирования
    # ========================================================================
    
    nb.step("Testing Summary")
    
    nb.section_header("Data Module Testing Results")
    
    # Проверяем что было загружено
    loaded_count = 0
    nb.summary_item("OANDA data", "loaded successfully" if oanda_data is not None else "failed to load", 
                   success=oanda_data is not None)
    if oanda_data is not None:
        loaded_count += 1
        
    nb.summary_item("MetaTrader data", "loaded successfully" if mt_data is not None else "failed to load",
                   success=mt_data is not None)
    if mt_data is not None:
        loaded_count += 1
    
    nb.section_header("Summary Statistics")
    nb.data_info("Successfully loaded", f"{loaded_count}/2 datasets")
    nb.data_info("Available symbols", len(available_symbols) if 'available_symbols' in locals() else 'Unknown')
    nb.data_info("CSV files found", len(list(get_data_dir().glob('*.csv'))))
    
    nb.next_steps([
        "Test data validation functions",
        "Test data processing functions", 
        "Test sample data functionality",
        "Performance testing"
    ])
    
    nb.success("Data module basic testing completed!")
    
    nb.wait()
    
    # ========================================================================
    # FINISH: Завершение скрипта - АВТОМАТИЧЕСКИ!
    # ========================================================================
    
    nb.finish("BQuant Data Module Testing finished successfully!")


if __name__ == "__main__":
    main()