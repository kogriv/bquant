"""Модуль визуализации зон BQuant."""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union
import warnings

import numpy as np
import pandas as pd

from ..core.logging_config import get_logger
from ..core.exceptions import AnalysisError
from ..analysis.zones.models import ZoneInfo, SwingContext, SwingPoint
from .themes import ChartThemes
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


ALLOWED_DETAIL_KWARGS: Set[str] = {
    'context_bars',
    'max_zone_detail_bars',
    'xaxis_num_ticks',
    'time_axis_mode',
    'show_indicators',
    'show_volume',
    'show_swings',
    'swing_marker_size',
    'max_swings_to_display',
    'indicator_palette',
    'indicator_chart_types',
    'volume_panel_height',
    'indicator_panel_height',
    'chart_info',
    'metrics_annotation_position',
}

ALLOWED_OVERVIEW_KWARGS: Set[str] = {
    'xaxis_num_ticks',
    'time_axis_mode',
    'show_gap_lines',
    'show_indicators',
    'indicator_columns',
    'indicator_chart_types',
    'show_zone_labels',
    'metrics_annotation_position',
    'show_zone_stats',
    'show_aggregate_metrics',
    'aggregate_metrics_mode',
    'show_volume',
    'chart_info',
    'indicator_palette',
    'volume_panel_height',
    'indicator_panel_height',
    'show_swings',
    'swing_marker_size',
    'max_swings_to_display',
}


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

                if isinstance(zone, ZoneInfo):
                    normalized.append(self._normalize_zone(zone))
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

    def _add_annotation(
        self,
        fig: Union["go.Figure", "plt.Figure"],
        text: str,
        position: str = 'top-left',
        row: int = 1,
        col: int = 1,
        **kwargs: Any,
    ) -> None:
        """
        Унифицированное добавление текстовой аннотации на график.

        Args:
            fig: Plotly или Matplotlib figure
            text: Текст аннотации
            position: Одна из позиций ('top-left', 'top-right', 'bottom-left', 'bottom-right')
            row: Строка subplot (Plotly)
            col: Колонка subplot (Plotly)
            **kwargs: Дополнительные параметры оформления
        """
        if self.backend == 'plotly':
            if not PLOTLY_AVAILABLE:
                self.logger.warning("Plotly backend unavailable for annotations")
                return

            position_map = {
                'top-left': {'x': 0.02, 'y': 0.95, 'xanchor': 'left', 'yanchor': 'top'},
                'top-right': {'x': 0.98, 'y': 0.95, 'xanchor': 'right', 'yanchor': 'top'},
                'bottom-left': {'x': 0.02, 'y': 0.05, 'xanchor': 'left', 'yanchor': 'bottom'},
                'bottom-right': {'x': 0.98, 'y': 0.05, 'xanchor': 'right', 'yanchor': 'bottom'},
            }
            coords = position_map.get(position, position_map['top-left'])

            annotation_kwargs = dict(
                text=text,
                xref='paper',
                yref='paper',
                x=coords['x'],
                y=coords['y'],
                xanchor=coords['xanchor'],
                yanchor=coords['yanchor'],
                showarrow=False,
                font=dict(
                    size=kwargs.get('font_size', 10),
                    family=kwargs.get('font_family', 'monospace'),
                    color=kwargs.get('font_color', '#333333'),
                ),
                align=kwargs.get('align', 'left'),
                bgcolor=kwargs.get('bgcolor', 'rgba(255,255,255,0.85)'),
                bordercolor=kwargs.get('bordercolor', 'rgba(0,0,0,0.1)'),
                borderwidth=kwargs.get('borderwidth', 1),
                borderpad=kwargs.get('borderpad', 4),
            )

            # ВАЖНО: Не передаём row/col для paper-координат, т.к. Plotly автоматически
            # переключит xref/yref на x/y для конкретного subplot, что сломает позиционирование
            # Paper-координаты работают глобально для всей фигуры

            fig.add_annotation(**annotation_kwargs)
            return

        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("Matplotlib backend unavailable for annotations")
            return

        position_map = {
            'top-left': (0.02, 0.98, 'left', 'top'),
            'top-right': (0.98, 0.98, 'right', 'top'),
            'bottom-left': (0.02, 0.02, 'left', 'bottom'),
            'bottom-right': (0.98, 0.02, 'right', 'bottom'),
        }
        x, y, ha, va = position_map.get(position, position_map['top-left'])

        if not getattr(fig, "axes", None):
            self.logger.warning("Matplotlib figure has no axes for annotation")
            return

        axis_index = max(0, min(len(fig.axes) - 1, row - 1))
        ax = fig.axes[axis_index]
        matplotlib_text = text.replace('<br>', '\n')

        ax.text(
            x,
            y,
            matplotlib_text,
            transform=ax.transAxes,
            fontsize=kwargs.get('font_size', 8),
            fontfamily=kwargs.get('font_family', 'monospace'),
            color=kwargs.get('font_color', '#333333'),
            ha=ha,
            va=va,
            bbox=dict(
                boxstyle='round,pad=0.4',
                facecolor=kwargs.get('bgcolor', 'wheat'),
                edgecolor=kwargs.get('bordercolor', 'black'),
                linewidth=kwargs.get('borderwidth', 1),
                alpha=kwargs.get('alpha', 0.8),
            ),
        )

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
                'swing_context': zone.swing_context,
                'original_zone': zone,
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

        self.theme_manager = ChartThemes()
        requested_theme = kwargs.get('theme') or 'bquant_light'
        available_themes = self.theme_manager.get_available_themes()
        theme_name = requested_theme if requested_theme in available_themes else available_themes[0]
        try:
            theme_config = deepcopy(self.theme_manager.get_theme(theme_name))
        except Exception:
            fallback = available_themes[0]
            theme_config = deepcopy(self.theme_manager.get_theme(fallback))
            theme_name = fallback

        colors = theme_config.setdefault('colors', {})
        colors.setdefault('swing_peak', '#d62728')
        colors.setdefault('swing_trough', '#2ca02c')

        self.theme_name = theme_name
        self.theme = theme_config
        
        # Настройки по умолчанию
        self.default_config = {
            'width': kwargs.get('width', 1200),
            'height': kwargs.get('height', 800),
            'show_zone_labels': kwargs.get('show_zone_labels', False),
            'show_zone_stats': kwargs.get('show_zone_stats', True),
            'show_zone_metrics': kwargs.get('show_zone_metrics', False),
            'show_aggregate_metrics': kwargs.get('show_aggregate_metrics', False),
            'aggregate_metrics_mode': kwargs.get('aggregate_metrics_mode', 'compact'),
            'show_swings': kwargs.get('show_swings', False),
            'metrics_annotation_position': kwargs.get('metrics_annotation_position', 'top-left'),
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
    
    def _get_theme_color(self, role: str, default: str = '#000000') -> str:
        """
        Получить цвет из активной темы визуализатора.

        Args:
            role: ключ цвета (например, 'swing_peak')
            default: значение по умолчанию
        """
        colors = {}
        if isinstance(self.theme, dict):
            colors = self.theme.get('colors', {}) or {}
        return colors.get(role, default)

    def _validate_and_get_config(
        self,
        param_name: str,
        explicit_value: Any,
        kwargs: Dict[str, Any],
        default: Any,
        allowed_kwargs: Iterable[str],
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Разрешение значения конфигурации с валидацией поддерживаемых kwargs.

        Возвращает кортеж: (значение параметра, отфильтрованные kwargs).
        """
        allowed_set = set(allowed_kwargs)
        allowed_set.add(param_name)

        unknown_keys = set(kwargs.keys()) - allowed_set
        if unknown_keys:
            message = "Unknown parameters will be ignored: %s" % ', '.join(sorted(unknown_keys))
            self.logger.warning(message)
            warnings.warn(message, category=UserWarning, stacklevel=2)

        cleaned_kwargs = {k: v for k, v in kwargs.items() if k in allowed_set and k != param_name}

        if explicit_value is not None:
            if param_name in kwargs and kwargs[param_name] != explicit_value:
                self.logger.warning(
                    "Parameter '%s' specified both explicitly and in kwargs. "
                    "Using explicit value: %s (kwargs value %s ignored)",
                    param_name,
                    explicit_value,
                    kwargs[param_name],
                )
            return explicit_value, cleaned_kwargs

        if param_name in kwargs:
            return kwargs[param_name], cleaned_kwargs

        if param_name in self.default_config:
            return self.default_config[param_name], cleaned_kwargs

        return default, cleaned_kwargs

    def _extract_zone_metrics(self, zone: Union[Dict[str, Any], ZoneInfo]) -> Dict[str, Any]:
        """Извлечь метрики зоны для отображения."""
        if isinstance(zone, dict):
            zone_dict = zone
            indicator_context = zone.get('indicator_context') or {}
        else:
            zone_dict = self._normalize_zone(zone)
            indicator_context = zone.indicator_context or {}

        features = zone_dict.get('features') or {}
        metadata = features.get('metadata') or {}

        swing_metrics = metadata.get('swing_metrics')
        shape_metrics = metadata.get('shape_metrics')

        indicator_name = indicator_context.get('detection_indicator') or indicator_context.get('indicator')
        if not indicator_name:
            indicator_name = indicator_context.get('primary_indicator') or 'indicator'

        return {
            'zone': zone_dict,
            'swing_metrics': swing_metrics,
            'shape_metrics': shape_metrics,
            'indicator_name': indicator_name,
        }

    def _diagnose_missing_swing_metrics(self, zone: Dict[str, Any]) -> str:
        """Выявить причину отсутствия swing_metrics."""
        duration = zone.get('duration')
        if isinstance(duration, (int, float)) and duration < 8:
            return f"Zone too short ({int(duration)} < 8 bars)"

        swing_context = zone.get('swing_context')
        if swing_context is None:
            original = zone.get('original_zone')
            if isinstance(original, ZoneInfo):
                swing_context = original.swing_context
        if swing_context is None:
            return "No swing context"

        return "Not available"

    def _format_swing_metrics(self, swing_metrics: Optional[Dict[str, Any]], zone: Dict[str, Any]) -> str:
        """Форматировать swing_metrics в текст."""
        separator = '<br>' if self.backend == 'plotly' else '\n'
        zone_id = zone.get('zone_id', '?')

        if not swing_metrics:
            reason = self._diagnose_missing_swing_metrics(zone)
            self.logger.info("Zone %s has no swing metrics: %s", zone_id, reason)
            return f"📊 Swing Metrics: {reason}"

        num_swings = swing_metrics.get('num_swings')
        if num_swings is None:
            num_swings = swing_metrics.get('swings_count')

        rally_count = swing_metrics.get('rally_count')
        drop_count = swing_metrics.get('drop_count')
        avg_rally = swing_metrics.get('avg_rally') or swing_metrics.get('avg_rally_pct')
        avg_drop = swing_metrics.get('avg_drop') or swing_metrics.get('avg_drop_pct')
        ratio = swing_metrics.get('rally_to_drop_ratio')
        avg_rally_dur = swing_metrics.get('avg_rally_duration') or swing_metrics.get('avg_rally_duration_bars')
        avg_drop_dur = swing_metrics.get('avg_drop_duration') or swing_metrics.get('avg_drop_duration_bars')

        # Проверяем наличие хотя бы одного показателя (для несбалансированных свингов)
        if avg_rally is None and avg_drop is None and (num_swings == 0 or num_swings is None):
            self.logger.debug("Zone %s has no swing data", zone_id)
            return "📊 Swing Metrics: No swing data"

        parts = ["📊 Swing Metrics:"]
        if num_swings is not None:
            swings_text = f"  Swings: {num_swings}"
            if rally_count is not None or drop_count is not None:
                swings_text += f" ({rally_count or 0}↑ / {drop_count or 0}↓)"
            parts.append(swings_text)

        if avg_rally is not None:
            dur_text = f" ({float(avg_rally_dur):.1f} bars)" if isinstance(avg_rally_dur, (int, float)) else ""
            # avg_rally_pct уже в процентах, не умножаем на 100
            parts.append(f"  Avg Rally: {float(avg_rally):+.2f}%{dur_text}")

        if avg_drop is not None:
            dur_text = f" ({float(avg_drop_dur):.1f} bars)" if isinstance(avg_drop_dur, (int, float)) else ""
            # avg_drop_pct уже в процентах, не умножаем на 100
            parts.append(f"  Avg Drop: {float(avg_drop):+.2f}%{dur_text}")

        if ratio is not None:
            parts.append(f"  Rally/Drop Ratio: {float(ratio):.2f}x")

        return separator.join(parts)

    def _format_shape_metrics(
        self,
        shape_metrics: Optional[Dict[str, Any]],
        indicator_name: str = 'indicator',
    ) -> str:
        """Форматировать shape_metrics в текст."""
        separator = '<br>' if self.backend == 'plotly' else '\n'

        header = f"📈 Shape Metrics ({indicator_name})" if indicator_name else "📈 Shape Metrics"

        if not shape_metrics:
            return f"{header}: Not available"

        skewness = shape_metrics.get('hist_skewness')
        kurtosis = shape_metrics.get('hist_kurtosis')
        mean_value = shape_metrics.get('hist_mean')
        std_value = shape_metrics.get('hist_std')

        if skewness is None and kurtosis is None and mean_value is None and std_value is None:
            return f"{header}: Not available"

        parts = [f"{header}:"]
        if skewness is not None:
            if abs(skewness) < 1e-6:
                skew_label = "symmetric"
            elif skewness > 0:
                skew_label = "right-tailed"
            else:
                skew_label = "left-tailed"
            parts.append(f"  Skewness: {float(skewness):+.2f} ({skew_label})")

        if kurtosis is not None:
            if abs(kurtosis - 3) < 0.1:
                kurt_label = "mesokurtic"
            elif kurtosis > 3:
                kurt_label = "leptokurtic"
            else:
                kurt_label = "platykurtic"
            parts.append(f"  Kurtosis: {float(kurtosis):.2f} ({kurt_label})")

        if mean_value is not None:
            parts.append(f"  Mean: {float(mean_value):+.4f}")
        if std_value is not None:
            parts.append(f"  Std: {float(std_value):.4f}")

        return separator.join(parts)

    def _build_zone_annotation_text(
        self,
        zone: Union[Dict[str, Any], ZoneInfo],
        include_basic_stats: bool = True,
        include_metrics: bool = True,
    ) -> str:
        """Построить текст аннотации зоны."""
        zone_dict = zone if isinstance(zone, dict) else self._normalize_zone(zone)
        separator = '<br>' if self.backend == 'plotly' else '\n'

        parts: List[str] = []

        if include_basic_stats:
            zone_id = zone_dict.get('zone_id', '?')
            zone_type = zone_dict.get('type', 'n/a')
            duration = zone_dict.get('duration', 'n/a')
            parts.append(f"Zone #{zone_id} ({zone_type}) • {duration} bars")

            features = zone_dict.get('features') or {}
            strength = features.get('strength')
            if isinstance(strength, (int, float)):
                parts.append(f"Strength: {float(strength):.2f}")

        if include_metrics:
            metrics = self._extract_zone_metrics(zone_dict)
            if parts:
                parts.append('-' * 20)

            swing_text = self._format_swing_metrics(metrics['swing_metrics'], zone_dict)
            parts.append(swing_text)

            shape_text = self._format_shape_metrics(
                metrics['shape_metrics'],
                indicator_name=metrics['indicator_name'],
            )
            parts.append(shape_text)

        return separator.join(parts) if parts else ""
    
    def plot_zones_on_price_chart(self, price_data: pd.DataFrame,
                                 zones_data: Union[List[Dict], pd.DataFrame],
                                 title: str = "Price Chart with Zones",
                                 show_indicators: bool = False,
                                 indicator_columns: Optional[List[str]] = None,
                                 indicator_chart_types: Optional[Dict[str, str]] = None,
                                 show_gap_lines: bool = False,
                                 xaxis_num_ticks: int = 16,
                                 time_axis_mode: str = 'dense',
                         show_aggregate_metrics: bool = False,
                         aggregate_metrics_mode: str = 'compact',
                         show_swings: bool = False,
                         swing_marker_size: int = 8,
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
            show_aggregate_metrics: Отображать ли агрегированные метрики (MVP вариант).
            aggregate_metrics_mode: 'compact' или 'full' режим отображения агрегированных метрик.
            show_swings: Отображать ли глобальные swing-точки (только Plotly в v1.0).
            swing_marker_size: Размер маркеров свингов (Plotly).
            **kwargs: Дополнительные параметры
        
        Returns:
            Объект графика
        """
        show_aggregate_metrics, kwargs = self._validate_and_get_config(
            'show_aggregate_metrics',
            show_aggregate_metrics,
            kwargs,
            default=self.default_config.get('show_aggregate_metrics', False),
            allowed_kwargs=ALLOWED_OVERVIEW_KWARGS,
        )

        aggregate_metrics_mode, kwargs = self._validate_and_get_config(
            'aggregate_metrics_mode',
            aggregate_metrics_mode,
            kwargs,
            default='compact',
            allowed_kwargs=ALLOWED_OVERVIEW_KWARGS,
        )

        show_swings, kwargs = self._validate_and_get_config(
            'show_swings',
            show_swings,
            kwargs,
            default=self.default_config.get('show_swings', False),
            allowed_kwargs=ALLOWED_OVERVIEW_KWARGS,
        )

        swing_marker_size, kwargs = self._validate_and_get_config(
            'swing_marker_size',
            swing_marker_size,
            kwargs,
            default=8,
            allowed_kwargs=ALLOWED_OVERVIEW_KWARGS,
        )

        max_swings_to_display, kwargs = self._validate_and_get_config(
            'max_swings_to_display',
            kwargs.get('max_swings_to_display'),
            kwargs,
            default=None,
            allowed_kwargs=ALLOWED_OVERVIEW_KWARGS,
        )

        zones = self._prepare_zone_data(zones_data)
        
        if self.backend == 'plotly':
            fig = self._create_plotly_zones_on_price(
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
            fig = self._create_matplotlib_zones_on_price(price_data, zones, title, **kwargs)

        if show_aggregate_metrics and zones:
            aggregated = self._aggregate_zone_metrics_mvp(zones)
            if aggregated:
                annotation_text = self._format_aggregate_metrics_mvp(
                    aggregated,
                    mode=aggregate_metrics_mode,
                )
                if annotation_text:
                    position = kwargs.get(
                        'metrics_annotation_position',
                        self.default_config.get('metrics_annotation_position', 'top-left'),
                    )
                    self._add_annotation(fig, text=annotation_text, position=position, row=1, col=1)

        if show_swings:
            swing_context = self._resolve_global_swing_context(zones)
            if swing_context:
                visible_swings = [
                    sp
                    for sp in swing_context.swing_points
                    if price_data.index[0] <= sp.timestamp <= price_data.index[-1]
                ]
                limit = max_swings_to_display
                if limit is not None and len(visible_swings) > limit:
                    visible_swings = visible_swings[:limit]
                    self.logger.warning(
                        "Overview swing overlay truncated to %s points due to max_swings_to_display",
                        limit,
                    )
                if len(visible_swings) > 200:
                    self.logger.warning(
                        "Overview swing overlay has %s points; rendering may be slow",
                        len(visible_swings),
                    )
                # Используем позиционные индексы в dense режиме
                use_positional = (time_axis_mode == 'dense')
                self._add_swing_overlay(
                    fig,
                    visible_swings,
                    row=1,
                    col=1,
                    marker_size=int(swing_marker_size),
                    price_data=price_data,
                    use_positional_index=use_positional,
                )
                
                # Явно устанавливаем диапазон Y-оси на основе данных price_data, а не автомасштабирование
                # чтобы свинги не растягивали ось
                if self.backend == 'plotly' and PLOTLY_AVAILABLE:
                    y_min = price_data['low'].min()
                    y_max = price_data['high'].max()
                    y_margin = (y_max - y_min) * 0.05  # 5% отступ сверху и снизу
                    fig.update_yaxes(range=[y_min - y_margin, y_max + y_margin], row=1, col=1)
            else:
                self.logger.debug("No swing_context found among zones for overview overlay")

        return fig

    def _aggregate_zone_metrics_mvp(
        self,
        zones: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """Агрегировать swing-метрики по списку зон (MVP)."""
        bull_zones = [zone for zone in zones if zone.get('type') == 'bull']
        bear_zones = [zone for zone in zones if zone.get('type') == 'bear']

        if not bull_zones and not bear_zones:
            return None

        def _collect(zones_list: List[Dict[str, Any]]) -> Dict[str, Any]:
            rallies: List[float] = []
            drops: List[float] = []
            ratios: List[float] = []
            avg_rally_durations: List[float] = []
            avg_drop_durations: List[float] = []
            all_durations: List[float] = []
            zones_with_swings = 0
            metric_samples = {
                'avg_rally': 0,
                'avg_drop': 0,
                'avg_rally_duration': 0,
                'avg_drop_duration': 0,
                'avg_duration': 0,
                'ratio': 0,
            }

            for zone in zones_list:
                metrics = self._extract_zone_metrics(zone)
                swing_metrics = metrics.get('swing_metrics')
                if not swing_metrics:
                    continue

                # Проверяем наличие хотя бы одного rally или drop
                # Не требуем num_swings > 0, т.к. в глобальном режиме
                # в короткие зоны может попадать мало свинг-точек,
                # создавая несбалансированные движения (только rally или только drop)
                avg_rally = swing_metrics.get('avg_rally') or swing_metrics.get('avg_rally_pct')
                avg_drop = swing_metrics.get('avg_drop') or swing_metrics.get('avg_drop_pct')

                # Пропускаем только если нет вообще никаких данных
                if avg_rally is None and avg_drop is None:
                    continue

                zones_with_swings += 1

                if avg_rally is not None:
                    rallies.append(float(avg_rally))
                    metric_samples['avg_rally'] += 1

                if avg_drop is not None:
                    drops.append(float(avg_drop))
                    metric_samples['avg_drop'] += 1

                ratio = swing_metrics.get('rally_to_drop_ratio')
                if ratio is not None:
                    ratios.append(float(ratio))
                    metric_samples['ratio'] += 1

                rally_dur = swing_metrics.get('avg_rally_duration') or swing_metrics.get('avg_rally_duration_bars')
                drop_dur = swing_metrics.get('avg_drop_duration') or swing_metrics.get('avg_drop_duration_bars')
                if rally_dur is not None:
                    avg_rally_durations.append(float(rally_dur))
                    all_durations.append(float(rally_dur))
                    metric_samples['avg_rally_duration'] += 1
                    metric_samples['avg_duration'] += 1
                if drop_dur is not None:
                    avg_drop_durations.append(float(drop_dur))
                    all_durations.append(float(drop_dur))
                    metric_samples['avg_drop_duration'] += 1
                    metric_samples['avg_duration'] += 1

            def _mean_std(values: List[float]) -> Tuple[Optional[float], Optional[float]]:
                if not values:
                    return None, None
                arr = np.asarray(values, dtype=float)
                return float(arr.mean()), float(arr.std(ddof=0))

            rally_mean, rally_std = _mean_std(rallies)
            drop_mean, drop_std = _mean_std(drops)
            ratio_mean, _ = _mean_std(ratios)
            rally_dur_mean, rally_dur_std = _mean_std(avg_rally_durations)
            drop_dur_mean, drop_dur_std = _mean_std(avg_drop_durations)
            avg_duration_mean, avg_duration_std = _mean_std(all_durations)

            return {
                'count': len(zones_list),
                'with_swings': zones_with_swings,
                'avg_rally_mean': rally_mean,
                'avg_rally_std': rally_std,
                'avg_drop_mean': drop_mean,
                'avg_drop_std': drop_std,
                'ratio_mean': ratio_mean,
                'avg_rally_duration_mean': rally_dur_mean,
                'avg_rally_duration_std': rally_dur_std,
                'avg_drop_duration_mean': drop_dur_mean,
                'avg_drop_duration_std': drop_dur_std,
                'avg_duration_mean': avg_duration_mean,
                'avg_duration_std': avg_duration_std,
                'avg_rally_samples': metric_samples['avg_rally'],
                'avg_drop_samples': metric_samples['avg_drop'],
                'avg_rally_duration_samples': metric_samples['avg_rally_duration'],
                'avg_drop_duration_samples': metric_samples['avg_drop_duration'],
                'avg_duration_samples': metric_samples['avg_duration'],
                'ratio_samples': metric_samples['ratio'],
            }

        result: Dict[str, Dict[str, Any]] = {}
        if bull_zones:
            result['bull'] = _collect(bull_zones)
        if bear_zones:
            result['bear'] = _collect(bear_zones)

        return result if result else None

    def _format_aggregate_metrics_mvp(
        self,
        aggregated: Dict[str, Dict[str, Any]],
        mode: str = 'compact',
    ) -> str:
        """Сформатировать агрегированные метрики (compact | full)."""
        separator = '<br>' if self.backend == 'plotly' else '\n'
        mode = (mode or '').lower()
        if mode not in {'compact', 'full'}:
            self.logger.warning("Unknown aggregate_metrics_mode '%s', falling back to 'compact'", mode)
            mode = 'compact'

        parts: List[str] = []
        for side in ('bull', 'bear'):
            if side not in aggregated:
                continue
            stats = aggregated[side]
            label = "📊 Bull Zones" if side == 'bull' else "📊 Bear Zones"
            count = stats.get('count', 0) or 0
            with_swings = stats.get('with_swings', 0) or 0
            coverage_pct = (with_swings / count * 100) if count else 0.0
            parts.append(f"{label}: {with_swings}/{count} with swings ({coverage_pct:.0f}%)")

            rally_mean = stats.get('avg_rally_mean')
            rally_std = stats.get('avg_rally_std')
            drop_mean = stats.get('avg_drop_mean')
            drop_std = stats.get('avg_drop_std')
            ratio_mean = stats.get('ratio_mean')

            if mode == 'compact':
                if rally_mean is not None:
                    # Значения уже в процентах, не умножаем на 100
                    parts.append(f"  Avg Rally: {float(rally_mean):+.2f}% ± {float(rally_std or 0):.2f}%")
                else:
                    parts.append("  Avg Rally: N/A (no aggregated data)")
                if drop_mean is not None:
                    # Значения уже в процентах, не умножаем на 100
                    parts.append(f"  Avg Drop: {float(drop_mean):+.2f}% ± {float(drop_std or 0):.2f}%")
                else:
                    parts.append("  Avg Drop: N/A (no aggregated data)")
                if ratio_mean is not None:
                    parts.append(f"  Rally/Drop Ratio: {float(ratio_mean):.2f}x")
                else:
                    parts.append("  Rally/Drop Ratio: N/A (no aggregated data)")
            else:
                rally_line = "  Avg Rally:"
                if rally_mean is not None:
                    # Значения уже в процентах, не умножаем на 100
                    rally_line += f" {float(rally_mean):+.2f}%"
                if rally_std is not None:
                    rally_line += f" ± {float(rally_std):.2f}%"
                rally_dur_mean = stats.get('avg_rally_duration_mean')
                rally_dur_std = stats.get('avg_rally_duration_std')
                if rally_dur_mean is not None:
                    rally_line += f" ({float(rally_dur_mean):.1f}"
                    if rally_dur_std is not None:
                        rally_line += f" ± {float(rally_dur_std):.1f}"
                    rally_line += " bars)"
                if rally_mean is None and rally_dur_mean is None:
                    rally_line += " N/A (no aggregated data)"
                parts.append(rally_line)

                drop_line = "  Avg Drop:"
                if drop_mean is not None:
                    # Значения уже в процентах, не умножаем на 100
                    drop_line += f" {float(drop_mean):+.2f}%"
                if drop_std is not None:
                    drop_line += f" ± {float(drop_std):.2f}%"
                drop_dur_mean = stats.get('avg_drop_duration_mean')
                drop_dur_std = stats.get('avg_drop_duration_std')
                if drop_dur_mean is not None:
                    drop_line += f" ({float(drop_dur_mean):.1f}"
                    if drop_dur_std is not None:
                        drop_line += f" ± {float(drop_dur_std):.1f}"
                    drop_line += " bars)"
                if drop_mean is None and drop_dur_mean is None:
                    drop_line += " N/A (no aggregated data)"
                parts.append(drop_line)

                if ratio_mean is not None:
                    parts.append(f"  Rally/Drop Ratio: {float(ratio_mean):.2f}x")
                else:
                    parts.append("  Rally/Drop Ratio: N/A (no aggregated data)")

                avg_duration_mean = stats.get('avg_duration_mean')
                avg_duration_std = stats.get('avg_duration_std')
                if avg_duration_mean is not None:
                    duration_line = f"  Avg Swing Duration: {float(avg_duration_mean):.1f}"
                    if avg_duration_std is not None:
                        duration_line += f" ± {float(avg_duration_std):.1f}"
                    duration_line += " bars"
                else:
                    duration_line = "  Avg Swing Duration: N/A (no aggregated data)"
                parts.append(duration_line)

        return separator.join(parts) if parts else ""

    def plot_zone_detail(self, price_data: pd.DataFrame,
                         zone: Union[Dict[str, Any], ZoneInfo, Any],
                         context_bars: int = 20,
                         title: str = "Zone Detail",
                         show_zone_metrics: bool = False,
                         show_indicators: bool = True,
                         show_volume: bool = True,
                         show_swings: bool = False,
                         swing_marker_size: int = 10,
                         show_zone_stats: Optional[bool] = None,
                         time_axis_mode: str = 'dense',
                         xaxis_num_ticks: int = 16,
                         **kwargs) -> Union[go.Figure, plt.Figure]:
        """Детализированный просмотр отдельной зоны."""

        if price_data is None or price_data.empty:
            raise ValueError("price_data must be a non-empty DataFrame")

        show_zone_metrics, kwargs = self._validate_and_get_config(
            'show_zone_metrics',
            show_zone_metrics,
            kwargs,
            default=self.default_config.get('show_zone_metrics', False),
            allowed_kwargs=ALLOWED_DETAIL_KWARGS,
        )

        metrics_position = kwargs.get(
            'metrics_annotation_position',
            self.default_config.get('metrics_annotation_position', 'top-left'),
        )
        if 'metrics_annotation_position' in kwargs:
            kwargs = dict(kwargs)
            kwargs.pop('metrics_annotation_position', None)

        show_zone_stats, kwargs = self._validate_and_get_config(
            'show_zone_stats',
            show_zone_stats,
            kwargs,
            default=self.default_config.get('show_zone_stats', True),
            allowed_kwargs=ALLOWED_DETAIL_KWARGS,
        )

        show_swings, kwargs = self._validate_and_get_config(
            'show_swings',
            show_swings,
            kwargs,
            default=self.default_config.get('show_swings', False),
            allowed_kwargs=ALLOWED_DETAIL_KWARGS,
        )

        swing_marker_size, kwargs = self._validate_and_get_config(
            'swing_marker_size',
            swing_marker_size,
            kwargs,
            default=10,
            allowed_kwargs=ALLOWED_DETAIL_KWARGS,
        )

        max_swings_to_display, kwargs = self._validate_and_get_config(
            'max_swings_to_display',
            kwargs.get('max_swings_to_display'),
            kwargs,
            default=None,
            allowed_kwargs=ALLOWED_DETAIL_KWARGS,
        )

        # Проверяем параметры из kwargs (приоритет выше параметров)
        show_indicators = kwargs.get('show_indicators', show_indicators)
        show_volume = kwargs.get('show_volume', show_volume)
        time_axis_mode = kwargs.get('time_axis_mode', time_axis_mode)

        zone_dict = self._normalize_zone(zone)
        context = kwargs.get('context_bars', context_bars)
        if context is None:
            context = self.default_config['zone_detail_context']

        max_bars = kwargs.get('max_zone_detail_bars', self.default_config['max_zone_detail_bars'])

        window_df, window_meta = self._get_zone_window(price_data, zone_dict, context, max_bars=max_bars)

        # Для индикаторов всегда используем window_df (полный диапазон с контекстом)
        indicator_source = window_df
        
        indicator_columns = None
        if show_indicators:
            # Определяем колонки индикаторов
            zone_data = zone_dict.get('data')
            if isinstance(zone_data, pd.DataFrame) and not zone_data.empty:
                # Используем zone_data для определения колонок, но данные возьмем из window_df
                indicator_columns = self._detect_indicators_from_features(zone_dict, zone_data)
            if not indicator_columns:
                indicator_columns = self._detect_indicators_from_features(zone_dict, window_df)
        
        indicator_data = pd.DataFrame(index=window_df.index)
        if indicator_columns and show_indicators:
            # Берем индикаторы из window_df (полный диапазон с контекстом)
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
            fig = self._create_plotly_zone_detail(
                window_df,
                zone_dict,
                indicator_data,
                title,
                window_meta,
                show_indicators=show_indicators,
                show_volume=show_volume,
                time_axis_mode=time_axis_mode,
                xaxis_num_ticks=kwargs.get('xaxis_num_ticks', xaxis_num_ticks),
                **kwargs,
            )
        else:
            fig = self._create_matplotlib_zone_detail(
                window_df,
                zone_dict,
                indicator_data,
                title,
                window_meta,
                **kwargs,
            )

        if show_zone_stats or show_zone_metrics:
            annotation_text = self._build_zone_annotation_text(
                zone_dict,
                include_basic_stats=bool(show_zone_stats),
                include_metrics=bool(show_zone_metrics),
            )
            if annotation_text:
                self._add_annotation(fig, text=annotation_text, position=metrics_position, row=1, col=1)

        if show_swings:
            swing_context = self._resolve_swing_context(zone_dict)
            if swing_context:
                zone_swings = self._get_zone_swings_safe(zone_dict, swing_context)
                limit = max_swings_to_display
                if limit is not None and len(zone_swings) > limit:
                    self.logger.warning(
                        "Plot detail swing overlay truncated to %s points (requested limit).",
                        limit,
                    )
                    zone_swings = zone_swings[:limit]
                if len(zone_swings) > 200:
                    self.logger.warning(
                        "Plot detail swing overlay has %s points; rendering may be slow.",
                        len(zone_swings),
                    )
                # Используем позиционные индексы в dense режиме
                use_positional = (time_axis_mode == 'dense')
                self._add_swing_overlay(
                    fig,
                    zone_swings,
                    row=1,
                    col=1,
                    marker_size=int(swing_marker_size),
                    price_data=window_df,
                    use_positional_index=use_positional,
                )
            else:
                self.logger.debug(
                    "Zone %s has no swing_context; ensure global swing scope is enabled.",
                    zone_dict.get('zone_id', '?'),
                )

        return fig

    def _resolve_global_swing_context(self, zones: List[Dict[str, Any]]) -> Optional["SwingContext"]:
        """Попытаться найти глобальный swing_context среди зон."""
        for zone in zones:
            context = zone.get('swing_context')
            if context:
                return context
            original = zone.get('original_zone')
            if isinstance(original, ZoneInfo) and original.swing_context:
                return original.swing_context
        return None

    def _resolve_swing_context(self, zone: Union[Dict[str, Any], ZoneInfo]) -> Optional["SwingContext"]:
        """Извлечь SwingContext из зоны."""
        if isinstance(zone, dict):
            swing_context = zone.get('swing_context')
            if swing_context:
                return swing_context
            original = zone.get('original_zone')
            if isinstance(original, ZoneInfo):
                return original.swing_context
            return None

        if isinstance(zone, ZoneInfo):
            return zone.swing_context

        return None

    def _get_zone_swings_safe(
        self,
        zone: Union[Dict[str, Any], ZoneInfo],
        swing_context: "SwingContext",
    ) -> List["SwingPoint"]:
        """Безопасно получить свинг-точки для зоны."""
        try:
            if isinstance(zone, ZoneInfo):
                return swing_context.get_swings_for_zone(zone)
            original_zone = zone.get('original_zone')
            if isinstance(original_zone, ZoneInfo):
                return swing_context.get_swings_for_zone(original_zone)
            temp_zone = ZoneInfo(
                zone_id=zone.get('zone_id', -1),
                type=zone.get('type', 'unknown'),
                start_idx=zone.get('start_idx', 0),
                end_idx=zone.get('end_idx', 0),
                start_time=zone.get('start_time'),
                end_time=zone.get('end_time'),
                duration=zone.get('duration', 0),
                data=zone.get('data', pd.DataFrame()),
                features=zone.get('features'),
                indicator_context=zone.get('indicator_context'),
                swing_context=swing_context,
            )
            return swing_context.get_swings_for_zone(temp_zone)
        except Exception as error:
            self.logger.warning("Failed to resolve swings for zone %s: %s", zone, error)
            return []

    def _add_swing_overlay(
        self,
        fig: Union["go.Figure", "plt.Figure"],
        swing_points: List["SwingPoint"],
        row: int = 1,
        col: int = 1,
        marker_size: int = 10,
        price_data: Optional[pd.DataFrame] = None,
        use_positional_index: bool = False,
    ) -> None:
        """
        Добавить визуализацию свинго-точек.
        
        Args:
            fig: График для добавления overlay
            swing_points: Список SwingPoint для отображения
            row: Номер строки subplot (для Plotly)
            col: Номер колонки subplot (для Plotly)
            marker_size: Размер маркеров
            price_data: DataFrame с ценами (нужен для преобразования timestamp в индексы в dense режиме)
            use_positional_index: Если True, использовать позиционные индексы вместо timestamp (для dense режима)
        """
        if not swing_points:
            return

        peak_color = self._get_theme_color('swing_peak', '#d62728')
        trough_color = self._get_theme_color('swing_trough', '#2ca02c')

        peaks = [sp for sp in swing_points if sp.swing_type == 'peak']
        troughs = [sp for sp in swing_points if sp.swing_type == 'trough']

        if self.backend == 'plotly':
            if not PLOTLY_AVAILABLE:
                self.logger.warning("Plotly backend unavailable for swing overlay")
                return
            
            # Если используем позиционные индексы, нужно преобразовать timestamp в индексы
            if use_positional_index and price_data is not None:
                # Создаём маппинг timestamp -> позиционный индекс (используем range вместо enumerate)
                timestamp_to_idx = {ts: pos for pos, ts in zip(range(len(price_data)), price_data.index)}
                
                def get_x_coord(sp):
                    """Преобразовать timestamp свинга в позиционный индекс."""
                    return timestamp_to_idx.get(sp.timestamp, None)
                
                # Фильтруем свинги, для которых есть соответствие в price_data
                peaks_x = [get_x_coord(sp) for sp in peaks]
                peaks_y = [sp.price for sp in peaks]
                peaks_timestamps = [sp.timestamp for sp in peaks]
                # Удаляем None значения (свинги вне диапазона price_data)
                peaks_data = [(x, y, ts) for x, y, ts in zip(peaks_x, peaks_y, peaks_timestamps) if x is not None]
                
                troughs_x = [get_x_coord(sp) for sp in troughs]
                troughs_y = [sp.price for sp in troughs]
                troughs_timestamps = [sp.timestamp for sp in troughs]
                troughs_data = [(x, y, ts) for x, y, ts in zip(troughs_x, troughs_y, troughs_timestamps) if x is not None]
            else:
                # Используем timestamp напрямую (для timeseries режима)
                peaks_data = [(sp.timestamp, sp.price, sp.timestamp) for sp in peaks]
                troughs_data = [(sp.timestamp, sp.price, sp.timestamp) for sp in troughs]
            
            if peaks_data:
                peaks_x, peaks_y, peaks_timestamps = zip(*peaks_data)
                fig.add_trace(
                    go.Scatter(
                        x=list(peaks_x),
                        y=list(peaks_y),
                        mode='markers',
                        marker=dict(
                            symbol='triangle-down',
                            size=marker_size,
                            color=peak_color,
                            line=dict(width=1, color='darkred'),
                        ),
                        name='Swing Peaks',
                        customdata=list(peaks_timestamps),
                        hovertemplate='<b>Peak</b><br>Price: %{y:.2f}<br>Time: %{customdata}<extra></extra>',
                        showlegend=True,
                    ),
                    row=row,
                    col=col,
                )
            if troughs_data:
                troughs_x, troughs_y, troughs_timestamps = zip(*troughs_data)
                fig.add_trace(
                    go.Scatter(
                        x=list(troughs_x),
                        y=list(troughs_y),
                        mode='markers',
                        marker=dict(
                            symbol='triangle-up',
                            size=marker_size,
                            color=trough_color,
                            line=dict(width=1, color='darkgreen'),
                        ),
                        name='Swing Troughs',
                        customdata=list(troughs_timestamps),
                        hovertemplate='<b>Trough</b><br>Price: %{y:.2f}<br>Time: %{customdata}<extra></extra>',
                        showlegend=True,
                    ),
                    row=row,
                    col=col,
                )
            return

        if self.backend == 'matplotlib':
            if not MATPLOTLIB_AVAILABLE:
                self.logger.warning("Matplotlib backend unavailable for swing overlay")
                return
            self.logger.warning(
                "Swing overlay for Matplotlib backend will be implemented in v1.1 (Этап 4). "
                "Current version skips overlay."
            )
            return

        self.logger.warning("Swing overlay not supported for backend %s", self.backend)

    def plot_zones_comparison(self, price_data: pd.DataFrame,
                              zones_data: Union[List[Dict], pd.DataFrame, List[Any]],
                              max_zones: int = 5,
                              date_range: Optional[Tuple[datetime, datetime]] = None,
                              title: str = "Zones Comparison",
                              show_indicators: bool = True,
                              show_volume: bool = True,
                              indicator_columns: Optional[List[str]] = None,
                              indicator_chart_types: Optional[Dict[str, str]] = None,
                              time_axis_mode: str = 'dense',
                              **kwargs) -> Union[go.Figure, plt.Figure]:
        """Сравнение нескольких зон на ценовом графике."""

        if price_data is None or price_data.empty:
            raise ValueError("price_data must be a non-empty DataFrame")

        # Проверяем параметры из kwargs (приоритет выше параметров)
        show_indicators = kwargs.get('show_indicators', show_indicators)
        show_volume = kwargs.get('show_volume', show_volume)
        time_axis_mode = kwargs.get('time_axis_mode', time_axis_mode)

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

        # Сортируем зоны по времени начала для последовательного отображения
        filtered_zones_sorted = sorted(
            filtered_zones,
            key=lambda z: z.get('start_time') or z.get('start_idx', 0)
        )

        for zone in filtered_zones_sorted:
            window_df, window_meta = self._get_zone_window(price_data, zone, context, max_bars=None)
            
            indicators_df = pd.DataFrame(index=window_df.index)
            
            # Определяем индикаторы только если show_indicators=True
            if show_indicators:
                # Для индикаторов всегда используем window_df (полный диапазон с контекстом)
                indicator_source = window_df
                
                # Определяем колонки индикаторов
                zone_indicator_columns = indicator_columns  # Используем переданные колонки или None
                if zone_indicator_columns is None:
                    zone_data = zone.get('data')
                    if isinstance(zone_data, pd.DataFrame) and not zone_data.empty:
                        zone_indicator_columns = self._detect_indicators_from_features(zone, zone_data)
                    if not zone_indicator_columns:
                        zone_indicator_columns = self._detect_indicators_from_features(zone, window_df)
                
                if zone_indicator_columns:
                    indicators_df = indicator_source[zone_indicator_columns].copy()

            zone_windows.append({
                'zone': zone,
                'window': window_df,
                'meta': window_meta,
                'indicators': indicators_df,
            })

        # Формируем «плотную» ось времени: каждая зона размещается в своем блоке
        if not zone_windows:
            dense_window = price_data.iloc[0:min(100, len(price_data))].copy()
            dense_window['__timestamp__'] = dense_window.index
            dense_window.index = range(len(dense_window))
            zone_blocks = []
        else:
            gap_size = 3  # Отступ между блоками зон
            current_offset = 0
            dense_rows: Dict[str, List[Any]] = {
                'open': [], 'high': [], 'low': [], 'close': [], 'volume': [], '__timestamp__': []
            }
            dense_index: List[int] = []
            zone_blocks = []

            for payload in zone_windows:
                window_df = payload['window']
                block_positions: List[int] = []
                block_timestamps: List[pd.Timestamp] = []

                for row_ts, row in window_df.iterrows():
                    dense_index.append(current_offset)
                    dense_rows['open'].append(row.get('open'))
                    dense_rows['high'].append(row.get('high'))
                    dense_rows['low'].append(row.get('low'))
                    dense_rows['close'].append(row.get('close'))
                    dense_rows['volume'].append(row.get('volume') if 'volume' in row else None)
                    dense_rows['__timestamp__'].append(row_ts)

                    block_positions.append(current_offset)
                    block_timestamps.append(row_ts)
                    current_offset += 1

                zone_blocks.append({
                    'payload': payload,
                    'positions': block_positions,
                    'timestamps': block_timestamps,
                })

                current_offset += gap_size  # Отступ перед следующей зоной

            dense_window = pd.DataFrame(dense_rows, index=dense_index)

        if not zone_windows:
            global_window = dense_window
        else:
            global_window = dense_window

        if self.backend == 'plotly':
            return self._create_plotly_zones_comparison(
                global_window,
                zone_blocks if zone_windows else [],
                title,
                show_indicators=show_indicators,
                show_volume=show_volume,
                indicator_chart_types=indicator_chart_types,
                time_axis_mode=time_axis_mode,
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
                                   time_axis_mode: str = 'dense',
                                   xaxis_num_ticks: int = 16,
                                   **kwargs) -> go.Figure:
        """Создание детального графика зоны с Plotly."""

        # Проверяем параметры show_indicators и show_volume
        show_indicators = kwargs.get('show_indicators', True)
        show_volume = kwargs.get('show_volume', True) and 'volume' in price_window.columns and price_window['volume'].notna().any()
        time_axis_mode = kwargs.get('time_axis_mode', time_axis_mode)
        xaxis_num_ticks = kwargs.get('xaxis_num_ticks', xaxis_num_ticks)
        
        # Проверяем, есть ли индикаторы
        has_indicators = show_indicators and not indicator_data.empty and len(indicator_data.columns) > 0
        
        # Определяем количество панелей
        rows = 1
        if has_indicators:
            rows += 1
        if show_volume:
            rows += 1
        
        # Высота панелей
        volume_height = kwargs.get('volume_panel_height', self.default_config['volume_panel_height'])
        indicator_panel_height = kwargs.get('indicator_panel_height', 0.3)
        
        row_heights = [1.0]
        if rows == 2:
            if has_indicators:
                row_heights = [1 - indicator_panel_height, indicator_panel_height]
            else:  # только volume
                row_heights = [1 - volume_height, volume_height]
        elif rows == 3:
            # цена, индикаторы, volume
            row_heights = [
                1 - indicator_panel_height - volume_height,
                indicator_panel_height,
                volume_height
            ]

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
            gap_mask = find_all_gaps(price_window.index)
            
            # Свечной график
            fig.add_trace(go.Candlestick(
                x=price_window.index,
                open=price_window['open'],
                high=price_window['high'],
                low=price_window['low'],
                close=price_window['close'],
                name='Price',
            ), row=1, col=1)
            
            # Устанавливаем rangemode='normal' для оси Y цен, чтобы избежать "сплющивания"
            fig.update_yaxes(rangemode='normal', title_text="Price", row=1, col=1)

            # Индикаторы на отдельной панели (если есть)
            if has_indicators:
                indicator_row = 2
                palette = kwargs.get('indicator_palette', self.default_config['indicator_palette'])
                indicator_chart_types = kwargs.get('indicator_chart_types', {})
                default_chart_type = lambda col: 'bar' if 'hist' in col.lower() else 'line'
                
                for i, column in enumerate(indicator_data.columns):
                    color = palette[i % len(palette)]
                    chart_type = indicator_chart_types.get(column, default_chart_type(column))
                    
                    if chart_type == 'bar':
                        fig.add_trace(
                            go.Bar(
                                x=indicator_data.index,
                                y=indicator_data[column],
                                name=column,
                                marker_color=color,
                                opacity=0.7,
                            ),
                            row=indicator_row,
                            col=1,
                        )
                    else:
                        fig.add_trace(
                            go.Scatter(
                                x=indicator_data.index,
                                y=indicator_data[column],
                                mode='lines',
                                name=column,
                                line=dict(color=color, width=1.6),
                            ),
                            row=indicator_row,
                            col=1,
                        )
                
                # Добавляем горизонтальную линию на нуле (если один индикатор)
                if len(indicator_data.columns) == 1:
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=indicator_row, col=1)
                fig.update_yaxes(title_text="Indicator", row=indicator_row, col=1)

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
                volume_row = 2 if not has_indicators else 3
                fig.add_trace(
                    go.Bar(
                        x=price_window.index,
                        y=price_window['volume'],
                        name='Volume',
                        marker_color='rgba(100, 149, 237, 0.4)',
                    ),
                    row=volume_row,
                    col=1,
                )
                fig.update_yaxes(title_text='Volume', row=volume_row, col=1)

            # Применяем маску разрывов ко всем панелям
            if gap_mask:
                rangebreaks = [dict(bounds=gap) for gap in gap_mask]
                for row in range(1, rows + 1):
                    fig.update_xaxes(
                        type='date',
                        rangebreaks=rangebreaks,
                        row=row,
                        col=1
                    )
            else:
                for row in range(1, rows + 1):
                    fig.update_xaxes(type='date', row=row, col=1)

        # --- РЕЖИМ DENSE ---
        else:
            x_positions = list(range(len(price_window)))
            x_dates = price_window.index
            date_to_position = {date: pos for pos, date in enumerate(x_dates)}

            # Свечной график
            fig.add_trace(go.Candlestick(
                x=x_positions,
                open=price_window['open'],
                high=price_window['high'],
                low=price_window['low'],
                close=price_window['close'],
                name='Price',
            ), row=1, col=1)
            
            # Устанавливаем rangemode='normal' для оси Y цен, чтобы избежать "сплющивания"
            fig.update_yaxes(rangemode='normal', title_text="Price", row=1, col=1)

            # Индикаторы на отдельной панели (если есть)
            if has_indicators:
                indicator_row = 2
                palette = kwargs.get('indicator_palette', self.default_config['indicator_palette'])
                indicator_chart_types = kwargs.get('indicator_chart_types', {})
                default_chart_type = lambda col: 'bar' if 'hist' in col.lower() else 'line'
                
                for i, column in enumerate(indicator_data.columns):
                    color = palette[i % len(palette)]
                    chart_type = indicator_chart_types.get(column, default_chart_type(column))
                    
                    if chart_type == 'bar':
                        fig.add_trace(
                            go.Bar(
                                x=x_positions,
                                y=indicator_data[column],
                                name=column,
                                marker_color=color,
                                opacity=0.7,
                            ),
                            row=indicator_row,
                            col=1,
                        )
                    else:
                        fig.add_trace(
                            go.Scatter(
                                x=x_positions,
                                y=indicator_data[column],
                                mode='lines',
                                name=column,
                                line=dict(color=color, width=1.6),
                            ),
                            row=indicator_row,
                            col=1,
                        )
                
                # Добавляем горизонтальную линию на нуле (если один индикатор)
                if len(indicator_data.columns) == 1:
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=indicator_row, col=1)
                fig.update_yaxes(title_text="Indicator", row=indicator_row, col=1)

            # Заливка зоны (используем позиционные индексы)
            window_index = price_window.index
            zone_start_idx = max(0, window_meta['zone_left'] - window_meta['left_idx'])
            zone_end_idx = min(len(window_index) - 1, window_meta['zone_right'] - window_meta['left_idx'])
            if zone_start_idx <= zone_end_idx:
                x0_pos = zone_start_idx - 0.5
                x1_pos = zone_end_idx + 0.5
                zone_type = zone.get('type', 'bull')
                color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
                y0 = price_window['low'].min()
                y1 = price_window['high'].max()
                fig.add_shape(
                    type="rect",
                    x0=x0_pos,
                    y0=y0,
                    x1=x1_pos,
                    y1=y1,
                    fillcolor=color_config['fill'],
                    line=dict(color=color_config['line'], width=1),
                    layer="below",
                    xref="x",
                    row=1,
                    col=1
                )

            if show_volume:
                volume_row = 2 if not has_indicators else 3
                fig.add_trace(
                    go.Bar(
                        x=x_positions,
                        y=price_window['volume'],
                        name='Volume',
                        marker_color='rgba(100, 149, 237, 0.4)',
                    ),
                    row=volume_row,
                    col=1,
                )
                fig.update_yaxes(title_text='Volume', row=volume_row, col=1)

            # Умные метки времени для dense режима
            num_ticks_requested = xaxis_num_ticks
            if len(x_dates) > 0 and len(x_positions) > 0:
                time_range = (x_dates[-1] - x_dates[0]).total_seconds()
                data_points = len(x_positions)
                if time_range < 3600 * 24:
                    ideal_ticks = max(8, min(20, data_points // 30))
                elif time_range < 3600 * 24 * 7:
                    ideal_ticks = max(8, min(20, data_points // 6))
                elif time_range < 3600 * 24 * 30:
                    ideal_ticks = max(8, min(20, data_points // 2))
                else:
                    ideal_ticks = max(8, min(20, data_points // 10))
                num_ticks = max(8, min(num_ticks_requested, ideal_ticks, data_points))
            else:
                num_ticks = max(8, min(num_ticks_requested, len(x_positions)))
            tick_step = max(1, len(x_positions) // num_ticks) if num_ticks > 0 else 1
            tick_positions = x_positions[::tick_step]
            
            show_date, show_time, show_year_separately = True, True, False
            if len(x_dates) > 0:
                time_range = (x_dates[-1] - x_dates[0]).total_seconds()
                if time_range < 3600 * 24:
                    date_format, time_format, show_date = '%H:%M', '%H:%M', False
                elif time_range < 3600 * 24 * 7:
                    date_format, time_format = '%d.%m', '%H:%M'
                elif time_range < 3600 * 24 * 30:
                    date_format = '%d.%m'
                    unique_times = set(dt.strftime('%H:%M') for dt in x_dates if hasattr(dt, 'strftime'))
                    if len(unique_times) == 1:
                        time_format, show_time = '%d.%m', False
                    else:
                        time_format = '%H:%M'
                else:
                    date_format, time_format, show_time, show_year_separately = '%d.%m', '%d.%m', False, True
            else:
                date_format, time_format = '%d.%m', '%H:%M'
            
            tick_labels, prev_year = [], None
            for i in range(0, len(x_positions), tick_step):
                if i < len(x_dates):
                    date_obj, current_year = x_dates[i], x_dates[i].year
                    show_year = show_year_separately and (prev_year is None or current_year != prev_year)
                    date_str, time_str = date_obj.strftime(date_format), date_obj.strftime(time_format)
                    if show_year:
                        label = f"{date_str}<br><b>{current_year}</b>"
                    elif show_date and show_time and date_str != time_str:
                        label = f"{date_str}<br>{time_str}"
                    elif show_date:
                        label = date_str
                    else:
                        label = time_str
                    tick_labels.append(label)
                    prev_year = current_year
                else:
                    tick_labels.append('')
            
            # Применяем метки ко всем панелям
            for row in range(1, rows + 1):
                fig.update_xaxes(
                    tickmode='array',
                    tickvals=tick_positions,
                    ticktext=tick_labels,
                    tickangle=0,
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    row=row,
                    col=1
                )

        # Добавляем overlay свингов
        if kwargs.get('show_swings') or self.default_config.get('show_swings'):
            swing_context = self._resolve_swing_context(zone)
            if swing_context:
                zone_swings = self._get_zone_swings_safe(zone, swing_context)
                limit = kwargs.get('max_swings_to_display')
                if limit is not None and len(zone_swings) > limit:
                    zone_swings = zone_swings[:limit]
                    self.logger.warning(
                        "Zone %s has more than %s swing points; truncating display.",
                        zone.get('zone_id', '?'),
                        limit,
                    )
                if len(zone_swings) > 200:
                    self.logger.warning(
                        "Zone %s swing overlay has %s points. Rendering may be slow.",
                        zone.get('zone_id', '?'),
                        len(zone_swings),
                    )
                self._add_swing_overlay(fig, zone_swings, row=1, col=1, marker_size=kwargs.get('swing_marker_size', 10))
            else:
                self.logger.debug(
                    "Zone %s has no swing_context; ensure .with_swing_scope('global') was used.",
                    zone.get('zone_id', '?'),
            )

        # Аннотация для zone label (используем правильный x в зависимости от режима)
        if self.default_config['show_zone_labels']:
            window_index = price_window.index
            zone_start_idx = max(0, window_meta['zone_left'] - window_meta['left_idx'])
            if time_axis_mode == 'timeseries':
                zone_x = zone.get('start_time', window_index[zone_start_idx])
            else:
                zone_x = zone_start_idx
            fig.add_annotation(
                xref='x',
                yref='paper',
                x=zone_x,
                y=1.05,
                text=f"Zone {zone.get('zone_id', 'n/a')}",
                showarrow=False,
                font=dict(size=12, color='black'),
                bgcolor='rgba(255,255,255,0.8)',
                # NOTE: Не используем row/col с xref/yref, это может сбросить настройки осей
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

        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1.0),
            # NOTE: rangemode='normal' уже установлено через fig.update_yaxes() выше (строки 1082, 1187)
            # Повторная установка через yaxis=dict() перезаписывает domain, что ломает multi-panel layout
        )

        return fig

    def _create_plotly_zones_comparison(self,
                                        price_window: pd.DataFrame,
                                        zone_blocks: List[Dict[str, Any]],
                                        title: str,
                                        show_indicators: bool = True,
                                        show_volume: bool = True,
                                        indicator_chart_types: Optional[Dict[str, str]] = None,
                                        time_axis_mode: str = 'dense',
                                        **kwargs) -> go.Figure:
        """Создание сравнительного графика зон (Plotly)."""

        # Проверяем наличие данных volume и применяем параметр show_volume
        has_volume_data = 'volume' in price_window.columns and price_window['volume'].notna().any()
        show_volume = show_volume and has_volume_data
        
        # Проверяем, есть ли индикаторы хотя бы в одной зоне
        has_indicators = show_indicators and any(
            (not block['payload']['indicators'].empty)
            for block in zone_blocks
        )
        
        # Определяем количество панелей: цена + (индикаторы?) + (volume?)
        rows = 1
        if has_indicators:
            rows += 1
        if show_volume:
            rows += 1
        
        # Высота панелей
        volume_height = kwargs.get('volume_panel_height', self.default_config['volume_panel_height'])
        indicator_panel_height = kwargs.get('indicator_panel_height', 0.3)
        
        row_heights = [1.0]
        if rows == 2:
            if has_indicators:
                row_heights = [1 - indicator_panel_height, indicator_panel_height]
            else:  # только volume
                row_heights = [1 - volume_height, volume_height]
        elif rows == 3:
            # цена, индикаторы, volume
            row_heights = [
                1 - indicator_panel_height - volume_height,
                indicator_panel_height,
                volume_height
            ]

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

        # Формируем подписи для оси X в зависимости от режима
        tickvals: List[int] = []
        ticktext: List[str] = []
        
        if time_axis_mode == 'dense':
            # Режим dense: используем позиционные индексы с метками времени
            timestamp_series = price_window.get('__timestamp__')
            if timestamp_series is not None and len(price_window.index) > 0:
                timestamps = list(timestamp_series)
                positions = list(price_window.index)
                max_ticks = min(20, max(1, len(positions)))
                step = max(1, len(positions) // max_ticks)
                for i in range(0, len(positions), step):
                    ts = timestamps[i]
                    label = ts.strftime('%d.%m %H:%M') if hasattr(ts, 'strftime') else str(ts)
                    tickvals.append(positions[i])
                    ticktext.append(label)
                # Добавляем последний тик
                if positions[-1] not in tickvals:
                    ts = timestamps[-1]
                    label = ts.strftime('%d.%m %H:%M') if hasattr(ts, 'strftime') else str(ts)
                    tickvals.append(positions[-1])
                    ticktext.append(label)
        # Для режима 'timeseries' не устанавливаем tickvals/ticktext - Plotly использует автоматические метки

        # Добавляем зоны и собираем информацию о блоках
        for block_idx, block in enumerate(zone_blocks):
            payload = block['payload']
            zone = payload['zone']
            zone_type = zone.get('type', 'bull')
            color_config = self.zone_colors.get(zone_type, self.zone_colors['bull'])
            positions = block['positions']
            timestamps = block.get('timestamps') or []
            if not positions:
                continue
            
            zone_start = zone.get('start_time')
            zone_end = zone.get('end_time')

            zone_start_pos = positions[0]
            zone_end_pos = positions[-1]
            if zone_start is not None and timestamps:
                for pos, ts in zip(positions, timestamps):
                    if ts >= zone_start:
                        zone_start_pos = pos
                        break
            if zone_end is not None and timestamps:
                for pos, ts in zip(reversed(positions), reversed(timestamps)):
                    if ts <= zone_end:
                        zone_end_pos = pos
                        break

            x0 = zone_start_pos - 0.5
            x1 = zone_end_pos + 0.5

            # Прямоугольник зоны должен занимать всю высоту панели
            # Не ограничиваем по Y, чтобы прямоугольник был виден
            fig.add_vrect(
                x0=x0,
                x1=x1,
                fillcolor=color_config['fill'],
                line=dict(color=color_config['line'], width=1),
                layer="below",
                annotation_text=f"Zone {zone.get('zone_id', block_idx + 1)}",
                annotation_position="top left",
                row=1, col=1
            )

        # Добавляем индикаторы на отдельную панель (если есть)
        if has_indicators:
            indicator_row = 2
            chart_types = indicator_chart_types or {}
            default_chart_type = lambda col: 'bar' if 'hist' in col.lower() else 'line'
            
            for block_idx, block in enumerate(zone_blocks):
                payload = block['payload']
                indicators = payload['indicators']
                
                if indicators.empty or len(indicators.columns) == 0:
                    continue
                    
                positions = block['positions']
                timestamps = block.get('timestamps') or []
                zone_window = payload['window']
                indicators_aligned = indicators.reindex(zone_window.index)

                # Индикаторы отображаются для всего блока (с контекстом), а не только для зоны
                # Используем все позиции блока
                indicator_positions = positions
                indicator_values = indicators_aligned
                
                for j, column in enumerate(indicators_aligned.columns):
                    color = palette[(block_idx + j) % len(palette)]
                    chart_type = chart_types.get(column, default_chart_type(column))
                    
                    if chart_type == 'bar':
                        fig.add_trace(
                            go.Bar(
                                x=indicator_positions,
                                y=indicator_values[column],
                                name=f"{payload['zone'].get('zone_id', block_idx + 1)} · {column}",
                                marker_color=color,
                                opacity=0.7,
                            ),
                            row=indicator_row,
                            col=1,
                        )
                    else:
                        fig.add_trace(
                            go.Scatter(
                                x=indicator_positions,
                                y=indicator_values[column],
                                mode='lines',
                                name=f"{payload['zone'].get('zone_id', block_idx + 1)} · {column}",
                                line=dict(color=color, width=1.4),
                                opacity=0.85,
                            ),
                            row=indicator_row,
                            col=1,
                        )
            
            # Добавляем горизонтальную линию на нуле (если один индикатор)
            if len(zone_blocks) == 1 and len(zone_blocks[0]['payload']['indicators'].columns) == 1:
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=indicator_row, col=1)
            fig.update_yaxes(title_text="Indicator", row=indicator_row, col=1)

        if show_volume:
            volume_row = 2 if not has_indicators else 3
            fig.add_trace(
                go.Bar(
                    x=price_window.index,
                    y=price_window['volume'],
                    name='Volume',
                    marker_color='rgba(120, 120, 220, 0.35)',
                ),
                row=volume_row,
                col=1,
            )
            fig.update_yaxes(title_text='Volume', row=volume_row, col=1)

        fig.update_layout(
            title=title,
            width=self.default_config['width'],
            height=self.default_config['height'],
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1.0),
        )

        for row in range(1, rows + 1):
            if time_axis_mode == 'dense':
                # Режим dense: используем позиционные индексы с кастомными метками
                fig.update_xaxes(
                    tickmode='array' if tickvals else 'auto',
                    tickvals=tickvals if tickvals else None,
                    ticktext=ticktext if tickvals else None,
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    row=row,
                    col=1,
                    type='linear'
                )
            else:
                # Режим timeseries: используем datetime (если понадобится в будущем)
                fig.update_xaxes(
                    type='date',
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(128, 128, 128, 0.2)',
                    row=row,
                    col=1
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
