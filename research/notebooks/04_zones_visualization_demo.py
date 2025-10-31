"""
Zones Visualization Demo (Stage 4)

Research script-notebook using NotebookSimulator to demonstrate the
visualization capabilities for zone analysis in a single, compact flow.

Key goals:
- Build a universal zone analysis pipeline on sample data
- Visualize: overview, detail (single zone), comparison (multiple zones), statistics
- Select the single zone deterministically by median duration using existing
  statistics exposed by ZoneAnalysisResult (no new methods added)

Usage (CLI is auto-configured by NotebookSimulator):
    python research/notebooks/04_zones_visualization_demo.py

This script relies only on built-in sample data and package APIs.
"""

from __future__ import annotations

from pathlib import Path

from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones.pipeline import analyze_zones
from bquant.visualization import (
    ZoneVisualizer,
    plot_zone_detail,
    plot_zones_comparison,
)
from bquant.visualization.export import save_figure


# -----------------------------------------------------------------------------
# Quiet logging for notebook/demo usage
# -----------------------------------------------------------------------------
# Консоль — тихая (ERROR), базовые сообщения NotebookSimulator остаются видимыми.
setup_logging(profile='clean', exceptions={'bquant.core.nb': 'INFO'})

# -----------------------------------------------------------------------------
# Image saving flag (default: False for faster test runs)
# -----------------------------------------------------------------------------
SAVE_IMAGES = False


# use package save_figure directly

nb = NotebookSimulator("Zones Visualization Demo (Stage 4)")

# ---------------------------------------------------------------------
# Step 1: Setup
# ---------------------------------------------------------------------
nb.step("Step 1: Setup")
# Общее описание сценария и окружения.
# NotebookSimulator обеспечивает понятные шаги, логирование и "ожидания" (wait),
# чтобы можно было пошагово смотреть на вывод и артефакты.
nb.info("Initializing demo configuration and environment")
nb.wait()

# ---------------------------------------------------------------------
# Step 2: Data Loading (sample data only)
# ---------------------------------------------------------------------
nb.step("Step 2: Data Loading")
# Используем встроенный датасет (без внешних путей):
# - соблюдаем правила проекта (повторяемость, CI-friendly)
# - исключаем нефиксируемые внешние зависимости
with nb.error_handling("Loading sample data"):
    df = get_sample_data("tv_xauusd_1h")
    nb.success(f"Loaded sample dataset: tv_xauusd_1h, shape={df.shape}")
nb.wait()

# ---------------------------------------------------------------------
# Step 3: Zone Analysis Pipeline (Universal)
# ---------------------------------------------------------------------
nb.step("Step 3: Zone Analysis Pipeline")
# Универсальный pipeline: один вход для разных индикаторов и стратегий.
# Здесь: рассчитываем MACD, детектим зоны по zero_crossing, запускаем анализ.
with nb.error_handling("Building and running pipeline"):
    # Build pipeline with MACD indicator and zero-crossing zone detection
    result = (
        analyze_zones(df)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    nb.success(f"Pipeline completed: zones={len(result.zones)}")
nb.wait()

# ---------------------------------------------------------------------
# Step 4: Overview Visualization
# ---------------------------------------------------------------------
nb.step("Step 4: Overview Visualization")
# Режим 'overview' показывает все зоны на цене — первичный обзор.
with nb.error_handling("Creating overview figure"):
    fig_overview = result.visualize("overview", title="Zones Overview")
    nb.success("Overview figure created")
    if SAVE_IMAGES:
        saved = save_figure(fig_overview, "01_overview")
        if saved:
            nb.log(f"Saved: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 5: Detail Visualization (single zone by median duration)
# ---------------------------------------------------------------------
nb.step("Step 5: Detail Visualization (single zone)")
# Детальный просмотр по одной зоне. Выбор делаем детерминированно: медианная длительность.
with nb.error_handling("Selecting median-duration zone and rendering detail"):
    base_zone = None
    median_dur = None
    # 1) Попробовать взять медиану из statistics
    stats = result.statistics if isinstance(result.statistics, dict) else {}
    median_val = (
        stats.get("duration_distribution", {})
             .get("overall", {})
             .get("median")
    )
    # 2) Выбрать зону с длительностью, ближайшей к медиане
    def _dur(z):
        feats = getattr(z, "features", None)
        if isinstance(feats, dict) and isinstance(feats.get("duration"), (int, float)):
            return float(feats["duration"]) 
        val = getattr(z, "duration", None)
        return float(val) if isinstance(val, (int, float)) else None

    if result.zones:
        if isinstance(median_val, (int, float)):
            candidates = [(z, d) for z in result.zones if (d := _dur(z)) is not None]
            if candidates:
                base_zone, median_dur = min(candidates, key=lambda t: abs(t[1] - float(median_val)))
        # Fallback: если медиана отсутствует или нет длительностей — берем первую зону
        if base_zone is None:
            base_zone = result.zones[0]
            d = _dur(base_zone)
            median_dur = d if isinstance(d, (int, float)) else None

    if base_zone is None:
        nb.warning("Unable to select a zone for detail view")
    else:
        z_id = getattr(base_zone, "zone_id", 0)
        fig_detail_1 = result.visualize(
            "detail", zone_id=z_id, context_bars=20, title=f"Zone #{z_id} (≈ median duration: {median_dur:.1f} bars)"
        )
        nb.success(f"Detail figure for zone #{z_id} created (duration≈{median_dur:.1f} bars)")
        if SAVE_IMAGES:
            saved = save_figure(fig_detail_1, "02_detail_median")
            if saved:
                nb.log(f"Saved: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 6: Detail Visualization (second zone) and Comparison (minimal pair)
# ---------------------------------------------------------------------
nb.step("Step 6: Detail (second zone) and Comparison")
# Для сравнения берём ещё одну «соседнюю» зону и строим минимальную пару.
with nb.error_handling("Selecting an additional zone for comparison"):
    if 'base_zone' in locals() and base_zone is not None:
        base_id = getattr(base_zone, "zone_id", 0)
        ids = [getattr(z, "zone_id", idx) for idx, z in enumerate(result.zones)]
        extra_ids = []
        if ids:
            if base_id in ids:
                i = ids.index(base_id)
                if i - 1 >= 0:
                    extra_ids.append(ids[i - 1])
                if i + 1 < len(ids):
                    extra_ids.append(ids[i + 1])
            else:
                extra_ids = ids[:1]
        if not extra_ids:
            nb.warning("No additional zone available for comparison; skipping pair demo")
        else:
            z2 = extra_ids[0]
            # Detail for the second zone (optional but useful)
            fig_detail_2 = result.visualize("detail", zone_id=z2, context_bars=20, title=f"Zone #{z2} (second for demo)")
            if SAVE_IMAGES:
                save_figure(fig_detail_2, "02_detail_second")
            # Minimal comparison for two zones
            fig_cmp = result.visualize("comparison", title="Zones Comparison (2 zones)", max_zones=2)
            nb.success(f"Comparison figure created for zones #{base_id} and #{z2}")
            if SAVE_IMAGES:
                saved = save_figure(fig_cmp, "03_comparison_pair")
                if saved:
                    nb.log(f"Saved: {saved}")
    else:
        nb.warning("Skipping comparison due to missing median selection")
nb.wait()

# ---------------------------------------------------------------------
# Step 7: Statistics Visualization
# ---------------------------------------------------------------------
nb.step("Step 7: Statistics Visualization")
# Агрегированные статистики по зонам (распределения, соотношения и т.п.).
with nb.error_handling("Creating statistics figure"):
    fig_stats = result.visualize("statistics", title="Zones Statistics")
    nb.success("Statistics figure created")
    if SAVE_IMAGES:
        saved = save_figure(fig_stats, "04_statistics")
        if saved:
            nb.log(f"Saved: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 8: Alternative Interfaces (ZoneVisualizer and Convenience Functions)
# ---------------------------------------------------------------------
nb.step("Step 8: Alternative Interfaces (Visualizer & Convenience)")
# Полное покрытие интерфейсов визуализации:
# - Прямой вызов методов ZoneVisualizer (деталь/сравнение)
# - Convenience-функции (те же визуализации без явного создания инстанса)
with nb.error_handling("Creating figures via ZoneVisualizer and convenience functions"):
    # Detail via ZoneVisualizer (extended context)
    if 'base_zone' in locals() and base_zone is not None:
        median_zone = base_zone
        z_id = getattr(base_zone, "zone_id", 0)
        visualizer = ZoneVisualizer(backend='plotly')
        fig_detail_v = visualizer.plot_zone_detail(
            result.data, median_zone, context_bars=30, title=f"Zone #{z_id} Detail - Visualizer"
        )
        if SAVE_IMAGES:
            save_figure(fig_detail_v, "02_detail_visualizer")

        # Detail via convenience function
        fig_detail_c = plot_zone_detail(
            result.data, median_zone, context_bars=15, title=f"Zone #{z_id} Detail - Convenience", backend='plotly'
        )
        if SAVE_IMAGES:
            save_figure(fig_detail_c, "02_detail_convenience")

    # Comparison via ZoneVisualizer
    fig_cmp_v = ZoneVisualizer(backend='plotly').plot_zones_comparison(
        result.data, result.zones, max_zones=4, title="Zones Comparison - Visualizer"
    )
    if SAVE_IMAGES:
        save_figure(fig_cmp_v, "03_comparison_visualizer")

    # Comparison via convenience function
    fig_cmp_c = plot_zones_comparison(
        result.data, result.zones, max_zones=3, title="Zones Comparison - Convenience", backend='plotly'
    )
    if SAVE_IMAGES:
        save_figure(fig_cmp_c, "03_comparison_convenience")
nb.wait()

# ---------------------------------------------------------------------
# Step 9: Custom Configuration Demo
# ---------------------------------------------------------------------
nb.step("Step 9: Custom Configuration")
# Демонстрация настраиваемости визуализатора (размеры, прозрачность, подписи и т.д.).
with nb.error_handling("Creating custom-configured detail figure"):
    if result.zones:
        custom_vis = ZoneVisualizer(
            backend='plotly',
            width=1400,
            height=900,
            show_zone_labels=True,
            show_zone_stats=True,
            opacity=0.4,
            zone_detail_context=25,
        )
        target_zone = result.zones[0]
        fig_custom = custom_vis.plot_zone_detail(
            result.data, target_zone, context_bars=25, title='Custom Configured Zone Detail'
        )
        if SAVE_IMAGES:
            save_figure(fig_custom, "05_custom_configuration")
nb.wait()

# ---------------------------------------------------------------------
# Finish
# ---------------------------------------------------------------------
nb.finish()


