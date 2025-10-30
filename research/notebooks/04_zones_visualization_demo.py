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

from typing import List, Optional, Tuple

import math
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


# -----------------------------------------------------------------------------
# Output directory for saved figures
# -----------------------------------------------------------------------------
# Output directory for saved figures
# -----------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent / "outputs" / "visualization"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Quiet logging for notebook/demo usage
# -----------------------------------------------------------------------------
# Консоль — тихая (ERROR), базовые сообщения NotebookSimulator остаются видимыми.
setup_logging(profile='clean', exceptions={'bquant.core.nb': 'INFO'})

# -----------------------------------------------------------------------------
# Image saving flag (default: False for faster test runs)
# -----------------------------------------------------------------------------
SAVE_IMAGES = False


# -----------------------------------------------------------------------------
# Saving configuration
# -----------------------------------------------------------------------------
# Options:
#   - "html": always save Plotly as HTML (no external deps), Matplotlib as PNG
#   - "png":  try to save Plotly as PNG (requires kaleido); on failure fallback to HTML
#              Matplotlib remains PNG
SAVE_IMAGE_FORMAT = "png"  # set to "png" to prefer PNG (Plotly falls back to HTML if unavailable)


def save_figure(fig, filename: str) -> bool:
    """Save figure to OUTPUT_DIR without requiring external exporters.

    Rationale:
    - Для Plotly:
        * При SAVE_IMAGE_FORMAT == 'png' пробуем записать PNG (требуется kaleido),
          при ошибке тихо сохраняем HTML (fallback).
        * При SAVE_IMAGE_FORMAT == 'html' всегда сохраняем HTML.
    - Для Matplotlib: сохраняем PNG независимо от настроек.

    Возвращаем True при успешном сохранении (HTML/PNG), иначе False.
    """
    try:
        # Plotly detection: prefer method presence to avoid hard imports
        if hasattr(fig, "write_html"):
            # Prefer PNG if requested; fallback to HTML when PNG export not available
            if SAVE_IMAGE_FORMAT.lower() == "png" and hasattr(fig, "write_image"):
                try:
                    png_path = OUTPUT_DIR / f"{filename}.png"
                    fig.write_image(str(png_path), width=1400, height=900)
                    return True
                except Exception:
                    # Fallback to HTML if PNG export (kaleido) is unavailable
                    html_path = OUTPUT_DIR / f"{filename}.html"
                    fig.write_html(str(html_path))
                    return True
            # Default: HTML
            html_path = OUTPUT_DIR / f"{filename}.html"
            fig.write_html(str(html_path))
            return True

        # Matplotlib fallback
        if hasattr(fig, "savefig"):
            png_path = OUTPUT_DIR / f"{filename}.png"
            fig.savefig(str(png_path), dpi=150, bbox_inches="tight")
            return True
    except Exception:
        return False

    return False


def _get_zone_duration_bars(zone) -> Optional[float]:
    """Return zone duration in bars as a float, if available.

    Контракт данных:
    - После вызова UniversalZoneAnalyzer, признаки зоны (в т.ч. длительность в барах)
      записаны в `zone.features`.
    - Структуры моделей могут отличаться, поэтому предусмотрены fallback-варианты.

    Приоритет выбора значения:
    1) `zone.features['duration']` (если доступно) — длительность в барах.
    2) `zone.duration` (если это уже числовое значение в барах).
    """
    # Prefer features (set by UniversalZoneAnalyzer)
    if getattr(zone, "features", None) and isinstance(zone.features, dict):
        dur = zone.features.get("duration")
        if isinstance(dur, (int, float)) and math.isfinite(dur):
            return float(dur)

    # Fallbacks: some ZoneInfo implementations store raw duration differently
    # Attempt attribute access; if it is a Timedelta-like, try to read .components or total bars
    if hasattr(zone, "duration"):
        value = getattr(zone, "duration")
        # Common cases: numeric already; otherwise try to coerce if possible
        if isinstance(value, (int, float)) and math.isfinite(value):
            return float(value)

    return None


def _get_statistics_median_bars(statistics: dict) -> Optional[float]:
    """Extract median duration in bars from result.statistics if available.

    Ожидаемый формат (стандартная сборка statistics в UniversalZoneAnalyzer):
    statistics['duration_distribution']['overall']['median'] -> float

    Если формат иной или раздел отсутствует — возвращаем None (fallback на локальный расчёт).
    """
    if not isinstance(statistics, dict):
        return None

    # Preferred layout produced by ZoneFeaturesAnalyzer.analyze_zones_distribution()
    # statistics['duration_distribution']['overall']['median']
    dist = statistics.get("duration_distribution")
    if isinstance(dist, dict):
        overall = dist.get("overall")
        if isinstance(overall, dict):
            median = overall.get("median")
            if isinstance(median, (int, float)) and math.isfinite(median):
                return float(median)

    # Graceful fallback: if different statistics layout, return None
    return None


def _select_median_zone(zones: List, statistics: dict) -> Optional[Tuple[object, float]]:
    """Select the zone whose duration is closest to the median duration.

    Цель демо:
    - Выбрать «репрезентативную» зону для детального показа без ручного вмешательства.
    - Критерий репрезентативности — близость длительности к медиане по всему множеству зон.

    Алгоритм:
    1) Пытаемся взять медиану из result.statistics (если доступна).
    2) Если нет — считаем медиану локально по списку зон (устойчиво к формату статистики).
    3) Находим зону, чья длительность минимально отклоняется от медианы.

    Returns: (zone, duration_bars) или None, если выбор невозможен.
    """
    if not zones:
        return None

    median_bars = _get_statistics_median_bars(statistics)

    # Fallback: compute local median if statistics are missing
    durations: List[float] = []
    if median_bars is None:
        for z in zones:
            dur = _get_zone_duration_bars(z)
            if dur is not None:
                durations.append(dur)
        if not durations:
            return None
        durations_sorted = sorted(durations)
        n = len(durations_sorted)
        mid = n // 2
        if n % 2 == 1:
            median_bars = float(durations_sorted[mid])
        else:
            median_bars = float((durations_sorted[mid - 1] + durations_sorted[mid]) / 2.0)

    # Find closest zone by absolute difference
    best_zone = None
    best_zone_dur = None
    best_diff = float("inf")
    for z in zones:
        dur = _get_zone_duration_bars(z)
        if dur is None:
            continue
        diff = abs(dur - median_bars)
        if diff < best_diff:
            best_diff = diff
            best_zone = z
            best_zone_dur = dur

    if best_zone is None:
        return None
    return best_zone, float(best_zone_dur)


def _select_additional_zones(zones: List, base_zone_id: int, k: int = 1) -> List[int]:
    """Select additional zone IDs near the base zone for minimal demo comparison.

    Назначение:
    - Для компактной демонстрации comparison достаточно пары зон.
    - Берём соседние к базовой зоне (по порядку), чтобы высока была вероятность
      близости контекста и читаемости сравнения.

    Strategy: pick up to k nearest in index order different from base.
    """
    if not zones:
        return []
    ids = [getattr(z, "zone_id", idx) for idx, z in enumerate(zones)]
    if base_zone_id not in ids:
        return ids[:k]
    base_idx = ids.index(base_zone_id)
    candidates: List[int] = []
    # Try previous then next
    if base_idx - 1 >= 0:
        candidates.append(ids[base_idx - 1])
    if base_idx + 1 < len(ids):
        candidates.append(ids[base_idx + 1])
    return candidates[:k]


def main() -> None:
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
        if SAVE_IMAGES and save_figure(fig_overview, "01_overview"):
            nb.log(f"Saved: {OUTPUT_DIR / '01_overview.html'}")
    nb.wait()

    # ---------------------------------------------------------------------
    # Step 5: Detail Visualization (single zone by median duration)
    # ---------------------------------------------------------------------
    nb.step("Step 5: Detail Visualization (single zone)")
    # Детальный просмотр по одной зоне. Выбор делаем детерминированно: медианная длительность.
    with nb.error_handling("Selecting median-duration zone and rendering detail"):
        selection = _select_median_zone(result.zones, result.statistics)
        if not selection:
            nb.warning("Unable to select median-duration zone (insufficient statistics)")
        else:
            median_zone, median_dur = selection
            z_id = getattr(median_zone, "zone_id", 0)
            fig_detail_1 = result.visualize(
                "detail", zone_id=z_id, context_bars=20, title=f"Zone #{z_id} (≈ median duration: {median_dur:.1f} bars)"
            )
            nb.success(f"Detail figure for zone #{z_id} created (duration≈{median_dur:.1f} bars)")
            if SAVE_IMAGES and save_figure(fig_detail_1, "02_detail_median"):
                nb.log(f"Saved: {OUTPUT_DIR / '02_detail_median.html'}")
    nb.wait()

    # ---------------------------------------------------------------------
    # Step 6: Detail Visualization (second zone) and Comparison (minimal pair)
    # ---------------------------------------------------------------------
    nb.step("Step 6: Detail (second zone) and Comparison")
    # Для сравнения берём ещё одну «соседнюю» зону и строим минимальную пару.
    with nb.error_handling("Selecting an additional zone for comparison"):
        if selection:
            median_zone, _ = selection
            base_id = getattr(median_zone, "zone_id", 0)
            extra_ids = _select_additional_zones(result.zones, base_id, k=1)
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
                if SAVE_IMAGES and save_figure(fig_cmp, "03_comparison_pair"):
                    nb.log(f"Saved: {OUTPUT_DIR / '03_comparison_pair.html'}")
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
        if SAVE_IMAGES and save_figure(fig_stats, "04_statistics"):
            nb.log(f"Saved: {OUTPUT_DIR / '04_statistics.html'}")
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
        if selection:
            median_zone, _ = selection
            z_id = getattr(median_zone, "zone_id", 0)
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


if __name__ == "__main__":
    main()


