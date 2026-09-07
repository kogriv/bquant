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
bind the same function or class name twice. Repeating a name is legitimate in
two shapes, and they behave oppositely afterwards, so the exclusion cannot be
"any marked definition clears the group":

* accessor groups — `@property` / `@x.setter` / `@x.getter` / `@x.deleter` /
  `@cached_property`. A plain definition **after** such a group is shadowing of
  the worst kind: the property disappears and the type of access changes with
  it, `c.x` stops being a value and becomes a bound method.
* overload groups — `@typing.overload` stubs and `@singledispatch`
  registrations. A plain definition after such a group is the **implementation**,
  the legal end of the pattern.

So the rule is about the *previous* binding, not the current one: a finding if
the previous binding was plain (anything following kills it), or the previous
was an accessor and the current is plain. A previous overload kills nothing.

Reported against this guard by the downstream lab as bquant#118 with the
mutation shown; the hole was empty on this tree (0 findings before and after).
"""

import ast
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Accessor decorators: repeating the name inside the group is intentional, but a
#: plain definition after the group destroys the property.
ACCESSOR_MARKERS = frozenset({"property", "setter", "deleter", "getter", "cached_property"})

#: Overload decorators: repeating the name is intentional and the plain definition
#: that follows is the implementation, not a replacement.
OVERLOAD_MARKERS = frozenset(
    {"overload", "register", "singledispatch", "singledispatchmethod"}
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


def _binding_kind(node):
    """`accessor`, `overload` or `plain` — what the decorators make this binding."""
    names = _decorator_names(node)
    if names & OVERLOAD_MARKERS:
        return "overload"
    if names & ACCESSOR_MARKERS:
        return "accessor"
    return "plain"


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
            kind = _binding_kind(stmt)
            previous = seen.get(stmt.name)
            if previous is not None:
                previous_line, previous_kind = previous
                killed = previous_kind == "plain" or (
                    previous_kind == "accessor" and kind == "plain"
                )
                if killed:
                    findings.append((scope_name, stmt.name, previous_line, stmt.lineno))
            seen[stmt.name] = (stmt.lineno, kind)
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


def test_a_plain_definition_after_a_property_group_is_shadowing():
    """The hole reported as bquant#118: the property is gone and so is its type of access.

    Measured, not read off the source: after the second definition the class
    attribute is no longer a `property` and `c.x` is a bound method, not a value.
    """
    source = (
        "class C:\n"
        "    @property\n"
        "    def x(self):\n"
        "        return 'property'\n"
        "    def x(self):\n"
        "        return 'plain method'\n"
    )
    namespace = {}
    exec(compile(source, "<probe>", "exec"), namespace)
    cls = namespace["C"]
    assert not isinstance(cls.__dict__["x"], property)
    assert callable(cls().x)

    assert _shadowed_definitions(ast.parse(source)) == [("C", "x", 3, 5)]


def test_a_plain_definition_after_overloads_is_the_implementation():
    """The opposite case the fix must not break: overloads end in a plain body."""
    source = (
        "from typing import overload\n"
        "class D:\n"
        "    @overload\n"
        "    def f(self, v: int) -> int: ...\n"
        "    @overload\n"
        "    def f(self, v: str) -> str: ...\n"
        "    def f(self, v):\n"
        "        return v\n"
    )
    namespace = {}
    exec(compile(source, "<probe>", "exec"), namespace)
    instance = namespace["D"]()
    assert instance.f(5) == 5 and instance.f("s") == "s"

    assert _shadowed_definitions(ast.parse(source)) == []


def test_a_plain_definition_before_a_property_is_shadowing_too():
    """Order matters only through the previous binding: a plain body dies either way."""
    source = (
        "class E:\n"
        "    def x(self):\n"
        "        return 1\n"
        "    @property\n"
        "    def x(self):\n"
        "        return 2\n"
    )
    assert _shadowed_definitions(ast.parse(source)) == [("E", "x", 2, 5)]
