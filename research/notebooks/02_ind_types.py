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
nb = NotebookSimulator("Демонстрация работы с новой архитектурой индикаторов BQuant")

nb.step("Обзор новой архитектуры индикаторов")

nb.info("BQuant поддерживает три источника индикаторов:")
nb.info("1. PRELOADED - готовые индикаторы для работы с предзагруженными данными")
nb.info("2. LIBRARY - индикаторы на основе внешних библиотек (TA-Lib, pandas-ta)")
nb.info("3. CUSTOM - пользовательские индикаторы с собственной логикой расчета")

df_sample_tv = get_sample_data('tv_xauusd_1h')
nb.log(f"Загружены тестовые данные: {len(df_sample_tv)} строк, колонки: {list(df_sample_tv.columns)}")

nb.wait()

# Демонстрация PRELOADED индикаторов
nb.substep("PRELOADED индикаторы")

from bquant.indicators.preloaded import MACDPreloadedIndicator

nb.info("PRELOADED индикаторы работают с уже рассчитанными данными (например, из TradingView)")

# Получаем информацию о классе без создания объекта
default_cols = MACDPreloadedIndicator.get_default_columns()
info = MACDPreloadedIndicator.get_info()

nb.log(f"Default columns: {default_cols}")
nb.log(f"Indicator type: {info['type']}")
nb.log(f"Description: {info['description']}")
nb.log(f"Required fields: {info['required_fields']}")
nb.log(f"Optional fields: {info['optional_fields']}")

# Создаем индикатор
macd_preloaded = MACDPreloadedIndicator()
nb.log(f"Created PRELOADED indicator: {macd_preloaded.name}")

# Извлекаем данные
nb.info("Extracting MACD data from preloaded dataset:")
macd_preloaded_result = macd_preloaded.calculate(df_sample_tv)
nb.log(f"Extracted {len(macd_preloaded_result.data)} rows")
nb.log(f"Columns: {list(macd_preloaded_result.data.columns)}")

# Значения
nb.log("Sample MACD values:")
nb.log(macd_preloaded_result.data.tail().to_string())

# Демонстрация методов анализа
nb.info("Demonstrating analysis methods:")

# Валидация данных
is_valid = macd_preloaded.validate_data(df_sample_tv)
nb.log(f"Data validation: {is_valid}")

# Статистика
stats = macd_preloaded.get_statistics(df_sample_tv)
nb.log("Statistics:")
for col, col_stats in stats.items():
    nb.log(f"  {col}: min={col_stats['min']:.4f}, max={col_stats['max']:.4f}, mean={col_stats['mean']:.4f}")

# Анализ трендов
trending_up = macd_preloaded.is_trending_up(df_sample_tv, column='macd')
trending_down = macd_preloaded.is_trending_down(df_sample_tv, column='macd')
nb.log(f"MACD trending up: {trending_up}")
nb.log(f"MACD trending down: {trending_down}")

# Пересечения
crossovers = macd_preloaded.get_crossovers(df_sample_tv)
nb.log(f"Bullish crossovers: {crossovers['bullish_crossovers']}")
nb.log(f"Bearish crossovers: {crossovers['bearish_crossovers']}")

# Метаданные
nb.log("Metadata:")
nb.log(f"  Source: {macd_preloaded_result.metadata['source']}")
nb.log(f"  Method: {macd_preloaded_result.metadata['calculation_method']}")
nb.log(f"  Extracted columns: {macd_preloaded_result.metadata['extracted_columns']}")
nb.log(f"  Total records: {macd_preloaded_result.metadata['total_records']}")

nb.wait()

# Демонстрация LIBRARY индикаторов
nb.substep("LIBRARY индикаторы")

from bquant.indicators.base import LibraryIndicator
import numpy as np

nb.info("LIBRARY индикаторы используют внешние библиотеки (например, TA-Lib, pandas-ta)")

# Создаем простую функцию для расчета SMA (имитация внешней библиотеки)
def sma_library_function(data, period=20, **kwargs):
    """Простая функция SMA для демонстрации LibraryIndicator"""
    if 'close' not in data.columns:
        raise ValueError("Data must contain 'close' column")
    
    close_prices = data['close'].values
    sma_values = np.full_like(close_prices, np.nan)
    
    for i in range(period - 1, len(close_prices)):
        sma_values[i] = np.mean(close_prices[i - period + 1:i + 1])
    
    return pd.DataFrame({
        f'sma_{period}': sma_values
    }, index=data.index)

# Создаем LIBRARY индикатор
sma_library = LibraryIndicator(
    name="sma_library",
    library_func=sma_library_function,
    parameters={'period': 20}
)
nb.log(f"Created LIBRARY indicator: {sma_library.name}")

# Рассчитываем SMA
nb.info("Calculating SMA using library function:")
sma_library_result = sma_library.calculate(df_sample_tv)
nb.log(f"Calculated {len(sma_library_result.data)} rows")
nb.log(f"Columns: {list(sma_library_result.data.columns)}")

# Значения
nb.log("Sample SMA values:")
nb.log(sma_library_result.data.tail().to_string())

# Демонстрация доступа к исходной функции
nb.info("Accessing native library function:")
native_func = sma_library.native_indicator
nb.log(f"Native function: {native_func.__name__}")
nb.log(f"Function callable: {callable(native_func)}")

# Прямой вызов функции
direct_result = native_func(df_sample_tv, period=10)
nb.log(f"Direct function call result: {list(direct_result.columns)}")

nb.wait()

# Демонстрация CUSTOM индикаторов
nb.substep("CUSTOM индикаторы")

from bquant.indicators.base import BaseIndicator, IndicatorResult, IndicatorConfig, IndicatorSource

class CustomRSIIndicator(BaseIndicator):
    """Кастомный RSI индикатор с собственной логикой расчета"""
    
    def __init__(self, period=14):
        config = IndicatorConfig(
            name='custom_rsi',
            parameters={'period': period},
            source=IndicatorSource.CUSTOM,
            columns=[f'rsi_{period}'],
            description=f'Custom RSI with period {period}'
        )
        super().__init__(f'rsi_{period}', config)
    
    @classmethod
    def get_default_columns(cls):
        return ['rsi_14']
    
    @classmethod
    def get_info(cls):
        return {
            'name': 'CustomRSIIndicator',
            'type': 'CUSTOM',
            'description': 'Custom RSI implementation with numpy',
            'default_columns': cls.get_default_columns(),
            'required_fields': {
                'close': 'Close price values (numeric)'
            },
            'usage_examples': {
                'basic': 'CustomRSIIndicator()',
                'custom_params': 'CustomRSIIndicator(period=21)'
            }
        }
    
    def calculate(self, data, **kwargs):
        """Кастомный расчет RSI"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for custom RSI calculation")
        
        close_prices = data['close'].values
        period = self.config.parameters['period']
        
        # Рассчитываем изменения цены
        price_changes = np.diff(close_prices)
        
        # Разделяем на положительные и отрицательные изменения
        gains = np.where(price_changes > 0, price_changes, 0)
        losses = np.where(price_changes < 0, -price_changes, 0)
        
        # Рассчитываем средние значения
        avg_gains = np.full_like(close_prices, np.nan)
        avg_losses = np.full_like(close_prices, np.nan)
        
        # Первое значение
        avg_gains[period] = np.mean(gains[:period])
        avg_losses[period] = np.mean(losses[:period])
        
        # Остальные значения с экспоненциальным сглаживанием
        for i in range(period + 1, len(close_prices)):
            avg_gains[i] = (avg_gains[i-1] * (period - 1) + gains[i-1]) / period
            avg_losses[i] = (avg_losses[i-1] * (period - 1) + losses[i-1]) / period
        
        # Рассчитываем RSI
        rs = avg_gains / np.where(avg_losses == 0, 1e-10, avg_losses)
        rsi_values = 100 - (100 / (1 + rs))
        
        # Создаем DataFrame
        result_data = pd.DataFrame({
            f'rsi_{period}': rsi_values
        }, index=data.index)
        
        return IndicatorResult(
            name=self.name,
            data=result_data,
            config=self.config,
            metadata={
                'source': 'custom',
                'calculation_method': 'numpy_rsi',
                'parameters': self.config.parameters,
                'total_records': len(result_data)
            }
        )
    
    def validate_data(self, data):
        """Валидация данных для кастомного RSI"""
        if data.empty:
            return False
        
        if 'close' not in data.columns:
            return False
        
        if len(data) < self.config.parameters['period'] + 1:
            return False
        
        return True

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

# Создаем кастомный RSI индикатор
rsi_custom = CustomRSIIndicator(period=14)
nb.log(f"Created CUSTOM RSI indicator: {rsi_custom.name}")

# Получаем информацию о классе
custom_info = CustomRSIIndicator.get_info()
nb.log(f"CUSTOM RSI indicator type: {custom_info['type']}")
nb.log(f"Required fields: {custom_info['required_fields']}")

# Рассчитываем RSI
nb.info("Calculating RSI using custom implementation:")
rsi_custom_result = rsi_custom.calculate(df_sample_tv)
nb.log(f"Calculated {len(rsi_custom_result.data)} rows")
nb.log(f"Columns: {list(rsi_custom_result.data.columns)}")

# Значения
nb.log("Sample RSI values:")
nb.log(rsi_custom_result.data.tail().to_string())

# Проверяем диапазон RSI (должен быть 0-100)
rsi_values = rsi_custom_result.data[f'rsi_14'].dropna()
nb.log(f"RSI range: {rsi_values.min():.2f} to {rsi_values.max():.2f}")

# Создаем кастомный MACD индикатор
macd_custom = CustomMACDIndicator(fast_period=12, slow_period=26, signal_period=9)
nb.log(f"Created CUSTOM MACD indicator: {macd_custom.name}")

# Рассчитываем MACD
nb.info("Calculating MACD using custom implementation:")
macd_custom_result = macd_custom.calculate(df_sample_tv)
nb.log(f"Calculated {len(macd_custom_result.data)} rows")
nb.log(f"Columns: {list(macd_custom_result.data.columns)}")

# Значения
nb.log("Sample MACD values:")
nb.log(macd_custom_result.data.tail().to_string())

nb.wait()

# Демонстрация IndicatorFactory
nb.substep("IndicatorFactory - универсальный способ создания индикаторов")

from bquant.indicators import IndicatorFactory, IndicatorSource

nb.info("IndicatorFactory предоставляет единый интерфейс для создания всех типов индикаторов")

# Список доступных индикаторов
nb.info("Available indicators:")
available_indicators = IndicatorFactory.list_indicators()
nb.log(f"Total indicators: {len(available_indicators)}")
nb.log(f"Indicator names: {list(available_indicators.keys())}")

# Создание индикаторов через фабрику
nb.info("Creating indicators through factory:")

# CUSTOM индикатор
sma_factory = IndicatorFactory.create('custom', 'sma', period=20)
nb.log(f"Created SMA via factory: {sma_factory.name}, period: {sma_factory.period}")

# PRELOADED индикатор
macd_factory = IndicatorFactory.create('preloaded', 'macd_preloaded')
nb.log(f"Created MACD via factory: {macd_factory.name}")

# Информация об индикаторах
nb.info("Indicator information:")
sma_info = IndicatorFactory.get_indicator_info('sma')
nb.log(f"SMA info: {sma_info}")

macd_info = IndicatorFactory.get_indicator_info('macd_preloaded')
nb.log(f"MACD info: {macd_info}")

# Расчет через фабричные индикаторы
nb.info("Calculating indicators created via factory:")

# SMA
sma_factory_result = sma_factory.calculate(df_sample_tv)
nb.log(f"SMA factory result: {list(sma_factory_result.data.columns)}")

# MACD
macd_factory_result = macd_factory.calculate(df_sample_tv)
nb.log(f"MACD factory result: {list(macd_factory_result.data.columns)}")

nb.wait()

# Сравнение всех подходов
nb.substep("Сравнение всех подходов")

nb.info("Comparison of all three approaches:")

# Создаем таблицу сравнения
comparison_data = {
    'Approach': ['PRELOADED', 'LIBRARY', 'CUSTOM', 'FACTORY'],
    'Indicator': ['MACD', 'SMA', 'RSI', 'SMA+MACD'],
    'Columns': [
        str(list(macd_preloaded_result.data.columns)),
        str(list(sma_library_result.data.columns)),
        str(list(rsi_custom_result.data.columns)),
        str(list(sma_factory_result.data.columns))
    ],
    'Rows': [
        len(macd_preloaded_result.data),
        len(sma_library_result.data),
        len(rsi_custom_result.data),
        len(sma_factory_result.data)
    ],
    'Source': [
        macd_preloaded_result.metadata.get('source', 'unknown'),
        sma_library_result.metadata.get('source', 'unknown'),
        rsi_custom_result.metadata.get('source', 'unknown'),
        sma_factory_result.metadata.get('source', 'unknown')
    ]
}

comparison_df = pd.DataFrame(comparison_data)
nb.log("Comparison table:")
nb.log(comparison_df.to_string(index=False))

# Анализ производительности
nb.info("Performance analysis:")
nb.log(f"PRELOADED: {len(macd_preloaded_result.data)} rows - {macd_preloaded_result.metadata.get('source', 'unknown')}")
nb.log(f"LIBRARY: {len(sma_library_result.data)} rows - {sma_library_result.metadata.get('source', 'unknown')}")
nb.log(f"CUSTOM: {len(rsi_custom_result.data)} rows - {rsi_custom_result.metadata.get('source', 'unknown')}")
nb.log(f"FACTORY: {len(sma_factory_result.data)} rows - {sma_factory_result.metadata.get('source', 'unknown')}")

# Дополнительная информация о метаданных
nb.info("Metadata analysis:")
nb.log(f"PRELOADED metadata keys: {list(macd_preloaded_result.metadata.keys())}")
nb.log(f"LIBRARY metadata keys: {list(sma_library_result.metadata.keys())}")
nb.log(f"CUSTOM metadata keys: {list(rsi_custom_result.metadata.keys())}")
nb.log(f"FACTORY metadata keys: {list(sma_factory_result.metadata.keys())}")

nb.wait()

# Заключение
nb.step("Заключение")

nb.info("Новая архитектура индикаторов BQuant предоставляет:")
nb.info("✅ Единообразный интерфейс для всех типов индикаторов")
nb.info("✅ Гибкость в выборе источника данных (PRELOADED, LIBRARY, CUSTOM)")
nb.info("✅ Универсальную фабрику для создания индикаторов")
nb.info("✅ Совместимость с существующим кодом")
nb.info("✅ Расширяемость для новых типов индикаторов")

nb.info("Рекомендации по использованию:")
nb.info("• PRELOADED: для работы с готовыми данными (TradingView, MT5)")
nb.info("• LIBRARY: для использования внешних библиотек (TA-Lib, pandas-ta)")
nb.info("• CUSTOM: для реализации собственной логики расчета")
nb.info("• FACTORY: для универсального создания индикаторов")

nb.log("Демонстрация завершена успешно!")