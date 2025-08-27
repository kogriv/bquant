"""
Модуль создания финансовых графиков BQuant

Предоставляет инструменты для создания различных типов финансовых графиков:
- Свечные графики (Candlestick)
- OHLC графики  
- Линейные графики цен
- Графики объемов
- Комбинированные графики с индикаторами
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import warnings

from ..core.logging_config import get_logger
from ..core.exceptions import AnalysisError

# Получаем логгер для модуля
logger = get_logger(__name__)

# Проверка доступности библиотек
try:
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available - some chart functionality will be limited")

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - some chart functionality will be limited")


class ChartBuilder:
    """
    Базовый класс для построения графиков.
    
    Предоставляет общие методы для создания и настройки графиков.
    """
    
    def __init__(self, backend: str = 'plotly'):
        """
        Инициализация построителя графиков.
        
        Args:
            backend: Библиотека для построения ('plotly' или 'matplotlib')
        """
        self.backend = backend
        self.logger = get_logger(f"{__name__}.ChartBuilder")
        
        # Проверяем доступность выбранной библиотеки
        if backend == 'plotly' and not PLOTLY_AVAILABLE:
            if MATPLOTLIB_AVAILABLE:
                self.backend = 'matplotlib'
                self.logger.warning("Plotly not available, switching to matplotlib")
            else:
                raise AnalysisError("No visualization libraries available")
        
        elif backend == 'matplotlib' and not MATPLOTLIB_AVAILABLE:
            if PLOTLY_AVAILABLE:
                self.backend = 'plotly'
                self.logger.warning("Matplotlib not available, switching to plotly")
            else:
                raise AnalysisError("No visualization libraries available")
        
        self.logger.info(f"Chart builder initialized with {self.backend} backend")
    
    def validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        Валидация данных для построения графика.
        
        Args:
            data: DataFrame с данными
            required_columns: Список обязательных колонок
        
        Returns:
            True если данные валидны
        """
        if data is None or data.empty:
            raise ValueError("Data is empty")
        
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        return True
    
    def _prepare_datetime_index(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Подготовка datetime индекса для графика.
        
        Args:
            data: DataFrame с данными
        
        Returns:
            DataFrame с подготовленным индексом
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
            elif 'date' in data.columns:
                data = data.set_index('date')
            else:
                # Создаем временной индекс если его нет
                data.index = pd.date_range('2024-01-01', periods=len(data), freq='1H')
        
        return data


class FinancialCharts(ChartBuilder):
    """
    Класс для создания финансовых графиков.
    
    Предоставляет методы для создания различных типов финансовых визуализаций.
    """
    
    def __init__(self, backend: str = 'plotly', **kwargs):
        """
        Инициализация создателя финансовых графиков.
        
        Args:
            backend: Библиотека для построения
            **kwargs: Дополнительные параметры
        """
        super().__init__(backend)
        
        # Настройки по умолчанию
        self.default_config = {
            'width': kwargs.get('width', 1200),
            'height': kwargs.get('height', 600),
            'title_font_size': kwargs.get('title_font_size', 16),
            'show_volume': kwargs.get('show_volume', True),
            'volume_ratio': kwargs.get('volume_ratio', 0.3),
            'colors': {
                'bullish': kwargs.get('bullish_color', '#00ff88'),
                'bearish': kwargs.get('bearish_color', '#ff4444'),
                'volume': kwargs.get('volume_color', '#888888'),
                'background': kwargs.get('background_color', '#ffffff')
            }
        }
    
    def create_candlestick_chart(self, data: pd.DataFrame, 
                                title: str = "Candlestick Chart",
                                show_volume: bool = True,
                                **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание свечного графика.
        
        Args:
            data: DataFrame с OHLCV данными
            title: Заголовок графика
            show_volume: Показывать график объемов
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика (Plotly Figure или Matplotlib Figure)
        """
        self.validate_data(data, ['open', 'high', 'low', 'close'])
        data = self._prepare_datetime_index(data)
        
        if self.backend == 'plotly':
            return self._create_plotly_candlestick(data, title, show_volume, **kwargs)
        else:
            return self._create_matplotlib_candlestick(data, title, show_volume, **kwargs)
    
    def create_ohlc_chart(self, data: pd.DataFrame,
                         title: str = "OHLC Chart",
                         **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание OHLC графика.
        
        Args:
            data: DataFrame с OHLC данными
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        self.validate_data(data, ['open', 'high', 'low', 'close'])
        data = self._prepare_datetime_index(data)
        
        if self.backend == 'plotly':
            return self._create_plotly_ohlc(data, title, **kwargs)
        else:
            return self._create_matplotlib_ohlc(data, title, **kwargs)
    
    def create_line_chart(self, data: pd.DataFrame,
                         columns: List[str] = None,
                         title: str = "Price Chart",
                         **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание линейного графика цен.
        
        Args:
            data: DataFrame с данными
            columns: Колонки для отображения (по умолчанию 'close')
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if columns is None:
            columns = ['close'] if 'close' in data.columns else [data.columns[0]]
        
        self.validate_data(data, columns)
        data = self._prepare_datetime_index(data)
        
        if self.backend == 'plotly':
            return self._create_plotly_line(data, columns, title, **kwargs)
        else:
            return self._create_matplotlib_line(data, columns, title, **kwargs)
    
    def create_area_chart(self, data: pd.DataFrame,
                         columns: List[str] = None,
                         title: str = "Area Chart",
                         **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание графика-области.
        
        Args:
            data: DataFrame с данными
            columns: Колонки для отображения
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if columns is None:
            columns = ['close'] if 'close' in data.columns else [data.columns[0]]
        
        self.validate_data(data, columns)
        data = self._prepare_datetime_index(data)
        
        if self.backend == 'plotly':
            return self._create_plotly_area(data, columns, title, **kwargs)
        else:
            return self._create_matplotlib_area(data, columns, title, **kwargs)
    
    def plot_ohlcv(self, data: pd.DataFrame,
                   title: str = "OHLCV Chart",
                   chart_type: str = 'candlestick',
                   **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание OHLCV графика (совместимость с API).
        
        Args:
            data: DataFrame с OHLCV данными
            title: Заголовок графика
            chart_type: Тип графика ('candlestick', 'ohlc', 'line')
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if chart_type == 'candlestick':
            return self.create_candlestick_chart(data, title, **kwargs)
        elif chart_type == 'ohlc':
            return self.create_ohlc_chart(data, title, **kwargs)
        elif chart_type == 'line':
            return self.create_line_chart(data, title=title, **kwargs)
        else:
            raise ValueError(f"Unknown chart type: {chart_type}")
    
    def plot_macd_with_zones(self, macd_data: pd.DataFrame, 
                           zones_data: List[Dict] = None,
                           title: str = "MACD with Zones",
                           **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание графика MACD с зонами.
        
        Args:
            macd_data: DataFrame с данными MACD
            zones_data: Данные зон (опционально)
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        required_columns = ['macd', 'macd_signal', 'macd_hist']
        self.validate_data(macd_data, required_columns)
        macd_data = self._prepare_datetime_index(macd_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_macd_with_zones(macd_data, zones_data, title, **kwargs)
        else:
            return self._create_matplotlib_macd_with_zones(macd_data, zones_data, title, **kwargs)
    
    # Plotly реализации
    def _create_plotly_candlestick(self, data: pd.DataFrame, title: str, 
                                  show_volume: bool, **kwargs) -> go.Figure:
        """Создание свечного графика с помощью Plotly."""
        # Определяем количество подграфиков
        rows = 2 if show_volume and 'volume' in data.columns else 1
        row_heights = [0.7, 0.3] if rows == 2 else [1.0]
        
        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=row_heights,
            subplot_titles=[title, "Volume"] if rows == 2 else [title]
        )
        
        # Свечной график
        candlestick = go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='Price',
            increasing_line_color=self.default_config['colors']['bullish'],
            decreasing_line_color=self.default_config['colors']['bearish']
        )
        
        fig.add_trace(candlestick, row=1, col=1)
        
        # График объемов
        if show_volume and 'volume' in data.columns:
            colors = ['green' if close >= open else 'red' 
                     for close, open in zip(data['close'], data['open'])]
            
            volume_bars = go.Bar(
                x=data.index,
                y=data['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7
            )
            
            fig.add_trace(volume_bars, row=2, col=1)
        
        # Настройка макета
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            showlegend=True,
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_ohlc(self, data: pd.DataFrame, title: str, **kwargs) -> go.Figure:
        """Создание OHLC графика с помощью Plotly."""
        fig = go.Figure(data=go.Ohlc(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='OHLC'
        ))
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_line(self, data: pd.DataFrame, columns: List[str], 
                           title: str, **kwargs) -> go.Figure:
        """Создание линейного графика с помощью Plotly."""
        fig = go.Figure()
        
        for column in columns:
            if column in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data[column],
                    mode='lines',
                    name=column.title(),
                    line=dict(width=2)
                ))
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    def _create_plotly_area(self, data: pd.DataFrame, columns: List[str], 
                           title: str, **kwargs) -> go.Figure:
        """Создание графика-области с помощью Plotly."""
        fig = go.Figure()
        
        for column in columns:
            if column in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data[column],
                    mode='lines',
                    name=column.title(),
                    fill='tonexty' if fig.data else 'tozeroy',
                    line=dict(width=0)
                ))
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    def _create_plotly_macd_with_zones(self, macd_data: pd.DataFrame, 
                                     zones_data: List[Dict], title: str, 
                                     **kwargs) -> go.Figure:
        """Создание графика MACD с зонами с помощью Plotly."""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.4],
            subplot_titles=['MACD', 'Histogram']
        )
        
        # MACD линии
        fig.add_trace(go.Scatter(
            x=macd_data.index,
            y=macd_data['macd'],
            mode='lines',
            name='MACD',
            line=dict(color='blue', width=2)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=macd_data.index,
            y=macd_data['macd_signal'],
            mode='lines',
            name='Signal',
            line=dict(color='red', width=2)
        ), row=1, col=1)
        
        # Гистограмма
        colors = ['green' if val >= 0 else 'red' for val in macd_data['macd_hist']]
        fig.add_trace(go.Bar(
            x=macd_data.index,
            y=macd_data['macd_hist'],
            name='Histogram',
            marker_color=colors,
            opacity=0.7
        ), row=2, col=1)
        
        # Добавляем зоны если есть
        if zones_data:
            for i, zone in enumerate(zones_data):
                if 'start_time' in zone and 'end_time' in zone:
                    fig.add_vrect(
                        x0=zone['start_time'],
                        x1=zone['end_time'],
                        fillcolor='lightblue' if zone.get('type') == 'bull' else 'lightpink',
                        opacity=0.3,
                        layer="below",
                        line_width=0,
                        row=1, col=1
                    )
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    # Matplotlib реализации (упрощенные заглушки)
    def _create_matplotlib_candlestick(self, data: pd.DataFrame, title: str, 
                                      show_volume: bool, **kwargs) -> plt.Figure:
        """Создание свечного графика с помощью Matplotlib (заглушка)."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Простая реализация без библиотеки mplfinance
        ax.plot(data.index, data['close'], label='Close Price')
        ax.set_title(title)
        ax.legend()
        
        self.logger.warning("Matplotlib candlestick chart is simplified. Consider using Plotly for full functionality.")
        
        return fig
    
    def _create_matplotlib_ohlc(self, data: pd.DataFrame, title: str, **kwargs) -> plt.Figure:
        """Создание OHLC графика с помощью Matplotlib (заглушка)."""
        return self._create_matplotlib_candlestick(data, title, False, **kwargs)
    
    def _create_matplotlib_line(self, data: pd.DataFrame, columns: List[str], 
                               title: str, **kwargs) -> plt.Figure:
        """Создание линейного графика с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for column in columns:
            if column in data.columns:
                ax.plot(data.index, data[column], label=column.title())
        
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def _create_matplotlib_area(self, data: pd.DataFrame, columns: List[str], 
                               title: str, **kwargs) -> plt.Figure:
        """Создание графика-области с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for column in columns:
            if column in data.columns:
                ax.fill_between(data.index, data[column], alpha=0.7, label=column.title())
        
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def _create_matplotlib_macd_with_zones(self, macd_data: pd.DataFrame, 
                                          zones_data: List[Dict], title: str, 
                                          **kwargs) -> plt.Figure:
        """Создание графика MACD с зонами с помощью Matplotlib."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # MACD
        ax1.plot(macd_data.index, macd_data['macd'], label='MACD', color='blue')
        ax1.plot(macd_data.index, macd_data['macd_signal'], label='Signal', color='red')
        ax1.set_title('MACD')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Гистограмма
        colors = ['green' if val >= 0 else 'red' for val in macd_data['macd_hist']]
        ax2.bar(macd_data.index, macd_data['macd_hist'], color=colors, alpha=0.7)
        ax2.set_title('Histogram')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig


# Удобные функции
def create_candlestick_chart(data: pd.DataFrame, **kwargs):
    """
    Быстрое создание свечного графика.
    
    Args:
        data: DataFrame с OHLCV данными
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика
    """
    charts = FinancialCharts()
    return charts.create_candlestick_chart(data, **kwargs)


def create_price_chart(data: pd.DataFrame, chart_type: str = 'line', **kwargs):
    """
    Быстрое создание графика цен.
    
    Args:
        data: DataFrame с данными
        chart_type: Тип графика ('line', 'area', 'candlestick')
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика или None в случае ошибки
    """
    try:
        charts = FinancialCharts()
        
        if chart_type == 'line':
            return charts.create_line_chart(data, **kwargs)
        elif chart_type == 'area':
            return charts.create_area_chart(data, **kwargs)
        elif chart_type == 'candlestick':
            return charts.create_candlestick_chart(data, **kwargs)
        else:
            logger.warning(f"Unknown chart type: {chart_type}")
            return None
    except Exception as e:
        logger.warning(f"Failed to create chart: {e}")
        return None


# Экспорт
__all__ = [
    'ChartBuilder',
    'FinancialCharts',
    'create_candlestick_chart',
    'create_price_chart',
    'PLOTLY_AVAILABLE',
    'MATPLOTLIB_AVAILABLE'
]
