"""
Zone Analysis Presets - Convenience Wrappers

Удобные shortcuts для частых сценариев анализа зон.

Каждая функция - тонкая обертка (5-10 строк) поверх универсального
analyze_zones() API для упрощения работы с популярными индикаторами.

Example:
    # Вместо:
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .analyze(clustering=True)
        .build()
    )
    
    # Можно использовать:
    from bquant.analysis.zones.presets import analyze_macd_zones
    result = analyze_macd_zones(df, fast=12, slow=26, signal=9, clustering=True)

Note:
    Эти функции предназначены для быстрого старта и простых сценариев.
    Для более сложных случаев используйте напрямую analyze_zones() builder.
"""

from typing import Optional, Union, Any
import pandas as pd
from pathlib import Path

from .pipeline import analyze_zones
from .models import ZoneAnalysisResult


def analyze_macd_zones(df: pd.DataFrame,
                       fast: int = 12,
                       slow: int = 26,
                       signal: int = 9,
                       min_duration: int = 2,
                       zone_types: Optional[list] = None,
                       smooth_window: Optional[int] = None,
                       clustering: bool = True,
                       n_clusters: int = 3,
                       regression: bool = False,
                       validation: bool = False,
                       enable_cache: bool = True,
                       cache_ttl: int = 3600) -> ZoneAnalysisResult:
    """
    Convenience wrapper для анализа MACD зон.
    
    Использует:
    - Indicator: 'custom' MACD с параметрами fast/slow/signal
    - Detection: 'zero_crossing' стратегия (пересечение нулевой линии)
    - Analysis: полный набор (features, statistics, hypothesis tests, sequences)
    
    Args:
        df: DataFrame с OHLCV данными
        fast: Быстрый период MACD (default: 12)
        slow: Медленный период MACD (default: 26)
        signal: Период сигнальной линии (default: 9)
        min_duration: Минимальная длительность зоны в барах (default: 2)
        zone_types: Типы зон для анализа (default: ['bull', 'bear'])
        smooth_window: Окно сглаживания для детекции (optional)
        clustering: Выполнять кластеризацию (default: True)
        n_clusters: Количество кластеров (default: 3)
        regression: Запустить регрессионный анализ (default: False)
        validation: Запустить валидацию (default: False)
        enable_cache: Использовать кэширование (default: True)
        cache_ttl: Время жизни кэша в секундах (default: 3600)
    
    Returns:
        ZoneAnalysisResult с полным анализом MACD зон
    
    Example:
        from bquant.analysis.zones.presets import analyze_macd_zones
        
        # Базовый анализ
        result = analyze_macd_zones(df)
        
        # С кастомными параметрами
        result = analyze_macd_zones(
            df, 
            fast=10, slow=20, signal=5,
            min_duration=5,
            clustering=True,
            regression=True
        )
        
        # Визуализация
        result.visualize('overview')
    """
    builder = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', 
                       fast_period=fast, 
                       slow_period=slow, 
                       signal_period=signal)
        .detect_zones('zero_crossing', 
                     indicator_col='macd_hist',
                     min_duration=min_duration,
                     zone_types=zone_types,
                     smooth_window=smooth_window)
        .analyze(clustering=clustering,
                n_clusters=n_clusters,
                regression=regression,
                validation=validation)
        .with_cache(enable=enable_cache, ttl=cache_ttl)
    )
    
    return builder.build()


def analyze_rsi_zones(df: pd.DataFrame,
                      period: int = 14,
                      upper_threshold: float = 70,
                      lower_threshold: float = 30,
                      min_duration: int = 2,
                      zone_types: Optional[list] = None,
                      clustering: bool = True,
                      n_clusters: int = 3,
                      regression: bool = False,
                      validation: bool = False,
                      enable_cache: bool = True,
                      cache_ttl: int = 3600) -> ZoneAnalysisResult:
    """
    Convenience wrapper для анализа RSI зон.
    
    Использует:
    - Indicator: 'pandas_ta' RSI с заданным периодом
    - Detection: 'threshold' стратегия (зоны перекупленности/перепроданности)
    - Analysis: полный набор
    
    Args:
        df: DataFrame с OHLCV данными
        period: Период RSI (default: 14)
        upper_threshold: Порог перекупленности (default: 70)
        lower_threshold: Порог перепроданности (default: 30)
        min_duration: Минимальная длительность зоны (default: 2)
        zone_types: Типы зон (default: ['overbought', 'neutral', 'oversold'])
        clustering: Выполнять кластеризацию (default: True)
        n_clusters: Количество кластеров (default: 3)
        regression: Запустить регрессионный анализ (default: False)
        validation: Запустить валидацию (default: False)
        enable_cache: Использовать кэширование (default: True)
        cache_ttl: Время жизни кэша в секундах (default: 3600)
    
    Returns:
        ZoneAnalysisResult с полным анализом RSI зон
    
    Example:
        from bquant.analysis.zones.presets import analyze_rsi_zones
        
        # Стандартные параметры
        result = analyze_rsi_zones(df)
        
        # Более строгие пороги
        result = analyze_rsi_zones(
            df,
            upper_threshold=80,
            lower_threshold=20,
            min_duration=3
        )
    """
    builder = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'rsi', length=period)
        .detect_zones('threshold',
                     indicator_col='RSI_14' if period == 14 else f'RSI_{period}',
                     upper_threshold=upper_threshold,
                     lower_threshold=lower_threshold,
                     min_duration=min_duration,
                     zone_types=zone_types)
        .analyze(clustering=clustering,
                n_clusters=n_clusters,
                regression=regression,
                validation=validation)
        .with_cache(enable=enable_cache, ttl=cache_ttl)
    )
    
    return builder.build()


def analyze_ao_zones(df: pd.DataFrame,
                     fast: int = 5,
                     slow: int = 34,
                     min_duration: int = 2,
                     zone_types: Optional[list] = None,
                     smooth_window: Optional[int] = None,
                     clustering: bool = True,
                     n_clusters: int = 3,
                     regression: bool = False,
                     validation: bool = False,
                     enable_cache: bool = True,
                     cache_ttl: int = 3600) -> ZoneAnalysisResult:
    """
    Convenience wrapper для анализа Awesome Oscillator зон.
    
    Использует:
    - Indicator: 'pandas_ta' AO с периодами fast/slow
    - Detection: 'zero_crossing' стратегия (пересечение нулевой линии)
    - Analysis: полный набор
    
    Args:
        df: DataFrame с OHLCV данными
        fast: Быстрый период (default: 5)
        slow: Медленный период (default: 34)
        min_duration: Минимальная длительность зоны (default: 2)
        zone_types: Типы зон для анализа (default: ['bull', 'bear'])
        smooth_window: Окно сглаживания для детекции (optional)
        clustering: Выполнять кластеризацию (default: True)
        n_clusters: Количество кластеров (default: 3)
        regression: Запустить регрессионный анализ (default: False)
        validation: Запустить валидацию (default: False)
        enable_cache: Использовать кэширование (default: True)
        cache_ttl: Время жизни кэша в секундах (default: 3600)
    
    Returns:
        ZoneAnalysisResult с полным анализом AO зон
    
    Example:
        from bquant.analysis.zones.presets import analyze_ao_zones
        
        # Стандартные параметры
        result = analyze_ao_zones(df)
        
        # Кастомные периоды
        result = analyze_ao_zones(df, fast=7, slow=21, min_duration=3)
    """
    # Note: pandas_ta AO naming convention is AO_{fast}_{slow}
    ao_col = f'AO_{fast}_{slow}'
    
    builder = (
        analyze_zones(df)
        .with_indicator('pandas_ta', 'ao', fast=fast, slow=slow)
        .detect_zones('zero_crossing',
                     indicator_col=ao_col,
                     min_duration=min_duration,
                     zone_types=zone_types,
                     smooth_window=smooth_window)
        .analyze(clustering=clustering,
                n_clusters=n_clusters,
                regression=regression,
                validation=validation)
        .with_cache(enable=enable_cache, ttl=cache_ttl)
    )
    
    return builder.build()


def analyze_preloaded_zones(df: pd.DataFrame,
                            zones_data: Union[str, Path, pd.DataFrame],
                            clustering: bool = True,
                            n_clusters: int = 3,
                            regression: bool = False,
                            validation: bool = False,
                            enable_cache: bool = True,
                            cache_ttl: int = 3600) -> ZoneAnalysisResult:
    """
    Convenience wrapper для анализа предзагруженных зон.
    
    Использует:
    - Detection: 'preloaded' стратегия (зоны из внешнего источника)
    - Analysis: полный набор
    
    Args:
        df: DataFrame с OHLCV данными
        zones_data: Путь к CSV файлу или DataFrame с зонами
            Требуемые колонки: start_time, end_time, type
            Опциональные: zone_id, start_idx, end_idx, duration
        clustering: Выполнять кластеризацию (default: True)
        n_clusters: Количество кластеров (default: 3)
        regression: Запустить регрессионный анализ (default: False)
        validation: Запустить валидацию (default: False)
        enable_cache: Использовать кэширование (default: True)
        cache_ttl: Время жизни кэша в секундах (default: 3600)
    
    Returns:
        ZoneAnalysisResult с полным анализом предзагруженных зон
    
    Example:
        from bquant.analysis.zones.presets import analyze_preloaded_zones
        
        # Из CSV файла
        result = analyze_preloaded_zones(df, 'zones/my_zones.csv')
        
        # Из DataFrame
        zones_df = pd.DataFrame({
            'start_time': [...],
            'end_time': [...],
            'type': ['bull', 'bear', ...]
        })
        result = analyze_preloaded_zones(df, zones_df, clustering=False)
    """
    builder = (
        analyze_zones(df)
        .detect_zones('preloaded', zones_data=zones_data)
        .analyze(clustering=clustering,
                n_clusters=n_clusters,
                regression=regression,
                validation=validation)
        .with_cache(enable=enable_cache, ttl=cache_ttl)
    )
    
    return builder.build()


# Export all preset functions
__all__ = [
    'analyze_macd_zones',
    'analyze_rsi_zones',
    'analyze_ao_zones',
    'analyze_preloaded_zones'
]

