"""Вызовы в примерах доков сверяются с реальными сигнатурами (G27, шаг 3).

Зачем ещё одна проверка
=======================

Их теперь три, и каждая берёт свой слой:

1. ``test_docs_parity.py`` — **имя** резолвится: модуль импортируется, символ есть.
2. ``test_docs_examples_run.py`` — **самодостаточный** пример исполняется.
3. этот файл — **вызов** согласован с сигнатурой, без исполнения.

Третий слой нужен из-за арифметики: из 433 python-блоков доков исполнимы 167, а 85
используют пакет, но опираются на предыдущий блок страницы. Исполнить их нельзя —
сшивка блоков ввела бы порядок, которого дока не обещает. А **сверить** можно:
страница сама объявляет, что значит каждое имя, своими же импортами.

Что ловится и чего не ловится
=============================

Ловится прямой вызов функции или класса, чьё имя импортировано где-то на этой
странице: неизвестный именованный аргумент, пропущенный обязательный, лишний
позиционный. На вчерашних дефектах это дало бы ``create_swing_strategy(legs=15)``
при сигнатуре ``(config=None)`` и ``ZoneAnalysisPipeline()`` без обязательного
``config``.

**Не** ловится вызов метода на объекте (``builder.with_data(...)``): чтобы узнать
сигнатуру, нужен тип получателя, а он статически неизвестен. Такие места остаются
за исполнением и за чтением — честнее сказать это прямо, чем делать вид, что слой
покрывает всё.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
import re
import sys
from pathlib import Path

import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.unit.test_docs_parity import (  # noqa: E402
    PROJECT_ROOT,
    _iter_docs,
    _python_blocks,
)


#: Вызовы, которые обязаны не сходиться с сигнатурой, и почему.
#: Пусто — и пусть остаётся пустым: запись здесь означает, что дока показывает
#: заведомо неверный вызов, а таких поводов почти не бывает.
EXPECTED_MISMATCHES: dict[tuple[str, str], str] = {}


def _unwrap(block: str) -> str:
    """Снять цитату и общий отступ (та же обработка, что у исполнителя)."""
    import textwrap

    lines = block.split("\n")
    meaningful = [ln for ln in lines if ln.strip()]
    if meaningful and all(ln.lstrip().startswith(">") for ln in meaningful):
        lines = [ln.lstrip()[1:].removeprefix(" ") if ln.strip() else ln for ln in lines]
    return textwrap.dedent("\n".join(lines))


def _page_symbols(blocks) -> dict[str, object]:
    """Что значат имена на этой странице — по её собственным импортам.

    Это не сшивка исполнения, а таблица имён: страница сама объявляет, что
    ``analyze_zones`` — это ``bquant.analysis.zones.analyze_zones``. Имя,
    связанное на странице **по-разному** (импорт из двух мест, переприсваивание),
    выбрасывается: неоднозначность лучше пропустить, чем угадать.
    """
    # Значения складываются по id: импортируемый объект не обязан быть хешируемым
    # (константы-словари в пакете есть), а нам нужна лишь однозначность.
    candidates: dict[str, dict[int, object]] = {}
    rebound: set[str] = set()

    for block in blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("bquant"):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local = alias.asname or alias.name
                    try:
                        module = importlib.import_module(node.module)
                        obj = getattr(module, alias.name)
                    except Exception:
                        continue
                    candidates.setdefault(local, {})[id(obj)] = obj
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                rebound.add(node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                rebound.add(node.name)

    return {
        name: next(iter(objs.values()))
        for name, objs in candidates.items()
        if len(objs) == 1 and name not in rebound
    }


def _direct_calls(block: str):
    """Вызовы вида ``name(...)`` — только они статически разрешимы."""
    try:
        tree = ast.parse(block)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            yield node


def _collect_call_checks():
    items = []
    for doc in _iter_docs():
        text = doc.read_text(encoding="utf-8")
        rel = doc.relative_to(PROJECT_ROOT).as_posix()
        blocks = [_unwrap(b) for b in _python_blocks(doc, text)]
        symbols = _page_symbols(blocks)
        if not symbols:
            continue
        for block in blocks:
            for call in _direct_calls(block):
                target = symbols.get(call.func.id)
                if target is None or not callable(target):
                    continue
                # Распаковка скрывает фактические аргументы — проверять нечего.
                if any(isinstance(a, ast.Starred) for a in call.args):
                    continue
                if any(kw.arg is None for kw in call.keywords):
                    continue
                try:
                    signature = inspect.signature(target)
                except (TypeError, ValueError):
                    continue
                line = text[:text.find(block[:40])].count("\n") + 1 if block[:40] in text else 0
                items.append((rel, line, call.func.id, target, signature,
                              len(call.args),
                              tuple(kw.arg for kw in call.keywords)))
    return items


CALL_CHECKS = _collect_call_checks()


@pytest.mark.parametrize(
    "rel, line, name, target, signature, positional, keywords",
    CALL_CHECKS,
    ids=[f"{rel}:{name}" for rel, _, name, *_ in CALL_CHECKS],
)
def test_a_documented_call_matches_the_signature(
    rel, line, name, target, signature, positional, keywords
):
    """Вызов в доке обязан быть вызовом, который примет реальная функция."""

    reason = EXPECTED_MISMATCHES.get((rel, name))
    placeholder = object()
    try:
        signature.bind(*[placeholder] * positional,
                       **{kw: placeholder for kw in keywords})
    except TypeError as exc:
        if reason:
            return
        pytest.fail(
            f"{rel}: документированный вызов `{name}(…)` не подходит под сигнатуру\n"
            f"    вызов:    {positional} позиционных, именованные: {list(keywords)}\n"
            f"    сигнатура: {name}{signature}\n"
            f"    {exc}"
        )

    if reason:
        pytest.fail(
            f"{rel}: `{name}` числится в EXPECTED_MISMATCHES ({reason}), но вызов "
            f"сходится с сигнатурой. Уберите запись."
        )


def test_the_scan_found_calls_to_check():
    """Пустой сбор — молчаливый no-op, а не зелёная проверка."""
    assert len(CALL_CHECKS) >= 100, (
        f"собрано всего {len(CALL_CHECKS)} проверяемых вызовов — "
        "похоже, таблица имён страницы или сбор вызовов сломались"
    )


def test_an_ambiguous_name_is_skipped_rather_than_guessed():
    """Имя, связанное на странице по-разному, не проверяется вовсе.

    Угадать, какое связывание действует в данном блоке, статически нельзя, а
    угаданная проверка хуже отсутствующей: она краснеет на верном коде.
    """
    blocks = [
        "from bquant.data.samples import get_sample_data\n",
        "def get_sample_data(x):\n    return x\n",
    ]
    assert "get_sample_data" not in _page_symbols(blocks)

    only_imported = ["from bquant.data.samples import get_sample_data\n"]
    assert "get_sample_data" in _page_symbols(only_imported)
