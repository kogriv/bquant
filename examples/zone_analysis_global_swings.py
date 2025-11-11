#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример BQuant: глобальные свинги против локальных.

Что показывает скрипт
=====================
1. Как запустить пайплайн анализа зон в режимах ``per_zone`` и ``global``.
2. Чем отличается покрытие зон свингами и среднее число колебаний.
3. Как получить список глобальных пивотов через ``ZoneInfo.get_zone_swings``.
4. Как быстро визуализировать разницу в покрытии (бар-чарт).

Скрипт предназначен для живой демонстрации преимуществ перехода на
``with_swing_scope('global')`` из плана gloswing.md (пункт 6.2.4).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

os.environ.setdefault("BQUANT_SKIP_TALIB", "1")
os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bquant.analysis.zones import analyze_zones
from bquant.core.logging_config import setup_logging
from bquant.data.samples import get_sample_data


@dataclass
class CoverageReport:
    """Удобная обёртка с ключевыми метриками по зонам."""

    mode: str
    total_zones: int
    zones_with_swings: int
    coverage_pct: float
    avg_swings_per_active_zone: float

    def as_printable(self) -> str:
        """Вернуть человекочитаемое описание результатов."""

        return (
            f"Режим: {self.mode}\n"
            f"  Зон всего: {self.total_zones}\n"
            f"  Зон со свингами: {self.zones_with_swings}"
            f" ({self.coverage_pct:.1%})\n"
            f"  Среднее число свингов в активной зоне: "
            f"{self.avg_swings_per_active_zone:.2f}\n"
        )


def prepare_sample_data(dataset: str = "mt_xauusd_m15"):
    """Загрузить встроенный датасет и привести индекс ко времени."""

    df = get_sample_data(dataset)

    if "time" in df.columns:
        timestamps = pd.to_datetime(df["time"], utc=True, errors="coerce")
        df = df.drop(columns=["time"]).set_index(timestamps)
        df.index.name = "time"

    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert(None)

    return df


def run_zone_analysis(data, swing_scope: str):
    """Запустить анализ зон в выбранном режиме расчёта свингов."""

    return (
        analyze_zones(data)
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones(
            "zero_crossing",
            indicator_col="macd_hist",
            zone_types=["bull", "bear"],
            min_duration=8,
        )
        .with_strategies(swing="zigzag")
        .with_auto_swing_thresholds(True)
        .with_swing_scope(swing_scope)
        .build()
    )


def extract_swing_metrics(zone) -> Dict:
    """Достать метрики свингов из zone.features.metadata."""

    features = zone.features or {}
    metadata = features.get("metadata", {})
    return metadata.get("swing_metrics") or {}


def collect_coverage(result, mode: str) -> CoverageReport:
    """Посчитать покрытие зон свингами и усреднённые значения."""

    zones_with_swings = 0
    total_swings = 0

    for zone in result.zones:
        metrics = extract_swing_metrics(zone)
        if metrics and metrics.get("num_swings", 0) > 0:
            zones_with_swings += 1
            total_swings += metrics.get("num_swings", 0)

    total = len(result.zones)
    coverage = zones_with_swings / total if total else 0.0
    avg_swings = total_swings / zones_with_swings if zones_with_swings else 0.0

    return CoverageReport(
        mode=mode,
        total_zones=total,
        zones_with_swings=zones_with_swings,
        coverage_pct=coverage,
        avg_swings_per_active_zone=avg_swings,
    )


def preview_global_swings(zones: List):
    """Вывести пример глобальных пивотов для первой бычьей зоны."""

    target_zone = next((zone for zone in zones if zone.type == "bull"), None)
    if target_zone is None:
        print("[-] В глобальном результате не найдено бычьих зон для предпросмотра.")
        return

    swings = target_zone.get_zone_swings()
    if not swings:
        print("[-] SwingContext отсутствует — возможно, включён fallback.")
        return

    print("Пример глобальных пивотов для первой bull-зоны:")
    for idx, swing in enumerate(swings[:4], start=1):
        print(
            f"  #{idx}: {swing.timestamp} | тип={swing.swing_type} | "
            f"цена={swing.price:.2f} | delta→next={swing.amplitude_to_next or 0:.2%}"
        )
    if len(swings) > 4:
        print(f"  … всего пивотов в зоне: {len(swings)}")


def plot_coverage_bar(reports: List[CoverageReport]):
    """Нарисовать простую диаграмму различий (опционально)."""

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - только для живого запуска
        print(f"[!] Matplotlib недоступен, пропускаем график: {exc}")
        return

    labels = [r.mode for r in reports]
    values = [r.coverage_pct * 100 for r in reports]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(labels, values, color=["#6BA292", "#3B6FB6"])
    ax.set_ylim(0, max(values) * 1.2 if values else 1)
    ax.set_ylabel("Покрытие зон свингами, %")
    ax.set_title("Global vs Per-Zone Swing Calculation")

    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}%", ha="center", va="bottom")

    plt.tight_layout()
    plt.show()


def main():
    """Точка входа для демонстрации."""

    setup_logging(console_level="WARNING", file_level="ERROR", log_to_file=False, use_colors=False, reset_loggers=True)

    print("Загружаем sample-датасет ...")
    data = prepare_sample_data()
    print(f"Получено строк: {len(data)}, колонок: {list(data.columns)}")

    print("\n=== Режим per_zone (наследие) ===")
    per_zone_result = run_zone_analysis(data, "per_zone")
    per_zone_report = collect_coverage(per_zone_result, "per_zone")
    print(per_zone_report.as_printable())

    print("=== Режим global (новый) ===")
    global_result = run_zone_analysis(data, "global")
    global_report = collect_coverage(global_result, "global")
    print(global_report.as_printable())

    improvement = (global_report.coverage_pct - per_zone_report.coverage_pct) * 100
    print(f"Δ Coverage: {improvement:+.1f} п.п. (global против per_zone)")

    preview_global_swings(global_result.zones)

    print("\nСтроим диаграмму различий ...")
    plot_coverage_bar([per_zone_report, global_report])


if __name__ == "__main__":
    main()
