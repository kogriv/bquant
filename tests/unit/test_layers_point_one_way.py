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
LAYERS = ["cli", "visualization", "analysis", "indicators", "data", "core"]
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
