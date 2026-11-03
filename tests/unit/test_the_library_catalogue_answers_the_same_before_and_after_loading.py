"""`get_library_info` answers the same question the same way, loaded or not (G90).

Discovery collects every callable of `pandas_ta` — 246 names, classes and helpers among
them (`AnalysisIndicators`, `Study`, `above`) — and used to publish that list as the
library's "available indicators". Registration filtered it to the 158 that are
indicators and overwrote the same list. So `get_library_info('pandas_ta')` reported 246
in a fresh process and 158 after anything had loaded the library; the documented example
promised 158 and, run on its own, printed 246 — a claim written under the call, which
the docs runner does not check. Found by a sweep of such claims, 2026-11-03.

Each check runs in a fresh process: the registry and the loader cache are process-wide,
and "fresh" is exactly the state that answered wrong.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PROBE = """
import json
from bquant.indicators import LibraryManager, IndicatorFactory
cold = LibraryManager.get_library_info('pandas_ta')
registry_after_cold = sum(1 for k in IndicatorFactory._registry if k.startswith('pandas_ta_'))   # not list_indicators(): it loads lazily (G64)
LibraryManager.load_all_libraries()
warm = LibraryManager.get_library_info('pandas_ta')
library = sorted(k[len('pandas_ta_'):] for k, v in IndicatorFactory.list_indicators().items()
                 if v == 'library' and k.startswith('pandas_ta_'))
print("<<<" + json.dumps({"cold": cold, "warm": warm, "registry_after_cold": registry_after_cold,
                          "library": library}))
"""


@pytest.fixture(scope="module")
def answers():
    pytest.importorskip("pandas_ta")
    run = subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, run.stderr[-2000:]
    line = next(l for l in run.stdout.splitlines() if l.startswith("<<<"))
    return json.loads(line[3:])


def test_the_cold_and_the_warm_answer_are_the_same(answers):
    assert answers["cold"]["indicators_count"] == answers["warm"]["indicators_count"]
    assert answers["cold"]["indicators"] == answers["warm"]["indicators"]


def test_the_list_holds_indicators_not_every_callable(answers):
    names = set(answers["cold"]["indicators"])
    assert not names & {"AnalysisIndicators", "Study", "above", "above_value"}, sorted(names & {"AnalysisIndicators", "Study", "above"})
    assert {"rsi", "macd", "zigzag"} <= names


def test_asking_does_not_register(answers):
    assert answers["registry_after_cold"] == 0, "get_library_info must not load the library as a side effect"


def test_the_published_list_is_what_the_factory_can_create(answers):
    lowered = sorted(n.lower() for n in answers["warm"]["indicators"])
    assert lowered == answers["library"]
