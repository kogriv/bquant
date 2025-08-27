# Visualization - Модули визуализации BQuant

## 📚 Обзор

Visualization модули предоставляют инструменты для создания финансовых графиков, визуализации зон, статистических графиков и настройки тем.

## 🗂️ Модули

### 📊 [bquant.visualization.charts](charts.md) - Финансовые графики
- **FinancialCharts** - Создание финансовых графиков
- **create_candlestick_chart()** - Candlestick график
- **create_ohlc_chart()** - OHLC график
- **create_line_chart()** - Линейный график

### 🎯 [bquant.visualization.zones](zones.md) - Визуализация зон
- **ZoneVisualizer** - Визуализация зон
- **plot_macd_with_zones()** - MACD с зонами
- **highlight_zones()** - Подсветка зон
- **ZoneChart** - График зон

### 📈 [bquant.visualization.statistical](statistical.md) - Статистические графики
- **StatisticalPlots** - Статистические графики
- **plot_correlation_matrix()** - Матрица корреляции
- **plot_distribution()** - Распределение данных
- **plot_hypothesis_results()** - Результаты гипотез

### 🎨 [bquant.visualization.themes](themes.md) - Темы и стили
- **ChartThemes** - Темы графиков
- **set_theme()** - Установка темы
- **create_custom_theme()** - Создание кастомной темы
- **ThemeManager** - Управление темами

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
    data['close'],
    title="XAUUSD 1H - Close Price",
    theme='blue'
)

# Показ графиков
candlestick_fig.show()
ohlc_fig.show()
line_fig.show()
```

### Визуализация зон MACD

```python
from bquant.visualization import ZoneVisualizer
from bquant.indicators import MACDZoneAnalyzer

# Анализ MACD
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)

# Создание визуализатора зон
zone_viz = ZoneVisualizer()

# MACD с зонами
macd_fig = zone_viz.plot_macd_with_zones(
    data,
    result.zones,
    title="XAUUSD 1H - MACD with Zones",
    show_statistics=True,
    theme='dark'
)

# Подсветка зон на ценовом графике
price_fig = zone_viz.highlight_zones(
    data,
    result.zones,
    title="XAUUSD 1H - Price with Zones",
    zone_colors={'bull': 'green', 'bear': 'red'},
    theme='light'
)

# График статистики зон
stats_fig = zone_viz.plot_zone_statistics(
    result.zones,
    title="Zone Statistics",
    theme='blue'
)

# Показ графиков
macd_fig.show()
price_fig.show()
stats_fig.show()
```

### Статистические графики

```python
from bquant.visualization import StatisticalPlots
from bquant.analysis.statistical import run_all_hypothesis_tests

# Статистический анализ
zones_info = {
    'zones_features': [zone.features for zone in result.zones if zone.features],
    'zones': result.zones,
    'statistics': result.statistics
}
hypothesis_results = run_all_hypothesis_tests(zones_info)

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

# Результаты гипотезных тестов
hypothesis_fig = stat_plots.plot_hypothesis_results(
    hypothesis_results,
    title="Hypothesis Test Results",
    theme='dark'
)

# Box plot для сравнения зон
box_fig = stat_plots.plot_box_plot(
    data=[bull_volatility, bear_volatility],
    labels=['Bull Zones', 'Bear Zones'],
    title="Volatility Comparison",
    theme='light'
)

# Показ графиков
corr_fig.show()
dist_fig.show()
hypothesis_fig.show()
box_fig.show()
```

### Настройка тем

```python
from bquant.visualization import ChartThemes

# Создание менеджера тем
themes = ChartThemes()

# Получение доступных тем
available_themes = themes.get_available_themes()
print(f"Available themes: {available_themes}")

# Установка темы
themes.set_theme('dark')

# Создание кастомной темы
custom_theme = themes.create_custom_theme(
    name='my_theme',
    colors={
        'primary': '#1f77b4',
        'secondary': '#ff7f0e',
        'background': '#f8f9fa',
        'text': '#2c3e50'
    },
    font_family='Arial',
    font_size=12
)

# Применение темы
themes.apply_theme('my_theme')

# Создание графика с кастомной темой
fig = charts.create_candlestick_chart(
    data,
    title="Custom Theme Chart",
    theme='my_theme'
)
fig.show()
```

### Комбинированная визуализация

```python
from bquant.visualization import FinancialCharts, ZoneVisualizer, StatisticalPlots

# Создание комплексной визуализации
def create_comprehensive_analysis(data, zones, hypothesis_results):
    """Создание комплексной визуализации анализа"""
    
    charts = FinancialCharts()
    zone_viz = ZoneVisualizer()
    stat_plots = StatisticalPlots()
    
    # 1. Ценовой график с зонами
    price_fig = zone_viz.highlight_zones(
        data, zones,
        title="Price Analysis with MACD Zones",
        theme='dark'
    )
    
    # 2. MACD с зонами
    macd_fig = zone_viz.plot_macd_with_zones(
        data, zones,
        title="MACD Analysis with Zones",
        theme='dark'
    )
    
    # 3. Статистика зон
    zone_stats_fig = zone_viz.plot_zone_statistics(
        zones,
        title="Zone Statistics",
        theme='blue'
    )
    
    # 4. Результаты гипотезных тестов
    hypothesis_fig = stat_plots.plot_hypothesis_results(
        hypothesis_results,
        title="Statistical Test Results",
        theme='dark'
    )
    
    return {
        'price_chart': price_fig,
        'macd_chart': macd_fig,
        'zone_stats': zone_stats_fig,
        'hypothesis_results': hypothesis_fig
    }

# Создание комплексной визуализации
analysis_figures = create_comprehensive_analysis(data, result.zones, hypothesis_results)

# Показ всех графиков
for name, fig in analysis_figures.items():
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

# PDF
fig.write_image(f"{export_dir}/chart.pdf", width=1200, height=800)

# SVG (векторный)
fig.write_image(f"{export_dir}/chart.svg", width=1200, height=800)

print(f"Charts exported to {export_dir}/")
```

### Создание собственного графика

```python
from bquant.visualization.base import BaseChart
import plotly.graph_objects as go
import plotly.express as px

class CustomVolatilityChart(BaseChart):
    """Кастомный график волатильности"""
    
    def __init__(self, theme='default'):
        super().__init__(theme)
    
    def create_chart(self, data, window_size=20, title="Volatility Chart"):
        """Создание графика волатильности"""
        
        # Расчет волатильности
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=window_size).std()
        
        # Создание графика
        fig = go.Figure()
        
        # Добавление линии волатильности
        fig.add_trace(go.Scatter(
            x=data.index,
            y=volatility,
            mode='lines',
            name='Volatility',
            line=dict(color=self.theme.colors['primary'])
        ))
        
        # Настройка макета
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Volatility",
            template=self.theme.template,
            height=600
        )
        
        return fig

# Использование кастомного графика
volatility_chart = CustomVolatilityChart(theme='dark')
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
- **[Indicators](../indicators/)** - Технические индикаторы
- **[Analysis](../analysis/)** - Аналитические модули

## 📖 Детальная документация

- **[Charts Module](charts.md)** - Подробная документация финансовых графиков
- **[Zones Module](zones.md)** - Документация визуализации зон
- **[Statistical Module](statistical.md)** - Документация статистических графиков
- **[Themes Module](themes.md)** - Документация тем и стилей

## 🚀 Руководство по расширению

### Создание нового типа графика

1. **Наследование от BaseChart**
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
