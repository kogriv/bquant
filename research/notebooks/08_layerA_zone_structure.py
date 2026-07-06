"""Слой A — Структура и классы завершённых зон MACD (дескриптивная статистика).

Первый шаг слоя A программы `research/methodology/swing_structure_research_program.md`.

ЦЕЛЬ: описать завершённые зоны как траектории свингов (направленно-нормированно:
bull → импульс=rally, bear → импульс=drop) и найти устойчивые архетипы (A1), их
торговую различимость (A2), масштаб с длиной (A3), профиль импульса по классам (A4).
Фундамент под слой B (прогнозируемость).

ЭКСТРАКТОР k-НАРЕЗАЕМЫЙ: `zone_descriptors(zone, prefix_bars=None)` считает дескрипторы
либо на всей зоне (A), либо на префиксе первых k баров (задел под B, без утечки будущего).

НЕ бэктест: harvest/max_adverse — статистики структуры, не симулированный P&L.

Запуск:
    python research/notebooks/08_layerA_zone_structure.py --no-trap
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from bquant.core.config import PROJECT_ROOT
from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

setup_logging(profile="research")

DATASETS = ["tv_xauusd_1h", "mt_xauusd_m15"]
OUT_DIR = PROJECT_ROOT / "research" / "notebooks" / "outputs" / "layerA_zone_structure"

# Дескрипторы, идущие в кластеризацию A1 (направленно-нормированные).
CLUSTER_FEATURES = [
    "num_legs", "imp_counter_ratio", "harvest", "max_impulse",
    "max_impulse_rel", "median_counter", "impulse_decay_slope", "macd_shape_skew",
]


def zone_descriptors(zone, prefix_bars: Optional[int] = None) -> Optional[Dict]:
    """Направленно-нормированные структурные дескрипторы зоны.

    prefix_bars=None → вся зона (слой A); иначе — префикс первых k баров (слой B).
    Импульс = нога в направлении зоны (rally для bull, drop для bear); контр = откат.
    """
    fav_up = zone.type == "bull"
    start, end = zone.start_idx, zone.end_idx
    cutoff = end if prefix_bars is None else min(end, start + prefix_bars)
    span = max(1, end - start)

    legs = []  # (rel_time, abs_amp, is_impulse, dur)
    for sp in zone.get_zone_swings():
        if sp.index < start or sp.index > cutoff or sp.amplitude_to_next is None:
            continue
        amp = float(sp.amplitude_to_next)
        is_impulse = (amp > 0) == fav_up
        rel = float(np.clip((sp.index - start) / span, 0.0, 1.0))
        legs.append((rel, abs(amp), is_impulse, sp.duration_to_next))

    imp = [l for l in legs if l[2]]
    cnt = [l for l in legs if not l[2]]
    if len(imp) < 2 or len(cnt) < 1:
        return None  # слишком мало структуры для дескрипторов

    harvest = float(sum(l[1] for l in imp))
    counter_sum = float(sum(l[1] for l in cnt))
    max_imp = max(l[1] for l in imp)
    max_imp_rel = float([l[0] for l in imp if l[1] == max_imp][0])
    # наклон затухания импульса: abs(импульс) ~ rel_time
    xi = np.array([l[0] for l in imp]); yi = np.array([l[1] for l in imp])
    slope = float(np.polyfit(xi, yi, 1)[0]) if len(imp) >= 3 else np.nan

    # форма кривой MACD-линии внутри зоны (skew/kurtosis)
    macd_seg = zone.data["macd"].to_numpy()[: cutoff - start + 1] if "macd" in zone.data else None
    sk = float(skew(macd_seg)) if macd_seg is not None and len(macd_seg) > 3 else np.nan
    ku = float(kurtosis(macd_seg)) if macd_seg is not None and len(macd_seg) > 3 else np.nan

    return {
        "zone_id": zone.zone_id, "ztype": zone.type, "duration": int(zone.duration),
        "num_legs": len(legs), "num_impulse": len(imp), "num_counter": len(cnt),
        "harvest": harvest, "counter_sum": counter_sum,
        "imp_counter_ratio": harvest / counter_sum if counter_sum > 0 else np.nan,
        "max_impulse": max_imp, "max_impulse_rel": max_imp_rel,
        "median_counter": float(np.median([l[1] for l in cnt])),
        "max_adverse": float(max(l[1] for l in cnt)),
        "impulse_decay_slope": slope,
        "macd_shape_skew": sk, "macd_shape_kurt": ku,
    }


def build_table() -> pd.DataFrame:
    rows = []
    for ds in DATASETS:
        df = get_sample_data(ds)
        # narrow_zone preset: дефолтный zigzag (dev 5%) даёт свинги лишь в 31% зон;
        # narrow_zone поднимает до 70% (медиана ног 6->13) — структурному анализу
        # нужна плотность свингов (как и в прежних case-study).
        r = (
            analyze_zones(df).with_indicator("custom", "macd")
            .detect_zones("zero_crossing", indicator_col="macd", min_duration=2)
            .with_strategies(swing="zigzag").with_swing_scope("global")
            .with_swing_preset("narrow_zone")
            .analyze(clustering=False).build()
        )
        for z in r.zones:
            d = zone_descriptors(z)
            if d is not None:
                d["dataset"] = ds
                rows.append(d)
    return pd.DataFrame(rows)


def main() -> None:
    nb = NotebookSimulator("Слой A — структура и классы зон MACD")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Step 1: descriptor table ------------------------------------------ #
    nb.step("Шаг 1. Дескрипторы завершённых зон (bull+bear, direction-normalized)")
    with nb.error_handling("build table"):
        T = build_table()
        nb.data_info("зон с достаточной структурой", len(T))
        for ds in DATASETS:
            sub = T[T.dataset == ds]
            nb.data_info(f"  {ds}", f"{len(sub)} зон (bull {sum(sub.ztype=='bull')} / bear {sum(sub.ztype=='bear')})")
        T.to_csv(OUT_DIR / "zone_descriptors.csv", index=False)
        nb.success(f"Saved {(OUT_DIR/'zone_descriptors.csv').relative_to(PROJECT_ROOT)}")
    nb.wait()

    # --- Step 2: A1 clustering --------------------------------------------- #
    nb.step("Шаг 2. A1 — кластеризация в архетипы (пул bull+bear, оба датасета)")
    labels = None
    with nb.error_handling("clustering"):
        C = T.dropna(subset=CLUSTER_FEATURES).copy()
        X = StandardScaler().fit_transform(C[CLUSTER_FEATURES].to_numpy())
        nb.data_info("зон в кластеризации (без NaN)", len(C))
        best = None
        for k in range(2, 6):
            if len(C) <= k:
                continue
            km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
            sil = silhouette_score(X, km.labels_)
            nb.info(f"  k={k}: silhouette={sil:.3f}")
            if best is None or sil > best[1]:
                best = (k, sil, km)
        k, sil, km = best
        C["cluster"] = km.labels_
        labels = C
        nb.summary_item("Выбрано кластеров (max silhouette)", f"k={k} (sil={sil:.3f})")
        # состав кластеров по датасету и направлению (репликация + асимметрия)
        for cl in sorted(C.cluster.unique()):
            g = C[C.cluster == cl]
            comp_ds = "/".join(f"{ds}:{sum(g.dataset==ds)}" for ds in DATASETS)
            nb.info(f"  cluster {cl}: n={len(g)} | bull {sum(g.ztype=='bull')} bear {sum(g.ztype=='bear')} | {comp_ds}")
    nb.wait()

    # --- Step 3: A2 distinguishability ------------------------------------- #
    nb.step("Шаг 3. A2 — портрет кластеров (торговая различимость)")
    with nb.error_handling("cluster profiles"):
        prof = labels.groupby("cluster")[
            ["num_legs", "harvest", "imp_counter_ratio", "max_impulse",
             "max_impulse_rel", "median_counter", "max_adverse",
             "impulse_decay_slope", "duration"]
        ].median().round(3)
        nb.log(prof.to_string())
    nb.wait()

    # --- Step 4: A3 scale with length -------------------------------------- #
    nb.step("Шаг 4. A3 — масштаб структуры с длиной зоны (Spearman)")
    with nb.error_handling("scale with length"):
        from scipy.stats import spearmanr
        for col in ["num_legs", "harvest", "max_impulse", "imp_counter_ratio"]:
            rho, p = spearmanr(T["duration"], T[col], nan_policy="omit")
            nb.info(f"  duration vs {col:18}: rho={rho:+.3f} p={p:.3f}")
    nb.wait()

    # --- Step 5: A4 decay profile per cluster ------------------------------ #
    nb.step("Шаг 5. A4 — профиль затухания импульса по классам")
    with nb.error_handling("decay per cluster"):
        for cl in sorted(labels.cluster.unique()):
            g = labels[labels.cluster == cl]
            nb.info(f"  cluster {cl}: median impulse_decay_slope={g.impulse_decay_slope.median():+.3f} "
                    f"(neg = импульс затухает к концу)")
    nb.wait()

    # --- Step 6: persist --------------------------------------------------- #
    nb.step("Шаг 6. Сохранение меток классов (вход для слоя B)")
    with nb.error_handling("persist"):
        labels[["dataset", "zone_id", "ztype", "cluster"]].to_csv(
            OUT_DIR / "zone_classes.csv", index=False)
        nb.success(f"Saved {(OUT_DIR/'zone_classes.csv').relative_to(PROJECT_ROOT)}")
        nb.next_steps([
            "A: перепроверить устойчивость k между датасетами (репликация архетипов).",
            "B: k-нарезаемый прогноз класса/структуры (приор + частичное на баре k),",
            "   кривая информации, honest survivorship.",
        ])
    nb.finish("Layer A (structure + classes) completed.")


if __name__ == "__main__":
    main()
