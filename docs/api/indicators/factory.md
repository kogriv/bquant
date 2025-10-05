# Фабрика и библиотека индикаторов

## IndicatorFactory (`bquant.indicators.base`)

`IndicatorFactory` — центральный реестр индикаторов BQuant. Он хранит классы для всех типов индикаторов
(встроенные PRELOADED, пользовательские CUSTOM и обёртки внешних библиотек) и предоставляет единый интерфейс
создания экземпляров.

### Основные методы

- `register_indicator(name, indicator_class)` — сохраняет класс индикатора в реестре. Используется как при ручной
  регистрации пользовательских индикаторов, так и загрузчиками внешних библиотек.
- `register_library_function(name, func)` — сохраняет оригинальную функцию библиотеки для обратных ссылок.
  Динамический загрузчик `pandas-ta` вызывает его для каждой обнаруженной функции.
- `create(source, indicator, **params) -> BaseIndicator` — современный интерфейс создания индикатора. Принимает
  источник (`preloaded`, `custom`, `pandas_ta`, `talib`) и имя индикатора без префиксов.
- `create_indicator(name, **kwargs)` — устаревшая оболочка, совместимая со старым API. В новых сценариях предпочтительно
  использовать `create()`.
- `list_indicators() -> Dict[str, str]` — возвращает реестр индикаторов и их тип (preloaded/custom/library).
- `get_indicator_info(name) -> Optional[Dict]` — предоставляет подробную информацию об индикаторе, если она определена
  в классе.

### Как работает реестр

- **PRELOADED/CUSTOM индикаторы** регистрируются под своим именем (например, `sma`, `macd_preloaded`).
- **LIBRARY индикаторы** регистрируются с ключом `{library}_{indicator}` (например, `pandas_ta_macd`). Динамические
  загрузчики (`PandasTALoader`, `TALibLoader`) создают наследников `LibraryIndicator` на лету и добавляют их в реестр.
- `LibraryManager` управляет загрузкой внешних библиотек и вызывает `IndicatorFactory.register_indicator()` для всех
  найденных обёрток. Благодаря этому `IndicatorFactory.create('pandas_ta', name, **params)` доступен без ручного кода.

### Пример: создание индикаторов

```python
from bquant.indicators import IndicatorFactory, LibraryManager

# PRELOADED и CUSTOM индикаторы регистрируются автоматически при импорте пакета
macd_preloaded = IndicatorFactory.create('preloaded', 'macd_preloaded')
custom_sma = IndicatorFactory.create('custom', 'sma', period=20)

# Загружаем внешние библиотеки (pandas-ta, TA-Lib)
LibraryManager.load_all_libraries()

# Создаём индикаторы из pandas-ta без ручной регистрации
macd = IndicatorFactory.create('pandas_ta', 'macd', fast=12, slow=26, signal=9)
rsi = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
```

### Пример: получение метаданных

```python
from bquant.indicators import IndicatorFactory

info = IndicatorFactory.get_indicator_info('pandas_ta_macd')
print(info['description'])
print(info['parameters'])
```

## Встроенные индикаторы (`bquant.indicators`)

При импорте `bquant.indicators` вызывается вспомогательная функция `_register_all_indicators()`, которая:

1. Регистрирует PRELOADED индикаторы (например, `MACDPreloadedIndicator`).
2. Добавляет CUSTOM реализации (SMA, EMA, RSI, MACD, Bollinger Bands).
3. Делегирует загрузку внешних библиотек `LibraryManager.load_all_libraries()`.

Благодаря этому любой индикатор можно создать одной строкой через `IndicatorFactory.create()` или «простой способ»
через `LibraryManager.create_indicator()`.

## Загрузчики внешних библиотек

- `PandasTALoader` автоматически обнаруживает десятки функций `pandas-ta`, создаёт для них обёртки и регистрирует их в
  `IndicatorFactory`.
- `TALibLoader` выполняет аналогичную задачу для `TA-Lib` (при наличии зависимости).
- `LibraryManager` отвечает за последовательную загрузку, логирование и предоставление информации о доступных
  индикаторах пользователю.

Подробнее о менеджере библиотек см. в разделе [LibraryManager](library_manager.md).
