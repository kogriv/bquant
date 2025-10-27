#!/usr/bin/env python3
"""
Демонстрация статистического анализа bquant.analysis.statistical

Этот скрипт демонстрирует работу с модулем статистического анализа:
- StatisticalAnalyzer - базовый класс статистического анализа
- HypothesisTestSuite - комплексное тестирование гипотез
- Описательная статистика, тесты нормальности, корреляционный анализ

Запуск: python 03_analysis_statistical.py [--no-trap]
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем путь к корню проекта для импорта bquant
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bquant.core.nb import NotebookSimulator
from bquant.analysis.statistical import (
    StatisticalAnalyzer,
    HypothesisTestSuite
)

# Создаем экземпляр NotebookSimulator
nb = NotebookSimulator(
    description="Изучаем статистический анализ данных и тестирование гипотез"
)

# --- Шаг 1: Инициализация и обзор ---
nb.step("Шаг 1: Инициализация и обзор")

nb.info("Изучаем модуль статистического анализа bquant.analysis.statistical")
nb.log("Доступные компоненты:")
nb.log("  - StatisticalAnalyzer - базовый класс статистического анализа")
nb.log("  - HypothesisTestSuite - комплексное тестирование гипотез")
nb.log("  - Функции для описательной статистики, тестов нормальности, корреляционного анализа")

# Создаем тестовые данные
np.random.seed(42)  # Для воспроизводимости
nb.log("\nСоздание тестовых данных...")

# Создаем OHLCV данные с различными характеристиками
dates = pd.date_range('2024-01-01', periods=500, freq='H')
returns = np.random.randn(500) * 0.02  # 2% волатильность
prices = 100 * np.exp(np.cumsum(returns))  # Логарифмические доходности

test_data = pd.DataFrame({
    'open': prices * (1 + np.random.randn(500) * 0.001),
    'high': prices * (1 + np.abs(np.random.randn(500) * 0.005)),
    'low': prices * (1 - np.abs(np.random.randn(500) * 0.005)),
    'close': prices,
    'volume': np.random.randint(1000, 10000, 500)
}, index=dates)

# Добавляем производные показатели
test_data['returns'] = test_data['close'].pct_change()
test_data['volatility'] = test_data['returns'].rolling(20).std()
test_data['price_range'] = (test_data['high'] - test_data['low']) / test_data['close']

nb.log(f"Создан тестовый датасет: {test_data.shape}")
nb.log(f"Колонки: {list(test_data.columns)}")
nb.log(f"Период: {test_data.index[0]} - {test_data.index[-1]}")

nb.wait()

# --- Шаг 2: Создание StatisticalAnalyzer ---
nb.step("Шаг 2: Создание StatisticalAnalyzer")

nb.info("Создаем и настраиваем статистический анализатор")

with nb.error_handling("Creating StatisticalAnalyzer"):
    # Создаем анализатор с настройками
    analyzer_config = {
        'alpha': 0.05,  # Уровень значимости
        'min_sample_size': 30,  # Минимальный размер выборки
        'enable_outlier_detection': True,
        'confidence_level': 0.95
    }
    
    statistical_analyzer = StatisticalAnalyzer(config=analyzer_config)
    
    nb.log(f"Создан статистический анализатор:")
    nb.log(f"  - Имя: {statistical_analyzer.name}")
    nb.log(f"  - Конфигурация: {statistical_analyzer.config}")
    nb.log(f"  - Уровень значимости: {statistical_analyzer.default_alpha}")
    nb.log(f"  - Минимальный размер выборки: {statistical_analyzer.min_sample_size}")

nb.wait()

# --- Шаг 3: Описательная статистика ---
nb.step("Шаг 3: Описательная статистика")

nb.info("Вычисляем описательную статистику для различных показателей")

with nb.error_handling("Computing descriptive statistics"):
    # Анализируем основные показатели
    indicators = ['close', 'returns', 'volume', 'price_range']
    
    for indicator in indicators:
        if indicator in test_data.columns:
            nb.log(f"\n3.1. Статистика для {indicator}:")
            
            # Получаем данные без NaN
            data_series = test_data[indicator].dropna()
            
            if len(data_series) > 0:
                stats = statistical_analyzer.descriptive_statistics(data_series, indicator)
                
                nb.log(f"  - Количество: {stats.get('count', 'N/A')}")
                nb.log(f"  - Среднее: {stats.get('mean', 'N/A'):.6f}")
                nb.log(f"  - Стандартное отклонение: {stats.get('std', 'N/A'):.6f}")
                nb.log(f"  - Минимум: {stats.get('min', 'N/A'):.6f}")
                nb.log(f"  - Максимум: {stats.get('max', 'N/A'):.6f}")
                nb.log(f"  - Медиана: {stats.get('median', 'N/A'):.6f}")
                nb.log(f"  - Q25: {stats.get('q25', 'N/A'):.6f}")
                nb.log(f"  - Q75: {stats.get('q75', 'N/A'):.6f}")
                nb.log(f"  - Асимметрия: {stats.get('skewness', 'N/A'):.6f}")
                nb.log(f"  - Эксцесс: {stats.get('kurtosis', 'N/A'):.6f}")
                nb.log(f"  - Коэффициент вариации: {stats.get('cv', 'N/A'):.6f}")
            else:
                nb.log(f"  - Нет данных для анализа")

nb.wait()

# --- Шаг 4: Тесты нормальности ---
nb.step("Шаг 4: Тесты нормальности")

nb.info("Тестируем нормальность распределения различных показателей")

with nb.error_handling("Testing normality"):
    # Тестируем нормальность для основных показателей
    for indicator in ['returns', 'price_range']:
        if indicator in test_data.columns:
            nb.log(f"\n4.1. Тест нормальности для {indicator}:")
            
            data_series = test_data[indicator].dropna()
            
            if len(data_series) >= 3:
                normality_result = statistical_analyzer.normality_test(data_series)
                
                if 'error' not in normality_result:
                    nb.log(f"  - Тест Шапиро-Уилка:")
                    if 'shapiro' in normality_result:
                        shapiro = normality_result['shapiro']
                        nb.log(f"    * Статистика: {shapiro.get('statistic', 'N/A'):.6f}")
                        nb.log(f"    * p-значение: {shapiro.get('p_value', 'N/A'):.6f}")
                        nb.log(f"    * Нормальное: {'Да' if shapiro.get('is_normal', False) else 'Нет'}")
                    
                    nb.log(f"  - Тест Колмогорова-Смирнова:")
                    if 'ks' in normality_result:
                        ks = normality_result['ks']
                        nb.log(f"    * Статистика: {ks.get('statistic', 'N/A'):.6f}")
                        nb.log(f"    * p-значение: {ks.get('p_value', 'N/A'):.6f}")
                        nb.log(f"    * Нормальное: {'Да' if ks.get('is_normal', False) else 'Нет'}")
                    
                    nb.log(f"  - Общий результат: {'Нормальное' if normality_result.get('is_normal', False) else 'Не нормальное'}")
                else:
                    nb.log(f"  - Ошибка: {normality_result['error']}")
            else:
                nb.log(f"  - Недостаточно данных для теста")

nb.wait()

# --- Шаг 5: Корреляционный анализ ---
nb.step("Шаг 5: Корреляционный анализ")

nb.info("Анализируем корреляции между различными показателями")

with nb.error_handling("Correlation analysis"):
    # Выбираем числовые колонки для корреляционного анализа
    numeric_columns = test_data.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_columns) >= 2:
        nb.log("5.1. Корреляционная матрица:")
        
        # Вычисляем корреляции
        correlation_matrix = test_data[numeric_columns].corr()
        nb.log(f"  - Размер матрицы: {correlation_matrix.shape}")
        
        # Показываем основные корреляции
        nb.log("5.2. Основные корреляции:")
        for i in range(len(numeric_columns)):
            for j in range(i + 1, len(numeric_columns)):
                col1, col2 = numeric_columns[i], numeric_columns[j]
                corr_value = correlation_matrix.loc[col1, col2]
                nb.log(f"  - {col1} ↔ {col2}: {corr_value:.4f}")
        
        # Тестируем значимость корреляций
        nb.log("5.3. Тестирование значимости корреляций:")
        for i in range(len(numeric_columns)):
            for j in range(i + 1, len(numeric_columns)):
                col1, col2 = numeric_columns[i], numeric_columns[j]
                
                # Получаем данные без NaN
                data1 = test_data[col1].dropna()
                data2 = test_data[col2].dropna()
                
                # Приводим к общему индексу
                common_index = data1.index.intersection(data2.index)
                if len(common_index) >= 30:
                    data1_common = data1.loc[common_index]
                    data2_common = data2.loc[common_index]
                    
                    # Тестируем корреляцию
                    try:
                        from scipy.stats import pearsonr
                        corr, p_value = pearsonr(data1_common, data2_common)
                        significant = p_value < 0.05
                        nb.log(f"  - {col1} ↔ {col2}: r={corr:.4f}, p={p_value:.4f}, значима={'Да' if significant else 'Нет'}")
                    except Exception as e:
                        nb.log(f"  - {col1} ↔ {col2}: ошибка тестирования - {str(e)}")
    else:
        nb.log("  - Недостаточно числовых колонок для корреляционного анализа")

nb.wait()

# --- Шаг 6: Создание HypothesisTestSuite ---
nb.step("Шаг 6: Создание HypothesisTestSuite")

nb.info("Создаем набор статистических тестов для анализа торговых данных")

with nb.error_handling("Creating HypothesisTestSuite"):
    # Создаем набор тестов с различными уровнями значимости
    test_suites = {
        'conservative': HypothesisTestSuite(alpha=0.01),
        'standard': HypothesisTestSuite(alpha=0.05),
        'liberal': HypothesisTestSuite(alpha=0.10)
    }
    
    nb.log("Созданы наборы тестов:")
    for name, suite in test_suites.items():
        nb.log(f"  - {name}: α = {suite.alpha}")

nb.wait()

# --- Шаг 7: Тестирование гипотез о зонах ---
nb.step("Шаг 7: Тестирование гипотез о зонах")

nb.info("Тестируем гипотезы о влиянии различных факторов на торговые результаты")

with nb.error_handling("Testing trading hypotheses"):
    # Создаем синтетические данные о зонах для демонстрации
    nb.log("7.1. Создание синтетических данных о зонах:")
    
    # Создаем данные о зонах
    zone_data = []
    for i in range(100):
        zone_data.append({
            'zone_id': f'zone_{i}',
            'duration': np.random.randint(2, 20),
            'price_return': np.random.randn() * 0.05,
            'volume_ratio': np.random.uniform(0.5, 2.0),
            'volatility': np.random.uniform(0.01, 0.05),
            'zone_type': np.random.choice(['bull', 'bear', 'neutral'])
        })
    
    nb.log(f"  - Создано {len(zone_data)} синтетических зон")
    
    # Тестируем гипотезы с разными уровнями значимости
    for suite_name, test_suite in test_suites.items():
        nb.log(f"\n7.2. Тестирование с {suite_name} уровнем значимости (α = {test_suite.alpha}):")
        
        try:
            # Тестируем гипотезу о влиянии длительности на доходность
            duration_result = test_suite.test_zone_duration_hypothesis(zone_data)
            
            nb.log(f"  - Гипотеза: {duration_result.hypothesis}")
            nb.log(f"  - Тип теста: {duration_result.test_type}")
            nb.log(f"  - Статистика: {duration_result.statistic:.6f}")
            nb.log(f"  - p-значение: {duration_result.p_value:.6f}")
            nb.log(f"  - Значимый: {'Да' if duration_result.significant else 'Нет'}")
            nb.log(f"  - Размер эффекта: {duration_result.effect_size:.6f}" if duration_result.effect_size else "  - Размер эффекта: N/A")
            
        except Exception as e:
            nb.log(f"  - Ошибка тестирования: {str(e)}")

nb.wait()

# --- Шаг 8: Анализ распределений ---
nb.step("Шаг 8: Анализ распределений")

nb.info("Анализируем распределения различных торговых показателей")

with nb.error_handling("Distribution analysis"):
    # Анализируем распределения основных показателей
    for indicator in ['returns', 'volume', 'price_range']:
        if indicator in test_data.columns:
            nb.log(f"\n8.1. Анализ распределения {indicator}:")
            
            data_series = test_data[indicator].dropna()
            
            if len(data_series) > 0:
                # Базовые характеристики распределения
                stats = statistical_analyzer.descriptive_statistics(data_series, indicator)
                
                nb.log(f"  - Форма распределения:")
                nb.log(f"    * Асимметрия: {stats.get('skewness', 'N/A'):.4f}")
                nb.log(f"    * Эксцесс: {stats.get('kurtosis', 'N/A'):.4f}")
                
                # Интерпретация асимметрии
                skewness = stats.get('skewness', 0)
                if abs(skewness) < 0.5:
                    skew_interpretation = "Примерно симметричное"
                elif skewness > 0.5:
                    skew_interpretation = "Правостороннее (положительная асимметрия)"
                else:
                    skew_interpretation = "Левостороннее (отрицательная асимметрия)"
                
                nb.log(f"    * Интерпретация асимметрии: {skew_interpretation}")
                
                # Интерпретация эксцесса
                kurtosis = stats.get('kurtosis', 0)
                if abs(kurtosis) < 2:
                    kurt_interpretation = "Нормальный эксцесс"
                elif kurtosis > 2:
                    kurt_interpretation = "Высокий эксцесс (островершинное)"
                else:
                    kurt_interpretation = "Низкий эксцесс (плосковершинное)"
                
                nb.log(f"    * Интерпретация эксцесса: {kurt_interpretation}")
                
                # Квантили для понимания хвостов
                nb.log(f"  - Квантили (хвосты распределения):")
                nb.log(f"    * 1%: {data_series.quantile(0.01):.6f}")
                nb.log(f"    * 5%: {data_series.quantile(0.05):.6f}")
                nb.log(f"    * 95%: {data_series.quantile(0.95):.6f}")
                nb.log(f"    * 99%: {data_series.quantile(0.99):.6f}")

nb.wait()

# --- Шаг 9: Статистические тесты для торговых стратегий ---
nb.step("Шаг 9: Статистические тесты для торговых стратегий")

nb.info("Тестируем статистическую значимость торговых стратегий")

with nb.error_handling("Testing trading strategies"):
    # Создаем синтетические результаты стратегий
    nb.log("9.1. Создание данных о результатах стратегий:")
    
    # Стратегия 1: Простая покупка и удержание
    buy_hold_returns = test_data['returns'].dropna()
    
    # Стратегия 2: Стратегия на основе волатильности (покупка при низкой волатильности)
    volatility_strategy = test_data.copy()
    volatility_strategy['volatility_signal'] = (
        volatility_strategy['volatility']
        < volatility_strategy['volatility'].rolling(20).mean()
    ).astype(float)
    volatility_strategy['strategy_return'] = volatility_strategy['returns'] * (
        volatility_strategy['volatility_signal'].shift(1).fillna(0.0)
    )
    volatility_returns = volatility_strategy['strategy_return'].dropna().astype(float)
    
    # Стратегия 3: Стратегия на основе объема (покупка при высоком объеме)
    volume_strategy = test_data.copy()
    volume_strategy['volume_signal'] = (
        volume_strategy['volume']
        > volume_strategy['volume'].rolling(20).mean()
    ).astype(float)
    volume_strategy['strategy_return'] = volume_strategy['returns'] * (
        volume_strategy['volume_signal'].shift(1).fillna(0.0)
    )
    volume_returns = volume_strategy['strategy_return'].dropna().astype(float)
    
    nb.log(f"  - Buy & Hold: {len(buy_hold_returns)} наблюдений")
    nb.log(f"  - Волатильностная стратегия: {len(volatility_returns)} наблюдений")
    nb.log(f"  - Объемная стратегия: {len(volume_returns)} наблюдений")
    
    # Тестируем статистическую значимость стратегий
    nb.log("\n9.2. Статистическое сравнение стратегий:")
    
    strategies = {
        'Buy & Hold': buy_hold_returns,
        'Volatility Strategy': volatility_returns,
        'Volume Strategy': volume_returns
    }
    
    # Вычисляем статистики для каждой стратегии
    strategy_stats = {}
    for name, returns in strategies.items():
        if len(returns) > 0:
            stats = statistical_analyzer.descriptive_statistics(returns, name)
            strategy_stats[name] = stats
            
            nb.log(f"  - {name}:")
            nb.log(f"    * Средняя доходность: {stats.get('mean', 'N/A'):.6f}")
            nb.log(f"    * Волатильность: {stats.get('std', 'N/A'):.6f}")
            nb.log(f"    * Коэффициент Шарпа: {stats.get('mean', 0) / stats.get('std', 1):.4f}" if stats.get('std', 0) != 0 else "    * Коэффициент Шарпа: N/A")
    
    # Тестируем различия между стратегиями
    nb.log("\n9.3. Тестирование различий между стратегиями:")
    
    if len(strategies) >= 2:
        strategy_names = list(strategies.keys())
        for i in range(len(strategy_names)):
            for j in range(i + 1, len(strategy_names)):
                name1, name2 = strategy_names[i], strategy_names[j]
                returns1 = strategies[name1]
                returns2 = strategies[name2]
                
                if len(returns1) >= 10 and len(returns2) >= 10:
                    try:
                        from scipy.stats import ttest_ind
                        t_stat, p_value = ttest_ind(returns1, returns2)
                        significant = p_value < 0.05
                        
                        nb.log(f"  - {name1} vs {name2}:")
                        nb.log(f"    * t-статистика: {t_stat:.4f}")
                        nb.log(f"    * p-значение: {p_value:.6f}")
                        nb.log(f"    * Значимое различие: {'Да' if significant else 'Нет'}")
                        
                    except Exception as e:
                        nb.log(f"  - {name1} vs {name2}: ошибка тестирования - {str(e)}")

nb.wait()

# --- Шаг 10: Интеграция и экспорт результатов ---
nb.step("Шаг 10: Интеграция и экспорт результатов")

nb.info("Интегрируем все результаты анализа и экспортируем их")

with nb.error_handling("Integration and export"):
    # Создаем сводный отчет
    nb.log("10.1. Создание сводного отчета:")
    
    summary_report = {
        'analysis_timestamp': datetime.now().isoformat(),
        'data_summary': {
            'total_observations': len(test_data),
            'time_period': f"{test_data.index[0]} - {test_data.index[-1]}",
            'columns_analyzed': list(test_data.select_dtypes(include=[np.number]).columns)
        },
        'statistical_summary': {},
        'hypothesis_tests': {},
        'strategy_analysis': {}
    }
    
    # Добавляем статистическую сводку
    for indicator in ['returns', 'volume', 'price_range']:
        if indicator in test_data.columns:
            data_series = test_data[indicator].dropna()
            if len(data_series) > 0:
                stats = statistical_analyzer.descriptive_statistics(data_series, indicator)
                summary_report['statistical_summary'][indicator] = {
                    'mean': stats.get('mean', 'N/A'),
                    'std': stats.get('std', 'N/A'),
                    'skewness': stats.get('skewness', 'N/A'),
                    'kurtosis': stats.get('kurtosis', 'N/A'),
                    'is_normal': False  # Будет заполнено ниже
                }
                
                # Тестируем нормальность
                try:
                    normality_result = statistical_analyzer.normality_test(data_series)
                    if 'error' not in normality_result:
                        summary_report['statistical_summary'][indicator]['is_normal'] = normality_result.get('is_normal', False)
                except:
                    pass
    
    # Добавляем результаты тестирования гипотез
    summary_report['hypothesis_tests'] = {
        'test_suites': list(test_suites.keys()),
        'alpha_levels': [suite.alpha for suite in test_suites.values()],
        'zones_analyzed': len(zone_data)
    }
    
    # Добавляем анализ стратегий
    summary_report['strategy_analysis'] = {
        'strategies_tested': list(strategies.keys()),
        'total_strategies': len(strategies)
    }
    
    nb.log(f"  - Сводный отчет создан")
    nb.log(f"  - Анализировано показателей: {len(summary_report['statistical_summary'])}")
    nb.log(f"  - Протестировано стратегий: {len(strategies)}")
    
    # Экспорт результатов
    nb.log("\n10.2. Экспорт результатов:")
    
    try:
        # Экспорт сводного отчета в JSON
        import json
        json_filename = "statistical_analysis_report.json"
        
        # Конвертируем numpy типы в Python типы для JSON
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Рекурсивно конвертируем все значения
        def clean_dict(d):
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [clean_dict(v) for v in d]
            else:
                return convert_numpy(d)
        
        clean_summary = clean_dict(summary_report)
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(clean_summary, f, indent=2, ensure_ascii=False)
        
        nb.log(f"  - JSON отчет: {json_filename}")
        nb.log(f"  - Размер файла: {os.path.getsize(json_filename)} байт")
        
        # Экспорт статистических данных в CSV
        csv_filename = "statistical_analysis_data.csv"
        
        # Создаем DataFrame с основными статистиками
        stats_data = []
        for indicator, stats in summary_report['statistical_summary'].items():
            stats_data.append({
                'indicator': indicator,
                'mean': stats['mean'],
                'std': stats['std'],
                'skewness': stats['skewness'],
                'kurtosis': stats['kurtosis'],
                'is_normal': stats['is_normal']
            })
        
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_csv(csv_filename, index=False)
        
        nb.log(f"  - CSV данные: {csv_filename}")
        nb.log(f"  - Размер файла: {os.path.getsize(csv_filename)} байт")
        
        # Показываем содержимое CSV
        nb.log("  - Содержимое CSV:")
        nb.log(str(stats_df))
        
        # Удаляем тестовые файлы
        os.remove(json_filename)
        os.remove(csv_filename)
        nb.log(f"  - Тестовые файлы удалены")
        
    except Exception as e:
        nb.log(f"  - Ошибка экспорта: {str(e)}")

nb.wait()

# --- Завершение ---
nb.step("Завершение")

nb.info("Демонстрация статистического анализа bquant.analysis.statistical завершена")
nb.log("Изучены:")
nb.log("  ✓ StatisticalAnalyzer - базовый класс статистического анализа")
nb.log("  ✓ HypothesisTestSuite - комплексное тестирование гипотез")
nb.log("  ✓ Описательная статистика для торговых показателей")
nb.log("  ✓ Тесты нормальности распределений")
nb.log("  ✓ Корреляционный анализ между показателями")
nb.log("  ✓ Статистическое тестирование торговых стратегий")
nb.log("  ✓ Анализ распределений и их характеристик")
nb.log("  ✓ Экспорт результатов анализа")

nb.log("\nГотово к созданию скриптов для других модулей анализа!")

# Завершаем работу
nb.finish()
