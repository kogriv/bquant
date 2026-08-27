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


def _pyplot_aliases(tree):
    """Names bound to `matplotlib.pyplot` in this module."""
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "matplotlib.pyplot":
                    aliases.add(alias.asname or "matplotlib")
        elif isinstance(node, ast.ImportFrom) and node.module == "matplotlib":
            for alias in node.names:
                if alias.name == "pyplot":
                    aliases.add(alias.asname or "pyplot")
    return aliases


def _unguarded_show_calls(tree, aliases):
    """`plt.show()` calls that no `if` stands in front of.

    Walked with an explicit stack rather than `ast.walk` because the question is
    about ancestry: the same call is fine under a condition and fatal without one.
    """
    found = []

    def visit(node, under_if):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "show"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in aliases
            and not under_if
        ):
            found.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child, under_if or isinstance(node, ast.If))

    visit(tree, False)
    return found


@pytest.mark.parametrize(
    "path", list(_iter_scripts()),
    ids=[str(p.relative_to(PROJECT_ROOT)) for p in _iter_scripts()],
)
def test_script_does_not_block_on_a_gui_window(path):
    """`plt.show()` with an interactive backend waits for the window to be closed.

    A shipped script has to be runnable without anyone at the screen — from a
    terminal, from CI, from another script. `examples/zone_analysis_global_swings.py`
    ended with a bare `plt.show()`, and with matplotlib's `tkagg` backend and a
    live DISPLAY it stopped there: 4 seconds of work followed by an unbounded
    wait, with the console output already fully printed. From the outside it read
    as "computes for several minutes" rather than "waiting for a click", which is
    how the note "takes ~7 minutes, not a hang" came to be written down.

    The rule is not "never show a chart" — it is that showing one must be a
    decision someone made. A call under any `if` passes; a bare one does not.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    aliases = _pyplot_aliases(tree)
    if not aliases:
        pytest.skip("script does not use pyplot")

    lines = _unguarded_show_calls(tree, aliases)
    assert not lines, (
        f"{path.relative_to(PROJECT_ROOT)}: unconditional pyplot.show() at line(s) "
        f"{lines} — it blocks until the window is closed. Save the figure by "
        f"default and put the call behind an explicit opt-in."
    )
