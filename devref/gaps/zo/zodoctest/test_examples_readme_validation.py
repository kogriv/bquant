"""Валидация раздела docs/examples/README.md (этап 5.6)."""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_README = PROJECT_ROOT / "docs/examples/README.md"
EXAMPLES_DIR = PROJECT_ROOT / "examples"

os.environ.setdefault("BQUANT_LOG_LEVEL", "ERROR")
os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("PANDAS_TA_SILENT", "1")
logging.getLogger().setLevel(logging.WARNING)


def _extract_links(markdown_text: str) -> List[str]:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    return pattern.findall(markdown_text)


def _extract_code_blocks(markdown_text: str, language: str) -> List[str]:
    pattern = re.compile(rf"```{language}\n(.*?)```", re.DOTALL)
    return [block.strip() for block in pattern.findall(markdown_text)]


def _extract_line_expectations(markdown_text: str) -> List[Tuple[str, int]]:
    pattern = re.compile(
        r"\*\*(\d{2}[a-z]?_[^*]+?\.py)\*\* — [^()]+\((\d+) строк\)",
        re.IGNORECASE,
    )
    return [(match[0], int(match[1])) for match in pattern.findall(markdown_text)]


def test_relative_links() -> bool:
    print("🔗 Проверяем относительные ссылки docs/examples/README.md")
    content = EXAMPLES_README.read_text(encoding="utf-8")
    links = _extract_links(content)
    relative_links = [
        link for link in links if not link.startswith(("http://", "https://", "mailto:"))
    ]

    all_exist = True
    for link in relative_links:
        target = link.split("#", 1)[0]
        if not target:
            continue
        target_path = (EXAMPLES_README.parent / target).resolve()
        exists = target_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {link} → {target_path}")
        if not exists:
            all_exist = False

    return all_exist


def test_python_code_blocks() -> bool:
    print("🐍 Выполняем python-блоки из документации")
    content = EXAMPLES_README.read_text(encoding="utf-8")
    python_blocks = _extract_code_blocks(content, "python")

    if not python_blocks:
        print("  ❌ Не найдены python-блоки")
        return False

    os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    namespace: dict[str, object] = {"__name__": "__main__"}
    success = True

    for idx, block in enumerate(python_blocks):
        print(f"  ▶️ Блок {idx + 1}/{len(python_blocks)}")
        try:
            exec(compile(block, f"examples_readme_block_{idx}", "exec"), namespace)
        except Exception as exc:  # noqa: BLE001
            print(f"    ❌ Ошибка при выполнении блока {idx}: {exc}")
            success = False
            continue

        if idx in (0, 1, 2):
            result = namespace.get("result")
            if not hasattr(result, "zones"):
                print("    ❌ В блоке не получен объект результата с зонами")
                success = False
            else:
                zones = getattr(result, "zones", [])
                print(f"    ✅ Получено зон: {len(zones)}")
                if len(zones) == 0:
                    print("    ⚠️ Зоны не найдены для текущих параметров (это допустимо для RSI 70/30).")

    return success


def test_bash_blocks() -> bool:
    print("🐚 Проверяем bash-блоки с командами")
    content = EXAMPLES_README.read_text(encoding="utf-8")
    bash_blocks = _extract_code_blocks(content, "bash")

    if not bash_blocks:
        print("  ❌ Не найдены bash-блоки")
        return False

    commands = [line.strip() for block in bash_blocks for line in block.splitlines() if line.strip()]
    print(f"  Найдено {len(commands)} команд")

    required_markers: Iterable[str] = (
        "git clone https://github.com/bquant-team/bquant.git",
        "cd bquant",
        "pip install -e .",
        "python examples/01_basic_indicators.py",
        "python examples/02a_universal_zones.py",
    )

    ok = True
    for marker in required_markers:
        if marker not in commands:
            print(f"  ❌ Не найдена команда: {marker}")
            ok = False
        else:
            print(f"  ✅ Обнаружена команда: {marker}")

    forbidden_fragments = ("docs/examples/",)
    for cmd in commands:
        if any(fragment in cmd for fragment in forbidden_fragments):
            print(f"  ❌ Недопустимая команда: {cmd}")
            ok = False

    return ok


def test_language_markers() -> bool:
    print("🗣️ Проверяем русскоязычное содержание")
    content = EXAMPLES_README.read_text(encoding="utf-8").lower()
    markers: Iterable[str] = (
        "пример",
        "анализ",
        "стратег",
        "зона",
        "визуал",
        "миграц",
    )
    found = sum(1 for marker in markers if marker in content)
    print(f"  Найдено {found} тематических маркеров")
    return found >= 5


def test_line_counts() -> bool:
    print("📏 Сверяем количество строк в перечисленных примерах")
    content = EXAMPLES_README.read_text(encoding="utf-8")
    expectations = _extract_line_expectations(content)

    if not expectations:
        print("  ❌ Не удалось найти утверждения о количестве строк")
        return False

    success = True
    for filename, expected_lines in expectations:
        target = EXAMPLES_DIR / filename
        if not target.exists():
            print(f"  ❌ Файл {filename} не найден")
            success = False
            continue

        with target.open(encoding="utf-8") as handle:
            actual_lines = sum(1 for _ in handle)

        if actual_lines != expected_lines:
            print(
                f"  ❌ {filename}: заявлено {expected_lines}, фактически {actual_lines} строк",
            )
            success = False
        else:
            print(f"  ✅ {filename}: {actual_lines} строк")

    return success


def test_quality_standards_structure() -> bool:
    print("📚 Проверяем раздел стандартов качества")
    content = EXAMPLES_README.read_text(encoding="utf-8")
    required_markers: Iterable[str] = (
        "## 📏 Example Quality Standards",
        "### Self-contained",
        "### Well-documented",
        "### Error-handled",
        "### Performance-aware",
    )

    missing = [marker for marker in required_markers if marker not in content]
    for marker in required_markers:
        status = "✅" if marker in content else "❌"
        print(f"  {status} {marker}")

    if missing:
        print("  ❌ Отсутствуют обязательные секции: " + ", ".join(missing))
        return False

    return True


def main() -> bool:
    print("🔍 Валидация docs/examples/README.md")
    print("=" * 50)

    tests = [
        ("Относительные ссылки", test_relative_links),
        ("Python-блоки", test_python_code_blocks),
        ("Bash-команды", test_bash_blocks),
        ("Русскоязычное содержание", test_language_markers),
        ("Количество строк примеров", test_line_counts),
        ("Стандарты качества", test_quality_standards_structure),
    ]

    passed = 0
    for name, func in tests:
        print(f"\n📋 Тест: {name}")
        try:
            if func():
                print("  ✅ Тест пройден")
                passed += 1
            else:
                print("  ❌ Тест провален")
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Критическая ошибка: {exc}")

    total = len(tests)
    print("\n" + "=" * 50)
    print(f"📊 Результат: {passed}/{total} тестов пройдено")
    success = passed == total
    print("🎉 Все проверки успешны!" if success else "⚠️ Обнаружены проблемы!")
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
