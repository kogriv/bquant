# 🚀 Демонстрация системы логирования BQuant

Этот набор скриптов демонстрирует все возможности системы логирования BQuant. Каждый скрипт можно запустить отдельно для изучения конкретного аспекта.

## 📋 Список демо-скриптов

### 1. `00_logging_profiles_demo.py` - Демонстрация профилей
**Что показывает:** Как работают все 8 предустановленных профилей
- `research` - скрывает технические детали data модулей
- `clean` - минимальный вывод (только ERROR+)
- `debug` - максимальная детализация
- `verbose` - DEBUG везде
- `focused` - DEBUG для core, INFO для остальных
- `critical` - только критические события
- `audit` - полное логирование в файл, минимум в консоль

**Запуск:**
```bash
python research/notebooks/00_logging_profiles_demo.py
```

### 2. `00_logging_modules_demo.py` - Модульная настройка
**Что показывает:** Точный контроль логирования по модулям
- Базовая модульная настройка через `modules_config`
- Профили с исключениями через `exceptions`
- Сложная настройка с точным контролем каждого подмодуля

**Запуск:**
```bash
python research/notebooks/00_logging_modules_demo.py
```

### 3. `00_logging_configurator_demo.py` - Fluent API
**Что показывает:** Использование LoggingConfigurator для сложных конфигураций
- Базовые preset'ы с профилями
- Модульная настройка через цепочку методов
- Исключения и переопределения
- Продвинутые паттерны конфигурации

**Запуск:**
```bash
python research/notebooks/00_logging_configurator_demo.py
```

### 4. `00_logging_quick_start.py` - Готовые заготовки
**Что показывает:** Готовые функции для быстрого старта
- Простые профили для типовых сценариев
- Базовые модульные настройки
- Комбинации профилей с исключениями
- Готовые Fluent API конфигурации

**Запуск:**
```bash
python research/notebooks/00_logging_quick_start.py
```

## 🎯 Как использовать

### Для изучения возможностей
Запустите все скрипты по очереди, чтобы понять, как работает система логирования:

```bash
# 1. Сначала изучите профили
python research/notebooks/00_logging_profiles_demo.py

# 2. Потом модульную настройку
python research/notebooks/00_logging_modules_demo.py

# 3. Затем Fluent API
python research/notebooks/00_logging_configurator_demo.py

# 4. И наконец готовые заготовки
python research/notebooks/00_logging_quick_start.py

# 5. Для изолированного тестирования конкретных вариантов
python research/notebooks/00_logging_hardcode_demo.py
```

### Для копирования в свой код
Используйте функции из `00_logging_quick_start.py` как готовые заготовки:

```python
from research.notebooks.00_logging_quick_start import quick_research_setup

# Быстрая настройка для research
quick_research_setup()

# Теперь можно импортировать модули
from bquant.data.loader import load_ohlcv_data
```

### Для кастомизации
Изучите код в демо-скриптах и адаптируйте под свои нужды:

```python
# Пример из 00_logging_modules_demo.py
setup_logging(
    modules_config={
        'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
        'bquant.indicators': {'console': 'ERROR', 'file': 'DEBUG'},
        'bquant.analysis': {'console': 'INFO', 'file': 'DEBUG'}
    }
)
```

## 🔧 Требования

- Python 3.8+
- BQuant пакет установлен
- Виртуальное окружение активировано

## 📚 Дополнительные ресурсы

- **API документация:** `docs/api/core/logging.md`
- **Основные примеры:** `examples/` папка
- **Тесты:** `tests/unit/test_core_modules.py`

## 💡 Советы по использованию

### 1. Порядок настройки
**Всегда настраивайте логирование ДО импорта модулей:**

```python
# ✅ ПРАВИЛЬНО
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')
from bquant.data.loader import load_ohlcv_data

# ❌ НЕПРАВИЛЬНО
from bquant.data.loader import load_ohlcv_data
setup_logging(profile='research')  # Слишком поздно!
```

### 2. Выбор профиля
**Используйте готовые профили для типовых сценариев:**

- `research` - для notebook скриптов и демонстраций
- `clean` - для тихих сценариев
- `verbose` - для разработки и отладки
- `critical` - для production

### 3. Модульная настройка
**Для точного контроля используйте `modules_config`:**

```python
setup_logging(
    modules_config={
        'bquant.data': {'console': 'WARNING', 'file': 'INFO'},
        'bquant.analysis': {'console': 'DEBUG', 'file': 'DEBUG'}
    }
)
```

### 4. Fluent API
**Для сложных конфигураций используйте LoggingConfigurator:**

```python
from bquant.core.logging_config import LoggingConfigurator

configurator = (
    LoggingConfigurator()
        .preset('notebook', 'research')
        .module('bquant.data').console('WARNING')
        .exception('bquant.data.loader', 'INFO')
        .apply()
)
```

## 🎉 Результат

После изучения этих демо-скриптов вы сможете:

- ✅ Выбрать подходящий профиль для любого сценария
- ✅ Точно настроить логирование для конкретных модулей
- ✅ Создать сложные конфигурации через Fluent API
- ✅ Использовать готовые заготовки для быстрого старта
- ✅ Решить проблемы с дублированием логов
- ✅ Интегрировать логирование с NotebookSimulator

**Удачного изучения системы логирования BQuant! 🚀**
