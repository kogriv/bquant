"""``python -m bquant`` is an entry point, not a second implementation.

Until 0.0.19 the form exited rc 1 with ``No module named bquant.__main__``, which reads
as a broken package rather than an unsupported invocation. It is the form people reach
for when the console script is not on PATH.

The second test is the one that matters over time: the module must *delegate*, never
carry its own copy of the argument parsing. A second literal that has to stay in step
with the first is the defect this project has closed three times (G8, G32, G33).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import bquant.__main__ as module_entry
from bquant.cli import build_parser, main as cli_main

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_module_entry_point_runs_and_prints_the_same_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "bquant", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stderr[-500:]

    usage_line = build_parser().format_usage().strip()
    assert usage_line.splitlines()[0] in completed.stdout


def test_the_module_delegates_instead_of_reimplementing() -> None:
    assert module_entry.main is cli_main

    source = (PROJECT_ROOT / "bquant" / "__main__.py").read_text(encoding="utf-8")
    assert "argparse" not in source, "the parser lives in bquant.cli and nowhere else"
    assert "add_argument" not in source
