# `bquant.visualization` — графики

Три класса и несколько коротких функций поверх Plotly. Всё, что рисует пакет, —
финансовые графики цен, зоны на них и статистические разрезы — собирается этими
инструментами и возвращается объектом `plotly.graph_objects.Figure`: показать
(`fig.show()`), сохранить (`fig.write_html(...)`) или встроить его — уже дело
вызывающего.

| Модуль | Класс | О чём |
|---|---|---|
| `charts.py` | `FinancialCharts` | свечи, OHLC, линия, область, объёмы |
| [`zones.py`](zones.md) | `ZoneVisualizer` | зоны на цене, разбор одной зоны, сравнение, статистика зон |
| `statistical.py` | `StatisticalPlots` | гистограммы, распределения, корреляции, боксплоты, результаты гипотез |
| `themes.py` | `ChartThemes` | пять тем и применение их к готовой фигуре |

## Быстрый старт

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts

data = get_sample_data('tv_xauusd_1h')

charts = FinancialCharts()
figure = charts.create_candlestick_chart(data, title="XAUUSD 1H")

print(type(figure).__name__)
# Figure
```

Показать график — `figure.show()`; в примерах ниже вызов опущен, чтобы их можно было
прогонять без браузера.

## Финансовые графики

`FinancialCharts` — семь методов, все возвращают `Figure`:

| Метод | Что строит |
|---|---|
| `create_candlestick_chart(data, title, show_volume=True)` | свечи, при наличии `volume` — вторая панель |
| `create_ohlc_chart(data, title)` | OHLC-бары |
| `create_line_chart(data, title)` | линия по колонкам кадра |
| `create_area_chart(data, title)` | область |
| `plot_ohlcv(data, title)` | цена и объём вместе |
| `plot_macd_with_zones(macd_data, zones, ...)` | MACD с подсветкой зон |
| `plot_zones_over_indicator(data, zones, ...)` | зоны поверх произвольного осциллятора |

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts

data = get_sample_data('tv_xauusd_1h')
charts = FinancialCharts()

candles = charts.create_candlestick_chart(data, title="XAUUSD 1H", show_volume=True)
ohlc = charts.create_ohlc_chart(data, title="OHLC")
line = charts.create_line_chart(data[['close']], title="Close")

print(type(candles).__name__, type(ohlc).__name__, type(line).__name__)
# Figure Figure Figure
```

Параметр объёма называется `show_volume`, а не `volume`. Это существенно: лишние
именованные аргументы уходят в `**kwargs` и **молча отбрасываются**, поэтому опечатка
в имени параметра не вызовет ошибки — просто ничего не произойдёт. Реально читаются
девять ключей:

`width`, `height`, `title_font_size`, `show_volume`, `volume_ratio`,
`bullish_color`, `bearish_color`, `volume_color`, `background_color` —

и они же принимаются конструктором `FinancialCharts(...)` как умолчания на все
последующие графики.

### Короткие входы

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import create_financial_chart, create_statistical_plot

data = get_sample_data('tv_xauusd_1h')

figure = create_financial_chart('candlestick', data=data)
histogram = create_statistical_plot('histogram', data['close'])

print(type(figure).__name__, type(histogram).__name__)
# Figure Figure
```

`create_financial_chart` принимает `'candlestick'`, `'ohlc'`, `'line'`, `'area'`;
`create_statistical_plot` — `'histogram'`, `'scatter'`, `'correlation'`,
`'distribution'`. На неизвестном типе — `ValueError`, при недоступном модуле графиков —
`VisualizationError`.

**Форма данных у статистических типов разная:** гистограмме и распределению довольно
ряда, диаграмме рассеяния нужны кадр и `x_column`/`y_column`, матрице корреляций —
кадр из числовых колонок.

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import create_statistical_plot

data = get_sample_data('tv_xauusd_1h')

scatter = create_statistical_plot('scatter', data, x_column='open', y_column='close')
corr = create_statistical_plot('correlation', data[['open', 'high', 'low', 'close']])

print(type(scatter).__name__, type(corr).__name__)
# Figure Figure
```

## Зоны

Готовый результат пайплайна умеет рисовать себя сам — четыре режима:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True)
    .build()
)

overview = result.visualize('overview')
detail = result.visualize('detail', zone_id=result.zones[0].zone_id)
comparison = result.visualize('comparison', max_zones=5)
statistics = result.visualize('statistics')

print(type(overview).__name__, len(result.zones))
```

Тот же результат через `ZoneVisualizer` напрямую — когда нужны параметры, которых
`visualize()` не предлагает:

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.visualization import ZoneVisualizer

data = get_sample_data('tv_xauusd_1h')
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=False)
    .build()
)

visualizer = ZoneVisualizer()
figure = visualizer.plot_zone_detail(
    result.data, result.zones[0], context_bars=15, show_indicators=True
)
print(type(figure).__name__)
# Figure
```

**Передавайте `result.data`, а не исходный `data`.** Индикаторы вычисляет пайплайн, и
живут они в `result.data`; в исходном кадре их нет, поэтому `show_indicators=True` там
рисовать нечего.

Подробности всех методов, ролей колонок и разбор одной зоны — [zones.md](zones.md).

## Темы

Пять тем: `bquant_light` (текущая по умолчанию), `bquant_dark`, `financial`, `minimal`,
`professional`.

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts, get_available_themes

data = get_sample_data('tv_xauusd_1h')

print(get_available_themes())
# ['bquant_light', 'bquant_dark', 'financial', 'minimal', 'professional']

charts = FinancialCharts()
dark = charts.create_candlestick_chart(data, title="XAUUSD", theme='bquant_dark')
print(type(dark).__name__)
# Figure
```

Тему можно задать вызову (`theme=`) или объекту (`FinancialCharts(theme='bquant_dark')`,
`ZoneVisualizer(theme=...)`, `StatisticalPlots(theme=...)`); аргумент вызова
сильнее. **Без явного `theme=` тема не применяется** — фигура выходит с оформлением
Plotly по умолчанию.

Имя темы проверяется. Несуществующее — отказ с перечнем настоящих:

```python
from bquant.visualization import FinancialCharts
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

try:
    FinancialCharts().create_candlestick_chart(data, theme='dark')
except ValueError as error:
    print(error)
# Unknown theme: 'dark'. Available: ['bquant_dark', 'bquant_light', 'financial', 'minimal', 'professional']
```

> До сентября 2026 `theme=` принимали три класса и не применял ни один: светлая и
> тёмная давали побайтно одинаковую фигуру, а `'dark'`, `'light'`, `'blue'` —
> несуществующие имена — выглядели как настоящие темы. Разбор:
> `devref/gaps/core/g47_the_theme_was_accepted_and_ignored_2026-09.md`.

Своя тема и применение к уже готовой фигуре:

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts
from bquant.visualization.themes import apply_theme_to_figure, create_custom_theme

data = get_sample_data('tv_xauusd_1h')

create_custom_theme(
    name='my_theme',
    colors={
        'background': '#f8f9fa',
        'paper': '#ffffff',
        'text': '#2c3e50',
        'grid': '#d1d5db',
        'bullish': '#1f77b4',
        'bearish': '#ff7f0e',
        'volume': '#2c3e50',
    },
)

figure = FinancialCharts().create_candlestick_chart(data, title="Custom")
figure = apply_theme_to_figure(figure, 'my_theme')
print(type(figure).__name__)
# Figure
```

Прочее из `bquant.visualization.themes`: `apply_theme(name)` делает тему текущей для
последующих графиков (возвращает `bool`), `get_theme_colors(name)` отдаёт палитру,
`list_theme_info()` печатает перечень для человека, `reset_theme()` возвращает
умолчание.

## Статистические графики

```python
from bquant.data.samples import get_sample_data
from bquant.visualization import StatisticalPlots

data = get_sample_data('tv_xauusd_1h')
plots = StatisticalPlots()

correlation = plots.plot_correlation_matrix(data[['open', 'high', 'low', 'close']])
distribution = plots.plot_distribution(data['close'], plot_type='histogram')

print(type(correlation).__name__, type(distribution).__name__)
# Figure Figure
```

Есть и `create_*`-версии тех же графиков (`create_histogram`, `create_scatter_plot`,
`create_correlation_matrix`, `create_distribution_plot`, `create_box_plot`,
`create_time_series_plot`), и `plot_hypothesis_results(results)` для вывода
статистических тестов пайплайна — они лежат в `result.hypothesis_tests`.

## Готовность окружения

```python
from bquant.visualization import check_visualization_dependencies, get_visualization_info

print(check_visualization_dependencies())
# True

print(sorted(get_visualization_info()))
# ['available_libraries', 'dependencies_met', 'modules_loaded', 'version']
```

`check_visualization_dependencies()` — для скриптов, которые должны деградировать до
текста, а не падать на середине. `print_visualization_status()` печатает то же самое
для человека.

## Свой тип графика

Наследуйте `ChartBuilder`: он даёт `self.backend`, `validate_data()`,
`_prepare_datetime_index()` и `self.theme_manager`.

```python
import plotly.graph_objects as go

from bquant.data.samples import get_sample_data
from bquant.visualization.charts import ChartBuilder, themed


class VolatilityChart(ChartBuilder):
    """График скользящей волатильности."""

    @themed
    def create_chart(self, data, window=20, title="Volatility"):
        self.validate_data(data, ['close'])
        data = self._prepare_datetime_index(data.copy())

        volatility = data['close'].pct_change().rolling(window=window).std()

        figure = go.Figure()
        figure.add_trace(go.Scatter(x=data.index, y=volatility, mode='lines', name='Volatility'))
        figure.update_layout(title=title, xaxis_title="Date", yaxis_title="Volatility")
        return figure


chart = VolatilityChart().create_chart(get_sample_data('tv_xauusd_1h'), theme='bquant_dark')
print(type(chart).__name__)
# Figure
```

Декоратор `@themed` — то, чем тема применяется к готовой фигуре; без него параметр
`theme=` у вашего метода будет принят и проигнорирован.

## Дальше

| | |
|---|---|
| [Зоны на графиках](zones.md) | `ZoneVisualizer` целиком, роли колонок, разбор зоны |
| [Пайплайн зон](../analysis/pipeline.md) | откуда берётся `result` |
| [Индикаторы](../indicators/README.md) | что рисовать поверх цены |
