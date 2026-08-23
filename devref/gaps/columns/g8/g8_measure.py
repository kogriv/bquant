#!/usr/bin/env python3
"""G8 measurement — what the output-column contract actually does today.

The registry records G8 as "inconsistent naming of output columns: custom RSI ->
`rsi_14`, MACD -> `macd/macd_signal/macd_hist`". That is true but it is the mildest
of three defects that share one root, and this script measures all three so the
design decision is made against numbers rather than impressions.

Root cause: a column name is asked to carry two unrelated things at once —
*identity* (which indicator instance produced this series) and *role* (what the
series means) — and nothing owns the mapping between them. Every producer invents a
string; every consumer guesses one.

The three observable consequences:

  D1  Three naming conventions.
        name + period      : sma_20, ema_20, rsi_14
        name, no period    : macd, macd_signal, macd_hist
        abbreviated name   : bb_upper, bb_middle, ... (indicator is "bbands")
      Consequence: the period is not recoverable from the column, so two instances
      of the same indicator with different parameters claim the same name.

  D2  Silent overwrite at the pipeline merge point (pipeline.py:294-295):
          for col in result.data.columns:
              df_with_indicator[col] = result.data[col]
      Unconditional assignment. The bundled TradingView sample already carries its
      own `macd` column, so computing MACD replaces the user's data with no warning.

  D3  Library columns are labelled with the WRONG parameters
      (library/pandas_ta.py:409: `result_df.columns = output_columns`).
      `output_columns` is computed once at registration time, on synthetic data, with
      DEFAULT parameters, then reused for every later call. pandas-ta itself names
      the result correctly — bquant overwrites that name. The values are right; the
      label lies. This is the worst of the three: `macd_hist` is merely silent about
      its parameters, `RSI_14` actively misstates them.

Run:
    venv_bquant/bin/python devref/gaps/columns/g8/g8_measure.py
    venv_bquant/bin/python devref/gaps/columns/g8/g8_measure.py --json
"""
from __future__ import annotations

import argparse
import json
import logging
import os

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

logging.getLogger("bquant").setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

import pandas as pd

from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory, LibraryManager

DATASET = "tv_xauusd_1h"

# (factory name, kwargs) pairs covering every custom indicator that ships.
CUSTOM_CASES = [
    ("sma", {"period": 20}),
    ("ema", {"period": 20}),
    ("rsi", {"period": 14}),
    ("macd", {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
    ("bbands", {"period": 20}),
]


def _columns_of(name: str, params: dict, data: pd.DataFrame) -> list:
    return IndicatorFactory.create("custom", name, **params).calculate(data).data.columns.tolist()


def measure_d1_conventions(data: pd.DataFrame) -> dict:
    """D1 — classify each indicator's naming convention, and show parameter loss."""
    conventions = {}
    for name, params in CUSTOM_CASES:
        cols = _columns_of(name, params, data)
        # Does any parameter value appear in any column name?
        encoded = any(str(v) in c for c in cols for v in params.values())
        conventions[name] = {
            "params": params,
            "columns": cols,
            "encodes_parameters": encoded,
            "name_matches_column_prefix": all(c.startswith(name) for c in cols),
        }

    # Parameter loss is only observable by varying a parameter and comparing names.
    collisions = {}
    for name, variants in [
        ("rsi", [{"period": 14}, {"period": 21}]),
        ("macd", [
            {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            {"fast_period": 5, "slow_period": 35, "signal_period": 5},
        ]),
        ("bbands", [{"period": 20}, {"period": 50}]),
    ]:
        seen = [_columns_of(name, v, data) for v in variants]
        collisions[name] = {
            "variants": variants,
            "columns": seen,
            "collides": seen[0] == seen[1],
        }
    return {"conventions": conventions, "parameter_collisions": collisions}


def measure_d2_overwrite(data: pd.DataFrame) -> dict:
    """D2 — quantify the silent overwrite of the input frame's own columns."""
    incoming = set(data.columns)
    findings = {}
    for name, params in CUSTOM_CASES:
        cols = _columns_of(name, params, data)
        clashing = sorted(set(cols) & incoming)
        entry = {"columns": cols, "clashes_with_input": clashing}
        if clashing:
            # Reproduce the merge exactly as pipeline.py does, then measure the damage.
            result = IndicatorFactory.create("custom", name, **params).calculate(data)
            merged = data.copy()
            for col in result.data.columns:
                merged[col] = result.data[col]
            entry["max_abs_change"] = {
                col: float((merged[col] - data[col]).abs().max()) for col in clashing
            }
        findings[name] = entry

    # Two instances of one indicator overwriting each other in a shared frame.
    frame = data.copy()
    trace = []
    for fs in ((12, 26, 9), (5, 35, 5)):
        r = IndicatorFactory.create(
            "custom", "macd",
            fast_period=fs[0], slow_period=fs[1], signal_period=fs[2],
        ).calculate(data)
        for col in r.data.columns:
            frame[col] = r.data[col]
        trace.append({"params": fs, "macd_hist_last": float(frame["macd_hist"].iloc[-1])})
    findings["_self_overwrite"] = {
        "trace": trace,
        "surviving_macd_columns": [c for c in frame.columns if c.startswith("macd")],
        "first_instance_recoverable": False,
    }
    return findings


def measure_d3_mislabelled_library(data: pd.DataFrame) -> dict:
    """D3 — library columns carry the parameters the indicator was REGISTERED with."""
    try:
        import pandas_ta as ta
    except Exception as exc:  # pragma: no cover - environment without pandas_ta
        return {"skipped": f"pandas_ta unavailable: {exc}"}

    LibraryManager.load_all_libraries()
    findings = {}
    for length in (14, 21, 50):
        via = LibraryManager.create_indicator("pandas_ta", "rsi", length=length).calculate(data)
        col = via.data.columns[0]
        direct = ta.rsi(data["close"], length=length)
        findings[f"rsi_length_{length}"] = {
            "bquant_column_name": col,
            "pandas_ta_own_name": direct.name,
            "label_correct": col == direct.name,
            # The values are computed with the requested parameter even though the
            # label says otherwise — this is a naming defect, not a wrong-result one.
            "values_match_requested_length": bool(
                abs(float(via.data[col].iloc[-1]) - float(direct.iloc[-1])) < 1e-9
            ),
        }
    return findings


def measure_declared_vs_actual(data: pd.DataFrame) -> dict:
    """Unenforced contract: get_output_columns() vs the columns calculate() emits.

    Each indicator states its columns in `get_output_columns()` and then rebuilds the
    same literals inside `calculate()`. Nothing checks that the two agree, so they can
    drift silently. Measured here so the refactor starts from a known-consistent base.
    """
    out = {}
    for name, params in CUSTOM_CASES:
        ind = IndicatorFactory.create("custom", name, **params)
        declared = ind.get_output_columns()
        actual = ind.calculate(data).data.columns.tolist()
        out[name] = {"declared": declared, "actual": actual, "match": declared == actual}
    return out


def measure_impact_radius() -> dict:
    """Where hardcoded column names live, so the refactor cost is measured not guessed."""
    import subprocess

    patterns = "'macd_hist'|'macd_signal'|'bb_upper'|'rsi_14'|'sma_20'"
    areas = {
        "bquant (package)": "bquant",
        "tests": "tests",
        "docs": "docs",
        "examples": "examples",
        "research": "research",
        "devref (history — do not rewrite)": "devref",
        "changelogs (history — do not rewrite)": "changelogs",
    }
    radius = {}
    for label, path in areas.items():
        try:
            out = subprocess.run(
                ["grep", "-rEn", patterns, path],
                capture_output=True, text=True, timeout=60,
            ).stdout
            lines = [l for l in out.splitlines() if "_build" not in l]
            files = {l.split(":", 1)[0] for l in lines}
            radius[label] = {"occurrences": len(lines), "files": len(files)}
        except Exception as exc:  # pragma: no cover
            radius[label] = {"error": str(exc)}
    return radius


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit raw JSON")
    args = parser.parse_args()

    data = get_sample_data(DATASET)
    report = {
        "dataset": DATASET,
        "input_columns": data.columns.tolist(),
        "D1_naming_conventions": measure_d1_conventions(data),
        "D2_silent_overwrite": measure_d2_overwrite(data),
        "D3_mislabelled_library_columns": measure_d3_mislabelled_library(data),
        "declared_vs_actual": measure_declared_vs_actual(data),
        "impact_radius": measure_impact_radius(),
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print(f"dataset: {DATASET}")
    print(f"input columns: {report['input_columns']}\n")

    print("D1 — naming conventions")
    for name, info in report["D1_naming_conventions"]["conventions"].items():
        flag = "params encoded" if info["encodes_parameters"] else "PARAMS LOST"
        print(f"  {name:7s} {info['params']}")
        print(f"  {'':7s} -> {info['columns']}  [{flag}]")
    print("\n  same indicator, different parameters:")
    for name, info in report["D1_naming_conventions"]["parameter_collisions"].items():
        mark = "COLLIDE" if info["collides"] else "distinct"
        print(f"    {name:7s} {info['columns'][0]} vs {info['columns'][1]}  [{mark}]")

    print("\nD2 — silent overwrite of the input frame")
    for name, info in report["D2_silent_overwrite"].items():
        if name.startswith("_"):
            continue
        if info["clashes_with_input"]:
            dmg = ", ".join(f"{c}: max|Δ|={v:.4f}" for c, v in info["max_abs_change"].items())
            print(f"  {name:7s} OVERWRITES {info['clashes_with_input']}  ({dmg})")
        else:
            print(f"  {name:7s} no clash")
    so = report["D2_silent_overwrite"]["_self_overwrite"]
    print("  two MACD instances into one frame:")
    for t in so["trace"]:
        print(f"    after macd{t['params']}: macd_hist[-1] = {t['macd_hist_last']:.4f}")
    print(f"    surviving columns: {so['surviving_macd_columns']} -> first instance lost")

    print("\nD3 — library columns labelled with registration-time parameters")
    d3 = report["D3_mislabelled_library_columns"]
    if "skipped" in d3:
        print(f"  {d3['skipped']}")
    else:
        for key, info in d3.items():
            mark = "ok" if info["label_correct"] else "MISLABELLED"
            print(f"  {key:15s} bquant={info['bquant_column_name']:8s} "
                  f"pandas_ta={info['pandas_ta_own_name']:8s} [{mark}] "
                  f"values_correct={info['values_match_requested_length']}")

    print("\ndeclared get_output_columns() vs actual calculate()")
    for name, info in report["declared_vs_actual"].items():
        print(f"  {name:7s} {'MATCH' if info['match'] else 'MISMATCH'}")

    print("\nimpact radius (hardcoded column names)")
    for label, info in report["impact_radius"].items():
        if "error" in info:
            print(f"  {label:36s} error: {info['error']}")
        else:
            print(f"  {label:36s} {info['occurrences']:4d} occurrences in {info['files']:3d} files")


if __name__ == "__main__":
    main()
