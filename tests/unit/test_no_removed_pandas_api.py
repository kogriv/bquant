"""pandas 3 removed what pandas 2.2 deprecated, and the suite could not see it.

Every environment the suite had run in carried pandas 2.3.3, where ``freq='1H'`` and
``fillna(method='ffill')`` still work behind a warning nobody reads. A clean install
resolved pandas 3.0.5 and the same tree gave 57 failures and 33 errors — in test
fixtures, in doc examples, and in ``clean_ohlcv_data`` itself. This guard reddens
on the shapes that broke, so a deprecation does not have to be read to be acted on.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Offset aliases pandas 2.2 deprecated and 3.0 rejects, at the places they reach pandas directly.
REMOVED_ALIAS_TO_PANDAS = re.compile(
    r"""(?:freq\s*=|\.resample\(|\.asfreq\(|to_offset\()\s*['"]\d*(?:H|T|S|L|U|N|M|Q|Y|A)['"]"""
)
# The same aliases handed to the package's own resampler and continuity check. Those translate
# the project convention (m/h/d/w/M) before pandas sees it, so '1M' is fine there; uppercase
# H/T/S/L/U/N are not project units and go through to pandas unchanged.
REMOVED_ALIAS_TO_OURS = re.compile(
    r"""(?:resample_ohlcv\([^,]+,|target_timeframe\s*=|expected_frequency\s*=)"""
    r"""\s*['"]\d*(?:H|T|S|L|U|N)['"]"""
)
FILLNA_METHOD = re.compile(r"\.fillna\([^)]*\bmethod\s*=")

PATTERNS = (REMOVED_ALIAS_TO_PANDAS, REMOVED_ALIAS_TO_OURS, FILLNA_METHOD)


def offences(text: str):
    found = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(pattern.search(line) for pattern in PATTERNS):
            found.append((lineno, line.strip()))
    return found


def _scanned_files():
    listed = subprocess.run(
        ["git", "ls-files", "bquant/*.py", "tests/*.py", "examples/*.py",
         "research/*.py", "scripts/*.py", "docs/*.md"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.split()
    here = Path(__file__).resolve()
    return [REPO / p for p in listed if (REPO / p).resolve() != here]


def test_no_file_hands_pandas_an_alias_it_no_longer_accepts():
    hits = []
    for path in _scanned_files():
        if not path.exists():
            # Listed in the index but gone from the worktree (deleted, not yet
            # staged): nothing to scan.
            continue
        for lineno, line in offences(path.read_text(encoding="utf-8")):
            hits.append(f"{path.relative_to(REPO)}:{lineno}: {line}")
    assert not hits, "\n".join(hits)


@pytest.mark.parametrize(
    "snippet",
    [
        "idx = pd.date_range('2024-01-01', periods=3, freq='1H')",
        'idx = pd.date_range("2024-01-01", periods=3, freq="H")',
        "bars = df.resample('4H').agg(rules)",
        "bars = df.resample('1M').last()",
        "df = df.fillna(method='ffill')",
        "bars = resample_ohlcv(df, '4H')",
        "bars = resample_ohlcv(df, target_timeframe='4H')",
        "report = validate_time_series_continuity(df, expected_frequency='1H')",
    ],
)
def test_the_guard_reddens_on_the_shapes_that_broke(snippet):
    assert offences(snippet)


@pytest.mark.parametrize(
    "snippet",
    [
        "idx = pd.date_range('2024-01-01', periods=3, freq='1h')",
        "bars = df.resample('4h').agg(rules)",
        "bars = df.resample('1ME').last()",
        "df = df.ffill()",
        "timeframe = '1M'  # project convention, translated by pandas_offset_alias",
        "bars = resample_ohlcv(df, '4h')",
        "bars = resample_ohlcv(df, '1M')",
    ],
)
def test_the_guard_stays_quiet_on_the_replacements(snippet):
    assert not offences(snippet)
