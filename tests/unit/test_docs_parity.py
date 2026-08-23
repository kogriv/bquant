"""Documentation ↔ code parity tests (auto-scanning).

These supersede the hand-maintained validators under
``devref/gaps/zo/zodoctest/``. Rather than hardcoding per-document expectations
(which silently go stale — the D1 triage found a validator still pointing at a
file that had moved to ``devref/archive/``), these scan the *live* docs on every
run and assert two invariants:

1. **Cross-reference integrity** — every local file link in the scanned markdown
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
import textwrap
from pathlib import Path

import pytest

# Keep external indicator libraries out of the import path — parity only needs
# the pure-python bquant surface, and loading pandas_ta/TA-Lib is slow/fragile.
os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS = PROJECT_ROOT / "docs"

# User-facing docs that live OUTSIDE `docs/`. Each entry here was added because
# the scanner's scope, not the check itself, was the thing that failed:
#   - `README.md` is what `pyproject.toml` ships to PyPI as the package
#     description; a removed API left a broken
#     `from bquant.indicators import MACDZoneAnalyzer` on the front page.
#   - `examples/README.md` carried the same broken import in a ```python block
#     while the whole suite stayed green.
# Add a file here rather than trusting that `docs/` is the whole surface.
EXTRA_DOCS = (
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "examples/README.md",
    "research/README.md",
    "scripts/README.md",
)

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_HAS_EXT_RE = re.compile(r"\.\w+$")
_PY_BLOCK_RE = re.compile(r"```python\n(.*?)```", re.DOTALL)
# reStructuredText equivalent. `docs/index.rst` is the Sphinx landing page and was
# invisible to a markdown-only scanner — it kept a live import of a class that had
# already been deleted. Matches an indented literal block after the directive.
_RST_BLOCK_RE = re.compile(
    r"\.\.[ \t]+code-block::[ \t]*python[^\n]*\n\n((?:(?:[ \t]+[^\n]*)?\n)+)"
)
# Matches both single-line imports and the parenthesised multi-line form. The
# earlier single-line pattern captured a bare "(" as the imported name, which the
# collector then stripped to an empty string and skipped — so every multi-line
# `from bquant... import (...)` block in the docs (11 of them) was silently
# unchecked. A silent skip in a parity checker is worse than no checker.
_IMPORT_RE = re.compile(
    r"^[ \t]*from[ \t]+(bquant[\w.]*)[ \t]+import[ \t]+(\([\s\S]*?\)|[^\n(]+)",
    re.MULTILINE,
)
_COMMENT_RE = re.compile(r"#[^\n]*")


def _iter_docs():
    docs = [p for p in DOCS.rglob("*.md") if "_build" not in p.parts]
    docs += [p for p in DOCS.rglob("*.rst") if "_build" not in p.parts]
    docs += [PROJECT_ROOT / name for name in EXTRA_DOCS
             if (PROJECT_ROOT / name).is_file()]
    return sorted(docs)


def _python_blocks(md, text):
    """Python example blocks, in whichever markup the file uses."""
    if md.suffix == ".rst":
        return [textwrap.dedent(b) for b in _RST_BLOCK_RE.findall(text)]
    return _PY_BLOCK_RE.findall(text)


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
        for block in _python_blocks(md, text):
            for match in _IMPORT_RE.finditer(block):
                module = match.group(1)
                # Strip comments on every line, not just the first — multi-line
                # blocks can annotate individual names.
                raw_names = _COMMENT_RE.sub("", match.group(2))
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


def test_parity_parses_multiline_imports():
    """Parenthesised multi-line imports must yield their names, not a bare "(".

    Pinned because they used to collapse to an empty name and be skipped, leaving
    11 documented import blocks unchecked while the suite reported green.
    """
    sample = (
        "from bquant.analysis.zones.presets import (\n"
        "    analyze_macd_zones,\n"
        "    analyze_rsi_zones,  # comment\n"
        ")\n"
    )
    found = _IMPORT_RE.findall(sample)
    assert found, "multi-line import not matched at all"
    module, raw = found[0]
    names = {
        n.strip()
        for n in _COMMENT_RE.sub("", raw).replace("(", "").replace(")", "").split(",")
        if n.strip()
    }
    assert module == "bquant.analysis.zones.presets"
    assert names == {"analyze_macd_zones", "analyze_rsi_zones"}


def test_parity_scan_found_content():
    """Guard against the scanners silently collecting nothing (e.g. moved docs)."""
    assert _LOCAL_LINKS, "no local markdown links collected — docs path wrong?"
    assert _BQUANT_IMPORTS, "no bquant imports collected — docs path wrong?"


def test_parity_covers_docs_outside_the_docs_tree():
    """Files that a narrower scanner missed must stay in scope.

    Each of these was a real blind spot, not a hypothetical one: `README.md` is the
    package description shipped to PyPI, `examples/README.md` held a ```python block
    importing a deleted class, and `docs/index.rst` — the Sphinx landing page — was
    invisible to a markdown-only scan. All three stayed green while broken.
    """
    scanned = {p.relative_to(PROJECT_ROOT).as_posix() for p in _iter_docs()}
    for required in ("README.md", "examples/README.md", "docs/index.rst"):
        assert required in scanned, f"{required} dropped out of parity scope"


def test_parity_reads_rst_code_blocks():
    """The .rst extractor must actually extract — a silently-empty regex is a no-op."""
    landing = DOCS / "index.rst"
    blocks = _python_blocks(landing, landing.read_text(encoding="utf-8"))
    assert blocks, "no python code-blocks parsed out of docs/index.rst"
    assert any("bquant" in b for b in blocks), "rst blocks parsed but carry no bquant code"
