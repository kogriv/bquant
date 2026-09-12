"""The changelog must mark what it breaks, in one form, findable by one grep.

`docs/versioning.md` promises a stranger that a single command over `CHANGELOG.md`
lists every breaking change. That promise was false when it was written: three
different conventions had been used across sixteen releases — a `(breaking)` suffix
in the section heading (0.0.7-0.0.10), the words `(ломающее изменение)` in prose
(0.0.5), and a `Ломает:` line naming the replacement (0.0.12 onward) — and two
releases that removed public names carried no marker at all. 0.0.11 deleted two
public dataclass fields and narrowed a metadata key with nothing to grep for.

The defect is the project's own recurring form in documentation shape: a promise that
reads like a guarantee, and a reader who finds nothing and concludes nothing broke.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"

# The marker in force since 0.0.12: a line that names what broke and what replaces it.
CURRENT_MARKER = "Ломает:"

# Superseded forms. They stay readable in the releases that used them — history is not
# rewritten — but a new release may not reach for them again.
LEGACY_MARKERS = ("(breaking)", "(ломающее изменение)")

# The release in which `Ломает:` became the convention. Anything newer must use it.
CONVENTION_SINCE = (0, 0, 12)

_HEADING_RE = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)


def _sections() -> list[tuple[str, str]]:
    """`[(version, body), ...]` in file order, `Unreleased` included."""
    text = CHANGELOG.read_text(encoding="utf-8")
    marks = list(_HEADING_RE.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), text[m.end():end]))
    return out


def _as_tuple(version: str) -> tuple[int, ...] | None:
    """`0.0.12` -> `(0, 0, 12)`; `Unreleased` and anything unparsable -> `None`."""
    parts = version.split(".")
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


SECTIONS = _sections()


def test_the_scan_found_a_changelog_to_check():
    """Positive control: an empty parse must not pass as a clean changelog.

    Every other check here is a `for` over `SECTIONS`. A regex that stopped matching
    would make all of them vacuously green — the exact shape this repository keeps
    finding in its own guards.
    """
    assert len(SECTIONS) >= 16, f"only {len(SECTIONS)} release sections parsed"
    markers = sum(body.count(CURRENT_MARKER) for _, body in SECTIONS)
    assert markers >= 20, f"only {markers} `{CURRENT_MARKER}` lines found in the whole file"


@pytest.mark.parametrize("version, body", SECTIONS, ids=[v for v, _ in SECTIONS])
def test_a_release_that_removes_something_says_what_it_breaks(version, body):
    """A `### Removed` section without a marker leaves the reader nothing to grep."""
    if "### Removed" not in body:
        return
    has_marker = CURRENT_MARKER in body or any(m in body for m in LEGACY_MARKERS)
    assert has_marker, (
        f"release {version} has a `### Removed` section but no breaking-change marker; "
        f"`docs/versioning.md` tells readers to grep for `{CURRENT_MARKER}`"
    )


@pytest.mark.parametrize("version, body", SECTIONS, ids=[v for v, _ in SECTIONS])
def test_new_releases_use_one_convention(version, body):
    """One marker going forward. Old releases keep the form they shipped with."""
    number = _as_tuple(version)
    if number is not None and number < CONVENTION_SINCE:
        return
    for legacy in LEGACY_MARKERS:
        assert legacy not in body, (
            f"release {version} uses the superseded marker `{legacy}`; "
            f"since 0.0.12 the convention is a `{CURRENT_MARKER}` line naming the replacement"
        )


@pytest.mark.parametrize("version, body", SECTIONS, ids=[v for v, _ in SECTIONS])
def test_every_marker_names_something(version, body):
    """`Ломает:` with nothing after it is a marker that answers no question."""
    for line in body.splitlines():
        if CURRENT_MARKER not in line:
            continue
        said = line.split(CURRENT_MARKER, 1)[1].strip()
        assert len(said) >= 10, (
            f"release {version} has a bare `{CURRENT_MARKER}` line: {line.strip()!r}"
        )


def test_the_documented_command_finds_every_marked_release():
    """The grep `docs/versioning.md` hands the reader must return every marked release.

    Not a tautology: it fails if the document's regex and the convention drift apart —
    which is how the third phrasing went unnoticed for eleven releases.
    """
    documented = re.compile(r"Ломает:|\(breaking\)")
    policy = (PROJECT_ROOT / "docs" / "versioning.md").read_text(encoding="utf-8")
    assert "Ломает:|\\(breaking\\)" in policy, (
        "docs/versioning.md no longer hands the reader the grep this test checks"
    )
    marked = {v for v, body in SECTIONS if documented.search(body)}
    removing = {v for v, body in SECTIONS if "### Removed" in body}
    assert removing <= marked, f"releases with removals the documented grep misses: {removing - marked}"
