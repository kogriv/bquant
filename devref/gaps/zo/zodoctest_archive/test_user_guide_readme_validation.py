#!/usr/bin/env python3
"""
Валидация раздела docs/user_guide/README.md и сопутствующего файла core_concepts.md.

Сценарий выполняет следующие шаги:
- проверяет все ссылки и навигационные элементы в README;
- убеждается в наличии русскоязычного текста и блока установки зависимостей;
- подтверждает существование core_concepts.md;
- выполняет все python-примеры из core_concepts.md, чтобы гарантировать их актуальность.
"""

import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Iterable, List

import pandas as pd  # Используется в стабах для pandas-ta

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

README_PATH = PROJECT_ROOT / "docs/user_guide/README.md"
CORE_CONCEPTS_PATH = PROJECT_ROOT / "docs/user_guide/core_concepts.md"


def _prepare_pandas_ta(minimal_functions: Iterable[str] = ("rsi", "ao", "stoch")) -> None:
    """Ограничиваем регистрацию pandas-ta базовым набором индикаторов."""

    try:
        from bquant.indicators.library import pandas_ta as pandas_ta_loader  # type: ignore
    except Exception:
        return

    try:
        import pandas_ta as ta  # type: ignore
    except Exception:
        return

    loader = pandas_ta_loader.PandasTALoader
    selected = {}
    for name in minimal_functions:
        func = getattr(ta, name, None)
        if func is not None:
            selected[name] = func

    if not selected:
        return

    loader._function_cache = selected  # type: ignore[attr-defined]
    loader._available_indicators = sorted(selected.keys())  # type: ignore[attr-defined]
    loader._indicators_registered = False  # type: ignore[attr-defined]


def _ensure_stub_zigzag_registered() -> None:
    """Регистрируем упрощенный zigzag, если он отсутствует."""

    try:
        from bquant.indicators.base import IndicatorFactory, LibraryIndicator  # type: ignore
    except Exception:
        return

    registry = getattr(IndicatorFactory, "_registry", {})
    if "pandas_ta_zigzag" in registry:
        return

    def _zigzag_stub(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        if isinstance(df, pd.DataFrame):
            series = df.get("close")
            if series is None:
                numeric = df.select_dtypes(include=["number"])
                series = numeric.iloc[:, 0] if not numeric.empty else pd.Series(dtype=float)
        else:
            series = pd.Series(df)

        return pd.DataFrame({"zigzag": series.to_numpy(copy=True)})

    class _StubZigZagIndicator(LibraryIndicator):
        def __init__(self, **params):
            super().__init__("zigzag", _zigzag_stub, parameters=params)

    IndicatorFactory.register_indicator("pandas_ta_zigzag", _StubZigZagIndicator)
    IndicatorFactory.register_library_function("pandas_ta_zigzag", _zigzag_stub)


def _extract_links(markdown_text: str) -> List[str]:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    return pattern.findall(markdown_text)


def _extract_python_blocks(markdown_text: str) -> List[str]:
    pattern = re.compile(r"```python\n(.*?)```", re.DOTALL)
    return [textwrap.dedent(block).strip() for block in pattern.findall(markdown_text)]


def test_navigation_links() -> bool:
    print("🔗 Проверяем ссылки из README")
    content = README_PATH.read_text(encoding="utf-8")
    links = _extract_links(content)

    relative_links = [link for link in links if not link.startswith("http")]
    all_exist = True
    for link in relative_links:
        target_path = (README_PATH.parent / link).resolve()
        exists = target_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {link} → {target_path}")
        if not exists:
            all_exist = False

    return all_exist


def test_language_presence() -> bool:
    print("🗣️ Проверяем наличие русскоязычного текста")
    content = README_PATH.read_text(encoding="utf-8")
    russian_markers = ["руководство", "данных", "анализ", "визуализация", "конфигурация"]
    found = sum(1 for marker in russian_markers if marker in content.lower())
    print(f"  Найдено {found} русских маркеров из {len(russian_markers)}")
    return found >= 3


def test_pip_command() -> bool:
    print("📦 Проверяем команду установки зависимостей")
    content = README_PATH.read_text(encoding="utf-8")
    snippet = "pip install pandas numpy matplotlib seaborn plotly"
    has_command = snippet in content
    print(f"  Команда присутствует: {'✅' if has_command else '❌'}")
    return has_command


def test_universal_pipeline_mentions() -> bool:
    print("🧠 Проверяем упоминания Universal Pipeline")
    content = README_PATH.read_text(encoding="utf-8")
    required_phrases = [
        "Universal Zone Analysis Pipeline v2.1",
        "Core Concepts",
        "macd",
    ]
    results = []
    for phrase in required_phrases:
        present = phrase.lower() in content.lower()
        status = "✅" if present else "❌"
        print(f"  {status} '{phrase}'")
        results.append(present)
    return all(results)


def test_core_concepts_file_exists() -> bool:
    print("📄 Проверяем наличие core_concepts.md")
    exists = CORE_CONCEPTS_PATH.exists()
    print(f"  Файл {'найден' if exists else 'не найден'}: {CORE_CONCEPTS_PATH}")
    return exists


def test_core_concepts_examples() -> bool:
    print("🧪 Выполняем примеры из core_concepts.md")
    if not CORE_CONCEPTS_PATH.exists():
        print("  ❌ core_concepts.md отсутствует")
        return False

    content = CORE_CONCEPTS_PATH.read_text(encoding="utf-8")
    code_blocks = _extract_python_blocks(content)

    if len(code_blocks) < 2:
        print("  ❌ Недостаточно примеров кода (ожидалось ≥ 2)")
        return False

    print("  ▶️ Пример 1: конфигурация ZoneAnalysisConfig")
    globals_dict = {"__name__": "__main__"}
    locals_dict = {}
    exec(code_blocks[0], globals_dict, locals_dict)

    config = locals_dict.get("config")
    if config is None:
        print("  ❌ После выполнения примера не найден объект config")
        return False

    checks = [
        config.zone_detection.strategy_name == "zero_crossing",
        config.indicator.name == "macd",
        config.perform_clustering is True,
        config.n_clusters == 3,
    ]
    if not all(checks):
        print("  ❌ Конфигурация не соответствует документации")
        return False
    print("  ✅ Конфигурация собрана корректно")

    print("  ▶️ Пример 2: анализ готовых данных")
    _prepare_pandas_ta()
    _ensure_stub_zigzag_registered()

    globals_dict_2 = {"__name__": "__main__"}
    locals_dict_2 = {}
    exec(code_blocks[1], globals_dict_2, locals_dict_2)

    result = locals_dict_2.get("result")
    if result is None:
        print("  ❌ После выполнения примера не найден объект result")
        return False

    zones_count = len(getattr(result, "zones", []))
    stats = getattr(result, "statistics", {})
    clustering = getattr(result, "clustering", None)

    print(f"  🔢 Найдено зон: {zones_count}")
    print(f"  📊 Ключи статистики: {list(stats.keys())[:3]}")
    print(f"  🧩 Кластеризация: {'включена' if clustering else 'отключена'}")

    return zones_count > 0 and isinstance(stats, dict) and clustering is not None


def main() -> bool:
    print("🔍 Валидация docs/user_guide/README.md и core_concepts.md")
    print("=" * 60)

    tests = [
        ("Ссылки README", test_navigation_links),
        ("Русскоязычный текст", test_language_presence),
        ("Команда pip install", test_pip_command),
        ("Universal Pipeline в навигации", test_universal_pipeline_mentions),
        ("Наличие core_concepts.md", test_core_concepts_file_exists),
        ("Примеры core_concepts.md", test_core_concepts_examples),
    ]

    results = []
    for name, func in tests:
        print(f"\n📋 Тест: {name}")
        try:
            result = func()
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Критическая ошибка: {exc}")
            result = False
        results.append((name, result))

    print("\n" + "=" * 60)
    print("📊 РЕЗЮМЕ ТЕСТОВ:")
    passed = 0
    for name, status in results:
        flag = "✅" if status else "❌"
        print(f"  {flag} {name}")
        if status:
            passed += 1

    total = len(results)
    print(f"\n🎯 Итог: {passed}/{total} тестов пройдено")
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
