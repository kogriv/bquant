from pathlib import Path
import pandas as pd
import json
import logging

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.core.config import get_data_dir, set_data_dir, reset_directories_to_defaults
from bquant.data.loader import (
    load_ohlcv_data,
    load_symbol_data,
    load_xauusd_data,
    load_all_data_files,
    get_data_info,
    get_available_symbols,
    get_available_timeframes
)
from bquant.data.samples import (
    get_sample_data,
    list_datasets,
    get_dataset_info
)

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)


# Инициализируем симулятор. Описание берется как первый аргумент.
nb = NotebookSimulator("Демонстрация работы пакета bquant")

nb.step("Работа с индикаторами")

nb.info("BQuant поддерживает источники: PRELOADED, LIBRARY, CUSTOM")

df_sample_tv = get_sample_data('tv_xauusd_1h')

# Демонстрация PRELOADED MACD индикатора
nb.substep("PRELOADED MACD индикатор")

from bquant.indicators.preloaded import MACDPreloadedIndicator

nb.info("Демонстрация новых class methods:")

# Получаем информацию о классе без создания объекта
default_cols = MACDPreloadedIndicator.get_default_columns()
info = MACDPreloadedIndicator.get_info()

nb.log(f"Default columns: {default_cols}")
nb.log(f"Indicator type: {info['type']}")
nb.log(f"Description: {info['description']}")
nb.log(f"Required fields: {info['required_fields']}")
nb.log(f"Optional fields: {info['optional_fields']}")

# Создаем индикатор
macd_indicator = MACDPreloadedIndicator()
nb.log(f"Created indicator: {macd_indicator.name}")

# Извлекаем данные
nb.info("Extracting MACD data:")
macd_result = macd_indicator.calculate(df_sample_tv)
nb.log(f"Extracted {len(macd_result.data)} rows")
nb.log(f"Columns: {list(macd_result.data.columns)}")

# Значения
nb.log(macd_result.data.tail().to_string())

# Демонстрация всех методов
nb.info("Demonstrating all methods:")

# Валидация данных
is_valid = macd_indicator.validate_data(df_sample_tv)
nb.log(f"Data validation: {is_valid}")

# Статистика
stats = macd_indicator.get_statistics(df_sample_tv)
nb.log("Statistics:")
for col, col_stats in stats.items():
    nb.log(f"  {col}: min={col_stats['min']:.4f}, max={col_stats['max']:.4f}, mean={col_stats['mean']:.4f}")

# Анализ трендов
trending_up = macd_indicator.is_trending_up(df_sample_tv, column='macd')
trending_down = macd_indicator.is_trending_down(df_sample_tv, column='macd')
nb.log(f"MACD trending up: {trending_up}")
nb.log(f"MACD trending down: {trending_down}")

# Пересечения
crossovers = macd_indicator.get_crossovers(df_sample_tv)
nb.log(f"Bullish crossovers: {crossovers['bullish_crossovers']}")
nb.log(f"Bearish crossovers: {crossovers['bearish_crossovers']}")

# Метаданные
nb.log("Metadata:")
nb.log(f"  Source: {macd_result.metadata['source']}")
nb.log(f"  Method: {macd_result.metadata['calculation_method']}")
nb.log(f"  Extracted columns: {macd_result.metadata['extracted_columns']}")
nb.log(f"  Total records: {macd_result.metadata['total_records']}")

nb.wait()

# Демонстрация LIBRARY MACD индикатора
nb.substep("LIBRARY MACD индикатор")

from bquant.indicators.library import MACDLibraryIndicator

nb.info("LIBRARY индикатор использует внешние библиотеки (например, TA-Lib)")

# Создаем LIBRARY индикатор
macd_library = MACDLibraryIndicator(
    fast_period=12,
    slow_period=26,
    signal_period=9
)
nb.log(f"Created LIBRARY indicator: {macd_library.name}")

# Рассчитываем MACD
nb.info("Calculating MACD using library:")
macd_library_result = macd_library.calculate(df_sample_tv)
nb.log(f"Calculated {len(macd_library_result.data)} rows")
nb.log(f"Columns: {list(macd_library_result.data.columns)}")

# Значения
nb.log(macd_library_result.data.tail().to_string())

# Сравнение с PRELOADED
nb.info("Comparing LIBRARY vs PRELOADED:")
nb.log(f"PRELOADED columns: {list(macd_result.data.columns)}")
nb.log(f"LIBRARY columns: {list(macd_library_result.data.columns)}")

nb.wait()

# Демонстрация CUSTOM MACD индикатора
nb.substep("CUSTOM MACD индикатор")

from bquant.indicators.base import BaseIndicator, IndicatorResult, IndicatorConfig, IndicatorSource
import numpy as np

class CustomMACDIndicator(BaseIndicator):
    """Кастомный MACD индикатор с собственной логикой расчета"""
    
    def __init__(self, fast_period=12, slow_period=26, signal_period=9):
        config = IndicatorConfig(
            name='custom_macd',
            parameters={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'signal_period': signal_period
            },
            source=IndicatorSource.CUSTOM,
            columns=['macd', 'signal', 'histogram'],
            description=f'Custom MACD (fast={fast_period}, slow={slow_period}, signal={signal_period})'
        )
        super().__init__('custom_macd', config)
    
    @classmethod
    def get_default_columns(cls):
        return ['macd', 'signal', 'histogram']
    
    @classmethod
    def get_info(cls):
        return {
            'name': 'CustomMACDIndicator',
            'type': 'CUSTOM',
            'description': 'Custom MACD implementation with numpy',
            'default_columns': cls.get_default_columns(),
            'required_fields': {
                'close': 'Close price values (numeric)'
            },
            'usage_examples': {
                'basic': 'CustomMACDIndicator()',
                'custom_params': 'CustomMACDIndicator(fast_period=8, slow_period=21, signal_period=5)'
            }
        }
    
    def calculate(self, data, **kwargs):
        """Кастомный расчет MACD"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for custom MACD calculation")
        
        close_prices = data['close'].values
        fast_period = self.config.parameters['fast_period']
        slow_period = self.config.parameters['slow_period']
        signal_period = self.config.parameters['signal_period']
        
        # Простая реализация EMA
        def ema(prices, period):
            alpha = 2.0 / (period + 1)
            ema_values = np.zeros_like(prices)
            ema_values[0] = prices[0]
            for i in range(1, len(prices)):
                ema_values[i] = alpha * prices[i] + (1 - alpha) * ema_values[i-1]
            return ema_values
        
        # Рассчитываем EMA
        ema_fast = ema(close_prices, fast_period)
        ema_slow = ema(close_prices, slow_period)
        
        # MACD линия
        macd_line = ema_fast - ema_slow
        
        # Signal линия (EMA от MACD)
        signal_line = ema(macd_line, signal_period)
        
        # Histogram
        histogram = macd_line - signal_line
        
        # Создаем DataFrame
        result_data = pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }, index=data.index)
        
        return IndicatorResult(
            name=self.name,
            data=result_data,
            config=self.config,
            metadata={
                'source': 'custom',
                'calculation_method': 'numpy_ema',
                'parameters': self.config.parameters,
                'total_records': len(result_data)
            }
        )
    
    def validate_data(self, data):
        """Валидация данных для кастомного MACD"""
        if data.empty:
            return False
        
        if 'close' not in data.columns:
            return False
        
        if len(data) < max(self.config.parameters['fast_period'], 
                          self.config.parameters['slow_period']):
            return False
        
        return True

# Создаем кастомный индикатор
macd_custom = CustomMACDIndicator(fast_period=8, slow_period=21, signal_period=5)
nb.log(f"Created CUSTOM indicator: {macd_custom.name}")

# Получаем информацию о классе
custom_info = CustomMACDIndicator.get_info()
nb.log(f"CUSTOM indicator type: {custom_info['type']}")
nb.log(f"Required fields: {custom_info['required_fields']}")

# Рассчитываем MACD
nb.info("Calculating MACD using custom implementation:")
macd_custom_result = macd_custom.calculate(df_sample_tv)
nb.log(f"Calculated {len(macd_custom_result.data)} rows")
nb.log(f"Columns: {list(macd_custom_result.data.columns)}")

# Значения
nb.log(macd_custom_result.data.tail().to_string())

# Сравнение всех трех способов
nb.info("Comparison of all three approaches:")
nb.log(f"PRELOADED: {list(macd_result.data.columns)} - {len(macd_result.data)} rows")
nb.log(f"LIBRARY: {list(macd_library_result.data.columns)} - {len(macd_library_result.data)} rows")
nb.log(f"CUSTOM: {list(macd_custom_result.data.columns)} - {len(macd_custom_result.data)} rows")

nb.wait()