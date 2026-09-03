"""A name defined twice in one scope is a defect the suite cannot see.

`MockSwingStrategy` in `test_strategy_infrastructure.py` defined `get_metadata`
twice. The second definition silently replaced the first, and the two returned
different values — `{'name': 'mock', ...}` against `{'name': 'MockSwingStrategy',
'description': ..., ...}`. The only test that reached the method asserted
`isinstance(metadata, dict)` and `'name' in metadata`, so it passed under either
body: the check could not distinguish the thing it was checking.

Nothing else found it either. Grep sees two definitions and reads them as two
methods; the interpreter keeps the last one and says nothing. It surfaced only
because a code graph emitted the `contains` edge twice, and that duplicate had
to be explained.

The guard below is the general form: for every tracked Python file, no scope may
bind the same function or class name twice. Property accessor groups
(`@property` / `@x.setter` / `@x.deleter`), `@typing.overload` stubs and
`@singledispatch` registrations legitimately repeat a name and are excluded by
their decorators — everything else is a definition whose predecessor is dead.
"""

import ast
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Decorators under which repeating a name in one scope is intentional.
ACCESSOR_MARKERS = frozenset(
    {"property", "setter", "deleter", "getter", "overload", "register", "cached_property"}
)


def _tracked_python_files():
    """Every Python file git tracks — keeps virtualenvs and build output out."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [REPO_ROOT / line for line in out.splitlines() if line]


def _decorator_names(node):
    names = set()
    for dec in getattr(node, "decorator_list", []):
        while isinstance(dec, ast.Call):
            dec = dec.func
        if isinstance(dec, ast.Name):
            names.add(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.add(dec.attr)
    return names


def _shadowed_definitions(tree):
    """(scope, name, lines) for every name bound twice in the same scope."""
    findings = []
    scopes = [("<module>", tree)]
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            scopes.append((node.name, node))

    for scope_name, scope in scopes:
        seen = {}
        for stmt in scope.body:
            if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if _decorator_names(stmt) & ACCESSOR_MARKERS:
                continue
            if stmt.name in seen:
                findings.append((scope_name, stmt.name, seen[stmt.name], stmt.lineno))
            seen[stmt.name] = stmt.lineno
    return findings


def test_no_definition_is_silently_shadowed():
    """No tracked file binds the same name twice in one scope."""
    offenders = []
    for path in _tracked_python_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            # A file that does not parse cannot shadow anything; other suites
            # are responsible for it being valid Python.
            continue
        for scope, name, first, second in _shadowed_definitions(tree):
            rel = path.relative_to(REPO_ROOT)
            offenders.append(f"{rel}:{second} {scope}.{name} replaces the definition at line {first}")

    assert not offenders, "definitions silently shadowed:\n  " + "\n  ".join(offenders)


def test_the_guard_sees_a_shadowed_definition():
    """The guard is only worth having if it reddens on the shape it forbids."""
    source = (
        "class C:\n"
        "    def m(self):\n"
        "        return 1\n"
        "    def m(self):\n"
        "        return 2\n"
    )
    findings = _shadowed_definitions(ast.parse(source))
    assert findings == [("C", "m", 2, 4)]


def test_property_accessors_are_not_shadowing():
    """A property and its setter share a name on purpose."""
    source = (
        "class C:\n"
        "    @property\n"
        "    def x(self):\n"
        "        return self._x\n"
        "    @x.setter\n"
        "    def x(self, value):\n"
        "        self._x = value\n"
    )
    assert _shadowed_definitions(ast.parse(source)) == []
