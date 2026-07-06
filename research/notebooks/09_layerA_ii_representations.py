"""Слой A-ii — Multi-view классификация зон: сравнение представлений и методов.

Шаг A-ii программы `research/methodology/swing_structure_research_program.md`.
Метод-стек: `research/methodology/method_tool_stack.md`.

ИДЕЯ: зона — один объект на разных уровнях абстракции (лестница представлений):
  candle/price path → MACD-line path → swing-leg sequence.
Классифицируем на КАЖДОМ (multi-view) разными методами и меряем СОГЛАСИЕ партиций
(adjusted Rand index) — главный выход не «красивое разбиение», а робастность структуры
к выбору представления. На малых данных: только механика, без статвыводов.

Представления (direction-normalized: favorable-направление = вверх для bull и bear):
  * leg_seq   — последовательность знаковых амплитуд ног (импульс +, откат −), var-length → DTW
  * macd_path — путь MACD-линии в зоне, ресемпл к L → DTW + catch22
  * price_path— favorable-нормированный ценовой путь, ресемпл к L → DTW + catch22

Запуск:
    python research/notebooks/09_layerA_ii_representations.py --no-trap
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
import pycatch22
from tslearn.clustering import TimeSeriesKMeans
from tslearn.utils import to_time_series_dataset
from tslearn.preprocessing import TimeSeriesScalerMeanVariance

from bquant.core.config import PROJECT_ROOT
from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

setup_logging(profile="research")

DATASETS = ["tv_xauusd_1h", "mt_xauusd_m15"]
OUT_DIR = PROJECT_ROOT / "research" / "notebooks" / "outputs" / "layerA_ii_representations"
L = 24        # длина ресемпла путей
K = 3         # число кластеров (фикс. для сопоставимости методов)
MIN_LEGS = 3
MIN_BARS = 12


def _resample(series: np.ndarray, n: int = L) -> np.ndarray:
    series = np.asarray(series, float)
    if len(series) < 2:
        return np.full(n, series[0] if len(series) else 0.0)
    xp = np.linspace(0.0, 1.0, len(series))
    return np.interp(np.linspace(0.0, 1.0, n), xp, series)


def zone_views(zone) -> Optional[Dict]:
    """Три direction-normalized представления зоны на одном наборе зон."""
    fav_up = zone.type == "bull"
    start, end = zone.start_idx, zone.end_idx
    if end - start + 1 < MIN_BARS:
        return None

    # leg_seq: знаковые амплитуды (импульс +, откат −)
    legs = []
    for sp in zone.get_zone_swings():
        if sp.index < start or sp.index > end or sp.amplitude_to_next is None:
            continue
        amp = float(sp.amplitude_to_next)
        is_impulse = (amp > 0) == fav_up
        legs.append(abs(amp) if is_impulse else -abs(amp))
    if len(legs) < MIN_LEGS:
        return None

    d = zone.data
    sign = 1.0 if fav_up else -1.0
    macd_path = _resample(sign * d["macd"].to_numpy())
    c0 = float(d["close"].iloc[0])
    price_path = _resample(sign * (d["close"].to_numpy() / c0 - 1.0) * 100)

    return {
        "zone_id": zone.zone_id, "ztype": zone.type, "dataset": None,
        "leg_seq": np.asarray(legs, float),
        "macd_path": macd_path, "price_path": price_path,
    }


def build_views() -> List[Dict]:
    rows = []
    for ds in DATASETS:
        df = get_sample_data(ds)
        r = (
            analyze_zones(df).with_indicator("custom", "macd")
            .detect_zones("zero_crossing", indicator_col="macd", min_duration=2)
            .with_strategies(swing="zigzag").with_swing_scope("global")
            .with_swing_preset("narrow_zone").analyze(clustering=False).build()
        )
        for z in r.zones:
            v = zone_views(z)
            if v is not None:
                v["dataset"] = ds
                rows.append(v)
    return rows


def dtw_labels(seqs: List[np.ndarray], k: int = K) -> np.ndarray:
    # z-нормировка каждого ряда: убрать масштаб/датасет-конфаунд, кластеризовать ФОРМУ.
    ds = TimeSeriesScalerMeanVariance().fit_transform(to_time_series_dataset(seqs))
    km = TimeSeriesKMeans(n_clusters=k, metric="dtw", random_state=42, n_init=2)
    return km.fit_predict(ds)


def catch22_labels(paths: List[np.ndarray], k: int = K) -> np.ndarray:
    feats = np.array([pycatch22.catch22_all(p.tolist())["values"] for p in paths])
    feats = np.nan_to_num(feats)
    X = StandardScaler().fit_transform(feats)
    return KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)


def main() -> None:
    nb = NotebookSimulator("Слой A-ii — multi-view классификация зон")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    nb.step("Шаг 1. Три представления зон (ноги / MACD-путь / ценовой путь)")
    with nb.error_handling("build views"):
        V = build_views()
        nb.data_info("зон в анализе (общий набор для всех представлений)", len(V))
        for ds in DATASETS:
            nb.data_info(f"  {ds}", sum(1 for v in V if v["dataset"] == ds))
    nb.wait()

    nb.step("Шаг 2. Партиции: 5 разбиений (метод × представление)")
    partitions: Dict[str, np.ndarray] = {}
    with nb.error_handling("partitions"):
        partitions["DTW:leg_seq"] = dtw_labels([v["leg_seq"] for v in V])
        partitions["DTW:macd_path"] = dtw_labels([v["macd_path"] for v in V])
        partitions["DTW:price_path"] = dtw_labels([v["price_path"] for v in V])
        partitions["catch22:macd_path"] = catch22_labels([v["macd_path"] for v in V])
        partitions["catch22:price_path"] = catch22_labels([v["price_path"] for v in V])
        for name, lab in partitions.items():
            sizes = np.bincount(lab, minlength=K)
            nb.info(f"  {name:22} sizes={sizes.tolist()}")
    nb.wait()

    nb.step("Шаг 3. Согласие представлений — adjusted Rand index (главный выход)")
    with nb.error_handling("ARI matrix"):
        names = list(partitions.keys())
        nb.log("ARI (1.0 = идентичные разбиения, 0 = случайное совпадение):")
        header = "                       " + " ".join(f"{n.split(':')[0][:6]:>7}" for n in names)
        nb.log(header)
        for a in names:
            row = " ".join(f"{adjusted_rand_score(partitions[a], partitions[b]):>7.2f}" for b in names)
            nb.log(f"  {a:22} {row}")
        # среднее попарное согласие (вне диагонали)
        aris = [adjusted_rand_score(partitions[a], partitions[b])
                for i, a in enumerate(names) for b in names[i+1:]]
        nb.summary_item("Среднее попарное ARI", f"{np.mean(aris):.2f} (min {min(aris):.2f}, max {max(aris):.2f})")
    nb.wait()

    nb.step("Шаг 4. Репликация: совпадает ли структура по датасетам")
    with nb.error_handling("replication"):
        idx = np.array([v["dataset"] for v in V])
        for name, lab in partitions.items():
            comp = "; ".join(
                f"{ds}: {np.bincount(lab[idx==ds], minlength=K).tolist()}" for ds in DATASETS
            )
            nb.info(f"  {name:22} {comp}")
    nb.wait()

    nb.step("Шаг 5. Сохранение партиций")
    with nb.error_handling("persist"):
        out = pd.DataFrame({"dataset": [v["dataset"] for v in V],
                            "zone_id": [v["zone_id"] for v in V],
                            "ztype": [v["ztype"] for v in V]})
        for name, lab in partitions.items():
            out[name.replace(":", "_")] = lab
        out.to_csv(OUT_DIR / "partitions.csv", index=False)
        nb.success(f"Saved {(OUT_DIR/'partitions.csv').relative_to(PROJECT_ROOT)}")
        nb.next_steps([
            "Интерпретация: высокое ARI между представлениями = структура робастна;",
            "низкое = структура зависит от уровня абстракции (какой информативнее?).",
            "Далее: добавить BOSS/SAX (pyts) как ещё одно представление; затем слой B.",
        ])
    nb.finish("Layer A-ii (multi-view) completed.")


if __name__ == "__main__":
    main()
