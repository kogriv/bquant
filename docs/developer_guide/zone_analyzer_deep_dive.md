# Глубокое погружение: Пайплайн анализатора зон

> 💡 **Для кого это руководство?**
>
> Этот документ предназначен для разработчиков и аналитиков, которые хотят понять **внутреннюю логику и механику** универсального пайплайна `analyze_zones`. Если вы ищете справочник по функциям и параметрам, обратитесь к [API документации](../api/analysis/zones.md).

### Импорт

Рекомендуемый импорт (через публичный API модуля):

```python
from bquant.analysis.zones import analyze_zones
```

---

## 1. Главная идея: Универсальность и Контекст

Основная цель пайплайна `analyze_zones` — предоставить **универсальный** инструмент для исследования рыночных "зон". Зона — это не просто отрезок времени, а период, выделенный по определенному правилу, основанному на поведении технического индикатора.

Ключевая инновация — **контекст**. Каждая найденная зона "знает", как она была обнаружена: какой индикатор использовался, по какой стратегии (пересечение нуля, выход из зоны перекупленности и т.д.) и с какими параметрами. Это позволяет анализировать и визуализировать зоны от **любого индикатора** (MACD, RSI, Stochastic или даже вашего собственного) единым образом, без необходимости переписывать код.

---

## 2. Пошаговый процесс анализа

Пайплайн представляет собой "конструктор" (builder), где вы по шагам настраиваете каждый аспект анализа.

**Обязательные и опциональные методы:**
- **Обязательно:** `detect_zones()` — без него `build()` вызовет ошибку.
- **Опционально:** `with_indicator()`, `with_strategies()`, `with_swing_preset()`, `with_swing_scope()`, `with_cache()`, `with_auto_swing_thresholds()`, `analyze()`.
- Если `with_strategies()` не вызван, считаются свинги (`zigzag`) и форма (`statistical`); дивергенции, волатильность и объём — только по запросу.

#### Шаг 1: Инициализация (`analyze_zones(df)`)

-   **Что происходит?** Вы передаете в пайплайн исходные данные — DataFrame с колонками `open`, `high`, `low`, `close`, `volume`.
-   **Результат:** Создается объект-конструктор `ZoneAnalysisBuilder`, который готов к дальнейшей настройке.

#### Шаг 2: Расчет индикатора (`.with_indicator(...)`)

-   **Что происходит?** На этом шаге вы "сообщаете" пайплайну, какой индикатор использовать. Это может быть:
    -   **Встроенный индикатор**: Например, `.with_indicator('custom', 'macd', ...)` рассчитает MACD.
    -   **Индикатор из библиотеки `pandas-ta`**: Например, `.with_indicator('pandas_ta', 'rsi', length=14)` рассчитает RSI.
    -   **Уже существующий индикатор**: Если в вашем DataFrame уже есть колонка с индикатором, этот шаг можно пропустить.
-   **Результат:** В DataFrame добавляются колонки индикатора, названные по его идентичности (`macd_12_26_9__line`, `macd_12_26_9__signal`, `macd_12_26_9__hist`; у pandas-ta — свои имена, например `RSI_14`), и колонка `atr` (период — `.with_atr_period()`, по умолчанию 14), если её не принесли. Карта «роль → колонка» едет в `result.column_schema`.

#### Шаг 3: Детекция зон (`.detect_zones(...)`)

-   **Что происходит?** Это ядро процесса. Здесь пайплайн ищет на графике индикатора отрезки, соответствующие заданной **стратегии детекции**.
-   **Доступные стратегии:**
    -   `'zero_crossing'`: Находит зоны, где индикатор-осциллятор (например, гистограмма MACD) находится выше или ниже нуля. Требует `indicator_role` (`'hist'`, `'value'`, …) — или `indicator_col`, если колонку принесли вы сами.
    -   `'threshold'`: Находит зоны, где индикатор (например, RSI) выходит за пределы заданных порогов (например, выше 70 или ниже 30). Требует `indicator_role`/`indicator_col`, `upper_threshold`, `lower_threshold`.
    -   `'line_crossing'`: Находит зоны между пересечениями двух линий индикатора (например, основной и сигнальной линий Stochastic). Требует `line1_role`/`line2_role` или `line1_col`/`line2_col`.
    -   `'preloaded'`: Загружает зоны из внешнего DataFrame. Полезно для анализа заранее определённых зон.
    -   `'combined'`: Объединяет несколько правил детекции в одну стратегию.
-   **Результат:** Создается предварительный список зон. Каждая зона — это объект с временем начала, временем конца, индексами (`start_idx`, `end_idx`) и типом (`bull`/`bear`).

#### Шаг 4: Глубокий анализ характеристик

Это самый насыщенный этап анализа, состоящий из трех логических частей: подключение стратегий, запуск анализа и сборка результата.

##### 4.1. Подключение стратегий анализа (`.with_strategies(...)`)

На этом шаге вы сообщаете пайплайну, какие именно характеристики (метрики) нужно извлечь из каждой зоны. Это делается путем передачи строковых идентификаторов для каждого типа анализа.

-   **Что происходит?** Вы выбираете и настраиваете "анализаторы", которые будут применяться к каждой зоне.
-   **Доступные стратегии:**
    -   **Анализ внутренних колебаний (`swing`):**
        -   `swing='find_peaks'`: Поиск пиков и впадин на основе `scipy.signal.find_peaks`. Требует подбора порогов или пресета.
        -   `swing='pivot_points'`: Классические точки разворота. Может давать низкое покрытие зон на коротких таймфреймах.
        -   `swing='zigzag'`: Поиск экстремумов с помощью индикатора ZigZag. **Рекомендуется для исследовательского анализа и проверки гипотез** — на встроенном сэмпле покрывает 56% бычьих зон в `per_zone` и 92% в `global` (замер 2026-09-04). См. [Сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md).
    -   **Анализ формы (`shape`):**
        -   `shape='statistical'`: Расчет статистических моментов (асимметрия, эксцесс) для формы индикатора.
    -   **Анализ дивергенций (`divergence`):**
        -   `divergence='classic'`: Поиск классических бычьих и медвежьих дивергенций.
    -   **Анализ волатильности (`volatility`):**
        -   `volatility='combined'`: Расчет составного индекса волатильности внутри зоны.
    -   **Анализ объема (`volume`):**
        -   `volume='standard'`: Расчет метрик, связанных с объемом.

##### 4.2. Запуск анализа и доп. процессов (`.analyze(...)`)

Этот метод запускает извлечение всех метрик, настроенных на предыдущем шаге. Кроме того, он может запускать дополнительные высокоуровневые аналитические процессы.

**Параметры:**
-   `clustering` (bool, по умолчанию `True`): Включить кластеризацию зон.
-   `n_clusters` (int, по умолчанию `3`): Количество кластеров для KMeans.
-   `regression` (bool, по умолчанию `False`): Объясняющая (in-sample) регрессия длительности и доходности зоны на её признаки — `explain_zone_duration`/`explain_price_return`; не прогноз: признаки известны только по окончании зоны.
-   `validation` (bool, по умолчанию `False`): Out-of-sample проверка детекции — кадр делится 70/30, частота зон на бар обязана удержаться; итог в `result.validation_results` и `result.metadata['validation']`.
-   `min_duration` (int, по умолчанию `1`): порог отчётности — короткие зоны остаются в `result.zones`, но не входят в агрегаты.

-   **Что происходит?**
    1.  Пайплайн проходит по каждой зоне и применяет к ней все стратегии, указанные в `.with_strategies()`. Результаты сохраняются в словарь `zone.features`.
    2.  **Кластеризация:** Если передан аргумент `clustering=True`, запускается алгоритм кластеризации (например, KMeans) для группировки похожих зон. Результаты доступны в `result.clustering`.
    3.  **Статистические тесты:** Пайплайн **автоматически** запускает набор тестов гипотез (например, t-тест для сравнения доходностей бычьих и медвежьих зон). Результаты доступны в `result.hypothesis_tests`.

##### 4.3. Ключевые метрики (Features), генерируемые стратегиями

Главный результат этого шага — наполнение словаря `features` для каждой зоны. Ниже приведены примеры ключевых метрик, которые генерируют разные стратегии.

| Стратегия (`.with_strategies(...)`) | Ключевая метрика в `zone.features` | Описание |
| :--- | :--- | :--- |
| всегда | `num_peaks`, `num_troughs`, `peak_time_ratio`, `trough_time_ratio`, `drawdown_from_peak`, `rally_from_trough`, `price_return`, `atr_normalized_return`, `oscillator_amplitude`, `correlation_price_oscillator` | Верхний уровень `zone.features`; считаются по `close`/`high`/`low` и колонке индикатора из контекста, стратегии для них не нужны. |
| `swing='*'` | `metadata['swing_metrics']` | 23 поля: `num_swings`, `rally_count`, `drop_count`, `avg_rally_pct`, `avg_drop_pct`, `rally_to_drop_ratio`, длительности и скорости, `strategy_name`, `strategy_params`. |
| `shape='statistical'` | `metadata['shape_metrics']` | `hist_skewness`, `hist_kurtosis`, `hist_smoothness`. |
| `divergence='classic'` | `metadata['divergence_metrics']` | `divergence_type` (`none`/`regular`/`hidden`/`mixed`), `divergence_count`, `divergence_strength`, `divergence_direction`. |
| `volatility='combined'` | `metadata['volatility_metrics']` | `volatility_score`, `volatility_regime`, `atr_trend`, `atr_normalized_range`, полосы Боллинджера (`bollinger_*`). |
| `volume='standard'` | `metadata['volume_metrics']` | `avg_volume_zone`, `volume_zone_ratio`, `volume_at_entry_change`, `volume_indicator_corr`. |

Ключи сняты прогоном полного пайплайна на сэмпле; `has_classic_divergence`, `skewness` и `kurtosis` верхнего уровня, которые здесь стояли раньше, в результате не существуют.

**Структура `zone.features` и вложенные метрики:**

Часть метрик хранится на верхнем уровне `zone.features`, а часть — во вложенном словаре `metadata`. Метрики свингов (rally/drop counts, avg_rally_pct, avg_drop_pct) находятся в `metadata['swing_metrics']`:

```python
# Метрики верхнего уровня (напрямую)
num_peaks = zone.features.get('num_peaks')
peak_time_ratio = zone.features.get('peak_time_ratio')

# Метрики свингов (через metadata)
metadata = zone.features.get('metadata', {})
swing_metrics = metadata.get('swing_metrics', {})
rally_count = swing_metrics.get('rally_count')
drop_count = swing_metrics.get('drop_count')
avg_rally_pct = swing_metrics.get('avg_rally_pct')
avg_drop_pct = swing_metrics.get('avg_drop_pct')
num_swings = swing_metrics.get('num_swings')
```

Аналогично: `metadata['shape_metrics']`, `metadata['divergence_metrics']`, `metadata['volatility_metrics']`, `metadata['volume_metrics']` — для соответствующих стратегий.

##### 4.4. Опциональная настройка пайплайна

Эти методы вызываются **до** `.build()` в любом порядке и позволяют fine-tune поведение пайплайна:

| Метод | Описание |
| :--- | :--- |
| `.with_swing_preset(name)` | Применить именованный пресет параметров для свингов. Пресетов два: `'narrow_zone'` (по умолчанию) и `'wide_zone'` (`SWING_PRESETS` в `bquant/core/config.py`). Фиксирует пороги для `find_peaks`, `pivot_points`, `zigzag`. |
| `.with_swing_scope(scope)` | Режим расчёта свингов. **По умолчанию** `'global'` — свинги вычисляются один раз по всему датасету и «нарезаются» по зонам. `'per_zone'` — свинги считаются отдельно внутри каждой зоны. `global` часто даёт выше покрытие (см. кейс по состоятельности). |
| `.with_cache(enable=True, ttl=3600)` | Включить/отключить кэширование результата. `ttl` — время жизни кэша в секундах. Отключайте кэш (`enable=False`) при экспериментировании с разными параметрами. |
| `.with_auto_swing_thresholds(enable=True)` | Вывести порог из самих данных вместо константы пресета. После G38 (2026-09-03) слой трогает **только** `deviation` у `zigzag`; `find_peaks` и `pivot_points` остаются на пороге пресета. До G38 было наоборот — и обнуляло их покрытие. |
| `.with_atr_period(period)` | Период колонки `atr`, которую пайплайн добавляет сам (по умолчанию 14); входит в ключ кэша. |

Пример исследовательского пайплайна с настройкой свингов:

```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .with_swing_preset('narrow_zone')
    .with_swing_scope('global')
    .with_cache(enable=False)  # отключить кэш при сравнении стратегий
    .analyze(clustering=False)
    .build()
)
```

#### Шаг 5: Сборка (`.build()`)

-   **Что происходит?** Финальный вызов, который запускает весь настроенный конвейер в правильном порядке: `.with_indicator` -> `.detect_zones` -> `.analyze`.
-   **Результат:** Возвращается единый, полностью готовый объект `ZoneAnalysisResult`.

---
#### Пример полного пайплайна

Вот как выглядит полный цикл анализа в коде, объединяющий все шаги:

```python
from bquant.analysis.zones import analyze_zones

# Базовый пайплайн от данных до результата
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag', shape='statistical', divergence='classic')
    .with_swing_preset('narrow_zone')
    .with_swing_scope('global')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

# Пример доступа к извлеченным метрикам
zone = result.zones[0]
print(f"Положение пика: {zone.features.get('peak_time_ratio')}")
print(f"Длительность: {zone.features.get('duration')}")

# Доступ к метрикам свингов (для анализа состоятельности зон)
swing_metrics = zone.features.get('metadata', {}).get('swing_metrics', {})
if swing_metrics:
    print(f"Ап-свингов: {swing_metrics.get('rally_count')}, "
          f"даун-свингов: {swing_metrics.get('drop_count')}")

# Результаты тестов гипотез
if result.hypothesis_tests:
    print(result.hypothesis_tests['summary'])
```

---

## 3. Итоговая информация (объект `ZoneAnalysisResult`)

В результате вы получаете не просто набор цифр, а структурированный объект, готовый к дальнейшему исследованию и визуализации.

-   **`result.zones`**: Это список объектов `ZoneInfo`. Каждый объект `ZoneInfo` — это исчерпывающее описание одной зоны:
    -   `zone_id`, `type`, `start_time`, `end_time`: Базовая информация.
    -   `start_idx`, `end_idx`, `duration`: Позиционные индексы и число баров в зоне.
    -   `data`: Срез DataFrame с OHLCV и индикаторами для зоны.
    -   **`features`**: Словарь со всеми численными метриками, извлеченными на Шаге 4 (например, `{'duration': 15, 'price_return': 0.012, 'num_peaks': 3, 'metadata': {...}}`). **Это и есть главные данные для анализа.** См. структуру `zone.features` и `metadata` выше.
    -   **`indicator_context`**: Словарь, описывающий, как зона была найдена — на сэмпле `{'detection_strategy': 'zero_crossing', 'detection_indicator': 'macd_12_26_9__hist', 'signal_line': None, 'detection_rules': {'indicator_col': 'macd_12_26_9__hist'}}`. Это ключ к универсальности: по `detection_indicator` считаются метрики осциллятора; без него они `None`, а не угадываются по первой попавшейся колонке (G61).
    -   `swing_context` (при глобальном режиме, по умолчанию): Контекст свингов для метода `zone.get_zone_swings()`.

-   **`result.statistics`**: Агрегированная статистика по зонам — шесть разделов: `total_statistics`, `duration_distribution`, `return_distribution`, `line_amplitude_distribution`, `oscillator_amplitude_distribution`, `additional_metrics`. Распределения по часам суток здесь нет.

-   **`result.clustering`**: Если была включена кластеризация, здесь хранятся ее результаты (например, какому кластеру принадлежит каждая зона).

-   **`result.visualize(...)`**: Встроенный метод, который использует всю собранную информацию (особенно `indicator_context`) для автоматического построения [графиков визуализации зон](../api/visualization/zones.md).

### Итог

Пайплайн `analyze_zones` — это конвейер, который превращает сырые ценовые данные в богатый, структурированный набор данных. Он не просто находит отрезки на графике, а **количественно описывает** их внутреннюю структуру (через `features`) и **сохраняет контекст** их обнаружения (через `indicator_context`), что делает результаты универсальными, воспроизводимыми и готовыми к немедленной визуализации и дальнейшему анализу.

---

## 4. Статистическая верификация

Поиск и описание зон — это первый шаг анализа. Однако, чтобы убедиться, что найденные закономерности (например, повышенная доходность в бычьих зонах) не являются случайностью, их необходимо проверить с помощью статистических тестов.

**Для подробного изучения методов валидации и проверки гипотез обратитесь к нашему руководству:**

**➡️ [Руководство по рабочему процессу статистического анализа](./statistical_analysis_workflow.md)**

---

## 🔗 См. также

- **[Технический справочник API (analysis.zones)](../api/analysis/zones.md)**: Полный список классов, методов и параметров.
- **[Документация по визуализации](../api/visualization/zones.md)**: Как визуализировать полученные зоны.
- **[Руководство пользователя по анализу зон](../user_guide/zone_analysis.md)**: Практические примеры использования.
- **[Сравнение свинг-стратегий](../analytics/zones/swing_strategy_comparison_case_study.md)**: покрытие и время стратегий свингов в режимах `per_zone`/`global`.
