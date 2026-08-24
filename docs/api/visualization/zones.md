# Zone Visualization - Визуализация зон

## 📚 Обзор

Модуль `bquant.visualization.zones` предоставляет комплексные инструменты для визуализации торговых зон, обнаруженных с помощью [Universal Zone Analysis Pipeline](../analysis/zones.md). Поддерживает два backend'а визуализации — **Plotly** (интерактивный) и **Matplotlib** (статический) — с автоматическим fallback при недоступности библиотек.

**Ключевые возможности:**
- 🎯 **Два основных подхода**: Встроенный вызов `result.visualize()` и прямое использование класса `ZoneVisualizer`.
- 📊 **4 режима визуализации**: `overview`, `detail`, `comparison`, `statistics`.
- 🕒 **Продвинутое управление осью времени**: Режимы `dense` (без разрывов) и `timeseries` (реальное время).
- ⚙️ **Гибкая настройка индикаторов**: Автоматическое определение, явное указание и настройка типов графиков (`line`/`bar`).
- 💾 **Удобный экспорт**: Встроенная функция `save_figure` с умными настройками по умолчанию для сохранения в PNG/HTML.
- 🎨 **Полная кастомизация**: Управление контекстом, количеством тиков, отображением гэпов и панелями.

---

## 🚀 Рекомендуемый рабочий процесс

Для большинства задач рекомендуется следующий двухэтапный процесс:

1.  **Анализ**: Используйте [Universal Zone Analysis Pipeline](../analysis/zones.md) для обнаружения и анализа зон.
    ```python
    from bquant.analysis.zones import analyze_zones
    from bquant.data.samples import get_sample_data

    # Запускаем пайплайн
    result = (
        analyze_zones(get_sample_data('tv_xauusd_1h'))
        .with_indicator('custom', 'macd')
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze()
        .build()
    )
    ```

2.  **Визуализация**: Используйте метод `result.visualize()` для создания графиков. Это самый простой и мощный способ.
    ```python
    # Общий обзор всех зон
    fig_overview = result.visualize('overview', title="MACD Zones Overview")

    # Детальный обзор одной зоны
    fig_detail = result.visualize('detail', zone_id=3, context_bars=15)

    # Сравнение нескольких зон
    fig_comparison = result.visualize('comparison', max_zones=4)

    # Показать график
    fig_overview.show()
    ```

---

## 🎯 Встроенная визуализация из `ZoneAnalysisResult`

Метод `result.visualize(mode, **kwargs)` — это основной и наиболее удобный интерфейс для визуализации.

### Режим `overview`

Общий обзор всех зон на графике цены.

```python
fig = result.visualize(
    'overview',
    title="Zones Overview with Timeseries Axis",
    show_indicators=True,
    time_axis_mode='timeseries'  # Отображение с учетом реального времени (включая выходные)
)
```

**Ключевые параметры `overview`:**
- `show_indicators` (bool, default=`False`): Отобразить панель с индикаторами.
- `indicator_chart_types` (dict, optional): Явно задать тип графика для индикатора. Пример: `{'macd_hist': 'bar'}`.
- `time_axis_mode` (str, default=`'dense'`): Режим оси времени.
  - `'dense'`: Убирает разрывы (выходные), отображая только торговые дни. Быстро и компактно.
  - `'timeseries'`: Сохраняет временную шкалу, показывая разрывы. Идеально для анализа пропорций.
- `xaxis_num_ticks` (int, default=16): Желаемое количество меток на оси X (только для `dense` режима).
- `show_gap_lines` (bool, default=`False`): Показывать вертикальные линии в местах временных разрывов.
- `date_range` (Tuple[datetime, datetime], optional): Фильтрация по диапазону дат. См. [раздел ниже](#фильтрация-по-диапазону-дат-date_range).
- `show_aggregate_metrics` (bool, default=`False`): Отобразить агрегированные метрики по зонам. См. [раздел ниже](#агрегированные-метрики).
- `aggregate_metrics_mode` (str, default=`'compact'`): Режим вывода метрик (`'compact'` или `'full'`).
- `show_swings` (bool, default=`False`): Отобразить swing-точки (peaks/troughs) на графике.
- `swing_marker_size` (int, default=8): Размер маркеров для swing-точек.

#### Фильтрация по диапазону дат: `date_range`

При использовании параметра `date_range` визуализатор автоматически фильтрует как данные, так и зоны:

```python
import pandas as pd

# Создаем диапазон дат
start_date = pd.Timestamp('2025-06-25', tz='UTC')
end_date = pd.Timestamp('2025-07-03', tz='UTC')

# Визуализируем только этот период
fig = result.visualize(
    'overview',
    date_range=(start_date, end_date),
    title=f"Zones from {start_date.date()} to {end_date.date()}",
    show_aggregate_metrics=True,  # Метрики будут считаться только для этого периода!
    show_swings=True
)
```

**⚠️ Важно**: Агрегированные метрики (если включены) рассчитываются **только для зон в выбранном диапазоне**, а не по всему датасету. Это позволяет анализировать характеристики зон в разные временные периоды.

**Пример use case** - сравнение поведения зон по месяцам:
```python
# Июнь
fig_june = result.visualize('overview',
    date_range=(pd.Timestamp('2025-06-01'), pd.Timestamp('2025-06-30')),
    show_aggregate_metrics=True, aggregate_metrics_mode='full')

# Июль
fig_july = result.visualize('overview',
    date_range=(pd.Timestamp('2025-07-01'), pd.Timestamp('2025-07-31')),
    show_aggregate_metrics=True, aggregate_metrics_mode='full')

# Метрики будут разные для каждого месяца!
```

#### Цвет зоны следует объявленной полярности

Цвет и подпись зоны берутся из **объявленных свойств** её типа, а не из имени. Стратегия
детекции объявляет для каждого типа полярность (см.
[`ZoneType`](../analysis/zones.md)), а визуализатор отображает её в палитру:

| Полярность | Смысл | Plotly | Matplotlib |
|---|---|---|---|
| `+1` | ряд приподнят | `#00ff88` | `lightgreen` |
| `-1` | ряд подавлен | `#ff4444` | `lightpink` |
| `0` | объявленно нейтральная | `#a0a0a0` | `lightgrey` |
| `None` | направление не объявлено | `#0088ff` | `lightblue` |

Раньше палитра была словарём по именам с фолбэком на `'bull'`, поэтому зона любого другого
типа молча рисовалась бычьим цветом — график сообщал направление, которого никто не
объявлял. Для `bull`/`bear` цвета не изменились.

**Изменение поведения:** matplotlib-пути раньше красили приподнятые зоны в `lightblue`, а
всё остальное — в `lightpink`. Теперь оба бэкенда согласованы, и приподнятая зона на
matplotlib-графике зелёная, а не голубая.

Именованные переопределения по-прежнему возможны и имеют приоритет над полярностью:

```python
from bquant.visualization.zones import ZoneVisualizer

visualizer = ZoneVisualizer()
visualizer.zone_colors['overbought'] = {
    'fill': 'rgba(255, 136, 0, 0.3)',
    'line': '#ff8800',
}
```

#### Агрегированные метрики

Параметр `show_aggregate_metrics` добавляет на график текстовую аннотацию с агрегированной
статистикой **по каждому встреченному типу зон** — `bull`/`bear` у MACD,
`overbought`/`neutral`/`oversold` у порогового детектора, и так далее. Порядок блоков
определяется объявленной полярностью: приподнятые, нейтральные, подавленные.

```python
fig = result.visualize(
    'overview',
    show_aggregate_metrics=True,        # Включить метрики
    aggregate_metrics_mode='compact',   # Режим: 'compact' (8 строк) или 'full' (~16 строк)
)
```

**Режимы вывода**:

- **`compact`** (по умолчанию, 8 строк):
  ```
  📊 Bull Zones: 37/37 with swings (100%)
    Avg Rally: +1.11% ± 0.70%
    Avg Drop: -1.00% ± 0.64%
    Rally/Drop Ratio: 1.11x
  ```

- **`full`** (~16 строк, включает длительности):
  ```
  📊 Bull Zones: 37/37 with swings (100%)
    Avg Rally: +1.11% ± 0.70% (3.5 ± 1.2 bars)
    Avg Drop: -1.00% ± 0.64% (2.1 ± 0.8 bars)
    Rally/Drop Ratio: 1.11x
    Avg Swing Duration: 2.8 ± 1.5 bars
  ```

**Метрики включают** (v1.0):
- Покрытие зон свингами (% зон с обнаруженными свингами)
- Средняя амплитуда rally/drop (mean ± std)
- Ratio (соотношение rally к drop)
- Средняя длительность движений в барах (только в `full` режиме)

**Примечание**: Текущая версия (v1.0) использует MVP-агрегацию с mean±std. Расширенная версия (v1.2) с median/IQR и shape метриками запланирована. См. [zomet_v1.2_advanced_aggregation.md](../../../devref/gaps/graph/zomet_v1.2_advanced_aggregation.md).

---

### Режим `detail`

Детальный просмотр одной зоны с окружающим контекстом.

```python
# Найти зону для анализа
median_zone = min(result.zones, key=lambda z: abs(z.duration - 30))

fig = result.visualize(
    'detail',
    zone_id=median_zone.zone_id,
    context_bars=20,
    show_indicators=True,
    show_volume=True,
    time_axis_mode='dense',
    xaxis_num_ticks=20,
    title=f"Detail for Zone #{median_zone.zone_id}"
)
```

**Ключевые параметры `detail`:**
- `zone_id` (int, **required**): ID зоны для детального просмотра.
- `context_bars` (int, default=20): Количество баров до и после зоны для контекста.
- `show_indicators` (bool, default=`True`): Показать панель индикаторов.
- `show_volume` (bool, default=`True`): Показать панель объема.
- `time_axis_mode` (str, default=`'dense'`): Режим оси времени (`dense` или `timeseries`).
- `xaxis_num_ticks` (int, default=16): Количество меток на оси X (для `dense` режима).

---

### Режим `comparison`

Сравнение нескольких зон, каждая в своем "слоте" для удобного сопоставления.

```python
fig = result.visualize(
    'comparison',
    max_zones=4,
    comparison_context=10, # Меньше контекста для сравнения
    show_indicators=True,
    time_axis_mode='dense',
    title="Comparison of 4 Zones"
)
```

**Ключевые параметры `comparison`:**
- `max_zones` (int, default=5): Максимальное количество зон для отображения.
- `date_range` (Tuple[datetime, datetime], optional): Диапазон дат для фильтрации зон.
- `comparison_context` (int, default=30): Количество баров до и после *каждой* зоны в режиме сравнения.
- `time_axis_mode` (str, default=`'dense'`): Режим оси времени.

---

### Режим `statistics`

Статистический анализ всех зон (распределения, типы и т.д.).

```python
fig = result.visualize('statistics', title='Zone Statistics')
```
**Внутри вызывает:** `ZoneVisualizer.plot_zones_analysis()`

---

## 💾 Экспорт графиков: `save_figure`

Вместо `fig.write_html()` или `fig.write_image()`, рекомендуется использовать универсальную функцию `save_figure` из `bquant.visualization.export`.

```python
from bquant.visualization.export import save_figure

# Создаем график
fig = result.visualize('overview', time_axis_mode='timeseries')

# Просто сохраняем
# Автоматически создаст папку и выберет формат
saved_path = save_figure(fig, "01_overview_timeseries")
print(f"Chart saved to: {saved_path}")

# Сохранение с кастомными параметрами
saved_path_png = save_figure(
    fig,
    "01_overview_custom",
    output_dir="output/my_charts",
    prefer='png',  # Предпочесть PNG, если возможно
    width=1600,
    height=900
)
```

**Преимущества `save_figure`:**
- **Умные пути**: Автоматически сохраняет в `output/vis/<имя_скрипта>/<имя_файла>`.
- **Надежный экспорт**: Пытается сохранить в `PNG` (если установлен `kaleido`), при ошибке автоматически переключается на `HTML`.
- **Простота**: Требует только фигуру и имя файла.

---

## 🏗️ Прямое использование `ZoneVisualizer`

Для полного контроля над процессом можно использовать класс `ZoneVisualizer` напрямую.

```python
from bquant.visualization import ZoneVisualizer

# 1. Инициализация
visualizer = ZoneVisualizer(backend='plotly')

# 2. Вызов методов с полными параметрами
fig_detail = visualizer.plot_zone_detail(
    price_data=result.data,
    zone=median_zone,
    context_bars=15,
    show_indicators=True,
    indicator_chart_types={'macd_hist': 'bar'}, # Явно задаем гистограмму
    time_axis_mode='dense',
    title="Detail from ZoneVisualizer"
)
fig_detail.show()
```

### Основные методы `ZoneVisualizer`

- `plot_zones_on_price_chart()`: Основа для режима `overview`.
- `plot_zone_detail()`: Основа для режима `detail`.
- `plot_zones_comparison()`: Основа для режима `comparison`.

Все эти методы принимают те же параметры, что и `result.visualize()`, но требуют явной передачи `price_data` и данных о зонах.

---

## 🔧 Convenience-функции

Для быстрых построений без создания `ZoneVisualizer` или `ZoneAnalysisResult`.

```python
from bquant.visualization import plot_zone_detail, plot_zones_comparison

# Детальный график
fig_detail = plot_zone_detail(result.data, median_zone, context_bars=10)

# График сравнения
fig_cmp = plot_zones_comparison(result.data, result.zones[:3], max_zones=3)
```
Эти функции являются обертками над методами `ZoneVisualizer`.

### Визуализация ZigZag индикатора: `plot_zigzag_verification`

Функция для построения графика ZigZag индикатора с swing-точками для визуальной проверки параметров стратегии. Полезно для отладки и верификации настроек swing-стратегии.

```python
from bquant.visualization import plot_zigzag_verification

# Простой вариант - только параметры
fig = plot_zigzag_verification(
    price_data=result.data,
    legs=10,
    deviation=0.05
)

# С swing_context для точных типов точек
fig = plot_zigzag_verification(
    price_data=result.data,
    legs=10,
    deviation=0.05,
    swing_context=result.zones[0].swing_context
)
```

**Параметры:**
- `price_data` (pd.DataFrame, **required**): DataFrame с OHLCV данными (должен содержать 'close', 'high', 'low').
- `legs` (int, **required**): Количество баров для подтверждения разворота (параметр ZigZag).
- `deviation` (float, **required**): Минимальное процентное отклонение (например, 0.05 = 5%).
- `swing_context` (SwingContext, optional): Опциональный SwingContext для точного определения типов точек (peaks/troughs).
- `title` (str, optional): Заголовок графика (по умолчанию генерируется автоматически).
- `height` (int, default=800): Высота графика в пикселях.
- `show_rangeslider` (bool, default=False): Показывать ползунок диапазона (range slider) под графиком для навигации по большим датасетам.
- `**kwargs`: Дополнительные параметры для Plotly figure (например, `width`).

**Возвращает:**
- `go.Figure` или `None` если Plotly недоступен.

**Что показывает график:**
- Свечной график (Candlestick) с ценой
- Маркеры swing-точек поверх графика:
  - 🔴 Красные треугольники вниз (peaks)
  - 🟢 Зеленые треугольники вверх (troughs)
- Опционально: ползунок диапазона (rangeslider) для навигации по большим датасетам

**Пример использования в скрипте:**

```python
# После анализа зон
result = (
    analyze_zones(df)
    .with_strategies(swing="zigzag")
    .with_auto_swing_thresholds(True)
    .analyze()
    .build()
)

# Получаем параметры из первой зоны
if result.zones:
    first_zone = result.zones[0]
    swing_context = first_zone.swing_context
    strategy_params = swing_context.strategy_params
    
    # Строим график для визуальной проверки
    fig_zigzag = plot_zigzag_verification(
        price_data=result.data,
        legs=strategy_params.get('legs', 10),
        deviation=strategy_params.get('deviation', 0.05),
        swing_context=swing_context,
        show_rangeslider=True  # Включаем ползунок для навигации по большому датасету
    )

    if fig_zigzag:
        save_figure(fig_zigzag, "zigzag_verification")
```

---

## 📖 Полный пример использования

Этот пример демонстрирует современный подход к визуализации, включая анализ, создание разных типов графиков и их сохранение.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones
from bquant.visualization.export import save_figure
from datetime import datetime

# 1. Загрузка данных и анализ
data = get_sample_data('tv_xauusd_1h')
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=3)
    .analyze(clustering=True)
    .build()
)
print(f"Обнаружено {len(result.zones)} зон.")

# 2. Создание и сохранение графика "overview" в режиме timeseries
print("Создание overview-графика в режиме timeseries...")
fig_overview = result.visualize(
    'overview',
    title="Обзор зон MACD (режим Timeseries)",
    show_indicators=True,
    time_axis_mode='timeseries' # Сохраняем пропорции времени
)
save_figure(fig_overview, "01_overview_timeseries_mode")

# 3. Детальный анализ одной зоны
# Находим зону с длительностью, близкой к медианной
median_duration = result.statistics['duration_distribution']['overall']['median']
median_zone = min(result.zones, key=lambda z: abs(z.features['duration'] - median_duration))

print(f"Создание детального графика для зоны #{median_zone.zone_id}...")
fig_detail = result.visualize(
    'detail',
    zone_id=median_zone.zone_id,
    context_bars=25,
    show_indicators=True,
    indicator_chart_types={'macd_hist': 'bar'}, # Явное указание типа графика
    time_axis_mode='dense', # Компактный вид
    xaxis_num_ticks=20,
    title=f"Детализация зоны #{median_zone.zone_id}"
)
save_figure(fig_detail, f"02_detail_zone_{median_zone.zone_id}")

# 4. Сравнение первых 4 зон
print("Создание графика для сравнения 4 зон...")
fig_comparison = result.visualize(
    'comparison',
    max_zones=4,
    comparison_context=5, # Небольшой контекст для сравнения
    show_indicators=True,
    title="Сравнение первых 4 зон"
)
save_figure(fig_comparison, "03_comparison_4_zones")

print("Все графики успешно созданы и сохранены в папку 'output/vis/'.")
```

---

## 🔗 Связанные разделы

- **[Zone Analysis](../analysis/zones.md)**: Документация по `ZoneAnalysisResult`.
- **[research/notebooks/04_zones_sample.py](../../../research/notebooks/04_zones_sample.py)**: Актуальный скрипт с полным покрытием всех интерфейсов.

---

## 📝 Changelog

- **v1.1** (2025-11-12):
  - ✨ **Новая функция `plot_zigzag_verification`**: Добавлена convenience-функция для визуализации ZigZag swing-точек на графике цены. Показывает candlestick-график с маркерами peaks/troughs для визуальной проверки параметров swing-стратегии.
  - ✨ **Параметр `show_rangeslider`**: Опциональный ползунок диапазона для навигации по большим датасетам (по умолчанию отключён для чистого отображения).
  - 📚 **Документация**: Добавлен раздел с описанием `plot_zigzag_verification` и примерами использования.

- **v1.0** (2025-11-11):
  - ✨ **Агрегированные метрики**: Новые параметры `show_aggregate_metrics` и `aggregate_metrics_mode` для отображения статистики по зонам.
  - ✨ **Визуализация свингов**: Параметр `show_swings` для отображения swing-точек (peaks/troughs) на графике.
  - ✨ **Метрики зон в detail режиме**: Параметры `show_zone_metrics` и `show_zone_stats` для детального просмотра.
  - 🐛 **Исправлена агрегация**: Теперь корректно обрабатывает несбалансированные свинги и использует правильные ключи (`avg_rally_pct`).
  - 📚 **Документация**: Добавлены разделы по агрегированным метрикам и фильтрации по `date_range`.

- **v0.0.1** (2025-11-05):
  - ✨ **Добавлен `time_axis_mode`**: Параметр для выбора между `dense` и `timeseries` режимами оси времени.
  - ✨ **Добавлен `xaxis_num_ticks`**: Параметр для контроля количества меток на оси X в `dense` режиме.
  - ✨ **Добавлен `indicator_chart_types`**: Позволяет явно задавать тип графика для индикаторов (`bar`/`line`).
  - ✨ **Добавлен `comparison_context`**: Специальный параметр контекста для режима `comparison`.
  - 📚 **Документация**: Полностью переработана для отражения новых возможностей и лучших практик.

- **v0.0.0** (2025-10-28):
  - 🎉 **Начальная реализация**: Добавлены `plot_zone_detail()`, `plot_zones_comparison()`.
  - 🎉 **Встроенная визуализация**: `ZoneAnalysisResult.visualize()`.
  - 🎉 **Поддержка Backends**: Plotly и Matplotlib.

