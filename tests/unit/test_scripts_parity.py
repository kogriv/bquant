"""Shipped scripts must import what actually exists.

`tests/unit/test_docs_parity.py` does this for documentation. Nothing did it
for the scripts, and it showed: four of the eleven files in `examples/` did not
run at all, and two of them failed on the very first statement.

* `01_basic_indicators.py` imported six `calculate_*` helpers from
  `bquant.indicators`. They live in `bquant.indicators.calculators` and are
  deliberately not raised into the package's `__all__`.
* `03_data_processing.py` imported six names that exist nowhere under any
  module — the data API was renamed (`clean_data` -> `clean_ohlcv_data`,
  `resample_data` -> `resample_ohlcv`, and so on) and the example was left
  behind.

Both are the same failure as a stale doc link, and the same check catches them.
Import resolution is cheap; it runs on every commit, unlike actually executing
the scripts (minutes) or a person happening to try one.

This does **not** assert the scripts run — only that every name they import is
real. Running them is a separate, slower exercise; see the trace log for when it
was last done in full.
"""

import ast
import importlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIRS = [PROJECT_ROOT / "examples", PROJECT_ROOT / "research" / "notebooks"]


def _iter_scripts():
    for directory in SCRIPT_DIRS:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.py")):
            yield path


def _collect_imports():
    """Every ``from bquant... import name`` in a shipped script.

    Parsed with `ast` rather than a regex: a script is real Python, so there is
    no reason to guess at its syntax, and prose about an import (a comment
    naming an old symbol, say) must not be mistaken for one.
    """
    seen = {}
    for path in _iter_scripts():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - reported by its own test
            seen.setdefault(("<syntax error>", str(exc)), path)
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level:
                continue
            module = node.module or ""
            if not module.startswith("bquant"):
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                seen.setdefault((module, alias.name), path)
    return [(module, name, path) for (module, name), path in sorted(seen.items())]


_IMPORTS = _collect_imports()


def test_the_scan_found_something():
    """A scan that silently matches nothing would pass forever."""
    assert len(_IMPORTS) > 20, (
        f"only {len(_IMPORTS)} imports found across examples/ and "
        "research/notebooks/ — the scan is probably looking in the wrong place"
    )


@pytest.mark.parametrize(
    "module, name, path",
    _IMPORTS,
    ids=[f"{module}.{name}" for module, name, _ in _IMPORTS],
)
def test_script_import_resolves(module, name, path):
    if module == "<syntax error>":
        pytest.fail(f"{path.relative_to(PROJECT_ROOT)}: {name}")
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # pragma: no cover - failure path is the assertion
        pytest.fail(f"{path.relative_to(PROJECT_ROOT)}: cannot import '{module}': {exc}")
    assert hasattr(mod, name), (
        f"{path.relative_to(PROJECT_ROOT)}: 'from {module} import {name}' — "
        f"'{module}' has no attribute '{name}'"
    )


@pytest.mark.parametrize(
    "path", list(_iter_scripts()),
    ids=[str(p.relative_to(PROJECT_ROOT)) for p in _iter_scripts()],
)
def test_script_parses(path):
    """A script that is not valid Python cannot run, whatever else is true."""
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:  # pragma: no cover - failure path is the assertion
        pytest.fail(f"{path.relative_to(PROJECT_ROOT)}: {exc}")
