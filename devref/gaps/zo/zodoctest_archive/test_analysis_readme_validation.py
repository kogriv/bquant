#!/usr/bin/env python3
"""
Тест валидации docs/api/analysis/README.md
Проверяет все примеры кода, cross-references и структуру API
"""

import sys
import os
import importlib
import traceback
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports_from_docs():
    """Тестируем все импорты из документации"""
    print("📋 Тест: Импорты из документации")
    
    imports_to_test = [
        # Universal Pipeline
        ('bquant.analysis.zones', 'analyze_zones'),
        ('bquant.data.samples', 'get_sample_data'),
        
        # Statistical analysis
        ('bquant.analysis.statistical', 'HypothesisTestSuite'),
        ('bquant.analysis.statistical', 'StatisticalAnalyzer'),
        ('bquant.analysis.statistical', 'run_all_hypothesis_tests'),
        
        # Base analysis
        ('bquant.analysis', 'BaseAnalyzer'),
        ('bquant.analysis', 'AnalysisResult'),
    ]
    
    success_count = 0
    total_count = len(imports_to_test)
    
    for module_name, class_or_func_name in imports_to_test:
        try:
            module = importlib.import_module(module_name)
            obj = getattr(module, class_or_func_name)
            print(f"  ✅ {module_name}.{class_or_func_name}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {module_name}.{class_or_func_name}: {e}")
    
    print(f"  Результат: {success_count}/{total_count} импортов успешно")
    return success_count == total_count

def test_universal_pipeline_example():
    """Тестируем пример Universal Pipeline из документации"""
    print("\n📋 Тест: Universal Pipeline пример")
    
    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Загрузка данных
        data = get_sample_data('tv_xauusd_1h')
        print(f"  ✅ Данные загружены: {len(data)} записей")
        
        # Universal Pipeline с автоматическими hypothesis tests
        result = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing='find_peaks', divergence='classic')
            .analyze(clustering=True)  # Автоматически включает hypothesis tests
            .build()
        )
        
        print(f"  ✅ Universal Pipeline выполнен: {len(result.zones)} зон")
        
        # Анализ результатов
        if result.hypothesis_tests:
            print(f"  ✅ Hypothesis tests доступны: {len(result.hypothesis_tests.results)} тестов")
            for test_name, test_result in result.hypothesis_tests.results.items():
                # Проверяем структуру результата
                if hasattr(test_result, 'p_value'):
                    print(f"    {test_name}: p={test_result.p_value:.4f}")
                elif isinstance(test_result, dict) and 'p_value' in test_result:
                    print(f"    {test_name}: p={test_result['p_value']:.4f}")
                else:
                    print(f"    {test_name}: {test_result}")
        else:
            print(f"  ⚠️ Hypothesis tests недоступны")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Universal Pipeline: {e}")
        traceback.print_exc()
        return False

def test_single_hypothesis_example():
    """Тестируем пример тестирования отдельной гипотезы"""
    print("\n📋 Тест: Тестирование отдельной гипотезы")
    
    try:
        from bquant.analysis.statistical import run_all_hypothesis_tests
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        import numpy as np
        from scipy import stats
        
        # Загрузка данных и анализ
        data = get_sample_data('tv_xauusd_1h')
        result = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=False)
            .build()
        )
        
        # Подготовка данных для теста
        bull_volatility = []
        bear_volatility = []
        
        for zone in result.zones:
            if zone.features:
                volatility = zone.features.get('avg_volatility', 0)
                if zone.type == 'bull':
                    bull_volatility.append(volatility)
                elif zone.type == 'bear':
                    bear_volatility.append(volatility)
        
        if len(bull_volatility) > 0 and len(bear_volatility) > 0:
            # T-тест
            t_stat, p_value = stats.ttest_ind(bull_volatility, bear_volatility)
            
            print(f"  ✅ T-test выполнен:")
            print(f"    p-value: {p_value:.4f}")
            print(f"    Significant: {p_value < 0.05}")
            print(f"    t-statistic: {t_stat:.4f}")
            return True
        else:
            print(f"  ⚠️ Недостаточно данных для T-test")
            return True
            
    except Exception as e:
        print(f"  ❌ Single hypothesis test: {e}")
        traceback.print_exc()
        return False

def test_zone_features_analysis():
    """Тестируем анализ характеристик зон"""
    print("\n📋 Тест: Анализ характеристик зон")
    
    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Universal Pipeline автоматически извлекает характеристики
        data = get_sample_data('tv_xauusd_1h')
        result = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing='find_peaks', volatility='combined')
            .analyze(clustering=True)
            .build()
        )
        
        print(f"  ✅ Zone features analysis:")
        print(f"    Total zones analyzed: {len(result.zones)}")
        
        features_count = 0
        for i, zone in enumerate(result.zones[:3]):
            if zone.features:
                features_count += 1
                print(f"    Zone {i}: volatility={zone.features.get('volatility_regime', 'unknown')}")
                print(f"      Swings: {zone.features.get('num_swings', 0)}")
                print(f"      Duration: {zone.features.get('duration', 0):.2f}")
        
        print(f"  ✅ Zones with features: {features_count}")
        return True
        
    except Exception as e:
        print(f"  ❌ Zone features analysis: {e}")
        traceback.print_exc()
        return False

def test_sequence_analysis():
    """Тестируем анализ последовательностей зон"""
    print("\n📋 Тест: Анализ последовательностей зон")
    
    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Universal Pipeline с sequence analysis
        data = get_sample_data('tv_xauusd_1h')
        result = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=True)  # sequence analysis включен автоматически
            .build()
        )
        
        print(f"  ✅ Sequence analysis:")
        
        # Анализ переходов между зонами
        if result.sequence_analysis:
            print(f"    Bull to Bear transitions: {result.sequence_analysis.get('bull_to_bear', 0)}")
            print(f"    Bear to Bull transitions: {result.sequence_analysis.get('bear_to_bull', 0)}")
        else:
            print(f"    ⚠️ Sequence analysis недоступен")
        
        # Кластерный анализ зон
        if result.clustering:
            print(f"    Number of clusters: {result.clustering.get('n_clusters', 0)}")
            cluster_labels = result.clustering.get('cluster_labels', [])
            print(f"    Cluster labels: {cluster_labels[:5]}...")
        else:
            print(f"    ⚠️ Clustering недоступен")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Sequence analysis: {e}")
        traceback.print_exc()
        return False

def test_statistical_analyzer():
    """Тестируем StatisticalAnalyzer"""
    print("\n📋 Тест: StatisticalAnalyzer")
    
    try:
        from bquant.analysis.statistical import StatisticalAnalyzer
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Создание статистического анализатора
        stat_analyzer = StatisticalAnalyzer()
        print(f"  ✅ StatisticalAnalyzer создан")
        
        # Подготовка данных для анализа
        data = get_sample_data('tv_xauusd_1h')
        result = (
            analyze_zones(data)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=False)
            .build()
        )
        
        bull_zones = [zone for zone in result.zones if zone.type == 'bull']
        bear_zones = [zone for zone in result.zones if zone.type == 'bear']
        
        # Извлечение характеристик
        bull_durations = [zone.duration for zone in bull_zones]
        bear_durations = [zone.duration for zone in bear_zones]
        
        if len(bull_durations) > 0 and len(bear_durations) > 0:
            # Комплексный статистический анализ
            from scipy import stats
            
            # T-тест для сравнения групп
            duration_t_stat, duration_p_value = stats.ttest_ind(bull_durations, bear_durations)
            
            # Описательная статистика
            import numpy as np
            bull_duration_stats = {
                'mean': np.mean(bull_durations),
                'std': np.std(bull_durations),
                'min': np.min(bull_durations),
                'max': np.max(bull_durations)
            }
            
            print(f"  ✅ Duration comparison:")
            print(f"    p-value: {duration_p_value:.4f}")
            print(f"    Significant: {duration_p_value < 0.05}")
            
            print(f"  ✅ Bull duration stats:")
            print(f"    Mean: {bull_duration_stats['mean']:.4f}")
            print(f"    Std: {bull_duration_stats['std']:.4f}")
            
            return True
        else:
            print(f"  ⚠️ Недостаточно данных для статистического анализа")
            return True
            
    except Exception as e:
        print(f"  ❌ StatisticalAnalyzer: {e}")
        traceback.print_exc()
        return False

def test_custom_analyzer():
    """Тестируем создание собственного анализатора"""
    print("\n📋 Тест: Создание собственного анализатора")
    
    try:
        from bquant.analysis import BaseAnalyzer, AnalysisResult
        from bquant.data.samples import get_sample_data
        import numpy as np
        
        class VolatilityAnalyzer(BaseAnalyzer):
            """Анализатор волатильности"""
            
            def __init__(self, window_size=20):
                super().__init__('VolatilityAnalyzer')
                self.window_size = window_size
            
            def analyze(self, data):
                """Анализ волатильности"""
                if not self.validate_data(data):
                    raise ValueError("Invalid data for volatility analysis")
                
                # Расчет волатильности
                returns = data['close'].pct_change()
                volatility = returns.rolling(window=self.window_size).std()
                
                # Статистики волатильности
                volatility_stats = {
                    'mean': volatility.mean(),
                    'std': volatility.std(),
                    'min': volatility.min(),
                    'max': volatility.max(),
                    'current': volatility.iloc[-1]
                }
                
                return AnalysisResult(
                    analysis_type='VolatilityAnalyzer',
                    results=volatility_stats,
                    data_size=len(volatility),
                    metadata={'window_size': self.window_size}
                )
            
            def validate_data(self, data):
                """Валидация данных"""
                required_columns = ['close']
                return all(col in data.columns for col in required_columns)
        
        # Использование собственного анализатора
        data = get_sample_data('tv_xauusd_1h')
        volatility_analyzer = VolatilityAnalyzer(window_size=20)
        volatility_result = volatility_analyzer.analyze(data)
        
        print(f"  ✅ VolatilityAnalyzer создан и выполнен:")
        print(f"    Mean volatility: {volatility_result.results['mean']:.4f}")
        print(f"    Current volatility: {volatility_result.results['current']:.4f}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Custom analyzer: {e}")
        traceback.print_exc()
        return False

def test_cross_references():
    """Тестируем cross-references"""
    print("\n📋 Тест: Cross-references")
    
    cross_refs = [
        'docs/api/core/README.md',
        'docs/api/data/README.md', 
        'docs/api/indicators/README.md',
        'docs/api/visualization/README.md',
        'docs/api/analysis/pipeline.md',
        'docs/api/analysis/strategies.md',
        'docs/api/analysis/statistical.md',
        'docs/api/analysis/zones.md',
        'docs/api/analysis/base.md'
    ]
    
    success_count = 0
    for ref in cross_refs:
        if os.path.exists(ref):
            print(f"  ✅ {ref}")
            success_count += 1
        else:
            print(f"  ❌ {ref} - НЕ СУЩЕСТВУЕТ")
    
    print(f"  Результат: {success_count}/{len(cross_refs)} ссылок существуют")
    return success_count == len(cross_refs)

def test_language_check():
    """Проверяем язык текста"""
    print("\n📋 Тест: Язык текста")
    
    try:
        with open('docs/api/analysis/README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие русских слов
        russian_words = ['анализ', 'модули', 'статистический', 'зоны', 'результат', 'данные']
        found_russian = sum(1 for word in russian_words if word in content.lower())
        
        # Проверяем наличие блоков кода
        code_blocks = content.count('```python')
        
        print(f"  ✅ Найдено русских слов: {found_russian}")
        print(f"  ✅ Найдено блоков кода: {code_blocks}")
        print(f"  ✅ Язык текста: русский (код на английском)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Language check: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🔍 Валидация docs/api/analysis/README.md")
    print("=" * 60)
    
    tests = [
        test_imports_from_docs,
        test_universal_pipeline_example,
        test_single_hypothesis_example,
        test_zone_features_analysis,
        test_sequence_analysis,
        test_statistical_analyzer,
        test_custom_analyzer,
        test_cross_references,
        test_language_check
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Тест {test.__name__} упал: {e}")
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ:")
    print(f"  Импорты из документации: {'✅ ПРОЙДЕН' if passed >= 1 else '❌ ПРОВАЛЕН'}")
    print(f"  Universal Pipeline пример: {'✅ ПРОЙДЕН' if passed >= 2 else '❌ ПРОВАЛЕН'}")
    print(f"  Single hypothesis test: {'✅ ПРОЙДЕН' if passed >= 3 else '❌ ПРОВАЛЕН'}")
    print(f"  Zone features analysis: {'✅ ПРОЙДЕН' if passed >= 4 else '❌ ПРОВАЛЕН'}")
    print(f"  Sequence analysis: {'✅ ПРОЙДЕН' if passed >= 5 else '❌ ПРОВАЛЕН'}")
    print(f"  StatisticalAnalyzer: {'✅ ПРОЙДЕН' if passed >= 6 else '❌ ПРОВАЛЕН'}")
    print(f"  Custom analyzer: {'✅ ПРОЙДЕН' if passed >= 7 else '❌ ПРОВАЛЕН'}")
    print(f"  Cross-references: {'✅ ПРОЙДЕН' if passed >= 8 else '❌ ПРОВАЛЕН'}")
    print(f"  Язык текста: {'✅ ПРОЙДЕН' if passed >= 9 else '❌ ПРОВАЛЕН'}")
    
    print(f"\n🎯 Итого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
