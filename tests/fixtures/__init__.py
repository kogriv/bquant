"""
BQuant Test Fixtures

Общие fixtures и тестовые данные для всех типов тестов.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

def create_sample_ohlcv_data(periods: int = 100, freq: str = 'H') -> pd.DataFrame:
    """
    Создать sample OHLCV данные для тестирования.
    
    Args:
        periods: Количество периодов
        freq: Частота данных ('H', 'D', etc.)
    
    Returns:
        DataFrame с OHLCV данными
    """
    # Создаем временной индекс
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=periods if freq == 'H' else periods*24)
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)[:periods]
    
    # Генерируем случайные цены с трендом
    np.random.seed(42)  # Для воспроизводимости
    
    base_price = 2000.0
    price_changes = np.random.normal(0, 10, periods)
    trend = np.linspace(0, 50, periods)  # Небольшой восходящий тренд
    
    # Создаем цены закрытия
    closes = base_price + np.cumsum(price_changes) + trend
    
    # Создаем остальные цены
    high_offset = np.random.uniform(5, 20, periods)
    low_offset = np.random.uniform(5, 20, periods)
    open_offset = np.random.uniform(-5, 5, periods)
    
    highs = closes + high_offset
    lows = closes - low_offset
    opens = np.roll(closes, 1) + open_offset
    opens[0] = closes[0] + open_offset[0]
    
    # Создаем объемы
    volumes = np.random.uniform(1000, 10000, periods)
    
    # Собираем DataFrame
    df = pd.DataFrame({
        'time': date_range,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    # Устанавливаем time как индекс
    df.set_index('time', inplace=True)
    
    return df


def create_sample_macd_data(periods: int = 100) -> pd.DataFrame:
    """
    Создать sample данные с рассчитанными MACD индикаторами.
    
    Args:
        periods: Количество периодов
    
    Returns:
        DataFrame с OHLCV и MACD данными
    """
    # Создаем базовые OHLCV данные
    df = create_sample_ohlcv_data(periods)
    
    # Рассчитываем простые MACD
    ema_12 = df['close'].ewm(span=12).mean()
    ema_26 = df['close'].ewm(span=26).mean()
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal
    
    # Добавляем MACD данные
    df['macd'] = macd
    df['signal'] = signal
    df['histogram'] = histogram
    
    # Добавляем ATR для зон
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    df['atr'] = true_range.rolling(window=14).mean()
    
    return df


def create_sample_zones_data() -> List[Dict[str, Any]]:
    """
    Создать sample данные зон для тестирования.
    
    Returns:
        Список зон с характеристиками
    """
    zones = [
        {
            'zone_id': 1,
            'type': 'bull',
            'start_idx': 10,
            'end_idx': 25,
            'duration': 15,
            'start_time': datetime(2025, 1, 1, 10, 0),
            'end_time': datetime(2025, 1, 2, 1, 0),
            'features': {
                'duration': 15,
                'price_return': 0.045,
                'volatility': 0.023,
                'volume_mean': 5500,
                'slope': 0.12
            }
        },
        {
            'zone_id': 2,
            'type': 'bear',
            'start_idx': 30,
            'end_idx': 42,
            'duration': 12,
            'start_time': datetime(2025, 1, 2, 6, 0),
            'end_time': datetime(2025, 1, 2, 18, 0),
            'features': {
                'duration': 12,
                'price_return': -0.032,
                'volatility': 0.019,
                'volume_mean': 4800,
                'slope': -0.08
            }
        },
        {
            'zone_id': 3,
            'type': 'bull',
            'start_idx': 50,
            'end_idx': 68,
            'duration': 18,
            'start_time': datetime(2025, 1, 3, 2, 0),
            'end_time': datetime(2025, 1, 3, 20, 0),
            'features': {
                'duration': 18,
                'price_return': 0.067,
                'volatility': 0.028,
                'volume_mean': 6200,
                'slope': 0.15
            }
        }
    ]
    
    return zones


def create_sample_analysis_results() -> Dict[str, Any]:
    """
    Создать sample результаты анализа для тестирования.
    
    Returns:
        Словарь с результатами анализа
    """
    return {
        'metadata': {
            'symbol': 'TEST_SYMBOL',
            'timeframe': '1h',
            'analysis_date': datetime.now().isoformat(),
            'analysis_duration_seconds': 2.5,
            'bquant_version': '0.0.0-test'
        },
        'data_info': {
            'total_periods': 100,
            'data_start': '2025-01-01T00:00:00',
            'data_end': '2025-01-05T00:00:00',
            'price_range': {
                'min': 1980.5,
                'max': 2120.8,
                'current': 2067.3
            }
        },
        'macd_analysis': {
            'zones_statistics': {
                'total_zones': 3,
                'bull_zones': 2,
                'bear_zones': 1,
                'avg_duration': 15.0
            },
            'macd_statistics': {
                'current_macd': 12.45,
                'current_signal': 8.32,
                'current_histogram': 4.13
            }
        },
        'summary': {
            'recommendation': 'BULLISH: Current uptrend with positive MACD momentum',
            'key_insights': [
                'Predominantly bullish market sentiment',
                'Long-duration zones indicate strong trends',
                'Strong MACD momentum detected'
            ]
        }
    }


class TestDataFixtures:
    """
    Класс с готовыми fixtures для различных типов тестирования.
    """
    
    @staticmethod
    def small_ohlcv(periods: int = 50) -> pd.DataFrame:
        """Небольшой dataset для быстрых тестов."""
        return create_sample_ohlcv_data(periods)
    
    @staticmethod
    def large_ohlcv(periods: int = 1000) -> pd.DataFrame:
        """Большой dataset для performance тестов."""
        return create_sample_ohlcv_data(periods)
    
    @staticmethod
    def macd_with_zones(periods: int = 100) -> pd.DataFrame:
        """Dataset с MACD данными для тестирования зон."""
        return create_sample_macd_data(periods)
    
    @staticmethod
    def sample_zones() -> List[Dict[str, Any]]:
        """Sample зоны для тестирования анализа."""
        return create_sample_zones_data()
    
    @staticmethod
    def analysis_results() -> Dict[str, Any]:
        """Sample результаты анализа."""
        return create_sample_analysis_results()


# Константы для тестирования
TEST_SYMBOLS = ['XAUUSD', 'EURUSD', 'BTCUSD', 'TEST_SYMBOL']
TEST_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
TEST_PERIODS = [50, 100, 500, 1000]

# Параметры для различных типов тестов
MACD_PARAMS = {
    'fast': 12,
    'slow': 26,
    'signal': 9
}

ZONE_PARAMS = {
    'min_duration': 2,
    'min_amplitude': 0.001,
    'normalization_method': 'atr',
    'detection_method': 'sign_change'
}

PERFORMANCE_THRESHOLDS = {
    'macd_calculation_max_time': 5.0,  # секунд
    'zone_identification_max_time': 10.0,  # секунд
    'statistical_analysis_max_time': 15.0,  # секунд
    'visualization_max_time': 20.0  # секунд
}
