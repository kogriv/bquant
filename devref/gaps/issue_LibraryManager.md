# Issue: LibraryManager не используется в текущей архитектуре

## 📋 Описание проблемы

`LibraryManager` - централизованный менеджер для управления внешними библиотеками индикаторов (pandas-ta, TA-Lib), но в текущей архитектуре BQuant он **импортируется, но не используется**.

**Дополнительная проблема:** Модуль `pandas_ta.py` использует хардкод для регистрации конкретных индикаторов, что делает его не универсальным и не масштабируемым.

## 🏗️ Текущая архитектура

### Структура модулей
```
bquant/indicators/
├── __init__.py              # Основной модуль (импортирует LibraryManager)
├── base.py                  # Базовые классы и IndicatorFactory
├── library/                 # Модуль внешних библиотек
│   ├── __init__.py         # Импортирует LibraryManager
│   ├── manager.py          # LibraryManager (определение)
│   ├── pandas_ta.py        # PandasTALoader (автоинициализация + хардкод)
│   └── talib.py            # TALibLoader
└── calculators.py           # Использует LibraryManager
```

### Текущий поток инициализации

#### 1. Автоматическая инициализация в pandas_ta.py
```python
# bquant/indicators/library/pandas_ta.py (конец файла)
try:
    loader = PandasTALoader()           # Создается экземпляр
    loader.register_indicators()         # Регистрирует индикаторы в IndicatorFactory
except Exception as e:
    logger.warning(f"Failed to initialize pandas-ta loader: {e}")
```

#### 2. Импорт в основной модуль
```python
# bquant/indicators/__init__.py
from .library import (
    PandasTALoader,
    TALibLoader,
    LibraryManager,           # Импортируется, но НЕ используется
    load_pandas_ta,
    load_talib,
    load_all_indicators
)
```

#### 3. Авторегистрация индикаторов
```python
# bquant/indicators/__init__.py
def _register_all_indicators():
    try:
        # PRELOADED и CUSTOM индикаторы
        IndicatorFactory.register_indicator('macd_preloaded', MACDPreloadedIndicator)
        # ... другие индикаторы
        
        # ❌ ВМЕСТО этого комментария:
        # LIBRARY индикаторы регистрируются автоматически при загрузке
        # через соответствующие загрузчики
        
        # ✅ ДОЛЖНО БЫТЬ:
        # LibraryManager.load_all_libraries()  # Загружает все внешние библиотеки
        
    except Exception as e:
        pass
```

## ⚠️ Проблемы текущего подхода

### 1. LibraryManager не используется
- Импортируется, но не вызывается
- Не выполняет свою основную функцию централизованного управления

### 2. Дублирование логики инициализации
- Каждый загрузчик (pandas_ta.py, talib.py) сам себя инициализирует
- Нет единой точки управления зависимостями

### 3. Отсутствие централизованного контроля
- Нельзя проверить доступность библиотек через единый интерфейс
- Нет возможности управлять порядком загрузки

### 4. Смешение ответственности
- `pandas_ta.py` отвечает и за определение классов, и за инициализацию
- Нарушение принципа единственной ответственности

### 5. Хардкод индикаторов в pandas_ta.py
- **Явное кодирование конкретных индикаторов:** SMA, EMA, RSI, MACD, BBands
- **Множество методов `_register_*`:** `_register_sma()`, `_register_ema()`, `_register_rsi()`, `_register_macd()`, `_register_bbands()`
- **Неуниверсальность:** Для новых индикаторов нужно добавлять новые методы
- **Раздувание модуля:** Код растет линейно с количеством индикаторов

## 🔧 Решения

### Вариант 1: Использовать LibraryManager + Универсальный подход (Рекомендуется)

#### 1.1 Убрать автоинициализацию из pandas_ta.py
```python
# bquant/indicators/library/pandas_ta.py
# УБРАТЬ этот блок:
# try:
#     loader = PandasTALoader()
#     loader.register_indicators()
# except Exception as e:
#     logger.warning(f"Failed to initialize pandas-ta loader: {e}")
```

#### 1.2 Реализовать универсальный подход в PandasTALoader
```python
# bquant/indicators/library/pandas_ta.py
@classmethod
def register_indicators(cls) -> int:
    """Динамически обнаружить и зарегистрировать ВСЕ доступные индикаторы."""
    if not cls.is_available():
        return 0
    
    try:
        # 1. Обнаруживаем все доступные функции pandas-ta
        available_functions = cls._discover_all_functions()
        
        # 2. Анализируем каждую функцию динамически
        for func_name, func in available_functions.items():
            config = cls._analyze_function_dynamically(func_name, func)
            
            # 3. Создаем класс индикатора
            indicator_class = cls._create_indicator_class_dynamically(func_name, config)
            
            # 4. Регистрируем в фабрике
            IndicatorFactory.register_indicator(f'pandas_ta_{func_name}', indicator_class)
        
        return len(available_functions)
        
    except Exception as e:
        logger.error(f"Failed to register indicators: {e}")
        return 0

@classmethod
def _discover_all_functions(cls):
    """Обнаружить все доступные функции pandas-ta."""
    import pandas_ta as ta
    import inspect
    
    functions = {}
    for func_name in dir(ta):
        if not func_name.startswith('_'):  # Публичные функции
            func = getattr(ta, func_name)
            if callable(func):
                functions[func_name] = func
    
    return functions

@classmethod
def _analyze_function_dynamically(cls, func_name: str, func: callable):
    """Анализирует функцию pandas-ta и создает конфигурацию."""
    import inspect
    
    signature = inspect.signature(func)
    doc = func.__doc__ or f"{func_name} indicator"
    
    # Анализируем параметры
    parameters = list(signature.parameters.keys())
    
    # Убираем стандартные параметры pandas-ta
    pandas_ta_params = ['open', 'high', 'low', 'close', 'volume']
    config_params = [p for p in parameters if p not in pandas_ta_params]
    
    # Определяем колонки по имени функции
    columns = [f'{func_name}_{"_".join(config_params)}']
    
    return {
        'function': func,
        'parameters': config_params,
        'columns': columns,
        'description': doc,
        'signature': signature
    }

@classmethod
def _create_indicator_class_dynamically(cls, func_name: str, config: dict):
    """Создает класс индикатора динамически."""
    
    def calculate_method(self, data: pd.DataFrame, **kwargs):
        """Динамически созданный метод calculate."""
        try:
            # Вызываем функцию pandas-ta с правильными параметрами
            result = config['function'](data, **kwargs)
            
            # Формируем результат
            if isinstance(result, pd.Series):
                result = pd.DataFrame({config['columns'][0]: result})
            
            return result
            
        except Exception as e:
            raise IndicatorCalculationError(f"Failed to calculate {func_name}: {e}")
    
    # Создаем класс динамически
    indicator_class = type(
        f'PandasTA{func_name.upper()}',
        (LibraryIndicator,),
        {
            '__init__': cls._create_init_method(config),
            'calculate': calculate_method,
            'native_indicator': property(lambda self: config['function'])
        }
    )
    
    return indicator_class
```

#### 1.3 Использовать LibraryManager в основном модуле
```python
# bquant/indicators/__init__.py
def _register_all_indicators():
    try:
        # PRELOADED и CUSTOM индикаторы
        IndicatorFactory.register_indicator('macd_preloaded', MACDPreloadedIndicator)
        IndicatorFactory.register_indicator('sma', SimpleMovingAverage)
        IndicatorFactory.register_indicator('ema', ExponentialMovingAverage)
        IndicatorFactory.register_indicator('rsi', RelativeStrengthIndex)
        IndicatorFactory.register_indicator('macd', MACD)
        IndicatorFactory.register_indicator('bbands', BollingerBands)
        
        # LIBRARY индикаторы через LibraryManager
        library_results = LibraryManager.load_all_libraries()
        logger.info(f"Loaded external libraries: {library_results}")
        
    except Exception as e:
        logger.warning(f"Failed to register some indicators: {e}")
```

#### 1.4 Добавить проверку доступности библиотек
```python
# bquant/indicators/__init__.py
def _check_library_availability():
    """Проверить доступность внешних библиотек."""
    available_libs = LibraryManager.get_available_libraries()
    
    for lib_name in available_libs:
        info = LibraryManager.get_library_info(lib_name)
        if info['available']:
            logger.info(f"Library {lib_name}: {info['indicators_count']} indicators available")
        else:
            logger.warning(f"Library {lib_name}: {info['error']}")

# Вызывать после _register_all_indicators()
_check_library_availability()
```

### Вариант 2: Улучшить текущий подход (Временное решение)

#### 2.1 Добавить управление через LibraryManager
```python
# bquant/indicators/__init__.py
def _register_all_indicators():
    try:
        # PRELOADED и CUSTOM индикаторы
        # ... существующий код ...
        
        # LIBRARY индикаторы - проверяем через LibraryManager
        if LibraryManager.check_library_availability('pandas_ta'):
            logger.info("pandas_ta library available")
        else:
            logger.warning("pandas_ta library not available")
            
        if LibraryManager.check_library_availability('talib'):
            logger.info("TA-Lib library available")
        else:
            logger.warning("TA-Lib library not available")
        
    except Exception as e:
        pass
```

## 📊 Преимущества использования LibraryManager

### 1. Централизованное управление
- Единая точка загрузки всех внешних библиотек
- Контроль порядка инициализации

### 2. Лучшая обработка ошибок
- Централизованная обработка ошибок загрузки
- Логирование состояния всех библиотек

### 3. Управление зависимостями
- Проверка доступности библиотек
- Информация о количестве доступных индикаторов

### 4. Гибкость конфигурации
- Возможность выборочной загрузки библиотек
- Управление параметрами загрузки

### 5. Тестируемость
- Легче тестировать загрузку библиотек
- Мокать поведение LibraryManager

## 🚀 Преимущества универсального подхода

### 1. Автоматическое обнаружение индикаторов
- **0 хардкода** - все индикаторы определяются автоматически
- **100% автоматизации** - не нужно знать заранее, какие индикаторы существуют

### 2. Масштабируемость
- **Фиксированный размер кода** - не растет с количеством индикаторов
- **Автоматическое добавление** новых индикаторов при обновлении pandas-ta

### 3. Гибкость
- **Адаптивность** - автоматически подстраивается под доступные функции
- **Конфигурируемость** - параметры определяются динамически

### 4. Поддержка
- **Единое место** для логики создания индикаторов
- **Автоматическое обновление** при изменении API pandas-ta

## 📈 Сравнение подходов

| Аспект | Текущий хардкод | Конфигурация | Универсальный |
|--------|------------------|---------------|---------------|
| **Новые индикаторы** | ❌ Изменение кода | ❌ Изменение конфига | ✅ Автоматически |
| **Поддержка** | ❌ Множество мест | ⚠️ Одно место | ✅ Автоматически |
| **Размер кода** | ❌ Растет линейно | ⚠️ Растет медленно | ✅ Фиксированный |
| **Гибкость** | ❌ Жестко задано | ⚠️ Настраиваемо | ✅ Адаптивно |
| **Масштабируемость** | ❌ Ограничена | ⚠️ Частично | ✅ Неограничена |

## 🎯 Роли компонентов в новой архитектуре

### LibraryManager - оркестратор библиотек
- **Управление жизненным циклом** библиотек (загрузка, выгрузка)
- **Проверка доступности** библиотек
- **Координация** между разными загрузчиками
- **Единая точка входа** для работы с внешними библиотеками
- **НЕ создает индикаторы** - это не его ответственность

### PandasTALoader - генератор индикаторов
- **Динамическое обнаружение** всех доступных функций pandas-ta
- **Автоматический анализ** функций и создание конфигураций
- **Генерация классов** индикаторов на лету
- **Регистрация** в IndicatorFactory

### IndicatorFactory - фабрика индикаторов
- **Единый интерфейс** для создания индикаторов
- **Управление** зарегистрированными индикаторами
- **Валидация** параметров и данных
- **Создание экземпляров** индикаторов по запросу пользователя

## 🔄 Правильный поток работы

### 1. LibraryManager загружает библиотеки
```python
# В __init__.py
def _register_all_indicators():
    # PRELOADED и CUSTOM индикаторы
    IndicatorFactory.register_indicator('macd_preloaded', MACDPreloadedIndicator)
    
    # LIBRARY индикаторы через LibraryManager
    library_results = LibraryManager.load_all_libraries()
    # LibraryManager.load_all_libraries() вызывает:
    # - PandasTALoader.register_indicators()
    # - TALibLoader.register_indicators()
    # Которые регистрируют индикаторы в IndicatorFactory
```

### 2. PandasTALoader регистрирует индикаторы
```python
class PandasTALoader:
    @classmethod
    def register_indicators(cls) -> int:
        # Обнаруживает функции pandas-ta
        # Создает классы индикаторов
        # Регистрирует их в IndicatorFactory
        IndicatorFactory.register_indicator(f'pandas_ta_{func_name}', indicator_class)
```

### 3. IndicatorFactory создает индикаторы
```python
# Пользователь создает индикатор
macd = IndicatorFactory.create('pandas_ta_macd', fast=12, slow=26, signal=9)
```

## 🏗️ Архитектурные принципы

### Single Responsibility Principle:
- **LibraryManager** - управление жизненным циклом библиотек
- **IndicatorFactory** - создание и управление индикаторами
- **PandasTALoader** - генерация классов индикаторов из pandas-ta

### Dependency Inversion:
- **LibraryManager** зависит от загрузчиков (PandasTALoader, TALibLoader)
- **IndicatorFactory** зависит от зарегистрированных классов
- **Загрузчики** регистрируют индикаторы в IndicatorFactory

### Отсутствие дублирования:
- **LibraryManager НЕ создает индикаторы** - это дублирует IndicatorFactory
- **IndicatorFactory НЕ управляет библиотеками** - это дублирует LibraryManager
- **Четкое разделение** ответственности без пересечений

## 🚀 План реализации

### Этап 1: Подготовка (1-2 часа)
- [ ] Убрать автоинициализацию из `pandas_ta.py`
- [ ] Убрать автоинициализацию из `talib.py`
- [ ] Проверить, что индикаторы не регистрируются автоматически

### Этап 2: Реализация универсального подхода (3-4 часа)
- [ ] Заменить хардкод в `pandas_ta.py` на динамическое обнаружение
- [ ] Реализовать методы `_discover_all_functions()`, `_analyze_function_dynamically()`, `_create_indicator_class_dynamically()`
- [ ] Убрать все методы `_register_*` и заменить на универсальный `register_indicators()`

### Этап 3: Интеграция LibraryManager (2-3 часа)
- [ ] Модифицировать `_register_all_indicators()` в `__init__.py`
- [ ] Добавить вызов `LibraryManager.load_all_libraries()`
- [ ] Добавить проверку доступности библиотек

### Этап 4: Тестирование (2-3 часа)
- [ ] Проверить, что все индикаторы загружаются автоматически
- [ ] Проверить обработку ошибок
- [ ] Проверить логирование
- [ ] Проверить, что новые индикаторы pandas-ta автоматически доступны

### Этап 5: Документация (1-2 часа)
- [ ] Обновить документацию по использованию
- [ ] Добавить примеры использования LibraryManager
- [ ] Документировать универсальный подход

## 🔍 Примеры использования LibraryManager

### Проверка доступности библиотеки
```python
from bquant.indicators import LibraryManager

# Проверить доступность pandas_ta
if LibraryManager.check_library_availability('pandas_ta'):
    print("pandas_ta доступна")
else:
    print("pandas_ta недоступна")

# Получить информацию о библиотеке
info = LibraryManager.get_library_info('pandas_ta')
print(f"Индикаторов: {info['indicators_count']}")
```

### Загрузка конкретной библиотеки
```python
# Загрузить только pandas_ta
count = LibraryManager.load_library('pandas_ta')
print(f"Загружено {count} индикаторов из pandas_ta")

# Загрузить все доступные библиотеки
results = LibraryManager.load_all_libraries()
print(f"Результаты загрузки: {results}")
```

## 🔍 Примеры использования IndicatorFactory

### Создание индикатора через IndicatorFactory
```python
from bquant.indicators import IndicatorFactory

# Создать MACD индикатор из pandas_ta
try:
    macd = IndicatorFactory.create('pandas_ta_macd', fast=12, slow=26, signal=9)
    print(f"Создан индикатор: {macd.name}")
except Exception as e:
    print(f"Ошибка создания: {e}")

# Создать PRELOADED индикатор
sma = IndicatorFactory.create('sma', length=20)

# Создать CUSTOM индикатор
custom_macd = IndicatorFactory.create('macd', fast=10, slow=20, signal=5)
```

### Автоматическое обнаружение новых индикаторов
```python
# После обновления pandas-ta новые индикаторы автоматически доступны
# Никаких изменений в коде не требуется!

# Например, если в pandas-ta появился новый индикатор 'kst':
# IndicatorFactory.create('pandas_ta_kst', ...) - автоматически работает
```

## 🔄 Полный пример работы

### Инициализация системы
```python
# 1. LibraryManager загружает библиотеки
LibraryManager.load_all_libraries()
# Результат: {'pandas_ta': 150, 'talib': 0}  # 150 индикаторов из pandas-ta

# 2. Индикаторы автоматически зарегистрированы в IndicatorFactory
available = IndicatorFactory.get_available_indicators()
print(f"Доступно индикаторов: {len(available)}")
# Вывод: Доступно индикаторов: 155 (5 PRELOADED + 150 pandas_ta)

# 3. Создание индикаторов
macd = IndicatorFactory.create('pandas_ta_macd', fast=12, slow=26, signal=9)
rsi = IndicatorFactory.create('pandas_ta_rsi', length=14)
```

## 📝 Заключение

**LibraryManager** - это хорошо спроектированный компонент для централизованного управления внешними библиотеками индикаторов, но он не используется в текущей архитектуре.

**Дополнительная проблема хардкода** в `pandas_ta.py` делает модуль не универсальным и не масштабируемым.

**Рекомендуется реализовать Вариант 1** - использовать LibraryManager для централизованной загрузки всех внешних библиотек + реализовать универсальный подход в PandasTALoader, что обеспечит:

- **Лучшую архитектуру** - централизованное управление библиотеками
- **0 хардкода** - автоматическое обнаружение всех индикаторов
- **100% автоматизацию** - новые индикаторы доступны без изменений кода
- **Масштабируемость** - код не растет с количеством индикаторов
- **Упрощенное тестирование** - единая логика для всех индикаторов
- **Более надежную обработку ошибок** - централизованная обработка
- **Четкое разделение ответственности** - LibraryManager управляет библиотеками, IndicatorFactory создает индикаторы

**Временное решение (Вариант 2)** можно использовать, если требуется быстрое исправление без изменения существующей логики, но оно не решает проблему хардкода.

**Идеальный результат:** 
1. **LibraryManager** загружает библиотеки и координирует загрузчики
2. **PandasTALoader** автоматически обнаруживает все функции pandas-ta и создает классы индикаторов
3. **IndicatorFactory** создает экземпляры индикаторов по запросу пользователя

**0 хардкода, 100% автоматизации, неограниченная масштабируемость, четкое разделение ответственности.**
