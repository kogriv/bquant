"""G48 — порог свинг-стратегий от масштаба зоны: измерен, вдвое лучше по покрытию, не доказан.

При закрытии G38 (2026-09-03) плечо «`min_amplitude_pct` = медианный относительный размах
зоны × k, без пола `base_deviation`» дало `find_peaks` и `pivot_points` 84.4 % покрытия зон
против 36.4 % и 49.4 % у пресета `narrow_zone`. Не отгружено: покрытие — не качество.
Втрое более низкий порог пропускает втрое более мелкие движения, и таблица покрытия не
различает движение и шум.

Этот скрипт снимает четыре измерения из критерия приёмки G48
(`devref/gaps/swing/g48_zone_scale_thresholds_measured_but_unproven_2026-09.md`, §4):

1. **Свинги не шум** — доля точек, подтверждаемых ZigZag (пресет `narrow_zone`) на тех же
   данных: отдельно для точек, которые есть и у пресета («существующие»), и для точек,
   которые появились только под новым порогом («добавленные»); распределение амплитуд
   добавленных против существующих; вырождение метрик зон, посчитанных из свингов
   (`rally_to_drop_ratio`, `duration_symmetry`) на зонах, которые получили свинги только
   под новым порогом.
2. **Второй датасет** — `mt_xauusd_m15`, другой масштаб зоны.
3. **Потолок 65/77** — зоны без свингов под новым порогом: их размах против порога и длина
   против минимума баров стратегии.
4. **Пол** — что остаётся от `base_deviation`, если его снять для этих двух стратегий.

Запуск:
    python research/notebooks/06_swing_scale_threshold_study.py --no-trap
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.strategies.swing import (
    SWING_PRESETS,
    FindPeaksSwingStrategy,
    PivotPointsSwingStrategy,
    ZigZagSwingStrategy,
)
from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data

setup_logging(profile="research")

DATASETS = ("tv_xauusd_1h", "mt_xauusd_m15")
#: Множители плеча — те же, что стояли в `auto_swing_thresholds` до G38.
K = {"find_peaks": 0.3, "pivot_points": 0.25}
PRESET = SWING_PRESETS["narrow_zone"]
CONFIRM_TOL = 2  # баров: точка «подтверждена», если у ZigZag есть точка не дальше


def _zones_and_data(dataset: str):
    result = (
        analyze_zones(get_sample_data(dataset))
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_strategies(swing="zigzag")
        .with_cache(enable=False)
        .analyze(clustering=False)
        .build()
    )
    return result.zones, result.data


def _zone_relative_range(zone) -> float:
    frame = zone.data
    mid = float(frame["close"].median())
    return float(frame["high"].max() - frame["low"].min()) / mid if mid else float("nan")


def _make(strategy: str, min_amplitude_pct: float):
    if strategy == "find_peaks":
        params = {**PRESET.find_peaks, "min_amplitude_pct": min_amplitude_pct}
        return FindPeaksSwingStrategy(**params), params
    params = {**PRESET.pivot_points, "min_amplitude_pct": min_amplitude_pct}
    return PivotPointsSwingStrategy(**params), params


def _run_global(strategy, zones, data) -> Tuple[object, Dict[int, object]]:
    context = strategy.calculate_global(data)
    metrics = {z.zone_id: strategy.aggregate_for_zone(z, context) for z in zones}
    return context, metrics


def _run_per_zone(strategy, zones) -> Dict[int, object]:
    out = {}
    for z in zones:
        try:
            out[z.zone_id] = strategy.calculate(z.data)
        except Exception:  # короткая зона: стратегии нечего считать
            out[z.zone_id] = None
    return out


def _covered(metrics: Dict[int, object]) -> set:
    return {zid for zid, m in metrics.items() if m is not None and m.num_swings > 0}


def _confirmed_share(indices: List[int], reference: np.ndarray, tol: int) -> float:
    if not indices:
        return float("nan")
    ref = np.asarray(sorted(reference))
    hits = 0
    for i in indices:
        pos = np.searchsorted(ref, i)
        near = [ref[j] for j in (pos - 1, pos) if 0 <= j < len(ref)]
        if near and min(abs(int(n) - i) for n in near) <= tol:
            hits += 1
    return hits / len(indices)


def _amplitudes(points, indices: set) -> List[float]:
    return [abs(p.amplitude_to_next) for p in points if p.index in indices and p.amplitude_to_next is not None]


def _degenerate(metrics: Dict[int, object], zone_ids: set) -> Dict[str, float]:
    ratio = [metrics[z].rally_to_drop_ratio for z in zone_ids if metrics[z] is not None]
    symmetry = [metrics[z].duration_symmetry for z in zone_ids if metrics[z] is not None]
    def _stats(values: List[float]) -> Dict[str, float]:
        arr = np.asarray([v for v in values if v is not None], dtype=float)
        finite = arr[np.isfinite(arr)]
        return {
            "n": int(len(arr)),
            "non_finite_or_zero": int(((~np.isfinite(arr)) | (arr == 0)).sum()),
            "exactly_one": int((finite == 1.0).sum()),
            "median": float(np.median(finite)) if len(finite) else float("nan"),
            "p10": float(np.percentile(finite, 10)) if len(finite) else float("nan"),
            "p90": float(np.percentile(finite, 90)) if len(finite) else float("nan"),
        }
    return {"rally_to_drop_ratio": _stats(ratio), "duration_symmetry": _stats(symmetry)}


nb = NotebookSimulator("G48 — порог свингов от масштаба зоны: проверка по критерию приёмки")
records: List[Dict] = []

for dataset in DATASETS:
    nb.step(f"{dataset}: зоны, масштаб, ZigZag-эталон")
    zones, data = _zones_and_data(dataset)
    ranges = np.array([_zone_relative_range(z) for z in zones])
    median_range = float(np.nanmedian(ranges))
    zigzag_ctx = ZigZagSwingStrategy(**PRESET.zigzag).calculate_global(data)
    zigzag_idx = np.asarray(zigzag_ctx.indices)
    nb.log(f"зон: {len(zones)}; медианный относительный размах зоны: {median_range:.5f}; "
           f"порог пресета: {PRESET.find_peaks['min_amplitude_pct']}; "
           f"ZigZag ({PRESET.zigzag}) точек: {len(zigzag_idx)}")
    nb.wait()

    for strategy in ("find_peaks", "pivot_points"):
        nb.step(f"{dataset} / {strategy}: пресет против порога от масштаба зоны")
        lever_threshold = median_range * K[strategy]
        base, base_params = _make(strategy, PRESET.find_peaks["min_amplitude_pct"] if strategy == "find_peaks" else PRESET.pivot_points["min_amplitude_pct"])
        lever, lever_params = _make(strategy, lever_threshold)

        base_ctx, base_m = _run_global(base, zones, data)
        lever_ctx, lever_m = _run_global(lever, zones, data)
        base_cov, lever_cov = _covered(base_m), _covered(lever_m)
        base_pz, lever_pz = _covered(_run_per_zone(base, zones)), _covered(_run_per_zone(lever, zones))

        base_idx = set(int(i) for i in base_ctx.indices)
        lever_idx = set(int(i) for i in lever_ctx.indices)
        existing, added = sorted(base_idx & lever_idx), sorted(lever_idx - base_idx)
        conf = {tol: (_confirmed_share(existing, zigzag_idx, tol), _confirmed_share(added, zigzag_idx, tol)) for tol in (0, 1, 2, 3)}
        amp_existing = _amplitudes(lever_ctx.swing_points, set(existing))
        amp_added = _amplitudes(lever_ctx.swing_points, set(added))
        gained = lever_cov - base_cov
        degen_gained = _degenerate(lever_m, gained)
        degen_base = _degenerate(base_m, base_cov)

        # Пол от данных, не константа: медианный относительный размах одного бара — движение
        # меньше типичного бара лежит внутри бара и порогом быть не может.
        bar_floor = float(((data["high"] - data["low"]) / data["close"]).median())
        floored_threshold = max(lever_threshold, bar_floor)
        floored, _fp = _make(strategy, floored_threshold)
        _, floored_m = _run_global(floored, zones, data)
        floored_cov = _covered(floored_m)
        # Амплитуды движений (не точек): на зонах, покрытых только под плечом, против зон пресета
        def _movement_amplitudes(metrics, zone_ids):
            vals = []
            for zid in zone_ids:
                m = metrics[zid]
                if m is None or m.num_swings == 0:
                    continue
                vals.extend(v for v in (m.min_rally_pct, m.min_drop_pct, m.avg_rally_pct, m.avg_drop_pct) if v)
            return vals
        mov_gained = _movement_amplitudes(lever_m, gained)
        mov_preset = _movement_amplitudes(base_m, base_cov)

        uncovered = [z for z in zones if z.zone_id not in lever_cov]
        min_bars = (base.left_bars + base.right_bars + 1) if strategy == "pivot_points" else base.distance + 1
        unc_short = sum(1 for z in uncovered if z.duration < min_bars)
        unc_small = sum(1 for z in uncovered if _zone_relative_range(z) < lever_threshold)

        nb.log(f"порог: пресет {base_params['min_amplitude_pct']:.4f} → плечо {lever_threshold:.4f} (k={K[strategy]})")
        nb.log(f"покрытие global:   пресет {len(base_cov)}/{len(zones)} = {len(base_cov)/len(zones):.1%} → плечо {len(lever_cov)}/{len(zones)} = {len(lever_cov)/len(zones):.1%}")
        nb.log(f"покрытие per_zone: пресет {len(base_pz)}/{len(zones)} = {len(base_pz)/len(zones):.1%} → плечо {len(lever_pz)}/{len(zones)} = {len(lever_pz)/len(zones):.1%}")
        nb.log(f"точек global: пресет {len(base_idx)}, плечо {len(lever_idx)}; существующих {len(existing)}, добавленных {len(added)}, исчезнувших {len(base_idx - lever_idx)}")
        for tol, (ce, ca) in conf.items():
            nb.log(f"  подтверждено ZigZag (±{tol} бар): существующие {ce:.1%}, добавленные {ca:.1%}")
        if amp_existing and amp_added:
            nb.log(f"  |амплитуда| существующих: медиана {np.median(amp_existing):.3f}%, p10 {np.percentile(amp_existing, 10):.3f}%; "
                   f"добавленных: медиана {np.median(amp_added):.3f}%, p10 {np.percentile(amp_added, 10):.3f}%, p90 {np.percentile(amp_added, 90):.3f}%")
        nb.log(f"  зоны, получившие свинги только под плечом: {len(gained)}; метрики на них: {json.dumps(degen_gained)}")
        nb.log(f"  те же метрики на зонах пресета: {json.dumps(degen_base)}")
        nb.log(f"  без свингов под плечом: {len(uncovered)} зон; из них короче {min_bars} баров: {unc_short}, с размахом ниже порога: {unc_small}")
        nb.log(f"  пол от данных: медианный размах бара {bar_floor:.5f}; порог с полом {floored_threshold:.4f}; покрытие с полом {len(floored_cov)}/{len(zones)}")
        if mov_gained and mov_preset:
            nb.log(f"  амплитуды движений (%): зоны только под плечом — медиана {np.median(mov_gained):.3f}, p10 {np.percentile(mov_gained, 10):.3f}; "
                   f"зоны пресета — медиана {np.median(mov_preset):.3f}, p10 {np.percentile(mov_preset, 10):.3f}")
        records.append({
            "dataset": dataset, "strategy": strategy, "zones": len(zones), "median_range": median_range,
            "threshold_preset": base_params["min_amplitude_pct"], "threshold_lever": lever_threshold,
            "coverage_global": {"preset": len(base_cov), "lever": len(lever_cov)},
            "coverage_per_zone": {"preset": len(base_pz), "lever": len(lever_pz)},
            "points": {"preset": len(base_idx), "lever": len(lever_idx), "existing": len(existing), "added": len(added)},
            "zigzag_confirmed": {str(t): {"existing": ce, "added": ca} for t, (ce, ca) in conf.items()},
            "amplitude_pct": {"existing_median": float(np.median(amp_existing)) if amp_existing else None,
                              "added_median": float(np.median(amp_added)) if amp_added else None,
                              "added_p10": float(np.percentile(amp_added, 10)) if amp_added else None},
            "metrics_on_gained_zones": degen_gained, "metrics_on_preset_zones": degen_base,
            "uncovered": {"total": len(uncovered), "shorter_than_min_bars": unc_short, "range_below_threshold": unc_small},
            "floor": {"median_bar_range": bar_floor, "threshold_floored": floored_threshold, "coverage_floored": len(floored_cov)},
            "movement_amplitude_pct": {"gained_median": float(np.median(mov_gained)) if mov_gained else None,
                                       "gained_p10": float(np.percentile(mov_gained, 10)) if mov_gained else None,
                                       "preset_median": float(np.median(mov_preset)) if mov_preset else None},
        })
        nb.wait()

nb.step("Итог по критерию приёмки")
for r in records:
    c2 = r["zigzag_confirmed"]["2"]
    added = r["points"]["added"]
    nb.log(f"{r['dataset']:<14} {r['strategy']:<13} покрытие {r['coverage_global']['preset']}→{r['coverage_global']['lever']} из {r['zones']} "
           f"(с полом {r['floor']['coverage_floored']}); новых точек {added}; точки подтверждены ZigZag ±2: {c2['existing']:.0%}; "
           f"движения на новых зонах / зонах пресета, медиана: {r['movement_amplitude_pct']['gained_median'] or float('nan'):.3f} / {r['movement_amplitude_pct']['preset_median'] or float('nan'):.3f}; "
           f"непокрытых {r['uncovered']['total']}, из них короче минимума баров {r['uncovered']['shorter_than_min_bars']}")
reports_dir = Path("outputs/reports")
reports_dir.mkdir(parents=True, exist_ok=True)
json_path = reports_dir / "g48_swing_scale_threshold_study.json"
with open(json_path, "w", encoding="utf-8") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=2)
nb.success(f"JSON сохранён: {json_path}")
nb.finish()
