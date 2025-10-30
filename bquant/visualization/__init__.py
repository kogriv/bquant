"""
Модуль визуализации BQuant

Предоставляет инструменты для создания интерактивных графиков и диаграмм:
- Финансовые графики (OHLCV, свечи, объемы)
- Визуализация технических индикаторов
- Отображение торговых зон
- Статистические диаграммы
- Настраиваемые темы оформления
"""

from typing import Any, Dict, List, Optional, Tuple, Union

from ..core.logging_config import get_logger

# Получаем логгер для модуля
logger = get_logger(__name__)

# Версия модуля визуализации
__version__ = "0.0.0"

# Проверяем доступность библиотек визуализации
_plotting_libraries = {}

try:
    import plotly.graph_objects as go
    import plotly.subplots as sp
    import plotly.express as px
    _plotting_libraries['plotly'] = True
    logger.debug("Plotly library available")
except ImportError:
    _plotting_libraries['plotly'] = False
    logger.warning(
        "Plotly library not available - interactive visualization features (zones detail/comparison) will be limited"
    )

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    _plotting_libraries['matplotlib'] = True
    logger.debug("Matplotlib/Seaborn libraries available")
except ImportError:
    _plotting_libraries['matplotlib'] = False
    logger.warning(
        "Matplotlib/Seaborn libraries not available - static visualization features (zones detail/comparison fallback) will be limited"
    )

try:
    import pandas as pd
    import numpy as np
    _plotting_libraries['data'] = True
except ImportError:
    _plotting_libraries['data'] = False
    logger.error("Pandas/Numpy not available - visualization module cannot function")


def get_available_libraries() -> Dict[str, bool]:
    """
    Получить информацию о доступных библиотеках визуализации.
    
    Returns:
        Словарь с информацией о доступности библиотек
    """
    return _plotting_libraries.copy()


def check_visualization_dependencies() -> bool:
    """
    Проверить наличие основных зависимостей для визуализации.
    
    Returns:
        True если основные зависимости доступны
    """
    return _plotting_libraries.get('data', False) and (
        _plotting_libraries.get('plotly', False) or 
        _plotting_libraries.get('matplotlib', False)
    )


# Импорт основных компонентов (с проверкой зависимостей)
if check_visualization_dependencies():
    try:
        from .charts import FinancialCharts, ChartBuilder
        _charts_available = True
        logger.debug("Charts module loaded successfully")
    except ImportError as e:
        logger.warning(f"Charts module not available: {e}")
        _charts_available = False
    
    try:
        from .zones import (
            ZoneVisualizer,
            ZoneChartBuilder,
            plot_zones_on_chart,
            plot_macd_zones_chart,
            analyze_zones_visually,
        )
        _zones_available = True
        logger.debug("Zones visualization module loaded successfully")
    except ImportError as e:
        logger.warning(f"Zones visualization module not available: {e}")
        _zones_available = False
    
    try:
        from .statistical import StatisticalPlots, DistributionPlotter
        _statistical_available = True
        logger.debug("Statistical plots module loaded successfully")
    except ImportError as e:
        logger.warning(f"Statistical plots module not available: {e}")
        _statistical_available = False
    
    try:
        from .themes import ChartThemes, get_theme, apply_theme
        _themes_available = True
        logger.debug("Themes module loaded successfully")
    except ImportError as e:
        logger.warning(f"Themes module not available: {e}")
        _themes_available = False

else:
    logger.error("Visualization dependencies not met - module functionality limited")
    _charts_available = False
    _zones_available = False
    _statistical_available = False
    _themes_available = False


class VisualizationError(Exception):
    """Исключение для ошибок визуализации."""
    pass


def create_financial_chart(chart_type: str = 'candlestick', **kwargs):
    """
    Создать финансовый график.
    
    Args:
        chart_type: Тип графика ('candlestick', 'ohlc', 'line', 'area')
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика или None если недоступно
    """
    if not _charts_available:
        raise VisualizationError("Charts module not available")
    
    charts = FinancialCharts()
    
    if chart_type == 'candlestick':
        return charts.create_candlestick_chart(**kwargs)
    elif chart_type == 'ohlc':
        return charts.create_ohlc_chart(**kwargs)
    elif chart_type == 'line':
        return charts.create_line_chart(**kwargs)
    elif chart_type == 'area':
        return charts.create_area_chart(**kwargs)
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")


def plot_zone_detail(price_data,
                     zone,
                     context_bars: int = 20,
                     title: str = "Zone Detail",
                     **kwargs):
    """Детализированный просмотр отдельной торговой зоны."""

    if not _zones_available:
        raise VisualizationError("Zones visualization module not available")

    visualizer = ZoneVisualizer()
    call_kwargs = dict(kwargs)
    effective_context = call_kwargs.pop('context_bars', context_bars)
    effective_title = call_kwargs.pop('title', title)

    return visualizer.plot_zone_detail(
        price_data,
        zone,
        context_bars=effective_context,
        title=effective_title,
        **call_kwargs,
    )


def plot_zones_comparison(price_data,
                          zones_data,
                          max_zones: int = 5,
                          date_range: Optional[Tuple[Any, Any]] = None,
                          title: str = "Zones Comparison",
                          **kwargs):
    """Сравнение нескольких торговых зон на едином графике."""

    if not _zones_available:
        raise VisualizationError("Zones visualization module not available")

    visualizer = ZoneVisualizer()
    call_kwargs = dict(kwargs)
    effective_max_zones = call_kwargs.pop('max_zones', max_zones)
    effective_date_range = call_kwargs.pop('date_range', date_range)
    effective_title = call_kwargs.pop('title', title)

    return visualizer.plot_zones_comparison(
        price_data,
        zones_data,
        max_zones=effective_max_zones,
        date_range=effective_date_range,
        title=effective_title,
        **call_kwargs,
    )


def plot_zones_analysis(zones_data, analysis_data=None, **kwargs):
    """
    Визуализация анализа зон.
    
    Args:
        zones_data: Данные зон
        analysis_data: Данные анализа (опционально)
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика или None если недоступно
    """
    if not _zones_available:
        raise VisualizationError("Zones visualization module not available")
    
    visualizer = ZoneVisualizer()
    return visualizer.plot_zones_analysis(zones_data, analysis_data, **kwargs)


def create_statistical_plot(plot_type: str, data, **kwargs):
    """
    Создать статистический график.
    
    Args:
        plot_type: Тип графика ('histogram', 'scatter', 'correlation', 'distribution')
        data: Данные для визуализации
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика или None если недоступно
    """
    if not _statistical_available:
        raise VisualizationError("Statistical plots module not available")
    
    plotter = StatisticalPlots()
    
    if plot_type == 'histogram':
        return plotter.create_histogram(data, **kwargs)
    elif plot_type == 'scatter':
        return plotter.create_scatter_plot(data, **kwargs)
    elif plot_type == 'correlation':
        return plotter.create_correlation_matrix(data, **kwargs)
    elif plot_type == 'distribution':
        return plotter.create_distribution_plot(data, **kwargs)
    else:
        raise ValueError(f"Unknown plot type: {plot_type}")


def get_available_themes() -> List[str]:
    """
    Получить список доступных тем оформления.
    
    Returns:
        Список названий тем
    """
    if not _themes_available:
        return ['default']
    
    from .themes import get_available_themes as themes_get_available
    return themes_get_available()


def set_default_theme(theme_name: str) -> bool:
    """
    Установить тему оформления по умолчанию.
    
    Args:
        theme_name: Название темы
    
    Returns:
        True если тема успешно установлена
    """
    if not _themes_available:
        logger.warning(f"Themes module not available, cannot set theme: {theme_name}")
        return False
    
    try:
        apply_theme(theme_name)
        logger.info(f"Default theme set to: {theme_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to set theme {theme_name}: {e}")
        return False


# Информационные функции
def get_visualization_info() -> Dict[str, Any]:
    """
    Получить информацию о модуле визуализации.
    
    Returns:
        Словарь с информацией о модуле
    """
    return {
        'version': __version__,
        'available_libraries': _plotting_libraries,
        'modules_loaded': {
            'charts': _charts_available,
            'zones': _zones_available,
            'statistical': _statistical_available,
            'themes': _themes_available
        },
        'dependencies_met': check_visualization_dependencies()
    }


def print_visualization_status():
    """Вывести статус модуля визуализации."""
    info = get_visualization_info()
    
    print(f"BQuant Visualization Module v{info['version']}")
    print("=" * 50)
    
    print("\nLibrary Dependencies:")
    for lib, available in info['available_libraries'].items():
        status = "✓" if available else "✗"
        print(f"  {status} {lib}")
    
    print("\nLoaded Modules:")
    for module, loaded in info['modules_loaded'].items():
        status = "✓" if loaded else "✗"
        print(f"  {status} {module}")
    
    print(f"\nOverall Status: {'Ready' if info['dependencies_met'] else 'Limited functionality'}")


# Экспорт основных компонентов
__all__ = [
    # Основные классы (если доступны)
    '__version__',
    'VisualizationError',
    
    # Утилитарные функции
    'get_available_libraries',
    'check_visualization_dependencies',
    'get_visualization_info',
    'print_visualization_status',
    
    # Удобные функции создания графиков
    'create_financial_chart',
    'plot_zones_analysis',
    'plot_zone_detail',
    'plot_zones_comparison',
    'create_statistical_plot',
    
    # Функции работы с темами
    'get_available_themes',
    'set_default_theme'
]

# Добавляем классы если модули доступны
if _charts_available:
    __all__.extend(['FinancialCharts', 'ChartBuilder'])

if _zones_available:
    __all__.extend([
        'ZoneVisualizer',
        'ZoneChartBuilder',
        'plot_zones_on_chart',
        'plot_macd_zones_chart',
        'analyze_zones_visually',
    ])

if _statistical_available:
    __all__.extend(['StatisticalPlots', 'DistributionPlotter'])

if _themes_available:
    __all__.extend(['ChartThemes', 'get_theme', 'apply_theme'])

# Инициализация модуля
# Сводный INFO об инициализации (одна строка)
logger.info(
    "Visualization initialized: plotly=%s, matplotlib=%s, charts=%s, zones=%s, statistical=%s, themes=%s",
    _plotting_libraries.get('plotly'),
    _plotting_libraries.get('matplotlib'),
    'yes' if 'FinancialCharts' in globals() else 'no',
    'yes' if 'ZoneVisualizer' in globals() else 'no',
    'yes' if 'StatisticalPlots' in globals() else 'no',
    'yes' if 'ChartThemes' in globals() else 'no',
)
if not check_visualization_dependencies():
    logger.warning("Visualization module initialized with limited functionality due to missing dependencies")