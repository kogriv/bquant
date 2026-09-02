"""
Модуль создания финансовых графиков BQuant

Предоставляет инструменты для создания различных типов финансовых графиков:
- Свечные графики (Candlestick)
- OHLC графики  
- Линейные графики цен
- Графики объемов
- Комбинированные графики с индикаторами
"""

import functools

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import warnings

from ..core.logging_config import get_logger
from ..core.exceptions import AnalysisError
from ..indicators.schema import resolve_role_columns
from ..data.processor import resolve_time_index

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


def themed(method):
    """Применить к готовой фигуре тему, о которой попросил вызывающий.

    Тему принимали три класса и не применял ни один: аргумент уходил в `**kwargs`
    и там оставался, а фигура выходила без темы. Светлая и тёмная давали побайтно
    одинаковый результат (G47).

    Умолчание сохранено намеренно: без явного `theme=` тема **не** применяется, и
    вывод остаётся тем же, что и до правки. Меняется только тот вызов, который о
    теме просил и до сих пор её не получал.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        requested = kwargs.pop('theme', None) or getattr(self, '_explicit_theme', None)
        figure = method(self, *args, **kwargs)
        if requested is None or figure is None:
            return figure
        return self.theme_manager.apply_theme_to_figure(figure, requested)

    return wrapper


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

        # Менеджер тем нужен каждому построителю: через него `@themed` применяет
        # тему к готовой фигуре. Незнакомое имя он отвергает, а не подменяет.
        from .themes import ChartThemes
        self.theme_manager = ChartThemes()
        self._explicit_theme = None
        
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
        """Поставить время из данных на индекс — или честно оставить позиционную ось.

        Разбор живёт в :func:`bquant.data.processor.resolve_time_index`; здесь
        только вызов. Своя копия этой логики тут была и чинилась отдельно в 0.0.8
        (она не знала про колонку ``time`` и **синтезировала** ось
        ``date_range('2024-01-01', …)``). Две копии одного разбора расходятся:
        одна научится понимать колонку, другая нет — и вторая начнёт врать.
        """
        prepared = resolve_time_index(data)
        if prepared is data and not isinstance(data.index, pd.DatetimeIndex):
            self.logger.warning(
                "No time column found; the X axis stays positional. "
                "Times are not invented."
            )
        return prepared

    #: Чтобы пин мог проверить, что слой графиков пользуется общим помощником,
    #: а не завёл себе вторую копию разбора.
    _prepare_datetime_index.__wrapped_helper__ = resolve_time_index


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

        # Имя темы проверяется здесь: отказ на незнакомом имени лучше, чем график,
        # который выглядит как тематизированный и им не является.
        theme = kwargs.get('theme')
        if theme is not None:
            self.theme_manager.get_theme(theme)
            self._explicit_theme = theme

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
    
    @themed
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
    
    @themed
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
    
    @themed
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
    
    @themed
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
    
    @themed
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
    
    @themed
    def plot_macd_with_zones(self, macd_data: pd.DataFrame, 
                           zones_data: List[Dict] = None,
                           title: str = "MACD with Zones",
                           column_schema=None,
                           columns: Optional[Dict[str, str]] = None,
                           **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Создание графика MACD с зонами.
        
        Args:
            macd_data: DataFrame с данными MACD
            zones_data: Данные зон (опционально)
            title: Заголовок графика
            column_schema: Схема ``(индикатор, роль) → колонка`` из результата
                анализа (``result.column_schema``). Предпочтительный способ:
                график берёт колонки по **ролям**, а не по угаданным именам.
            columns: Явное сопоставление ``{'line': ..., 'signal': ..., 'hist': ...}``
                для кадров, пришедших со стороны.
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        # Раньше здесь стоял список литералов `['macd', 'macd_signal',
        # 'macd_hist']`: график знал имена колонок наизусть и рисовал не то (или
        # отказывался), стоило индикатору быть настроенным иначе или прийти из
        # библиотеки. Теперь спрашиваются роли.
        resolved = resolve_role_columns(
            macd_data, ('line', 'signal', 'hist'),
            schema=column_schema, overrides=columns,
        )
        macd_data = self._prepare_datetime_index(macd_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_macd_with_zones(macd_data, zones_data, title, resolved, **kwargs)
        else:
            return self._create_matplotlib_macd_with_zones(macd_data, zones_data, title, resolved, **kwargs)

    @themed
    def plot_zones_over_indicator(self, data: pd.DataFrame,
                                  zones_data: List[Dict] = None,
                                  title: str = "Zones",
                                  column_schema=None,
                                  columns: Optional[Dict[str, str]] = None,
                                  **kwargs) -> Union[go.Figure, plt.Figure]:
        """Нарисовать зоны поверх того индикатора, который есть в кадре.

        :meth:`plot_macd_with_zones` требует тройку ролей ``line``/``signal``/``hist``
        и отказывается работать, если их нет. Но осциллятор не обязан быть MACD:
        RSI и AO объявляют **одну** роль ``value``, поэтому зоны, посчитанные по ним,
        нечем было показать — а универсальность пайплайна как раз в том, что зоны
        считаются по любому осциллятору.

        Метод спрашивает у кадра, что в нём вообще есть, и рисует это:

        * есть ``line``/``signal``/``hist`` → полноценный двухпанельный вид MACD;
        * есть одна роль (``value``, ``line`` или ``hist``) → одна панель с этим рядом.

        Отказ остаётся отказом: если по схеме не резолвится ни один осциллятор,
        поднимается ``ValueError`` — рисовать «что-нибудь похожее» нельзя, иначе
        график начнёт утверждать то, чего никто не считал.

        Args:
            data: кадр с посчитанным индикатором (``result.data``)
            zones_data: зоны (``result.zones``) — объекты ``ZoneInfo`` или словари
            title: заголовок
            column_schema: схема ``(индикатор, роль) → колонка`` из результата анализа
            columns: явное сопоставление роли на колонку для чужих кадров

        Returns:
            Объект графика
        """
        try:
            resolved = resolve_role_columns(
                data, ('line', 'signal', 'hist'),
                schema=column_schema, overrides=columns,
            )
        except ValueError:
            resolved = None

        if resolved is not None:
            return self.plot_macd_with_zones(
                data, zones_data=zones_data, title=title,
                column_schema=column_schema, columns=columns, **kwargs
            )

        single = None
        for role in ('value', 'line', 'hist'):
            try:
                single = resolve_role_columns(
                    data, (role,), schema=column_schema, overrides=columns,
                )
                break
            except ValueError:
                continue

        if single is None:
            raise ValueError(
                "No oscillator to draw: none of the roles line/signal/hist, value "
                "or hist resolved against this frame. Pass `column_schema` from the "
                "analysis result, or name the column explicitly via `columns`."
            )

        prepared = self._prepare_datetime_index(data)
        role, column = next(iter(single.items()))

        if self.backend == 'plotly':
            return self._create_plotly_zones_over_series(
                prepared, zones_data, title, column, role, **kwargs
            )
        raise NotImplementedError(
            "plot_zones_over_indicator is implemented for the plotly backend only"
        )

    def _zone_shading_colors(self, zones_data: List[Dict]):
        """Сопоставление зоны и цвета по ОБЪЯВЛЕННОЙ полярности её типа."""

        from ..analysis.zones.detection import resolve_vocabulary

        try:
            vocabulary = resolve_vocabulary(zones_data)
        except Exception as exc:  # pragma: no cover - защита от чужой формы входа
            self.logger.debug(f"Could not resolve zone vocabulary: {exc}")
            vocabulary = None

        palette = {1: 'lightgreen', -1: 'lightpink', 0: 'lightgrey', None: 'lightblue'}
        return vocabulary, palette

    @staticmethod
    def _zone_bounds(zone):
        """Границы зоны — одинаково для ``ZoneInfo`` и для словаря."""

        if isinstance(zone, dict):
            return zone.get('start_time'), zone.get('end_time'), zone.get('type')
        return (getattr(zone, 'start_time', None),
                getattr(zone, 'end_time', None),
                getattr(zone, 'type', None))

    @staticmethod
    def _bound_on_axis(bound, axis) -> Any:
        """Перевести границу зоны в координату той оси, что реально нарисована.

        ``ZoneInfo.start_time``/``end_time`` — это **позиция в кадре**, если анализ
        шёл по кадру с ``RangeIndex`` (а ``get_sample_data()`` отдаёт именно такой:
        время лежит в колонке ``time``). Стоит поставить на график временную ось, и
        целое ``0`` читается plotly как эпоха — зона уезжает в 1970 год, за левый
        край. Прямоугольники при этом **есть**, и их ровно столько, сколько зон, так
        что проверка «зоны размечены» проходит, а размечено не то место.

        Поэтому позиция переводится через сам индекс, а не подставляется как есть.
        """
        if axis is None or not isinstance(axis, pd.DatetimeIndex):
            return bound
        if isinstance(bound, (pd.Timestamp, datetime)):
            return bound
        try:
            position = int(bound)
        except (TypeError, ValueError):
            return bound
        if 0 <= position < len(axis):
            return axis[position]
        # Позиция вне кадра — рисовать нечего; пусть лучше зона не будет
        # закрашена, чем будет закрашена наугад.
        return None

    def _shade_zones(self, fig, zones_data: List[Dict], row: int = 1, col: int = 1,
                     axis=None) -> None:
        """Закрасить зоны на указанной панели фигуры.

        Args:
            axis: индекс кадра, который нарисован. Нужен, чтобы позиционные
                границы зон легли на временную ось, а не на эпоху.
        """

        if not zones_data:
            return

        vocabulary, palette = self._zone_shading_colors(zones_data)

        for zone in zones_data:
            start_time, end_time, zone_type = self._zone_bounds(zone)
            if start_time is None or end_time is None:
                continue
            x0 = self._bound_on_axis(start_time, axis)
            x1 = self._bound_on_axis(end_time, axis)
            if x0 is None or x1 is None:
                continue
            fig.add_vrect(
                x0=x0,
                x1=x1,
                fillcolor=palette.get(
                    vocabulary.polarity_of(zone_type) if vocabulary else None,
                    palette[None],
                ),
                opacity=0.3,
                layer="below",
                line_width=0,
                row=row, col=col,
            )

    def _create_plotly_zones_over_series(self, data: pd.DataFrame,
                                         zones_data: List[Dict], title: str,
                                         column: str, role: str,
                                         **kwargs) -> go.Figure:
        """Одна панель: ряд осциллятора и закрашенные зоны поверх него."""

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[column],
            mode='lines',
            name=str(column),
            line=dict(color='blue', width=2),
        ))

        self._shade_zones(fig, zones_data, axis=data.index)

        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            template='plotly_white',
            showlegend=True,
            yaxis_title=role,
        )
        return fig
    
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
                                     columns: Dict[str, str],
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
            y=macd_data[columns['line']],
            mode='lines',
            name='MACD',
            line=dict(color='blue', width=2)
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=macd_data.index,
            y=macd_data[columns['signal']],
            mode='lines',
            name='Signal',
            line=dict(color='red', width=2)
        ), row=1, col=1)
        
        # Гистограмма
        colors = ['green' if val >= 0 else 'red' for val in macd_data[columns['hist']]]
        fig.add_trace(go.Bar(
            x=macd_data.index,
            y=macd_data[columns['hist']],
            name='Histogram',
            marker_color=colors,
            opacity=0.7
        ), row=2, col=1)
        
        # Цвет зоны следует ОБЪЯВЛЕННОЙ ПОЛЯРНОСТИ её типа, а не имени: раньше здесь
        # стояло `'lightblue' if zone_type == 'bull' else 'lightpink'`, и зона любого
        # другого словаря (`overbought`, `regime_a`, …) молча окрашивалась как
        # медвежья — график сообщал направление, которого никто не объявлял.
        # Сама разметка вынесена в `_shade_zones`, чтобы одинаково работать и здесь,
        # и на одноряднoм графике для осцилляторов с единственной ролью `value`.
        self._shade_zones(fig, zones_data, row=1, col=1, axis=macd_data.index)


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
                                          columns: Dict[str, str],
                                          **kwargs) -> plt.Figure:
        """Создание графика MACD с зонами с помощью Matplotlib."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # MACD
        ax1.plot(macd_data.index, macd_data[columns['line']], label='MACD', color='blue')
        ax1.plot(macd_data.index, macd_data[columns['signal']], label='Signal', color='red')
        ax1.set_title('MACD')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Гистограмма
        colors = ['green' if val >= 0 else 'red' for val in macd_data[columns['hist']]]
        ax2.bar(macd_data.index, macd_data[columns['hist']], color=colors, alpha=0.7)
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


def create_zones_chart(data: pd.DataFrame, zones_data=None, **kwargs):
    """
    Быстрое создание графика зон поверх посчитанного индикатора.

    В отличие от :func:`create_price_chart`, ошибки **не глотаются**: если
    осциллятор не резолвится по схеме, поднимается ``ValueError``. Молча вернуть
    ``None`` здесь нельзя — вызывающий не отличит «нечего рисовать» от «нарисовано
    не то», а именно на этом различии и держится правдивость графика.

    Args:
        data: кадр с посчитанным индикатором (``result.data``)
        zones_data: зоны (``result.zones``)
        **kwargs: ``title``, ``column_schema``, ``columns``

    Returns:
        Объект графика
    """
    charts = FinancialCharts()
    return charts.plot_zones_over_indicator(data, zones_data=zones_data, **kwargs)


# Экспорт
__all__ = [
    'ChartBuilder',
    'FinancialCharts',
    'create_candlestick_chart',
    'create_price_chart',
    'create_zones_chart',
    'PLOTLY_AVAILABLE',
    'MATPLOTLIB_AVAILABLE'
]
