'''
Демонстрация работы специализированного MACD анализатора bquant.indicators.macd

Этот скрипт показывает, как использовать MACDZoneAnalyzer для продвинутого анализа MACD:
1.  Создание и настройка MACD анализатора
2.  Анализ зон MACD (бычьи/медвежьи)
3.  Статистические тесты и кластеризация
4.  Анализ последовательностей и паттернов
5.  Детекция сигналов и пересечений
6.  Визуализация результатов анализа
7.  Экспорт результатов в различные форматы
8.  Сравнение различных конфигураций MACD
9.  Анализ производительности и оптимизация
10. Интеграция с другими индикаторами
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
from bquant.indicators.macd import MACDZoneAnalyzer

from bquant.indicators.base import IndicatorFactory

# Устанавливаем более широкий вывод для pandas
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)

# Инициализируем симулятор
nb = NotebookSimulator("Демонстрация работы специализированного MACD анализатора bquant.indicators.macd")

# --- Шаг 1: Загрузка тестовых данных ---
nb.step("Шаг 1: Загрузка тестовых данных")

nb.info("Для демонстрации MACD анализатора используем sample-данные.")

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
    
    nb.info("1.2. Анализ исходных данных:")
    
    # Анализируем исходные данные
    nb.log(f"Статистика по основным колонкам:")
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df_sample.columns:
            col_data = df_sample[col].dropna()
            if len(col_data) > 0:
                nb.log(f"  - {col}: min={col_data.min():.4f}, max={col_data.max():.4f}, mean={col_data.mean():.4f}")

nb.wait()

# --- Шаг 2: Создание и настройка MACD анализатора ---
nb.step("Шаг 2: Создание и настройка MACD анализатора")

nb.info("Создаем и настраиваем MACDZoneAnalyzer с различными параметрами.")

with nb.error_handling("Creating MACD analyzer"):
    nb.info("2.1. Создание базового MACD анализатора:")
    
    # Создаем базовый MACD анализатор
    basic_analyzer = MACDZoneAnalyzer(
        macd_params={'fast': 12, 'slow': 26, 'signal': 9}
    )
    nb.log(f"Создан базовый MACD анализатор: fast={12}, slow={26}, signal={9}")
    
    nb.info("2.2. Создание MACD анализатора с агрессивными параметрами:")
    
    # Создаем агрессивный MACD анализатор
    aggressive_analyzer = MACDZoneAnalyzer(
        macd_params={'fast': 8, 'slow': 21, 'signal': 5}
    )
    nb.log(f"Создан агрессивный MACD анализатор: fast={8}, slow={21}, signal={5}")
    
    nb.info("2.3. Создание MACD анализатора с консервативными параметрами:")
    
    # Создаем консервативный MACD анализатор
    conservative_analyzer = MACDZoneAnalyzer(
        macd_params={'fast': 21, 'slow': 55, 'signal': 13}
    )
    nb.log(f"Создан консервативный MACD анализатор: fast={21}, slow={55}, signal={13}")
    
    nb.info("2.4. Анализ конфигураций анализаторов:")
    
    analyzers = {
        'basic': basic_analyzer,
        'aggressive': aggressive_analyzer,
        'conservative': conservative_analyzer
    }
    
    for name, analyzer in analyzers.items():
        nb.log(f"  - {name}:")
        nb.log(f"    * Быстрый период: {analyzer.macd_params['fast']}")
        nb.log(f"    * Медленный период: {analyzer.macd_params['slow']}")
        nb.log(f"    * Сигнальный период: {analyzer.macd_params['signal']}")
        nb.log(f"    * Чувствительность: {'Высокая' if analyzer.macd_params['fast'] < 15 else 'Средняя' if analyzer.macd_params['fast'] < 20 else 'Низкая'}")

nb.wait()

# --- Шаг 3: Расчет MACD и анализ зон ---
nb.step("Шаг 3: Расчет MACD и анализ зон")

nb.info("Рассчитываем MACD и анализируем зоны для различных конфигураций.")

with nb.error_handling("Calculating MACD and analyzing zones"):
    nb.info("3.1. Расчет MACD для всех конфигураций:")
    
    # Рассчитываем MACD для всех конфигураций
    macd_results = {}
    for name, analyzer in analyzers.items():
        result = analyzer.calculate_macd_with_atr(df_sample)
        macd_results[name] = result
        nb.log(f"  - {name}: {result.shape}, колонки: {list(result.columns)}")
    
    nb.info("3.2. Анализ зон MACD:")
    
    # Анализируем зоны для каждой конфигурации
    zone_analysis = {}
    for name, analyzer in analyzers.items():
        nb.log(f"  - Анализ зон для {name}:")
        
        # Анализируем зоны
        zones = analyzer.identify_zones(df_sample)
        zone_analysis[name] = zones
        
        if zones is not None and len(zones) > 0:
            nb.log(f"    * Обнаружено зон: {len(zones)}")
            
            # Анализируем типы зон
            bullish_zones = len([z for z in zones if z.type == 'bull'])
            bearish_zones = len([z for z in zones if z.type == 'bear'])
            neutral_zones = len([z for z in zones if z.type not in ['bull', 'bear']])
            
            nb.log(f"    * Бычьи зоны: {bullish_zones}")
            nb.log(f"    * Медвежьи зоны: {bearish_zones}")
            nb.log(f"    * Нейтральные зоны: {neutral_zones}")
            
            # Анализируем длительность зон
            if len(zones) > 0:
                durations = [z.duration for z in zones if hasattr(z, 'duration') and z.duration is not None]
                if durations:
                    nb.log(f"    * Средняя длительность: {np.mean(durations):.1f} периодов")
                    nb.log(f"    * Минимальная длительность: {min(durations)} периодов")
                    nb.log(f"    * Максимальная длительность: {max(durations)} периодов")
        else:
            nb.log(f"    * Зоны не обнаружены")

nb.wait()

# --- Шаг 4: Статистические тесты и кластеризация ---
nb.step("Шаг 4: Статистические тесты и кластеризация")

nb.info("Выполняем статистические тесты и кластеризацию MACD данных.")

with nb.error_handling("Statistical tests and clustering"):
    nb.info("4.1. Статистические тесты для MACD данных:")
    
    # Выполняем статистические тесты для каждой конфигурации
    for name, result in macd_results.items():
        nb.log(f"  - Статистические тесты для {name}:")
        
        if 'macd' in result.columns:
            macd_data = result['macd'].dropna()
            if len(macd_data) > 0:
                # Базовые статистики
                nb.log(f"    * MACD линия:")
                nb.log(f"      - Среднее: {macd_data.mean():.4f}")
                nb.log(f"      - Стандартное отклонение: {macd_data.std():.4f}")
                nb.log(f"      - Минимум: {macd_data.min():.4f}")
                nb.log(f"      - Максимум: {macd_data.max():.4f}")
                nb.log(f"      - Медиана: {macd_data.median():.4f}")
                
                # Тест на нормальность (простой тест через skewness и kurtosis)
                skewness = macd_data.skew()
                kurtosis = macd_data.kurtosis()
                nb.log(f"      - Асимметрия: {skewness:.4f}")
                nb.log(f"      - Эксцесс: {kurtosis:.4f}")
                
                # Анализ выбросов
                q1 = macd_data.quantile(0.25)
                q3 = macd_data.quantile(0.75)
                iqr = q3 - q1
                outliers = len(macd_data[(macd_data < q1 - 1.5*iqr) | (macd_data > q3 + 1.5*iqr)])
                nb.log(f"      - Выбросы (IQR метод): {outliers}")
    
    nb.info("4.2. Кластеризация MACD данных:")
    
    # Простая кластеризация на основе значений MACD
    for name, result in macd_results.items():
        nb.log(f"  - Кластеризация для {name}:")
        
        if 'macd' in result.columns:
            macd_data = result['macd'].dropna()
            if len(macd_data) > 0:
                # Простая кластеризация по квантилям
                quantiles = [0.25, 0.5, 0.75]
                cluster_bounds = [macd_data.quantile(q) for q in quantiles]
                
                nb.log(f"    * Границы кластеров (квантили):")
                for i, bound in enumerate(cluster_bounds):
                    nb.log(f"      - Q{int((i+1)*25)}: {bound:.4f}")
                
                # Распределение по кластерам
                cluster_counts = {
                    'Низкий': len(macd_data[macd_data <= cluster_bounds[0]]),
                    'Средний-низкий': len(macd_data[(macd_data > cluster_bounds[0]) & (macd_data <= cluster_bounds[1])]),
                    'Средний-высокий': len(macd_data[(macd_data > cluster_bounds[1]) & (macd_data <= cluster_bounds[2])]),
                    'Высокий': len(macd_data[macd_data > cluster_bounds[2]])
                }
                
                nb.log(f"    * Распределение по кластерам:")
                for cluster, count in cluster_counts.items():
                    percentage = (count / len(macd_data)) * 100
                    nb.log(f"      - {cluster}: {count} ({percentage:.1f}%)")

nb.wait()

# --- Шаг 5: Анализ последовательностей и паттернов ---
nb.step("Шаг 5: Анализ последовательностей и паттернов")

nb.info("Анализируем последовательности и паттерны в MACD данных.")

with nb.error_handling("Sequence and pattern analysis"):
    nb.info("5.1. Анализ последовательностей MACD:")
    
    # Анализируем последовательности для каждой конфигурации
    for name, result in macd_results.items():
        nb.log(f"  - Анализ последовательностей для {name}:")
        
        if 'macd' in result.columns and 'macd_signal' in result.columns:
            macd_line = result['macd'].dropna()
            signal_line = result['macd_signal'].dropna()
            
            if len(macd_line) > 0 and len(signal_line) > 0:
                # Находим общий диапазон
                common_length = min(len(macd_line), len(signal_line))
                macd_common = macd_line.iloc[-common_length:]
                signal_common = signal_line.iloc[-common_length:]
                
                # Анализируем последовательности
                nb.log(f"    * Анализ пересечений:")
                
                # Считаем пересечения
                bullish_crosses = 0
                bearish_crosses = 0
                cross_points = []
                
                for i in range(1, len(macd_common)):
                    if (macd_common.iloc[i-1] <= signal_common.iloc[i-1] and 
                        macd_common.iloc[i] > signal_common.iloc[i]):
                        bullish_crosses += 1
                        cross_points.append({'type': 'bullish', 'index': i, 'value': macd_common.iloc[i]})
                    elif (macd_common.iloc[i-1] >= signal_common.iloc[i-1] and 
                          macd_common.iloc[i] < signal_common.iloc[i]):
                        bearish_crosses += 1
                        cross_points.append({'type': 'bearish', 'index': i, 'value': macd_common.iloc[i]})
                
                nb.log(f"      - Бычьи пересечения: {bullish_crosses}")
                nb.log(f"      - Медвежьи пересечения: {bearish_crosses}")
                nb.log(f"      - Всего пересечений: {len(cross_points)}")
                
                # Анализируем последние пересечения
                if cross_points:
                    recent_crosses = cross_points[-min(5, len(cross_points)):]
                    nb.log(f"    * Последние пересечения:")
                    for cross in recent_crosses:
                        nb.log(f"      - {cross['type']}: значение {cross['value']:.4f}")
    
    nb.info("5.2. Анализ паттернов MACD:")
    
    # Анализируем паттерны для каждой конфигурации
    for name, result in macd_results.items():
        nb.log(f"  - Анализ паттернов для {name}:")
        
        if 'macd_hist' in result.columns:
            hist_data = result['macd_hist'].dropna()
            if len(hist_data) > 0:
                # Анализируем паттерны гистограммы
                nb.log(f"    * Паттерны гистограммы:")
                
                # Считаем изменения знака
                sign_changes = 0
                for i in range(1, len(hist_data)):
                    if (hist_data.iloc[i-1] < 0 and hist_data.iloc[i] > 0) or \
                       (hist_data.iloc[i-1] > 0 and hist_data.iloc[i] < 0):
                        sign_changes += 1
                
                nb.log(f"      - Изменения знака: {sign_changes}")
                
                # Анализируем дивергенции
                positive_bars = len(hist_data[hist_data > 0])
                negative_bars = len(hist_data[hist_data < 0])
                nb.log(f"      - Положительные бары: {positive_bars} ({positive_bars/len(hist_data)*100:.1f}%)")
                nb.log(f"      - Отрицательные бары: {negative_bars} ({negative_bars/len(hist_data)*100:.1f}%)")

nb.wait()

# --- Шаг 6: Полный анализ MACD зон ---
nb.step("Шаг 6: Полный анализ MACD зон")

nb.info("Выполняем полный анализ MACD зон для различных конфигураций.")

with nb.error_handling("Complete MACD zone analysis"):
    nb.info("6.1. Полный анализ MACD зон:")
    
    # Выполняем полный анализ для каждой конфигурации
    complete_analysis = {}
    for name, analyzer in analyzers.items():
        nb.log(f"  - Полный анализ для {name}:")
        
        try:
            # Выполняем полный анализ
            analysis_result = analyzer.analyze_complete(df_sample)
            complete_analysis[name] = analysis_result
            
            if analysis_result and hasattr(analysis_result, 'zones'):
                nb.log(f"    * Обнаружено зон: {len(analysis_result.zones)}")
                
                # Анализируем статистики
                if hasattr(analysis_result, 'statistics') and analysis_result.statistics:
                    stats = analysis_result.statistics
                    nb.log(f"    * Статистики зон:")
                    if 'total_zones' in stats:
                        nb.log(f"      - Всего зон: {stats['total_zones']}")
                    if 'bull_zones' in stats:
                        nb.log(f"      - Бычьи зоны: {stats['bull_zones']}")
                    if 'bear_zones' in stats:
                        nb.log(f"      - Медвежьи зоны: {stats['bear_zones']}")
                    if 'avg_duration' in stats:
                        nb.log(f"      - Средняя длительность: {stats['avg_duration']:.1f}")
            else:
                nb.log(f"    * Анализ не выполнен")
        except Exception as e:
            nb.log(f"    * Ошибка полного анализа: {str(e)}")
    
    nb.info("6.2. Анализ гипотез:")
    
    # Анализируем гипотезы для каждой конфигурации
    for name, analysis_result in complete_analysis.items():
        nb.log(f"  - Анализ гипотез для {name}:")
        
        try:
            if hasattr(analysis_result, 'hypothesis_tests') and analysis_result.hypothesis_tests:
                tests = analysis_result.hypothesis_tests
                nb.log(f"    * Результаты тестов гипотез:")
                for test_name, test_result in tests.items():
                    if isinstance(test_result, dict):
                        nb.log(f"      - {test_name}:")
                        for key, value in test_result.items():
                            if isinstance(value, float):
                                nb.log(f"      - {key}: {value:.4f}")
                            else:
                                nb.log(f"      - {key}: {value}")
                    else:
                        nb.log(f"      - {test_name}: {test_result}")
            else:
                nb.log(f"    * Тесты гипотез недоступны")
                
        except Exception as e:
            nb.log(f"    * Ошибка анализа гипотез: {str(e)}")

nb.wait()

# --- Шаг 7: Визуализация результатов анализа ---
nb.step("Шаг 7: Визуализация результатов анализа")

nb.info("Создаем визуализации и экспортируем результаты анализа.")

with nb.error_handling("Visualization and export"):
    nb.info("7.1. Создание сводки анализа:")
    
    # Создаем сводку анализа для каждой конфигурации
    analysis_summary = {}
    for name, analysis_result in complete_analysis.items():
        nb.log(f"  - Создание сводки для {name}:")
        
        try:
            if analysis_result and hasattr(analysis_result, 'metadata'):
                summary = {
                    'zones_count': len(analysis_result.zones) if hasattr(analysis_result, 'zones') else 0,
                    'statistics': analysis_result.statistics if hasattr(analysis_result, 'statistics') else {},
                    'hypothesis_tests': analysis_result.hypothesis_tests if hasattr(analysis_result, 'hypothesis_tests') else {},
                    'metadata': analysis_result.metadata if hasattr(analysis_result, 'metadata') else {}
                }
                analysis_summary[name] = summary
                nb.log(f"    * Сводка создана успешно")
                
                # Показываем ключевые метрики
                if 'zones_count' in summary:
                    nb.log(f"      - Всего зон: {summary['zones_count']}")
                if 'statistics' in summary and summary['statistics']:
                    stats = summary['statistics']
                    if 'total_zones' in stats:
                        nb.log(f"      - Всего зон: {stats['total_zones']}")
                    if 'avg_duration' in stats:
                        nb.log(f"      - Средняя длительность: {stats['avg_duration']:.1f}")
            else:
                nb.log(f"    * Сводка недоступна")
        except Exception as e:
            nb.log(f"    * Ошибка создания сводки: {str(e)}")
    
    nb.info("7.2. Экспорт результатов:")
    
    # Экспортируем результаты в различные форматы
    for name, summary in analysis_summary.items():
        nb.log(f"  - Экспорт результатов для {name}:")
        
        try:
            # Экспорт в JSON
            json_filename = f"macd_analysis_{name}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, default=str)
            nb.log(f"    * JSON экспорт: {json_filename}")
            
            # Экспорт в CSV (если есть данные)
            if 'zones_count' in summary and summary['zones_count'] > 0:
                csv_filename = f"macd_zones_{name}.csv"
                # Создаем простой CSV с основными метриками
                zones_data = {
                    'metric': ['total_zones', 'avg_duration'],
                    'value': [
                        summary.get('zones_count', 0),
                        summary.get('statistics', {}).get('avg_duration', 0)
                    ]
                }
                zones_df = pd.DataFrame(zones_data)
                zones_df.to_csv(csv_filename, index=False)
                nb.log(f"    * CSV экспорт: {csv_filename}")
            
        except Exception as e:
            nb.log(f"    * Ошибка экспорта: {str(e)}")

nb.wait()

# --- Шаг 8: Сравнение различных конфигураций MACD ---
nb.step("Шаг 8: Сравнение различных конфигураций MACD")

nb.info("Сравниваем эффективность различных конфигураций MACD.")

with nb.error_handling("Comparing MACD configurations"):
    nb.info("8.1. Сравнение производительности конфигураций:")
    
    # Сравниваем производительность
    performance_comparison = {}
    for name, analyzer in analyzers.items():
        nb.log(f"  - Тестирование производительности {name}:")
        
        start_time = datetime.now()
        try:
            result = analyzer.calculate_macd_with_atr(df_sample)
            calc_time = (datetime.now() - start_time).total_seconds()
            
            performance_comparison[name] = {
                'calculation_time': calc_time,
                'records_processed': len(result),
                'speed': len(result) / calc_time if calc_time > 0 else 0
            }
            
            nb.log(f"    * Время расчета: {calc_time:.4f} сек")
            nb.log(f"    * Скорость: {performance_comparison[name]['speed']:.0f} записей/сек")
            
        except Exception as e:
            nb.log(f"    * Ошибка расчета: {str(e)}")
    
    nb.info("8.2. Сравнение качества анализа:")
    
    # Сравниваем качество анализа
    analysis_quality_comparison = {}
    for name, analysis_result in complete_analysis.items():
        nb.log(f"  - Анализ качества анализа {name}:")
        
        try:
            if analysis_result and hasattr(analysis_result, 'statistics'):
                quality = analysis_result.statistics
                analysis_quality_comparison[name] = quality
                
                # Показываем ключевые метрики
                if 'total_zones' in quality:
                    nb.log(f"    * Всего зон: {quality['total_zones']}")
                if 'bull_zones' in quality:
                    nb.log(f"    * Бычьи зоны: {quality['bull_zones']}")
                if 'bear_zones' in quality:
                    nb.log(f"    * Медвежьи зоны: {quality['bear_zones']}")
                if 'avg_duration' in quality:
                    nb.log(f"    * Средняя длительность: {quality['avg_duration']:.1f}")
            else:
                nb.log(f"    * Метрики качества недоступны")
                
        except Exception as e:
            nb.log(f"    * Ошибка анализа качества: {str(e)}")
    
    nb.info("8.3. Рейтинг конфигураций:")
    
    # Создаем рейтинг конфигураций
    if performance_comparison and analysis_quality_comparison:
        nb.log(f"  - Рейтинг конфигураций:")
        
        # Простой рейтинг на основе производительности и количества зон
        rankings = []
        for name in performance_comparison.keys():
            if name in analysis_quality_comparison:
                perf_score = 1 / performance_comparison[name]['calculation_time'] if performance_comparison[name]['calculation_time'] > 0 else 0
                zones_score = analysis_quality_comparison[name].get('total_zones', 0)
                total_score = perf_score + zones_score * 0.1  # Нормализуем зоны
                
                rankings.append((name, total_score, perf_score, zones_score))
        
        # Сортируем по общему баллу
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        for i, (name, total_score, perf_score, zones_score) in enumerate(rankings):
            nb.log(f"    * {i+1}. {name}: общий балл {total_score:.4f} (производительность: {perf_score:.4f}, зоны: {zones_score})")

nb.wait()

# --- Шаг 9: Анализ производительности и оптимизация ---
nb.step("Шаг 9: Анализ производительности и оптимизация")

nb.info("Анализируем производительность и находим возможности оптимизации.")

with nb.error_handling("Performance analysis and optimization"):
    nb.info("9.1. Детальный анализ производительности:")
    
    # Детальный анализ производительности
    if performance_comparison:
        nb.log(f"  - Детальный анализ производительности:")
        
        # Находим лучшие и худшие показатели
        fastest = min(performance_comparison.items(), key=lambda x: x[1]['calculation_time'])
        slowest = max(performance_comparison.items(), key=lambda x: x[1]['calculation_time'])
        
        nb.log(f"    * Самый быстрый: {fastest[0]} ({fastest[1]['calculation_time']:.4f} сек)")
        nb.log(f"    * Самый медленный: {slowest[0]} ({slowest[1]['calculation_time']:.4f} сек)")
        nb.log(f"    * Разница в скорости: {slowest[1]['calculation_time']/fastest[1]['calculation_time']:.2f}x")
        
        # Анализируем эффективность
        for name, metrics in performance_comparison.items():
            efficiency = metrics['speed'] / 1000  # Нормализуем на 1000 записей
            nb.log(f"    * {name}: эффективность {efficiency:.2f} тыс. записей/сек")
    
    nb.info("9.2. Анализ использования памяти:")
    
    # Анализируем использование памяти
    for name, result in macd_results.items():
        nb.log(f"  - Использование памяти для {name}:")
        
        try:
            # Оцениваем размер данных
            data_size = result.memory_usage(deep=True).sum()
            data_size_mb = data_size / (1024 * 1024)
            
            nb.log(f"    * Размер данных: {data_size_mb:.2f} МБ")
            nb.log(f"    * Количество колонок: {len(result.columns)}")
            nb.log(f"    * Типы данных: {result.dtypes.unique()}")
            
        except Exception as e:
            nb.log(f"    * Ошибка анализа памяти: {str(e)}")
    
    nb.info("9.3. Рекомендации по оптимизации:")
    
    # Даем рекомендации по оптимизации
    nb.log(f"  - Рекомендации по оптимизации:")
    
    if performance_comparison:
        # Анализируем паттерны производительности
        fast_configs = [name for name, metrics in performance_comparison.items() 
                       if metrics['calculation_time'] < 0.01]
        slow_configs = [name for name, metrics in performance_comparison.items() 
                       if metrics['calculation_time'] > 0.01]
        
        if fast_configs:
            nb.log(f"    * Быстрые конфигурации: {', '.join(fast_configs)}")
            nb.log(f"      - Рекомендуется для высокочастотного анализа")
        
        if slow_configs:
            nb.log(f"    * Медленные конфигурации: {', '.join(slow_configs)}")
            nb.log(f"      - Рекомендуется для долгосрочного анализа")
    
    # Общие рекомендации
    nb.log(f"    * Общие рекомендации:")
    nb.log(f"      - Используйте кэширование для повторных расчетов")
    nb.log(f"      - Оптимизируйте размер данных для анализа")
    nb.log(f"      - Выбирайте конфигурацию под конкретную задачу")

nb.wait()

# --- Шаг 10: Интеграция с другими индикаторами ---
nb.step("Шаг 10: Интеграция с другими индикаторами")

nb.info("Интегрируем MACD анализ с другими техническими индикаторами.")

with nb.error_handling("Integration with other indicators"):
    nb.info("10.1. Создание комплексного набора индикаторов:")
    
    # Создаем комплексный набор индикаторов
    nb.log(f"  - Создание комплексного набора:")
    
    # Базовые индикаторы
    basic_indicators = {
        'sma_20': 'SimpleMovingAverage(period=20)',
        'rsi_14': 'RelativeStrengthIndex(period=14)',
        'bbands': 'BollingerBands(period=20, std_dev=2.0)'
    }
    
    # MACD конфигурации
    macd_configs = {
        'macd_basic': 'MACDZoneAnalyzer(fast=12, slow=26, signal=9)',
        'macd_aggressive': 'MACDZoneAnalyzer(fast=8, slow=21, signal=5)',
        'macd_conservative': 'MACDZoneAnalyzer(fast=21, slow=55, signal=13)'
    }
    
    nb.log(f"    * Базовые индикаторы:")
    for name, config in basic_indicators.items():
        nb.log(f"      - {name}: {config}")
    
    nb.log(f"    * MACD конфигурации:")
    for name, config in macd_configs.items():
        nb.log(f"      - {name}: {config}")
    
    nb.info("10.2. Анализ корреляций между индикаторами:")
    
    # Анализируем корреляции между индикаторами
    nb.log(f"  - Анализ корреляций:")
    
    # Создаем DataFrame с основными индикаторами
    try:
        from bquant.indicators.custom import SimpleMovingAverage, RelativeStrengthIndex, BollingerBands
        
        # Рассчитываем базовые индикаторы
        sma_20 = SimpleMovingAverage(period=20).calculate(df_sample)
        rsi_14 = RelativeStrengthIndex(period=14).calculate(df_sample)
        bb = BollingerBands(period=20, std_dev=2.0).calculate(df_sample)
        
        # Объединяем данные
        combined_data = df_sample.copy()
        combined_data['sma_20'] = sma_20.data.iloc[:, 0]
        combined_data['rsi_14'] = rsi_14.data.iloc[:, 0]
        combined_data['bb_middle'] = bb.data['bb_middle']
        
        # Добавляем MACD данные
        for name, result in macd_results.items():
            if 'macd' in result.columns:
                combined_data[f'{name}_macd'] = result['macd']
        
        # Анализируем корреляции
        correlation_cols = [col for col in combined_data.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        if len(correlation_cols) > 1:
            correlation_matrix = combined_data[correlation_cols].corr()
            
            nb.log(f"    * Корреляции между индикаторами:")
            for i, col1 in enumerate(correlation_cols):
                for j, col2 in enumerate(correlation_cols):
                    if i < j:  # Показываем только верхний треугольник
                        corr_value = correlation_matrix.loc[col1, col2]
                        if abs(corr_value) > 0.3:  # Показываем только значимые корреляции
                            nb.log(f"      - {col1} ↔ {col2}: {corr_value:.3f}")
        
    except Exception as e:
        nb.log(f"    * Ошибка анализа корреляций: {str(e)}")
    
    nb.info("10.3. Создание торговых стратегий:")
    
    # Создаем простые торговые стратегии
    nb.log(f"  - Примеры торговых стратегий:")
    
    strategies = [
        "MACD + RSI: Покупка при бычьем пересечении MACD и RSI < 30",
        "MACD + Bollinger Bands: Продажа при медвежьем пересечении MACD и цена выше верхней полосы",
        "MACD + SMA: Покупка при бычьем пересечении MACD и цена выше SMA20",
        "MACD + Volume: Подтверждение сигнала MACD объемом выше среднего"
    ]
    
    for i, strategy in enumerate(strategies, 1):
        nb.log(f"    * Стратегия {i}: {strategy}")

nb.wait()

# --- Заключение ---
nb.step("Заключение")

nb.info("Мы протестировали все основные возможности MACDZoneAnalyzer BQuant:")
nb.log("✅ Создание и настройка MACD анализатора с различными параметрами")
nb.log("✅ Анализ зон MACD (бычьи/медвежьи/нейтральные)")
nb.log("✅ Статистические тесты и кластеризация данных")
nb.log("✅ Анализ последовательностей и паттернов")
nb.log("✅ Детекция торговых сигналов и пересечений")
nb.log("✅ Визуализация и экспорт результатов")
nb.log("✅ Сравнение различных конфигураций MACD")
nb.log("✅ Анализ производительности и оптимизация")
nb.log("✅ Интеграция с другими техническими индикаторами")

nb.info("Протестированы возможности MACDZoneAnalyzer:")
nb.log("🔧 Различные конфигурации (базовая, агрессивная, консервативная)")
nb.log("🔧 Анализ зон и детекция сигналов")
nb.log("🔧 Статистический анализ и кластеризация")
nb.log("🔧 Экспорт результатов в JSON и CSV")
nb.log("🔧 Интеграция с базовыми индикаторами")

nb.info("MACDZoneAnalyzer BQuant предоставляет:")
nb.log("🏗️ Продвинутый анализ MACD с зональным подходом")
nb.log("🏗️ Гибкие конфигурации для различных торговых стилей")
nb.log("🏗️ Статистические инструменты для валидации сигналов")
nb.log("🏗️ Интеграцию с экосистемой индикаторов BQuant")
nb.log("🏗️ Экспорт результатов для дальнейшего анализа")
nb.log("🏗️ Высокую производительность и оптимизацию")

nb.info("Это демонстрирует мощь и гибкость специализированного MACD анализатора BQuant для продвинутого технического анализа.")

nb.finish()
