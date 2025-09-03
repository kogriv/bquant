"""
PRELOADED Indicators Module

Индикаторы для работы с уже готовыми данными.
Эти индикаторы извлекают значения, которые уже были рассчитаны
и встроены в данные (например, из sample-данных или предобработанных файлов).

Основные типы PRELOADED индикаторов:
- MACD (Moving Average Convergence Divergence)
- RSI (Relative Strength Index)
- Bollinger Bands
- Moving Averages
- Volume indicators
"""

from .macd import MACDPreloadedIndicator

__all__ = [
    "MACDPreloadedIndicator",
]

# Автоматическая регистрация в IndicatorFactory
try:
    from ..base import IndicatorFactory
    from .macd import MACDPreloadedIndicator
    
    # Регистрируем PRELOADED индикаторы
    IndicatorFactory.register_indicator("macd_preloaded", MACDPreloadedIndicator)
    
except Exception:
    pass  # Игнорируем ошибки при авторегистрации
