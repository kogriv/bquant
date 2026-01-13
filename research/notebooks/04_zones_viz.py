"""
Zones ZigZag Verification Demo

Скрипт для визуального сравнения:
- зонового overview-графика из пакетного визуализатора (с уже встроенным ZigZag),
- и отдельного графика ZigZag через convenience-функцию `plot_zigzag_verification`
на одном и том же диапазоне дат.

Запуск (из корня проекта):
    python research/notebooks/04_zones_viz.py

Скрипт использует только sample-данные и публичные API пакета.
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

import pandas as pd

from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones.pipeline import analyze_zones
from bquant.visualization import (
    plot_zigzag_verification,
)
from bquant.visualization.export import save_figure


# -----------------------------------------------------------------------------
# Quiet logging for notebook/demo usage
# -----------------------------------------------------------------------------
# Консоль — тихая (ERROR), базовые сообщения NotebookSimulator остаются видимыми.
setup_logging(profile="clean", exceptions={"bquant.core.nb": "INFO"})


# -----------------------------------------------------------------------------
# Image saving configuration
# -----------------------------------------------------------------------------
SAVE_IMAGES = True

# Формат сохранения (для простых графиков используем PNG, для сложных можно HTML)
SAVE_IMAGE_FORMAT = "png"

# Общая директория вывода — относительно текущего скрипта
OUTPUT_DIR = Path(__file__).parent / "outputs" / "vis" / Path(__file__).stem


nb = NotebookSimulator("Zones ZigZag Verification Demo")


# ---------------------------------------------------------------------
# Step 1: Data Loading (sample data only)
# ---------------------------------------------------------------------
nb.step("Step 1: Data Loading")
with nb.error_handling("Loading sample data"):
    df = get_sample_data("tv_xauusd_1h")

    # ВАЖНО: Устанавливаем 'time' как индекс для правильной работы визуализации зон
    if "time" in df.columns:
        df = df.set_index("time")

    nb.success(f"Loaded sample dataset: tv_xauusd_1h, shape={df.shape}")
    nb.log(str(df.head()))
nb.wait()


# ---------------------------------------------------------------------
# Step 2: Zone Analysis Pipeline with ZigZag swings
# ---------------------------------------------------------------------
nb.step("Step 2: Zone Analysis Pipeline (with ZigZag swings)")
with nb.error_handling("Building and running pipeline"):
    # Универсальный pipeline:
    # - рассчитываем MACD,
    # - детектим зоны по zero_crossing,
    # - включаем swing-стратегию 'zigzag'.
    result = (
        analyze_zones(df)
        .with_indicator(
            "custom",
            "macd",
            fast_period=12,
            slow_period=26,
            signal_period=9,
        )
        .detect_zones("zero_crossing", indicator_col="macd")
        .with_strategies(swing="zigzag")
        .with_auto_swing_thresholds(True)
        .with_swing_scope("global")
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    nb.success(f"Pipeline completed: zones={len(result.zones)}")

    # Диагностический контекст ZigZag-стратегии из первой зоны
    swing_context = None
    legs = None
    deviation = None

    if result.zones:
        first_zone = result.zones[0]
        swing_context = getattr(first_zone, "swing_context", None)

        nb.log("Swing strategy context (preview):")
        nb.log(f"  strategy_name: {getattr(swing_context, 'strategy_name', 'N/A')}")
        nb.log(f"  strategy_params: {getattr(swing_context, 'strategy_params', {})}")
        nb.log(
            f"  swing_points_total: {len(getattr(swing_context, 'swing_points', []))}"
        )

        # Извлекаем параметры ZigZag (legs, deviation) из контекста стратегии
        if swing_context and getattr(swing_context, "strategy_params", None):
            strategy_params = swing_context.strategy_params
            legs = strategy_params.get("legs")
            deviation = strategy_params.get("deviation")

        nb.log("Zone indicator context (detection + swing):")
        nb.log(str(first_zone.indicator_context))

    if legs is None or deviation is None:
        nb.warning(
            "ZigZag parameters (legs/deviation) not found in swing_context; "
            "fallback comparison may be less meaningful."
        )
nb.wait()


# ---------------------------------------------------------------------
# Step 3: Overview Visualization on Date Range (Dense)
# ---------------------------------------------------------------------
nb.step("Step 3: Overview Visualization on Date Range (Dense)")
nb.log(f"Output directory for charts: {OUTPUT_DIR.resolve()}")

with nb.error_handling("Creating overview figure for date range (dense)"):
    # Создаем даты с тем же timezone, что и данные
    tz = result.data.index.tz
    start_date = (
        pd.Timestamp("2025-06-25", tz=tz)
        if tz
        else pd.Timestamp("2025-06-25")
    )
    end_date = (
        pd.Timestamp("2025-07-03", tz=tz)
        if tz
        else pd.Timestamp("2025-07-03")
    )

    title_dense = (
        f"Zones Overview (Dense Mode) - "
        f"{start_date.strftime('%d.%m.%Y')} to {end_date.strftime('%d.%m.%Y')}"
    )

    fig_overview_dense = result.visualize(
        "overview",
        date_range=(start_date, end_date),
        title=title_dense,
        show_aggregate_metrics=True,
        aggregate_metrics_mode="full",
        show_swings=True,
        swing_marker_size=9,
        show_indicators=True,
        time_axis_mode="dense",  # Явно указываем для наглядности
    )
    nb.success("Created DENSE overview for date range.")

    if SAVE_IMAGES:
        saved = save_figure(
            fig_overview_dense,
            "01_overview_date_range_dense",
            output_dir=str(OUTPUT_DIR),
            prefer=SAVE_IMAGE_FORMAT,
        )
        if saved:
            nb.log(f"Saved dense chart: {saved}")
nb.wait()


# ---------------------------------------------------------------------
# Step 4: ZigZag Verification on the Same Date Range
# ---------------------------------------------------------------------
nb.step("Step 4: ZigZag Verification on the Same Date Range")

with nb.error_handling("Creating ZigZag verification figure for the same date range"):
    if legs is None or deviation is None:
        nb.warning(
            "Cannot build ZigZag verification chart: "
            "legs/deviation parameters are not available."
        )
    else:
        tz = result.data.index.tz
        start_date = (
            pd.Timestamp("2025-06-25", tz=tz)
            if tz
            else pd.Timestamp("2025-06-25")
        )
        end_date = (
            pd.Timestamp("2025-07-03", tz=tz)
            if tz
            else pd.Timestamp("2025-07-03")
        )

        # Выделяем тот же диапазон данных, что и для overview
        price_slice = result.data.loc[start_date:end_date]
        nb.log(
            f"Price slice for ZigZag verification: shape={price_slice.shape}, "
            f"from={price_slice.index.min()} to={price_slice.index.max()}"
        )

        nb.log("\n--- ZigZag Indicator Verification on Range ---")
        nb.log(f"Parameters: legs={legs}, deviation={deviation:.6f} ({deviation*100:.4f}%)")

        zigzag_data = None  # Инициализируем для использования в Step 5
        # Используем полный датасет для расчета ZigZag (как в визуализаторе),
        # но отображаем только срез price_slice
        fig_zigzag, zigzag_data = plot_zigzag_verification(
            price_data=price_slice,  # Данные для отображения на графике
            legs=int(legs),
            deviation=float(deviation),
            swing_context=swing_context,
            title=None,  # авто-заголовок
            height=800,
            show_rangeslider=True,
            return_data=True,  # Получаем данные для сравнения
            full_data_for_calculation=result.data,  # Полный датасет для расчета ZigZag (как в визуализаторе)
        )

        if fig_zigzag:
            nb.success("ZigZag verification figure created on the same date range")

            if SAVE_IMAGES:
                saved = save_figure(
                    fig_zigzag,
                    "02_zigzag_verification_range",
                    output_dir=str(OUTPUT_DIR),
                    # Для удобства анализа интерактивный формат может быть полезнее:
                    prefer=SAVE_IMAGE_FORMAT,
                )
                if saved:
                    nb.log(f"Saved ZigZag verification chart (range): {saved}")
        else:
            nb.warning("Failed to create ZigZag verification figure")
            if zigzag_data is None:
                nb.warning("ZigZag data extraction also failed")
nb.wait()


# ---------------------------------------------------------------------
# Step 5: Extract and Compare ZigZag Points
# ---------------------------------------------------------------------
nb.step("Step 5: Extract and Compare ZigZag Points")

with nb.error_handling("Extracting and comparing ZigZag points from both sources"):
    if swing_context is None or zigzag_data is None:
        nb.warning(
            "Cannot compare points: swing_context or zigzag_data is not available"
        )
    else:
        # Определяем Date Range для фильтрации
        tz = result.data.index.tz
        start_date = (
            pd.Timestamp("2025-06-25", tz=tz)
            if tz
            else pd.Timestamp("2025-06-25")
        )
        end_date = (
            pd.Timestamp("2025-07-03", tz=tz)
            if tz
            else pd.Timestamp("2025-07-03")
        )

        # 1. Извлекаем точки из swing_context (визуализатор пакета)
        package_points = []
        for sp in swing_context.swing_points:
            # Фильтруем по Date Range
            if start_date <= sp.timestamp <= end_date:
                package_points.append({
                    "timestamp": sp.timestamp.isoformat() if hasattr(sp.timestamp, "isoformat") else str(sp.timestamp),
                    "index": sp.index,
                    "price": float(sp.price),
                    "swing_type": sp.swing_type,
                    "point_id": sp.point_id,
                })

        nb.log(f"Extracted {len(package_points)} points from swing_context (package visualizer)")
        nb.log(f"  Package calculates ZigZag on FULL dataset ({len(result.data)} bars), then filters by date range")

        # 2. Извлекаем точки из plot_zigzag_verification (pandas_ta)
        verification_points = []
        if zigzag_data:
            # Объединяем peaks и troughs
            all_verification_points = zigzag_data["peaks"] + zigzag_data["troughs"]
            
            for timestamp, price in all_verification_points:
                # Фильтруем по Date Range
                if start_date <= timestamp <= end_date:
                    # Определяем тип из исходных списков
                    swing_type = "peak" if (timestamp, price) in zigzag_data["peaks"] else "trough"
                    verification_points.append({
                        "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                        "price": float(price),
                        "swing_type": swing_type,
                    })

        nb.log(f"Extracted {len(verification_points)} points from plot_zigzag_verification (pandas_ta)")
        nb.log(f"  Verification now calculates ZigZag on FULL dataset (via full_data_for_calculation parameter)")
        nb.log(f"  Both methods use the same context - results should match!")

        # 3. Сравнение точек: Full Join по timestamp
        # Создаём словари для быстрого поиска по timestamp
        package_dict = {pt["timestamp"]: pt for pt in package_points}
        verification_dict = {pt["timestamp"]: pt for pt in verification_points}

        # Full join: все уникальные timestamps из обоих источников
        all_timestamps = set(package_dict.keys()) | set(verification_dict.keys())
        
        comparison_results = {
            "only_in_package": [],  # Точки только в пакете
            "only_in_verification": [],  # Точки только в verification
            "in_both": [],  # Точки в обоих источниках
            "price_differences": [],  # Различия в ценах для одинаковых timestamps
        }

        for ts in sorted(all_timestamps):
            pkg_pt = package_dict.get(ts)
            ver_pt = verification_dict.get(ts)

            if pkg_pt and ver_pt:
                # Точка есть в обоих источниках
                price_diff = abs(pkg_pt["price"] - ver_pt["price"])
                price_diff_pct = (price_diff / pkg_pt["price"] * 100) if pkg_pt["price"] != 0 else 0.0
                
                comparison_results["in_both"].append({
                    "timestamp": ts,
                    "package_price": pkg_pt["price"],
                    "verification_price": ver_pt["price"],
                    "price_difference": price_diff,
                    "price_difference_pct": price_diff_pct,
                    "package_type": pkg_pt["swing_type"],
                    "verification_type": ver_pt["swing_type"],
                    "type_match": pkg_pt["swing_type"] == ver_pt["swing_type"],
                })

                if price_diff > 1e-6:  # Учитываем погрешности float
                    comparison_results["price_differences"].append({
                        "timestamp": ts,
                        "package_price": pkg_pt["price"],
                        "verification_price": ver_pt["price"],
                        "difference": price_diff,
                        "difference_pct": price_diff_pct,
                    })
            elif pkg_pt:
                comparison_results["only_in_package"].append(pkg_pt)
            elif ver_pt:
                comparison_results["only_in_verification"].append(ver_pt)

        # Статистика сравнения
        nb.log("\n--- Comparison Statistics ---")
        nb.log(f"Total unique timestamps: {len(all_timestamps)}")
        nb.log(f"Points only in package: {len(comparison_results['only_in_package'])}")
        nb.log(f"Points only in verification: {len(comparison_results['only_in_verification'])}")
        nb.log(f"Points in both: {len(comparison_results['in_both'])}")
        nb.log(f"Price differences found: {len(comparison_results['price_differences'])}")

        if comparison_results["price_differences"]:
            max_diff = max(d["difference"] for d in comparison_results["price_differences"])
            max_diff_pct = max(d["difference_pct"] for d in comparison_results["price_differences"])
            nb.log(f"Max price difference: {max_diff:.6f} ({max_diff_pct:.4f}%)")

        # 4. Сериализация результатов для сохранения
        comparison_export = {
            "date_range": {
                "start": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date),
                "end": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date),
            },
            "parameters": {
                "legs": int(legs),
                "deviation": float(deviation),
            },
            "package_points": package_points,
            "verification_points": verification_points,
            "comparison": {
                "total_unique_timestamps": len(all_timestamps),
                "only_in_package_count": len(comparison_results["only_in_package"]),
                "only_in_verification_count": len(comparison_results["only_in_verification"]),
                "in_both_count": len(comparison_results["in_both"]),
                "price_differences_count": len(comparison_results["price_differences"]),
                "only_in_package": comparison_results["only_in_package"],
                "only_in_verification": comparison_results["only_in_verification"],
                "in_both": comparison_results["in_both"],
                "price_differences": comparison_results["price_differences"],
            },
        }

        # Сохраняем JSON
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "03_zigzag_points_comparison.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(comparison_export, f, indent=2, ensure_ascii=False, default=str)
        
        nb.success(f"Comparison data saved to: {json_path}")
        nb.log(f"JSON file size: {json_path.stat().st_size / 1024:.2f} KB")

        # Краткий вывод первых различий (если есть)
        if comparison_results["price_differences"]:
            nb.log("\n--- First 5 Price Differences ---")
            for diff in comparison_results["price_differences"][:5]:
                nb.log(
                    f"  {diff['timestamp']}: "
                    f"package={diff['package_price']:.6f}, "
                    f"verification={diff['verification_price']:.6f}, "
                    f"diff={diff['difference']:.6f} ({diff['difference_pct']:.4f}%)"
                )

        if comparison_results["only_in_package"]:
            nb.log(f"\n--- Points Only in Package (calculated on FULL dataset) ---")
            nb.log(f"  These points were detected because ZigZag saw full context")
            for pt in comparison_results["only_in_package"][:3]:
                nb.log(f"  {pt['timestamp']}: price={pt['price']:.6f}, type={pt['swing_type']}, index={pt.get('index', 'N/A')}")

        if comparison_results["only_in_verification"]:
            nb.log(f"\n--- Points Only in Verification (calculated on SLICE only) ---")
            nb.log(f"  These points appeared due to boundary effects from truncated data")
            for pt in comparison_results["only_in_verification"][:3]:
                nb.log(f"  {pt['timestamp']}: price={pt['price']:.6f}, type={pt['swing_type']}")

        # Проверка совпадения результатов
        if len(comparison_results["in_both"]) == len(package_points) and \
           len(comparison_results["only_in_package"]) == 0 and \
           len(comparison_results["only_in_verification"]) == 0:
            nb.success("\n✅ Perfect match! Both methods now use the same data context (FULL dataset)")
            nb.log("  plot_zigzag_verification now calculates ZigZag on full dataset")
            nb.log("  (via full_data_for_calculation parameter), matching the visualizer behavior")
        else:
            nb.log("\n--- Note on ZigZag context dependency ---")
            nb.log("  ZigZag indicator is CONTEXT-DEPENDENT:")
            nb.log("  - It needs bars BEFORE a potential swing to confirm a reversal")
            nb.log("  - It needs bars AFTER to validate the swing")
            nb.log("  - When calculated on a slice, boundary effects occur:")
            nb.log("    * Points near range start may be missed (no prior context)")
            nb.log("    * Points near range end may be missed (no future context)")
            nb.log("    * New points may appear at boundaries (artificial reversals)")
            nb.log("  Solution: Use full_data_for_calculation parameter for consistent results")

nb.wait()


# ---------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------
nb.finish(message="Zones ZigZag verification demo completed")


