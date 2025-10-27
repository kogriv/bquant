"""Валидатор для examples/05_strategies_demo.py."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "examples" / "05_strategies_demo.py"


@lru_cache(maxsize=1)
def _run_example() -> Tuple[int, str, str]:
    """Запускает пример стратегий и кэширует вывод."""

    env = os.environ.copy()
    env.setdefault("NUMBA_DISABLE_JIT", "1")

    with tempfile.TemporaryDirectory() as tmpdir:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            check=False,
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env,
        )

    return proc.returncode, proc.stdout, proc.stderr


def _combined_output() -> str:
    code, stdout, stderr = _run_example()
    return stdout + "\n" + stderr + f"\n[exit={code}]"


def test_script_execution() -> bool:
    print("📋 Тест: запуск examples/05_strategies_demo.py")

    code, stdout, stderr = _run_example()

    if code != 0:
        print(f"  ❌ Код завершения {code}")
        if stderr:
            print("  ℹ️ STDERR:")
            print(stderr)
        return False

    if "Traceback" in stdout or "Traceback" in stderr:
        print("  ❌ Найден traceback в выводе")
        return False

    print("  ✅ Скрипт завершился без ошибок")
    return True


def test_indicator_sections_present() -> bool:
    print("📋 Тест: наличие секций индикаторов")
    lines = _combined_output().splitlines()

    macd_count = None
    rsi_found = False

    for idx, line in enumerate(lines):
        if "=== Testing MACD" in line:
            window = lines[idx + 1 : idx + 5]
            for candidate in window:
                tokens = candidate.strip().split()
                if tokens[:1] == ["Detected"] and any(token.isdigit() for token in tokens):
                    macd_count = next(int(token) for token in tokens if token.isdigit())
                    break
        if "=== Testing RSI" in line:
            rsi_found = True

    if not macd_count or macd_count == 0:
        print("  ❌ MACD секция не найдена или не обнаружены зоны")
        return False

    if not rsi_found:
        print("  ❌ RSI секция отсутствует")
        return False

    print("  ✅ Обе секции присутствуют")
    return True


def test_strategy_table_metrics() -> bool:
    print("📋 Тест: таблица сравнения стратегий")
    lines = _combined_output().splitlines()

    header_index = next((i for i, line in enumerate(lines) if "Strategy        Swings" in line), None)
    if header_index is None:
        print("  ❌ Заголовок таблицы не найден")
        return False

    rows = []
    for line in lines[header_index + 2 : header_index + 6]:
        if not line.strip():
            continue
        match = re.match(r"\s*(zigzag|find_peaks|pivot_points)\s+(\d+)", line)
        if match:
            rows.append((match.group(1), int(match.group(2))))

    if len(rows) != 3:
        print("  ❌ Не удалось извлечь все строки таблицы")
        return False

    if any(value == 0 for _, value in rows):
        print(f"  ❌ Ожидались ненулевые показатели, получено: {rows}")
        return False

    print(f"  ✅ Таблица стратегий обнаружена, значения: {rows}")
    return True


def test_average_swings_summary() -> bool:
    print("📋 Тест: среднее количество свингов по зонам")
    lines = _combined_output().splitlines()
    try:
        idx = next(i for i, line in enumerate(lines) if "Average swings per zone:" in line)
    except StopIteration:
        print("  ❌ Блок средних значений не найден")
        return False

    summary_lines = []
    for line in lines[idx + 1 : idx + 5]:
        if not line.strip():
            break
        summary_lines.append(line.strip())

    if not summary_lines:
        print("  ❌ Строки со средними значениями отсутствуют")
        return False

    if not all("swings/zone" in entry for entry in summary_lines):
        print("  ❌ Не найдены числовые значения свингов")
        return False

    print("  ✅ Средние значения рассчитаны")
    return True


def test_guidelines_block() -> bool:
    print("📋 Тест: рекомендации по выбору стратегий")
    output = _combined_output()

    if "Strategy Selection Guidelines:" not in output:
        print("  ❌ Не найден блок рекомендаций")
        return False

    checklist = ["ZigZag:", "FindPeaks:", "PivotPoints:"]
    missing = [item for item in checklist if item not in output]
    if missing:
        print("  ❌ Отсутствуют секции: " + ", ".join(missing))
        return False

    print("  ✅ Блок рекомендаций присутствует")
    return True


def test_cross_reference_targets() -> bool:
    print("📋 Тест: проверка ссылок в конце вывода")
    output = _combined_output()

    resources_match = re.search(r"Further resources:(.*)", output, re.S)
    if not resources_match:
        print("  ❌ Блок ссылок не найден")
        return False

    entries = [line.strip(" -") for line in resources_match.group(1).splitlines() if line.strip()]
    targets = [entry for entry in entries if entry.endswith((".md", ".py"))]

    missing = []
    for entry in targets:
        path = PROJECT_ROOT / entry
        if not path.exists():
            missing.append(entry)

    if missing:
        print("  ❌ Не найдены файлы: " + ", ".join(missing))
        return False

    print("  ✅ Все ресурсы существуют")
    return True


def main() -> None:
    tests = [
        test_script_execution,
        test_indicator_sections_present,
        test_strategy_table_metrics,
        test_average_swings_summary,
        test_guidelines_block,
        test_cross_reference_targets,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as exc:  # pragma: no cover
            print(f"  ❌ Необработанное исключение в {test.__name__}: {exc}")
            results.append(False)

    passed = sum(1 for value in results if value)
    print(f"\n✅ Пройдено {passed}/{len(tests)} тестов")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
