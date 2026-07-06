"""S1 — Анатомия свингов внутри зон MACD (структура: позиция + последовательность).

Первый шаг программы `research/methodology/swing_structure_research_program.md`.

ЦЕЛЬ (этап методологии, НЕ альфа): охарактеризовать структуру свингов внутри зон
MACD — какие свинги (rally/drop), какой амплитуды/длительности, и ГДЕ внутри зоны
(позиция) они происходят. Работаем сразу со структурой (наивную свёрнутую метрику
зоны не считаем).

ОПЕРАЦИОННЫЙ СПЕК S1 (согласованные решения):
* Зона MACD детектируется по ЛИНИИ MACD (`indicator_col='macd'`), не по гистограмме
  (методология проекта; длинные стабильные зоны). min_duration=2.
* Свинги: `zigzag` + `global` scope.
* Единица анализа — НОГА свинга (rally/drop) = движение между двумя соседними
  глобальными пивотами; относится к зоне, если её СТАРТОВЫЙ пивот лежит внутри
  [start_idx, end_idx] (индексы позиционные iloc в полном датасете). Паддинг
  соседей из `get_zone_swings()` отфильтровывается по этому правилу.
* Метрики ноги: direction (rally/drop по знаку amplitude_to_next), amplitude_pct
  (|amplitude_to_next|), duration_bars (duration_to_next), rel_time (позиция
  стартового пивота в зоне 0..1 по индексу бара), rel_price (позиция цены
  стартового пивота в реализованном диапазоне зоны 0..1).
* Дисциплина малых n: effect size (Cliff's delta) + bootstrap CI + репликация
  1h<->m15 + null-модель (внутризонная перестановка позиций).

Запуск:
    python research/notebooks/07_s1_swing_anatomy.py --no-trap
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

from bquant.core.config import PROJECT_ROOT
from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

setup_logging(profile="research")

DATASETS = ["tv_xauusd_1h", "mt_xauusd_m15"]
OUT_DIR = PROJECT_ROOT / "research" / "notebooks" / "outputs" / "s1_swing_anatomy"
RNG = np.random.default_rng(20260706)


# --------------------------------------------------------------------------- #
# Extraction: per-swing (per-leg) table
# --------------------------------------------------------------------------- #
def build_swing_table(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """Explode MACD-line zones into individual swing legs with in-zone position."""

    result = (
        analyze_zones(df)
        .with_indicator("custom", "macd")
        .detect_zones("zero_crossing", indicator_col="macd", min_duration=2)
        .with_strategies(swing="zigzag")
        .with_swing_scope("global")
        .analyze(clustering=False)
        .build()
    )

    rows: List[Dict] = []
    for zone in result.zones:
        span = max(1, zone.end_idx - zone.start_idx)
        low_min = float(zone.data["low"].min())
        high_max = float(zone.data["high"].max())
        price_range = high_max - low_min if high_max > low_min else np.nan

        # Global swings sliced for this zone (with neighbor padding).
        swings = zone.get_zone_swings()
        order = 0
        for sp in swings:
            # Keep only legs whose STARTING pivot lies inside the zone.
            if sp.index < zone.start_idx or sp.index > zone.end_idx:
                continue
            if sp.amplitude_to_next is None:
                continue

            amp = float(sp.amplitude_to_next)
            rel_time = np.clip((sp.index - zone.start_idx) / span, 0.0, 1.0)
            rel_price = (
                np.clip((sp.price - low_min) / price_range, 0.0, 1.0)
                if price_range and not np.isnan(price_range)
                else np.nan
            )
            rows.append(
                {
                    "dataset": dataset,
                    "zone_id": zone.zone_id,
                    "zone_type": zone.type,
                    "zone_duration": zone.duration,
                    "swing_order": order,
                    "direction": "rally" if amp > 0 else "drop",
                    "amplitude_pct": abs(amp),
                    "duration_bars": sp.duration_to_next,
                    "rel_time": float(rel_time),
                    "rel_price": float(rel_price) if rel_price == rel_price else np.nan,
                }
            )
            order += 1

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Small-n statistics helpers (no extra deps)
# --------------------------------------------------------------------------- #
def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Cliff's delta effect size in [-1, 1]. >0 means a tends to exceed b."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    return float(np.sign(a[:, None] - b[None, :]).mean())


def bootstrap_ci_median_diff(
    a: np.ndarray, b: np.ndarray, n_boot: int = 2000, alpha: float = 0.05
) -> tuple:
    """Bootstrap CI for median(a) - median(b)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return (float("nan"), float("nan"))
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        ra = RNG.choice(a, size=len(a), replace=True)
        rb = RNG.choice(b, size=len(b), replace=True)
        diffs[i] = np.median(ra) - np.median(rb)
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))


def position_null_test(
    table: pd.DataFrame, zone_type: str, direction: str, n_perm: int = 2000
) -> Dict[str, float]:
    """Permutation test: does swing amplitude depend on in-zone position?

    Statistic = Spearman corr(rel_time, amplitude_pct). Null = shuffle rel_time
    WITHIN each zone (breaks the position<->amplitude link, preserves per-zone
    amplitude set and swing count).
    """
    sub = table[(table.zone_type == zone_type) & (table.direction == direction)]
    sub = sub.dropna(subset=["rel_time", "amplitude_pct"])
    if len(sub) < 5:
        return {"n": len(sub), "rho": float("nan"), "p_perm": float("nan")}

    obs = spearmanr(sub["rel_time"], sub["amplitude_pct"]).correlation
    groups = [g["rel_time"].to_numpy() for _, g in sub.groupby("zone_id")]
    amp = sub["amplitude_pct"].to_numpy()
    zone_index = sub.groupby("zone_id").ngroup().to_numpy()

    count = 0
    for _ in range(n_perm):
        shuffled = np.empty_like(sub["rel_time"].to_numpy())
        for gi, g in enumerate(groups):
            perm = RNG.permutation(g)
            shuffled[zone_index == gi] = perm
        rho = spearmanr(shuffled, amp).correlation
        if abs(rho) >= abs(obs):
            count += 1
    return {"n": int(len(sub)), "rho": float(obs), "p_perm": (count + 1) / (n_perm + 1)}


def thirds_table(table: pd.DataFrame, zone_type: str) -> pd.DataFrame:
    """Mean amplitude and leg counts of rally/drop by early/mid/late third."""
    sub = table[table.zone_type == zone_type].copy()
    if sub.empty:
        return pd.DataFrame()
    sub["third"] = pd.cut(
        sub["rel_time"], [0, 1 / 3, 2 / 3, 1.0], labels=["early", "mid", "late"],
        include_lowest=True,
    )
    return (
        sub.groupby(["third", "direction"], observed=True)["amplitude_pct"]
        .agg(["count", "mean", "median"])
        .round(3)
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    nb = NotebookSimulator("S1 — Анатомия свингов внутри зон MACD")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tables: Dict[str, pd.DataFrame] = {}
    summary: Dict[str, dict] = {}

    # --- Step 1: data & framing --------------------------------------------- #
    nb.step("Шаг 1. Данные, определение зоны и рамка")
    with nb.error_handling("load and framing"):
        nb.info("Зоны детектируются по ЛИНИИ MACD (indicator_col='macd'), не по гистограмме.")
        nb.info("Единица анализа — нога свинга (rally/drop), зоны zigzag+global, min_duration=2.")
        for ds in DATASETS:
            df = get_sample_data(ds)
            nb.data_info(f"{ds}: bars", len(df))
    nb.wait()

    # --- Step 2: build per-swing dataset ------------------------------------ #
    nb.step("Шаг 2. Построение per-swing датасета")
    with nb.error_handling("build swing tables"):
        for ds in DATASETS:
            df = get_sample_data(ds)
            tbl = build_swing_table(df, ds)
            tables[ds] = tbl
            n_zones = tbl["zone_id"].nunique() if not tbl.empty else 0
            bull = tbl[tbl.zone_type == "bull"]
            bear = tbl[tbl.zone_type == "bear"]
            csv_path = OUT_DIR / f"per_swing_{ds}.csv"
            tbl.to_csv(csv_path, index=False)
            nb.data_info(f"{ds}: swing legs", len(tbl))
            nb.data_info(f"{ds}: zones with >=1 leg", n_zones)
            nb.data_info(f"{ds}: bull/bear legs", f"{len(bull)}/{len(bear)}")
            nb.success(f"Saved {csv_path.relative_to(PROJECT_ROOT)}")
    nb.wait()

    # --- Step 3: consistency contrast (rally vs drop) with effect size ------ #
    nb.step("Шаг 3. Состоятельность: rally vs drop амплитуда (effect size + CI)")
    with nb.error_handling("consistency contrast"):
        for ds in DATASETS:
            tbl = tables[ds]
            ds_summary = {}
            for zt in ("bull", "bear"):
                rally = tbl[(tbl.zone_type == zt) & (tbl.direction == "rally")]["amplitude_pct"].to_numpy()
                drop = tbl[(tbl.zone_type == zt) & (tbl.direction == "drop")]["amplitude_pct"].to_numpy()
                delta = cliffs_delta(rally, drop)
                ci = bootstrap_ci_median_diff(rally, drop)
                if len(rally) >= 3 and len(drop) >= 3:
                    p = float(mannwhitneyu(rally, drop, alternative="two-sided").pvalue)
                else:
                    p = float("nan")
                ds_summary[zt] = {
                    "n_rally": int(len(rally)), "n_drop": int(len(drop)),
                    "median_rally": float(np.median(rally)) if len(rally) else float("nan"),
                    "median_drop": float(np.median(drop)) if len(drop) else float("nan"),
                    "cliffs_delta_rally_vs_drop": delta,
                    "median_diff_ci95": ci, "mannwhitney_p": p,
                }
                nb.info(
                    f"[{ds}/{zt}] rally n={len(rally)} med={np.median(rally) if len(rally) else float('nan'):.3f} | "
                    f"drop n={len(drop)} med={np.median(drop) if len(drop) else float('nan'):.3f} | "
                    f"Cliff δ={delta:.3f} CI95(med diff)=[{ci[0]:.3f},{ci[1]:.3f}] p={p:.4f}"
                )
            summary.setdefault(ds, {})["consistency"] = ds_summary
    nb.wait()

    # --- Step 4: position analysis (thirds + rel_price) --------------------- #
    nb.step("Шаг 4. Позиция в зоне: rally/drop по третям (early/mid/late)")
    with nb.error_handling("position thirds"):
        for ds in DATASETS:
            for zt in ("bull", "bear"):
                t = thirds_table(tables[ds], zt)
                nb.info(f"[{ds}/{zt}] amplitude by third x direction:")
                nb.log(t.to_string() if not t.empty else "  (нет данных)")
    nb.wait()

    # --- Step 5: null model (is position structure non-random?) ------------- #
    nb.step("Шаг 5. Null-модель: зависит ли амплитуда от позиции (перестановка)")
    with nb.error_handling("position null test"):
        for ds in DATASETS:
            pos = {}
            for zt in ("bull", "bear"):
                for direction in ("rally", "drop"):
                    res = position_null_test(tables[ds], zt, direction)
                    pos[f"{zt}_{direction}"] = res
                    nb.info(
                        f"[{ds}/{zt}/{direction}] Spearman(rel_time,amp) rho={res['rho']:.3f} "
                        f"p_perm={res['p_perm']:.3f} (n={res['n']})"
                    )
            summary.setdefault(ds, {})["position_null"] = pos
    nb.wait()

    # --- Step 6: replication 1h <-> m15 ------------------------------------- #
    nb.step("Шаг 6. Репликация 1h <-> m15 (совпадает ли направление эффектов)")
    with nb.error_handling("replication"):
        for zt in ("bull", "bear"):
            deltas = {ds: summary[ds]["consistency"][zt]["cliffs_delta_rally_vs_drop"] for ds in DATASETS}
            agree = np.sign(deltas[DATASETS[0]]) == np.sign(deltas[DATASETS[1]])
            nb.summary_item(
                f"{zt}: Cliff δ (rally>drop) знак совпадает",
                f"{deltas[DATASETS[0]]:.3f} vs {deltas[DATASETS[1]]:.3f}",
                success=bool(agree),
            )
    nb.wait()

    # --- Step 7: persist summary + backlog ---------------------------------- #
    nb.step("Шаг 7. Сохранение сводки и backlog допила тулкита")
    with nb.error_handling("persist"):
        summary_path = OUT_DIR / "s1_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        nb.success(f"Saved {summary_path.relative_to(PROJECT_ROOT)}")
        nb.next_steps([
            "S1 backlog (toolkit): вынести per-swing позицию (rel_time/rel_price) в",
            "  переиспользуемый аналитический тул (сейчас считается ad-hoc в скрипте).",
            "S2: обусловить структуру свингов на класс формы зоны (кластеризация shape).",
            "S3: форвардная разметка 'откат vs конец зоны' для контр-свингов.",
        ])

    nb.finish("S1 swing anatomy completed.")


if __name__ == "__main__":
    main()
