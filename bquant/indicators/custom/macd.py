"""
Moving Average Convergence Divergence (MACD) Indicator

Custom implementation of MACD indicator for BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from ..base import CustomIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
from ...core.exceptions import IndicatorCalculationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class MACD(CustomIndicator):
    """
    Moving Average Convergence Divergence (MACD) indicator.
    
    Measures the relationship between two moving averages to identify momentum changes.
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize MACD indicator.
        
        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period  
            signal_period: Signal line EMA period
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        super().__init__('macd', {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period
        })
    
    def get_output_roles(self) -> Dict[str, str]:
        """Роль → колонка, которую этот экземпляр действительно выдаёт.

        **Это объявление**, а не производная: список колонок выводится отсюда
        (:meth:`get_output_columns`), а не пишется рядом вторым литералом. Два
        литерала — это два места, где можно разойтись, и этап A плана G8
        заводил тест-пин ровно на такое расхождение; теперь расходиться нечему.

        Имена — канонические (`macd_12_26_9__line`): слаг идентичности плюс роль.
        Так они несут параметры, с которыми ряд посчитан, и два экземпляра одного
        индикатора с разными настройками больше не претендуют на одну колонку.
        Раньше здесь стояли литералы `macd`/`macd_signal`/`macd_hist`, и первый
        из них **затирал** колонку `macd`, которую встроенный сэмпл несёт из
        выгрузки TradingView.
        """
        iid = self.get_indicator_id()
        return {role: iid.column(role) for role in ("line", "signal", "hist")}

    def get_output_columns(self) -> List[str]:
        """Колонки в порядке объявления ролей."""
        return list(self.get_output_roles().values())

    def get_description(self) -> str:
        """Returns indicator description."""
        return f"MACD ({self.fast_period}, {self.slow_period}, {self.signal_period})"
    
    def get_min_records(self) -> int:
        """Returns minimum records required."""
        return self.slow_period + self.signal_period
    
    def get_required_columns(self) -> List[str]:
        """Returns required input columns."""
        return ['close']
    
    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate MACD.
        
        Args:
            data: DataFrame with price data
            **kwargs: Additional parameters
        
        Returns:
            IndicatorResult with MACD values
        """
        try:
            self.validate_data(data)
            
            fast_period = kwargs.get('fast_period', self.fast_period)
            slow_period = kwargs.get('slow_period', self.slow_period)
            signal_period = kwargs.get('signal_period', self.signal_period)
            
            self.logger.info(f"Calculating MACD ({fast_period}, {slow_period}, {signal_period})")
            
            # Вычисляем быструю и медленную EMA
            fast_ema = data['close'].ewm(span=fast_period).mean()
            slow_ema = data['close'].ewm(span=slow_period).mean()
            
            # Вычисляем MACD линию
            macd_line = fast_ema - slow_ema
            
            # Вычисляем сигнальную линию
            signal_line = macd_line.ewm(span=signal_period).mean()
            
            # Вычисляем гистограмму
            histogram = macd_line - signal_line

            # Прогрев: значение, посчитанное на неполном окне, не публикуется (G45).
            # `ewm` определён с первого бара и потому отдаёт число там, где медленная
            # EMA ещё не набрала своих `slow_period` наблюдений. На нулевом баре обе
            # EMA равны одной и той же цене закрытия, поэтому линия там — ровно 0.0,
            # и детектор пересечений нуля читает это как сигнал. Маска той же формы,
            # что у SMA и BollingerBands в этом же пакете (`period-1`), и совпадает с
            # соглашением pandas-ta: линия `slow-1`, сигнал и гистограмма — плюс
            # прогрев самой сигнальной EMA.
            line_warmup = slow_period - 1
            signal_warmup = line_warmup + signal_period - 1
            macd_line.iloc[:line_warmup] = np.nan
            signal_line.iloc[:signal_warmup] = np.nan
            histogram.iloc[:signal_warmup] = np.nan

            # Имена берутся у идентичности, посчитанной по **фактическим**
            # параметрам этого вызова: `calculate(data, fast_period=5)` считает
            # не то, что объявлял конструктор, и колонка обязана это сказать.
            columns = self.get_indicator_id(
                fast_period=fast_period,
                slow_period=slow_period,
                signal_period=signal_period,
            )
            result_data = pd.DataFrame({
                columns.column('line'): macd_line,
                columns.column('signal'): signal_line,
                columns.column('hist'): histogram,
            }, index=data.index)
            
            return IndicatorResult(
                name=self.name,
                data=result_data,
                config=self.config,
                metadata={
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period,
                    'calculation_method': 'ema_difference',
                    'first_valid_index': result_data.first_valid_index(),
                    'last_valid_index': result_data.last_valid_index()
                }
            )
            
        except Exception as e:
            fast_period = kwargs.get('fast_period', self.fast_period)
            slow_period = kwargs.get('slow_period', self.slow_period)
            signal_period = kwargs.get('signal_period', self.signal_period)
            
            raise IndicatorCalculationError(
                f"Failed to calculate MACD: {e}",
                {
                    'indicator': self.name,
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period
                }
            )
    
    @classmethod
    def get_default_columns(cls) -> List[str]:
        """Колонки экземпляра с параметрами по умолчанию.

        Выводятся из объявления, а не перечисляются литералом: это метод класса,
        поэтому параметры он берёт из дефолтов конструктора. Список литералом был
        бы ещё одним местом, где живут имена выходов, — тем самым, из-за которого
        заведён G8.
        """
        return cls().get_output_columns()
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """Returns class information."""
        return {
            'name': 'MACD',
            'type': 'CUSTOM',
            'description': 'Moving Average Convergence Divergence indicator implementation',
            'default_columns': cls.get_default_columns(),
            'required_fields': {
                'close': 'Close price values (numeric)'
            },
            'optional_fields': {
                'high': 'High price values (numeric)',
                'low': 'Low price values (numeric)',
                'open': 'Open price values (numeric)'
            },
            'parameters': {
                'fast_period': 'Fast EMA period (default: 12)',
                'slow_period': 'Slow EMA period (default: 26)',
                'signal_period': 'Signal line EMA period (default: 9)'
            },
            'usage_examples': {
                'basic': "MACD()",
                'custom_periods': "MACD(fast_period=10, slow_period=21, signal_period=7)"
            },
            'data_requirements': {
                'min_records': 35,
                'column_types': 'numeric',
                'required_columns': ['close']
            },
            'available_methods': [
                'calculate()',
                'validate_data()',
                'get_statistics()',
                'is_trending_up()',
                'is_trending_down()',
                'get_crossovers()'
            ],
            'interpretation': {
                'macd_line': 'Difference between fast and slow EMA',
                'signal_line': 'EMA of MACD line',
                'histogram': 'MACD line minus signal line',
                'bullish_crossover': 'MACD crosses above signal line',
                'bearish_crossover': 'MACD crosses below signal line'
            }
        }
