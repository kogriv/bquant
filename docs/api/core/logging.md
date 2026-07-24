# bquant.core.logging_config — Логирование

## Обзор

Централизованная система логирования BQuant с **модульной конфигурацией**, **предустановленными профилями** и **гибкими настройками** для различных сценариев использования. Решает проблему дублирования логов в многомодульных скриптах через гранулярный контроль уровней логирования.

## 🎯 Ключевые возможности

- **Единый API** - одна функция `setup_logging()` для всех сценариев
- **8 предустановленных профилей** - от research до production
- **Модульная настройка** - точный контроль по модулям и подмодулям
- **Автоматическое наследование** - дочерние логгеры наследуют настройки
- **Fluent API** - сложные конфигурации через LoggingConfigurator
- **Контекстные логгеры** - автоматическое добавление контекста
- **Цветной вывод** - ANSI цвета для консоли

## 📚 Основные функции

### `setup_logging()` - Единая точка конфигурации

```python
def setup_logging(
    level: str = None,                    # Общий уровень логирования
    console_level: str = None,            # Уровень для консоли
    file_level: str = None,               # Уровень для файла
    log_to_file: bool = None,             # Включить файловое логирование
    log_file: Union[str, Path] = None,    # Путь к файлу логов
    use_colors: bool = True,              # Цветной вывод в консоль
    console_enabled: bool = True,         # Включить консольный вывод
    reset_loggers: bool = False,          # Сбросить существующие логгеры
    
    # 🆕 НОВЫЕ ПАРАМЕТРЫ ДЛЯ МОДУЛЬНОГО КОНТРОЛЯ
    modules_config: Dict[str, Dict[str, str]] = None,  # Настройки модулей
    profile: str = None,                  # Предустановленный профиль
    exceptions: Dict[str, str] = None     # Исключения для конкретных логгеров
) -> logging.Logger
```

### `get_logger()` - Получение логгера

```python
def get_logger(
    name: str,                            # Имя логгера (обычно __name__)
    context: Dict[str, Any] = None        # Контекстная информация
) -> Union[logging.Logger, ContextualLogger]
```

## 🎨 Предустановленные профили

### Research профили (для NotebookSimulator скриптов)

#### `'research'` - Скрытие технических деталей
```python
setup_logging(profile='research')
```
**Поведение:**
- **Консоль:** WARNING+ (скрывает INFO от data модулей)
- **Файл:** INFO+ (сохраняет все детали для отладки)
- **Применяется к:** `bquant.data.*`, `bquant.indicators.*`, `bquant.analysis.*`
- **Идеально для:** Research скрипты, демонстрации, презентации

#### `'clean'` - Минимальный вывод
```python
setup_logging(profile='clean')
```
**Поведение:**
- **Консоль:** ERROR+ (только ошибки и критические события)
- **Файл:** INFO+ (полное логирование для анализа)
- **Применяется к:** Все модули BQuant
- **Идеально для:** Чистый вывод, минимум шума

#### `'debug'` - Отладочный режим
```python
setup_logging(profile='debug')
```
**Поведение:**
- **Консоль:** DEBUG+ (все детали)
- **Файл:** DEBUG+ (максимальная детализация)
- **Применяется к:** Все модули BQuant
- **Идеально для:** Отладка, разработка, тестирование

### Development профили

#### `'verbose'` - Максимальная детализация
```python
setup_logging(profile='verbose')
```
**Поведение:**
- **Консоль:** DEBUG+ (все сообщения)
- **Файл:** DEBUG+ (все детали)
- **Применяется к:** Все модули BQuant
- **Идеально для:** Разработка, детальная отладка

#### `'focused'` - Фокус на core модулях
```python
setup_logging(profile='focused')
```
**Поведение:**
- **Консоль:** DEBUG для core, INFO для остальных
- **Файл:** DEBUG для core, DEBUG для остальных
- **Применяется к:** `bquant.core.*` (детально), остальные (стандартно)
- **Идеально для:** Разработка core функциональности

### Production профили

#### `'critical'` - Только критические события
```python
setup_logging(profile='critical')
```
**Поведение:**
- **Консоль:** ERROR+ (только ошибки)
- **Файл:** ERROR+ (только ошибки)
- **Применяется к:** Все модули BQuant
- **Идеально для:** Production серверы, минимальный шум

#### `'audit'` - Полный аудит
```python
setup_logging(profile='audit')
```
**Поведение:**
- **Консоль:** ERROR+ (минимум в консоль)
- **Файл:** INFO+ (полное логирование для аудита)
- **Применяется к:** Все модули BQuant
- **Идеально для:** Аудит, compliance, мониторинг

## 🔧 Модульная настройка

### Точный контроль по модулям

```python
setup_logging(
    modules_config={
        # Скрыть технические детали data модулей
        'bquant.data': {
            'console': 'WARNING',    # WARNING+ в консоль
            'file': 'INFO'           # INFO+ в файл
        },
        
        # Показать детали indicators
        'bquant.indicators': {
            'console': 'INFO',       # INFO+ в консоль
            'file': 'DEBUG'          # DEBUG+ в файл
        },
        
        # Максимальная детализация для analysis
        'bquant.analysis': {
            'console': 'DEBUG',      # DEBUG+ в консоль
            'file': 'DEBUG'          # DEBUG+ в файл
        }
    }
)
```

### Автоматическое наследование

Профили автоматически применяются ко всем дочерним логгерам:

```python
# Профиль 'research' автоматически применяется к:
# - bquant.data.loader
# - bquant.data.processor  
# - bquant.data.validator
# - bquant.indicators.macd
# - bquant.analysis.zones
# и т.д.
```

## ⚡ Исключения и переопределения

### Снижение уровня для конкретных логгеров

```python
setup_logging(
    profile='research',  # Базовый профиль
    exceptions={
        'bquant.data.loader': 'INFO',      # Показать детали загрузки
        'bquant.analysis.zones': 'DEBUG',  # Отладка анализа зон
        'bquant.core.nb': 'INFO'           # NotebookSimulator всегда видим
    }
)
```

### Приоритет настроек

1. **profile** → базовые настройки
2. **modules_config** → переопределения модулей  
3. **exceptions** → индивидуальные исключения

```python
# Пример: profile + modules_config + exceptions
setup_logging(
    profile='research',                    # 1. Базовые настройки
    modules_config={                       # 2. Переопределения
        'bquant.analysis': {'console': 'DEBUG'}
    },
    exceptions={                           # 3. Исключения
        'bquant.data.loader': 'INFO'
    }
)
```

## 🚀 LoggingConfigurator - Fluent API

### Сложные конфигурации через цепочку методов

```python
from bquant.core.logging_config import LoggingConfigurator

# Базовая настройка с профилем
configurator = LoggingConfigurator()
configurator.preset('notebook', 'research').apply()

# Сложная настройка
configurator = (
    LoggingConfigurator()
        .preset('development', 'focused')           # Базовый preset
        .module('bquant.data')                     # Настройка data модуля
            .console('WARNING')                    # WARNING+ в консоль
            .file('DEBUG')                         # DEBUG+ в файл
        .module('bquant.indicators')               # Настройка indicators
            .console('ERROR')                      # ERROR+ в консоль
        .exception('bquant.data.loader', 'INFO')   # Исключение для loader
        .apply()                                   # Применить настройки
)

> **💡 Примечание:** В примерах выше `'notebook'` и `'development'` в `.preset()` можно заменить на любой другой тип окружения - результат будет одинаковым. Важен только второй параметр (профиль).
```

### Доступные preset типы

- `'notebook'` → профили для research скриптов
- `'development'` → профили для разработки  
- `'production'` → профили для production
- `'quiet'` → профили для тихих сценариев

> **⚠️ Важно:** В текущей реализации BQuant параметр `env_type` (первый параметр в `.preset()`) **не влияет на конечную конфигурацию логирования**. Это означает, что `.preset('notebook', 'research')` и `.preset('development', 'research')` дают одинаковый результат.
>
> **Планируется:** В будущих версиях `env_type` будет влиять на специфичные настройки для разных окружений:
> - `'notebook'` → специальные форматы для Jupyter, отключение дублирования
> - `'development'` → подробное логирование в консоль, отладочные форматы
> - `'production'` → только файловое логирование, минимум в консоль
> - `'quiet'` → подавление всех внешних логгеров

## 📝 Практические примеры

### 1. Research скрипт (скрыть технические детали)

```python
from bquant.core.logging_config import setup_logging

# Настройка ДО импорта модулей
setup_logging(profile='research')

# Теперь INFO сообщения от bquant.data.loader скрыты
from bquant.data.loader import load_ohlcv_data
data = load_ohlcv_data('file.csv')  # Только WARNING+ в консоль
```

### 2. Development (максимальная детализация)

```python
from bquant.core.logging_config import setup_logging

# Показать все детали для отладки
setup_logging(profile='verbose')

# Теперь видны все DEBUG сообщения
from bquant.indicators.calculators import calculate_macd
result = calculate_macd(data)  # DEBUG+ в консоль
```

### 3. Production (только критические события)

```python
from bquant.core.logging_config import setup_logging

# Минимум шума в production
setup_logging(profile='critical')

# Только ERROR+ сообщения
from bquant.analysis.zones import analyze_zones
zones = analyze_zones(data)  # Только ошибки в консоль
```

### 4. Кастомная настройка (точный контроль)

```python
from bquant.core.logging_config import setup_logging

# Точная настройка для специфичного сценария
setup_logging(
    modules_config={
        'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
        'bquant.indicators': {'console': 'ERROR', 'file': 'DEBUG'},
        'bquant.analysis': {'console': 'INFO', 'file': 'INFO'}
    },
    exceptions={
        'bquant.data.loader': 'INFO',  # Показать детали загрузки
        'bquant.core.nb': 'INFO'       # NotebookSimulator всегда видим
    }
)
```

## 🤫 Quiet Init (Phase 4)

Чтобы консольные логи были «тихими» по умолчанию в ноутбуках и демо-скриптах, в пакете реализован quiet-init:

- Регистрация внешних индикаторов (например, pandas-ta) теперь выполняется в «тихом» контексте (подавление прямого stdout/stderr) и логируется на уровне DEBUG.
- Массовые регистрации свернуты в один сводный INFO:
  - Zone Detection: `Zone detection strategies registered: ...`
  - External Indicators: `External indicators registered: pandas_ta=N, talib=M`

Рекомендуемый пресет для ноутбуков:

```python
from bquant.core.logging_config import setup_logging

setup_logging(
    profile='clean',
    exceptions={'bquant.core.nb': 'INFO'}  # базовые сообщения NotebookSimulator видны
)
```

До quiet-init (пример «шумной» консоли):

```
[i] Requires TA-Lib to use 2crows. (pip install TA-Lib)
[i] Requires TA-Lib to use 3blackcrows. (pip install TA-Lib)
...
INFO - Registered zone detection strategy: zero_crossing
INFO - Registered zone detection strategy: threshold
...
```

После quiet-init (свернутые сообщения):

```
INFO - Zone detection strategies registered: combined, line_crossing, preloaded, threshold, zero_crossing
INFO - External indicators registered: pandas_ta=157, talib=0
```

Примечания:
- Детальные записи по стратегиям и регистрации индикаторов доступны на уровне DEBUG (профили `debug/verbose`).
- Предупреждение об отсутствии TA-Lib остаётся WARNING по умолчанию и может быть скрыто профилем/исключениями при необходимости.

## 🔍 Troubleshooting

### Проблема: INFO сообщения все еще видны

**Симптом:** Профиль `research` не скрывает INFO сообщения от `bquant.data.loader`

**Решение:** Убедитесь, что профиль применяется **ДО** импорта модулей

```python
# ❌ НЕПРАВИЛЬНО - профиль применяется после импорта
from bquant.data.loader import load_ohlcv_data
setup_logging(profile='research')  # Слишком поздно!

# ✅ ПРАВИЛЬНО - профиль применяется до импорта
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')  # Сначала настройка
from bquant.data.loader import load_ohlcv_data  # Потом импорт
```

### Проблема: Профили не работают

**Симптом:** Все профили показывают одинаковое поведение

**Решение:** Проверьте, что используете актуальную версию BQuant

```python
# Проверьте версию
import bquant
print(bquant.__version__)

# Убедитесь, что импортируете из правильного места
from bquant.core.logging_config import setup_logging  # ✅
# from bquant.core import setup_logging  # ❌
```

### Проблема: Логи не записываются в файл

**Симптом:** Логи видны в консоли, но не в файле

**Решение:** Проверьте настройки файлового логирования

```python
# Явно включить файловое логирование
setup_logging(
    profile='research',
    log_to_file=True,
    log_file='my_log.txt'
)

# Или использовать профиль, который включает файловое логирование
setup_logging(profile='research')  # Автоматически включает файл
```

## 📊 Сравнение профилей

| Профиль | Консоль | Файл | Применение |
|---------|---------|------|------------|
| `research` | WARNING+ | INFO+ | Research скрипты, демонстрации |
| `clean` | ERROR+ | INFO+ | Минимум шума, тихие сценарии |
| `debug` | DEBUG+ | DEBUG+ | Отладка, разработка |
| `verbose` | DEBUG+ | DEBUG+ | Максимальная детализация |
| `focused` | DEBUG (core), INFO (остальные) | DEBUG | Разработка core функциональности |
| `critical` | ERROR+ | ERROR+ | Production, только ошибки |
| `audit` | ERROR+ | INFO+ | Аудит, compliance |

## 🔗 Интеграция с NotebookSimulator

### Автоматическая защита

NotebookSimulator автоматически защищен от настроек логирования:

```python
from bquant.core.nb import NotebookSimulator
from bquant.core.logging_config import setup_logging

# Настройка логирования НЕ влияет на NotebookSimulator
setup_logging(profile='research')

nb = NotebookSimulator("Тест")
nb.info("Это сообщение ВСЕГДА видно")  # ✅ Защищено
nb.warning("Это тоже видно")            # ✅ Защищено
```

### Комбинирование с логированием

```python
from bquant.core.nb import NotebookSimulator
from bquant.core.logging_config import setup_logging

# Настройка логирования для технических модулей
setup_logging(profile='research')

nb = NotebookSimulator("Демонстрация логирования")

# Пользовательские сообщения (всегда видны)
nb.info("Шаг 1: Загрузка данных")

# Технические детали (скрыты профилем research)
from bquant.data.loader import load_ohlcv_data
data = load_ohlcv_data('file.csv')  # INFO сообщения скрыты

# Результаты (видны)
nb.success(f"Загружено {len(data)} строк")
```

## 🚀 Миграция с ручной настройки

### Замена множественных вызовов

```python
# ❌ СТАРЫЙ СПОСОБ (множественные вызовы)
import logging
logging.getLogger('bquant.data').setLevel(logging.WARNING)
logging.getLogger('bquant.indicators').setLevel(logging.WARNING)
logging.getLogger('bquant.analysis').setLevel(logging.INFO)

# ✅ НОВЫЙ СПОСОБ (один вызов)
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')
```

### Замена кастомных настроек

```python
# ❌ СТАРЫЙ СПОСОБ (ручная настройка)
import logging
for logger_name in ['bquant.data', 'bquant.indicators']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)

# ✅ НОВЫЙ СПОСОБ (модульная настройка)
from bquant.core.logging_config import setup_logging
setup_logging(
    modules_config={
        'bquant.data': {'console': 'WARNING'},
        'bquant.indicators': {'console': 'WARNING'}
    }
)
```

## 📚 См. также

- [NotebookSimulator API](nb.md#логирование) - интеграция с логированием
- [Data Modules](../data/README.md) - логирование в модулях данных
- [Developer Guide](../../developer_guide/README.md) - руководство разработчика
- [Best Practices](../../user_guide/best_practices.md) - лучшие практики работы с BQuant

## 🎉 Заключение

Система логирования BQuant предоставляет **мощный и гибкий API** для решения всех задач логирования:

- **Простота:** Один вызов `setup_logging(profile='research')` для типовых сценариев
- **Гибкость:** Точный контроль через `modules_config` и `exceptions`
- **Мощность:** Fluent API для сложных конфигураций
- **Надежность:** Автоматическое наследование и защита NotebookSimulator

Выберите подходящий профиль для вашего сценария или создайте кастомную конфигурацию - BQuant логирование адаптируется под ваши потребности! 🚀
