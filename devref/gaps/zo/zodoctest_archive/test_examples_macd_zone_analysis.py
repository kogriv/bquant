"""Валидатор для examples/02_macd_zone_analysis.py."""

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
SCRIPT_PATH = PROJECT_ROOT / "examples" / "02_macd_zone_analysis.py"


@lru_cache(maxsize=1)
def _run_example() -> Tuple[int, str, str]:
    """Запускает пример и кэширует вывод."""

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


def test_script_execution() -> bool:
    print("📋 Тест: запуск examples/02_macd_zone_analysis.py")

    code, stdout, stderr = _run_example()

    if code != 0:
        print(f"  ❌ Возврат кода {code}")
        if stderr:
            print("  ℹ️ STDERR:")
            print(stderr)
        return False

    if "Traceback" in stdout or "Traceback" in stderr:
        print("  ❌ Найден traceback в выводе")
        return False

    print("  ✅ Скрипт завершается без ошибок")
    return True


def test_sections_present() -> bool:
    print("📋 Тест: наличие ключевых разделов")
    _, stdout, _ = _run_example()

    required_markers = [
        "1. [!] Deprecated подход (MACDZoneAnalyzer)",
        "2. [OK] Новый универсальный подход",
        "3. Разные стратегии детекции MACD зон",
        "4. Модульное использование компонентов",
        "5. Визуализация результатов",
    ]

    missing = [marker for marker in required_markers if marker not in stdout]
    if missing:
        print("  ❌ Не найдены разделы:")
        for marker in missing:
            print(f"    - {marker}")
        return False

    print("  ✅ Все обязательные разделы присутствуют")
    return True


def test_zone_counts_consistency() -> bool:
    print("📋 Тест: сравнение количества зон старого и нового подходов")
    _, stdout, _ = _run_example()

    old_match = re.search(r"Analysis complete \(old approach\):.*?- Zones found: (\d+)", stdout, re.S)
    new_match = re.search(r"Analysis complete \(new approach\):.*?- Zones found: (\d+)", stdout, re.S)

    if not old_match or not new_match:
        print("  ❌ Не удалось извлечь счетчики зон")
        return False

    old_count = int(old_match.group(1))
    new_count = int(new_match.group(1))

    if old_count == 0 or new_count == 0:
        print(f"  ❌ Некорректные значения: old={old_count}, new={new_count}")
        return False

    if old_count != new_count:
        print(f"  ❌ Количество зон отличается: old={old_count}, new={new_count}")
        return False

    print(f"  ✅ Оба подхода нашли {old_count} зон")
    return True


def test_combined_strategy_non_empty() -> bool:
    print("📋 Тест: комбинированная стратегия")
    _, stdout, _ = _run_example()

    combined_match = re.search(r"Стратегия 3: Combined.*?\n[^\n]*Зон: (\d+)", stdout, re.S)
    if not combined_match:
        print("  ❌ Не найден блок комбинированной стратегии")
        return False

    combined_count = int(combined_match.group(1))
    if combined_count <= 0:
        print(f"  ❌ Комбинированная стратегия вернула {combined_count} зон")
        return False

    print(f"  ✅ Комбинированная стратегия нашла {combined_count} зон")
    return True


def test_cross_references() -> bool:
    print("📋 Тест: cross-reference ссылки в финальном блоке")

    targets = [
        PROJECT_ROOT / "examples" / "02a_universal_zones.py",
        PROJECT_ROOT / "examples" / "04_comprehensive_analysis.py",
        PROJECT_ROOT / "research" / "notebooks" / "03_zones_universal.py",
    ]

    missing = [str(path) for path in targets if not path.exists()]
    if missing:
        print("  ❌ Отсутствуют целевые файлы:")
        for path in missing:
            print(f"    - {path}")
        return False

    print("  ✅ Все ссылки ведут на существующие файлы")
    return True


def main() -> None:
    tests = [
        test_script_execution,
        test_sections_present,
        test_zone_counts_consistency,
        test_combined_strategy_non_empty,
        test_cross_references,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as exc:  # pragma: no cover - страховка
            print(f"  ❌ Необработанное исключение в {test.__name__}: {exc}")
            results.append(False)

    passed = sum(1 for value in results if value)
    print(f"\n✅ Пройдено {passed}/{len(tests)} тестов")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
