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

# Регистрация в IndicatorFactory — в одном месте, `bquant.indicators._bootstrap_registry()` (G64).
