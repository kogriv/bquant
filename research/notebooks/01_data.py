#!/usr/bin/env python3
"""
01. BQuant Data Module Testing

Тестирование функций загрузки, обработки и валидации данных из модуля `bquant.data`.
Имитация работы ноутбука с пошаговым выполнением.

План тестирования:
1. Настройка окружения - импорты и установка директории данных
2. Тестирование loader - загрузка CSV файлов  
3. Обзор доступных данных - символы и таймфреймы

Usage:
    python 01_data.py [--log LOGFILE] [--trap]
    
    --log LOGFILE    Write output to file (default: always to console + 01_data_log.txt)
    --trap          Enable step-by-step execution (default: enabled)
    --no-trap       Disable step-by-step execution
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Глобальные переменные для управления выводом
LOG_FILE = None
ENABLE_TRAP = True

def setup_logging(log_file_path=None):
    """Настройка логирования в файл и консоль"""
    global LOG_FILE
    
    if log_file_path:
        LOG_FILE = open(log_file_path, 'w', encoding='utf-8')
        log_message(f"🗂️ Log started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", to_file_only=True)
        log_message(f"📝 Output will be written to: {log_file_path}")
    

def log_message(message, to_file_only=False):
    """Вывод сообщения в консоль и/или файл"""
    if not to_file_only:
        print(message)
    
    if LOG_FILE:
        LOG_FILE.write(message + '\n')
        LOG_FILE.flush()

def wait_for_continue():
    """Ожидание команды продолжения (если включен trap режим)"""
    if not ENABLE_TRAP:
        return
        
    log_message("\n" + "="*60)
    try:
        user_input = input("Press ENTER to continue or 'q' to quit: ").strip().lower()
        if user_input == 'q':
            log_message("Exiting...")
            cleanup_and_exit(0)
    except KeyboardInterrupt:
        log_message("\nKeyboard interrupt received. Exiting...")
        cleanup_and_exit(1)
    log_message("="*60 + "\n")

def cleanup_and_exit(exit_code=0):
    """Очистка ресурсов и выход"""
    if LOG_FILE:
        log_message(f"🏁 Log ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", to_file_only=True)
        LOG_FILE.close()
    sys.exit(exit_code)

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='BQuant Data Module Testing - Notebook-style script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 01_data.py                    # Default: console + file log, with traps
  python 01_data.py --log mylog.txt    # Custom log file
  python 01_data.py --no-trap          # Run without step breaks
  python 01_data.py --log test.log --no-trap  # Custom log, no breaks
        """
    )
    
    script_dir = Path(__file__).parent
    default_log = script_dir / '01_data_log.txt'
    
    parser.add_argument('--log', 
                       default=str(default_log),
                       help=f'Log file path (default: {default_log})')
    
    trap_group = parser.add_mutually_exclusive_group()
    trap_group.add_argument('--trap', 
                           action='store_true',
                           default=True,
                           help='Enable step-by-step execution (default)')
    trap_group.add_argument('--no-trap',
                           action='store_false', 
                           dest='trap',
                           help='Disable step-by-step execution')
    
    return parser.parse_args()

# Парсинг аргументов
args = parse_arguments()
ENABLE_TRAP = args.trap

# Настройка логирования
setup_logging(args.log)

log_message("🚀 Starting BQuant Data Module Testing")
log_message("=" * 50)

# ============================================================================
# STEP 0: Настройка окружения
# ============================================================================
log_message("📋 STEP 0: Environment Setup")
log_message("-" * 30)

# Добавляем путь к пакету bquant
project_root = Path.cwd().parent.parent if Path.cwd().name == 'notebooks' else Path.cwd()
if not (project_root / 'bquant').exists():
    project_root = Path.cwd()
    
sys.path.insert(0, str(project_root))

log_message(f"📁 Project root: {project_root}")
log_message(f"🐍 Python path: {sys.path[0]}")

# Импортируем pandas здесь для проверки версии
try:
    import pandas as pd
    log_message(f"📊 Pandas version: {pd.__version__}")
except ImportError:
    log_message("⚠️ Pandas not available - will import later")

wait_for_continue()

# ============================================================================
# STEP 1: Настройка логирования
# ============================================================================
log_message("📋 STEP 1: Logging Setup")
log_message("-" * 25)

from bquant.core.logging_config import setup_notebook_logging

# Настраиваем логирование для скрипта
logger = setup_notebook_logging()
log_message("✅ Logging configured: WARNING+ to console, INFO+ to file")

wait_for_continue()

# ============================================================================
# STEP 2: Импорты модулей bquant
# ============================================================================
log_message("📋 STEP 2: BQuant Module Imports")
log_message("-" * 33)

try:
    from bquant.core.config import (
        get_data_dir, set_data_dir, PROJECT_ROOT
    )

    from bquant.data.loader import (
        load_ohlcv_data, get_data_info, 
        get_available_symbols, get_available_timeframes
    )
    
    log_message("✅ BQuant modules imported successfully")
    
except ImportError as e:
    log_message(f"❌ Import error: {e}")
    log_message("Make sure all dependencies are installed")
    cleanup_and_exit(1)

wait_for_continue()

# ============================================================================
# STEP 3: Установка директории данных
# ============================================================================
log_message("📋 STEP 3: Data Directory Setup")
log_message("-" * 30)

log_message(f"🔧 Current data dir: {get_data_dir()}")

# Устанавливаем data/row как рабочую директорию
raw_data_path = PROJECT_ROOT / "data" / "row"
set_data_dir(raw_data_path)

log_message(f"✅ New data directory: {get_data_dir()}")
log_message(f"✅ Directory exists: {get_data_dir().exists()}")

# Проверяем содержимое
if get_data_dir().exists():
    csv_files = list(get_data_dir().glob("*.csv"))
    log_message(f"\n📄 Found {len(csv_files)} CSV files:")
    for csv_file in csv_files:
        size_mb = csv_file.stat().st_size / (1024 * 1024)
        log_message(f"    {csv_file.name} ({size_mb:.2f} MB)")
else:
    log_message("❌ Directory not found!")
    log_message("Please check if data/row directory exists with CSV files")

wait_for_continue()

# ============================================================================
# STEP 4: Тестирование загрузки OANDA файла
# ============================================================================
log_message("📋 STEP 4: Test OANDA CSV Loading")
log_message("-" * 35)

log_message("🧪 Test 1: Loading OANDA_XAUUSD, 60.csv")
log_message("=" * 45)

oanda_file = get_data_dir() / "OANDA_XAUUSD, 60.csv"
log_message(f"File path: {oanda_file}")
log_message(f"File exists: {oanda_file.exists()}")

oanda_data = None
if oanda_file.exists():
    try:
        # Загружаем данные с контекстом
        oanda_data = load_ohlcv_data(
            oanda_file, 
            symbol='XAUUSD', 
            timeframe='1h',
            validate_data=True
        )
        
        log_message(f"✅ Data loaded successfully!")
        log_message(f"Shape: {oanda_data.shape}")
        log_message(f"Columns: {list(oanda_data.columns)}")
        log_message(f"Date range: {oanda_data.index.min()} to {oanda_data.index.max()}")
        
        log_message(f"\nFirst 3 rows:")
        log_message(str(oanda_data.head(3)))
        
        # Получаем информацию о данных
        data_info = get_data_info(oanda_data)
        log_message(f"\n📊 Data Info:")
        log_message(f"  Rows: {data_info['rows']}")
        log_message(f"  Memory usage: {data_info['memory_usage_mb']:.2f} MB")
        log_message(f"  Missing values: {data_info['missing_values']}")
        
    except Exception as e:
        log_message(f"❌ Error loading OANDA data: {e}")
        oanda_data = None
else:
    log_message("❌ OANDA file not found")

wait_for_continue()

# ============================================================================
# STEP 5: Тестирование загрузки MetaTrader файла
# ============================================================================
log_message("📋 STEP 5: Test MetaTrader CSV Loading")
log_message("-" * 37)

log_message("🧪 Test 2: Loading XAUUSDH1.csv")
log_message("=" * 35)

mt_file = get_data_dir() / "XAUUSDH1.csv"
log_message(f"File path: {mt_file}")
log_message(f"File exists: {mt_file.exists()}")

mt_data = None
if mt_file.exists():
    try:
        # Загружаем данные MetaTrader формата
        mt_data = load_ohlcv_data(
            mt_file,
            symbol='XAUUSD',
            timeframe='1h',
            validate_data=True
        )
        
        log_message(f"✅ Data loaded successfully!")
        log_message(f"Shape: {mt_data.shape}")
        log_message(f"Columns: {list(mt_data.columns)}")
        log_message(f"Date range: {mt_data.index.min()} to {mt_data.index.max()}")
        
        log_message(f"\nFirst 3 rows:")
        log_message(str(mt_data.head(3)))
        
        # Информация о данных
        mt_info = get_data_info(mt_data)
        log_message(f"\n📊 Data Info:")
        log_message(f"  Rows: {mt_info['rows']}")
        log_message(f"  Memory usage: {mt_info['memory_usage_mb']:.2f} MB")
        log_message(f"  Missing values: {mt_info['missing_values']}")
        
    except Exception as e:
        log_message(f"❌ Error loading MT data: {e}")
        log_message("This might be due to encoding issues or file format")
        mt_data = None
else:
    log_message("❌ MetaTrader file not found")

wait_for_continue()

# ============================================================================
# STEP 6: Сравнение источников данных
# ============================================================================
log_message("📋 STEP 6: Data Sources Comparison")
log_message("-" * 35)

log_message("🧪 Test 3: Comparing Data Sources")
log_message("=" * 35)

if oanda_data is not None and mt_data is not None:
    log_message("📊 Data Comparison:")
    log_message(f"  OANDA shape: {oanda_data.shape}")
    log_message(f"  MetaTrader shape: {mt_data.shape}")
    
    # Сравниваем колонки
    oanda_cols = set(oanda_data.columns)
    mt_cols = set(mt_data.columns)
    common_cols = oanda_cols.intersection(mt_cols)
    
    log_message(f"\n📋 Columns:")
    log_message(f"  Common columns: {sorted(common_cols)}")
    log_message(f"  OANDA only: {sorted(oanda_cols - mt_cols)}")
    log_message(f"  MetaTrader only: {sorted(mt_cols - oanda_cols)}")
    
    # Сравниваем временные диапазоны
    if not oanda_data.index.empty and not mt_data.index.empty:
        log_message(f"\n📅 Time Ranges:")
        log_message(f"  OANDA: {oanda_data.index.min()} to {oanda_data.index.max()}")
        log_message(f"  MetaTrader: {mt_data.index.min()} to {mt_data.index.max()}")
        
        # Базовая статистика по ценам закрытия
        if 'close' in common_cols:
            log_message(f"\n💰 Close Price Stats:")
            log_message(f"  OANDA - Mean: {oanda_data['close'].mean():.2f}, Std: {oanda_data['close'].std():.2f}")
            log_message(f"  MetaTrader - Mean: {mt_data['close'].mean():.2f}, Std: {mt_data['close'].std():.2f}")
else:
    log_message("⚠️ Cannot compare - one or both datasets not loaded")
    if oanda_data is not None:
        log_message("✅ OANDA data is available")
    if mt_data is not None:
        log_message("✅ MetaTrader data is available")

wait_for_continue()

# ============================================================================
# STEP 7: Обзор доступных данных
# ============================================================================
log_message("📋 STEP 7: Available Data Overview")
log_message("-" * 35)

log_message("🧪 Test 4: Data Overview")
log_message("=" * 25)

try:
    # Получаем список доступных символов и таймфреймов
    available_symbols = get_available_symbols(get_data_dir())
    log_message(f"📈 Available symbols: {available_symbols}")

    if available_symbols:
        log_message(f"\n📊 Symbol Details:")
        for symbol in available_symbols:
            timeframes = get_available_timeframes(symbol, get_data_dir())
            log_message(f"  {symbol}: {timeframes}")
    else:
        log_message("❌ No symbols detected in data directory")

    csv_files_count = len(list(get_data_dir().glob('*.csv')))
    log_message(f"\n📁 Total CSV files in directory: {csv_files_count}")

except Exception as e:
    log_message(f"❌ Error getting data overview: {e}")

wait_for_continue()

# ============================================================================
# STEP 8: Резюме тестирования
# ============================================================================
log_message("📋 STEP 8: Testing Summary")
log_message("-" * 27)

log_message("🎯 Data Module Testing Results:")
log_message("=" * 35)

# Проверяем что было загружено
loaded_count = 0
if oanda_data is not None:
    log_message("✅ OANDA data loaded successfully")
    loaded_count += 1
else:
    log_message("❌ OANDA data failed to load")

if mt_data is not None:
    log_message("✅ MetaTrader data loaded successfully") 
    loaded_count += 1
else:
    log_message("❌ MetaTrader data failed to load")

log_message(f"\n📊 Summary:")
log_message(f"  Successfully loaded: {loaded_count}/2 datasets")
log_message(f"  Available symbols: {len(available_symbols) if 'available_symbols' in locals() else 'Unknown'}")
log_message(f"  CSV files found: {len(list(get_data_dir().glob('*.csv')))}")

log_message("\n🚀 Next Steps:")
log_message("- Test data validation functions")
log_message("- Test data processing functions") 
log_message("- Test sample data functionality")
log_message("- Performance testing")

log_message("\n✅ Data module basic testing completed!")

wait_for_continue()

log_message("🏁 Script finished successfully!")

cleanup_and_exit(0)