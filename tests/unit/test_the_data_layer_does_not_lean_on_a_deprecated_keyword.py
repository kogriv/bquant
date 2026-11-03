"""The data layer does not use what pandas 4 will take away (G88).

pandas 3.1.0 started printing ``Pandas4Warning`` on the suite: ``inplace=`` in
``dropna``/``set_index``/``rename`` (PDEP-8 — the keyword goes away in pandas 4) in
``data/loader.py`` and ``data/processor.py``, and ``infer_freq`` announcing that it will
return an offset object instead of a string in ``data/validator.py``. Thirteen lines on
the pandas-3 arm of the 2026-11-03 run, none on pandas 2. A warning about a keyword's
removal is a future refusal with a date on it, not noise.

Two guards, because the two halves fail differently:

* **static** — no ``inplace=`` keyword anywhere in the package; works on every pandas
  and goes red the moment one is written back;
* **runtime** — on a pandas that has ``Pandas4Warning``, the loader, the processor's
  cleaning/resampling/preparation and the continuity validator run with that warning
  turned into an error. On older pandas the class does not exist and the check is
  skipped by name, not silently green.
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

import pandas as pd
import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "bquant"


def _inplace_calls():
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and any(k.arg == "inplace" for k in node.keywords):
                found.append(f"{path.relative_to(PACKAGE.parent)}:{node.lineno}")
    return found


def test_no_call_in_the_package_passes_inplace():
    assert _inplace_calls() == [], "PDEP-8: reassign the result instead:\n  " + "\n  ".join(_inplace_calls())


Pandas4Warning = getattr(pd.errors, "Pandas4Warning", None)


@pytest.mark.skipif(Pandas4Warning is None, reason="this pandas has no Pandas4Warning: nothing to turn into an error")
def test_the_data_layer_runs_clean_under_pandas4_warnings_as_errors(tmp_path):
    from bquant.data import (
        clean_ohlcv_data,
        load_ohlcv_data,
        prepare_data_for_analysis,
        resample_ohlcv,
        validate_time_series_continuity,
    )
    from bquant.data.samples import get_sample_data

    data = get_sample_data("tv_xauusd_1h")
    csv = tmp_path / "sample.csv"
    data.head(300).to_csv(csv)

    with warnings.catch_warnings():
        warnings.simplefilter("error", Pandas4Warning)
        loaded = load_ohlcv_data(csv)
        cleaned = clean_ohlcv_data(loaded)
        resampled = resample_ohlcv(cleaned, "4h")
        prepared = prepare_data_for_analysis(cleaned, target_column="close")
        continuity = validate_time_series_continuity(cleaned)

    assert len(loaded) == 300 and len(cleaned) <= 300
    assert 0 < len(resampled) < len(cleaned)
    assert len(prepared) > 0
    assert continuity["detected_frequency"] in ("h", "H"), continuity["detected_frequency"]
