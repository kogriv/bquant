"""
Скрипт с тестированием функционала анлиза и визуализации зон на sample-данных
"""
from datetime import datetime
import pandas as pd
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
SAVE_IMAGES = True


# -----------------------------------------------------------------------------
# Saving configuration
# -----------------------------------------------------------------------------
# Options:
#   - "html": always save Plotly as HTML (no external deps), Matplotlib as PNG
#   - "png":  try to save Plotly as PNG (requires kaleido); on failure fallback to HTML
#              Matplotlib remains PNG
SAVE_IMAGE_FORMAT = "png"  # set to "png" to prefer PNG (Plotly falls back to HTML if unavailable)

# use package save_figure directly

# Output directory - относительно текущего скрипта
OUTPUT_DIR = Path(__file__).parent / "outputs" / "vis" / Path(__file__).stem

nb = NotebookSimulator("Zones Visualization Demo. Crafting")


# ---------------------------------------------------------------------
# Step 1: Data Loading (sample data only)
# ---------------------------------------------------------------------
nb.step("Data Loading")
# Используем встроенный датасет (без внешних путей):
# - соблюдаем правила проекта (повторяемость, CI-friendly)
# - исключаем нефиксируемые внешние зависимости
with nb.error_handling("Loading sample data"):
    df = get_sample_data("tv_xauusd_1h")
    # ВАЖНО: Устанавливаем 'time' как индекс для правильной работы визуализации зон
    # Визуализатор использует start_time/end_time из индекса, а не из колонок
    if 'time' in df.columns:
        df = df.set_index('time')
    nb.success(f"Loaded sample dataset: tv_xauusd_1h, shape={df.shape}")
    nb.log(str(df.head()))

nb.wait()

# ---------------------------------------------------------------------
# Step 2: Zone Analysis Pipeline (Universal)
# ---------------------------------------------------------------------
nb.step("Zone Analysis Pipeline")
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
# Step 3: Overview Visualization
# ---------------------------------------------------------------------
# nb.step("Overview Visualization")
# # Режим 'overview' показывает все зоны на цене — первичный обзор.
# with nb.error_handling("Creating overview figure"):
#     fig_overview = result.visualize("overview", title="Zones Overview")
#     nb.success("Overview figure created")
#     if SAVE_IMAGES:
#         saved = save_figure(fig_overview, "01_overview")
#         if saved:
#             nb.log(f"Saved: {saved}")
# nb.wait()

# ---------------------------------------------------------------------
# Step 3.1: Overview Visualization with Indicators
# ---------------------------------------------------------------------
nb.step("Overview Visualization with Indicators")
# Демонстрация нового функционала - отображение индикаторов в отдельной панели
# Автоматическое определение индикатора из зон (macd_hist) и выбор типа отображения
with nb.error_handling("Creating overview figure with indicators"):
    fig_overview_indicators = result.visualize(
        "overview", 
        title="Zones Overview with MACD Histogram (auto-detected)",
        show_indicators=True
        # Автоматически определяется macd_hist и показывается как bar (гистограмма)
    )
    nb.success("Overview figure with indicators created (auto-detected)")
    if SAVE_IMAGES:
        saved = save_figure(fig_overview_indicators, "01_overview_with_indicators")
        if saved:
            nb.log(f"Saved: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 3.2: Overview Visualization with Explicit Indicator Types
# ---------------------------------------------------------------------
# nb.step("Overview Visualization with Explicit Indicator Configuration")
# # Демонстрация явного указания типа отображения индикаторов
# with nb.error_handling("Creating overview figure with explicit indicator types"):
#     fig_overview_explicit = result.visualize(
#         "overview",
#         title="Zones Overview with MACD Histogram (explicit config)",
#         show_indicators=True,
#         indicator_columns=['macd_hist'],
#         indicator_chart_types={'macd_hist': 'bar'}  # Явно указываем тип - столбики
#     )
#     nb.success("Overview figure with explicit indicator types created")
#     if SAVE_IMAGES:
#         saved = save_figure(fig_overview_explicit, "01_overview_with_indicators_explicit")
#         if saved:
#             nb.log(f"Saved: {saved}")
# nb.wait()

# ---------------------------------------------------------------------
# Step 4: Overview Visualization for Date Range
# ---------------------------------------------------------------------
nb.step("Overview Visualization (Date Range: 25.06.2025 - 03.07.2025)")
with nb.error_handling("Creating overview figure for date range"):
    # Создаем даты с тем же timezone, что и данные
    tz = result.data.index.tz
    start_date = pd.Timestamp('2025-06-25', tz=tz) if tz else pd.Timestamp('2025-06-25')
    end_date = pd.Timestamp('2025-07-03', tz=tz) if tz else pd.Timestamp('2025-07-03')
    
    # Используем встроенную поддержку date_range в API
    # symbol, timeframe, source автоматически извлекаются из метаданных
    fig_overview_range = result.visualize(
        "overview",
        date_range=(start_date, end_date),
        title=f"Zones Overview ({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})",
        show_indicators=True
    )
    nb.success("Overview figure for date range created")
    if SAVE_IMAGES:
        saved = save_figure(fig_overview_range, "01_overview_date_range", output_dir=str(OUTPUT_DIR))
        if saved:
            nb.log(f"Saved: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 4: Detail Visualization (single zone by median duration)
# ---------------------------------------------------------------------
# nb.step("Detail Visualization (single zone)")
# # Детальный просмотр по одной зоне. Выбор делаем детерминированно: медианная длительность.
# with nb.error_handling("Selecting median-duration zone and rendering detail"):
#     # Получить медиану из статистики
#     median_val = result.statistics['duration_distribution']['overall']['median']
#     nb.log(f"Median duration: {median_val}")
    
#     # Найти зону с длительностью, ближайшей к медиане
#     candidates = [(z, z.features['duration']) for z in result.zones]
#     base_zone, median_dur = min(candidates, key=lambda t: abs(t[1] - median_val))
#     nb.log(f"Base zone: {base_zone}, median duration: {median_dur}")
    
#     # z_id = getattr(base_zone, "zone_id", 0)
#     # ZoneInfo — это @dataclass с обязательным полем zone_id: int, поэтому zone_id всегда есть.
#     z_id = base_zone.zone_id
#     nb.log(f"Selected Base zone - Zone ID: {z_id}")
#     fig_detail_1 = result.visualize(
#         "detail", zone_id=z_id, context_bars=5, title=f"Zone #{z_id} (≈ median duration: {median_dur:.1f} bars)"
#     )
#     nb.success(f"Detail figure for zone #{z_id} created (duration≈{median_dur:.1f} bars)")
#     if SAVE_IMAGES:
#         saved = save_figure(fig_detail_1, f"02_detail_{z_id}")
#         if saved:
#             nb.log(f"Saved: {saved}")
# nb.wait()

# # ---------------------------------------------------------------------
# # Step 5: Detail Visualization (second zone) and Comparison (minimal pair)
# # ---------------------------------------------------------------------
# nb.step("Detail (second zone) and Comparison")
# # Для сравнения берём ещё одну «соседнюю» зону и строим минимальную пару.
# with nb.error_handling("Selecting an additional zone for comparison"):
#     if base_zone:
#         base_id = base_zone.zone_id
#         # Найти индекс base_zone в списке и взять следующую зону (или предыдущую, если это последняя)
#         base_idx = result.zones.index(base_zone)
#         z2 = result.zones[base_idx + 1].zone_id if base_idx + 1 < len(result.zones) else result.zones[base_idx - 1].zone_id
        
#         # Detail for the second zone
#         fig_detail_2 = result.visualize("detail", zone_id=z2, context_bars=20, title=f"Zone #{z2} (second for demo)")
#         if SAVE_IMAGES:
#             save_figure(fig_detail_2, f"02_detail_{z2}")
        
#         # Comparison for two zones

#         selected_zones = [z for z in result.zones if z.zone_id in [base_id, z2]]

#         visualizer = ZoneVisualizer(backend='plotly')
#         fig_cmp = visualizer.plot_zones_comparison(
#             result.data,  # ← price_data (OHLCV)
#             selected_zones,  # ← отфильтрованный список зон
#             max_zones=2,
#             title="Zones Comparison (2 zones)"
#         )
#         nb.success(f"Comparison figure created for zones #{base_id} and #{z2}")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_cmp, "03_comparison_pair")
#             if saved:
#                 nb.log(f"Saved: {saved}")
#     else:
#         nb.warning("Skipping comparison due to missing base_zone")
# nb.wait()

nb.finish(message="Done")

