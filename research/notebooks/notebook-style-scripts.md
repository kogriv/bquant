# Notebook-Style Scripts Guide

## Обзор

Этот гид описывает паттерны и лучшие практики создания Python скриптов, имитирующих поведение Jupyter ноутбуков со step-by-step выполнением. Основан на реализации `01_data.py`.

## Основные принципы

### 1. Модульная структура с шагами
Скрипт должен быть разделен на логические блоки-шаги с четким разделением:

```python
# ============================================================================
# STEP N: Описание шага
# ============================================================================
log_message("📋 STEP N: Step Description")
log_message("-" * 30)

# Код шага...

wait_for_continue()
```

### 2. Двойной вывод (консоль + файл)
Все выводы должны идти как в консоль, так и в лог-файл:

```python
def log_message(message, to_file_only=False):
    """Вывод сообщения в консоль и/или файл"""
    if not to_file_only:
        print(message)
    
    if LOG_FILE:
        LOG_FILE.write(message + '\n')
        LOG_FILE.flush()
```

### 3. Управление выполнением
Интерактивное управление выполнением с возможностью остановки:

```python
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
```

## Архитектура скрипта

### Глобальные переменные управления
```python
# Глобальные переменные для управления выводом
LOG_FILE = None
ENABLE_TRAP = True
```

### Настройка логирования
```python
def setup_logging(log_file_path=None):
    """Настройка логирования в файл и консоль"""
    global LOG_FILE
    
    if log_file_path:
        LOG_FILE = open(log_file_path, 'w', encoding='utf-8')
        log_message(f"🗂️ Log started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", to_file_only=True)
        log_message(f"📝 Output will be written to: {log_file_path}")
```

### Парсинг аргументов командной строки
```python
def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Script Description',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py                    # Default: console + file log, with traps
  python script.py --log mylog.txt    # Custom log file
  python script.py --no-trap          # Run without step breaks
        """
    )
    
    parser.add_argument('--log', 
                       default='script_log.txt',
                       help='Log file path (default: script_log.txt)')
    
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
```

### Очистка ресурсов
```python
def cleanup_and_exit(exit_code=0):
    """Очистка ресурсов и выход"""
    if LOG_FILE:
        log_message(f"🏁 Log ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", to_file_only=True)
        LOG_FILE.close()
    sys.exit(exit_code)
```

## Структура шагов

### Шаг 0: Настройка окружения
```python
# ============================================================================
# STEP 0: Environment Setup
# ============================================================================
log_message("📋 STEP 0: Environment Setup")
log_message("-" * 30)

# Настройка путей, импортов
project_root = Path.cwd().parent.parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(project_root))

log_message(f"📁 Project root: {project_root}")
log_message(f"🐍 Python path: {sys.path[0]}")

wait_for_continue()
```

### Типовой шаг тестирования
```python
# ============================================================================
# STEP N: Test Description
# ============================================================================
log_message("📋 STEP N: Test Description")
log_message("-" * 25)

log_message("🧪 Test X: Specific Test")
log_message("=" * 25)

try:
    # Тестовый код
    result = some_function()
    
    log_message("✅ Test completed successfully!")
    log_message(f"Result: {result}")
    
except Exception as e:
    log_message(f"❌ Test failed: {e}")

wait_for_continue()
```

### Финальный шаг
```python
# ============================================================================
# STEP FINAL: Testing Summary
# ============================================================================
log_message("📋 STEP FINAL: Testing Summary")
log_message("-" * 30)

log_message("🎯 Script Results:")
log_message("=" * 20)

# Подсчет результатов
success_count = 0
if condition1:
    log_message("✅ Test 1 passed")
    success_count += 1
else:
    log_message("❌ Test 1 failed")

log_message(f"\n📊 Summary:")
log_message(f"  Passed: {success_count}/total tests")

log_message("\n🚀 Next Steps:")
log_message("- Next action 1")
log_message("- Next action 2")

log_message("\n✅ Script completed!")
wait_for_continue()

log_message("🏁 Script finished successfully!")
cleanup_and_exit(0)
```

## Стиль и форматирование

### Использование эмодзи для визуального разделения
- 📋 - Заголовки шагов
- 🧪 - Тесты
- ✅ - Успешные операции
- ❌ - Ошибки
- ⚠️ - Предупреждения
- 📊 - Статистика/данные
- 📁 - Файлы/директории
- 🚀 - Следующие шаги
- 🏁 - Завершение

### Форматирование разделителей
```python
log_message("=" * 50)  # Основные разделители
log_message("-" * 30)  # Второстепенные разделители
```

### Структура вывода информации
```python
# Краткая информация
log_message(f"Status: {status}")

# Детальная информация
log_message(f"\n📊 Details:")
log_message(f"  Parameter 1: {value1}")
log_message(f"  Parameter 2: {value2}")
log_message(f"  Parameter 3: {value3}")
```

## Лучшие практики

### 1. Обработка ошибок
Каждый блок кода должен быть обернут в try-except:
```python
try:
    # Основной код
    result = risky_operation()
    log_message("✅ Operation successful")
except Exception as e:
    log_message(f"❌ Operation failed: {e}")
    # Опционально - продолжить или завершить
```

### 2. Информативный вывод
- Всегда показывать что происходит
- Выводить ключевые параметры и результаты
- Использовать прогресс-индикаторы для длительных операций

### 3. Гибкость запуска
Поддерживать разные режимы выполнения:
- `--trap` / `--no-trap` - пошаговое выполнение
- `--log filename` - настройка лог-файла
- Возможность запуска без интерактивности

### 4. Модульность
- Каждый шаг должен быть самодостаточным
- Возможность запуска с любого шага (опционально)
- Четкое разделение настройки и выполнения

### 5. Документация
- Подробные docstrings для функций
- Комментарии к сложным блокам кода
- Примеры использования в --help

## Пример основной структуры

```python
#!/usr/bin/env python3
"""
Script Name - Description

Usage:
    python script.py [--log LOGFILE] [--trap|--no-trap]
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Глобальные переменные
LOG_FILE = None
ENABLE_TRAP = True

def setup_logging(log_file_path=None): ...
def log_message(message, to_file_only=False): ...
def wait_for_continue(): ...
def cleanup_and_exit(exit_code=0): ...
def parse_arguments(): ...

# Парсинг аргументов
args = parse_arguments()
ENABLE_TRAP = args.trap
setup_logging(args.log)

log_message("🚀 Starting Script")
log_message("=" * 50)

# STEP 0: Setup
# STEP 1: Main logic
# STEP N: Testing/Results
# STEP FINAL: Summary

log_message("🏁 Script finished successfully!")
cleanup_and_exit(0)
```

Этот подход обеспечивает читаемость, интерактивность и надежность выполнения сложных аналитических скриптов.