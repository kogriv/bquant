"""The visualization package must not pull heavy libraries it does not call.

`bquant --help` took 3.95 s. Measured with `-X importtime`, the cost was not the CLI: it
was `bquant.visualization`, and inside it an `import plotly.figure_factory` that no line
in the package ever used — it drags the eager `plotly.graph_objs` tree behind it, 1.5 s.
Removing that one dead import took the command to 2.29 s.

Asserted as a **property, not a stopwatch**: a timing test passes or fails with machine
load, while "this module is not imported" is the same answer on a busy machine and an idle
one. Same reason `test_benchmark_global_vs_perzone` was replaced by counting tests.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Each name here was eagerly imported and cost measurable startup time for nothing.
#   plotly.figure_factory — never called anywhere in the package (1.5 s)
#   seaborn               — imported in five modules, called in two, both in statistical.py
FORBIDDEN_AT_IMPORT = ("plotly.figure_factory", "seaborn")


def _modules_after(import_line: str) -> set[str]:
    code = f"import sys; {import_line}; print('\\n'.join(sorted(sys.modules)))"
    completed = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT,
        capture_output=True, text=True, timeout=300,
        env={"MPLBACKEND": "Agg", "PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
    )
    assert completed.returncode == 0, completed.stderr[-600:]
    return set(completed.stdout.split())


@pytest.mark.parametrize("name", FORBIDDEN_AT_IMPORT)
def test_importing_visualization_does_not_load(name: str) -> None:
    loaded = _modules_after("import bquant.visualization")
    assert name not in loaded, f"{name} is imported eagerly again"


def test_the_probe_can_see_a_module_that_is_loaded() -> None:
    """Positive control: the check above would pass on a broken probe that sees nothing."""
    loaded = _modules_after("import bquant.visualization")
    assert "bquant.visualization" in loaded
    assert "plotly" in loaded, "plotly itself is a real dependency and must show up"


def test_seaborn_is_still_reachable_when_a_chart_needs_it() -> None:
    """Lazy must mean deferred, not dropped."""
    from bquant.visualization.statistical import _seaborn

    module = _seaborn()
    if module is None:
        pytest.skip("seaborn not installed in this environment")
    assert hasattr(module, "heatmap")
