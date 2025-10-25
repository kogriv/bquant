#!/usr/bin/env python3
"""
Тест валидации docs/api/analysis/base.md
Проверяет базовые классы, фабрики и пример из документации
"""

import sys
import traceback
from pathlib import Path
from typing import Dict

import pandas as pd

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports() -> bool:
    """Проверяем, что ключевые объекты доступны из модуля."""

    print("📋 Тест: Импорты")

    targets = [
        ("bquant.analysis", "AnalysisResult"),
        ("bquant.analysis", "BaseAnalyzer"),
        ("bquant.analysis", "get_available_analyzers"),
        ("bquant.analysis", "create_analyzer"),
        ("bquant.analysis", "SUPPORTED_ANALYSIS_TYPES"),
    ]

    success = 0
    for module_name, attr_name in targets:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            getattr(module, attr_name)
            print(f"  ✅ {module_name}.{attr_name}")
            success += 1
        except Exception as exc:  # pragma: no cover - диагностический вывод
            print(f"  ❌ {module_name}.{attr_name}: {exc}")
            traceback.print_exc()

    print(f"  Результат: {success}/{len(targets)} импортов успешно")
    return success == len(targets)


def test_example_from_docs() -> bool:
    """Воспроизводим кодовый пример из документации."""

    print("\n📋 Тест: Пример MyAnalyzer")

    try:
        from bquant.analysis import BaseAnalyzer, AnalysisResult
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Не удалось импортировать классы: {exc}")
        traceback.print_exc()
        return False

    class MyAnalyzer(BaseAnalyzer):
        def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
            if not self.validate_data(data):
                raise ValueError("Invalid data")
            return AnalysisResult(
                "my_analysis",
                results={"rows": len(data)},
                data_size=len(data),
            )

    try:
        analyzer = MyAnalyzer("MyAnalyzer")
        result = analyzer.analyze(pd.DataFrame({"close": list(range(1, 11))}))
        result_dict: Dict[str, object] = result.to_dict()
        print(f"  ✅ Результат анализа: {result_dict}")
        return result_dict.get("results", {}).get("rows") == 10
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка выполнения примера: {exc}")
        traceback.print_exc()
        return False


def test_factory_behaviour() -> bool:
    """Проверяем работу фабричной функции и списка анализаторов."""

    print("\n📋 Тест: Фабрика анализаторов")

    try:
        import types
        from unittest import mock

        import bquant.analysis as analysis_module
        from bquant.analysis import create_analyzer, BaseAnalyzer
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Импорты для фабрики: {exc}")
        traceback.print_exc()
        return False

    try:
        fake_zones = types.ModuleType("bquant.analysis.zones")
        fake_zones.get_zone_analyzers = lambda: {"zones": "Анализ зон"}

        with mock.patch.dict(sys.modules, {"bquant.analysis.zones": fake_zones}):
            registry = analysis_module.get_available_analyzers()

        print(f"  ✅ Доступные анализаторы: {sorted(registry.keys())[:6]}")

        analyzer = create_analyzer("statistical")
        print(f"  ✅ Фабрика вернула: {analyzer.__class__.__name__}")
        return isinstance(analyzer, BaseAnalyzer) and "statistical" in registry
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка фабрики: {exc}")
        traceback.print_exc()
        return False


def test_cross_references() -> bool:
    """Убеждаемся, что ссылки из раздела существуют."""

    print("\n📋 Тест: Cross-references")

    references = [
        Path("docs/api/analysis/statistical.md"),
        Path("docs/api/analysis/zones.md"),
    ]

    success = 0
    for ref in references:
        if ref.exists():
            print(f"  ✅ {ref}")
            success += 1
        else:
            print(f"  ❌ {ref} — отсутствует")

    return success == len(references)


def test_language() -> bool:
    """Проверяем, что текст раздела остается на русском языке."""

    print("\n📋 Тест: Язык документа")

    try:
        content = Path("docs/api/analysis/base.md").read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Не удалось прочитать файл: {exc}")
        traceback.print_exc()
        return False

    russian_markers = ["базовые", "анализатора", "фабрика", "поддерживаемых"]
    found = sum(1 for marker in russian_markers if marker in content.lower())
    code_blocks = content.count("```python")

    print(f"  ✅ Русскоязычных маркеров: {found}")
    print(f"  ✅ Python-блоков: {code_blocks}")
    return found >= len(russian_markers) - 1 and code_blocks >= 1


def main() -> bool:
    print("🔍 Валидация docs/api/analysis/base.md")
    print("=" * 60)

    tests = [
        ("Импорты", test_imports),
        ("Пример MyAnalyzer", test_example_from_docs),
        ("Фабрика анализаторов", test_factory_behaviour),
        ("Cross-references", test_cross_references),
        ("Язык документа", test_language),
    ]

    results = []
    for name, func in tests:
        print(f"\n➡️ {name}")
        ok = func()
        results.append(ok)
        print(f"✔️ {name}: {'успех' if ok else 'ошибка'}")

    total = sum(results)
    print("=" * 60)
    print(f"Итого: {total}/{len(tests)} тестов успешно")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
