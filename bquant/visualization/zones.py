"""Модуль визуализации зон BQuant."""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..core.logging_config import get_logger
from ..core.exceptions import AnalysisError
from ..analysis.zones.models import ZoneInfo
from .utils import find_all_gaps

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
        
        # Тихий вывод: детально логируем только на DEBUG
        self.logger.debug(f"Zone chart builder initialized with {self.backend} backend")
    
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
                    zone_dict = asdict(zone)
                    self.logger.debug(f"asdict result keys: {list(zone_dict.keys())}")
                    self.logger.debug(f"asdict start_time: {zone_dict.get('start_time')}, end_time: {zone_dict.get('end_time')}")
                    normalized.append(zone_dict)
                elif hasattr(zone, "__dict__"):
                    normalized.append({key: getattr(zone, key) for key in dir(zone)
                                       if not key.startswith("_") and not callable(getattr(zone, key))})
                else:
                    raise ValueError("Unsupported zone object type: %r" % (type(zone),))

            return normalized
        else:
            raise ValueError("zones_data must be DataFrame or list of dicts")

    def _normalize_zone(self, zone: Union[Dict[str, Any], ZoneInfo, Any]) -> Dict[str, Any]:
        """Приведение зоны к словарю с сохранением метаданных ZoneInfo."""

        if isinstance(zone, dict):
            return zone

        if isinstance(zone, ZoneInfo):
            return {
                'zone_id': zone.zone_id,
                'type': zone.type,
                'start_idx': zone.start_idx,
                'end_idx': zone.end_idx,
                'start_time': zone.start_time,
                'end_time': zone.end_time,
                'duration': zone.duration,
                'data': zone.data,
                'features': zone.features,
                'indicator_context': zone.indicator_context,
            }

        normalized = self._prepare_zone_data([zone])
        if not normalized:
            raise ValueError("Unable to normalize zone object")
        return normalized[0]

    def _get_zone_window(self,
                         price_data: pd.DataFrame,
                         zone: Dict[str, Any],
                         context_bars: int,
                         max_bars: Optional[int] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Определение окна данных вокруг зоны с учетом контекста."""

        if price_data is None or price_data.empty:
            raise ValueError("price_data is empty - cannot build zone window")

        index = price_data.index
        total_bars = len(price_data)

        def _safe_idx(idx_value: Optional[int], fallback_time: Optional[datetime]) -> Optional[int]:
            if idx_value is not None:
                try:
                    idx_int = int(idx_value)
                    if 0 <= idx_int < total_bars:
                        return idx_int
                except (TypeError, ValueError):
                    pass

            if fallback_time is None:
                return None

            if isinstance(index, pd.DatetimeIndex):
                try:
                    loc = index.get_loc(fallback_time)
                    if isinstance(loc, slice):
                        return loc.start
                    return int(loc)
                except KeyError:
                    position = index.get_indexer([pd.Timestamp(fallback_time)], method='nearest')
                    if position.size and position[0] != -1:
                        return int(position[0])
            return None

        start_idx = _safe_idx(zone.get('start_idx'), zone.get('start_time'))
        end_idx = _safe_idx(zone.get('end_idx'), zone.get('end_time'))

        if start_idx is None or end_idx is None:
            self.logger.warning(
                "Zone %s is missing start/end indices; using entire price range",
                zone.get('zone_id', '?'),
            )
            start_idx = 0
            end_idx = total_bars - 1

        zone_left = max(0, min(start_idx, end_idx))
        zone_right = min(total_bars - 1, max(start_idx, end_idx))

        left_idx = max(0, zone_left - int(context_bars))
        right_idx = min(total_bars - 1, zone_right + int(context_bars))

        window = price_data.iloc[left_idx:right_idx + 1]
        truncated = False
        truncation_reason = None

        if max_bars and len(window) > max_bars:
            truncated = True
            truncation_reason = 'max_bars'
            keep = max(1, max_bars)
            self.logger.warning(
                "Zone window truncated to %s bars (limit %s) for zone %s",
                keep,
                max_bars,
                zone.get('zone_id', '?'),
            )
            # Сохраняем правую часть (последние бары)
            window = window.iloc[-keep:]
            left_idx = right_idx - len(window) + 1

        return window, {
            'start_idx': start_idx,
            'end_idx': end_idx,
            'left_idx': left_idx,
            'right_idx': right_idx,
            'truncated': truncated,
            'truncation_reason': truncation_reason,
            'zone_left': zone_left,
            'zone_right': zone_right,
        }

    def _detect_indicators_from_features(self,
                                         zone: Dict[str, Any],
                                         data: Optional[pd.DataFrame]) -> List[str]:
        """Определение индикаторных колонок для отображения."""

        if data is None or data.empty:
            return []

        candidate_columns: List[str] = []
        indicator_context = zone.get('indicator_context') or {}
        features = zone.get('features') or {}

        def _extend_from(value: Any) -> None:
            if isinstance(value, str):
                candidate_columns.append(value)
            elif isinstance(value, Iterable):
                for item in value:
                    if isinstance(item, str):
                        candidate_columns.append(item)

        for key in ('detection_indicator', 'signal_line', 'indicator_columns'):
            _extend_from(indicator_context.get(key))

        for key in ('primary_indicator', 'secondary_indicator', 'indicator_columns', 'indicators'):
            _extend_from(features.get(key))

        standard_columns = {'open', 'high', 'low', 'close', 'volume', 'adj_close'}

        # Отбираем только колонки, присутствующие в данных
        detected = []
        for column in candidate_columns:
            if column in data.columns and column not in detected and column not in standard_columns:
                detected.append(column)

        if not detected:
            # Попытка автоматически найти индикаторы
            non_price_columns = [
                col for col in data.columns
                if col not in standard_columns and data[col].dtype.kind in {'f', 'i'}
            ]
            detected.extend(non_price_columns[:2])

        return detected

    def _filter_zones_by_date(self,
                              zones: List[Dict[str, Any]],
                              date_range: Optional[Tuple[datetime, datetime]]) -> List[Dict[str, Any]]:
        """Фильтрация зон по диапазону дат."""

        if not date_range:
            return zones

        start_range, end_range = date_range
        filtered: List[Dict[str, Any]] = []
        for zone in zones:
            start_time = zone.get('start_time')
            end_time = zone.get('end_time')
            if start_time is None or end_time is None:
                continue

            if end_time >= start_range and start_time <= end_range:
                filtered.append(zone)

        if len(filtered) < len(zones):
            self.logger.info(
                "Filtered zones by date range: kept %s of %s",
                len(filtered),
                len(zones),
            )

        return filtered


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
            'show_zone_labels': kwargs.get('show_zone_labels', False),
            'show_zone_stats': kwargs.get('show_zone_stats', True),
            'opacity': kwargs.get('opacity', 0.3),
            'zone_detail_context': kwargs.get('zone_detail_context', 40),
            'max_zone_detail_bars': kwargs.get('max_zone_detail_bars', 500),
            'comparison_context': kwargs.get('comparison_context', 30),
            'max_comparison_zones': kwargs.get('max_comparison_zones', 6),
            'volume_panel_height': kwargs.get('volume_panel_height', 0.25),
            'indicator_palette': kwargs.get('indicator_palette', [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
            ]),
        }
    
    def plot_zones_on_price_chart(self, price_data: pd.DataFrame,
                                 zones_data: Union[List[Dict], pd.DataFrame],
                                 title: str = "Price Chart with Zones",
                                 show_indicators: bool = False,
                                 indicator_columns: Optional[List[str]] = None,
                                 indicator_chart_types: Optional[Dict[str, str]] = None,
                                 show_gap_lines: bool = False,
                                 xaxis_num_ticks: int = 16,
                                 time_axis_mode: str = 'dense',
                                 **kwargs) -> Union[go.Figure, plt.Figure]:
        """
        Отображение зон на графике цен.
        
        Args:
            price_data: DataFrame с данными цен (OHLCV)
            zones_data: Данные зон
            title: Заголовок графика
            show_indicators: Показывать ли индикаторы в отдельной панели (по умолчанию False)
            indicator_columns: Список колонок индикаторов для отображения.
                               Если None, автоматически определяется из indicator_context зон
            indicator_chart_types: Словарь {колонка: тип} для указания типа отображения каждого индикатора.
                                   Типы: 'line' (линия) или 'bar' (столбики). По умолчанию все 'line'.
                                   Пример: {'macd_hist': 'bar', 'rsi': 'line'}
            show_gap_lines: Показывать ли вертикальные пунктирные линии для разрывов (выходные) (по умолчанию False)
            xaxis_num_ticks: Количество меток на оси X (по умолчанию 16). Автоматически корректируется
                            на основе диапазона данных для оптимальной читаемости.
            time_axis_mode: Режим оси времени ('dense' или 'timeseries'). 'dense' для плотного графика,
                            'timeseries' для реальной временной шкалы с пропуском выходных.
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        zones = self._prepare_zone_data(zones_data)
        
        if self.backend == 'plotly':
            return self._create_plotly_zones_on_price(
                price_data, zones, title, 
                show_indicators=show_indicators,
                indicator_columns=indicator_columns,
                indicator_chart_types=indicator_chart_types,
                show_gap_lines=show_gap_lines,
                xaxis_num_ticks=xaxis_num_ticks,
                time_axis_mode=time_axis_mode,
                **kwargs
            )
        else:
            return self._create_matplotlib_zones_on_price(price_data, zones, title, **kwargs)

    def plot_zone_detail(self, price_data: pd.DataFrame,
                         zone: Union[Dict[str, Any], ZoneInfo, Any],
                         context_bars: int = 20,
                         title: str = "Zone Detail",
                         **kwargs) -> Union[go.Figure, plt.Figure]:
        """Детализированный просмотр отдельной зоны."""

        if price_data is None or price_data.empty:
            raise ValueError("price_data must be a non-empty DataFrame")

        zone_dict = self._normalize_zone(zone)
        context = kwargs.get('context_bars', context_bars)
        if context is None:
            context = self.default_config['zone_detail_context']

        max_bars = kwargs.get('max_zone_detail_bars', self.default_config['max_zone_detail_bars'])

        window_df, window_meta = self._get_zone_window(price_data, zone_dict, context, max_bars=max_bars)

        zone_data = zone_dict.get('data')
        indicator_source: Optional[pd.DataFrame] = None
        if isinstance(zone_data, pd.DataFrame) and not zone_data.empty:
            indicator_source = zone_data.reindex(window_df.index)
        else:
            indicator_source = window_df

        indicator_columns = self._detect_indicators_from_features(zone_dict, indicator_source)
        indicator_data = pd.DataFrame(index=window_df.index)
        if indicator_columns:
            indicator_data = indicator_source[indicator_columns].copy()
            self.logger.debug(
                "Detected indicators for zone %s: %s",
                zone_dict.get('zone_id', '?'),
                indicator_columns,
            )

        if window_meta['truncated'] and window_meta['truncation_reason'] == 'max_bars':
            self.logger.warning(
                "Zone %s window clipped to last %s bars due to configuration limit",
                zone_dict.get('zone_id', '?'),
                len(window_df),
            )

        if self.backend == 'plotly':
            return self._create_plotly_zone_detail(
                window_df,
                zone_dict,
                indicator_data,
                title,
                window_meta,
                **kwargs,
            )
        else:
            return self._create_matplotlib_zone_detail(
                window_df,
                zone_dict,
                indicator_data,
                title,
                window_meta,
                **kwargs,
            )

    def plot_zones_comparison(self, price_data: pd.DataFrame,
                              zones_data: Union[List[Dict], pd.DataFrame, List[Any]],
                              max_zones: int = 5,
                              date_range: Optional[Tuple[datetime, datetime]] = None,
                              title: str = "Zones Comparison",
                              **kwargs) -> Union[go.Figure, plt.Figure]:
        """Сравнение нескольких зон на ценовом графике."""

        if price_data is None or price_data.empty:
            raise ValueError("price_data must be a non-empty DataFrame")

        # Нормализуем входные зоны
        if isinstance(zones_data, pd.DataFrame):
            normalized_zones = self._prepare_zone_data(zones_data)
        else:
            normalized_zones = [self._normalize_zone(zone) for zone in list(zones_data or [])]

        if not normalized_zones:
            self.logger.warning("No zones provided for comparison - returning empty chart")
            return self.plot_zones_on_price_chart(price_data, [], title=title, **kwargs)

        filtered_zones = self._filter_zones_by_date(normalized_zones, date_range)

        if not filtered_zones:
            self.logger.warning("No zones fall inside the requested date range")
            return self.plot_zones_on_price_chart(price_data, [], title=title, **kwargs)

        max_allowed = kwargs.get('max_zones', max_zones)
        if max_allowed is None:
            max_allowed = self.default_config['max_comparison_zones']

        if len(filtered_zones) > max_allowed:
            self.logger.warning(
                "Limiting zones comparison to first %s zones out of %s",
                max_allowed,
                len(filtered_zones),
            )
            filtered_zones = filtered_zones[:max_allowed]

        context = kwargs.get('comparison_context', self.default_config['comparison_context'])

        zone_windows: List[Dict[str, Any]] = []
        global_left = len(price_data)
        global_right = 0

        for zone in filtered_zones:
            window_df, window_meta = self._get_zone_window(price_data, zone, context, max_bars=None)
            zone_data = zone.get('data')
            if isinstance(zone_data, pd.DataFrame) and not zone_data.empty:
                indicator_source = zone_data.reindex(window_df.index)
            else:
                indicator_source = price_data.reindex(window_df.index)

            indicator_columns = self._detect_indicators_from_features(zone, indicator_source)
            indicators_df = pd.DataFrame(index=window_df.index)
            if indicator_columns:
                indicators_df = indicator_source[indicator_columns].copy()

            zone_windows.append({
                'zone': zone,
                'window': window_df,
                'meta': window_meta,
                'indicators': indicators_df,
            })

            global_left = min(global_left, window_meta['left_idx'])
            global_right = max(global_right, window_meta['right_idx'])

        if global_left > global_right:
            global_left, global_right = 0, len(price_data) - 1

        global_window = price_data.iloc[global_left:global_right + 1]

        if self.backend == 'plotly':
            return self._create_plotly_zones_comparison(
                global_window,
                zone_windows,
                title,
                **kwargs,
            )
        else:
            return self._create_matplotlib_zones_comparison(
                global_window,
                zone_windows,
                title,
                **kwargs,
            )

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
                                     show_indicators: bool = False,
                                     indicator_columns: Optional[List[str]] = None,
                                     indicator_chart_types: Optional[Dict[str, str]] = None,
                                     show_gap_lines: bool = False,
                                     xaxis_num_ticks: int = 16,
                                     time_axis_mode: str = 'dense',
                                     **kwargs) -> go.Figure:
        """Создание графика цен с зонами с помощью Plotly."""
        
        # Определяем, показывать ли индикаторы
        show_indicators = kwargs.get('show_indicators', show_indicators)

        # Определяем колонки индикаторов для отображения
        if show_indicators:
            if indicator_columns is None:
                indicator_columns = []
                seen_indicators = set()
                for zone in zones:
                    indicator_context = zone.get('indicator_context') or {}
                    detection_indicator = indicator_context.get('detection_indicator')
                    if (detection_indicator and 
                        detection_indicator not in seen_indicators and
                        detection_indicator in price_data.columns):
                        indicator_columns.append(detection_indicator)
                        seen_indicators.add(detection_indicator)
                        if len(indicator_columns) >= 3:
                            break
            if indicator_columns:
                indicator_columns = [
                    col for col in indicator_columns 
                    if col in price_data.columns and col not in {'open', 'high', 'low', 'close', 'volume', 'adj_close'}
                ]
            if not indicator_columns:
                show_indicators = False
        
        # Определяем количество панелей
        rows = 2 if show_indicators else 1
        row_heights = [1.0]
        if rows == 2:
            indicator_panel_height = kwargs.get('indicator_panel_height', 0.3)
            row_heights = [1 - indicator_panel_height, indicator_panel_height]
        
        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=row_heights,
        )

        # --- РЕЖИМ TIMESERIES ---
        if time_axis_mode == 'timeseries':
            # Находим разрывы для маски
            gap_mask = find_all_gaps(price_data.index)
            
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
            ), row=1, col=1)

            # Добавляем зоны
            for i, zone in enumerate(zones):
                if 'start_time' in zone and 'end_time' in zone:
                    zone_type = zone.get('type', 'bull')
                    color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
                    y0 = price_data['low'].min()
                    y1 = price_data['high'].max()
                    fig.add_vrect(
                        x0=zone['start_time'],
                        x1=zone['end_time'],
                        fillcolor=color_config['fill'],
                        line=dict(color=color_config['line'], width=1),
                        layer="below",
                        row=1, col=1
                    )
                    if self.default_config['show_zone_labels']:
                        fig.add_annotation(
                            x=zone['start_time'],
                            y=y1,
                            text=f"{zone_type.title()} Zone {i+1}",
                            showarrow=False,
                            font=dict(size=10),
                            bgcolor="white",
                            opacity=0.8,
                            row=1, col=1
                        )

            # Добавляем индикаторы на вторую панель (если есть)
            if show_indicators and indicator_columns:
                chart_types = indicator_chart_types or {}
                default_chart_type = lambda col: 'bar' if 'hist' in col.lower() else 'line'
                palette = kwargs.get('indicator_palette', self.default_config['indicator_palette'])
                for i, column in enumerate(indicator_columns):
                    color = palette[i % len(palette)]
                    chart_type = chart_types.get(column, default_chart_type(column))
                    if chart_type == 'bar':
                        fig.add_trace(go.Bar(
                            x=price_data.index,
                            y=price_data[column],
                            name=column,
                            marker_color=color,
                            opacity=0.7
                        ), row=2, col=1)
                    else:
                        fig.add_trace(go.Scatter(
                            x=price_data.index,
                            y=price_data[column],
                            mode='lines',
                            name=column,
                            line=dict(color=color, width=1.6)
                        ), row=2, col=1)
                if len(indicator_columns) == 1:
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
                fig.update_yaxes(title_text="Indicator", row=2, col=1)

            # Применяем маску разрывов к обеим панелям
            # Для Plotly rangebreaks: каждый разрыв должен быть отдельным dict
            # Формат: [dict(bounds=[start, end]), dict(bounds=[start2, end2]), ...]
            if gap_mask:
                # Преобразуем список списков в список словарей для Plotly
                rangebreaks = [dict(bounds=gap) for gap in gap_mask]
                fig.update_xaxes(
                    type='date',
                    rangebreaks=rangebreaks,
                    row=1,
                    col=1
                )
                if show_indicators and indicator_columns:
                    fig.update_xaxes(
                        type='date',
                        rangebreaks=rangebreaks,
                        row=2,
                        col=1
                    )
            else:
                # Если нет разрывов, просто указываем тип оси
                fig.update_xaxes(type='date', row=1, col=1)
                if show_indicators and indicator_columns:
                    fig.update_xaxes(type='date', row=2, col=1)

            # Настройка layout для режима timeseries
            fig.update_layout(
                title=title,
                width=self.default_config['width'],
                height=self.default_config['height'],
                xaxis_rangeslider_visible=False,
                template='plotly_white'
            )
            
            # Добавляем метаинформацию о данных (symbol, timeframe, source)
            chart_info = kwargs.get('chart_info', {})
            if chart_info:
                info_parts = []
                if 'symbol' in chart_info:
                    info_parts.append(f"<b>{chart_info['symbol']}</b>")
                if 'timeframe' in chart_info:
                    info_parts.append(chart_info['timeframe'])
                if 'source' in chart_info:
                    info_parts.append(f"<i>{chart_info['source']}</i>")
                if info_parts:
                    info_text = " | ".join(info_parts)
                    fig.add_annotation(
                        text=info_text,
                        xref="paper",
                        yref="paper",
                        x=1.0,
                        y=1.02,
                        xanchor='right',
                        yanchor='bottom',
                        showarrow=False,
                        font=dict(size=11, color='#666'),
                        bgcolor='rgba(255,255,255,0.8)',
                        borderpad=4
                    )
            
            return fig

        # --- РЕЖИМ DENSE ---
        else:
            x_positions = list(range(len(price_data)))
            x_dates = price_data.index
            date_to_position = {date: pos for pos, date in enumerate(x_dates)}

            fig.add_trace(go.Candlestick(
                x=x_positions,
                open=price_data['open'],
                high=price_data['high'],
                low=price_data['low'],
                close=price_data['close'],
                name='Price',
                increasing_line_color='#00ff88',
                decreasing_line_color='#ff4444'
            ), row=1, col=1)

            for i, zone in enumerate(zones):
                if 'start_time' in zone and 'end_time' in zone:
                    zone_type = zone.get('type', 'bull')
                    color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
                    start_time = zone['start_time']
                    end_time = zone['end_time']
                    x0_pos, x1_pos = None, None
                    if start_time in date_to_position:
                        x0_pos = date_to_position[start_time]
                    else:
                        try:
                            x0_pos = x_dates.get_indexer([start_time], method='nearest')[0]
                            if x0_pos < 0: x0_pos = 0
                        except Exception: x0_pos = 0
                    if end_time in date_to_position:
                        x1_pos = date_to_position[end_time]
                    else:
                        try:
                            x1_pos = x_dates.get_indexer([end_time], method='nearest')[0]
                            if x1_pos < 0 or x1_pos >= len(x_positions): x1_pos = len(x_positions) - 1
                        except Exception: x1_pos = len(x_positions) - 1
                    y0 = price_data['low'].min()
                    y1 = price_data['high'].max()
                    fig.add_shape(type="rect", x0=x0_pos, y0=y0, x1=x1_pos, y1=y1, fillcolor=color_config['fill'], line=dict(color=color_config['line'], width=1), layer="below", xref="x", row=1, col=1)
                    if self.default_config['show_zone_labels']:
                        fig.add_annotation(x=x0_pos, y=y1, text=f"{zone_type.title()} Zone {i+1}", showarrow=False, font=dict(size=10), bgcolor="white", opacity=0.8, xref="x", row=1, col=1)

            num_ticks_requested = kwargs.get('xaxis_num_ticks', xaxis_num_ticks)
            if len(x_dates) > 0 and len(x_positions) > 0:
                time_range = (x_dates[-1] - x_dates[0]).total_seconds()
                data_points = len(x_positions)
                if time_range < 3600 * 24: ideal_ticks = max(8, min(20, data_points // 30))
                elif time_range < 3600 * 24 * 7: ideal_ticks = max(8, min(20, data_points // 6))
                elif time_range < 3600 * 24 * 30: ideal_ticks = max(8, min(20, data_points // 2))
                else: ideal_ticks = max(8, min(20, data_points // 10))
                num_ticks = max(8, min(num_ticks_requested, ideal_ticks, data_points))
            else:
                num_ticks = max(8, min(num_ticks_requested, len(x_positions)))
            tick_step = max(1, len(x_positions) // num_ticks) if num_ticks > 0 else 1
            tick_positions = x_positions[::tick_step]
            show_date, show_time, show_year_separately = True, True, False
            if len(x_dates) > 0:
                time_range = (x_dates[-1] - x_dates[0]).total_seconds()
                if time_range < 3600 * 24: date_format, time_format, show_date = '%H:%M', '%H:%M', False
                elif time_range < 3600 * 24 * 7: date_format, time_format = '%d.%m', '%H:%M'
                elif time_range < 3600 * 24 * 30:
                    date_format = '%d.%m'
                    unique_times = set(dt.strftime('%H:%M') for dt in x_dates if hasattr(dt, 'strftime'))
                    if len(unique_times) == 1: time_format, show_time = '%d.%m', False
                    else: time_format = '%H:%M'
                else: date_format, time_format, show_time, show_year_separately = '%d.%m', '%d.%m', False, True
            else: date_format, time_format = '%d.%m', '%H:%M'
            tick_labels, prev_year = [], None
            for i in range(0, len(x_positions), tick_step):
                if i < len(x_dates):
                    date_obj, current_year = x_dates[i], x_dates[i].year
                    show_year = show_year_separately and (prev_year is None or current_year != prev_year)
                    date_str, time_str = date_obj.strftime(date_format), date_obj.strftime(time_format)
                    if show_year: label = f"{date_str}<br><b>{current_year}</b>"
                    elif show_date and show_time and date_str != time_str: label = f"{date_str}<br>{time_str}"
                    elif show_date: label = date_str
                    else: label = time_str
                    tick_labels.append(label)
                    prev_year = current_year
                else: tick_labels.append('')
            fig.update_xaxes(tickmode='array', tickvals=tick_positions, ticktext=tick_labels, tickangle=0, showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=1, col=1)
            if show_indicators and indicator_columns: fig.update_xaxes(tickmode='array', tickvals=tick_positions, ticktext=tick_labels, tickangle=0, showgrid=True, gridwidth=1, gridcolor='rgba(128, 128, 128, 0.2)', row=2, col=1)

        if show_indicators and indicator_columns:
            chart_types = indicator_chart_types or {}
            default_chart_type = lambda col: 'bar' if 'hist' in col.lower() else 'line'
            palette = kwargs.get('indicator_palette', self.default_config['indicator_palette'])
            for i, column in enumerate(indicator_columns):
                color = palette[i % len(palette)]
                chart_type = chart_types.get(column, default_chart_type(column))
                x_axis = price_data.index if time_axis_mode == 'timeseries' else x_positions
                if chart_type == 'bar':
                    fig.add_trace(go.Bar(x=x_axis, y=price_data[column], name=column, marker_color=color, opacity=0.7), row=2, col=1)
                else:
                    fig.add_trace(go.Scatter(x=x_axis, y=price_data[column], mode='lines', name=column, line=dict(color=color, width=1.6)), row=2, col=1)
            if len(indicator_columns) == 1:
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
            fig.update_yaxes(title_text="Indicator", row=2, col=1)

        fig.update_layout(title=title, width=self.default_config['width'], height=self.default_config['height'], xaxis_rangeslider_visible=False, template='plotly_white')
        chart_info = kwargs.get('chart_info', {})
        if chart_info:
            info_parts = []
            if 'symbol' in chart_info: info_parts.append(f"<b>{chart_info['symbol']}</b>")
            if 'timeframe' in chart_info: info_parts.append(chart_info['timeframe'])
            if 'source' in chart_info: info_parts.append(f"<i>{chart_info['source']}</i>")
            if info_parts:
                info_text = " | ".join(info_parts)
                fig.add_annotation(text=info_text, xref="paper", yref="paper", x=1.0, y=1.02, xanchor='right', yanchor='bottom', showarrow=False, font=dict(size=11, color='#666'), bgcolor='rgba(255,255,255,0.8)', borderpad=4)

        return fig

    def _create_plotly_zone_detail(self,
                                   price_window: pd.DataFrame,
                                   zone: Dict[str, Any],
                                   indicator_data: pd.DataFrame,
                                   title: str,
                                   window_meta: Dict[str, Any],
                                   **kwargs) -> go.Figure:
        """Создание детального графика зоны с Plotly."""

        show_volume = 'volume' in price_window.columns and price_window['volume'].notna().any()
        rows = 2 if show_volume else 1
        volume_height = kwargs.get('volume_panel_height', self.default_config['volume_panel_height'])
        row_heights = [1.0]
        if rows == 2:
            row_heights = [1 - volume_height, volume_height]

        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=row_heights,
        )

        # Свечной график
        fig.add_trace(go.Candlestick(
            x=price_window.index,
            open=price_window['open'],
            high=price_window['high'],
            low=price_window['low'],
            close=price_window['close'],
            name='Price',
        ), row=1, col=1)

        # Индикаторы
        palette = kwargs.get('indicator_palette', self.default_config['indicator_palette'])
        for i, column in enumerate(indicator_data.columns):
            color = palette[i % len(palette)]
            fig.add_trace(
                go.Scatter(
                    x=indicator_data.index,
                    y=indicator_data[column],
                    mode='lines',
                    name=column,
                    line=dict(color=color, width=1.6),
                ),
                row=1,
                col=1,
            )

        # Заливка зоны
        window_index = price_window.index
        zone_start_idx = max(0, window_meta['zone_left'] - window_meta['left_idx'])
        zone_end_idx = min(len(window_index) - 1, window_meta['zone_right'] - window_meta['left_idx'])
        if zone_start_idx <= zone_end_idx:
            x0 = window_index[zone_start_idx]
            x1 = window_index[zone_end_idx]
            zone_type = zone.get('type', 'bull')
            color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
            fig.add_vrect(
                x0=x0,
                x1=x1,
                fillcolor=color_config['fill'],
                line=dict(color=color_config['line'], width=1),
                layer="below",
            )

        if show_volume:
            fig.add_trace(
                go.Bar(
                    x=price_window.index,
                    y=price_window['volume'],
                    name='Volume',
                    marker_color='rgba(100, 149, 237, 0.4)',
                ),
                row=2,
                col=1,
            )
            fig.update_yaxes(title_text='Volume', row=2, col=1)

        # Аннотации
        if self.default_config['show_zone_stats']:
            stats_parts = [
                f"Type: {zone.get('type', 'n/a')}",
                f"Duration: {zone.get('duration', 'n/a')} bars",
            ]
            features = zone.get('features') or {}
            if 'strength' in features:
                stats_parts.append(f"Strength: {features['strength']:.2f}")
            fig.add_annotation(
                text='<br>'.join(stats_parts),
                xref='paper',
                yref='paper',
                x=0.01,
                y=0.98,
                showarrow=False,
                align='left',
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.1)',
                font=dict(size=11),
            )

        if self.default_config['show_zone_labels']:
            fig.add_annotation(
                xref='x',
                yref='paper',
                x=zone.get('start_time', window_index[zone_start_idx]),
                y=1.05,
                text=f"Zone {zone.get('zone_id', 'n/a')}",
                showarrow=False,
                font=dict(size=12, color='black'),
                bgcolor='rgba(255,255,255,0.8)',
            )

        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1.0),
        )

        fig.update_xaxes(matches='x')

        return fig

    def _create_plotly_zones_comparison(self,
                                        price_window: pd.DataFrame,
                                        zone_windows: List[Dict[str, Any]],
                                        title: str,
                                        **kwargs) -> go.Figure:
        """Создание сравнительного графика зон (Plotly)."""

        show_volume = 'volume' in price_window.columns and price_window['volume'].notna().any()
        rows = 2 if show_volume else 1
        volume_height = kwargs.get('volume_panel_height', self.default_config['volume_panel_height'])
        row_heights = [1.0]
        if rows == 2:
            row_heights = [1 - volume_height, volume_height]

        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=row_heights,
        )

        fig.add_trace(go.Candlestick(
            x=price_window.index,
            open=price_window['open'],
            high=price_window['high'],
            low=price_window['low'],
            close=price_window['close'],
            name='Price',
        ), row=1, col=1)

        palette = kwargs.get('indicator_palette', self.default_config['indicator_palette'])

        for zone_idx, payload in enumerate(zone_windows):
            zone = payload['zone']
            zone_type = zone.get('type', 'bull')
            color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
            meta = payload['meta']
            idx = price_window.index
            start_pos = max(0, meta['zone_left'] - meta['left_idx'])
            end_pos = min(len(idx) - 1, meta['zone_right'] - meta['left_idx'])
            if start_pos <= end_pos:
                fig.add_vrect(
                    x0=idx[start_pos],
                    x1=idx[end_pos],
                    fillcolor=color_config['fill'],
                    line=dict(color=color_config['line'], width=1),
                    layer="below",
                    annotation_text=f"Zone {zone.get('zone_id', zone_idx + 1)}",
                    annotation_position="top left",
                )

            indicators = payload['indicators'].reindex(price_window.index)
            for j, column in enumerate(indicators.columns):
                color = palette[(zone_idx + j) % len(palette)]
                fig.add_trace(
                    go.Scatter(
                        x=indicators.index,
                        y=indicators[column],
                        mode='lines',
                        name=f"{zone.get('zone_id', zone_idx + 1)} · {column}",
                        line=dict(color=color, width=1.4),
                        opacity=0.85,
                    ),
                    row=1,
                    col=1,
                )

        if show_volume:
            fig.add_trace(
                go.Bar(
                    x=price_window.index,
                    y=price_window['volume'],
                    name='Volume',
                    marker_color='rgba(120, 120, 220, 0.35)',
                ),
                row=2,
                col=1,
            )
            fig.update_yaxes(title_text='Volume', row=2, col=1)

        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1.0),
        )

        fig.update_xaxes(matches='x')

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

    def _create_matplotlib_zone_detail(self,
                                       price_window: pd.DataFrame,
                                       zone: Dict[str, Any],
                                       indicator_data: pd.DataFrame,
                                       title: str,
                                       window_meta: Dict[str, Any],
                                       **kwargs) -> plt.Figure:
        """Детальный график зоны с Matplotlib (упрощенная версия)."""

        show_volume = 'volume' in price_window.columns and price_window['volume'].notna().any()
        if show_volume:
            fig, (ax_price, ax_volume) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                                     gridspec_kw={'height_ratios': [3, 1]})
        else:
            fig, ax_price = plt.subplots(1, 1, figsize=(12, 6))
            ax_volume = None

        ax_price.plot(price_window.index, price_window['close'], label='Close', color='black', linewidth=1.2)

        for column in indicator_data.columns:
            ax_price.plot(indicator_data.index, indicator_data[column], label=column, linewidth=1)

        zone_start_idx = max(0, window_meta['zone_left'] - window_meta['left_idx'])
        zone_end_idx = min(len(price_window.index) - 1, window_meta['zone_right'] - window_meta['left_idx'])
        if zone_start_idx <= zone_end_idx:
            x0 = price_window.index[zone_start_idx]
            x1 = price_window.index[zone_end_idx]
            zone_type = zone.get('type', 'bull')
            color = 'lightblue' if zone_type == 'bull' else 'lightpink'
            ax_price.axvspan(x0, x1, alpha=self.default_config['opacity'], color=color)

        if show_volume and ax_volume is not None:
            ax_volume.bar(price_window.index, price_window['volume'], color='steelblue', alpha=0.4)
            ax_volume.set_ylabel('Volume')
            ax_volume.grid(True, alpha=0.2)

        ax_price.set_title(title)
        ax_price.legend(loc='upper left')
        ax_price.grid(True, alpha=0.3)

        if self.default_config['show_zone_stats']:
            stats_parts = [f"Type: {zone.get('type', 'n/a')}", f"Duration: {zone.get('duration', 'n/a')} bars"]
            features = zone.get('features') or {}
            if 'strength' in features:
                stats_parts.append(f"Strength: {features['strength']:.2f}")
            ax_price.text(0.01, 0.95, '\n'.join(stats_parts), transform=ax_price.transAxes,
                          fontsize=10, bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

        return fig

    def _create_matplotlib_zones_comparison(self,
                                            price_window: pd.DataFrame,
                                            zone_windows: List[Dict[str, Any]],
                                            title: str,
                                            **kwargs) -> plt.Figure:
        """Сравнительный график зон с Matplotlib (упрощенная версия)."""

        show_volume = 'volume' in price_window.columns and price_window['volume'].notna().any()
        if show_volume:
            fig, (ax_price, ax_volume) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                                     gridspec_kw={'height_ratios': [3, 1]})
        else:
            fig, ax_price = plt.subplots(1, 1, figsize=(12, 6))
            ax_volume = None

        ax_price.plot(price_window.index, price_window['close'], label='Close', color='black', linewidth=1.1)

        for idx, payload in enumerate(zone_windows):
            zone = payload['zone']
            meta = payload['meta']
            zone_start_idx = max(0, meta['zone_left'] - meta['left_idx'])
            zone_end_idx = min(len(price_window.index) - 1, meta['zone_right'] - meta['left_idx'])
            if zone_start_idx <= zone_end_idx:
                x0 = price_window.index[zone_start_idx]
                x1 = price_window.index[zone_end_idx]
                zone_type = zone.get('type', 'bull')
                color = 'lightblue' if zone_type == 'bull' else 'lightpink'
                ax_price.axvspan(x0, x1, alpha=self.default_config['opacity'], color=color,
                                 label=f"Zone {zone.get('zone_id', idx + 1)}")

            indicators = payload['indicators'].reindex(price_window.index)
            for column in indicators.columns:
                ax_price.plot(indicators.index, indicators[column], linewidth=1,
                              label=f"{zone.get('zone_id', idx + 1)} · {column}")

        if show_volume and ax_volume is not None:
            ax_volume.bar(price_window.index, price_window['volume'], color='steelblue', alpha=0.35)
            ax_volume.set_ylabel('Volume')
            ax_volume.grid(True, alpha=0.2)

        ax_price.set_title(title)
        ax_price.legend(loc='upper left')
        ax_price.grid(True, alpha=0.3)

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
