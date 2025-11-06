# Проблема и План Решения: Стратегии Анализа Свингов

**Статус:** Предложение
**Дата:** 2025-11-06

## 1. Описание Проблемы

В ходе разработки исследовательского кейса по анализу "состоятельности" зон (`05_case_study_zone_consistency.py`) была выявлена фундаментальная проблема в работе стратегий анализа свингов (`swing` strategies).

### Симптомы

При вызове пайплайна `analyze_zones` с любой из доступных `swing`-стратегий (`find_peaks`, `pivot_points`, `zigzag`), результирующие метрики свингов для всех зон были нулевыми. В частности, `num_swings`, `rally_count`, `drop_count` всегда были равны 0. Это делало невозможным проведение дальнейшего статистического анализа, основанного на внутренних колебаниях.

### Диагноз

Анализ исходного кода (`bquant/analysis/zones/strategies/swing.py`) выявил две основные причины проблемы:

1.  **Некорректная цель анализа:** Алгоритмы анализа свингов применялись к данным **индикатора** (например, к гистограмме MACD), а не к **ценовым данным** (`OHLC`). В пределах одной зоны индикатор часто ведет себя монотонно (только растет или только падает), не имея внутренних пиков и впадин, что и приводило к нулевому результату.

2.  **Расхождение с первоначальной задумкой:** Было подтверждено, что стратегия `zigzag` должна была использовать реализацию из библиотеки `pandas-ta`. Однако в текущем коде используется внутренняя, упрощенная реализация, основанная на `scipy.signal.find_peaks`. Это ограничивает гибкость и не соответствует ожиданиям от API.

## 2. План Решения: Редизайн API

Для устранения этих проблем предлагается не применять временные "затычки", а провести полноценный редизайн механизма вызова и работы свинг-стратегий.

### Основной Принцип

Все стратегии анализа свингов должны получать на вход **полный набор котировок (OHLC)** для анализируемой зоны, а не только отдельные столбцы. Это обеспечивает максимальную гибкость и совместимость с библиотечными индикаторами (например, `pandas-ta`), которые могут требовать весь OHLC-контекст для своих расчетов.

### Новый Дизайн API для `.with_strategies()`

Чтобы обеспечить необходимую гибкость, предлагается изменить формат аргумента `swing` в методе `.with_strategies()`.

**Было (текущая реализация):**

```python
.with_strategies(swing='zigzag')
```

**Предлагается (новый дизайн):**

Новый формат позволит явно указывать источник (`source`) и параметры (`params`) для стратегии, по аналогии с методом `.with_indicator()`.

1.  **Для библиотечных реализаций (например, `pandas-ta`):**

    ```python
    .with_strategies(swing={
        'source': 'pandas_ta',
        'name': 'zigzag',  # точное имя из pandas-ta (lowercase)
        'params': {'length': 5, 'percent': 0.01}  # параметры pandas-ta ZIGZAG
    })
    ```

    **Примечание:** В пакете уже реализована полная интеграция с pandas-ta через `IndicatorFactory` и `LibraryManager`. Зарегистрировано 158 индикаторов, включая `zigzag` (lowercase). Имена индикаторов соответствуют оригинальным именам из pandas-ta.

2.  **Для встроенных реализаций:**

    Для обратной совместимости и удобства, простые вызовы по имени должны сохраниться для встроенных стратегий.

    ```python
    # Простой вызов (как сейчас)
    .with_strategies(swing='find_peaks')

    # Явный вызов с параметрами
    .with_strategies(swing={
        'source': 'internal',
        'name': 'find_peaks',
        'params': {'distance': 3, 'min_amplitude_pct': 0.01}
    })
    ```

Этот подход делает API расширяемым, понятным и мощным, максимально используя существующую инфраструктуру пакета.

## 3. План Реализации

Для внедрения нового дизайна необходимо выполнить следующие шаги в указанной последовательности:

### Этап 1: Модифицировать `ZoneAnalysisBuilder`

**Файл:** `bquant/analysis/zones/builder.py`

Обновить метод `.with_strategies()`, чтобы он мог принимать как строку (для обратной совместимости), так и словарь для новой, структурированной конфигурации.

**Задачи:**
- [ ] Добавить проверку типа параметра `swing`: `str | dict | None`
- [ ] Сохранять конфигурацию в исходном формате для передачи в `ZoneFeaturesAnalyzer`
- [ ] Обновить docstring метода с примерами нового формата

```python
def with_strategies(self, swing: str | dict | None = None, ...) -> 'ZoneAnalysisBuilder':
    """Configure analysis strategies.

    Args:
        swing: Swing analysis strategy
            - str: Simple name for internal strategy (e.g., 'find_peaks')
            - dict: Structured config with 'source', 'name', 'params'
                Examples:
                {'source': 'internal', 'name': 'find_peaks', 'params': {...}}
                {'source': 'pandas_ta', 'name': 'zigzag', 'params': {...}}
    """
    if swing is not None:
        self._swing_config = swing  # Store as-is for ZoneFeaturesAnalyzer
    return self
```

**Дефолтное поведение:**

Если параметр `swing` не указан в `.with_strategies()`:
```python
.with_strategies()  # Без параметра swing
```

**Поведение:** `SwingMetrics` будут содержать нулевые значения. Это не является ошибкой - это ожидаемое поведение.

**Рекомендация:** Явно указывать `swing=None` если swing-анализ не требуется, либо использовать дефолтную стратегию (например, `swing='find_peaks'`).

---

### Этап 2: Обновить `ZoneFeaturesAnalyzer` - Добавить метод извлечения OHLC данных

**Файл:** `bquant/analysis/zones/features.py`

**КРИТИЧЕСКИ ВАЖНО:** Все swing-стратегии (как internal, так и pandas-ta) должны получать на вход **исходные OHLC данные** для диапазона зоны, а не индикаторные данные.

**Причина:** В пределах одной зоны индикатор (например, MACD histogram) часто монотонен (только растет или только падает), что делает поиск внутренних пиков/впадин бессмысленным. Ценовые данные (`high`/`low`) всегда содержат колебания, даже если индикатор показывает однородное поведение.

**Задачи:**
- [ ] Добавить метод `_get_zone_ohlc_data()` для извлечения OHLC данных
- [ ] Убедиться, что метод возвращает DataFrame с колонками `['time', 'open', 'high', 'low', 'close', 'volume']`
- [ ] Добавить проверку наличия всех необходимых колонок в `self.data`

**Реализация `_get_zone_ohlc_data()`:**
```python
def _get_zone_ohlc_data(self, zone: ZoneInfo) -> pd.DataFrame:
    """Extract OHLC data for zone time range from original price data.

    Returns:
        DataFrame with columns: ['time', 'open', 'high', 'low', 'close', 'volume']
    """
    zone_mask = (self.data['time'] >= zone.start_time) & (self.data['time'] <= zone.end_time)
    zone_ohlc = self.data.loc[zone_mask, ['time', 'open', 'high', 'low', 'close', 'volume']].copy()
    return zone_ohlc
```

**Правильный vs Неправильный подход:**

```python
# ✅ ПРАВИЛЬНО: извлекаем OHLC из исходного датасета
zone_ohlc = self._get_zone_ohlc_data(zone)
# zone_ohlc имеет колонки: ['time', 'open', 'high', 'low', 'close', 'volume']

# ❌ НЕПРАВИЛЬНО: использовать данные индикатора
# zone_data = self.data[zone_mask]  # содержит macd, macd_hist и т.д.
```

---

### Этап 3: Модифицировать `_calculate_swing_metrics()` для поддержки словарной конфигурации

**Файл:** `bquant/analysis/zones/features.py`

**Задачи:**
- [ ] Добавить парсинг конфигурации (строковый формат vs словарный формат)
- [ ] Добавить ветку для `source == 'pandas_ta'`
- [ ] Обновить вызов internal стратегий с передачей OHLC данных
- [ ] Добавить обработку ошибок с логированием
- [ ] Добавить метод `_empty_swing_metrics()` для возврата пустых метрик

**Реализация `_calculate_swing_metrics()`:**
   ```python
   def _calculate_swing_metrics(self, zone: ZoneInfo) -> dict:
       if self.swing_config is None:
           return self._empty_swing_metrics()

       # Get OHLC data for zone (NOT indicator data!)
       zone_ohlc = self._get_zone_ohlc_data(zone)

       # Parse configuration
       if isinstance(self.swing_config, str):
           # Simple format: 'find_peaks' -> internal
           source = 'internal'
           name = self.swing_config
           params = {}
       elif isinstance(self.swing_config, dict):
           source = self.swing_config.get('source', 'internal')
           name = self.swing_config['name']
           params = self.swing_config.get('params', {})
       else:
           raise ValueError(f"Invalid swing config type: {type(self.swing_config)}")

       # Create and execute strategy
       if source == 'pandas_ta':
           return self._execute_pandas_ta_strategy(name, params, zone_ohlc)
       else:  # source == 'internal'
           strategy = create_swing_strategy(name, **params)
           return strategy.analyze(zone_ohlc).to_dict()
   ```

---

### Этап 4: Интегрировать pandas-ta стратегии через существующую инфраструктуру

**Файл:** `bquant/analysis/zones/features.py`

Использовать `IndicatorFactory` и `LibraryManager` (уже реализованные в `bquant/indicators/`) для создания swing-стратегий на базе pandas-ta индикаторов.

**Задачи:**
- [ ] Реализовать метод `_execute_pandas_ta_strategy()` для выполнения pandas-ta индикаторов
- [ ] Реализовать метод `_convert_indicator_to_swing_metrics()` для конвертации результатов
- [ ] Добавить специфичную логику конвертации для `zigzag` индикатора
- [ ] Добавить generic fallback логику для других индикаторов
- [ ] Описать и реализовать расширяемый маппинг `индикатор → конвертер` с документированными ограничениями generic-режима
- [ ] Добавить обработку ошибок с логированием

#### Конвертация результатов нестандартных индикаторов

В первоначальном описании этапа 4 фигурировал «generic» конвертер: берутся все значения DataFrame, возвращённого индикатором, считаются не-`NaN` ячейки, и это число напрямую кладётся в `num_swings` (дальше — делится пополам для `rally_count`/`drop_count`). Такой подход годится только для инструментов, которые действительно выдают **разреженные** отметки экстремумов (пример — `zigzag`, где непустые значения появляются лишь в точках разворота).

Проблема в том, что большинство индикаторов библиотеки `pandas-ta` (и особенно пользовательские) возвращают **плотные** временные ряды без пропусков: скользящие средние (`sma`, `ema`), осцилляторы (`rsi`, `macd`, `stoch`), индексы объёма и т.д. Если на них запустить generic-конвертер, то «счётчик свингов» станет равен количеству свечей в зоне. Например:

* **RSI:** индикатор возвращает одно значение на каждую свечу. Для зоны из 120 баров generic-логика даст `num_swings = 120`, `rally_count = 60`, `drop_count = 60`. На графике RSI за этот же период может быть всего 4-6 реальных разворота, но отчёт покажет в двадцать раз больше «свингов».
* **MACD histogram:** DataFrame содержит столбцы `MACD`, `SIGNAL`, `HISTOGRAM`. Даже если из-за монотонности гистограммы не наблюдается ни одного внутреннего экстремума, generic-функция посчитает все 3 * 120 = 360 ненулевых ячеек и вернёт `num_swings = 360`. Аналитик получит «зашкаливающий» показатель и может сделать ложный вывод о сверхволатильности зоны.
* **Пользовательский индикатор тренда:** разработчик добавляет столбец `trend_strength`, где значения меняются плавно и без пропусков. Generic-конвертер посчитает каждый бар как свинг, хотя логика индикатора вообще не предполагает выделение экстремумов. Результат — полностью фиктивная статистика.

Именно поэтому generic-путь нельзя оставлять в качестве основной стратегии. Чтобы избежать таких артефактов, нужно реализовать следующий механизм:

1. **Специализированные конвертеры.** Для каждого поддерживаемого индикатора объявляется явная функция-конвертер, которая понимает структуру возвращаемого DataFrame/Series и корректно вычисляет `SwingMetrics`. Минимальный набор — `zigzag`, `zigzag_ht`, внутренние стратегии. По мере добавления новых индикаторов — расширять список.
2. **Расширяемый реестр.** Создать структуру данных (словарь, Enum или registry-класс), где ключом выступает полное имя индикатора (`library:name`), а значением — callable-конвертер. Реестр должен быть легко пополняемым без изменения базовой логики.
3. **Generic fallback как крайняя мера.** Универсальный путь (подсчёт ненулевых значений) сохранить только для сценариев, где индикатор действительно разреженный, и в коде явно логировать предупреждение (`logger.warning`) с перечислением предположений. Результат fallback'а должен быть «безопасным»: либо возвращаем пустые метрики, либо используем явно документированную эвристику (`num_swings = max(0, non_nan_count // 2)`), чтобы пользователь не трактовал цифры как точные.
4. **Документация и UX.** В developer docs и пользовательской документации прямо указать, что generic-конвертер — грубая эвристика. Для плотных индикаторов следует либо зарегистрировать собственный адаптер, либо отключить подсчёт свингов. В интерфейсе (логи, отчёты) стоит отображать предупреждение, что метрики получены через fallback и могут быть некорректными.

Такое описание исключает двусмысленность: разработчики понимают, почему generic-путь опасен, какие сценарии дают бессмысленные значения, и какие шаги нужно выполнить, чтобы получить корректные метрики.

**Параметры pandas-ta индикаторов:**

Для корректного использования pandas-ta индикаторов необходимо знать их точные имена и параметры. Используйте следующий код для получения информации:

```python
from bquant.indicators.library import LibraryManager

# Получить список всех доступных индикаторов
info = LibraryManager.get_library_info('pandas_ta')
print(f"Available: {info.get('available')}")
print(f"Total indicators: {info.get('indicators_count')}")

# Найти индикаторы, содержащие 'zigzag'
indicators = info.get('indicators', [])
zigzag_variants = [i for i in indicators if 'zigzag' in i.lower()]
print(f"Zigzag variants: {zigzag_variants}")
```

**Для ZIGZAG индикатора:**
- **Имя:** `'zigzag'` (lowercase)
- **Основные параметры:**
  - `length` (int): Количество баров для расчета (default: 5)
  - `percent` (float): Минимальное процентное изменение (default: 0.01, т.е. 1%)

**Пример использования:**
```python
result = analyze_zones(
    data,
    indicator='macd',
    strategy='combined'
).with_strategies(
    swing={
        'source': 'pandas_ta',
        'name': 'zigzag',
        'params': {'length': 5, 'percent': 0.01}
    }
).analyze()
```

**Реализация `_execute_pandas_ta_strategy()`:**

```python
def _execute_pandas_ta_strategy(self, name: str, params: dict, zone_ohlc: pd.DataFrame) -> dict:
    """Execute pandas-ta based swing strategy.

    Args:
        name: pandas-ta indicator name (e.g., 'zigzag')
        params: Parameters for the indicator
        zone_ohlc: OHLC DataFrame for the zone

    Returns:
        SwingMetrics as dict
    """
    from bquant.indicators.library import LibraryManager

    try:
        # Create pandas-ta indicator using existing infrastructure
        indicator = LibraryManager.create_indicator('pandas_ta', name, **params)

        # Calculate indicator on zone OHLC data
        result = indicator.calculate(zone_ohlc)  # Returns IndicatorResult

        # Convert indicator result to SwingMetrics
        return self._convert_indicator_to_swing_metrics(result, name)

    except Exception as e:
        logger.warning(f"Failed to execute pandas-ta strategy '{name}': {e}")
        return self._empty_swing_metrics()
```

**Новый метод `_convert_indicator_to_swing_metrics()`:**

```python
def _convert_indicator_to_swing_metrics(self, indicator_result, indicator_name: str) -> dict:
    """Convert pandas-ta indicator result to SwingMetrics format.

    Args:
        indicator_result: IndicatorResult from pandas-ta indicator
        indicator_name: Name of the indicator (for specific parsing logic)

    Returns:
        SwingMetrics as dict
    """
    data = indicator_result.data

    if indicator_name == 'zigzag':
        # pandas-ta ZIGZAG returns DataFrame with columns: ['ZZ', 'ZZ_PEAK', 'ZZ_VALLEY']
        # ZZ: zigzag line values (non-NaN at peaks/valleys)
        # ZZ_PEAK: 1 at peaks, 0 otherwise
        # ZZ_VALLEY: -1 at valleys, 0 otherwise

        if 'ZZ_PEAK' in data.columns and 'ZZ_VALLEY' in data.columns:
            peaks = data[data['ZZ_PEAK'] == 1]
            valleys = data[data['ZZ_VALLEY'] == -1]
        else:
            # Fallback: count non-NaN values in ZZ column and split by direction
            zz_values = data['ZZ'].dropna() if 'ZZ' in data.columns else pd.Series()
            if len(zz_values) < 2:
                return self._empty_swing_metrics()

            # Simple heuristic: alternating peaks/valleys
            num_swings = len(zz_values)
            rally_count = num_swings // 2 + (num_swings % 2)
            drop_count = num_swings // 2

            return {
                'num_swings': num_swings,
                'rally_count': rally_count,
                'drop_count': drop_count,
                'avg_swing_duration': None,
                'avg_swing_amplitude': None
            }

        num_peaks = len(peaks)
        num_valleys = len(valleys)
        num_swings = num_peaks + num_valleys

        # Calculate average swing duration and amplitude
        if num_swings > 1:
            swing_points = pd.concat([peaks, valleys]).sort_index()
            durations = swing_points.index.to_series().diff().dropna()
            avg_duration = durations.mean() if len(durations) > 0 else None

            swing_values = swing_points['ZZ'].values if 'ZZ' in swing_points.columns else []
            amplitudes = np.abs(np.diff(swing_values)) if len(swing_values) > 1 else []
            avg_amplitude = np.mean(amplitudes) if len(amplitudes) > 0 else None
        else:
            avg_duration = None
            avg_amplitude = None

        return {
            'num_swings': num_swings,
            'rally_count': num_peaks,
            'drop_count': num_valleys,
            'avg_swing_duration': avg_duration,
            'avg_swing_amplitude': avg_amplitude
        }

    else:
        # Generic conversion for other indicators
        # Assume non-NaN values indicate swing points
        logger.warning(f"Generic conversion for indicator '{indicator_name}' - may be inaccurate")
        non_nan_count = data.notna().sum().sum()
        return {
            'num_swings': int(non_nan_count),
            'rally_count': int(non_nan_count // 2),
            'drop_count': int(non_nan_count // 2),
            'avg_swing_duration': None,
            'avg_swing_amplitude': None
        }

def _empty_swing_metrics(self) -> dict:
    """Return empty swing metrics."""
    return {
        'num_swings': 0,
        'rally_count': 0,
        'drop_count': 0,
        'avg_swing_duration': None,
        'avg_swing_amplitude': None
    }
```

**Расширяемость на другие библиотеки:**

Предложенный дизайн легко расширяется на другие библиотеки технических индикаторов (например, `ta-lib`):

```python
.with_strategies(swing={
    'source': 'talib',
    'name': 'HT_TRENDMODE',  # Hilbert Transform - Trend vs Cycle Mode
    'params': {}
})
```

Для добавления поддержки новой библиотеки необходимо:
1. Добавить ветку `elif source == 'talib':` в `_calculate_swing_metrics()`
2. Реализовать метод `_execute_talib_strategy()` (аналогично `_execute_pandas_ta_strategy()`)
3. Добавить логику конвертации результата в `SwingMetrics`

---

### Этап 5: Исправить существующие internal стратегии

**Файл:** `bquant/analysis/zones/strategies/swing.py`

Переписать все внутренние стратегии (`FindPeaksSwingStrategy`, `PivotPointsSwingStrategy` и др.), чтобы они гарантированно применяли свою логику к **ценовым данным (OHLC)**, переданным в них, а не к данным индикатора.

**Задачи:**
- [ ] Обновить `FindPeaksSwingStrategy` для работы с OHLC данными
- [ ] Обновить `PivotPointsSwingStrategy` для работы с OHLC данными
- [ ] Обновить все другие существующие стратегии
- [ ] Убедиться, что метод `.analyze()` принимает DataFrame с колонками `['time', 'open', 'high', 'low', 'close', 'volume']`
- [ ] Использовать `high`/`low` для поиска пиков/впадин (вместо одного столбца индикатора)
- [ ] Обновить docstrings методов с указанием ожидаемого формата данных
- [ ] Добавить валидацию входных данных

---

### Этап 6: Написать тесты

**Файл:** `tests/analysis/zones/test_swing_strategies.py`

Покрыть новый функционал юнит-тестами.

**Задачи:**

- [ ] **Тест парсинга конфигурации:**
  - [ ] Строковый формат: `'find_peaks'`
  - [ ] Словарный формат internal: `{'source': 'internal', 'name': 'find_peaks', 'params': {...}}`
  - [ ] Словарный формат pandas-ta: `{'source': 'pandas_ta', 'name': 'zigzag', 'params': {...}}`
  - [ ] Некорректный формат (должен вызвать ValueError)

- [ ] **Тест извлечения OHLC данных для зоны:**
  - [ ] Проверить, что возвращается корректный DataFrame с нужными колонками
  - [ ] Проверить, что диапазон времени соответствует зоне
  - [ ] Проверить обработку пограничных случаев (пустая зона, зона вне диапазона данных)

- [ ] **Тест интеграции с pandas-ta:**
  - [ ] Создать тестовую зону с синтетическими данными
  - [ ] Выполнить `zigzag` стратегию с дефолтными параметрами
  - [ ] Выполнить `zigzag` стратегию с кастомными параметрами
  - [ ] Проверить, что `SwingMetrics` содержит ненулевые значения
  - [ ] Проверить структуру результата (все ключи присутствуют)

- [ ] **Тест конвертации IndicatorResult в SwingMetrics:**
  - [ ] Для `zigzag` индикатора (со всеми колонками ZZ, ZZ_PEAK, ZZ_VALLEY)
  - [ ] Для `zigzag` индикатора (только колонка ZZ - fallback логика)
  - [ ] Для generic индикатора (fallback логика)
  - [ ] Обработка пустых результатов

- [ ] **Regression тесты:**
  - [ ] Убедиться, что простой строковый формат (`swing='find_peaks'`) продолжает работать
  - [ ] Проверить обратную совместимость с существующими кейсами
  - [ ] Убедиться, что `swing=None` возвращает пустые метрики

---

### Этап 7: Обновить документацию

**Файлы:**
- `docs/api/analysis/zones.md`
- `docs/developer_guide/analytical_philosophy.md`

**Задачи:**
- [ ] Добавить примеры использования нового словарного формата в API документацию
- [ ] Описать интеграцию с pandas-ta (включая способ обнаружения доступных индикаторов)
- [ ] Добавить объяснение, что swing-стратегии применяются к OHLC данным, а не к индикаторам
- [ ] Обновить примеры кода для отражения best practices
- [ ] Добавить troubleshooting секцию для типичных ошибок
- [ ] Задокументировать ограничения generic-конвертера и описать процедуру регистрации кастомных конвертеров
- [ ] Обновить changelog в документации

---

## 4. Ожидаемый Результат

После выполнения всех этапов плана реализации:

**До (текущее состояние):**
```python
result = analyze_zones(data, indicator='macd').with_strategies(swing='zigzag').analyze()

# Для всех зон:
zone.features['swing'] = {
    'num_swings': 0,        # ❌ Всегда 0
    'rally_count': 0,       # ❌ Всегда 0
    'drop_count': 0,        # ❌ Всегда 0
}
```

**После (исправленное поведение):**
```python
result = analyze_zones(data, indicator='macd').with_strategies(
    swing={
        'source': 'pandas_ta',
        'name': 'zigzag',
        'params': {'length': 5, 'percent': 0.01}
    }
).analyze()

# Для зон:
zone.features['swing'] = {
    'num_swings': 12,           # ✅ Реальное значение
    'rally_count': 6,           # ✅ Количество пиков
    'drop_count': 6,            # ✅ Количество впадин
    'avg_swing_duration': 3.5,  # ✅ Средняя длительность свинга в барах
    'avg_swing_amplitude': 2.8  # ✅ Средняя амплитуда свинга
}
```

**Обратная совместимость сохранена:**
```python
# Простой формат продолжает работать
result = analyze_zones(data, indicator='macd').with_strategies(swing='find_peaks').analyze()
# ✅ Использует internal стратегию с дефолтными параметрами
```

## 5. Статус и Следующие Шаги

**Текущий статус:** План реализации готов, документ завершен

**Приоритет:** Высокий (блокирует исследовательский кейс `05_case_study_zone_consistency.py`)

**Оценка трудозатрат по этапам:**
- Этап 1 (ZoneAnalysisBuilder): ~30 минут
- Этап 2 (_get_zone_ohlc_data): ~30 минут
- Этап 3 (_calculate_swing_metrics): ~1-1.5 часа
- Этап 4 (pandas-ta интеграция): ~2-3 часа
- Этап 5 (internal стратегии): ~1-2 часа
- Этап 6 (тесты): ~2-3 часа
- Этап 7 (документация): ~1 час

**Итого:** ~8-12 часов работы

**Следующий шаг:** Начать с Этапа 1 (модификация `ZoneAnalysisBuilder.with_strategies()`)

**Прогресс выполнения:** Отмечайте выполненные задачи, заменяя `[ ]` на `[x]` в соответствующих чекбоксах плана.
