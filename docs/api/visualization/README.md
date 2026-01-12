# Visualization - Модули визуализации BQuant

## 📚 Обзор

Visualization модули предоставляют инструменты для создания финансовых графиков, визуализации зон, статистических графиков и настройки тем с **Universal Pipeline v2.1** интеграцией.

> **✅ v2.1 - Modern Visualization Architecture**
> 
> **ZoneVisualizer Integration:** Встроенная визуализация из ZoneAnalysisResult
> 
> **Universal Pipeline Support:** Работает с любыми индикаторами
> 
> **Advanced Features:** Auto-detect indicators, context bars, date range filtering

## 🗂️ Модули

### 📊 bquant.visualization.charts - Финансовые графики
- **FinancialCharts** - Создание финансовых графиков
- **create_candlestick_chart()** - Candlestick график
- **create_ohlc_chart()** - OHLC график
- **create_line_chart()** - Линейный график

### 🎯 [bquant.visualization.zones](zones.md) - Universal Zone Visualization

📘 **[Подробная документация →](zones.md)**

**ZoneVisualizer - Core Class:**
- **plot_zones_on_price_chart()** - общий график цен с зонами
- **plot_zone_detail()** - детальный просмотр одной зоны
- **plot_zones_comparison()** - сравнение нескольких зон
- **plot_zones_analysis()** - статистический анализ зон

**ZoneAnalysisResult Integration:**
- **Встроенная визуализация** из результата Universal Pipeline
- **Auto-detect Indicators** - автоматическое определение индикаторов
- **Context Bars** - настраиваемый контекст вокруг зоны
- **Date Range Filtering** - фильтрация зон по диапазону дат

### 📈 bquant.visualization.statistical - Статистические графики
- **StatisticalPlots** - Статистические графики
- **plot_correlation_matrix()** - Матрица корреляции
- **plot_distribution()** - Распределение данных
- **plot_hypothesis_results()** - Результаты гипотез
- > **Примечание:** Модуль доступен в коде, детальная документация будет добавлена позже.

### 🎨 bquant.visualization.themes - Темы и стили
- **ChartThemes** - Темы графиков
- **set_theme()** - Установка темы
- **create_custom_theme()** - Создание кастомной темы
- **ThemeManager** - Управление темами
- > **Примечание:** Модуль доступен в коде, детальная документация будет добавлена позже.

## 🔍 Быстрый поиск

### По функциональности

#### Финансовые графики
- `FinancialCharts.create_candlestick_chart()` - Candlestick график
- `FinancialCharts.create_ohlc_chart()` - OHLC график
- `FinancialCharts.create_line_chart()` - Линейный график
- `FinancialCharts.create_area_chart()` - Площадной график

#### Визуализация зон
- `ZoneVisualizer.plot_macd_with_zones()` - MACD с зонами
- `ZoneVisualizer.highlight_zones()` - Подсветка зон
- `ZoneVisualizer.create_zone_chart()` - График зон
- `ZoneVisualizer.plot_zone_statistics()` - Статистика зон

#### Статистические графики
- `StatisticalPlots.plot_correlation_matrix()` - Матрица корреляции
- `StatisticalPlots.plot_distribution()` - Распределение
- `StatisticalPlots.plot_hypothesis_results()` - Результаты тестов
- `StatisticalPlots.plot_box_plot()` - Box plot

#### Темы и стили
- `ChartThemes.set_theme()` - Установка темы
- `ChartThemes.create_custom_theme()` - Кастомная тема
- `ChartThemes.get_available_themes()` - Доступные темы
- `ChartThemes.apply_theme()` - Применение темы

### По типу

#### 🏗️ Классы
- `FinancialCharts` - Финансовые графики
- `ZoneVisualizer` - Визуализация зон
- `StatisticalPlots` - Статистические графики
- `ChartThemes` - Темы графиков

#### 🔧 Функции
- `create_candlestick_chart()` - Candlestick график
- `plot_macd_with_zones()` - MACD с зонами
- `plot_correlation_matrix()` - Матрица корреляции
- `set_theme()` - Установка темы

#### 📋 Типы данных
- `ChartConfig` - Конфигурация графика
- `ThemeConfig` - Конфигурация темы
- `ZoneVisualizationConfig` - Конфигурация визуализации зон
- `StatisticalPlotConfig` - Конфигурация статистического графика

## 💡 Примеры использования

### Создание финансовых графиков

```python
from bquant.visualization import FinancialCharts
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# Создание финансовых графиков
charts = FinancialCharts()

# Candlestick график
candlestick_fig = charts.create_candlestick_chart(
    data,
    title="XAUUSD 1H - Candlestick Chart",
    volume=True,
    theme='dark'
)

# OHLC график
ohlc_fig = charts.create_ohlc_chart(
    data,
    title="XAUUSD 1H - OHLC Chart",
    theme='light'
)

# Линейный график
line_fig = charts.create_line_chart(
    data[['close']],
    title="XAUUSD 1H - Close Price",
    theme='blue'
)

# Показ графиков
candlestick_fig.show()
ohlc_fig.show()
line_fig.show()
```

### Universal Pipeline Visualization

```python
from bquant.analysis.zones import analyze_zones
from bquant.visualization import ZoneVisualizer

# Universal Pipeline анализ
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

# Встроенная визуализация из результата
fig = result.visualize('overview')  # Общий обзор
fig.show()

fig = result.visualize('detail', zone_id=result.zones[0].zone_id)  # Детальный просмотр
fig.show()

fig = result.visualize('comparison', max_zones=5)  # Сравнение
fig.show()

fig = result.visualize('statistics')  # Статистика
fig.show()
```

### Advanced Zone Visualization

```python
from bquant.visualization import ZoneVisualizer

# Создание визуализатора зон
zone_viz = ZoneVisualizer()

# Детальный просмотр зоны с индикаторами
fig = zone_viz.plot_zone_detail(
    data,
    result.zones[0],
    context_bars=15,
    show_indicators=True,
    title="Zone Detail Analysis"
)
fig.show()

# Сравнение зон по датам
from datetime import datetime
fig = zone_viz.plot_zones_comparison(
    data,
    result.zones,
    date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1)),
    max_zones=min(5, len(result.zones)),
    title="Zones Comparison"
)
fig.show()

# Прямое использование ZoneVisualizer
fig = zone_viz.plot_zones_on_price_chart(data, result.zones)
fig.show()
```

### Статистические графики (Universal Pipeline)

```python
from bquant.visualization import StatisticalPlots

# Universal Pipeline с автоматическими hypothesis tests
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)  # Автоматически включает hypothesis tests
    .build()
)

# Создание статистических графиков
stat_plots = StatisticalPlots()

# Матрица корреляции
corr_fig = stat_plots.plot_correlation_matrix(
    data[['open', 'high', 'low', 'close', 'volume']],
    title="Correlation Matrix",
    theme='heatmap'
)

# Распределение цен закрытия
dist_fig = stat_plots.plot_distribution(
    data['close'],
    title="Close Price Distribution",
    plot_type='histogram',
    theme='blue'
)

# Результаты гипотезных тестов из Universal Pipeline
if result.hypothesis_tests:
    hypothesis_fig = stat_plots.plot_hypothesis_results(
        result.hypothesis_tests.results,
        title="Hypothesis Test Results",
        theme='dark'
    )
    hypothesis_fig.show()

# Box plot для сравнения зон
bull_volatility = [zone.features.get('volatility_score', 0) for zone in result.zones
                  if zone.type == 'bull' and zone.features]
bear_volatility = [zone.features.get('volatility_score', 0) for zone in result.zones
                  if zone.type == 'bear' and zone.features]

box_fig = stat_plots.plot_box_plot(
    data=[bull_volatility, bear_volatility],
    labels=['Bull Zones', 'Bear Zones'],
    title="Volatility Comparison",
    theme='light'
)

# Показ графиков
corr_fig.show()
dist_fig.show()
box_fig.show()
```

### Настройка тем

```python
from bquant.visualization.themes import (
    ChartThemes,
    create_custom_theme,
    apply_theme,
    apply_theme_to_figure,
)

# Создание менеджера тем
themes = ChartThemes()

# Получение доступных тем
available_themes = themes.get_available_themes()
print(f"Available themes: {available_themes}")

# Установка базовой темы
apply_theme('bquant_dark')

# Создание кастомной темы
create_custom_theme(
    name='my_theme',
    colors={
        'background': '#f8f9fa',
        'paper': '#ffffff',
        'text': '#2c3e50',
        'grid': '#d1d5db',
        'bullish': '#1f77b4',
        'bearish': '#ff7f0e',
        'volume': '#2c3e50'
    },
    layout={
        'font_family': 'Arial',
        'font_size': 12,
        'title_font_size': 16,
        'show_legend': True
    }
)

# Активация кастомной темы
apply_theme('my_theme')

# Создание графика и применение темы
fig = charts.create_candlestick_chart(
    data,
    title="Custom Theme Chart"
)
fig = apply_theme_to_figure(fig, 'my_theme')
fig.show()
```

### Комбинированная визуализация (Universal Pipeline)

```python
from bquant.visualization import FinancialCharts, ZoneVisualizer, StatisticalPlots

# Universal Pipeline анализ
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

# Создание комплексной визуализации
def create_comprehensive_analysis(data, result):
    """Создание комплексной визуализации анализа с Universal Pipeline"""
    
    charts = FinancialCharts()
    zone_viz = ZoneVisualizer()
    stat_plots = StatisticalPlots()
    
    # 1. Ценовой график с зонами
    price_fig = zone_viz.plot_zones_on_price_chart(
        data, result.zones,
        title="Price Analysis with Universal Zones",
        theme='dark'
    )
    
    # 2. Детальный анализ зоны
    detail_fig = zone_viz.plot_zone_detail(
        data, result.zones[0],
        context_bars=20,
        title="Zone Detail Analysis",
        theme='dark'
    )
    
    # 3. Сравнение зон
    comparison_fig = zone_viz.plot_zones_comparison(
        data, result.zones,
        max_zones=min(5, len(result.zones)),
        title="Zones Comparison",
        theme='blue'
    )
    
    # 4. Результаты гипотезных тестов
    hypothesis_fig = None
    if result.hypothesis_tests:
        hypothesis_fig = stat_plots.plot_hypothesis_results(
            result.hypothesis_tests.results,
            title="Statistical Test Results",
            theme='dark'
        )
    
    return {
        'price_chart': price_fig,
        'detail_chart': detail_fig,
        'comparison_chart': comparison_fig,
        'hypothesis_results': hypothesis_fig
    }

# Создание комплексной визуализации
analysis_figures = create_comprehensive_analysis(data, result)

# Показ всех графиков
for name, fig in analysis_figures.items():
    if fig is not None:
        print(f"Showing {name}...")
        fig.show()
```

### Экспорт графиков

```python
import os
from bquant.visualization import FinancialCharts

# Создание графика
charts = FinancialCharts()
fig = charts.create_candlestick_chart(
    data,
    title="XAUUSD 1H Analysis",
    theme='dark'
)

# Экспорт в различные форматы
export_dir = 'exports'
os.makedirs(export_dir, exist_ok=True)

# PNG
fig.write_image(f"{export_dir}/chart.png", width=1200, height=800)

# HTML (интерактивный)
fig.write_html(f"{export_dir}/chart.html")

# JSON (для интеграции)
fig.write_json(f"{export_dir}/chart.json")

print(f"Charts exported to {export_dir}/")
```

### Создание собственного графика

```python
from bquant.visualization.charts import ChartBuilder
from bquant.visualization.themes import ChartThemes
import plotly.graph_objects as go

class CustomVolatilityChart(ChartBuilder):
    """Кастомный график волатильности"""

    def __init__(self, theme='bquant_dark'):
        super().__init__(backend='plotly')
        self.theme_manager = ChartThemes()
        self.theme_name = theme
        self.theme_config = self.theme_manager.get_theme(self.theme_name)

    def create_chart(self, data, window_size=20, title="Volatility Chart"):
        """Создание графика волатильности"""

        self.validate_data(data, ['close'])
        data = self._prepare_datetime_index(data.copy())

        # Расчет волатильности
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=window_size).std()

        colors = self.theme_config.get('colors', {})

        # Создание графика
        fig = go.Figure()

        # Добавление линии волатильности
        fig.add_trace(go.Scatter(
            x=data.index,
            y=volatility,
            mode='lines',
            name='Volatility',
            line=dict(color=colors.get('neutral', '#3498db'))
        ))

        # Настройка макета
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Volatility",
            height=600
        )

        return self.theme_manager.apply_theme_to_figure(fig, self.theme_name)

# Использование кастомного графика
volatility_chart = CustomVolatilityChart(theme='bquant_dark')
vol_fig = volatility_chart.create_chart(data, window_size=20)
vol_fig.show()
```

### Интерактивные элементы

```python
from bquant.visualization import FinancialCharts

# Создание интерактивного графика
charts = FinancialCharts()

fig = charts.create_candlestick_chart(
    data,
    title="Interactive XAUUSD Chart",
    theme='dark',
    interactive=True
)

# Добавление интерактивных элементов
fig.update_layout(
    hovermode='x unified',
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Добавление кнопок
fig.update_layout(
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            x=0.1,
            y=1.1,
            showactive=False,
            buttons=list([
                dict(label="1H",
                     method="relayout",
                     args=[{"xaxis.range": [data.index[-100], data.index[-1]]}]),
                dict(label="1D",
                     method="relayout",
                     args=[{"xaxis.range": [data.index[-24], data.index[-1]]}]),
                dict(label="1W",
                     method="relayout",
                     args=[{"xaxis.range": [data.index[-168], data.index[-1]]}]),
                dict(label="All",
                     method="relayout",
                     args=[{"xaxis.range": [data.index[0], data.index[-1]]}])
            ])
        )
    ]
)

fig.show()
```

## 🔗 Связанные разделы

- **[Core Modules](../core/)** - Базовые модули
- **[Data Modules](../data/)** - Модули данных
- **[Indicators](../indicators/README.md)** - Технические индикаторы
- **[Analysis](../analysis/README.md)** - Аналитические модули

## 📖 Детальная документация

- **[Universal Pipeline](../analysis/pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Zones Analysis](../analysis/zones.md)** - Детали работы с зонами и результатами анализа
- **[Strategies](../analysis/strategies.md)** - Настройка стратегий и анализ зон
- **[Core Logging](../core/logging.md)** - Настройка логирования и мониторинга выполнения
- **[Indicators README](../indicators/README.md)** - Работа с индикаторами и фабрикой

## 🚀 Руководство по расширению

### Создание нового типа графика

1. **Наследование от ChartBuilder**
2. **Реализация метода create_chart()**
3. **Настройка темы**
4. **Добавление интерактивности**

### Лучшие практики

- Используйте консистентные цвета и стили
- Добавляйте интерактивные элементы
- Оптимизируйте производительность для больших данных
- Поддерживайте различные форматы экспорта

---

**Следующий раздел:** [Core Modules](../core/) 🏗️
