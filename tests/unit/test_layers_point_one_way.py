"""Слои смотрят в одну сторону, и импорт пакета не делает работы (G64).

Порядок сверху вниз: ``cli → visualization → analysis → indicators → data → core``.
Модуль импортирует только то, что ниже него — включая импорты внутри функций:
ленивый импорт наверх — та же зависимость, только спрятанная от импорта.

Что было до G64 (2026-09-06), по графу codemap на ``977f915``:

* ``core.config`` держал пять фабрик стратегий и лениво импортировал реестр анализа —
  единственное ребро ``core → analysis`` против сорока обратных;
* ``data.schemas.IndicatorSchema`` создавала индикатор через фабрику — ``data → indicators``;
* ``visualization.plot_zigzag_verification`` считала ZigZag через ``LibraryManager``;
* ``pipeline`` импортировал приватный ``_AdaptiveSwingStrategy``;
* ``import bquant.analysis.zones`` тянул ``import pandas_ta`` (2.55 с локально на тёплом
  кэше numba, 30 с на холодном) и регистрировал встроенные индикаторы трижды.

Проверяется текстом пакета (``ast``), а не графом: тесту нельзя зависеть от инструмента,
которого может не быть. Контракт для codemap — ``codemap.toml``.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "bquant"
# `__main__` — точка входа `python -m bquant`, выше всех: она зовёт `cli` и больше
# ничего. Объявлена слоем, а не исключением: при `exhaustive` нераспределённый модуль
# должен ломать сторож, и он сломал — эта строка появилась после того, как сторож
# покраснел на добавленном `bquant/__main__.py`.
LAYERS = ["__main__", "cli", "visualization", "analysis", "indicators", "data", "core"]
RANK = {name: i for i, name in enumerate(LAYERS)}


def _module_name(path: Path) -> str:
    rel = path.relative_to(PACKAGE.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve(module: str, node: ast.ImportFrom | ast.Import, alias: str | None) -> str | None:
    """Абсолютное имя импортируемого модуля или ``None`` для чужих пакетов."""
    if isinstance(node, ast.Import):
        return alias if alias.startswith("bquant") else None
    if node.level == 0:
        return node.module if (node.module or "").startswith("bquant") else None
    base = module.split(".")
    is_package = (PACKAGE.parent / Path(*base) / "__init__.py").exists()
    anchor = base if is_package else base[:-1]
    anchor = anchor[: len(anchor) - (node.level - 1)] if node.level > 1 else anchor
    return ".".join(anchor + ([node.module] if node.module else []))


def _layer(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 2:
        return None  # корень bquant — вне порядка
    return parts[1]


def _imports():
    """(модуль, узел импорта, целевой модуль, имена) по всему пакету, включая тела функций."""
    for path in sorted(PACKAGE.rglob("*.py")):
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    target = _resolve(module, node, a.name)
                    if target:
                        yield module, node, target, []
            elif isinstance(node, ast.ImportFrom):
                target = _resolve(module, node, None)
                if target:
                    yield module, node, target, [a.name for a in node.names]


def _classified_imports():
    """(модуль, строка, цель, вид) по всему пакету.

    Вид ребра решает, чем цикл является. ``eager`` — импорт на верхнем уровне
    модуля, он исполняется при загрузке и цикл из таких рёбер ломает импорт или
    оставляет полуинициализированный модуль. ``lazy`` — импорт в теле функции,
    исполняется по вызову: цикл из них законен и в пакете есть намеренный
    (``indicators.base`` ↔ ``custom.*`` через фабрику). ``type_only`` — импорт под
    ``if TYPE_CHECKING:``, во время исполнения его нет вовсе.
    """

    def walk(node, module, lazy, type_only):
        for child in ast.iter_child_nodes(node):
            child_lazy = lazy or isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)
            )
            child_type_only = type_only or (
                isinstance(node, ast.If)
                and node.test is not child
                and _is_type_checking_test(node.test)
            )
            if isinstance(child, ast.Import):
                for a in child.names:
                    target = _resolve(module, child, a.name)
                    if target:
                        yield module, child.lineno, target, _kind(child_lazy, child_type_only)
            elif isinstance(child, ast.ImportFrom):
                target = _resolve(module, child, None)
                if target:
                    yield module, child.lineno, target, _kind(child_lazy, child_type_only)
            yield from walk(child, module, child_lazy, child_type_only)

    for path in sorted(PACKAGE.rglob("*.py")):
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        yield from walk(tree, module, False, False)


def _kind(lazy: bool, type_only: bool) -> str:
    if lazy:
        return "lazy"
    return "type_only" if type_only else "eager"


def _is_type_checking_test(test) -> bool:
    """``TYPE_CHECKING`` или ``typing.TYPE_CHECKING`` в условии ``if``."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _cycle(edges):
    """Первый найденный цикл как список модулей или ``None``."""
    graph = {}
    for src, dst in edges:
        graph.setdefault(src, set()).add(dst)
    colour, stack = {}, []

    def visit(node):
        colour[node] = "grey"
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            if colour.get(nxt) == "grey":
                return stack[stack.index(nxt):] + [nxt]
            if nxt not in colour:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = "black"
        return None

    for node in sorted(graph):
        if node not in colour:
            found = visit(node)
            if found:
                return found
    return None


def _package_modules():
    return {_module_name(path) for path in PACKAGE.rglob("*.py")}


def _edges(kinds):
    """Рёбра между модулями пакета; цель-подпакет считается своим ``__init__``."""
    modules = _package_modules()
    for module, _, target, kind in _classified_imports():
        if kind not in kinds or target not in modules or target == module:
            continue
        yield module, target


def test_the_eager_import_graph_is_acyclic():
    """Цикл из импортов верхнего уровня — полуинициализированный модуль, не стиль."""
    cycle = _cycle(_edges({"eager"}))
    assert cycle is None, "eager import cycle: " + " -> ".join(cycle or [])


def test_the_type_only_graph_is_acyclic_too():
    """Аннотация вверх стирается при исполнении, но связь описывает ту же зависимость."""
    cycle = _cycle(_edges({"eager", "type_only"}))
    assert cycle is None, "cycle through a type-only import: " + " -> ".join(cycle or [])


def test_the_classifier_tells_the_three_kinds_apart():
    """Иначе «циклов нет» означало бы только, что сканер не видит рёбер."""
    kinds = {kind for *_, kind in _classified_imports()}
    assert "eager" in kinds and "lazy" in kinds, sorted(kinds)

    source = (
        "from typing import TYPE_CHECKING\n"
        "import bquant.core.cache\n"
        "if TYPE_CHECKING:\n"
        "    import bquant.analysis.zones\n"
        "def f():\n"
        "    import bquant.data.samples\n"
    )
    tree = ast.parse(source)
    seen = {}
    def walk(node, lazy, type_only):
        for child in ast.iter_child_nodes(node):
            child_lazy = lazy or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            child_type_only = type_only or (
                isinstance(node, ast.If)
                and node.test is not child
                and _is_type_checking_test(node.test)
            )
            if isinstance(child, ast.Import):
                seen[child.names[0].name] = _kind(child_lazy, child_type_only)
            walk(child, child_lazy, child_type_only)
    walk(tree, False, False)
    assert seen == {
        "bquant.core.cache": "eager",
        "bquant.analysis.zones": "type_only",
        "bquant.data.samples": "lazy",
    }


def test_imports_point_down_the_layer_stack():
    upward = []
    for module, node, target, _ in _imports():
        src, dst = _layer(module), _layer(target)
        if src is None or dst is None or src == dst:
            continue
        if src not in RANK or dst not in RANK:
            upward.append(f"{module}:{node.lineno} -> {target} (undeclared layer)")
        elif RANK[dst] < RANK[src]:
            upward.append(f"{module}:{node.lineno} -> {target}")
    assert not upward, "imports pointing UP the layer stack:\n  " + "\n  ".join(upward)


def test_no_private_name_is_imported_from_another_module():
    leaks = []
    for module, node, target, names in _imports():
        for name in names:
            if name.startswith("_") and not name.startswith("__") and target != module:
                leaks.append(f"{module}:{node.lineno} imports {target}.{name}")
    assert not leaks, "private names crossing module boundaries:\n  " + "\n  ".join(leaks)


def test_registration_happens_in_one_place_and_not_at_import_of_submodules():
    """Регистрация индикаторов — один бутстрап; загрузка библиотек — по запросу."""
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:  # только верхний уровень модуля
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute):
                    if call.func.attr in ("register_indicator", "load_all_libraries", "load_library", "ensure_loaded"):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                            continue
                        offenders.append(f"{module}:{call.lineno} {ast.unparse(call.func)}()")
    assert not offenders, "module-level registration/loading:\n  " + "\n  ".join(offenders)


@pytest.mark.parametrize("entry", ["bquant.analysis.zones", "bquant.indicators", "bquant.data"])
def test_importing_the_package_does_not_load_external_indicator_libraries(entry):
    code = (
        "import sys, os\n"
        "os.environ.pop('BQUANT_SKIP_PANDAS_TA', None); os.environ.pop('BQUANT_SKIP_TALIB', None)\n"
        f"import {entry}\n"
        "print(sorted(m for m in ('pandas_ta', 'talib') if m in sys.modules))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr[-800:]
    assert out.stdout.strip().splitlines()[-1] == "[]", (
        f"`import {entry}` loaded external indicator libraries: {out.stdout.strip()}"
    )


def test_the_scan_sees_the_package():
    modules = {m for m, *_ in _imports()}
    assert len(modules) > 60, f"only {len(modules)} modules with bquant imports — the scanner is broken"
