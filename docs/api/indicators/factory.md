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

# PRELOADED и CUSTOM индикаторы регистрируются при импорте пакета
macd_preloaded = IndicatorFactory.create('preloaded', 'macd_preloaded')
custom_sma = IndicatorFactory.create('custom', 'sma', period=20)

# Внешние библиотеки (pandas-ta, TA-Lib) подгружаются при первом обращении —
# явный вызов LibraryManager.load_all_libraries() не нужен
macd = IndicatorFactory.create('pandas_ta', 'macd', fast=12, slow=26, signal=9)
rsi = IndicatorFactory.create('pandas_ta', 'rsi', length=14)
```

### Пример: получение метаданных

```python
from bquant.indicators import IndicatorFactory, LibraryManager

LibraryManager.load_all_libraries()
info = IndicatorFactory.get_indicator_info('pandas_ta_macd')

print(sorted(info))
print(info['source'], info['class'], repr(info['description']))
# ['class', 'description', 'name', 'source']
# library PandasTAMacd 'No description'
```

`'No description'` у индикаторов из библиотеки — не ошибка: описание берётся из класса, а
обёртки над функциями `pandas-ta` создаются на лету и своего описания не имеют.

## Встроенные индикаторы (`bquant.indicators`)

При импорте `bquant.indicators` один бутстрап (`_bootstrap_registry()`) регистрирует
PRELOADED индикатор (`MACDPreloadedIndicator`) и пять CUSTOM (SMA, EMA, RSI, MACD,
Bollinger Bands) — классы этого пакета, дёшево и без побочных эффектов. **Внешние
библиотеки при импорте не загружаются**: `IndicatorFactory` зовёт
`LibraryManager.ensure_loaded()` при первом запросе библиотечного индикатора, полного списка
или сведений об индикаторе. До G64 (2026-09-06) импорт тянул `import pandas_ta` (≈1 с на тёплом
кэше numba, десятки секунд на холодном) и регистрировал встроенные индикаторы трижды.

Любой индикатор создаётся одной строкой через `IndicatorFactory.create()` или «простой способ»
через `LibraryManager.create_indicator()`.

## Загрузчики внешних библиотек

- `PandasTALoader` автоматически обнаруживает десятки функций `pandas-ta`, создаёт для них обёртки и регистрирует их в
  `IndicatorFactory`.
- `TALibLoader` выполняет аналогичную задачу для `TA-Lib` (при наличии зависимости).
- `LibraryManager` отвечает за последовательную загрузку, логирование и предоставление информации о доступных
  индикаторах пользователю.

Подробнее о менеджере библиотек см. в разделе [LibraryManager](library_manager.md).
