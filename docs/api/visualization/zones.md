# Zone Visualization - Визуализация зон

## 📚 Обзор

Модуль `bquant.visualization.zones` предоставляет комплексные инструменты для визуализации торговых зон, обнаруженных с помощью [Universal Zone Analysis Pipeline](../analysis/zones.md). Поддерживает два backend'а визуализации — Plotly (интерактивный) и Matplotlib (статический) — с автоматическим fallback при недоступности библиотек.

**Ключевые возможности:**
- 🎯 **Встроенная визуализация** - прямой вызов из `ZoneAnalysisResult.visualize()`
- 📊 **4 режима визуализации** - overview, detail, comparison, statistics
- 🔄 **Автоопределение индикаторов** - из метаданных зон
- 🎨 **Plotly/Matplotlib backends** - с автоматическим переключением
- 📈 **Контекстные бары** - настраиваемое окно вокруг зон
- 📅 **Фильтрация по датам** - выбор зон для сравнения
- 💾 **Экспорт HTML/PNG** - сохранение графиков

---

## 🏗️ Класс ZoneVisualizer

### Инициализация

```python
from bquant.visualization import ZoneVisualizer

visualizer = ZoneVisualizer(backend='plotly', config=None)
```

**Параметры:**
- `backend` (str, optional): Backend визуализации — `'plotly'` (default) или `'matplotlib'`
  - При недоступности выбранного backend автоматически переключается на доступный
  - Если оба недоступны, выбрасывает `AnalysisError`
- `config` (dict, optional): Кастомная конфигурация визуализации
  - `width` (int): Ширина графика в пикселях (default: 1400)
  - `height` (int): Высота графика в пикселях (default: 800)
  - `opacity` (float): Прозрачность зон (0.0-1.0, default: 0.3)
  - `show_zone_labels` (bool): Показывать метки зон (default: True)
  - `show_zone_stats` (bool): Показывать статистику зон (default: True)
  - `volume_panel_height` (float): Высота панели volume (0.0-1.0, default: 0.2)
  - `indicator_palette` (list): Цветовая палитра для индикаторов

**Цветовая схема зон:**
- **Bull zones**: `rgba(0, 255, 136, 0.3)` / `#00ff88`
- **Bear zones**: `rgba(255, 68, 68, 0.3)` / `#ff4444`
- **Support zones**: `rgba(0, 136, 255, 0.3)` / `#0088ff`
- **Resistance zones**: `rgba(255, 136, 0, 0.3)` / `#ff8800`

---

## 📊 Методы визуализации

### 1. plot_zones_on_price_chart()

Отображает все зоны поверх графика цены — базовый режим "overview".

```python
fig = visualizer.plot_zones_on_price_chart(
    price_data,
    zones_data,
    title="Price Chart with Zones",
    **kwargs
)
```

**Параметры:**
- `price_data` (pd.DataFrame): OHLCV данные (columns: open, high, low, close, volume)
- `zones_data` (List[Dict] | pd.DataFrame | List[ZoneInfo]): Список зон
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

**Пример:**
```python
from bquant.visualization import ZoneVisualizer
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')
result = analyze_zones(data).with_indicator('macd').detect_zones('zero_crossing').build()

visualizer = ZoneVisualizer(backend='plotly')
fig = visualizer.plot_zones_on_price_chart(data, result.zones, title='MACD Zones Overview')
fig.show()
```

---

### 2. plot_zone_detail()

Детальная визуализация **одной зоны** с контекстом (цена + индикаторы + volume).

```python
fig = visualizer.plot_zone_detail(
    price_data,
    zone,
    context_bars=20,
    max_bars=None,
    show_indicators=True,
    indicator_columns=None,
    show_volume=True,
    title="Zone Detail",
    **kwargs
)
```

**Параметры:**
- `price_data` (pd.DataFrame): OHLCV данные
- `zone` (Dict | ZoneInfo): Зона для детального просмотра
- `context_bars` (int, default=20): Количество баров до/после зоны для контекста
- `max_bars` (int, optional): Максимальное количество баров (truncate если больше)
- `show_indicators` (bool, default=True): Показывать индикаторы на графике
- `indicator_columns` (List[str], optional): Список индикаторных колонок для отображения
  - Если `None`, автоматически определяются из `zone.indicator_context` и `zone.features`
- `show_volume` (bool, default=True): Показывать панель volume (если доступен)
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Автоопределение индикаторов:**
Метод ищет индикаторы в следующих местах (в порядке приоритета):
1. `zone.indicator_context['detection_indicator']`
2. `zone.indicator_context['signal_line']`
3. `zone.indicator_context['indicator_columns']`
4. `zone.features['primary_indicator']`
5. `zone.features['secondary_indicator']`
6. `zone.features['indicators']`
7. Автоматически первые 2 non-price числовых колонки из `price_data`

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

**Пример:**
```python
# Отобразить зону с ID=5 с широким контекстом
zone = next((z for z in result.zones if z.zone_id == 5), None)
fig = visualizer.plot_zone_detail(
    data, zone,
    context_bars=30,
    show_indicators=True,
    title=f'Detail: Zone #{zone.zone_id}'
)
fig.show()

# Явно указать индикаторы для отображения
fig = visualizer.plot_zone_detail(
    data, zone,
    context_bars=15,
    indicator_columns=['macd_hist', 'macd_signal'],
    title='Zone Detail with Custom Indicators'
)
fig.show()
```

---

### 3. plot_zones_comparison()

Сравнение **нескольких зон** на едином графике цены.

```python
fig = visualizer.plot_zones_comparison(
    price_data,
    zones_data,
    max_zones=5,
    date_range=None,
    title="Zones Comparison",
    **kwargs
)
```

**Параметры:**
- `price_data` (pd.DataFrame): OHLCV данные
- `zones_data` (List[Dict] | pd.DataFrame | List[ZoneInfo]): Список зон для сравнения
- `max_zones` (int, default=5): Максимальное количество зон для отображения
  - При превышении выводится WARNING и берутся первые N зон
- `date_range` (Tuple[datetime, datetime], optional): Диапазон дат для фильтрации зон
  - Формат: `(start_date, end_date)`
  - Зоны вне диапазона отфильтровываются
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

**Пример:**
```python
# Сравнить первые 4 зоны
fig = visualizer.plot_zones_comparison(
    data, result.zones,
    max_zones=4,
    title='Top 4 Zones Comparison'
)
fig.show()

# Сравнить зоны в диапазоне дат
from datetime import datetime
fig = visualizer.plot_zones_comparison(
    data, result.zones,
    date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1)),
    max_zones=5,
    title='Q1 2024 Zones'
)
fig.show()
```

---

### 4. plot_macd_zones()

Специализированная визуализация MACD с зонами (2 панели: MACD линии + гистограмма).

```python
fig = visualizer.plot_macd_zones(
    macd_data,
    zones_data,
    title="MACD with Zones",
    **kwargs
)
```

**Параметры:**
- `macd_data` (pd.DataFrame): DataFrame с колонками `macd`, `macd_signal`, `macd_hist`
- `zones_data` (List[Dict] | pd.DataFrame): Зоны с `start_time`/`end_time`
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

---

### 5. plot_zones_analysis()

Статистический анализ зон: распределение типов, длительности, доходности, временная линия.

```python
fig = visualizer.plot_zones_analysis(
    zones_data,
    analysis_data=None,
    title="Zones Analysis",
    **kwargs
)
```

**Параметры:**
- `zones_data` (List[Dict] | pd.DataFrame): Зоны для анализа
- `analysis_data` (Dict[str, Any], optional): Дополнительные данные анализа
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Подграфики:**
1. **Pie chart** - распределение по типам зон (bull/bear)
2. **Histogram** - распределение длительности
3. **Histogram** - распределение доходности (`price_return`)
4. **Scatter plot** - временная линия зон (start_time vs duration)

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

---

### 6. plot_zones_distribution()

Распределение характеристик зон (общее + по типам).

```python
fig = visualizer.plot_zones_distribution(
    zones_data,
    feature='duration',
    title="Zones Distribution",
    **kwargs
)
```

**Параметры:**
- `zones_data` (List[Dict] | pd.DataFrame): Зоны для анализа
- `feature` (str, default='duration'): Характеристика для распределения
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

---

### 7. plot_zones_correlation()

Матрица корреляций характеристик зон (heatmap).

```python
fig = visualizer.plot_zones_correlation(
    zones_data,
    title="Zones Characteristics Correlation",
    **kwargs
)
```

**Параметры:**
- `zones_data` (List[Dict] | pd.DataFrame): Зоны для анализа корреляций
- `title` (str): Заголовок графика
- `**kwargs`: Дополнительные параметры backend'а

**Возвращает:** `plotly.graph_objects.Figure` или `matplotlib.pyplot.Figure`

---

## 🎯 Встроенная визуализация из ZoneAnalysisResult

Самый удобный способ визуализации — прямой вызов из результата анализа:

```python
from bquant.analysis.zones import analyze_zones

result = analyze_zones(data).with_indicator('macd').detect_zones('zero_crossing').build()

# 4 режима визуализации через единый интерфейс
fig = result.visualize('overview', title='Zones Overview')
fig = result.visualize('detail', zone_id=5, context_bars=25)
fig = result.visualize('comparison', max_zones=4, date_range=(start, end))
fig = result.visualize('statistics', title='Zone Statistics')
```

### Режимы визуализации

#### 1. overview

Общий обзор всех зон на графике цены.

```python
fig = result.visualize(
    'overview',
    backend='plotly',  # или 'matplotlib'
    title='Zones Overview',
    **kwargs
)
```

**Внутри вызывает:** `ZoneVisualizer.plot_zones_on_price_chart()`

---

#### 2. detail

Детальный просмотр одной зоны с контекстом.

```python
fig = result.visualize(
    'detail',
    zone_id=5,          # ID зоны (обязательно)
    context_bars=20,    # контекст до/после зоны
    show_indicators=True,
    backend='plotly',
    title='Zone Detail',
    **kwargs
)
```

**Параметры:**
- `zone_id` (int, **required**): ID зоны для детального просмотра
- `context_bars` (int, default=20): Контекстные бары
- `show_indicators` (bool, default=True): Показывать индикаторы
- `show_volume` (bool, default=True): Показывать volume
- `**kwargs`: Прокидываются в `plot_zone_detail()`

**Внутри вызывает:** `ZoneVisualizer.plot_zone_detail()`

**Пример:**
```python
# Найти зону с максимальной длительностью
longest_zone = max(result.zones, key=lambda z: z.duration)
fig = result.visualize('detail', zone_id=longest_zone.zone_id, context_bars=30)
fig.show()
```

---

#### 3. comparison

Сравнение нескольких зон на едином графике.

```python
fig = result.visualize(
    'comparison',
    max_zones=5,
    date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1)),
    backend='plotly',
    title='Zones Comparison',
    **kwargs
)
```

**Параметры:**
- `max_zones` (int, default=5): Максимальное количество зон
- `date_range` (Tuple[datetime, datetime], optional): Диапазон дат для фильтрации
- `**kwargs`: Прокидываются в `plot_zones_comparison()`

**Внутри вызывает:** `ZoneVisualizer.plot_zones_comparison()`

---

#### 4. statistics

Статистический анализ всех зон.

```python
fig = result.visualize(
    'statistics',
    backend='plotly',
    title='Zone Statistics',
    **kwargs
)
```

**Внутри вызывает:** `ZoneVisualizer.plot_zones_analysis()`

---

## 🔧 Convenience функции

Модуль экспортирует удобные функции для быстрого доступа без создания `ZoneVisualizer`:

### plot_zone_detail()

```python
from bquant.visualization import plot_zone_detail

fig = plot_zone_detail(
    price_data, zone,
    context_bars=20,
    backend='plotly',
    title='Zone Detail',
    **kwargs
)
```

Эквивалентно:
```python
visualizer = ZoneVisualizer(backend='plotly')
fig = visualizer.plot_zone_detail(price_data, zone, context_bars=20, title='Zone Detail', **kwargs)
```

---

### plot_zones_comparison()

```python
from bquant.visualization import plot_zones_comparison

fig = plot_zones_comparison(
    price_data, zones,
    max_zones=5,
    date_range=None,
    backend='plotly',
    title='Zones Comparison',
    **kwargs
)
```

Эквивалентно:
```python
visualizer = ZoneVisualizer(backend='plotly')
fig = visualizer.plot_zones_comparison(price_data, zones, max_zones=5, title='Zones Comparison', **kwargs)
```

---

### plot_zones_on_chart()

```python
from bquant.visualization import plot_zones_on_chart

fig = plot_zones_on_chart(price_data, zones, backend='plotly', title='Price with Zones')
```

Быстрая визуализация зон на графике цены.

---

## 🎨 Backend Configuration

### Выбор backend'а

**3 способа указать backend:**

#### 1. При создании ZoneVisualizer
```python
visualizer = ZoneVisualizer(backend='matplotlib')
fig = visualizer.plot_zone_detail(data, zone)
```

#### 2. Через result.visualize()
```python
fig = result.visualize('overview', backend='matplotlib')
```

#### 3. Через convenience функции
```python
fig = plot_zone_detail(data, zone, backend='matplotlib')
```

### Автоматический fallback

Если выбранный backend недоступен, происходит автоматическое переключение:

```python
# Plotly недоступен → переключается на Matplotlib
visualizer = ZoneVisualizer(backend='plotly')
# WARNING: Plotly not available, switching to matplotlib

# Оба недоступны → AnalysisError
# AnalysisError: No visualization libraries available
```

### Определение доступности

```python
from bquant.visualization import get_available_libraries

libs = get_available_libraries()
print(libs)
# {'plotly': True, 'matplotlib': True, 'data': True}
```

---

## 📏 Размер фигуры в Jupyter (Plotly)

В Jupyter/Notebook Plotly по умолчанию рендерит фигуры «резиново» (full width). Чтобы задать фиксированный размер:

```python
fig = result.visualize('detail', zone_id=5, context_bars=5, backend='plotly')
fig = fig.update_layout(width=800, height=400, autosize=False)
fig.show(config={'responsive': False})
```

Альтернатива — вывод через фиксированный HTML‑контейнер:

```python
from IPython.display import HTML
HTML(f"<div style='width:800px'>" + fig.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': False}) + "</div>")
```

Для Matplotlib используйте:

```python
fig = result.visualize('detail', zone_id=5, backend='matplotlib')
fig.set_size_inches(12, 6)
```

---

## 💾 Экспорт графиков

### HTML (Plotly)

Plotly по умолчанию экспортирует в HTML:

```python
fig = result.visualize('overview', backend='plotly')
fig.write_html('zone_overview.html')
```

### PNG (Plotly с kaleido)

Для экспорта Plotly в PNG требуется библиотека `kaleido`:

```bash
pip install kaleido
```

```python
fig = result.visualize('overview', backend='plotly')
try:
    fig.write_image('zone_overview.png', width=1400, height=800)
except Exception as e:
    print(f"PNG export failed (kaleido not available?): {e}")
    fig.write_html('zone_overview.html')  # fallback to HTML
```

### PNG (Matplotlib)

Matplotlib экспортирует в PNG нативно:

```python
fig = result.visualize('overview', backend='matplotlib')
fig.savefig('zone_overview.png', dpi=150, bbox_inches='tight')
```

### Универсальная функция сохранения (пакет)

Рекомендуется использовать встроенную утилиту:

```python
from bquant.visualization.export import save_figure

fig = result.visualize('overview', backend='plotly')
# Достаточно имени — всё остальное по умолчанию:
# - Папка: ./outputs/vis/<имя_скрипта>/
# - Формат: PNG для Plotly (если нет kaleido → HTML fallback), PNG для Matplotlib
# - Размеры: 1400x900 (Plotly), dpi=150 (Matplotlib)
save_figure(fig, '01_overview')

# При необходимости можно переопределить
save_figure(
    fig,
    '01_overview',
    output_dir='exports/visualization/',
    prefer='html',  # или 'png'
    width=1200,
    height=700,
    dpi=200,
)
```

---

## 📖 Полный пример использования

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones
from bquant.visualization import ZoneVisualizer, plot_zone_detail, plot_zones_comparison
from datetime import datetime

# 1. Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# 2. Universal Pipeline анализ
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=3)
    .analyze(clustering=True)
    .build()
)

print(f"Detected {len(result.zones)} zones")

# 3. Встроенная визуализация (самый простой способ)
fig_overview = result.visualize('overview', title='MACD Zones Overview')
fig_overview.show()

# Найти зону с медианной длительностью
median_duration = result.statistics['duration_distribution']['overall']['median']
median_zone = min(result.zones, key=lambda z: abs(z.duration - median_duration))

fig_detail = result.visualize('detail', zone_id=median_zone.zone_id, context_bars=25)
fig_detail.show()

fig_comparison = result.visualize('comparison', max_zones=4, title='Top 4 Zones')
fig_comparison.show()

fig_stats = result.visualize('statistics', title='Zone Statistics')
fig_stats.show()

# 4. Прямое использование ZoneVisualizer
visualizer = ZoneVisualizer(backend='plotly')

# Детальная визуализация с кастомными параметрами
fig = visualizer.plot_zone_detail(
    data, median_zone,
    context_bars=30,
    show_indicators=True,
    indicator_columns=['macd_hist', 'macd_signal'],
    show_volume=True,
    title=f'Zone #{median_zone.zone_id} Detail (Custom)'
)
fig.show()

# Сравнение зон за Q1
fig = visualizer.plot_zones_comparison(
    data, result.zones,
    date_range=(datetime(2024, 1, 1), datetime(2024, 4, 1)),
    max_zones=5,
    title='Q1 2024 Zones Comparison'
)
fig.show()

# 5. Convenience функции
fig = plot_zone_detail(data, median_zone, context_bars=20, backend='plotly')
fig.show()

fig = plot_zones_comparison(data, result.zones, max_zones=3, backend='matplotlib')
fig.show()

# 6. Экспорт
fig_overview.write_html('exports/zone_overview.html')
try:
    fig_detail.write_image('exports/zone_detail.png', width=1400, height=800)
except:
    fig_detail.write_html('exports/zone_detail.html')
```

---

## 🔗 Связанные разделы

### API Documentation
- **[Zone Analysis](../analysis/zones.md)** - Universal Zone Analysis Pipeline и ZoneAnalysisResult
- **[Visualization Overview](README.md)** - Обзор модулей визуализации
- **[Statistical Plots](statistical.md)** - Статистические графики
- **[Chart Themes](themes.md)** - Темы и стилизация графиков

### User Guides
- **[Zone Analysis Guide](../../user_guide/zone_analysis.md)** - Пользовательское руководство по анализу зон
- **[Quick Start](../../user_guide/quick_start.md)** - Быстрый старт с BQuant

### Tutorials
- **[MACD Basic Pipeline](../../tutorials/macd_basic_pipeline.md)** - Пошаговый туториал с примерами визуализации
- **[Combined Rules Detection](../../tutorials/combined_rules_detection.md)** - Комбинированные правила детекции

### Examples
- **[examples/09_zones_visualization_demo.py](../../../examples/09_zones_visualization_demo.py)** - Полнофункциональный пример всех режимов визуализации
- **[research/notebooks/04_zones_visualization_demo.py](../../../research/notebooks/04_zones_visualization_demo.py)** - Research ноутбук с полным покрытием интерфейсов

---

## ⚙️ Технические детали

### Требования
- **Python**: 3.8+
- **Обязательные**: `pandas`, `numpy`
- **Plotly backend**: `plotly>=5.0.0`
- **Matplotlib backend**: `matplotlib>=3.5.0`, `seaborn>=0.11.0`
- **PNG export (Plotly)**: `kaleido` (опционально)

### Производительность
- **Plotly**: Интерактивные графики (zoom, pan, hover), HTML ~500KB-2MB
- **Matplotlib**: Статичные графики, PNG ~100-500KB, быстрый рендеринг

### Ограничения
- **max_zones**: Рекомендуется ≤ 10 для сравнения (больше перегружает график)
- **context_bars**: Большие значения (>50) могут замедлить отрисовку
- **Plotly PNG**: Требует `kaleido`, иначе fallback на HTML

---

## 📝 Changelog

- **v0.0.0** (2025-10-28): Реализация Stage 4 (Visualization)
  - Добавлены методы `plot_zone_detail()`, `plot_zones_comparison()`
  - Встроенная визуализация из `ZoneAnalysisResult.visualize()`
  - Поддержка Plotly и Matplotlib backends
  - Автоопределение индикаторов из метаданных зон
  - Convenience функции для быстрого доступа

