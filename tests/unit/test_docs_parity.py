"""Documentation ↔ code parity tests (auto-scanning).

These supersede the hand-maintained validators under
``devref/gaps/zo/zodoctest/``. Rather than hardcoding per-document expectations
(which silently go stale — the D1 triage found a validator still pointing at a
file that had moved to ``devref/archive/``), these scan the *live* docs on every
run and assert two invariants:

1. **Cross-reference integrity** — every local file link in ``docs/**/*.md``
   resolves to a file that exists. (This is the check that caught the broken
   ``MIGRATION_v2`` and ``swing_detection_approaches`` links during D1, plus 12
   wrong-depth links during D2.)
2. **Example-import parity** — every ``from bquant... import ...`` that appears
   in a documentation python block resolves to a real module *and* symbol, so
   examples cannot reference a renamed/removed API without failing here.

Deliberately portable: filesystem + imports only. No network, no ``sphinx-build``,
no ``pandas_ta``/TA-Lib (those made the original validators non-CI-portable).

Backtick path *mentions* (e.g. `` `devref/…/foo.md` ``) are intentionally NOT
asserted: developer guides legitimately cite illustrative placeholder paths
(``tests/unit/zones/detection/test_my_strategy.py``) that do not exist, so a
strict check there would be flaky. Markdown links are the reliable signal.
"""

import importlib
import os
import re
from pathlib import Path

import pytest

# Keep external indicator libraries out of the import path — parity only needs
# the pure-python bquant surface, and loading pandas_ta/TA-Lib is slow/fragile.
os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS = PROJECT_ROOT / "docs"

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_HAS_EXT_RE = re.compile(r"\.\w+$")
_PY_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)
_IMPORT_RE = re.compile(r"^\s*from\s+(bquant[\w.]*)\s+import\s+(.+)$", re.MULTILINE)


def _iter_docs():
    return sorted(p for p in DOCS.rglob("*.md") if "_build" not in p.parts)


# --------------------------------------------------------------------------- #
# 1. Cross-reference integrity
# --------------------------------------------------------------------------- #
def _collect_local_links():
    items = []
    for md in _iter_docs():
        for match in _LINK_RE.finditer(md.read_text(encoding="utf-8")):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0].strip()
            # Only links that look like a file (have an extension); bare
            # directory / section links are out of scope.
            if not path_part or not _HAS_EXT_RE.search(path_part):
                continue
            items.append((md, path_part))
    return items


_LOCAL_LINKS = _collect_local_links()


@pytest.mark.parametrize(
    "md, link",
    _LOCAL_LINKS,
    ids=[
        f"{md.relative_to(PROJECT_ROOT)}->{link}" for md, link in _LOCAL_LINKS
    ],
)
def test_markdown_link_resolves(md, link):
    target = (md.parent / link).resolve()
    assert target.exists(), (
        f"{md.relative_to(PROJECT_ROOT)} links to a missing file: {link}"
    )


# --------------------------------------------------------------------------- #
# 2. Example-import parity
# --------------------------------------------------------------------------- #
def _collect_bquant_imports():
    seen = {}
    for md in _iter_docs():
        text = md.read_text(encoding="utf-8")
        for block in _PY_BLOCK_RE.findall(text):
            for match in _IMPORT_RE.finditer(block):
                module = match.group(1)
                raw_names = match.group(2).split("#", 1)[0]
                raw_names = raw_names.replace("(", "").replace(")", "")
                for name in raw_names.split(","):
                    name = name.strip().split(" as ", 1)[0].strip()
                    if not name or name == "*":
                        continue
                    seen.setdefault((module, name), md)
    return [(module, name, md) for (module, name), md in sorted(seen.items())]


_BQUANT_IMPORTS = _collect_bquant_imports()


@pytest.mark.parametrize(
    "module, name, md",
    _BQUANT_IMPORTS,
    ids=[f"{module}.{name}" for module, name, _ in _BQUANT_IMPORTS],
)
def test_doc_bquant_import_resolves(module, name, md):
    try:
        mod = importlib.import_module(module)
    except Exception as exc:  # pragma: no cover - failure path is the assertion
        pytest.fail(
            f"{md.relative_to(PROJECT_ROOT)}: cannot import '{module}': {exc}"
        )
    assert hasattr(mod, name), (
        f"{md.relative_to(PROJECT_ROOT)}: documented import "
        f"'from {module} import {name}' — '{module}' has no attribute '{name}'"
    )


def test_parity_scan_found_content():
    """Guard against the scanners silently collecting nothing (e.g. moved docs)."""
    assert _LOCAL_LINKS, "no local markdown links collected — docs path wrong?"
    assert _BQUANT_IMPORTS, "no bquant imports collected — docs path wrong?"
