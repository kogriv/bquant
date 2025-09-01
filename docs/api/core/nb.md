# bquant.core.nb - Notebook-Style Scripts API

## 📚 Обзор

Модуль `bquant.core.nb` предоставляет функциональность для создания Python скриптов, имитирующих поведение Jupyter ноутбуков с пошаговым выполнением. Основан на паттернах из `research/notebooks/01_data.py` и предоставляет универсальный API для создания интерактивных аналитических скриптов.

## 🏗️ Основные компоненты

### NotebookSimulator - Основной класс

Центральный класс для управления выполнением notebook-style скриптов с автоматической настройкой.

```python
from bquant.core.nb import NotebookSimulator

# Одна строка - всё настроено автоматически!
nb = NotebookSimulator("My Analysis Script")

nb.step("Data Loading")
# ваш код
nb.wait()

nb.step("Analysis")  
# ваш код
nb.wait()

nb.finish()
```


## 📖 API Reference

### NotebookSimulator Class

#### Инициализация

```python
NotebookSimulator(
    description: Optional[str] = None,
    default_log_name: Optional[str] = None,
    auto_setup: bool = True
)
```

**Параметры:**
- `description` (str, optional): Описание скрипта (автоопределение из имени файла если None)
- `default_log_name` (str, optional): Имя лог файла (автогенерация если None)
- `auto_setup` (bool): Автоматически парсить аргументы и настроить логирование

#### Основные методы

##### set_trap_mode()
```python
set_trap_mode(enable: bool) -> None
```
Включение/выключение пошагового режима (автоматически настраивается из аргументов).

##### setup_logging()
```python
setup_logging(log_file_path: Optional[Union[str, Path]] = None) -> None
```
Настройка двойного логирования (автоматически вызывается при инициализации).

**Параметры:**
- `log_file_path`: Путь к лог-файлу или None для консоли только

##### step()
```python
step(title: str, level: int = 0, separator_char: str = "-") -> None
```
Начало нового шага выполнения.

**Параметры:**
- `title`: Название шага
- `level`: Уровень (0=основной, 1=подшаг)
- `separator_char`: Символ разделителя

##### wait()
```python
wait() -> None
```
Ожидание команды продолжения (ENTER=продолжить, 'q'=выход).

#### Методы логирования

##### log()
```python
log(message: str, to_file_only: bool = False) -> None
```
Базовый метод вывода сообщений.

##### success() / error() / warning() / info()
```python
success(message: str) -> None    # ✅
error(message: str) -> None      # ❌  
warning(message: str) -> None    # ⚠️
info(message: str) -> None       # ℹ️
```
Специализированные методы с эмодзи-префиксами.

##### data_info()
```python
data_info(label: str, value: Any) -> None
```
Вывод структурированной информации.

```python
nb.data_info("Rows", 1000)
nb.data_info("Memory usage", "2.5 MB")
# Output:
#   Rows: 1000
#   Memory usage: 2.5 MB
```

##### section_header()
```python
section_header(title: str) -> None
```
Заголовок секции с форматированием.

##### summary_item()
```python
summary_item(label: str, value: Any, success: Optional[bool] = None) -> None
```
Элемент резюме со статусом.

```python
nb.summary_item("Data loaded", "Successfully", success=True)
nb.summary_item("Tests passed", "5/10", success=False)
# Output:
# ✅ Data loaded: Successfully
# ❌ Tests passed: 5/10
```

##### next_steps()
```python
next_steps(steps: List[str]) -> None
```
Список следующих действий.

```python
nb.next_steps([
    "Run validation tests",
    "Process missing data", 
    "Generate reports"
])
# Output:
# 🚀 Next Steps:
# - Run validation tests
# - Process missing data
# - Generate reports
```

#### Управление выполнением

##### finish()
```python
finish(message: str = "Script finished successfully!") -> None
```
Корректное завершение скрипта.

##### cleanup_and_exit()
```python
cleanup_and_exit(exit_code: int = 0) -> None
```
Очистка ресурсов и выход.

##### error_handling()
```python
@contextmanager
error_handling(operation_name: str, critical: bool = False)
```
Контекстный менеджер для обработки ошибок.

```python
with nb.error_handling("Data loading", critical=True):
    data = load_data_file()
# Если ошибка и critical=True - скрипт завершится
```

### Встроенные утилиты

Все утилиты встроены в класс `NotebookSimulator` и доступны как методы объекта.

#### format_file_size() (статический)
```python
@staticmethod
NotebookSimulator.format_file_size(size_bytes: int) -> str
```
Форматирование размера файла в читаемый вид.

```python
print(NotebookSimulator.format_file_size(1024))      # "1.00 KB"
print(NotebookSimulator.format_file_size(1048576))   # "1.00 MB"
```

#### format_duration()
```python
format_duration(start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> str
```
Форматирование длительности операции (по умолчанию от старта скрипта).

## 💡 Примеры использования

### Базовый скрипт

```python
#!/usr/bin/env python3
"""
Example Notebook-Style Script
"""

from bquant.core.nb import NotebookSimulator

# Одна строка - и всё готово!
nb = NotebookSimulator("Example Analysis Script")

# Шаг 1
nb.step("Data Loading")
try:
    # загрузка данных
    nb.success("Data loaded successfully")
except Exception as e:
    nb.error(f"Failed to load data: {e}")
    nb.cleanup_and_exit(1)

nb.wait()

# Шаг 2  
nb.step("Data Processing")
# обработка данных
nb.success("Processing completed")
nb.wait()

# Финиш
nb.finish()
```

### Продвинутый пример с обработкой ошибок

```python
from bquant.core.nb import NotebookSimulator

# Автоматическое определение параметров из командной строки
nb = NotebookSimulator("Advanced Data Analysis")

# Шаг 1: Загрузка с обработкой ошибок
nb.step("Data Loading and Validation")

with nb.error_handling("Data loading", critical=True):
    data = load_data()
    nb.data_info("Rows loaded", len(data))
    nb.data_info("Memory usage", f"{data.memory_usage().sum() / 1024**2:.2f} MB")

nb.wait()

# Шаг 2: Анализ с подшагами
nb.step("Statistical Analysis")

nb.substep("Descriptive Statistics")
stats = data.describe()
nb.success("Descriptive statistics calculated")

nb.substep("Correlation Analysis")  
correlations = data.corr()
nb.success("Correlation matrix generated")

nb.wait()

# Шаг 3: Резюме
nb.step("Results Summary")
nb.section_header("Analysis Results")

nb.summary_item("Records processed", len(data), success=True)
nb.summary_item("Variables analyzed", len(data.columns), success=True)
nb.summary_item("Missing values", data.isnull().sum().sum(), 
               success=data.isnull().sum().sum() == 0)

nb.next_steps([
    "Generate detailed report",
    "Create visualizations",
    "Export results to Excel"
])

nb.finish()
```
```

### Максимальная простота использования

API полностью устраняет boilerplate код - одна строка настройки:

```python
# Одна строка - всё настроено автоматически!
from bquant.core.nb import NotebookSimulator
nb = NotebookSimulator("My Analysis")

# Сразу к делу - никаких дополнительных настроек
nb.step("Loading Data")
# ваш код
nb.wait()

nb.step("Processing")  
# ваш код
nb.wait()

nb.finish()
```

### Автоматические возможности

- **Автоопределение имени скрипта** из `sys.argv[0]`
- **Автогенерация лог файла** на основе имени скрипта
- **Автопарсинг аргументов** командной строки (`--log`, `--trap`, `--no-trap`)
- **Автонастройка логирования** (консоль + файл)
- **Автоматический заголовок** с временными метками

## 🔗 Связанные разделы

- **[Core Modules Overview](README.md)** - Обзор всех core модулей
- **[Logging Configuration](logging.md)** - Детальная настройка логирования  
- **[Configuration Module](config.md)** - Управление конфигурацией
- **[Performance Module](performance.md)** - Мониторинг производительности

## 📝 Примечания

### Совместимость

- **Python**: >= 3.11
- **Кодировка**: UTF-8 для всех файлов логирования

### Лучшие практики

1. **Одна строка инициализации** - `nb = NotebookSimulator("Description")`
2. **Используйте контекстный менеджер** `error_handling()` для критических операций
3. **Структурируйте шаги** - основные шаги (`step()`) и подшаги (`substep()`)
4. **Логируйте все важные операции** - используйте специализированные методы (`success`, `error`, etc.)
5. **Всегда вызывайте** `finish()` в конце скрипта
6. **Тестируйте в разных режимах** - с `--trap` и `--no-trap`
7. **Не создавайте функцию main()** - размещайте код в корне модуля

### Логирование {#logging}

**Интеграция с системой логирования:**

NotebookSimulator использует собственный логгер для пользовательских сообщений, но может конфликтовать с техническими логгерами модулей. Для предотвращения дублирования логов:

```python
import logging
from bquant.core.nb import NotebookSimulator

# Скрыть технические логи для чистого вывода
logging.getLogger('bquant.data').setLevel(logging.WARNING)
logging.getLogger('bquant.indicators').setLevel(logging.WARNING)

nb = NotebookSimulator("My Analysis")
```

**См. подробности:** [Управление логированием](logging.md#управление-логированием-в-многомодульных-проектах)

### Ограничения

- Файлы логирования открываются в режиме перезаписи ('w')
- Интерактивный режим требует терминала с поддержкой input()

---

**Следующие разделы:** [Utils Module](utils.md) | [Performance Module](performance.md)