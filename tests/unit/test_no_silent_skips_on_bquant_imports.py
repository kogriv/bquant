"""Отсутствующий символ bquant обязан ронять сбор, а не превращаться в пропуск.

Откуда взялось
==============

2026-08-28, при разведении двух «зон» (G28), из пакета убрали модульную
``extract_zone_features`` — чистый дубль метода. В ``tests/unit/test_zones_analysis.py``
она импортировалась внутри ``try/except ImportError`` с флагом
``zone_features_available``, поэтому удаление не уронило ничего: флаг стал ``False``,
и **девять тестов начали молча скипаться**. Отчёт остался зелёным, проверок стало на
девять меньше. Заметил это только сравнение счётчиков полного прогона: 2542 passed /
36 skipped → 2536 / 45.

Форма та же, что ловили в парити доков и в исполнителе примеров: **молчаливое
выпадение из проверки хуже отсутствия проверки** — отчёт говорит «зелено», а
проверено меньше, чем вчера.

Что здесь законно, а что нет
============================

``try/except ImportError`` вокруг **сторонней** библиотеки — нормальный приём:
plotly или matplotlib может не быть, и тест честно пропускается. Вокруг **символа
самого bquant** — нет: если его нет, это либо поломка, либо переименование, и то и
другое обязано быть громким.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS = PROJECT_ROOT / "tests"

#: Файлы, где такой импорт bquant защищён сознательно, и почему. Пусто — и пусть
#: остаётся пустым: повод почти не встречается.
ALLOWED: dict[str, str] = {}


def _handler_is_loud(handler: ast.ExceptHandler) -> bool:
    """Обработчик роняет тест, а не глотает ошибку?

    Это и есть настоящая граница, а не сам факт ``try``. ``except ImportError:
    pytest.fail(...)`` — законно: файл проверяет, что импорт работает, и громко
    сообщает, если нет. ``except ImportError: flag = False`` — то самое проглатывание,
    из-за которого девять тестов молча выпали из прогона.
    """
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call):
            target = node.func
            name = getattr(target, "attr", None) or getattr(target, "id", None)
            if name in {"fail", "skip", "exit", "xfail"}:
                # `pytest.skip` тоже громкий в нужном смысле: пропуск объявлен в
                # точке импорта, а не разлит флагом по всему файлу.
                return True
        if isinstance(node, ast.Assert):
            return True
    return False


def _guarded_bquant_imports(path: Path):
    """Импорты из ``bquant``, ошибка которых **проглатывается**."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - синтаксис тестов проверяет сам pytest
        return []

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        swallows = [
            h for h in node.handlers
            if ((isinstance(h.type, ast.Name) and h.type.id in {"ImportError", "Exception"})
                or (isinstance(h.type, ast.Tuple)
                    and any(isinstance(e, ast.Name) and e.id in {"ImportError", "Exception"}
                            for e in h.type.elts))
                or h.type is None)
            and not _handler_is_loud(h)
        ]
        if not swallows:
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.ImportFrom) and (child.module or "").startswith("bquant"):
                names = ", ".join(a.name for a in child.names)
                found.append((child.lineno, child.module, names))
    return found


_FILES = sorted(p for p in TESTS.rglob("test_*.py") if "__pycache__" not in p.parts)


@pytest.mark.parametrize(
    "path", _FILES, ids=[str(p.relative_to(PROJECT_ROOT)) for p in _FILES]
)
def test_a_bquant_import_in_tests_is_not_guarded(path):
    """Ошибка импорта символа bquant не проглатывается молча."""

    rel = path.relative_to(PROJECT_ROOT).as_posix()
    if rel == Path(__file__).relative_to(PROJECT_ROOT).as_posix():
        return  # этот файл сам разбирает такие конструкции

    guarded = _guarded_bquant_imports(path)
    reason = ALLOWED.get(rel)

    if guarded and not reason:
        places = "; ".join(f"строка {ln}: from {mod} import {names}"
                           for ln, mod, names in guarded)
        pytest.fail(
            f"{rel}: ошибка импорта из bquant проглатывается — {places}\n"
            "Если символ исчезнет, тесты не упадут, а молча пропустятся, и отчёт "
            "останется зелёным при меньшем числе проверок. Импортируйте прямо; "
            "для сторонних необязательных библиотек защита остаётся уместной."
        )

    if reason and not guarded:
        pytest.fail(f"{rel} числится в ALLOWED ({reason}), но защиты уже нет — уберите запись.")


def test_the_scan_looked_at_the_whole_suite():
    """Пустой обход — молчаливый no-op, а не зелёная проверка."""
    assert len(_FILES) >= 50, f"собрано всего {len(_FILES)} тест-файлов — обход сломан"
