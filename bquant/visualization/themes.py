"""
Модуль тем оформления BQuant

Предоставляет различные темы оформления для графиков:
- Светлые и темные темы
- Финансовые цветовые схемы
- Настраиваемые стили
- Консистентность оформления
"""

from typing import Dict, Any, List, Optional, Union
import warnings

from ..core.logging_config import get_logger

# Получаем логгер для модуля
logger = get_logger(__name__)

# Проверка доступности библиотек
try:
    import plotly.graph_objects as go
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available - themes functionality will be limited")

try:
    import matplotlib.pyplot as plt
    import matplotlib.style as mplstyle
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - themes functionality will be limited")


class ChartThemes:
    """
    Класс для управления темами оформления графиков.
    """
    
    def __init__(self):
        """Инициализация менеджера тем."""
        self.logger = get_logger(f"{__name__}.ChartThemes")
        
        # Определяем доступные темы
        self._themes = {
            'bquant_light': self._get_bquant_light_theme(),
            'bquant_dark': self._get_bquant_dark_theme(),
            'financial': self._get_financial_theme(),
            'minimal': self._get_minimal_theme(),
            'professional': self._get_professional_theme()
        }
        
        # Текущая тема по умолчанию
        self._current_theme = 'bquant_light'
        
        self.logger.info(f"Chart themes initialized with {len(self._themes)} available themes")
    
    def get_available_themes(self) -> List[str]:
        """
        Получить список доступных тем.
        
        Returns:
            Список названий тем
        """
        return list(self._themes.keys())
    
    def get_theme(self, theme_name: str) -> Dict[str, Any]:
        """
        Получить конфигурацию темы.
        
        Args:
            theme_name: Название темы
        
        Returns:
            Словарь с конфигурацией темы
        """
        if theme_name not in self._themes:
            self.logger.warning(f"Theme '{theme_name}' not found, using default")
            theme_name = self._current_theme
        
        return self._themes[theme_name].copy()
    
    def set_default_theme(self, theme_name: str) -> bool:
        """
        Установить тему по умолчанию.
        
        Args:
            theme_name: Название темы
        
        Returns:
            True если тема успешно установлена
        """
        if theme_name not in self._themes:
            self.logger.error(f"Theme '{theme_name}' not found")
            return False
        
        self._current_theme = theme_name
        self.logger.info(f"Default theme set to: {theme_name}")
        
        # Применяем тему к библиотекам
        self._apply_theme_to_libraries(theme_name)
        
        return True
    
    def apply_theme_to_figure(self, fig: Union[go.Figure, plt.Figure], 
                             theme_name: str = None) -> Union[go.Figure, plt.Figure]:
        """
        Применить тему к конкретному графику.
        
        Args:
            fig: Объект графика
            theme_name: Название темы (если None, используется текущая)
        
        Returns:
            Обновленный объект графика
        """
        if theme_name is None:
            theme_name = self._current_theme
        
        theme_config = self.get_theme(theme_name)
        
        if PLOTLY_AVAILABLE and isinstance(fig, go.Figure):
            return self._apply_plotly_theme(fig, theme_config)
        elif MATPLOTLIB_AVAILABLE and hasattr(fig, 'patch'):
            return self._apply_matplotlib_theme(fig, theme_config)
        else:
            self.logger.warning("Unsupported figure type for theme application")
            return fig
    
    def _apply_theme_to_libraries(self, theme_name: str):
        """Применить тему к библиотекам визуализации."""
        theme_config = self.get_theme(theme_name)
        
        # Plotly
        if PLOTLY_AVAILABLE:
            try:
                plotly_template = self._create_plotly_template(theme_config)
                pio.templates['bquant_custom'] = plotly_template
                pio.templates.default = 'bquant_custom'
                self.logger.debug(f"Applied {theme_name} theme to Plotly")
            except Exception as e:
                self.logger.warning(f"Failed to apply theme to Plotly: {e}")
        
        # Matplotlib
        if MATPLOTLIB_AVAILABLE:
            try:
                self._apply_matplotlib_rcparams(theme_config)
                self.logger.debug(f"Applied {theme_name} theme to Matplotlib")
            except Exception as e:
                self.logger.warning(f"Failed to apply theme to Matplotlib: {e}")
    
    def _apply_plotly_theme(self, fig: go.Figure, theme_config: Dict[str, Any]) -> go.Figure:
        """Применить тему к Plotly графику."""
        colors = theme_config.get('colors', {})
        layout = theme_config.get('layout', {})
        
        # Обновляем layout
        fig.update_layout(
            plot_bgcolor=colors.get('background', '#ffffff'),
            paper_bgcolor=colors.get('paper', '#ffffff'),
            font=dict(
                family=layout.get('font_family', 'Arial'),
                size=layout.get('font_size', 12),
                color=colors.get('text', '#000000')
            ),
            title_font=dict(
                size=layout.get('title_font_size', 16),
                color=colors.get('text', '#000000')
            ),
            showlegend=layout.get('show_legend', True),
            legend=dict(
                bgcolor=colors.get('legend_bg', 'rgba(255,255,255,0.8)'),
                bordercolor=colors.get('legend_border', '#cccccc'),
                borderwidth=1
            )
        )
        
        # Обновляем оси
        axis_config = dict(
            gridcolor=colors.get('grid', '#eeeeee'),
            linecolor=colors.get('axis_line', '#cccccc'),
            tickcolor=colors.get('tick', '#cccccc'),
            title=dict(font=dict(color=colors.get('text', '#000000'))),
            tickfont=dict(color=colors.get('text', '#000000'))
        )
        
        fig.update_xaxes(**axis_config)
        fig.update_yaxes(**axis_config)
        
        return fig
    
    def _apply_matplotlib_theme(self, fig: plt.Figure, theme_config: Dict[str, Any]) -> plt.Figure:
        """Применить тему к Matplotlib графику."""
        colors = theme_config.get('colors', {})
        layout = theme_config.get('layout', {})
        
        # Применяем настройки к figure
        fig.patch.set_facecolor(colors.get('paper', '#ffffff'))
        
        # Применяем к осям
        for ax in fig.get_axes():
            ax.set_facecolor(colors.get('background', '#ffffff'))
            
            # Цвета осей и сетки
            ax.tick_params(colors=colors.get('text', '#000000'))
            ax.grid(True, color=colors.get('grid', '#eeeeee'), alpha=0.7)
            ax.spines['bottom'].set_color(colors.get('axis_line', '#cccccc'))
            ax.spines['top'].set_color(colors.get('axis_line', '#cccccc'))
            ax.spines['right'].set_color(colors.get('axis_line', '#cccccc'))
            ax.spines['left'].set_color(colors.get('axis_line', '#cccccc'))
            
            # Заголовки
            ax.title.set_color(colors.get('text', '#000000'))
            ax.xaxis.label.set_color(colors.get('text', '#000000'))
            ax.yaxis.label.set_color(colors.get('text', '#000000'))
        
        return fig
    
    def _create_plotly_template(self, theme_config: Dict[str, Any]) -> go.layout.Template:
        """Создать Plotly template из конфигурации темы."""
        colors = theme_config.get('colors', {})
        layout = theme_config.get('layout', {})
        
        template = go.layout.Template()
        
        # Layout настройки
        template.layout = go.Layout(
            font=dict(
                family=layout.get('font_family', 'Arial'),
                size=layout.get('font_size', 12),
                color=colors.get('text', '#000000')
            ),
            title_font=dict(
                size=layout.get('title_font_size', 16)
            ),
            plot_bgcolor=colors.get('background', '#ffffff'),
            paper_bgcolor=colors.get('paper', '#ffffff'),
            colorway=theme_config.get('color_sequence', [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
            ])
        )
        
        # Оси
        axis_template = dict(
            gridcolor=colors.get('grid', '#eeeeee'),
            linecolor=colors.get('axis_line', '#cccccc'),
            tickcolor=colors.get('tick', '#cccccc'),
            zerolinecolor=colors.get('zero_line', '#cccccc')
        )
        
        template.layout.xaxis = axis_template
        template.layout.yaxis = axis_template
        
        return template
    
    def _apply_matplotlib_rcparams(self, theme_config: Dict[str, Any]):
        """Применить настройки темы к matplotlib rcParams."""
        colors = theme_config.get('colors', {})
        layout = theme_config.get('layout', {})
        
        # Обновляем rcParams
        plt.rcParams.update({
            'figure.facecolor': colors.get('paper', '#ffffff'),
            'axes.facecolor': colors.get('background', '#ffffff'),
            'axes.edgecolor': colors.get('axis_line', '#cccccc'),
            'axes.labelcolor': colors.get('text', '#000000'),
            'xtick.color': colors.get('text', '#000000'),
            'ytick.color': colors.get('text', '#000000'),
            'text.color': colors.get('text', '#000000'),
            'grid.color': colors.get('grid', '#eeeeee'),
            'font.family': layout.get('font_family', 'sans-serif'),
            'font.size': layout.get('font_size', 12),
            'axes.titlesize': layout.get('title_font_size', 16),
            'figure.titlesize': layout.get('title_font_size', 16)
        })
    
    # Определения тем
    def _get_bquant_light_theme(self) -> Dict[str, Any]:
        """Светлая тема BQuant."""
        return {
            'name': 'BQuant Light',
            'colors': {
                'background': '#ffffff',
                'paper': '#fafafa',
                'text': '#2c3e50',
                'grid': '#ecf0f1',
                'axis_line': '#bdc3c7',
                'tick': '#7f8c8d',
                'zero_line': '#95a5a6',
                'legend_bg': 'rgba(255,255,255,0.9)',
                'legend_border': '#bdc3c7',
                'bullish': '#27ae60',
                'bearish': '#e74c3c',
                'neutral': '#3498db',
                'volume': '#95a5a6',
                'swing_peak': '#d62728',
                'swing_trough': '#2ca02c',
            },
            'layout': {
                'font_family': 'Segoe UI, Arial, sans-serif',
                'font_size': 12,
                'title_font_size': 16,
                'show_legend': True,
                'grid_alpha': 0.3
            },
            'color_sequence': [
                '#3498db', '#e74c3c', '#27ae60', '#f39c12',
                '#9b59b6', '#1abc9c', '#34495e', '#e67e22'
            ]
        }
    
    def _get_bquant_dark_theme(self) -> Dict[str, Any]:
        """Темная тема BQuant."""
        return {
            'name': 'BQuant Dark',
            'colors': {
                'background': '#2c3e50',
                'paper': '#34495e',
                'text': '#ecf0f1',
                'grid': '#4a5f7a',
                'axis_line': '#7f8c8d',
                'tick': '#bdc3c7',
                'zero_line': '#95a5a6',
                'legend_bg': 'rgba(52,73,94,0.9)',
                'legend_border': '#7f8c8d',
                'bullish': '#2ecc71',
                'bearish': '#e74c3c',
                'neutral': '#3498db',
                'volume': '#95a5a6',
                'swing_peak': '#ff6b6b',
                'swing_trough': '#1abc9c',
            },
            'layout': {
                'font_family': 'Segoe UI, Arial, sans-serif',
                'font_size': 12,
                'title_font_size': 16,
                'show_legend': True,
                'grid_alpha': 0.4
            },
            'color_sequence': [
                '#3498db', '#e74c3c', '#2ecc71', '#f39c12',
                '#9b59b6', '#1abc9c', '#ecf0f1', '#e67e22'
            ]
        }
    
    def _get_financial_theme(self) -> Dict[str, Any]:
        """Финансовая тема."""
        return {
            'name': 'Financial',
            'colors': {
                'background': '#ffffff',
                'paper': '#f8f9fa',
                'text': '#212529',
                'grid': '#dee2e6',
                'axis_line': '#6c757d',
                'tick': '#495057',
                'zero_line': '#6c757d',
                'legend_bg': 'rgba(248,249,250,0.95)',
                'legend_border': '#dee2e6',
                'bullish': '#198754',
                'bearish': '#dc3545',
                'neutral': '#0d6efd',
                'volume': '#6c757d',
                'swing_peak': '#c0392b',
                'swing_trough': '#27ae60',
            },
            'layout': {
                'font_family': 'Roboto, Helvetica, Arial, sans-serif',
                'font_size': 11,
                'title_font_size': 14,
                'show_legend': True,
                'grid_alpha': 0.5
            },
            'color_sequence': [
                '#0d6efd', '#dc3545', '#198754', '#fd7e14',
                '#6f42c1', '#20c997', '#212529', '#f77b72'
            ]
        }
    
    def _get_minimal_theme(self) -> Dict[str, Any]:
        """Минималистичная тема."""
        return {
            'name': 'Minimal',
            'colors': {
                'background': '#ffffff',
                'paper': '#ffffff',
                'text': '#333333',
                'grid': '#f0f0f0',
                'axis_line': '#cccccc',
                'tick': '#999999',
                'zero_line': '#cccccc',
                'legend_bg': 'rgba(255,255,255,0.8)',
                'legend_border': '#e0e0e0',
                'bullish': '#4caf50',
                'bearish': '#f44336',
                'neutral': '#2196f3',
                'volume': '#9e9e9e',
                'swing_peak': '#d32f2f',
                'swing_trough': '#388e3c',
            },
            'layout': {
                'font_family': 'Helvetica Neue, Arial, sans-serif',
                'font_size': 11,
                'title_font_size': 14,
                'show_legend': False,
                'grid_alpha': 0.2
            },
            'color_sequence': [
                '#2196f3', '#f44336', '#4caf50', '#ff9800',
                '#9c27b0', '#00bcd4', '#607d8b', '#795548'
            ]
        }
    
    def _get_professional_theme(self) -> Dict[str, Any]:
        """Профессиональная тема."""
        return {
            'name': 'Professional',
            'colors': {
                'background': '#fefefe',
                'paper': '#f5f5f5',
                'text': '#1a1a1a',
                'grid': '#e8e8e8',
                'axis_line': '#666666',
                'tick': '#4a4a4a',
                'zero_line': '#666666',
                'legend_bg': 'rgba(245,245,245,0.95)',
                'legend_border': '#cccccc',
                'bullish': '#2e7d32',
                'bearish': '#c62828',
                'neutral': '#1565c0',
                'volume': '#757575',
                'swing_peak': '#b71c1c',
                'swing_trough': '#1b5e20',
            },
            'layout': {
                'font_family': 'Times New Roman, serif',
                'font_size': 12,
                'title_font_size': 16,
                'show_legend': True,
                'grid_alpha': 0.4
            },
            'color_sequence': [
                '#1565c0', '#c62828', '#2e7d32', '#ef6c00',
                '#5e35b1', '#00838f', '#424242', '#d84315'
            ]
        }


# Глобальный экземпляр менеджера тем
_theme_manager = ChartThemes()


# Удобные функции
def get_available_themes() -> List[str]:
    """
    Получить список доступных тем.
    
    Returns:
        Список названий тем
    """
    return _theme_manager.get_available_themes()


def get_theme(theme_name: str) -> Dict[str, Any]:
    """
    Получить конфигурацию темы.
    
    Args:
        theme_name: Название темы
    
    Returns:
        Словарь с конфигурацией темы
    """
    return _theme_manager.get_theme(theme_name)


def apply_theme(theme_name: str) -> bool:
    """
    Применить тему ко всем последующим графикам.
    
    Args:
        theme_name: Название темы
    
    Returns:
        True если тема успешно применена
    """
    return _theme_manager.set_default_theme(theme_name)


def apply_theme_to_figure(fig: Union[go.Figure, plt.Figure], 
                         theme_name: str = None) -> Union[go.Figure, plt.Figure]:
    """
    Применить тему к конкретному графику.
    
    Args:
        fig: Объект графика
        theme_name: Название темы
    
    Returns:
        Обновленный объект графика
    """
    return _theme_manager.apply_theme_to_figure(fig, theme_name)


def get_theme_colors(theme_name: str = None) -> Dict[str, str]:
    """
    Получить цветовую схему темы.
    
    Args:
        theme_name: Название темы (если None, используется текущая)
    
    Returns:
        Словарь с цветами темы
    """
    if theme_name is None:
        theme_name = _theme_manager._current_theme
    
    theme_config = _theme_manager.get_theme(theme_name)
    return theme_config.get('colors', {})


def reset_theme():
    """Сбросить тему к значениям по умолчанию."""
    _theme_manager.set_default_theme('bquant_light')
    
    # Сброс matplotlib к defaults
    if MATPLOTLIB_AVAILABLE:
        plt.rcdefaults()
    
    logger.info("Theme reset to default")


def create_custom_theme(name: str, 
                       colors: Dict[str, str], 
                       layout: Dict[str, Any] = None) -> bool:
    """
    Создать пользовательскую тему.
    
    Args:
        name: Название темы
        colors: Словарь с цветами
        layout: Настройки макета (опционально)
    
    Returns:
        True если тема успешно создана
    """
    if layout is None:
        layout = {
            'font_family': 'Arial, sans-serif',
            'font_size': 12,
            'title_font_size': 16,
            'show_legend': True,
            'grid_alpha': 0.3
        }
    
    # Дополняем цвета значениями по умолчанию
    default_colors = _theme_manager._get_bquant_light_theme()['colors']
    full_colors = {**default_colors, **colors}
    
    custom_theme = {
        'name': name,
        'colors': full_colors,
        'layout': layout,
        'color_sequence': colors.get('color_sequence', default_colors.get('color_sequence', []))
    }
    
    _theme_manager._themes[name] = custom_theme
    logger.info(f"Custom theme '{name}' created")
    
    return True


def list_theme_info():
    """Вывести информацию о всех доступных темах."""
    themes = _theme_manager.get_available_themes()
    current = _theme_manager._current_theme
    
    print("Available BQuant Themes:")
    print("=" * 30)
    
    for theme_name in themes:
        theme_config = _theme_manager.get_theme(theme_name)
        status = " (current)" if theme_name == current else ""
        print(f"  • {theme_config['name']}{status}")
        print(f"    ID: {theme_name}")
        
        colors = theme_config.get('colors', {})
        if 'bullish' in colors and 'bearish' in colors:
            print(f"    Colors: Bullish({colors['bullish']}), Bearish({colors['bearish']})")
        
        print()


# Экспорт
__all__ = [
    'ChartThemes',
    'get_available_themes',
    'get_theme',
    'apply_theme', 
    'apply_theme_to_figure',
    'get_theme_colors',
    'reset_theme',
    'create_custom_theme',
    'list_theme_info'
]
