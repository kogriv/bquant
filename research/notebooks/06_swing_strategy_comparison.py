"""Сравнительный анализ стратегий свингов на глобальном и локальном режимах.

Цель скрипта — предоставить исследовательскую сводку по трём основным стратегиям
(`find_peaks`, `pivot_points`, `zigzag`) с измерением производительности,
покрытия зон и качественных рекомендаций. Результаты дополняют документацию
по глобальным свингам (план 6.2.3) и используются в обзоре решений.

Основные шаги:
1. Загрузка репрезентативного датасета и настройка окружения NotebookSimulator.
2. Запуск пайплайна `analyze_zones` для каждой стратегии в режимах `per_zone` и
   `global` с фиксированным набором параметров.
3. Измерение времени выполнения, подсчёт покрытия зон и ключевых метрик
   (`num_swings`, `avg_rally_pct`, `avg_drop_pct`).
4. Формирование сравнительной таблицы и сохранение результатов в JSON/CSV.
5. Вывод практических рекомендаций по выбору стратегии.

Запуск:
    python research/notebooks/06_swing_strategy_comparison.py --no-trap
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

setup_logging(profile="research")


def _gather_metrics(zones) -> Dict[str, float]:
    total_zones = 0
    zones_with_swings = 0
    num_swings_values: List[int] = []
    rally_pct_values: List[float] = []
    drop_pct_values: List[float] = []

    for zone in zones:
        if zone.type != "bull":
            continue

        total_zones += 1
        if not zone.features:
            continue

        swing_metrics = zone.features.get("metadata", {}).get("swing_metrics")
        if not swing_metrics:
            continue

        num_swings = swing_metrics.get("num_swings", 0)
        num_swings_values.append(num_swings)
        if num_swings > 0:
            zones_with_swings += 1

        if swing_metrics.get("rally_count", 0) > 0:
            rally_pct_values.append(swing_metrics.get("avg_rally_pct", 0.0))
        if swing_metrics.get("drop_count", 0) > 0:
            drop_pct_values.append(abs(swing_metrics.get("avg_drop_pct", 0.0)))

    return {
        "zones_total": total_zones,
        "zones_with_swings": zones_with_swings,
        "pct_with_swings": (zones_with_swings / total_zones * 100) if total_zones else 0.0,
        "avg_num_swings": float(np.mean(num_swings_values)) if num_swings_values else 0.0,
        "avg_rally_pct": float(np.mean(rally_pct_values)) if rally_pct_values else 0.0,
        "avg_drop_pct": float(np.mean(drop_pct_values)) if drop_pct_values else 0.0,
    }


def _run_pipeline(df, strategy: str, scope: str) -> Dict[str, float]:
    start = time.perf_counter()
    analysis_result = (
        analyze_zones(df)
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .with_strategies(swing=strategy)
        .with_swing_preset("narrow_zone")
        .with_auto_swing_thresholds(True)
        .with_swing_scope(scope)
        .analyze(clustering=False)
        .build()
    )
    elapsed = time.perf_counter() - start
    metrics = _gather_metrics(analysis_result.zones)
    metrics.update({
        "strategy": strategy,
        "scope": scope,
        "runtime_sec": round(elapsed, 3),
        "zones": len(analysis_result.zones),
    })
    return metrics


def _recommendations(df: pd.DataFrame) -> List[str]:
    recommendations = []
    for strategy in df["strategy"].unique():
        subset = df[df["strategy"] == strategy]
        global_row = subset[subset["scope"] == "global"].iloc[0]
        per_zone_row = subset[subset["scope"] == "per_zone"].iloc[0]

        if global_row["pct_with_swings"] - per_zone_row["pct_with_swings"] > 15:
            recommendations.append(
                f"Для {strategy}: использовать global-режим в production, выигрывает покрытие на "
                f"{global_row['pct_with_swings'] - per_zone_row['pct_with_swings']:.1f} п.п."
            )
        else:
            recommendations.append(
                f"Для {strategy}: per_zone допустим в бэктестах, глобальный режим можно включать "
                "для финального отчёта."
            )

        if global_row["runtime_sec"] - per_zone_row["runtime_sec"] > 0.5:
            recommendations.append(
                f"  ↳ Учесть: global медленнее на {global_row['runtime_sec'] - per_zone_row['runtime_sec']:.2f} c."
            )
    return recommendations


nb = NotebookSimulator("Сравнение стратегий свингов (6.2.3)")

nb.step("Шаг 1: Подготовка данных")

df = get_sample_data("tv_xauusd_1h")
if "time" in df.columns:
    df = df.set_index("time")
nb.success(
    "Загружен датасет tv_xauusd_1h: %s – %s (баров: %d)"
    % (df.index.min(), df.index.max(), len(df))
)
nb.wait()

nb.step("Шаг 2: Запуск пайплайнов для каждой стратегии")

records: List[Dict[str, float]] = []
strategies = ["find_peaks", "pivot_points", "zigzag"]
scopes = ["per_zone", "global"]

for strategy in strategies:
    nb.section_header(f"Стратегия {strategy}")
    for scope in scopes:
        nb.info(f"Запуск режима {scope}")
        metrics = _run_pipeline(df, strategy, scope)
        records.append(metrics)
        nb.success(
            "  coverage=%.1f%%, avg_num_swings=%.2f, runtime=%.3f c"
            % (metrics["pct_with_swings"], metrics["avg_num_swings"], metrics["runtime_sec"])
        )
    nb.wait()

nb.step("Шаг 3: Сводные таблицы")

results_df = pd.DataFrame(records)
nb.log(results_df.sort_values(["strategy", "scope"]).to_string(index=False))

pivot_df = (
    results_df.pivot_table(
        index="strategy",
        columns="scope",
        values="pct_with_swings",
        aggfunc="first",
    )
    .assign(delta=lambda d: d["global"] - d["per_zone"])
    .reset_index()
)
nb.log("Прирост покрытия (global - per_zone):")
nb.log(pivot_df.to_string(index=False))
nb.wait()

nb.step("Шаг 4: Рекомендации")

for line in _recommendations(results_df):
    nb.log(line)
nb.wait()

nb.step("Шаг 5: Сохранение результатов")

reports_dir = Path("outputs/reports")
reports_dir.mkdir(parents=True, exist_ok=True)

json_path = reports_dir / "swing_strategy_comparison.json"
with json_path.open("w", encoding="utf-8") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=2)
nb.success(f"JSON сохранён: {json_path}")

csv_path = reports_dir / "swing_strategy_comparison.csv"
results_df.to_csv(csv_path, index=False)
nb.success(f"CSV сохранён: {csv_path}")

nb.info("Готово. Используйте результаты в пользовательской и технической документации.")
nb.finish()
