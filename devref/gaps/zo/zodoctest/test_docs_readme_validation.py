#!/usr/bin/env python3
"""
Тестовый скрипт для валидации docs/README.md
Проверяет команды и ссылки из docs/README.md
Создан: 2025-10-24
"""

import sys
import os
import subprocess
import webbrowser
from pathlib import Path

def test_file_existence():
    """Проверяем существование файлов"""
    files_to_check = [
        'SETUP_READTHEDOCS.md',
        '.readthedocs.yml',
        'docs/conf.py',
        'docs/Makefile',
        'docs/index.rst'
    ]
    
    results = []
    for file_path in files_to_check:
        exists = os.path.exists(file_path)
        status = "✅ СУЩЕСТВУЕТ" if exists else "❌ НЕ НАЙДЕН"
        print(f"  {file_path}: {status}")
        results.append((file_path, exists))
    
    return all(exists for _, exists in results)

def test_sphinx_commands():
    """Проверяем команды Sphinx"""
    print("\n📋 Тест: Команды Sphinx")
    
    # Проверяем доступность sphinx-build
    try:
        result = subprocess.run(['sphinx-build', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ sphinx-build доступен")
            print(f"   Версия: {result.stdout.strip()}")
            return True
        else:
            print("❌ sphinx-build недоступен")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ Ошибка проверки sphinx-build: {e}")
        return False

def test_pip_install():
    """Проверяем команду pip install"""
    print("\n📋 Тест: pip install команда")
    
    try:
        # Проверяем только синтаксис команды, не выполняем установку
        cmd = ['pip', 'install', '-e', '.[docs]', '--dry-run']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Команда pip install -e .[docs] синтаксически корректна")
            return True
        else:
            print(f"❌ Ошибка в команде pip install: {result.stderr}")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"❌ Ошибка проверки pip install: {e}")
        return False

def test_sphinx_build_structure():
    """Проверяем структуру для сборки Sphinx"""
    print("\n📋 Тест: Структура для сборки")
    
    required_dirs = ['docs', 'docs/_static', 'docs/_templates']
    required_files = ['docs/conf.py', 'docs/index.rst']
    
    all_exist = True
    
    for dir_path in required_dirs:
        exists = os.path.exists(dir_path) and os.path.isdir(dir_path)
        status = "✅ СУЩЕСТВУЕТ" if exists else "❌ НЕ НАЙДЕН"
        print(f"  {dir_path}/: {status}")
        if not exists:
            all_exist = False
    
    for file_path in required_files:
        exists = os.path.exists(file_path)
        status = "✅ СУЩЕСТВУЕТ" if exists else "❌ НЕ НАЙДЕН"
        print(f"  {file_path}: {status}")
        if not exists:
            all_exist = False
    
    return all_exist

def test_language_check():
    """Проверяем язык текста"""
    print("\n📋 Тест: Язык текста")
    
    # Читаем файл и проверяем язык
    try:
        with open('docs/README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие русских слов
        russian_words = ['инструкции', 'сборка', 'просмотра', 'документации', 'руководство']
        found_russian = sum(1 for word in russian_words if word in content.lower())
        
        # Проверяем наличие английских слов в коде (это нормально)
        code_blocks = content.count('```')
        
        print(f"✅ Найдено русских слов: {found_russian}")
        print(f"✅ Найдено блоков кода: {code_blocks}")
        print("✅ Язык текста: русский (код на английском)")
        
        return found_russian > 0
    except Exception as e:
        print(f"❌ Ошибка проверки языка: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🔍 Валидация docs/README.md")
    print("=" * 50)
    
    tests = [
        ("Существование файлов", test_file_existence),
        ("Команды Sphinx", test_sphinx_commands),
        ("pip install команда", test_pip_install),
        ("Структура для сборки", test_sphinx_build_structure),
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
