'''
Демонстрация работы базовых классов и архитектуры индикаторов bquant.indicators.base

Этот скрипт показывает, как использовать фундаментальные компоненты системы индикаторов:
1.  Создание и настройка конфигураций индикаторов.
2.  Работа с базовым классом BaseIndicator.
3.  Создание пользовательских индикаторов.
4.  Работа с IndicatorFactory.
5.  Кэширование результатов вычислений.
6.  Валидация данных и обработка ошибок.
'''

from pathlib import Path
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# НАСТРОЙКА ЛОГИРОВАНИЯ ДО ИМПОРТА МОДУЛЕЙ
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.indicators.base import (
    IndicatorSource,
    IndicatorConfig,
    IndicatorResult,
    BaseIndicator,
    PreloadedIndicator,
    CustomIndicator,
    LibraryIndicator,
    IndicatorFactory
)
from bquant.indicators.library import LibraryManager

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы базовых классов индикаторов bquant.indicators.base")

# --- Шаг 1: Загрузка тестовых данных ---
nb.step("Шаг 1: Загрузка тестовых данных")

nb.info("Для демонстрации базовых классов индикаторов используем sample-данные.")

with nb.error_handling("Loading sample data"):
    nb.info("1.1. Загружаем sample-данные для тестирования:")
    df_sample = get_sample_data('tv_xauusd_1h')
    
    # Преобразуем колонку time в DatetimeIndex для корректной работы
    if 'time' in df_sample.columns:
        df_sample = df_sample.set_index('time')
        nb.log("Колонка 'time' преобразована в DatetimeIndex")
    
    nb.log(f"Загружено {len(df_sample)} строк данных")
    nb.log(f"Структура: {list(df_sample.columns)}")
    nb.log(f"Тип индекса: {type(df_sample.index)}")
    nb.log(f"Диапазон дат: {df_sample.index.min()} - {df_sample.index.max()}")

nb.wait()

# --- Шаг 2: Работа с IndicatorSource и IndicatorConfig ---
nb.step("Шаг 2: Работа с IndicatorSource и IndicatorConfig")

nb.info("IndicatorSource определяет источники индикаторов, а IndicatorConfig - их конфигурацию.")

with nb.error_handling("Testing IndicatorSource and IndicatorConfig"):
    nb.info("2.1. Изучение доступных источников индикаторов:")
    
    # Показываем все доступные источники
    sources = list(IndicatorSource)
    nb.log(f"Доступные источники индикаторов:")
    for source in sources:
        nb.log(f"  - {source.name}: {source.value}")
    
    nb.info("2.2. Создание конфигураций для различных типов индикаторов:")
    
    # Конфигурация для простого индикатора
    simple_config = IndicatorConfig(
        name="custom_sma",
        parameters={"period": 20},
        source=IndicatorSource.CUSTOM,
        columns=["sma_20"],
        description="Простая скользящая средняя с периодом 20"
    )
    
    # Конфигурация для сложного индикатора
    complex_config = IndicatorConfig(
        name="custom_bbands",
        parameters={"period": 20, "std_dev": 2},
        source=IndicatorSource.CUSTOM,
        columns=["bb_upper", "bb_middle", "bb_lower"],
        description="Полосы Боллинджера с периодом 20 и 2 стандартными отклонениями"
    )
    
    # Конфигурация для библиотечного индикатора
    library_config = IndicatorConfig(
        name="talib_rsi",
        parameters={"period": 14},
        source=IndicatorSource.LIBRARY,
        columns=["rsi_14"],
        description="RSI из библиотеки TALib с периодом 14"
    )
    
    nb.log(f"Создано {3} конфигурации индикаторов:")
    
    # Показываем детали каждой конфигурации
    for config in [simple_config, complex_config, library_config]:
        nb.log(f"  - {config.name}:")
        nb.log(f"    * Источник: {config.source.value}")
        nb.log(f"    * Параметры: {config.parameters}")
        nb.log(f"    * Колонки: {config.columns}")
        nb.log(f"    * Описание: {config.description}")

nb.wait()

# --- Шаг 3: Создание пользовательского индикатора на основе BaseIndicator ---
nb.step("Шаг 3: Создание пользовательского индикатора на основе BaseIndicator")

nb.info("BaseIndicator - это абстрактный базовый класс для создания пользовательских индикаторов.")

with nb.error_handling("Creating custom indicator"):
    nb.info("3.1. Создание пользовательского индикатора 'True Range':")
    
    class TrueRangeIndicator(CustomIndicator):
        """
        Пользовательский индикатор True Range.
        
        True Range = max(high - low, |high - prev_close|, |low - prev_close|)
        """
        
        def __init__(self, name: str = "true_range"):
            """Инициализация индикатора True Range."""
            super().__init__(name, {})
        
        def get_output_columns(self) -> List[str]:
            """Возвращает выходные колонки."""
            return ["true_range"]
        
        def get_description(self) -> str:
            """Возвращает описание индикатора."""
            return "True Range - максимальный диапазон цены"
        
        def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
            """
            Расчет True Range.
            
            Args:
                data: DataFrame с OHLC данными
                **kwargs: Дополнительные параметры
            
            Returns:
                IndicatorResult с результатами
            """
            try:
                self.validate_data(data)
                
                self.logger.info(f"Calculating True Range for {len(data)} records")
                
                # Получаем необходимые колонки
                high = data['high']
                low = data['low']
                close = data['close']
                
                # Вычисляем True Range
                tr1 = high - low  # Текущий high - low
                tr2 = abs(high - close.shift(1))  # |high - prev_close|
                tr3 = abs(low - close.shift(1))   # |low - prev_close|
                
                # True Range = максимум из трех значений
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                # Создаем результат
                result_data = pd.DataFrame({
                    'true_range': true_range
                }, index=data.index)
                
                return IndicatorResult(
                    name=self.name,
                    data=result_data,
                    config=self.config,
                    metadata={
                        'calculation_method': 'max_of_three_ranges',
                        'first_valid_index': result_data.first_valid_index(),
                        'last_valid_index': result_data.last_valid_index(),
                        'total_records': len(result_data)
                    }
                )
                
            except Exception as e:
                self.logger.error(f"Failed to calculate True Range: {e}")
                raise
        
        def get_min_records(self) -> int:
            """Минимальное количество записей для расчета."""
            return 2  # Нужны как минимум 2 записи для prev_close
        
        def get_required_columns(self) -> List[str]:
            """Требуемые колонки для расчета."""
            return ['high', 'low', 'close']
    
    nb.log(f"Создан пользовательский индикатор TrueRangeIndicator:")
    nb.log(f"  - Название: {TrueRangeIndicator.__name__}")
    nb.log(f"  - Базовый класс: {TrueRangeIndicator.__bases__[0].__name__}")
    nb.log(f"  - Минимальные записи: {TrueRangeIndicator('test').get_min_records()}")
    nb.log(f"  - Требуемые колонки: {TrueRangeIndicator('test').get_required_columns()}")

nb.wait()

# --- Шаг 4: Тестирование пользовательского индикатора ---
nb.step("Шаг 4: Тестирование пользовательского индикатора")

nb.info("Тестируем созданный пользовательский индикатор True Range.")

with nb.error_handling("Testing custom indicator"):
    nb.info("4.1. Создание экземпляра индикатора:")
    
    # Создаем экземпляр индикатора
    tr_indicator = TrueRangeIndicator()
    nb.log(f"Создан экземпляр индикатора:")
    nb.log(f"  - Название: {tr_indicator.name}")
    nb.log(f"  - Конфигурация: {tr_indicator.config.name}")
    nb.log(f"  - Источник: {tr_indicator.config.source.value}")
    
    nb.info("4.2. Валидация данных:")
    
    # Проверяем валидность данных
    is_valid = tr_indicator.validate_data(df_sample)
    nb.log(f"Данные валидны для индикатора: {is_valid}")
    
    nb.info("4.3. Расчет True Range:")
    
    # Вычисляем True Range
    tr_result = tr_indicator.calculate(df_sample)
    
    nb.log(f"Результат расчета True Range:")
    nb.log(f"  - Название: {tr_result.name}")
    nb.log(f"  - Размер данных: {tr_result.data.shape}")
    nb.log(f"  - Колонки: {list(tr_result.data.columns)}")
    nb.log(f"  - Метаданные: {tr_result.metadata}")
    
    # Показываем первые несколько значений
    nb.log(f"Первые 5 значений True Range:")
    nb.log(str(tr_result.data.head()))
    
    # Показываем статистику
    nb.log(f"Статистика True Range:")
    nb.log(f"  - Минимум: {tr_result.data['true_range'].min():.4f}")
    nb.log(f"  - Максимум: {tr_result.data['true_range'].max():.4f}")
    nb.log(f"  - Среднее: {tr_result.data['true_range'].mean():.4f}")
    nb.log(f"  - Медиана: {tr_result.data['true_range'].median():.4f}")

nb.wait()

# --- Шаг 5: Создание индикатора на основе PreloadedIndicator ---
nb.step("Шаг 5: Создание индикатора на основе PreloadedIndicator")

nb.info("PreloadedIndicator - это базовый класс для встроенных индикаторов BQuant.")

with nb.error_handling("Creating PreloadedIndicator"):
    nb.info("5.1. Создание индикатора 'Price Range' на основе PreloadedIndicator:")
    
    class PriceRangeIndicator(PreloadedIndicator):
        """
        Индикатор диапазона цен (Price Range).
        
        Price Range = (high - low) / close * 100
        """
        
        def __init__(self, name: str = "price_range"):
            """Инициализация индикатора Price Range."""
            super().__init__(name, {})
        
        def get_output_columns(self) -> List[str]:
            """Возвращает выходные колонки."""
            return ["price_range_pct"]
        
        @staticmethod
        def get_description() -> str:
            """Возвращает описание индикатора."""
            return "Price Range как процент от цены закрытия"
        
        def get_min_records(self) -> int:
            """Минимальное количество записей."""
            return 1
        
        def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
            """Расчет Price Range."""
            try:
                self.validate_data(data)
                
                self.logger.info(f"Calculating Price Range for {len(data)} records")
                
                # Вычисляем Price Range в процентах
                price_range = (data['high'] - data['low']) / data['close'] * 100
                
                # Создаем результат
                result_data = pd.DataFrame({
                    'price_range_pct': price_range
                }, index=data.index)
                
                return IndicatorResult(
                    name=self.name,
                    data=result_data,
                    config=self.config,
                    metadata={
                        'calculation_method': 'high_low_close_percentage',
                        'first_valid_index': result_data.first_valid_index(),
                        'last_valid_index': result_data.last_valid_index(),
                        'total_records': len(result_data)
                    }
                )
                
            except Exception as e:
                self.logger.error(f"Failed to calculate Price Range: {e}")
                raise
        
        def get_required_columns(self) -> List[str]:
            """Требуемые колонки."""
            return ['high', 'low', 'close']
    
    nb.log(f"Создан индикатор PriceRangeIndicator:")
    nb.log(f"  - Базовый класс: {PriceRangeIndicator.__bases__[0].__name__}")
    nb.log(f"  - Выходные колонки: {PriceRangeIndicator().get_output_columns()}")
    nb.log(f"  - Описание: {PriceRangeIndicator().get_description()}")
    
    nb.info("5.2. Тестирование PriceRangeIndicator:")
    
    # Создаем и тестируем индикатор
    pr_indicator = PriceRangeIndicator()
    pr_result = pr_indicator.calculate(df_sample)
    
    nb.log(f"Результат расчета Price Range:")
    nb.log(f"  - Размер данных: {pr_result.data.shape}")
    nb.log(f"  - Колонки: {list(pr_result.data.columns)}")
    
    # Показываем статистику
    nb.log(f"Статистика Price Range (%):")
    nb.log(f"  - Минимум: {pr_result.data['price_range_pct'].min():.4f}%")
    nb.log(f"  - Максимум: {pr_result.data['price_range_pct'].max():.4f}%")
    nb.log(f"  - Среднее: {pr_result.data['price_range_pct'].mean():.4f}%")

nb.wait()

# --- Шаг 6: Работа с IndicatorFactory ---
nb.step("Шаг 6: Работа с IndicatorFactory")

nb.info("IndicatorFactory - это фабрика для создания и управления индикаторами.")

with nb.error_handling("Testing IndicatorFactory"):
    nb.info("6.1. Регистрация пользовательских индикаторов:")
    
    # Регистрируем наши индикаторы в фабрике
    IndicatorFactory.register_indicator("true_range", TrueRangeIndicator)
    IndicatorFactory.register_indicator("price_range", PriceRangeIndicator)
    
    nb.log(f"Зарегистрированы индикаторы в фабрике:")
    nb.log(f"  - true_range: {TrueRangeIndicator}")
    nb.log(f"  - price_range: {PriceRangeIndicator}")
    
    nb.info("6.2. Просмотр доступных индикаторов:")
    
    # Получаем список всех зарегистрированных индикаторов
    available_indicators = IndicatorFactory.list_indicators()
    nb.log(f"Доступные индикаторы в фабрике:")
    for name, class_name in available_indicators.items():
        nb.log(f"  - {name}: {class_name}")
    
    nb.info("6.3. Создание индикаторов через фабрику:")
    
    # Создаем индикаторы через фабрику (новый единый интерфейс)
    tr_from_factory = IndicatorFactory.create("custom", "true_range")
    pr_from_factory = IndicatorFactory.create("preloaded", "price_range")
    
    nb.log(f"Индикаторы созданы через фабрику:")
    nb.log(f"  - true_range: {type(tr_from_factory).__name__}")
    nb.log(f"  - price_range: {type(pr_from_factory).__name__}")
    
    nb.info("6.4. Получение информации об индикаторах:")
    
    # Получаем детальную информацию об индикаторах
    for indicator_name in ["true_range", "price_range"]:
        info = IndicatorFactory.get_indicator_info(indicator_name)
        if info:
            nb.log(f"Информация об индикаторе '{indicator_name}':")
            nb.log(f"  - Класс: {info.get('class_name', 'N/A')}")
            nb.log(f"  - Источник: {info.get('source', 'N/A')}")
            nb.log(f"  - Описание: {info.get('description', 'N/A')}")

nb.wait()

# --- Шаг 7: Демонстрация работы с LibraryManager ---
nb.step("Шаг 7: Демонстрация работы с LibraryManager")

nb.info("LibraryManager предоставляет централизованное управление внешними библиотеками индикаторов.")

with nb.error_handling("Testing LibraryManager"):
    nb.info("7.1. Проверка доступности внешних библиотек:")
    
    # Проверяем доступность библиотек
    available_libs = LibraryManager.get_available_libraries()
    nb.log(f"Доступные библиотеки: {available_libs}")
    
    for lib_name in available_libs:
        is_available = LibraryManager.check_library_availability(lib_name)
        nb.log(f"  - {lib_name}: {'доступна' if is_available else 'недоступна'}")
        
        if is_available:
            info = LibraryManager.get_library_info(lib_name)
            nb.log(f"    * Индикаторов: {info.get('indicators_count', 0)}")
            nb.log(f"    * Статус: {info.get('available', False)}")
    
    nb.info("7.2. Загрузка внешних библиотек:")
    
    # Загружаем все доступные библиотеки
    library_results = LibraryManager.load_all_libraries()
    nb.log(f"Результаты загрузки библиотек: {library_results}")
    
    nb.info("7.3. Демонстрация создания индикатора через LibraryManager:")
    
    # Пытаемся создать индикатор из pandas_ta через LibraryManager
    if LibraryManager.check_library_availability('pandas_ta'):
        try:
            # Создаем RSI индикатор через LibraryManager
            rsi_lib = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)
            nb.log(f"Создан библиотечный индикатор: {type(rsi_lib).__name__}")
            nb.log(f"  - Источник: {rsi_lib.config.source.value}")
            nb.log(f"  - Название: {rsi_lib.name}")
            
            # Тестируем расчет
            rsi_result = rsi_lib.calculate(df_sample)
            nb.log(f"  - Результат расчета: {rsi_result.data.shape}")
            nb.log(f"  - Колонки: {list(rsi_result.data.columns)}")
            
        except Exception as e:
            nb.log(f"Ошибка создания библиотечного индикатора: {e}")
    else:
        nb.log("pandas_ta недоступна - пропускаем демонстрацию библиотечных индикаторов")
    
    nb.info("7.4. Демонстрация создания индикатора через IndicatorFactory:")
    
    # Создаем индикатор через новый единый интерфейс IndicatorFactory
    try:
        # Пытаемся создать индикатор из внешней библиотеки
        if LibraryManager.check_library_availability('pandas_ta'):
            macd_lib = IndicatorFactory.create('pandas_ta', 'macd', fast=12, slow=26, signal=9)
            nb.log(f"Создан индикатор через IndicatorFactory: {type(macd_lib).__name__}")
            nb.log(f"  - Источник: {macd_lib.config.source.value}")
            
            # Тестируем расчет
            macd_result = macd_lib.calculate(df_sample)
            nb.log(f"  - Результат расчета: {macd_result.data.shape}")
            nb.log(f"  - Колонки: {list(macd_result.data.columns)}")
        else:
            nb.log("pandas_ta недоступна - создаем CUSTOM индикатор")
            custom_sma = IndicatorFactory.create('custom', 'sma', period=20)
            nb.log(f"Создан CUSTOM индикатор: {type(custom_sma).__name__}")
            
            # Тестируем расчет
            sma_result = custom_sma.calculate(df_sample)
            nb.log(f"  - Результат расчета: {sma_result.data.shape}")
            nb.log(f"  - Колонки: {list(sma_result.data.columns)}")
            
    except Exception as e:
        nb.log(f"Ошибка создания индикатора через IndicatorFactory: {e}")

nb.wait()

# --- Шаг 8: Тестирование производительности ---
nb.step("Шаг 8: Тестирование производительности")

nb.info("BaseIndicator поддерживает кэширование результатов для оптимизации производительности.")

with nb.error_handling("Testing caching functionality"):
    nb.info("8.1. Тестирование производительности TrueRangeIndicator:")
    
    # Создаем индикатор для тестирования производительности
    tr_perf = TrueRangeIndicator("performance_test")
    
    nb.info("8.2. Первый расчет:")
    
    # Первый расчет
    start_time = datetime.now()
    result1 = tr_perf.calculate(df_sample)
    time1 = (datetime.now() - start_time).total_seconds()
    
    nb.log(f"Первый расчет завершен за {time1:.4f} секунд")
    nb.log(f"Размер результата: {result1.data.shape}")
    
    nb.info("8.3. Второй расчет:")
    
    # Второй расчет для сравнения производительности
    start_time = datetime.now()
    result2 = tr_perf.calculate(df_sample)
    time2 = (datetime.now() - start_time).total_seconds()
    
    nb.log(f"Второй расчет завершен за {time2:.4f} секунд")
    nb.log(f"Время расчетов: {time1:.4f}s / {time2:.4f}s")
    
    # Проверяем, что результаты одинаковые
    results_equal = result1.data.equals(result2.data)
    nb.log(f"Результаты расчетов идентичны: {results_equal}")
    
    nb.info("8.4. Примечание о кэшировании:")
    nb.log("В новой архитектуре кэширование для CustomIndicator пока не реализовано.")
    nb.log("Для оптимизации производительности используйте специализированные индикаторы или внешние библиотеки.")

nb.wait()

# --- Шаг 9: Создание комплексного индикатора ---
nb.step("Шаг 9: Создание комплексного индикатора")

nb.info("Демонстрация создания комплексного индикатора, объединяющего несколько расчетов.")

with nb.error_handling("Creating complex indicator"):
    nb.info("9.1. Создание комплексного индикатора 'Price Analysis':")
    
    class PriceAnalysisIndicator(CustomIndicator):
        """
        Комплексный индикатор анализа цен.
        
        Объединяет:
        - True Range
        - Price Range
        - Price Change
        - Volatility
        """
        
        def __init__(self, name: str = "price_analysis"):
            """Инициализация комплексного индикатора."""
            super().__init__(name, {})
        
        def get_output_columns(self) -> List[str]:
            """Возвращает выходные колонки."""
            return ["true_range", "price_range_pct", "price_change_pct", "volatility"]
        
        def get_description(self) -> str:
            """Возвращает описание индикатора."""
            return "Комплексный анализ цен с множественными метриками"
        
        def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
            """Расчет комплексного анализа цен."""
            try:
                self.validate_data(data)
                
                self.logger.info(f"Calculating Price Analysis for {len(data)} records")
                
                # 1. True Range
                high = data['high']
                low = data['low']
                close = data['close']
                
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                # 2. Price Range в процентах
                price_range_pct = (high - low) / close * 100
                
                # 3. Изменение цены в процентах
                price_change_pct = (close - close.shift(1)) / close.shift(1) * 100
                
                # 4. Волатильность (стандартное отклонение изменения цены за 20 периодов)
                volatility = price_change_pct.rolling(window=20).std()
                
                # Создаем результат
                result_data = pd.DataFrame({
                    'true_range': true_range,
                    'price_range_pct': price_range_pct,
                    'price_change_pct': price_change_pct,
                    'volatility': volatility
                }, index=data.index)
                
                return IndicatorResult(
                    name=self.name,
                    data=result_data,
                    config=self.config,
                    metadata={
                        'calculation_method': 'comprehensive_price_analysis',
                        'components': ['true_range', 'price_range_pct', 'price_change_pct', 'volatility'],
                        'first_valid_index': result_data.first_valid_index(),
                        'last_valid_index': result_data.last_valid_index(),
                        'total_records': len(result_data)
                    }
                )
                
            except Exception as e:
                self.logger.error(f"Failed to calculate Price Analysis: {e}")
                raise
        
        def get_min_records(self) -> int:
            """Минимальное количество записей."""
            return 21  # 20 для волатильности + 1 для текущего значения
        
        def get_required_columns(self) -> List[str]:
            """Требуемые колонки."""
            return ['high', 'low', 'close']
    
    nb.log(f"Создан комплексный индикатор PriceAnalysisIndicator:")
    nb.log(f"  - Название: {PriceAnalysisIndicator.__name__}")
    nb.log(f"  - Выходные колонки: {PriceAnalysisIndicator().config.columns}")
    nb.log(f"  - Минимальные записи: {PriceAnalysisIndicator().get_min_records()}")
    
    nb.info("9.2. Тестирование комплексного индикатора:")
    
    # Создаем и тестируем комплексный индикатор
    pa_indicator = PriceAnalysisIndicator()
    pa_result = pa_indicator.calculate(df_sample)
    
    nb.log(f"Результат комплексного анализа цен:")
    nb.log(f"  - Размер данных: {pa_result.data.shape}")
    nb.log(f"  - Колонки: {list(pa_result.data.columns)}")
    nb.log(f"  - Метаданные: {pa_result.metadata}")
    
    # Показываем статистику по каждой метрике
    nb.log(f"Статистика комплексного анализа:")
    for col in pa_result.data.columns:
        col_data = pa_result.data[col].dropna()
        if len(col_data) > 0:
            nb.log(f"  - {col}:")
            nb.log(f"    * Записей: {len(col_data)}")
            nb.log(f"    * Минимум: {col_data.min():.4f}")
            nb.log(f"    * Максимум: {col_data.max():.4f}")
            nb.log(f"    * Среднее: {col_data.mean():.4f}")

nb.wait()

# --- Шаг 10: Тестирование валидации данных ---
nb.step("Шаг 10: Тестирование валидации данных")

nb.info("BaseIndicator предоставляет встроенную валидацию данных для обеспечения корректности расчетов.")

with nb.error_handling("Testing data validation"):
    nb.info("10.1. Тестирование валидации корректных данных:")
    
    # Создаем индикатор для тестирования
    test_indicator = TrueRangeIndicator("test_validation")
    
    # Тестируем с корректными данными
    is_valid_correct = test_indicator.validate_data(df_sample)
    nb.log(f"Валидация корректных данных: {is_valid_correct}")
    
    nb.info("10.2. Тестирование валидации некорректных данных:")
    
    # Создаем некорректные данные (отсутствуют необходимые колонки)
    df_invalid = df_sample[['open', 'volume']].copy()  # Убираем high, low, close
    
    try:
        is_valid_invalid = test_indicator.validate_data(df_invalid)
        nb.log(f"Валидация некорректных данных: {is_valid_invalid}")
    except Exception as e:
        nb.log(f"Валидация некорректных данных вызвала ошибку: {type(e).__name__}: {e}")
    
    nb.info("10.3. Тестирование валидации данных с недостаточным количеством записей:")
    
    # Создаем данные с недостаточным количеством записей
    df_short = df_sample.head(1)  # Только 1 запись
    
    try:
        is_valid_short = test_indicator.validate_data(df_short)
        nb.log(f"Валидация коротких данных: {is_valid_short}")
    except Exception as e:
        nb.log(f"Валидация коротких данных вызвала ошибку: {type(e).__name__}: {e}")

nb.wait()

# --- Шаг 11: Анализ архитектуры и производительности ---
nb.step("Шаг 11: Анализ архитектуры и производительности")

nb.info("Анализ созданной архитектуры индикаторов и оценка производительности.")

with nb.error_handling("Analyzing architecture and performance"):
    nb.info("11.1. Анализ архитектуры индикаторов:")
    
    # Анализируем созданные индикаторы
    indicators_created = {
        'TrueRangeIndicator': TrueRangeIndicator,
        'PriceRangeIndicator': PriceRangeIndicator,
        'PriceAnalysisIndicator': PriceAnalysisIndicator
    }
    
    nb.log("Анализ созданных индикаторов:")
    for name, indicator_class in indicators_created.items():
        nb.log(f"  - {name}:")
        nb.log(f"    * Базовый класс: {indicator_class.__bases__[0].__name__}")
        
        # Создаем экземпляр для безопасной работы с config
        indicator = indicator_class()
        
        # Безопасное получение источника
        try:
            if hasattr(indicator.config, 'source'):
                source = indicator.config.source.value
            elif isinstance(indicator.config, dict) and 'source' in indicator.config:
                source = indicator.config['source']
            else:
                source = 'unknown'
            nb.log(f"    * Источник: {source}")
        except Exception as e:
            nb.log(f"    * Источник: unknown (error: {e})")
        
        # Безопасное получение колонок
        try:
            if hasattr(indicator.config, 'columns'):
                columns_count = len(indicator.config.columns)
            elif isinstance(indicator.config, dict) and 'columns' in indicator.config:
                columns_count = len(indicator.config['columns'])
            else:
                columns_count = 0
            nb.log(f"    * Выходные колонки: {columns_count}")
        except Exception as e:
            nb.log(f"    * Выходные колонки: unknown (error: {e})")
        
        nb.log(f"    * Минимальные записи: {indicator.get_min_records()}")
    
    nb.info("11.2. Оценка производительности:")
    
    # Тестируем производительность различных индикаторов
    performance_results = {}
    
    for name, indicator_class in indicators_created.items():
        indicator = indicator_class()
        
        # Измеряем время расчета
        start_time = datetime.now()
        result = indicator.calculate(df_sample)
        calc_time = (datetime.now() - start_time).total_seconds()
        
        performance_results[name] = {
            'calculation_time': calc_time,
            'output_columns': len(result.data.columns),
            'total_records': len(result.data)
        }
    
    nb.log("Результаты производительности:")
    for name, metrics in performance_results.items():
        nb.log(f"  - {name}:")
        nb.log(f"    * Время расчета: {metrics['calculation_time']:.4f} сек")
        nb.log(f"    * Выходные колонки: {metrics['output_columns']}")
        nb.log(f"    * Записей: {metrics['total_records']}")
        nb.log(f"    * Скорость: {metrics['total_records']/metrics['calculation_time']:.0f} записей/сек")
    
    nb.info("11.3. Анализ использования памяти:")
    
    # Анализируем использование памяти
    memory_analysis = {}
    
    for name, indicator_class in indicators_created.items():
        indicator = indicator_class()
        result = indicator.calculate(df_sample)
        
        # Оцениваем размер результата
        result_size = result.data.memory_usage(deep=True).sum()
        memory_analysis[name] = {
            'result_size_bytes': result_size,
            'result_size_mb': result_size / (1024 * 1024),
            'columns_count': len(result.data.columns)
        }
    
    nb.log("Анализ использования памяти:")
    for name, metrics in memory_analysis.items():
        nb.log(f"  - {name}:")
        nb.log(f"    * Размер результата: {metrics['result_size_mb']:.2f} МБ")
        nb.log(f"    * Колонок: {metrics['columns_count']}")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные компоненты обновленной архитектуры индикаторов BQuant:")
nb.log("[OK] IndicatorSource - источники индикаторов (PRELOADED, CUSTOM, LIBRARY)")
nb.log("[OK] IndicatorConfig - конфигурация индикаторов")
nb.log("[OK] IndicatorResult - результаты вычислений")
nb.log("[OK] BaseIndicator - абстрактный базовый класс для всех индикаторов")
nb.log("[OK] CustomIndicator - базовый класс для пользовательских индикаторов")
nb.log("[OK] PreloadedIndicator - базовый класс для встроенных индикаторов")
nb.log("[OK] LibraryIndicator - базовый класс для внешних библиотек")
nb.log("[OK] IndicatorFactory - единая фабрика для создания всех типов индикаторов")
nb.log("[OK] LibraryManager - централизованное управление внешними библиотеками")

nb.info("Созданы и протестированы пользовательские индикаторы:")
nb.log("[+] TrueRangeIndicator - индикатор истинного диапазона")
nb.log("[+] PriceRangeIndicator - индикатор диапазона цен")
nb.log("[+] PriceAnalysisIndicator - комплексный анализ цен")

nb.info("Новая архитектура индикаторов BQuant предоставляет:")
nb.log("[*] Единообразный интерфейс для всех типов индикаторов")
nb.log("[*] Четкое разделение ответственности между типами индикаторов")
nb.log("[*] Централизованное управление внешними библиотеками через LibraryManager")
nb.log("[*] Автоматическое обнаружение и регистрацию индикаторов из pandas-ta")
nb.log("[*] Встроенную валидацию данных и обработку ошибок")
nb.log("[*] Гибкую систему создания пользовательских индикаторов")
nb.log("[*] Единую фабрику для создания индикаторов из любого источника")

nb.info("Это демонстрирует мощь и гибкость обновленной архитектуры BQuant для работы с техническими индикаторами.")

nb.finish()
