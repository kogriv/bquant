#!/usr/bin/env python3
"""Валидация документации docs/api/core/nb.md."""

from __future__ import annotations

import builtins
import contextlib
import io
import os
import sys
import tempfile
import traceback
from datetime import timedelta
from pathlib import Path
from typing import Iterable, List, Optional

project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@contextlib.contextmanager
def _patched_argv(temp_dir: Path, script_name: str, extra_args: Optional[Iterable[str]] = None):
    original_argv = sys.argv[:]
    script_path = temp_dir / script_name
    argv = [str(script_path)]
    if extra_args:
        argv.extend(list(extra_args))
    sys.argv = argv
    try:
        yield script_path
    finally:
        sys.argv = original_argv


@contextlib.contextmanager
def _patched_input(responses: Iterable[str]):
    iterator = iter(responses)
    original_input = builtins.input

    def _fake_input(prompt: str = "") -> str:  # pragma: no cover - используется в доктестах
        try:
            return next(iterator)
        except StopIteration:
            return ""

    builtins.input = _fake_input
    try:
        yield
    finally:
        builtins.input = original_input


def _capture_exit(callable_obj, *args, **kwargs) -> int:
    try:
        callable_obj(*args, **kwargs)
    except SystemExit as exc:  # pragma: no cover - контролируем поведение выхода
        if isinstance(exc.code, int):
            return exc.code
        return 1
    return 0


def test_intro_snippet(temp_dir: Path) -> bool:
    """Воспроизводит первый пример с пошаговыми вызовами."""

    print("📋 Пример: NotebookSimulator — основной сниппет")

    try:
        from bquant.core.nb import NotebookSimulator
    except Exception as exc:
        print(f"  ❌ Импорт NotebookSimulator не удался: {exc}")
        traceback.print_exc()
        return False

    with _patched_argv(temp_dir, "intro_snippet.py"), _patched_input(["", ""]):
        nb = NotebookSimulator("My Analysis Script")
        nb.step("Data Loading")
        nb.wait()
        nb.step("Analysis")
        nb.wait()
        exit_code = _capture_exit(nb.finish)

    log_file = temp_dir / "intro_snippet_log.txt"
    exists = log_file.exists() and log_file.stat().st_size > 0
    print(f"  ✅ Лог-файл создан: {exists}")
    return exit_code == 0 and exists


def test_basic_script(temp_dir: Path) -> bool:
    """Проверяет базовый скрипт из раздела «Базовый скрипт»."""

    print("📋 Пример: Базовый скрипт")

    try:
        from bquant.core.nb import NotebookSimulator
    except Exception as exc:
        print(f"  ❌ Импорт NotebookSimulator не удался: {exc}")
        traceback.print_exc()
        return False

    cleanup_codes: List[int] = []

    try:
        with _patched_argv(temp_dir, "basic_script.py"), _patched_input(["", ""]):
            nb = NotebookSimulator("Example Analysis Script")

            nb.step("Data Loading")
            try:
                nb.success("Data loaded successfully")
            except Exception as exc:  # pragma: no cover - путь для диагностики
                nb.error(f"Failed to load data: {exc}")
                cleanup_codes.append(_capture_exit(nb.cleanup_and_exit, 1))

            nb.wait()

            nb.step("Data Processing")
            nb.success("Processing completed")
            nb.wait()

            exit_code = _capture_exit(nb.finish)
    except Exception as exc:
        print(f"  ❌ Ошибка выполнения базового примера: {exc}")
        traceback.print_exc()
        return False

    log_file = temp_dir / "basic_script_log.txt"
    exists = log_file.exists() and log_file.stat().st_size > 0
    print(f"  ✅ Базовый лог-файл создан: {exists}")
    return exit_code == 0 and exists and not cleanup_codes


def test_advanced_example(temp_dir: Path) -> bool:
    """Выполняет продвинутый пример с обработкой ошибок и анализом данных."""

    print("📋 Пример: Продвинутый анализ")

    try:
        from bquant.core.nb import NotebookSimulator
        from bquant.data.samples import get_sample_data
    except Exception as exc:
        print(f"  ❌ Импорт зависимостей не удался: {exc}")
        traceback.print_exc()
        return False

    data = None

    try:
        with _patched_argv(temp_dir, "advanced_script.py"), _patched_input(["", ""]):
            nb = NotebookSimulator("Advanced Data Analysis")

            def load_data():
                return get_sample_data("tv_xauusd_1h")

            nb.step("Data Loading and Validation")
            with nb.error_handling("Data loading", critical=True):
                data = load_data()
                nb.data_info("Rows loaded", len(data))
                nb.data_info("Memory usage", f"{data.memory_usage().sum() / 1024**2:.2f} MB")

            nb.wait()

            nb.step("Statistical Analysis")
            nb.substep("Descriptive Statistics")
            stats = data.describe()
            nb.success("Descriptive statistics calculated")

            nb.substep("Correlation Analysis")
            correlations = data.corr()
            nb.success("Correlation matrix generated")

            nb.wait()

            nb.step("Results Summary")
            nb.section_header("Analysis Results")
            nb.summary_item("Records processed", len(data), success=True)
            nb.summary_item("Variables analyzed", len(data.columns), success=True)
            missing = data.isnull().sum().sum()
            nb.summary_item("Missing values", missing, success=missing == 0)
            nb.next_steps([
                "Generate detailed report",
                "Create visualizations",
                "Export results to Excel",
            ])

            exit_code = _capture_exit(nb.finish)
    except Exception as exc:
        print(f"  ❌ Ошибка продвинутого примера: {exc}")
        traceback.print_exc()
        return False

    log_file = temp_dir / "advanced_script_log.txt"
    exists = log_file.exists() and log_file.stat().st_size > 0
    stats_ok = data is not None and not stats.empty and not correlations.empty
    print(f"  ✅ Продвинутый лог-файл создан: {exists}")
    return exit_code == 0 and exists and stats_ok


def test_minimal_usage(temp_dir: Path) -> bool:
    """Проверяет раздел «Максимальная простота использования»."""

    print("📋 Пример: Максимальная простота")

    try:
        from bquant.core.nb import NotebookSimulator
    except Exception as exc:
        print(f"  ❌ Импорт NotebookSimulator не удался: {exc}")
        traceback.print_exc()
        return False

    with _patched_argv(temp_dir, "minimal_script.py"), _patched_input(["", ""]):
        nb = NotebookSimulator("My Analysis")
        nb.step("Loading Data")
        nb.wait()
        nb.step("Processing")
        nb.wait()
        exit_code = _capture_exit(nb.finish)

    log_file = temp_dir / "minimal_script_log.txt"
    exists = log_file.exists() and log_file.stat().st_size > 0
    print(f"  ✅ Минимальный лог-файл создан: {exists}")
    return exit_code == 0 and exists


def test_utilities_section() -> bool:
    """Проверяет блоки data_info/summary_item/next_steps и утилиты."""

    print("📋 Проверка: Методы и утилиты")

    try:
        from bquant.core.nb import NotebookSimulator
    except Exception as exc:
        print(f"  ❌ Импорт NotebookSimulator не удался: {exc}")
        traceback.print_exc()
        return False

    nb = NotebookSimulator("Utilities Example", auto_setup=False)
    nb.set_trap_mode(False)

    buffer = io.StringIO()
    original_stdout = sys.stdout
    try:
        sys.stdout = buffer
        nb.data_info("Rows", 1000)
        nb.data_info("Memory usage", "2.5 MB")
        nb.summary_item("Data loaded", "Successfully", success=True)
        nb.summary_item("Tests passed", "5/10", success=False)
        nb.next_steps([
            "Run validation tests",
            "Process missing data",
            "Generate reports",
        ])
    finally:
        sys.stdout = original_stdout

    output = buffer.getvalue()

    checks = [
        "  Rows: 1000" in output,
        "  Memory usage: 2.5 MB" in output,
        "[OK] Data loaded: Successfully" in output,
        "[FAIL] Tests passed: 5/10" in output,
        "[NEXT] Next Steps:" in output,
        "- Run validation tests" in output,
        "- Process missing data" in output,
        "- Generate reports" in output,
    ]

    size_kb = NotebookSimulator.format_file_size(1024)
    size_mb = NotebookSimulator.format_file_size(1048576)
    duration = nb.format_duration(nb.start_time, nb.start_time + timedelta(seconds=75))

    print(f"  ✅ Проверки утилит: {checks.count(True)}/{len(checks)}")
    return all(checks) and size_kb == "1.00 KB" and size_mb == "1.00 MB" and duration == "1m 15s"


def test_cross_references() -> bool:
    """Убеждаемся, что ссылки на связанные разделы существуют."""

    print("📋 Проверка: Cross-references")

    targets = [
        project_root / "docs/api/core/README.md",
        project_root / "docs/api/core/logging.md",
        project_root / "docs/api/core/config.md",
        project_root / "docs/api/core/performance.md",
        project_root / "docs/api/core/utils.md",
    ]

    missing = [str(target) for target in targets if not target.exists()]
    if missing:
        print(f"  ❌ Не найдены файлы: {missing}")
        return False

    print("  ✅ Все связанные разделы доступны")
    return True


def test_language_requirements() -> bool:
    """Проверяет наличие русскоязычного текста и количество блоков кода."""

    print("📋 Проверка: Язык и структура")

    doc_path = project_root / "docs/api/core/nb.md"
    try:
        content = doc_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  ❌ Не удалось прочитать документ: {exc}")
        traceback.print_exc()
        return False

    lower = content.lower()
    markers = ["ноутбу", "логирован", "шаг", "подшаг", "резюме"]
    marker_hits = sum(1 for marker in markers if marker in lower)
    code_blocks = content.count("```python")

    print(f"  ✅ Найдено маркеров: {marker_hits}/{len(markers)}")
    print(f"  ✅ Количество python-блоков: {code_blocks}")

    return marker_hits == len(markers) and code_blocks >= 10


def main() -> bool:
    print("🔍 Валидация docs/api/core/nb.md")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_dir = Path(tmp_dir)
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)

            tests = [
                ("Основной сниппет", lambda: test_intro_snippet(temp_dir)),
                ("Базовый скрипт", lambda: test_basic_script(temp_dir)),
                ("Продвинутый пример", lambda: test_advanced_example(temp_dir)),
                ("Максимальная простота", lambda: test_minimal_usage(temp_dir)),
                ("Методы и утилиты", test_utilities_section),
                ("Cross-references", test_cross_references),
                ("Язык", test_language_requirements),
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
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
