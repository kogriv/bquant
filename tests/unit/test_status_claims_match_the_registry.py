"""Project-documentation status claims vs. the gap registry.

`docs/` is held by four layers; `devref/`, `tests/STATUS.md` and the README were
held by nothing, and in four days of September 2026 they went stale three times —
a backlog header reading 🟡 "in progress" directly above the line saying the pass
was finished, and `tests/STATUS.md` claiming property-based invariants did not
exist while explaining, further down, how to run them.

This guard owns **no storage and declares no truth**. It compares two records
that already exist — a claim made in a document and the row in
`devref/gaps/gap_inventory_2026-07.md` — and goes red when they disagree. The
registry stays the single source; that was the open question (§7.1 of
`READINESS_2026-09-10.md`) and this is the answer to it.

Three mechanical claims, nothing about meaning:

1. A gap number mentioned anywhere in project documentation exists in the registry.
2. In a **living** document, a line that calls a gap open/closed agrees with the
   registry row.
3. A living document whose header status is 🟡 does not also contain a line
   declaring the work closed.

**Living vs. frozen matters and is not a judgement call.** The repository already
marks it: `**Тип:** живой …` in the header. A dated snapshot
(`READINESS_2026-09-10.md`, an audit, a trace log) legitimately records what was
true on its date, so claims 2 and 3 do not apply to it — a guard that flagged
those would be wider than its subject, which is the failure mode this file is
supposed to be an example against, not an instance of.
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "devref" / "gaps" / "gap_inventory_2026-07.md"

# Always current, whatever their header says: they describe the tree as it is now.
ALWAYS_CURRENT = (
    "tests/STATUS.md",
    "README.md",
    "AGENTS.md",
)

# Excluded from the scan entirely, and each for a stated reason:
#   - `devref/archive/` — a frozen record of a previous session;
#   - `changelogs/` — append-only history; a trace log saying "G38 open" was
#     right on its date and must not be rewritten;
#   - the registry itself — it is the record being compared against.
EXCLUDED_DIRS = ("devref/archive/", "changelogs/")

_GAP_RE = re.compile(r"\bG(\d+[a-z]?)\b")
_REGISTRY_ROW_RE = re.compile(r"^\|\s*(G\d+[a-z]?)\s*\|(.*)$", re.MULTILINE)
_TYPE_RE = re.compile(r"^\*\*Тип:\*\*\s*(.+)$", re.MULTILINE)
# NOT anchored to the start of a line on purpose: the house header puts the marker
# either first (`**Статус:** ✅ …`) or after the date on the same line
# (`**Заведён:** … **Статус:** 🟡 …`). An anchored pattern matched the first shape
# and silently skipped the second — the mutation that proved it was a 🟡 document
# with an appended "✅ закрыт" line that the guard passed.
_STATUS_RE = re.compile(r"\*\*Статус:\*\*\s*(.+)$", re.MULTILINE)

# Openness/closure said in prose. Kept deliberately short: every branch here is a
# branch that can wrongly clear a file, so each one has to earn its place.
_SAYS_OPEN = re.compile(r"🟠|\bостаётся\s+открыт|\bпока\s+открыт|\bне\s+закрыт|\bвсё\s+ещё\s+открыт")
_SAYS_CLOSED = re.compile(r"✅")
_DECLARES_FINISHED = re.compile(
    r"✅\s*(закрыт|закрыта|закрыто|завершён|завершена|сделан|сделана)"
)

OPEN_STATUSES = {"🟠"}
CLOSED_STATUSES = {"✅", "🟢"}


def _registry_rows() -> dict[str, str | None]:
    """Map gap id -> status marker, or ``None`` for a row that carries no marker.

    The registry is not one table: the proposal sections list a gap with a
    rationale and a suggested fix and no legend column at all (``G8``). A row
    without a marker is still a row — it answers "does this number exist", which
    is claim 1, and simply has nothing to say about claim 2. Conflating the two
    would have reported fourteen phantom mentions of a gap that is in the file.
    """
    rows: dict[str, str | None] = {}
    for gap_id, rest in _REGISTRY_ROW_RE.findall(REGISTRY.read_text(encoding="utf-8")):
        marker = None
        cells = [c.strip() for c in rest.split("|")]
        # The status cell is the one *starting* with a legend marker; a description
        # cell can mention one mid-sentence, so position is what distinguishes them.
        for cell in cells:
            if cell[:1] in OPEN_STATUSES | CLOSED_STATUSES | {"🔵"}:
                marker = cell[:1]
                break
        rows.setdefault(gap_id, marker)
    return rows


def _scanned_files() -> list[Path]:
    files = [PROJECT_ROOT / name for name in ALWAYS_CURRENT]
    for path in sorted((PROJECT_ROOT / "devref").rglob("*.md")):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if path == REGISTRY or any(rel.startswith(d) for d in EXCLUDED_DIRS):
            continue
        files.append(path)
    return [f for f in files if f.exists()]


def _is_living(text: str) -> bool:
    declared = _TYPE_RE.search(text)
    return bool(declared and "живой" in declared.group(1).lower())


@pytest.fixture(scope="module")
def registry() -> dict[str, str | None]:
    return _registry_rows()


@pytest.fixture(scope="module")
def scanned() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in _scanned_files()]


def test_the_scan_sees_a_non_empty_corpus(registry, scanned):
    """Positive control: an empty scan passes every other check vacuously."""
    assert len(registry) >= 60, f"registry parsed only {len(registry)} rows"
    mentions = sum(len(_GAP_RE.findall(text)) for _, text in scanned)
    assert len(scanned) >= 10, f"only {len(scanned)} documents scanned"
    assert mentions >= 100, f"only {mentions} gap mentions found outside the registry"


def test_every_mentioned_gap_number_exists_in_the_registry(registry, scanned):
    phantom: list[str] = []
    for path, text in scanned:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        for suffix in sorted(set(_GAP_RE.findall(text))):
            if f"G{suffix}" not in registry:
                phantom.append(f"{rel}: G{suffix}")
    assert not phantom, "gap numbers named by a document but absent from the registry:\n" + "\n".join(
        phantom
    )


def test_living_documents_agree_with_the_registry_on_open_or_closed(registry, scanned):
    divergent: list[str] = []
    for path, text in scanned:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if not (_is_living(text) or rel in ALWAYS_CURRENT):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            ids = {f"G{s}" for s in _GAP_RE.findall(line)}
            if not ids:
                continue
            says_open = bool(_SAYS_OPEN.search(line))
            says_closed = bool(_SAYS_CLOSED.search(line))
            if says_open == says_closed:  # neither, or a line that says both
                continue
            for gap_id in sorted(ids):
                marker = registry.get(gap_id)
                if marker is None:
                    continue  # claim 1 owns this case
                if says_open and marker in CLOSED_STATUSES:
                    divergent.append(
                        f"{rel}:{lineno}: calls {gap_id} open, registry says {marker}"
                    )
                elif says_closed and marker in OPEN_STATUSES:
                    divergent.append(
                        f"{rel}:{lineno}: calls {gap_id} closed, registry says {marker}"
                    )
    assert not divergent, "status claims that disagree with the registry:\n" + "\n".join(divergent)


def test_every_living_document_declares_a_status(scanned):
    """A living document with no status line is invisible to the check below.

    Silence here would read as "nothing in progress", which is the shape of defect
    this whole file exists for: an empty answer that looks like a result.
    """
    silent = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path, text in scanned
        if _is_living(text) and not _STATUS_RE.search(text)
    ]
    assert not silent, "living documents that declare no **Статус:**:\n" + "\n".join(silent)


def test_a_document_marked_in_progress_does_not_also_declare_itself_finished(scanned):
    contradictory: list[str] = []
    for path, text in scanned:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if not _is_living(text):
            continue
        declared = _STATUS_RE.search(text)
        if not declared or "🟡" not in declared.group(1):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _DECLARES_FINISHED.search(line):
                contradictory.append(f"{rel}:{lineno}: {line.strip()[:80]}")
    assert not contradictory, (
        "documents whose header still reads 🟡 while a line declares the work closed:\n"
        + "\n".join(contradictory)
    )
