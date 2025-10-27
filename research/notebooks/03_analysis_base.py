#!/usr/bin/env python3
"""
Демонстрация базовых классов bquant.analysis

Этот скрипт демонстрирует работу с базовыми классами анализа:
- AnalysisResult - для хранения результатов анализа
- BaseAnalyzer - базовый класс для всех анализаторов
- Фабрика анализаторов и получение списка доступных анализаторов

Запуск: python 03_analysis_base.py [--no-trap]
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем путь к корню проекта для импорта bquant
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bquant.core.nb import NotebookSimulator
from bquant.analysis import (
    AnalysisResult,
    BaseAnalyzer,
    get_available_analyzers,
    create_analyzer,
    SUPPORTED_ANALYSIS_TYPES
)

# Создаем экземпляр NotebookSimulator
nb = NotebookSimulator(
    description="Изучаем AnalysisResult, BaseAnalyzer и фабрику анализаторов"
)

# --- Шаг 1: Инициализация и обзор ---
nb.step("Шаг 1: Инициализация и обзор")

nb.info("Изучаем базовые классы пакета bquant.analysis")
nb.log(f"Поддерживаемые типы анализа: {list(SUPPORTED_ANALYSIS_TYPES.keys())}")

for analysis_type, description in SUPPORTED_ANALYSIS_TYPES.items():
    nb.log(f"  - {analysis_type}: {description}")

nb.wait()

# --- Шаг 2: Работа с AnalysisResult ---
nb.step("Шаг 2: Работа с AnalysisResult")

nb.info("Создаем и настраиваем объекты AnalysisResult")

with nb.error_handling("Creating AnalysisResult objects"):
    # Создаем простой результат анализа
    simple_results = {
        'total_points': 1000,
        'success_rate': 0.85,
        'avg_duration': 2.5
    }
    
    simple_analysis = AnalysisResult(
        analysis_type='simple_test',
        results=simple_results,
        data_size=1000,
        metadata={'version': '1.0', 'author': 'demo'}
    )
    
    nb.log(f"Создан простой результат анализа:")
    nb.log(f"  - Тип: {simple_analysis.analysis_type}")
    nb.log(f"  - Размер данных: {simple_analysis.data_size}")
    nb.log(f"  - Время создания: {simple_analysis.timestamp}")
    nb.log(f"  - Ключи результатов: {list(simple_analysis.results.keys())}")
    nb.log(f"  - Метаданные: {simple_analysis.metadata}")

nb.wait()

# --- Шаг 3: Методы AnalysisResult ---
nb.step("Шаг 3: Методы AnalysisResult")

nb.info("Тестируем методы AnalysisResult")

with nb.error_handling("Testing AnalysisResult methods"):
    # Тестируем to_dict()
    nb.log("3.1. Конвертация в словарь:")
    result_dict = simple_analysis.to_dict()
    nb.log(f"  - Результат: {result_dict}")
    
    # Тестируем строковое представление
    nb.log("3.2. Строковое представление:")
    nb.log(f"  - str(): {str(simple_analysis)}")
    nb.log(f"  - repr(): {repr(simple_analysis)}")
    
    # Тестируем сохранение в CSV
    nb.log("3.3. Сохранение в CSV:")
    try:
        csv_filename = "simple_analysis_result.csv"
        simple_analysis.save_to_csv(csv_filename)
        nb.log(f"  - Результат сохранен в {csv_filename}")
        
        # Проверяем созданный файл
        if os.path.exists(csv_filename):
            nb.log(f"  - Файл создан успешно, размер: {os.path.getsize(csv_filename)} байт")
            # Удаляем тестовый файл
            os.remove(csv_filename)
            nb.log(f"  - Тестовый файл удален")
    except Exception as e:
        nb.log(f"  - Ошибка сохранения: {str(e)}")

nb.wait()

# --- Шаг 4: Создание BaseAnalyzer ---
nb.step("Шаг 4: Создание BaseAnalyzer")

nb.info("Создаем и настраиваем базовый анализатор")

with nb.error_handling("Creating BaseAnalyzer"):
    # Создаем базовый анализатор с конфигурацией
    analyzer_config = {
        'min_data_points': 50,
        'max_data_points': 10000,
        'enable_logging': True,
        'cache_results': True
    }
    
    base_analyzer = BaseAnalyzer(
        name="DemoAnalyzer",
        config=analyzer_config
    )
    
    nb.log(f"Создан базовый анализатор:")
    nb.log(f"  - Имя: {base_analyzer.name}")
    nb.log(f"  - Конфигурация: {base_analyzer.config}")
    nb.log(f"  - Логгер: {base_analyzer.logger.name}")

nb.wait()

# --- Шаг 5: Валидация данных ---
nb.step("Шаг 5: Валидация данных")

nb.info("Тестируем валидацию данных в BaseAnalyzer")

with nb.error_handling("Testing data validation"):
    # Создаем тестовые данные
    nb.log("5.1. Создание тестовых данных:")
    
    # Валидные данные
    valid_data = pd.DataFrame({
        'price': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100),
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='h')
    })
    valid_data.set_index('timestamp', inplace=True)
    
    nb.log(f"  - Валидные данные: {valid_data.shape}, колонки: {list(valid_data.columns)}")
    
    # Невалидные данные
    empty_data = pd.DataFrame()
    small_data = pd.DataFrame({'price': [1, 2, 3]})  # Меньше min_data_points
    
    nb.log(f"  - Пустые данные: {empty_data.shape}")
    nb.log(f"  - Маленькие данные: {small_data.shape}")
    
    # Тестируем валидацию
    nb.log("5.2. Тестирование валидации:")
    
    valid_result = base_analyzer.validate_data(valid_data)
    nb.log(f"  - Валидные данные: {valid_result}")
    
    empty_result = base_analyzer.validate_data(empty_data)
    nb.log(f"  - Пустые данные: {empty_result}")
    
    small_result = base_analyzer.validate_data(small_data)
    nb.log(f"  - Маленькие данные: {small_result}")

nb.wait()

# --- Шаг 6: Подготовка данных ---
nb.step("Шаг 6: Подготовка данных")

nb.info("Тестируем подготовку данных в BaseAnalyzer")

with nb.error_handling("Testing data preparation"):
    # Создаем неотсортированные данные
    nb.log("6.1. Создание неотсортированных данных:")
    
    unsorted_data = valid_data.copy()
    # Перемешиваем индексы
    unsorted_data = unsorted_data.sample(frac=1.0)
    nb.log(f"  - Неотсортированные данные: {unsorted_data.shape}")
    nb.log(f"  - Первые 3 индекса: {list(unsorted_data.index[:3])}")
    
    # Тестируем подготовку данных
    nb.log("6.2. Подготовка данных:")
    prepared_data = base_analyzer.prepare_data(unsorted_data)
    
    nb.log(f"  - Подготовленные данные: {prepared_data.shape}")
    nb.log(f"  - Первые 3 индекса: {list(prepared_data.index[:3])}")
    nb.log(f"  - Отсортированы: {prepared_data.index.is_monotonic_increasing}")

nb.wait()

# --- Шаг 7: Создание пользовательского анализатора ---
nb.step("Шаг 7: Создание пользовательского анализатора")

nb.info("Создаем пользовательский анализатор на основе BaseAnalyzer")

with nb.error_handling("Creating custom analyzer"):
    class CustomPriceAnalyzer(BaseAnalyzer):
        """Пользовательский анализатор цен."""
        
        def __init__(self, price_threshold: float = 100.0):
            config = {
                'price_threshold': price_threshold,
                'min_data_points': 10
            }
            super().__init__("CustomPriceAnalyzer", config)
            self.price_threshold = price_threshold
        
        def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
            """Анализ ценовых данных."""
            if not self.validate_data(data):
                raise ValueError("Invalid data for analysis")
            
            # Подготавливаем данные
            prepared_data = self.prepare_data(data)
            
            # Простой анализ цен
            price_series = prepared_data['price']
            above_threshold = (price_series > self.price_threshold).sum()
            below_threshold = (price_series <= self.price_threshold).sum()
            
            results = {
                'total_points': len(price_series),
                'above_threshold': above_threshold,
                'below_threshold': below_threshold,
                'above_threshold_pct': above_threshold / len(price_series) * 100,
                'price_stats': {
                    'mean': price_series.mean(),
                    'std': price_series.std(),
                    'min': price_series.min(),
                    'max': price_series.max()
                }
            }
            
            metadata = {
                'analyzer': self.name,
                'price_threshold': self.price_threshold,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return AnalysisResult(
                analysis_type='custom_price_analysis',
                results=results,
                data_size=len(data),
                metadata=metadata
            )
    
    # Создаем экземпляр пользовательского анализатора
    custom_analyzer = CustomPriceAnalyzer(price_threshold=100.0)
    nb.log(f"Создан пользовательский анализатор:")
    nb.log(f"  - Имя: {custom_analyzer.name}")
    nb.log(f"  - Порог цены: {custom_analyzer.price_threshold}")
    nb.log(f"  - Конфигурация: {custom_analyzer.config}")

nb.wait()

# --- Шаг 8: Использование пользовательского анализатора ---
nb.step("Шаг 8: Использование пользовательского анализатора")

nb.info("Тестируем пользовательский анализатор на реальных данных")

with nb.error_handling("Testing custom analyzer"):
    # Анализируем данные
    nb.log("8.1. Выполнение анализа:")
    analysis_result = custom_analyzer.analyze(valid_data)
    
    nb.log(f"  - Тип анализа: {analysis_result.analysis_type}")
    nb.log(f"  - Размер данных: {analysis_result.data_size}")
    nb.log(f"  - Время анализа: {analysis_result.timestamp}")
    
    # Показываем результаты
    nb.log("8.2. Результаты анализа:")
    results = analysis_result.results
    nb.log(f"  - Всего точек: {results['total_points']}")
    nb.log(f"  - Выше порога: {results['above_threshold']} ({results['above_threshold_pct']:.1f}%)")
    nb.log(f"  - Ниже порога: {results['below_threshold']}")
    
    nb.log("  - Статистика цен:")
    price_stats = results['price_stats']
    for stat, value in price_stats.items():
        nb.log(f"    * {stat}: {value:.2f}")
    
    # Показываем метаданные
    nb.log("8.3. Метаданные:")
    for key, value in analysis_result.metadata.items():
        nb.log(f"  - {key}: {value}")

nb.wait()

# --- Шаг 9: Фабрика анализаторов ---
nb.step("Шаг 9: Фабрика анализаторов")

nb.info("Тестируем фабрику анализаторов и получение списка доступных")

with nb.error_handling("Testing analyzer factory"):
    # Получаем список доступных анализаторов
    nb.log("9.1. Список доступных анализаторов:")
    available_analyzers = get_available_analyzers()
    
    if available_analyzers:
        for analyzer_name, description in available_analyzers.items():
            nb.log(f"  - {analyzer_name}: {description}")
    else:
        nb.log("  - Доступные анализаторы не найдены")
    
    # Тестируем создание анализатора через фабрику
    nb.log("9.2. Создание анализатора через фабрику:")
    
    try:
        # Пытаемся создать анализатор через фабрику
        factory_analyzer = create_analyzer('statistical', alpha=0.05)
        nb.log(f"  - Создан анализатор: {factory_analyzer.name}")
        nb.log(f"  - Тип: {factory_analyzer.__class__.__name__}")
        nb.log(f"  - Конфигурация: {factory_analyzer.config}")
    except Exception as e:
        nb.log(f"  - Ошибка создания через фабрику: {str(e)}")
        nb.log("  - Это ожидаемо, так как фабрика пока возвращает базовый анализатор")

nb.wait()

# --- Шаг 10: Интеграция и экспорт ---
nb.step("Шаг 10: Интеграция и экспорт")

nb.info("Демонстрируем интеграцию и экспорт результатов")

with nb.error_handling("Integration and export"):
    # Создаем несколько результатов анализа
    nb.log("10.1. Создание множественных результатов:")
    
    analysis_results = []
    
    # Анализ с разными порогами
    for threshold in [95.0, 100.0, 105.0]:
        analyzer = CustomPriceAnalyzer(price_threshold=threshold)
        result = analyzer.analyze(valid_data)
        analysis_results.append(result)
        nb.log(f"  - Создан анализ с порогом {threshold}: {result.analysis_type}")
    
    # Сравниваем результаты
    nb.log("10.2. Сравнение результатов:")
    for i, result in enumerate(analysis_results):
        threshold = result.metadata['price_threshold']
        above_pct = result.results['above_threshold_pct']
        nb.log(f"  - Порог {threshold}: {above_pct:.1f}% точек выше порога")
    
    # Экспорт всех результатов
    nb.log("10.3. Экспорт результатов:")
    try:
        export_filename = "multiple_analysis_results.csv"
        
        # Создаем сводную таблицу
        summary_data = []
        for result in analysis_results:
            summary_data.append({
                'analysis_type': result.analysis_type,
                'threshold': result.metadata['price_threshold'],
                'total_points': result.results['total_points'],
                'above_threshold': result.results['above_threshold'],
                'above_threshold_pct': result.results['above_threshold_pct'],
                'avg_price': result.results['price_stats']['mean'],
                'price_volatility': result.results['price_stats']['std']
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(export_filename, index=False)
        
        nb.log(f"  - Сводка экспортирована в {export_filename}")
        nb.log(f"  - Размер файла: {os.path.getsize(export_filename)} байт")
        
        # Показываем содержимое
        nb.log("  - Содержимое экспорта:")
        nb.log(str(summary_df))
        
        # Удаляем тестовый файл
        os.remove(export_filename)
        nb.log(f"  - Тестовый файл удален")
        
    except Exception as e:
        nb.log(f"  - Ошибка экспорта: {str(e)}")

nb.wait()

# --- Завершение ---
nb.step("Завершение")

nb.info("Демонстрация базовых классов bquant.analysis завершена")
nb.log("Изучены:")
nb.log("  ✓ AnalysisResult - для хранения результатов анализа")
nb.log("  ✓ BaseAnalyzer - базовый класс для всех анализаторов")
nb.log("  ✓ Пользовательские анализаторы на основе BaseAnalyzer")
nb.log("  ✓ Фабрика анализаторов и получение списка доступных")
nb.log("  ✓ Валидация и подготовка данных")
nb.log("  ✓ Экспорт результатов анализа")

nb.log("\nГотово к созданию специализированных анализаторов!")

# Завершаем работу
nb.finish()
