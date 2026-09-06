#!/usr/bin/env python3
"""Валидация раздела docs/tutorials/README.md (этап 4.1)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[4]
TUTORIALS_README = PROJECT_ROOT / "docs/tutorials/README.md"


def _extract_links(markdown_text: str) -> List[str]:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    return pattern.findall(markdown_text)


def _extract_code_blocks(markdown_text: str, language: str) -> List[str]:
    pattern = re.compile(rf"```{language}\n(.*?)```", re.DOTALL)
    return [block.strip() for block in pattern.findall(markdown_text)]


def test_relative_links() -> bool:
    print("🔗 Проверяем относительные ссылки tutorials/README.md")
    content = TUTORIALS_README.read_text(encoding="utf-8")
    links = _extract_links(content)
    relative_links = [
        link for link in links if not link.startswith(("http://", "https://", "mailto:"))
    ]

    all_exist = True
    for link in relative_links:
        target = link.split("#", 1)[0]
        if not target:
            continue
        target_path = (TUTORIALS_README.parent / target).resolve()
        exists = target_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {link} → {target_path}")
        if not exists:
            all_exist = False

    return all_exist


def test_language_markers() -> bool:
    print("🗣️ Проверяем русскоязычное содержание")
    content = TUTORIALS_README.read_text(encoding="utf-8").lower()
    markers: Iterable[str] = (
        "обучающие",
        "анализ",
        "стратег",
        "архитект",
        "конвейер",
    )
    found = sum(1 for marker in markers if marker in content)
    print(f"  Найдено {found} тематических маркеров")
    return found >= 4


def test_bash_examples() -> bool:
    print("🐚 Проверяем bash-пример установки")
    content = TUTORIALS_README.read_text(encoding="utf-8")
    bash_blocks = _extract_code_blocks(content, "bash")

    if not bash_blocks:
        print("  ❌ Не найден bash-блок с установкой")
        return False

    print(f"  Найдено bash-блоков: {len(bash_blocks)}")

    unique_commands = {line.strip() for block in bash_blocks for line in block.splitlines() if line.strip()}
    if unique_commands != {"pip install bquant"}:
        print(f"  ❌ Ожидался единственный пример 'pip install bquant', получено: {unique_commands}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "help", "install"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  ❌ Не удалось проверить доступность pip: {exc}")
        return False

    if "install packages" not in result.stdout.lower() and "install packages" not in result.stderr.lower():
        print("  ❌ Не удалось подтвердить справку pip install")
        return False

    print("  ✅ Команда pip install доступна (проверена через --help)")
    return True


def main() -> bool:
    print("🔍 Валидация docs/tutorials/README.md")
    print("=" * 50)

    tests = [
        ("Относительные ссылки", test_relative_links),
        ("Русскоязычные маркеры", test_language_markers),
        ("Bash-пример установки", test_bash_examples),
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
