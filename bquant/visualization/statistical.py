"""
Модуль статистических графиков BQuant

Предоставляет инструменты для создания статистических визуализаций:
- Гистограммы и распределения
- Диаграммы рассеяния  
- Корреляционные матрицы
- Box plots и violin plots
- Графики временных рядов
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

# Проверка доступности библиотек визуализации
try:
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.subplots import make_subplots
    import plotly.express as px
    import plotly.figure_factory as ff
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available - statistical plots will be limited")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from scipy import stats
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib/Seaborn not available - statistical plots will be limited")


class StatisticalPlots:
    """
    Класс для создания статистических графиков.
    """
    
    def __init__(self, backend: str = 'plotly', **kwargs):
        """
        Инициализация создателя статистических графиков.
        
        Args:
            backend: Библиотека для построения ('plotly' или 'matplotlib')
            **kwargs: Дополнительные параметры
        """
        self.backend = backend
        self.logger = get_logger(f"{__name__}.StatisticalPlots")
        
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
        
        # Настройки по умолчанию
        self.default_config = {
            'width': kwargs.get('width', 1000),
            'height': kwargs.get('height', 600),
            'color_scheme': kwargs.get('color_scheme', 'plotly'),
            'show_statistics': kwargs.get('show_statistics', True)
        }
        
        self.logger.info(f"Statistical plots initialized with {self.backend} backend")
    
    def create_histogram(self, data: Union[pd.Series, pd.DataFrame, np.ndarray],
                        title: str = "Histogram",
                        bins: int = 30,
                        column: str = None,
                        group_by: str = None,
                        **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание гистограммы.
        
        Args:
            data: Данные для гистограммы
            title: Заголовок графика
            bins: Количество бинов
            column: Колонка для анализа (если data - DataFrame)
            group_by: Колонка для группировки
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            return self._create_plotly_histogram(data, title, bins, column, group_by, **kwargs)
        else:
            return self._create_matplotlib_histogram(data, title, bins, column, group_by, **kwargs)
    
    def create_scatter_plot(self, data: pd.DataFrame,
                           x_column: str,
                           y_column: str,
                           title: str = "Scatter Plot",
                           color_column: str = None,
                           size_column: str = None,
                           **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание диаграммы рассеяния.
        
        Args:
            data: DataFrame с данными
            x_column: Колонка для оси X
            y_column: Колонка для оси Y
            title: Заголовок графика
            color_column: Колонка для цветового кодирования
            size_column: Колонка для размера точек
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            return self._create_plotly_scatter(data, x_column, y_column, title, 
                                             color_column, size_column, **kwargs)
        else:
            return self._create_matplotlib_scatter(data, x_column, y_column, title, 
                                                  color_column, size_column, **kwargs)
    
    def create_correlation_matrix(self, data: pd.DataFrame,
                                 title: str = "Correlation Matrix",
                                 method: str = 'pearson',
                                 **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание матрицы корреляций.
        
        Args:
            data: DataFrame с данными
            title: Заголовок графика
            method: Метод корреляции ('pearson', 'spearman', 'kendall')
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            return self._create_plotly_correlation(data, title, method, **kwargs)
        else:
            return self._create_matplotlib_correlation(data, title, method, **kwargs)
    
    def create_distribution_plot(self, data: Union[pd.Series, np.ndarray],
                                title: str = "Distribution Plot",
                                show_normal: bool = True,
                                **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание графика распределения с подгонкой кривой.
        
        Args:
            data: Данные для анализа
            title: Заголовок графика
            show_normal: Показать нормальное распределение
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            return self._create_plotly_distribution(data, title, show_normal, **kwargs)
        else:
            return self._create_matplotlib_distribution(data, title, show_normal, **kwargs)
    
    def create_box_plot(self, data: pd.DataFrame,
                       y_column: str,
                       x_column: str = None,
                       title: str = "Box Plot",
                       **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание box plot.
        
        Args:
            data: DataFrame с данными
            y_column: Колонка для анализа
            x_column: Колонка для группировки (опционально)
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            return self._create_plotly_box(data, y_column, x_column, title, **kwargs)
        else:
            return self._create_matplotlib_box(data, y_column, x_column, title, **kwargs)

    # Документационные алиасы
    def plot_correlation_matrix(self, data: pd.DataFrame,
                                title: str = "Correlation Matrix",
                                **kwargs) -> Union[go.Figure, plt.Figure]:
        return self.create_correlation_matrix(data, title=title, **kwargs)

    def plot_distribution(self, data: Union[pd.Series, np.ndarray],
                          title: str = "Distribution",
                          plot_type: str = "histogram",
                          **kwargs) -> Union[go.Figure, plt.Figure]:
        if plot_type == "histogram":
            return self.create_histogram(data, title=title, **kwargs)
        return self.create_distribution_plot(data, title=title, **kwargs)

    def plot_box_plot(self, data: List[List[float]],
                      labels: List[str],
                      title: str = "Box Plot",
                      **kwargs) -> Union[go.Figure, plt.Figure]:
        records = []
        for label, series in zip(labels, data):
            for value in series:
                records.append({"label": label, "value": value})

        frame = pd.DataFrame(records)
        return self.create_box_plot(frame, y_column="value", x_column="label", title=title, **kwargs)

    def plot_hypothesis_results(self, results: Dict[str, Any],
                                title: str = "Hypothesis Test Results",
                                **kwargs) -> Union[go.Figure, plt.Figure]:
        tests = []
        if isinstance(results, dict):
            tests = results.get("tests") or results.get("summary") or []

        names: List[str] = []
        values: List[float] = []
        colors: List[str] = []

        for entry in tests:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("test") or "Test"
                status = entry.get("passed") or entry.get("status")
                metric = entry.get("p_value") or entry.get("statistic")
            else:
                name = str(entry)
                status = None
                metric = None

            names.append(name)
            values.append(float(metric) if metric is not None else 0.0)
            colors.append("#2ecc71" if status in {True, "pass", "passed", "ok"} else "#e74c3c")

        if self.backend == 'plotly' and go is not None:
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=names,
                    y=values if any(values) else [1.0] * len(names),
                    marker_color=colors,
                    text=["PASS" if color == "#2ecc71" else "FAIL" for color in colors],
                    textposition="outside",
                    name="Hypothesis Tests",
                )
            )
            fig.update_layout(title=title, showlegend=False, height=self.default_config['height'])
            return fig

        if not MATPLOTLIB_AVAILABLE:
            raise AnalysisError("Matplotlib backend is required for hypothesis plotting")

        fig, ax = plt.subplots(figsize=(10, 4))  # type: ignore[attr-defined]
        ax.bar(names, values if any(values) else [1.0] * len(names), color=colors)  # type: ignore[attr-defined]
        ax.set_title(title)
        ax.set_ylabel("metric")
        return fig  # type: ignore[return-value]
    
    def create_time_series_plot(self, data: pd.DataFrame,
                               y_columns: List[str],
                               title: str = "Time Series",
                               show_trend: bool = False,
                               **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание графика временных рядов.
        
        Args:
            data: DataFrame с временным индексом
            y_columns: Колонки для отображения
            title: Заголовок графика
            show_trend: Показать линию тренда
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            return self._create_plotly_timeseries(data, y_columns, title, show_trend, **kwargs)
        else:
            return self._create_matplotlib_timeseries(data, y_columns, title, show_trend, **kwargs)
    
    # Plotly реализации
    def _create_plotly_histogram(self, data, title: str, bins: int, 
                                column: str, group_by: str, **kwargs) -> go.Figure:
        """Создание гистограммы с помощью Plotly."""
        # Подготовка данных
        if isinstance(data, pd.DataFrame):
            if column is None:
                # Используем первую числовую колонку
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) == 0:
                    raise ValueError("No numeric columns found")
                column = numeric_cols[0]
            
            plot_data = data[column].dropna()
        else:
            plot_data = pd.Series(data).dropna()
        
        fig = go.Figure()
        
        if group_by and isinstance(data, pd.DataFrame) and group_by in data.columns:
            # Группированная гистограмма
            for group in data[group_by].unique():
                group_data = data[data[group_by] == group][column].dropna()
                fig.add_trace(go.Histogram(
                    x=group_data,
                    name=str(group),
                    nbinsx=bins,
                    opacity=0.7
                ))
        else:
            # Простая гистограмма
            fig.add_trace(go.Histogram(
                x=plot_data,
                nbinsx=bins,
                name='Frequency'
            ))
        
        # Добавляем статистики если требуется
        if self.default_config['show_statistics']:
            stats_text = f"Mean: {plot_data.mean():.3f}<br>"
            stats_text += f"Std: {plot_data.std():.3f}<br>"
            stats_text += f"Count: {len(plot_data)}"
            
            fig.add_annotation(
                text=stats_text,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor='left', yanchor='top',
                bgcolor="white",
                bordercolor="black",
                borderwidth=1
            )
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            barmode='overlay' if group_by else 'group'
        )
        
        return fig
    
    def _create_plotly_scatter(self, data: pd.DataFrame, x_column: str, 
                              y_column: str, title: str, color_column: str, 
                              size_column: str, **kwargs) -> go.Figure:
        """Создание диаграммы рассеяния с помощью Plotly."""
        fig = go.Figure()
        
        # Основные данные
        scatter_kwargs = {
            'x': data[x_column],
            'y': data[y_column],
            'mode': 'markers',
            'name': 'Data Points'
        }
        
        # Цветовое кодирование
        if color_column and color_column in data.columns:
            scatter_kwargs['marker'] = dict(
                color=data[color_column],
                colorscale='viridis',
                showscale=True,
                colorbar=dict(title=color_column)
            )
        
        # Размер точек
        if size_column and size_column in data.columns:
            if 'marker' not in scatter_kwargs:
                scatter_kwargs['marker'] = {}
            scatter_kwargs['marker']['size'] = data[size_column]
            scatter_kwargs['marker']['sizemode'] = 'diameter'
            scatter_kwargs['marker']['sizeref'] = 2. * max(data[size_column]) / (20 ** 2)
        
        fig.add_trace(go.Scatter(**scatter_kwargs))
        
        # Добавляем линию тренда
        if kwargs.get('show_trendline', False):
            z = np.polyfit(data[x_column].dropna(), data[y_column].dropna(), 1)
            p = np.poly1d(z)
            
            fig.add_trace(go.Scatter(
                x=data[x_column],
                y=p(data[x_column]),
                mode='lines',
                name='Trend Line',
                line=dict(color='red', dash='dash')
            ))
        
        # Корреляция
        if self.default_config['show_statistics']:
            correlation = data[x_column].corr(data[y_column])
            fig.add_annotation(
                text=f"Correlation: {correlation:.3f}",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor='left', yanchor='top',
                bgcolor="white",
                bordercolor="black",
                borderwidth=1
            )
        
        fig.update_layout(
            title=title,
            xaxis_title=x_column,
            yaxis_title=y_column,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_correlation(self, data: pd.DataFrame, title: str, 
                                  method: str, **kwargs) -> go.Figure:
        """Создание матрицы корреляций с помощью Plotly."""
        # Выбираем только числовые колонки
        numeric_data = data.select_dtypes(include=[np.number])
        
        if numeric_data.empty:
            raise ValueError("No numeric columns found for correlation analysis")
        
        # Вычисляем корреляции
        corr_matrix = numeric_data.corr(method=method)
        
        # Создаем heatmap
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmin=-1, zmax=1,
            text=np.round(corr_matrix.values, 3),
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=f"{title} ({method.title()})",
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_distribution(self, data, title: str, show_normal: bool, 
                                   **kwargs) -> go.Figure:
        """Создание графика распределения с помощью Plotly."""
        data_series = pd.Series(data).dropna()
        
        # Создаем figure с подграфиками
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=['Histogram', 'Q-Q Plot'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Гистограмма
        fig.add_trace(go.Histogram(
            x=data_series,
            nbinsx=30,
            name='Data',
            opacity=0.7
        ), row=1, col=1)
        
        # Нормальное распределение если требуется
        if show_normal:
            x_range = np.linspace(data_series.min(), data_series.max(), 100)
            normal_dist = stats.norm.pdf(x_range, data_series.mean(), data_series.std())
            
            # Нормализуем к количеству точек
            normal_dist = normal_dist * len(data_series) * (data_series.max() - data_series.min()) / 30
            
            fig.add_trace(go.Scatter(
                x=x_range,
                y=normal_dist,
                mode='lines',
                name='Normal Distribution',
                line=dict(color='red', width=2)
            ), row=1, col=1)
        
        # Q-Q plot
        if MATPLOTLIB_AVAILABLE:
            try:
                # Используем scipy для Q-Q данных
                theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(data_series)))
                sample_quantiles = np.sort(data_series)
                
                fig.add_trace(go.Scatter(
                    x=theoretical_quantiles,
                    y=sample_quantiles,
                    mode='markers',
                    name='Q-Q Plot',
                    marker=dict(size=4)
                ), row=1, col=2)
                
                # Добавляем идеальную линию
                min_val = min(theoretical_quantiles.min(), sample_quantiles.min())
                max_val = max(theoretical_quantiles.max(), sample_quantiles.max())
                fig.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='Perfect Normal',
                    line=dict(color='red', dash='dash')
                ), row=1, col=2)
            except:
                # Fallback если scipy недоступен
                pass
        
        # Статистики
        if self.default_config['show_statistics']:
            stats_text = f"Mean: {data_series.mean():.3f}<br>"
            stats_text += f"Std: {data_series.std():.3f}<br>"
            stats_text += f"Skewness: {data_series.skew():.3f}<br>"
            stats_text += f"Kurtosis: {data_series.kurtosis():.3f}"
            
            fig.add_annotation(
                text=stats_text,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor='left', yanchor='top',
                bgcolor="white",
                bordercolor="black",
                borderwidth=1
            )
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    def _create_plotly_box(self, data: pd.DataFrame, y_column: str, 
                          x_column: str, title: str, **kwargs) -> go.Figure:
        """Создание box plot с помощью Plotly."""
        fig = go.Figure()
        
        if x_column and x_column in data.columns:
            # Группированный box plot
            for group in data[x_column].unique():
                group_data = data[data[x_column] == group][y_column].dropna()
                fig.add_trace(go.Box(
                    y=group_data,
                    name=str(group),
                    boxpoints='outliers'
                ))
        else:
            # Простой box plot
            fig.add_trace(go.Box(
                y=data[y_column].dropna(),
                name=y_column,
                boxpoints='outliers'
            ))
        
        fig.update_layout(
            title=title,
            yaxis_title=y_column,
            xaxis_title=x_column if x_column else '',
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white'
        )
        
        return fig
    
    def _create_plotly_timeseries(self, data: pd.DataFrame, y_columns: List[str], 
                                 title: str, show_trend: bool, **kwargs) -> go.Figure:
        """Создание графика временных рядов с помощью Plotly."""
        fig = go.Figure()
        
        for column in y_columns:
            if column in data.columns:
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=data[column],
                    mode='lines',
                    name=column,
                    line=dict(width=2)
                ))
                
                # Добавляем тренд если требуется
                if show_trend:
                    # Простая линейная регрессия
                    x_numeric = np.arange(len(data))
                    y_data = data[column].dropna()
                    x_clean = x_numeric[:len(y_data)]
                    
                    if len(x_clean) > 1:
                        z = np.polyfit(x_clean, y_data, 1)
                        p = np.poly1d(z)
                        
                        fig.add_trace(go.Scatter(
                            x=data.index,
                            y=p(x_numeric),
                            mode='lines',
                            name=f'{column} Trend',
                            line=dict(dash='dash', width=1)
                        ))
        
        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    
    # Matplotlib реализации (упрощенные)
    def _create_matplotlib_histogram(self, data, title: str, bins: int, 
                                    column: str, group_by: str, **kwargs) -> plt.Figure:
        """Создание гистограммы с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if isinstance(data, pd.DataFrame):
            if column is None:
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                column = numeric_cols[0] if len(numeric_cols) > 0 else data.columns[0]
            plot_data = data[column].dropna()
        else:
            plot_data = pd.Series(data).dropna()
        
        if group_by and isinstance(data, pd.DataFrame):
            for group in data[group_by].unique():
                group_data = data[data[group_by] == group][column].dropna()
                ax.hist(group_data, bins=bins, alpha=0.7, label=str(group))
            ax.legend()
        else:
            ax.hist(plot_data, bins=bins, alpha=0.7)
        
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        if self.default_config['show_statistics']:
            stats_text = f"Mean: {plot_data.mean():.3f}\nStd: {plot_data.std():.3f}"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white'))
        
        return fig
    
    def _create_matplotlib_scatter(self, data: pd.DataFrame, x_column: str, 
                                  y_column: str, title: str, color_column: str, 
                                  size_column: str, **kwargs) -> plt.Figure:
        """Создание диаграммы рассеяния с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        scatter_kwargs = {'alpha': 0.7}
        
        if color_column and color_column in data.columns:
            scatter_kwargs['c'] = data[color_column]
            scatter_kwargs['cmap'] = 'viridis'
        
        if size_column and size_column in data.columns:
            scatter_kwargs['s'] = data[size_column] * 10
        
        scatter = ax.scatter(data[x_column], data[y_column], **scatter_kwargs)
        
        if color_column:
            plt.colorbar(scatter, label=color_column)
        
        ax.set_xlabel(x_column)
        ax.set_ylabel(y_column)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        if self.default_config['show_statistics']:
            correlation = data[x_column].corr(data[y_column])
            ax.text(0.02, 0.98, f"Correlation: {correlation:.3f}", 
                   transform=ax.transAxes, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white'))
        
        return fig
    
    def _create_matplotlib_correlation(self, data: pd.DataFrame, title: str, 
                                      method: str, **kwargs) -> plt.Figure:
        """Создание матрицы корреляций с помощью Matplotlib."""
        numeric_data = data.select_dtypes(include=[np.number])
        corr_matrix = numeric_data.corr(method=method)
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        if MATPLOTLIB_AVAILABLE:
            sns.heatmap(corr_matrix, annot=True, cmap='RdBu', center=0, 
                       square=True, ax=ax, cbar_kws={"shrink": .8})
        else:
            im = ax.imshow(corr_matrix.values, cmap='RdBu', vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr_matrix.columns)))
            ax.set_yticks(range(len(corr_matrix.columns)))
            ax.set_xticklabels(corr_matrix.columns, rotation=45)
            ax.set_yticklabels(corr_matrix.columns)
            plt.colorbar(im)
        
        ax.set_title(f"{title} ({method.title()})")
        plt.tight_layout()
        return fig
    
    def _create_matplotlib_distribution(self, data, title: str, show_normal: bool, 
                                       **kwargs) -> plt.Figure:
        """Создание графика распределения с помощью Matplotlib."""
        data_series = pd.Series(data).dropna()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Гистограмма
        ax1.hist(data_series, bins=30, alpha=0.7, density=True)
        
        if show_normal and MATPLOTLIB_AVAILABLE:
            x_range = np.linspace(data_series.min(), data_series.max(), 100)
            normal_dist = stats.norm.pdf(x_range, data_series.mean(), data_series.std())
            ax1.plot(x_range, normal_dist, 'r-', linewidth=2, label='Normal Distribution')
            ax1.legend()
        
        ax1.set_title('Distribution')
        ax1.grid(True, alpha=0.3)
        
        # Q-Q plot
        if MATPLOTLIB_AVAILABLE:
            try:
                stats.probplot(data_series, dist="norm", plot=ax2)
                ax2.set_title('Q-Q Plot')
            except:
                ax2.text(0.5, 0.5, 'Q-Q Plot not available', ha='center', va='center')
        
        plt.suptitle(title)
        plt.tight_layout()
        return fig
    
    def _create_matplotlib_box(self, data: pd.DataFrame, y_column: str, 
                              x_column: str, title: str, **kwargs) -> plt.Figure:
        """Создание box plot с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if x_column and x_column in data.columns:
            if MATPLOTLIB_AVAILABLE:
                sns.boxplot(data=data, x=x_column, y=y_column, ax=ax)
            else:
                # Простая реализация без seaborn
                groups = data[x_column].unique()
                box_data = [data[data[x_column] == group][y_column].dropna() for group in groups]
                ax.boxplot(box_data, labels=groups)
        else:
            ax.boxplot(data[y_column].dropna())
        
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        return fig
    
    def _create_matplotlib_timeseries(self, data: pd.DataFrame, y_columns: List[str], 
                                     title: str, show_trend: bool, **kwargs) -> plt.Figure:
        """Создание графика временных рядов с помощью Matplotlib."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for column in y_columns:
            if column in data.columns:
                ax.plot(data.index, data[column], label=column, linewidth=2)
                
                if show_trend:
                    x_numeric = np.arange(len(data))
                    y_data = data[column].dropna()
                    if len(y_data) > 1:
                        z = np.polyfit(x_numeric[:len(y_data)], y_data, 1)
                        p = np.poly1d(z)
                        ax.plot(data.index, p(x_numeric), '--', 
                               label=f'{column} Trend', alpha=0.7)
        
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig


class DistributionPlotter(StatisticalPlots):
    """
    Специализированный класс для анализа распределений.
    """
    
    def plot_multiple_distributions(self, data: pd.DataFrame,
                                   columns: List[str],
                                   title: str = "Multiple Distributions",
                                   **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Сравнение нескольких распределений.
        
        Args:
            data: DataFrame с данными
            columns: Колонки для анализа
            title: Заголовок графика
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        if self.backend == 'plotly':
            fig = go.Figure()
            
            for column in columns:
                if column in data.columns:
                    fig.add_trace(go.Histogram(
                        x=data[column].dropna(),
                        name=column,
                        opacity=0.7,
                        nbinsx=30
                    ))
            
            fig.update_layout(
                title=title,
                barmode='overlay',
                width=self.default_config['width'],
                height=self.default_config['height'],
                template='plotly_white'
            )
            
            return fig
        
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for column in columns:
                if column in data.columns:
                    ax.hist(data[column].dropna(), alpha=0.7, label=column, bins=30)
            
            ax.set_title(title)
            ax.legend()
            ax.grid(True, alpha=0.3)
            return fig


# Удобные функции
def create_quick_histogram(data, title="Histogram", **kwargs):
    """Быстрое создание гистограммы."""
    plotter = StatisticalPlots()
    return plotter.create_histogram(data, title, **kwargs)


def create_quick_scatter(data: pd.DataFrame, x: str, y: str, **kwargs):
    """Быстрое создание диаграммы рассеяния."""
    plotter = StatisticalPlots()
    return plotter.create_scatter_plot(data, x, y, **kwargs)


def create_correlation_heatmap(data: pd.DataFrame, **kwargs):
    """Быстрое создание матрицы корреляций."""
    plotter = StatisticalPlots()
    return plotter.create_correlation_matrix(data, **kwargs)


# Экспорт
__all__ = [
    'StatisticalPlots',
    'DistributionPlotter',
    'create_quick_histogram',
    'create_quick_scatter',
    'create_correlation_heatmap'
]
