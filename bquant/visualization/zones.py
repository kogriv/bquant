"""Модуль визуализации зон BQuant."""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..core.logging_config import get_logger
from ..core.exceptions import AnalysisError

# Получаем логгер для модуля
logger = get_logger(__name__)

# Проверка доступности библиотек визуализации
try:
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available - zones visualization will be limited")

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - zones visualization will be limited")


class ZoneChartBuilder:
    """
    Базовый класс для построения графиков зон.
    """
    
    def __init__(self, backend: str = 'plotly'):
        """
        Инициализация построителя графиков зон.
        
        Args:
            backend: Библиотека для построения ('plotly' или 'matplotlib')
        """
        self.backend = backend
        self.logger = get_logger(f"{__name__}.ZoneChartBuilder")
        
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
        
        # Цветовая схема для зон
        self.zone_colors = {
            'bull': {'fill': 'rgba(0, 255, 136, 0.3)', 'line': '#00ff88'},
            'bear': {'fill': 'rgba(255, 68, 68, 0.3)', 'line': '#ff4444'},
            'support': {'fill': 'rgba(0, 136, 255, 0.3)', 'line': '#0088ff'},
            'resistance': {'fill': 'rgba(255, 136, 0, 0.3)', 'line': '#ff8800'}
        }
        
        self.logger.info(f"Zone chart builder initialized with {self.backend} backend")
    
    def _prepare_zone_data(self, zones_data: Union[List[Dict], pd.DataFrame, List[Any]]) -> List[Dict]:
        """
        Подготовка данных зон для визуализации.

        Args:
            zones_data: Данные зон

        Returns:
            Список словарей с данными зон
        """
        if isinstance(zones_data, pd.DataFrame):
            return zones_data.to_dict('records')
        elif isinstance(zones_data, list):
            normalized: List[Dict[str, Any]] = []
            for zone in zones_data:
                if isinstance(zone, dict):
                    normalized.append(zone)
                    continue

                if hasattr(zone, "to_analyzer_format"):
                    try:
                        normalized.append(zone.to_analyzer_format())
                        continue
                    except Exception:  # pragma: no cover - диагностический вывод
                        self.logger.debug("Failed to call to_analyzer_format() on %s", zone)

                if is_dataclass(zone):
                    normalized.append(asdict(zone))
                elif hasattr(zone, "__dict__"):
                    normalized.append({key: getattr(zone, key) for key in dir(zone)
                                       if not key.startswith("_") and not callable(getattr(zone, key))})
                else:
                    raise ValueError("Unsupported zone object type: %r" % (type(zone),))

            return normalized
        else:
            raise ValueError("zones_data must be DataFrame or list of dicts")


class ZoneVisualizer(ZoneChartBuilder):
    """
    Класс для визуализации торговых зон.
    """
    
    def __init__(self, backend: str = 'plotly', **kwargs):
        """
        Инициализация визуализатора зон.
        
        Args:
            backend: Библиотека для построения
            **kwargs: Дополнительные параметры
        """
        super().__init__(backend)
        
        # Настройки по умолчанию
        self.default_config = {
            'width': kwargs.get('width', 1200),
            'height': kwargs.get('height', 800),
            'show_zone_labels': kwargs.get('show_zone_labels', True),
            'show_zone_stats': kwargs.get('show_zone_stats', True),
            'opacity': kwargs.get('opacity', 0.3)
        }
    
    def plot_zones_on_price_chart(self, price_data: pd.DataFrame,
                                 zones_data: Union[List[Dict], pd.DataFrame],
                                 title: str = "Price Chart with Zones",
                                 **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Отображение зон на графике цен.
        
        Args:
            price_data: DataFrame с данными цен (OHLCV)
            zones_data: Данные зон
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        zones = self._prepare_zone_data(zones_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_zones_on_price(price_data, zones, title, **kwargs)
        else:
            return self._create_matplotlib_zones_on_price(price_data, zones, title, **kwargs)

    def plot_zone_detail(self, price_data: pd.DataFrame,
                         zone: Union[Dict[str, Any], Any],
                         context_bars: int = 20,
                         title: str = "Zone Detail",
                         **kwargs) -> Union[go.Figure, plt.Figure]:
        """Детализированный просмотр отдельной зоны."""

        zone_dict = self._prepare_zone_data([zone])[0]
        zone_start = zone_dict.get('start_time')
        zone_end = zone_dict.get('end_time')

        detail_data = price_data
        if zone_start is not None and zone_end is not None and not price_data.empty:
            index = price_data.index

            def _get_position(target):
                try:
                    loc = index.get_loc(target)
                    if isinstance(loc, slice):
                        return loc.start
                    return int(loc)
                except KeyError:
                    idx = index.get_indexer([target], method='nearest')
                    if idx.size and idx[0] != -1:
                        return int(idx[0])
                    return None

            start_idx = _get_position(zone_start)
            end_idx = _get_position(zone_end)

            if start_idx is not None and end_idx is not None:
                left = max(0, min(start_idx, end_idx) - int(context_bars))
                right = min(len(price_data) - 1, max(start_idx, end_idx) + int(context_bars))
                detail_data = price_data.iloc[left : right + 1]

        return self.plot_zones_on_price_chart(
            detail_data,
            [zone_dict],
            title=title,
            **kwargs,
        )

    def plot_zones_comparison(self, price_data: pd.DataFrame,
                              zones_data: Union[List[Dict], pd.DataFrame, List[Any]],
                              max_zones: int = 5,
                              date_range: Optional[Tuple[datetime, datetime]] = None,
                              title: str = "Zones Comparison",
                              **kwargs) -> Union[go.Figure, plt.Figure]:
        """Сравнение нескольких зон на ценовом графике."""

        zones = self._prepare_zone_data(zones_data)

        if date_range is not None:
            start_range, end_range = date_range
            zones = [
                zone for zone in zones
                if zone.get('start_time') is not None and zone.get('end_time') is not None
                and start_range <= zone['end_time'] and zone['start_time'] <= end_range
            ]

        if max_zones:
            zones = zones[:max(1, max_zones)]

        if not zones:
            return self.plot_zones_on_price_chart(price_data, [], title=title, **kwargs)

        subset = price_data
        start_times = [zone.get('start_time') for zone in zones if zone.get('start_time') is not None]
        end_times = [zone.get('end_time') for zone in zones if zone.get('end_time') is not None]
        if start_times and end_times and isinstance(price_data.index, pd.DatetimeIndex):
            global_start = min(start_times)
            global_end = max(end_times)
            subset = price_data[(price_data.index >= global_start) & (price_data.index <= global_end)]

        return self.plot_zones_on_price_chart(subset, zones, title=title, **kwargs)

    def plot_macd_zones(self, macd_data: pd.DataFrame,
                       zones_data: Union[List[Dict], pd.DataFrame],
                       title: str = "MACD with Zones",
                       **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Отображение зон на графике MACD.
        
        Args:
            macd_data: DataFrame с данными MACD
            zones_data: Данные зон
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        zones = self._prepare_zone_data(zones_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_macd_zones(macd_data, zones, title, **kwargs)
        else:
            return self._create_matplotlib_macd_zones(macd_data, zones, title, **kwargs)
    
    def plot_zones_analysis(self, zones_data: Union[List[Dict], pd.DataFrame],
                           analysis_data: Dict[str, Any] = None,
                           title: str = "Zones Analysis",
                           **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Визуализация анализа зон.
        
        Args:
            zones_data: Данные зон
            analysis_data: Результаты анализа зон (опционально)
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        zones = self._prepare_zone_data(zones_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_zones_analysis(zones, analysis_data, title, **kwargs)
        else:
            return self._create_matplotlib_zones_analysis(zones, analysis_data, title, **kwargs)
    
    def plot_zones_distribution(self, zones_data: Union[List[Dict], pd.DataFrame],
                               feature: str = 'duration',
                               title: str = "Zones Distribution",
                               **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Визуализация распределения характеристик зон.
        
        Args:
            zones_data: Данные зон
            feature: Характеристика для анализа
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        zones = self._prepare_zone_data(zones_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_zones_distribution(zones, feature, title, **kwargs)
        else:
            return self._create_matplotlib_zones_distribution(zones, feature, title, **kwargs)
    
    def plot_zones_correlation(self, zones_data: Union[List[Dict], pd.DataFrame],
                              title: str = "Zones Characteristics Correlation",
                              **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Визуализация корреляций характеристик зон.
        
        Args:
            zones_data: Данные зон
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        zones_df = pd.DataFrame(self._prepare_zone_data(zones_data))
        
        if self.backend == 'plotly':
            return self._create_plotly_zones_correlation(zones_df, title, **kwargs)
        else:
            return self._create_matplotlib_zones_correlation(zones_df, title, **kwargs)
    
    # Plotly реализации
    def _create_plotly_zones_on_price(self, price_data: pd.DataFrame, 
                                     zones: List[Dict], title: str, 
                                     **kwargs) -> go.Figure:
        """Создание графика цен с зонами с помощью Plotly."""
        # Основной график свечей
        fig = go.Figure()
        
        # Добавляем свечной график
        fig.add_trace(go.Candlestick(
            x=price_data.index,
            open=price_data['open'],
            high=price_data['high'],
            low=price_data['low'],
            close=price_data['close'],
            name='Price',
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4444'
        ))
        
        # Добавляем зоны
        for i, zone in enumerate(zones):
            if 'start_time' in zone and 'end_time' in zone:
                zone_type = zone.get('type', 'bull')
                color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
                
                # Определяем границы зоны по цене
                if 'start_price' in zone and 'end_price' in zone:
                    y0 = min(zone['start_price'], zone['end_price'])
                    y1 = max(zone['start_price'], zone['end_price'])
                else:
                    # Если нет ценовых границ, используем весь диапазон
                    y0 = price_data['low'].min()
                    y1 = price_data['high'].max()
                
                # Добавляем прямоугольник зоны
                fig.add_shape(
                    type="rect",
                    x0=zone['start_time'],
                    y0=y0,
                    x1=zone['end_time'],
                    y1=y1,
                    fillcolor=color_config['fill'],
                    line=dict(color=color_config['line'], width=1),
                    layer="below"
                )
                
                # Добавляем подпись зоны
                if self.default_config['show_zone_labels']:
                    fig.add_annotation(
                        x=zone['start_time'],
                        y=y1,
                        text=f"{zone_type.title()} Zone {i+1}",
                        showarrow=False,
                        font=dict(size=10),
                        bgcolor="white",
                        opacity=0.8
                    )
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_macd_zones(self, macd_data: pd.DataFrame, 
                                 zones: List[Dict], title: str, 
                                 **kwargs) -> go.Figure:
        """Создание графика MACD с зонами с помощью Plotly."""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.4],
            subplot_titles=['MACD with Zones', 'Histogram']
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
        
        # Добавляем зоны
        for i, zone in enumerate(zones):
            if 'start_time' in zone and 'end_time' in zone:
                zone_type = zone.get('type', 'bull')
                color = 'lightblue' if zone_type == 'bull' else 'lightpink'
                
                # Добавляем зону на график MACD
                fig.add_vrect(
                    x0=zone['start_time'],
                    x1=zone['end_time'],
                    fillcolor=color,
                    opacity=self.default_config['opacity'],
                    layer="below",
                    line_width=0,
                    row=1, col=1
                )
                
                # Добавляем зону на гистограмму
                fig.add_vrect(
                    x0=zone['start_time'],
                    x1=zone['end_time'],
                    fillcolor=color,
                    opacity=self.default_config['opacity'],
                    layer="below",
                    line_width=0,
                    row=2, col=1
                )
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    def _create_plotly_zones_analysis(self, zones: List[Dict], 
                                     analysis_data: Dict[str, Any], 
                                     title: str, **kwargs) -> go.Figure:
        """Создание графика анализа зон с помощью Plotly."""
        # Создаем DataFrame из зон
        zones_df = pd.DataFrame(zones)
        
        if zones_df.empty:
            # Создаем пустой график с сообщением
            fig = go.Figure()
            fig.add_annotation(
                text="No zones data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle'
            )
            fig.update_layout(title=title)
            return fig
        
        # Создаем подграфики для различных аспектов анализа
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Zones by Type', 'Duration Distribution', 
                           'Return Distribution', 'Zone Timeline'],
            specs=[[{"type": "pie"}, {"type": "histogram"}],
                   [{"type": "histogram"}, {"type": "scatter"}]]
        )
        
        # 1. Распределение по типам зон
        if 'zone_type' in zones_df.columns:
            type_counts = zones_df['zone_type'].value_counts()
            fig.add_trace(go.Pie(
                labels=type_counts.index,
                values=type_counts.values,
                name="Zone Types"
            ), row=1, col=1)
        
        # 2. Распределение длительности
        if 'duration' in zones_df.columns:
            fig.add_trace(go.Histogram(
                x=zones_df['duration'],
                name="Duration",
                nbinsx=20
            ), row=1, col=2)
        
        # 3. Распределение доходности
        if 'price_return' in zones_df.columns:
            fig.add_trace(go.Histogram(
                x=zones_df['price_return'],
                name="Returns",
                nbinsx=20
            ), row=2, col=1)
        
        # 4. Временная линия зон
        if 'start_time' in zones_df.columns and 'duration' in zones_df.columns:
            fig.add_trace(go.Scatter(
                x=zones_df['start_time'] if 'start_time' in zones_df.columns else range(len(zones_df)),
                y=zones_df['duration'],
                mode='markers',
                name="Zone Timeline",
                marker=dict(
                    size=8,
                    color=zones_df['zone_type'].map({'bull': 'blue', 'bear': 'red'}) if 'zone_type' in zones_df.columns else 'blue'
                )
            ), row=2, col=2)
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_zones_distribution(self, zones: List[Dict], 
                                         feature: str, title: str, 
                                         **kwargs) -> go.Figure:
        """Создание графика распределения характеристик зон с помощью Plotly."""
        zones_df = pd.DataFrame(zones)
        
        if zones_df.empty or feature not in zones_df.columns:
            fig = go.Figure()
            fig.add_annotation(
                text=f"No data available for feature: {feature}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle'
            )
            fig.update_layout(title=title)
            return fig
        
        # Создаем подграфики
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=[f'{feature.title()} Distribution', f'{feature.title()} by Zone Type']
        )
        
        # Общее распределение
        fig.add_trace(go.Histogram(
            x=zones_df[feature],
            name=f"All {feature}",
            nbinsx=20,
            opacity=0.7
        ), row=1, col=1)
        
        # Распределение по типам зон
        if 'zone_type' in zones_df.columns:
            for zone_type in zones_df['zone_type'].unique():
                type_data = zones_df[zones_df['zone_type'] == zone_type][feature]
                fig.add_trace(go.Histogram(
                    x=type_data,
                    name=f"{zone_type.title()} {feature}",
                    nbinsx=15,
                    opacity=0.7
                ), row=1, col=2)
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            barmode='overlay'
        )
        
        return fig
    
    def _create_plotly_zones_correlation(self, zones_df: pd.DataFrame, 
                                        title: str, **kwargs) -> go.Figure:
        """Создание матрицы корреляций характеристик зон с помощью Plotly."""
        # Выбираем только числовые колонки
        numeric_columns = zones_df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_columns) < 2:
            fig = go.Figure()
            fig.add_annotation(
                text="Insufficient numeric data for correlation analysis",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle'
            )
            fig.update_layout(title=title)
            return fig
        
        # Вычисляем корреляции
        corr_matrix = zones_df[numeric_columns].corr()
        
        # Создаем heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmin=-1, zmax=1,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white'
        )
        
        return fig
    
    # Matplotlib реализации (упрощенные)
    def _create_matplotlib_zones_on_price(self, price_data: pd.DataFrame, 
                                         zones: List[Dict], title: str, 
                                         **kwargs) -> plt.Figure:
        """Создание графика цен с зонами с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Простой линейный график цен
        ax.plot(price_data.index, price_data['close'], label='Close Price', linewidth=1)
        
        # Добавляем зоны как вертикальные полосы
        for i, zone in enumerate(zones):
            if 'start_time' in zone and 'end_time' in zone:
                zone_type = zone.get('type', 'bull')
                color = 'lightblue' if zone_type == 'bull' else 'lightpink'
                
                ax.axvspan(zone['start_time'], zone['end_time'], 
                          alpha=self.default_config['opacity'], 
                          color=color, 
                          label=f"{zone_type.title()} Zone" if i == 0 else "")
        
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def _create_matplotlib_macd_zones(self, macd_data: pd.DataFrame, 
                                     zones: List[Dict], title: str, 
                                     **kwargs) -> plt.Figure:
        """Создание графика MACD с зонами с помощью Matplotlib."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # MACD
        ax1.plot(macd_data.index, macd_data['macd'], label='MACD', color='blue')
        ax1.plot(macd_data.index, macd_data['macd_signal'], label='Signal', color='red')
        ax1.set_title('MACD with Zones')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Гистограмма
        colors = ['green' if val >= 0 else 'red' for val in macd_data['macd_hist']]
        ax2.bar(macd_data.index, macd_data['macd_hist'], color=colors, alpha=0.7)
        ax2.set_title('Histogram')
        ax2.grid(True, alpha=0.3)
        
        # Добавляем зоны
        for zone in zones:
            if 'start_time' in zone and 'end_time' in zone:
                zone_type = zone.get('type', 'bull')
                color = 'lightblue' if zone_type == 'bull' else 'lightpink'
                
                ax1.axvspan(zone['start_time'], zone['end_time'], 
                           alpha=self.default_config['opacity'], color=color)
                ax2.axvspan(zone['start_time'], zone['end_time'], 
                           alpha=self.default_config['opacity'], color=color)
        
        plt.tight_layout()
        return fig
    
    def _create_matplotlib_zones_analysis(self, zones: List[Dict], 
                                         analysis_data: Dict[str, Any], 
                                         title: str, **kwargs) -> plt.Figure:
        """Создание графика анализа зон с помощью Matplotlib."""
        zones_df = pd.DataFrame(zones)
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        
        # 1. Распределение по типам
        if 'zone_type' in zones_df.columns:
            type_counts = zones_df['zone_type'].value_counts()
            ax1.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%')
            ax1.set_title('Zones by Type')
        
        # 2. Распределение длительности
        if 'duration' in zones_df.columns:
            ax2.hist(zones_df['duration'], bins=20, alpha=0.7)
            ax2.set_title('Duration Distribution')
            ax2.set_xlabel('Duration')
        
        # 3. Распределение доходности
        if 'price_return' in zones_df.columns:
            ax3.hist(zones_df['price_return'], bins=20, alpha=0.7)
            ax3.set_title('Return Distribution')
            ax3.set_xlabel('Return')
        
        # 4. Scatter plot длительность vs доходность
        if 'duration' in zones_df.columns and 'price_return' in zones_df.columns:
            if 'zone_type' in zones_df.columns:
                for zone_type in zones_df['zone_type'].unique():
                    type_data = zones_df[zones_df['zone_type'] == zone_type]
                    ax4.scatter(type_data['duration'], type_data['price_return'], 
                               label=zone_type.title(), alpha=0.7)
                ax4.legend()
            else:
                ax4.scatter(zones_df['duration'], zones_df['price_return'], alpha=0.7)
            ax4.set_xlabel('Duration')
            ax4.set_ylabel('Return')
            ax4.set_title('Duration vs Return')
        
        plt.suptitle(title)
        plt.tight_layout()
        return fig
    
    def _create_matplotlib_zones_distribution(self, zones: List[Dict], 
                                             feature: str, title: str, 
                                             **kwargs) -> plt.Figure:
        """Создание графика распределения с помощью Matplotlib."""
        zones_df = pd.DataFrame(zones)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Общее распределение
        if feature in zones_df.columns:
            ax1.hist(zones_df[feature], bins=20, alpha=0.7)
            ax1.set_title(f'{feature.title()} Distribution')
            ax1.set_xlabel(feature.title())
        
        # По типам зон
        if 'zone_type' in zones_df.columns and feature in zones_df.columns:
            for zone_type in zones_df['zone_type'].unique():
                type_data = zones_df[zones_df['zone_type'] == zone_type][feature]
                ax2.hist(type_data, bins=15, alpha=0.7, label=zone_type.title())
            ax2.set_title(f'{feature.title()} by Zone Type')
            ax2.set_xlabel(feature.title())
            ax2.legend()
        
        plt.suptitle(title)
        plt.tight_layout()
        return fig
    
    def _create_matplotlib_zones_correlation(self, zones_df: pd.DataFrame, 
                                            title: str, **kwargs) -> plt.Figure:
        """Создание матрицы корреляций с помощью Matplotlib."""
        # Выбираем только числовые колонки
        numeric_columns = zones_df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_columns) < 2:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, 'Insufficient numeric data for correlation analysis', 
                   ha='center', va='center')
            ax.set_title(title)
            return fig
        
        # Вычисляем корреляции
        corr_matrix = zones_df[numeric_columns].corr()
        
        # Создаем heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(corr_matrix.values, cmap='RdBu', vmin=-1, vmax=1)
        
        # Настраиваем оси
        ax.set_xticks(range(len(corr_matrix.columns)))
        ax.set_yticks(range(len(corr_matrix.columns)))
        ax.set_xticklabels(corr_matrix.columns, rotation=45)
        ax.set_yticklabels(corr_matrix.columns)
        
        # Добавляем значения
        for i in range(len(corr_matrix.columns)):
            for j in range(len(corr_matrix.columns)):
                text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                             ha="center", va="center", color="black")
        
        fig.colorbar(im)
        ax.set_title(title)
        plt.tight_layout()
        return fig


# Удобные функции
def plot_zones_on_chart(price_data: pd.DataFrame, zones_data, **kwargs):
    """
    Быстрое отображение зон на графике цен.
    
    Args:
        price_data: DataFrame с данными цен
        zones_data: Данные зон
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика
    """
    visualizer = ZoneVisualizer()
    return visualizer.plot_zones_on_price_chart(price_data, zones_data, **kwargs)


def plot_macd_zones_chart(macd_data: pd.DataFrame, zones_data, **kwargs):
    """
    Быстрое отображение зон на графике MACD.
    
    Args:
        macd_data: DataFrame с данными MACD
        zones_data: Данные зон
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика
    """
    visualizer = ZoneVisualizer()
    return visualizer.plot_macd_zones(macd_data, zones_data, **kwargs)


def analyze_zones_visually(zones_data, **kwargs):
    """
    Быстрый визуальный анализ зон.
    
    Args:
        zones_data: Данные зон
        **kwargs: Дополнительные параметры
    
    Returns:
        Объект графика
    """
    visualizer = ZoneVisualizer()
    return visualizer.plot_zones_analysis(zones_data, **kwargs)


# Экспорт
__all__ = [
    'ZoneChartBuilder',
    'ZoneVisualizer',
    'plot_zones_on_chart',
    'plot_macd_zones_chart',
    'analyze_zones_visually'
]
