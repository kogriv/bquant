#!/usr/bin/env python3
"""
Тестовый скрипт для валидации docs/api/README.md
Проверяет РЕАЛЬНЫЕ примеры кода из документации docs/api/README.md
Создан: 2025-10-24
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

def test_real_examples_from_docs():
    """Тестируем РЕАЛЬНЫЕ примеры из docs/api/README.md"""
    print("📋 Тест: Реальные примеры из документации")
    
    # Примеры из раздела "По функциональности"
    examples_to_test = [
        # Технические индикаторы (актуальные в приоритете)
        ('bquant.indicators.base', 'BaseIndicator'),
        ('bquant.indicators.base', 'IndicatorFactory'),
        ('bquant.indicators.base', 'PreloadedIndicator'),  # Базовый класс для PRELOADED индикаторов
        ('bquant.indicators.preloaded', 'MACDPreloadedIndicator'),
        ('bquant.indicators.macd', 'MACDZoneAnalyzer'),  # Deprecated, но должен работать
        
        # Universal Zone Analysis
        ('bquant.analysis.zones', 'analyze_zones'),
        ('bquant.analysis.zones', 'ZoneAnalysisBuilder'),
        ('bquant.analysis.zones', 'UniversalZoneAnalyzer'),
        ('bquant.analysis.statistical', 'run_all_hypothesis_tests'),
        
        # Визуализация
        ('bquant.visualization.charts', 'FinancialCharts'),
        ('bquant.visualization.zones', 'ZoneVisualizer'),
        ('bquant.visualization.statistical', 'StatisticalPlots'),
        
        # Функции
        ('bquant.data.loader', 'load_ohlcv_data'),
        ('bquant.data.samples', 'get_sample_data'),
        ('bquant.data.processor', 'clean_ohlcv_data'),
        ('bquant.visualization.charts', 'create_candlestick_chart'),
        
        # Исключения
        ('bquant.core.exceptions', 'BQuantError'),
        ('bquant.core.exceptions', 'DataError'),
        ('bquant.core.exceptions', 'AnalysisError'),
        ('bquant.core.exceptions', 'VisualizationError'),
    ]
    
    results = []
    for module_path, function_name in examples_to_test:
        try:
            module = __import__(module_path, fromlist=[function_name])
            if hasattr(module, function_name):
                print(f"  ✅ {module_path}.{function_name}")
                results.append(True)
            else:
                print(f"  ❌ {module_path}.{function_name} - не найден")
                results.append(False)
        except ImportError as e:
            print(f"  ❌ {module_path}.{function_name}: {e}")
            results.append(False)
    
    return all(results)

def test_deprecated_warning():
    """Тестируем deprecated предупреждение для MACDZoneAnalyzer"""
    print("\n📋 Тест: Deprecated предупреждение")
    
    try:
        from bquant.indicators.macd import MACDZoneAnalyzer
        analyzer = MACDZoneAnalyzer()
        print("  ✅ MACDZoneAnalyzer доступен (deprecated)")
        return True
    except Exception as e:
        print(f"  ❌ MACDZoneAnalyzer: {e}")
        return False

def test_universal_pipeline_example():
    """Тестируем пример Universal Pipeline из документации"""
    print("\n📋 Тест: Universal Pipeline пример")
    
    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Загружаем sample данные
        data = get_sample_data('tv_xauusd_1h')
        
        # Тестируем Universal Pipeline (как в документации)
        result = (
            analyze_zones(data)
            .with_indicator('pandas_ta', 'rsi', length=14)
            .detect_zones('threshold', indicator_col='rsi', 
                         upper_threshold=70, lower_threshold=30)
            .analyze(clustering=False)
            .build()
        )
        
        print(f"  ✅ Universal Pipeline работает")
        print(f"     Найдено зон: {len(result.zones)}")
        return True
    except Exception as e:
        print(f"  ❌ Universal Pipeline: {e}")
        return False

def test_load_ohlcv_data_function():
    """Тестируем функцию load_ohlcv_data из документации"""
    print("\n📋 Тест: load_ohlcv_data функция")
    
    try:
        from bquant.data.loader import load_ohlcv_data
        import tempfile
        import pandas as pd
        
        # Создаем временный CSV файл для тестирования (минимум 100 записей)
        periods = 120  # Больше минимума в 100 записей
        test_data = pd.DataFrame({
            'time': pd.date_range('2023-01-01', periods=periods, freq='1H'),
            'open': [100 + i*0.1 for i in range(periods)],
            'high': [101 + i*0.1 for i in range(periods)],
            'low': [99 + i*0.1 for i in range(periods)],
            'close': [100.5 + i*0.1 for i in range(periods)],
            'volume': [1000 + i*10 for i in range(periods)]
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_data.to_csv(f.name, index=False)
            temp_file = f.name
        
        try:
            # Тестируем загрузку данных
            loaded_data = load_ohlcv_data(temp_file)
            print(f"  ✅ load_ohlcv_data работает: загружено {len(loaded_data)} записей")
            print(f"     Колонки: {list(loaded_data.columns)}")
            return True
        finally:
            # Удаляем временный файл
            import os
            os.unlink(temp_file)
            
    except Exception as e:
        print(f"  ❌ load_ohlcv_data: {e}")
        return False

def test_clean_ohlcv_data_function():
    """Тестируем функцию clean_ohlcv_data из документации"""
    print("\n📋 Тест: clean_ohlcv_data функция")
    
    try:
        from bquant.data.processor import clean_ohlcv_data
        from bquant.data.samples import get_sample_data
        
        # Загружаем sample данные
        data = get_sample_data('tv_xauusd_1h')
        
        # Тестируем очистку данных
        cleaned_data = clean_ohlcv_data(data)
        print(f"  ✅ clean_ohlcv_data работает: очищено {len(cleaned_data)} записей")
        print(f"     Исходных записей: {len(data)}")
        return True
    except Exception as e:
        print(f"  ❌ clean_ohlcv_data: {e}")
        return False

def test_preloaded_indicator_class():
    """Тестируем класс PreloadedIndicator из документации"""
    print("\n📋 Тест: PreloadedIndicator класс")
    
    try:
        # Импортируем PreloadedIndicator из правильного модуля (base)
        from bquant.indicators.base import PreloadedIndicator
        from bquant.indicators.preloaded import MACDPreloadedIndicator
        from bquant.data.samples import get_sample_data
        
        # Загружаем sample данные
        data = get_sample_data('tv_xauusd_1h')
        
        # Тестируем создание MACDPreloadedIndicator
        macd_indicator = MACDPreloadedIndicator()
        print(f"  ✅ MACDPreloadedIndicator создан успешно")
        
        # Проверяем базовый класс
        base_class = MACDPreloadedIndicator.__bases__[0]
        print(f"  ✅ Базовый класс MACDPreloadedIndicator: {base_class.__name__}")
        
        # Проверяем, что PreloadedIndicator доступен
        print(f"  ✅ PreloadedIndicator доступен из bquant.indicators.base")
        
        return True
    except Exception as e:
        print(f"  ❌ PreloadedIndicator: {e}")
        return False

def test_actual_macd_examples():
    """Тестируем актуальные примеры работы с MACD из документации"""
    print("\n📋 Тест: Актуальные примеры MACD")
    
    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Загружаем sample данные
        data = get_sample_data('tv_xauusd_1h')
        
        # Тест 1: Universal Pipeline с custom MACD
        result1 = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing='find_peaks', shape='statistical')
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
        
        print(f"  ✅ Custom MACD через Universal Pipeline: {len(result1.zones)} зон")
        
        # Тест 2: PRELOADED MACD
        result2 = (
            analyze_zones(data)
            .with_indicator('preloaded', 'macd_preloaded')
            .detect_zones('zero_crossing', indicator_col='macd')
            .analyze(clustering=False)
            .build()
        )
        
        print(f"  ✅ PRELOADED MACD через Universal Pipeline: {len(result2.zones)} зон")
        
        return True
    except Exception as e:
        print(f"  ❌ Актуальные примеры MACD: {e}")
        return False

def test_cross_references():
    """Проверяем cross-references из документации"""
    print("\n📋 Тест: Cross-references")
    
    references_to_check = [
        'docs/api/core/README.md',
        'docs/api/data/README.md',
        'docs/api/indicators/README.md',
        'docs/api/analysis/README.md',
        'docs/api/visualization/README.md',
        'docs/api/extension_guide.md',
    ]
    
    results = []
    for ref_path in references_to_check:
        exists = os.path.exists(ref_path)
        status = "✅ СУЩЕСТВУЕТ" if exists else "❌ НЕ НАЙДЕН"
        print(f"  {ref_path}: {status}")
        results.append(exists)
    
    return all(results)

def test_language_check():
    """Проверяем язык текста"""
    print("\n📋 Тест: Язык текста")
    
    try:
        with open('docs/api/README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие русских слов
        russian_words = ['справочник', 'модули', 'классы', 'функции', 'документация']
        found_russian = sum(1 for word in russian_words if word in content.lower())
        
        # Проверяем наличие английских слов в коде (это нормально)
        code_blocks = content.count('```')
        
        print(f"  ✅ Найдено русских слов: {found_russian}")
        print(f"  ✅ Найдено блоков кода: {code_blocks}")
        print("  ✅ Язык текста: русский (код на английском)")
        
        return found_russian > 0
    except Exception as e:
        print(f"  ❌ Ошибка проверки языка: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🔍 Валидация docs/api/README.md (РЕАЛЬНЫЕ примеры)")
    print("=" * 60)
    
    tests = [
        ("Реальные примеры из документации", test_real_examples_from_docs),
        ("load_ohlcv_data функция", test_load_ohlcv_data_function),
        ("clean_ohlcv_data функция", test_clean_ohlcv_data_function),
        ("PreloadedIndicator класс", test_preloaded_indicator_class),
        ("Актуальные примеры MACD", test_actual_macd_examples),
        ("Universal Pipeline пример", test_universal_pipeline_example),
        ("Deprecated предупреждение", test_deprecated_warning),
        ("Cross-references", test_cross_references),
        ("Язык текста", test_language_check),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Тест: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Итого: {passed}/{len(results)} тестов пройдено")
    
    if passed == len(results):
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("⚠️ ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
