#!/usr/bin/env python3
"""
Тестовый скрипт для валидации docs/index.rst
Проверяет все примеры кода и ссылки из docs/index.rst
Создан: 2025-10-24
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Тестируем импорты из примеров"""
    print("📋 Тест: Импорты")
    
    imports_to_test = [
        'bquant',
        'bquant.data.samples.get_sample_data',
        'bquant.analysis.zones.analyze_zones',
        'bquant.indicators.macd.MACDZoneAnalyzer',
    ]
    
    results = []
    for import_path in imports_to_test:
        try:
            if '.' in import_path:
                module_path, function_name = import_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[function_name])
                if hasattr(module, function_name):
                    print(f"  ✅ {import_path}")
                    results.append(True)
                else:
                    print(f"  ❌ {import_path} - не найден")
                    results.append(False)
            else:
                __import__(import_path)
                print(f"  ✅ {import_path}")
                results.append(True)
        except ImportError as e:
            print(f"  ❌ {import_path}: {e}")
            results.append(False)
    
    return all(results)

def test_sample_data():
    """Тестируем загрузку sample данных"""
    print("\n📋 Тест: Sample данные")
    
    try:
        from bquant.data.samples import get_sample_data
        data = get_sample_data('tv_xauusd_1h')
        print(f"  ✅ Sample данные загружены: {data.shape}")
        return True
    except Exception as e:
        print(f"  ❌ Ошибка загрузки sample данных: {e}")
        return False

def test_universal_pipeline():
    """Тестируем Universal Pipeline"""
    print("\n📋 Тест: Universal Pipeline")
    
    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data
        
        # Загружаем sample данные
        data = get_sample_data('tv_xauusd_1h')
        
        # Тестируем Universal Pipeline
        result = (
            analyze_zones(data)
            .with_indicator('pandas_ta', 'rsi', length=14)
            .detect_zones('threshold', indicator_col='rsi',
                         upper_threshold=70, lower_threshold=30)
            .analyze(clustering=True)
            .build()
        )
        
        print("  ✅ Universal Pipeline выполнен успешно")
        print(f"     Найдено зон: {len(result.zones)}")
        print(f"     Статистика: {result.statistics}")
        return True
    except Exception as e:
        print(f"  ❌ Ошибка Universal Pipeline: {e}")
        return False

def test_legacy_macd():
    """Тестируем Legacy MACD"""
    print("\n📋 Тест: Legacy MACD")
    
    try:
        from bquant.indicators.macd import MACDZoneAnalyzer
        from bquant.data.samples import get_sample_data
        
        # Загружаем sample данные
        data = get_sample_data('tv_xauusd_1h')
        
        # Тестируем Legacy MACD
        analyzer = MACDZoneAnalyzer()
        result = analyzer.analyze_complete(data)
        
        print("  ✅ Legacy MACD выполнен успешно (deprecated)")
        print(f"     Найдено зон: {len(result.zones)}")
        return True
    except Exception as e:
        print(f"  ❌ Ошибка Legacy MACD: {e}")
        return False

def test_cross_references():
    """Проверяем cross-references"""
    print("\n📋 Тест: Cross-references")
    
    references_to_check = [
        'docs/user_guide/quick_start.md',
        'docs/api/README.md',
        'docs/tutorials/README.md',
        'docs/examples/README.md',
        'docs/developer_guide/README.md',
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
        with open('docs/index.rst', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие русских слов
        russian_words = ['документация', 'руководство', 'примеры', 'быстрый', 'старт']
        found_russian = sum(1 for word in russian_words if word in content.lower())
        
        # Проверяем наличие английских слов в коде (это нормально)
        code_blocks = content.count('.. code-block::')
        
        print(f"  ✅ Найдено русских слов: {found_russian}")
        print(f"  ✅ Найдено блоков кода: {code_blocks}")
        print("  ✅ Язык текста: русский (код на английском)")
        
        return found_russian > 0
    except Exception as e:
        print(f"  ❌ Ошибка проверки языка: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🔍 Валидация docs/index.rst")
    print("=" * 50)
    
    tests = [
        ("Импорты", test_imports),
        ("Sample данные", test_sample_data),
        ("Universal Pipeline", test_universal_pipeline),
        ("Legacy MACD", test_legacy_macd),
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
    
    print("\n" + "=" * 50)
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
