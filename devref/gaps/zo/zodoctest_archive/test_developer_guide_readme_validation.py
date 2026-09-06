"""Проверка документа docs/developer_guide/README.md."""

import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Tuple

import pandas as pd

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("BQUANT_LOG_LEVEL", "ERROR")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEVELOPER_GUIDE = PROJECT_ROOT / "docs/developer_guide/README.md"


def _extract_links(markdown_text: str) -> List[str]:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    return pattern.findall(markdown_text)


def _extract_code_blocks(markdown_text: str, language: str) -> List[str]:
    pattern = re.compile(rf"```{language}\n(.*?)```", re.DOTALL)
    return [textwrap.dedent(block).strip() for block in pattern.findall(markdown_text)]


def _suppress_external_indicators() -> None:
    """Отключает регистрацию внешних библиотек индикаторов."""

    try:
        from bquant.indicators.library import manager as library_manager  # type: ignore
    except Exception:  # noqa: BLE001
        return

    def _noop_load_all(cls):  # type: ignore[no-untyped-def]
        print("    ⚠️ Пропускаем регистрацию внешних индикаторов для проверки документации")
        return {"pandas_ta": 0, "talib": 0}

    library_manager.LibraryManager.load_all_libraries = classmethod(_noop_load_all)  # type: ignore[assignment]


def test_relative_links() -> bool:
    print("🔗 Проверяем относительные ссылки developer_guide/README.md")
    content = DEVELOPER_GUIDE.read_text(encoding="utf-8")
    links = _extract_links(content)

    relative = [
        link
        for link in links
        if not link.startswith(("http://", "https://", "mailto:"))
    ]

    all_exist = True
    for link in relative:
        target = link.split("#", 1)[0]
        if not target:
            continue
        target_path = (DEVELOPER_GUIDE.parent / target).resolve()
        exists = target_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {link} → {target_path}")
        if not exists:
            all_exist = False

    return all_exist


def test_bash_blocks() -> bool:
    print("🐚 Проверяем bash-команды")
    content = DEVELOPER_GUIDE.read_text(encoding="utf-8")
    bash_blocks = _extract_code_blocks(content, "bash")

    if not bash_blocks:
        print("  ❌ Bash-блоки не найдены")
        return False

    commands = [line.strip() for block in bash_blocks for line in block.splitlines() if line.strip()]
    markers: Iterable[str] = (
        "git clone https://github.com/bquant-team/bquant.git",
        "pip install -e .[dev]",
        "pytest",
        "black bquant/",
    )

    ok = True
    for marker in markers:
        if marker not in commands:
            print(f"  ❌ Не найдена команда: {marker}")
            ok = False
        else:
            print(f"  ✅ Обнаружена команда: {marker}")

    return ok


def _run_python_block(block: str, index: int) -> Tuple[bool, str]:
    namespace: Dict[str, object] = {"__name__": "__main__"}
    try:
        exec(compile(block, f"developer_guide_block_{index}", "exec"), namespace)
    except Exception as exc:  # noqa: BLE001
        return False, f"Ошибка выполнения блока {index}: {exc}"

    return True, namespace


def _post_checks() -> Dict[int, Callable[[Dict[str, object]], bool]]:
    from bquant.analysis.zones.models import ZoneAnalysisResult, ZoneInfo

    def check_detection(ns: Dict[str, object]) -> bool:
        zones = ns.get("custom_zones")
        if not isinstance(zones, list) or not zones:
            print("    ❌ custom_zones отсутствует или пуст")
            return False
        first = zones[0]
        ok = isinstance(first, ZoneInfo)
        print(f"    ✅ Найдена зона типа {type(first).__name__}")
        return ok

    def check_analysis(ns: Dict[str, object]) -> bool:
        result = ns.get("analysis_result")
        if not isinstance(result, ZoneAnalysisResult):
            print("    ❌ analysis_result не ZoneAnalysisResult")
            return False
        stats = getattr(result, "statistics", {})
        print(f"    ✅ Статистика анализа: {stats}")
        return bool(stats.get("zones_count") == 1)

    def check_indicator(ns: Dict[str, object]) -> bool:
        spread_result = ns.get("spread_result")
        if spread_result is None:
            print("    ❌ spread_result не найден")
            return False
        frame = getattr(spread_result, "data", None)
        if frame is None or "spread" not in frame.columns:
            print("    ❌ В результате отсутствует колонка spread")
            return False
        print(f"    ✅ Последнее значение spread: {frame['spread'].iloc[-1]}")
        return True

    def check_typed(ns: Dict[str, object]) -> bool:
        typed = ns.get("typed_result")
        return isinstance(typed, ZoneAnalysisResult)

    def check_error_handling(ns: Dict[str, object]) -> bool:
        func = ns.get("analyze_with_graceful_degradation")
        if not callable(func):
            print("    ❌ Функция деградации не найдена")
            return False
        fallback = func(pd.DataFrame({"close": [1.0, 2.0]}), {})
        print(f"    ✅ Результат деградации: {fallback}")
        return isinstance(fallback, dict) and fallback.get("status") == "fallback"

    def check_performance(ns: Dict[str, object]) -> bool:
        cached = ns.get("cached_indicator")
        expensive = ns.get("expensive_calculation")
        analyzer_cls = ns.get("LazyZoneAnalyzer")
        if not callable(cached) or not callable(expensive) or analyzer_cls is None:
            print("    ❌ Не найдены объекты производительности")
            return False
        analyzer = analyzer_cls()
        _ = analyzer.analyzer
        cached_val = cached(5)
        expensive.cache_clear()  # type: ignore[attr-defined]
        val = expensive(10)
        print(f"    ✅ cached_indicator(5)={cached_val}, expensive_calculation(10)={val}")
        return cached_val == 10 and val == 20

    def run_unit_test(ns: Dict[str, object]) -> bool:
        func = ns.get("test_zone_result_shape")
        if not callable(func):
            print("    ❌ Функция unit-теста не найдена")
            return False
        func()
        print("    ✅ Unit-тест выполнен")
        return True

    def run_integration_test(ns: Dict[str, object]) -> bool:
        func = ns.get("test_full_pipeline")
        if not callable(func):
            print("    ❌ Интеграционный тест не найден")
            return False
        func()
        print("    ✅ Интеграционный тест выполнен")
        return True

    def run_performance_test(ns: Dict[str, object]) -> bool:
        func = ns.get("test_performance_budget")
        if not callable(func):
            print("    ❌ Тест производительности не найден")
            return False
        func()
        print("    ✅ Тест производительности выполнен")
        return True

    def check_profiling(ns: Dict[str, object]) -> bool:
        slow = ns.get("slow_function")
        return callable(slow)

    def check_logging(ns: Dict[str, object]) -> bool:
        return "logger" in ns

    def check_error_block(ns: Dict[str, object]) -> bool:
        return "dummy_analyzer" in ns

    return {
        0: check_detection,
        1: check_analysis,
        2: check_indicator,
        3: check_typed,
        5: check_error_handling,
        6: check_performance,
        7: run_unit_test,
        8: run_integration_test,
        9: run_performance_test,
        10: check_profiling,
        11: check_logging,
        12: check_error_block,
    }


def test_python_blocks() -> bool:
    print("🐍 Выполняем python-блоки")
    content = DEVELOPER_GUIDE.read_text(encoding="utf-8")
    python_blocks = _extract_code_blocks(content, "python")

    if not python_blocks:
        print("  ❌ Python-блоки не найдены")
        return False

    post = _post_checks()
    _suppress_external_indicators()
    success = True

    for idx, block in enumerate(python_blocks):
        print(f"  ▶️ Блок {idx + 1}/{len(python_blocks)}")
        ok, namespace_or_error = _run_python_block(block, idx)
        if not ok:
            print(f"    ❌ {namespace_or_error}")
            success = False
            continue

        namespace = namespace_or_error  # type: ignore[assignment]
        check = post.get(idx)
        if check is not None:
            try:
                if not check(namespace):
                    print(f"    ❌ Дополнительная проверка для блока {idx} не пройдена")
                    success = False
                else:
                    print(f"    ✅ Дополнительная проверка для блока {idx} пройдена")
            except AssertionError as exc:
                print(f"    ❌ AssertionError: {exc}")
                success = False

    return success


def test_language_markers() -> bool:
    print("🗣️ Проверяем русскоязычные маркеры")
    content = DEVELOPER_GUIDE.read_text(encoding="utf-8").lower()
    markers: Iterable[str] = (
        "архитектура",
        "тест",
        "производительность",
        "отладка",
        "упаковка",
    )
    found = sum(1 for marker in markers if marker in content)
    print(f"  Найдено {found} маркеров")
    return found >= 4


def main() -> bool:
    print("🔍 Валидация docs/developer_guide/README.md")
    print("=" * 50)

    tests: Iterable[Tuple[str, Callable[[], bool]]] = (
        ("Относительные ссылки", test_relative_links),
        ("Bash-команды", test_bash_blocks),
        ("Python-блоки", test_python_blocks),
        ("Русскоязычное содержание", test_language_markers),
    )

    passed = 0
    total = 0
    for name, func in tests:
        total += 1
        print(f"\n📋 Тест: {name}")
        try:
            if func():
                print("  ✅ Тест пройден")
                passed += 1
            else:
                print("  ❌ Тест провален")
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Критическая ошибка: {exc}")

    print("\n" + "=" * 50)
    print(f"📊 Результат: {passed}/{total} тестов пройдено")
    success = passed == total
    print("🎉 Все проверки успешны!" if success else "⚠️ Обнаружены проблемы!")
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
