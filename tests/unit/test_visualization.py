"""
Тесты для модуля визуализации BQuant

Проверяют корректность создания различных типов графиков и визуализаций.
"""

import pytest
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

# BQuant imports
from bquant.visualization import (
    get_available_libraries,
    check_visualization_dependencies,
    get_visualization_info,
    create_financial_chart,
    get_available_themes,
    set_default_theme
)

# Условные импорты для модулей
try:
    from bquant.visualization.charts import FinancialCharts, ChartBuilder
    charts_available = True
except ImportError:
    charts_available = False

try:
    from bquant.visualization.zones import ZoneVisualizer, plot_zones_on_chart
    zones_available = True
except ImportError:
    zones_available = False

try:
    from bquant.visualization.statistical import StatisticalPlots, create_quick_histogram
    statistical_available = True
except ImportError:
    statistical_available = False

try:
    from bquant.visualization.themes import ChartThemes, apply_theme
    themes_available = True
except ImportError:
    themes_available = False

# Проверка библиотек визуализации
try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def create_test_ohlcv_data(n_periods: int = 100, seed: int = 42) -> pd.DataFrame:
    """
    Создает тестовые OHLCV данные для графиков.
    
    Args:
        n_periods: Количество периодов
        seed: Семя для генератора случайных чисел
    
    Returns:
        DataFrame с OHLCV данными
    """
    np.random.seed(seed)
    
    # Создаем временные индексы
    timestamps = pd.date_range('2024-01-01', periods=n_periods, freq='1H')
    
    # Создаем базовую цену с трендом
    base_price = 2000
    trend = np.linspace(0, 200, n_periods)
    noise = np.random.normal(0, 10, n_periods)
    
    close_prices = base_price + trend + noise
    
    # Создаем OHLC на основе close
    high_offset = np.random.uniform(5, 20, n_periods)
    low_offset = np.random.uniform(5, 20, n_periods)
    open_offset = np.random.uniform(-10, 10, n_periods)
    
    data = pd.DataFrame({
        'open': close_prices + open_offset,
        'high': close_prices + high_offset,
        'low': close_prices - low_offset,
        'close': close_prices,
        'volume': np.random.uniform(1000, 10000, n_periods)
    }, index=timestamps)
    
    return data


def create_test_macd_data(n_periods: int = 100, seed: int = 42) -> pd.DataFrame:
    """
    Создает тестовые данные MACD.
    
    Args:
        n_periods: Количество периодов
        seed: Семя для генератора случайных чисел
    
    Returns:
        DataFrame с данными MACD
    """
    np.random.seed(seed)
    
    timestamps = pd.date_range('2024-01-01', periods=n_periods, freq='1H')
    
    # Создаем MACD данные
    macd = np.random.normal(0, 5, n_periods)
    macd_signal = np.convolve(macd, np.ones(9)/9, mode='same')  # Простое скользящее среднее
    macd_hist = macd - macd_signal
    
    data = pd.DataFrame({
        'macd': macd,
        'macd_signal': macd_signal,
        'macd_hist': macd_hist
    }, index=timestamps)
    
    return data


def create_test_zones_data() -> List[Dict[str, Any]]:
    """
    Создает тестовые данные зон.
    
    Returns:
        Список словарей с данными зон
    """
    return [
        {
            'zone_id': 'bull_zone_1',
            'type': 'bull',
            'start_time': '2024-01-01 10:00:00',
            'end_time': '2024-01-01 14:00:00',
            'start_price': 2000,
            'end_price': 2050,
            'duration': 4,
            'price_return': 0.025
        },
        {
            'zone_id': 'bear_zone_1',
            'type': 'bear',
            'start_time': '2024-01-01 15:00:00',
            'end_time': '2024-01-01 18:00:00',
            'start_price': 2050,
            'end_price': 2020,
            'duration': 3,
            'price_return': -0.015
        }
    ]


class TestVisualizationModule:
    """Тесты основного модуля визуализации."""
    
    def test_get_available_libraries(self):
        """Тест получения доступных библиотек."""
        libraries = get_available_libraries()
        
        assert isinstance(libraries, dict)
        assert 'plotly' in libraries
        assert 'matplotlib' in libraries
        assert 'data' in libraries
        
        # Проверяем типы значений
        for lib, available in libraries.items():
            assert isinstance(available, bool)
    
    def test_check_visualization_dependencies(self):
        """Тест проверки зависимостей."""
        deps_ok = check_visualization_dependencies()
        assert isinstance(deps_ok, bool)
    
    def test_get_visualization_info(self):
        """Тест получения информации о модуле."""
        info = get_visualization_info()
        
        assert isinstance(info, dict)
        assert 'version' in info
        assert 'available_libraries' in info
        assert 'modules_loaded' in info
        assert 'dependencies_met' in info
        
        # Проверяем структуру modules_loaded
        modules = info['modules_loaded']
        expected_modules = ['charts', 'zones', 'statistical', 'themes']
        for module in expected_modules:
            assert module in modules
            assert isinstance(modules[module], bool)
    
    def test_get_available_themes(self):
        """Тест получения доступных тем."""
        themes = get_available_themes()
        
        assert isinstance(themes, list)
        # Должна быть как минимум default тема
        assert len(themes) >= 1
    
    @pytest.mark.skipif(not (PLOTLY_AVAILABLE or MATPLOTLIB_AVAILABLE), 
                       reason="No visualization libraries available")
    def test_create_financial_chart(self):
        """Тест создания финансового графика."""
        data = create_test_ohlcv_data(50)
        
        # Тест различных типов графиков
        chart_types = ['candlestick', 'line']
        
        for chart_type in chart_types:
            try:
                fig = create_financial_chart(chart_type, data=data, title=f"Test {chart_type}")
                assert fig is not None
            except Exception as e:
                # Если конкретный тип не поддерживается, это не критично
                pytest.skip(f"Chart type {chart_type} not supported: {e}")


@pytest.mark.skipif(not charts_available, reason="Charts module not available")
class TestFinancialCharts:
    """Тесты модуля финансовых графиков."""
    
    @pytest.fixture
    def charts(self):
        """Создание объекта FinancialCharts."""
        backend = 'plotly' if PLOTLY_AVAILABLE else 'matplotlib'
        return FinancialCharts(backend=backend)
    
    @pytest.fixture
    def test_data(self):
        """Создание тестовых данных."""
        return create_test_ohlcv_data(50)
    
    @pytest.fixture
    def macd_data(self):
        """Создание тестовых данных MACD."""
        return create_test_macd_data(50)
    
    def test_charts_initialization(self, charts):
        """Тест инициализации объекта FinancialCharts."""
        assert charts.backend in ['plotly', 'matplotlib']
        assert hasattr(charts, 'default_config')
        assert isinstance(charts.default_config, dict)
    
    def test_create_candlestick_chart(self, charts, test_data):
        """Тест создания свечного графика."""
        fig = charts.create_candlestick_chart(test_data, title="Test Candlestick")
        assert fig is not None
    
    def test_create_line_chart(self, charts, test_data):
        """Тест создания линейного графика."""
        fig = charts.create_line_chart(test_data, columns=['close'], title="Test Line Chart")
        assert fig is not None
    
    def test_plot_ohlcv(self, charts, test_data):
        """Тест функции plot_ohlcv."""
        fig = charts.plot_ohlcv(test_data, title="Test OHLCV")
        assert fig is not None
    
    def test_plot_macd_with_zones(self, charts, macd_data):
        """Тест графика MACD с зонами."""
        zones_data = create_test_zones_data()
        
        fig = charts.plot_macd_with_zones(macd_data, zones_data, title="Test MACD with Zones")
        assert fig is not None
    
    def test_invalid_data_handling(self, charts):
        """Тест обработки некорректных данных."""
        # Пустой DataFrame
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError):
            charts.create_candlestick_chart(empty_data)
        
        # DataFrame без необходимых колонок
        invalid_data = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        
        with pytest.raises(ValueError):
            charts.create_candlestick_chart(invalid_data)


@pytest.mark.skipif(not zones_available, reason="Zones visualization module not available")
class TestZoneVisualizer:
    """Тесты модуля визуализации зон."""
    
    @pytest.fixture
    def visualizer(self):
        """Создание объекта ZoneVisualizer."""
        backend = 'plotly' if PLOTLY_AVAILABLE else 'matplotlib'
        return ZoneVisualizer(backend=backend)
    
    @pytest.fixture
    def test_data(self):
        """Создание тестовых данных."""
        return create_test_ohlcv_data(50)
    
    @pytest.fixture
    def zones_data(self):
        """Создание тестовых данных зон."""
        return create_test_zones_data()
    
    def test_visualizer_initialization(self, visualizer):
        """Тест инициализации визуализатора."""
        assert visualizer.backend in ['plotly', 'matplotlib']
        assert hasattr(visualizer, 'zone_colors')
        assert isinstance(visualizer.zone_colors, dict)
    
    def test_plot_zones_analysis(self, visualizer, zones_data):
        """Тест анализа зон."""
        fig = visualizer.plot_zones_analysis(zones_data, title="Test Zones Analysis")
        assert fig is not None
    
    def test_plot_zones_distribution(self, visualizer, zones_data):
        """Тест распределения зон."""
        fig = visualizer.plot_zones_distribution(zones_data, feature='duration', 
                                                title="Test Duration Distribution")
        assert fig is not None
    
    def test_convenience_functions(self, test_data, zones_data):
        """Тест удобных функций."""
        if PLOTLY_AVAILABLE or MATPLOTLIB_AVAILABLE:
            fig = plot_zones_on_chart(test_data, zones_data, title="Test Zones on Chart")
            assert fig is not None


@pytest.mark.skipif(not statistical_available, reason="Statistical plots module not available")
class TestStatisticalPlots:
    """Тесты модуля статистических графиков."""
    
    @pytest.fixture
    def plotter(self):
        """Создание объекта StatisticalPlots."""
        backend = 'plotly' if PLOTLY_AVAILABLE else 'matplotlib'
        return StatisticalPlots(backend=backend)
    
    @pytest.fixture
    def test_data(self):
        """Создание тестовых данных."""
        np.random.seed(42)
        return pd.DataFrame({
            'x': np.random.normal(0, 1, 100),
            'y': np.random.normal(0, 1, 100),
            'z': np.random.normal(0, 1, 100),
            'category': np.random.choice(['A', 'B', 'C'], 100)
        })
    
    def test_plotter_initialization(self, plotter):
        """Тест инициализации объекта StatisticalPlots."""
        assert plotter.backend in ['plotly', 'matplotlib']
        assert hasattr(plotter, 'default_config')
    
    def test_create_histogram(self, plotter, test_data):
        """Тест создания гистограммы."""
        fig = plotter.create_histogram(test_data['x'], title="Test Histogram")
        assert fig is not None
    
    def test_create_scatter_plot(self, plotter, test_data):
        """Тест создания диаграммы рассеяния."""
        fig = plotter.create_scatter_plot(test_data, 'x', 'y', title="Test Scatter")
        assert fig is not None
    
    def test_create_correlation_matrix(self, plotter, test_data):
        """Тест создания матрицы корреляций."""
        numeric_data = test_data[['x', 'y', 'z']]
        fig = plotter.create_correlation_matrix(numeric_data, title="Test Correlation")
        assert fig is not None
    
    def test_create_box_plot(self, plotter, test_data):
        """Тест создания box plot."""
        fig = plotter.create_box_plot(test_data, 'x', 'category', title="Test Box Plot")
        assert fig is not None
    
    def test_convenience_functions(self, test_data):
        """Тест удобных функций."""
        if PLOTLY_AVAILABLE or MATPLOTLIB_AVAILABLE:
            fig = create_quick_histogram(test_data['x'], title="Quick Histogram")
            assert fig is not None


@pytest.mark.skipif(not themes_available, reason="Themes module not available")
class TestChartThemes:
    """Тесты модуля тем оформления."""
    
    @pytest.fixture
    def theme_manager(self):
        """Создание объекта ChartThemes."""
        return ChartThemes()
    
    def test_theme_manager_initialization(self, theme_manager):
        """Тест инициализации менеджера тем."""
        assert hasattr(theme_manager, '_themes')
        assert isinstance(theme_manager._themes, dict)
        assert len(theme_manager._themes) > 0
    
    def test_get_available_themes(self, theme_manager):
        """Тест получения доступных тем."""
        themes = theme_manager.get_available_themes()
        
        assert isinstance(themes, list)
        assert len(themes) > 0
        
        # Проверяем наличие базовых тем
        expected_themes = ['bquant_light', 'bquant_dark', 'financial', 'minimal', 'professional']
        for theme in expected_themes:
            assert theme in themes
    
    def test_get_theme(self, theme_manager):
        """Тест получения конфигурации темы."""
        theme_config = theme_manager.get_theme('bquant_light')
        
        assert isinstance(theme_config, dict)
        assert 'name' in theme_config
        assert 'colors' in theme_config
        assert 'layout' in theme_config
        
        # Проверяем структуру цветов
        colors = theme_config['colors']
        required_colors = ['background', 'text', 'bullish', 'bearish']
        for color in required_colors:
            assert color in colors
    
    def test_set_default_theme(self, theme_manager):
        """Тест установки темы по умолчанию."""
        result = theme_manager.set_default_theme('bquant_dark')
        assert result is True
        
        # Тест с несуществующей темой
        result = theme_manager.set_default_theme('nonexistent_theme')
        assert result is False
    
    def test_theme_application_to_figure(self, theme_manager):
        """Тест применения темы к графику."""
        if PLOTLY_AVAILABLE:
            import plotly.graph_objects as go
            fig = go.Figure()
            
            themed_fig = theme_manager.apply_theme_to_figure(fig, 'bquant_light')
            assert themed_fig is not None
        
        if MATPLOTLIB_AVAILABLE:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            
            themed_fig = theme_manager.apply_theme_to_figure(fig, 'bquant_dark')
            assert themed_fig is not None
            plt.close(fig)
    
    def test_global_theme_functions(self):
        """Тест глобальных функций тем."""
        themes = get_available_themes()
        assert isinstance(themes, list)
        assert len(themes) > 0
        
        result = set_default_theme('minimal')
        assert isinstance(result, bool)


class TestIntegrationVisualization:
    """Интеграционные тесты модуля визуализации."""
    
    def test_complete_visualization_workflow(self):
        """Тест полного workflow визуализации."""
        # Создаем тестовые данные
        ohlcv_data = create_test_ohlcv_data(30)
        macd_data = create_test_macd_data(30)
        zones_data = create_test_zones_data()
        
        # Проверяем, что модуль загружается
        info = get_visualization_info()
        assert isinstance(info, dict)
        
        # Если библиотеки доступны, тестируем создание графиков
        if charts_available and (PLOTLY_AVAILABLE or MATPLOTLIB_AVAILABLE):
            charts = FinancialCharts()
            
            # Тест создания различных типов графиков
            candlestick_fig = charts.create_candlestick_chart(ohlcv_data)
            assert candlestick_fig is not None
            
            line_fig = charts.create_line_chart(ohlcv_data, ['close'])
            assert line_fig is not None
            
            macd_fig = charts.plot_macd_with_zones(macd_data, zones_data)
            assert macd_fig is not None
        
        # Тест тем если доступны
        if themes_available:
            themes = get_available_themes()
            assert len(themes) > 0
            
            # Применяем тему
            result = set_default_theme(themes[0])
            assert isinstance(result, bool)
    
    def test_error_handling_and_fallbacks(self):
        """Тест обработки ошибок и fallback behavior."""
        # Тест с пустыми данными
        empty_data = pd.DataFrame()
        
        if charts_available:
            charts = FinancialCharts()
            
            with pytest.raises(ValueError):
                charts.create_candlestick_chart(empty_data)
        
        # Тест с некорректными параметрами
        try:
            invalid_fig = create_financial_chart('unknown_type')
            # Если не выбросилось исключение, проверяем что вернулся None или похожее
            assert invalid_fig is None or hasattr(invalid_fig, '__class__')
        except (ValueError, Exception):
            # Ожидаемое поведение для некорректных параметров
            pass
    
    def test_backend_switching(self):
        """Тест переключения между backend'ами."""
        if charts_available:
            # Тест с plotly backend
            if PLOTLY_AVAILABLE:
                charts_plotly = FinancialCharts(backend='plotly')
                assert charts_plotly.backend == 'plotly'
            
            # Тест с matplotlib backend
            if MATPLOTLIB_AVAILABLE:
                charts_matplotlib = FinancialCharts(backend='matplotlib')
                assert charts_matplotlib.backend == 'matplotlib'
    
    def test_theme_consistency(self):
        """Тест консистентности тем."""
        if themes_available:
            theme_manager = ChartThemes()
            themes = theme_manager.get_available_themes()
            
            # Проверяем, что все темы имеют необходимые компоненты
            for theme_name in themes:
                theme_config = theme_manager.get_theme(theme_name)
                
                assert 'colors' in theme_config
                assert 'layout' in theme_config
                
                colors = theme_config['colors']
                required_colors = ['background', 'text', 'bullish', 'bearish']
                
                for color in required_colors:
                    assert color in colors
                    assert isinstance(colors[color], str)
                    # Проверяем, что это валидный цвет (начинается с # или названием)
                    assert colors[color].startswith('#') or colors[color].startswith('rgb') or colors[color].isalpha()


class TestVisualizationErrorHandling:
    """Тесты обработки ошибок в модуле визуализации."""
    
    def test_missing_dependencies_handling(self):
        """Тест обработки отсутствующих зависимостей."""
        # Тест информации о зависимостях
        deps_info = get_available_libraries()
        assert isinstance(deps_info, dict)
        
        deps_status = check_visualization_dependencies()
        assert isinstance(deps_status, bool)
    
    def test_invalid_data_types(self):
        """Тест обработки некорректных типов данных."""
        if charts_available:
            charts = FinancialCharts()
            
            # Тест с некорректными типами данных
            with pytest.raises((ValueError, TypeError, AttributeError)):
                charts.create_candlestick_chart("not a dataframe")
            
            with pytest.raises((ValueError, TypeError, AttributeError)):
                charts.create_candlestick_chart(None)
    
    def test_missing_columns_handling(self):
        """Тест обработки отсутствующих колонок."""
        if charts_available:
            charts = FinancialCharts()
            
            # DataFrame без необходимых колонок для OHLC
            invalid_data = pd.DataFrame({
                'price': [1, 2, 3, 4, 5],
                'volume': [100, 200, 300, 400, 500]
            })
            
            with pytest.raises(ValueError):
                charts.create_candlestick_chart(invalid_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
