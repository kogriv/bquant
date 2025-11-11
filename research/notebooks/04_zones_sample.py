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
        .with_strategies(swing="zigzag")
        .with_auto_swing_thresholds(True)
        .with_swing_scope("global")
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
#     fig_overview = result.visualize(
#         "overview",
#         title="Zones Overview (global swings)",
#         show_aggregate_metrics=True,
#         aggregate_metrics_mode="full",
#         show_swings=True,
#         swing_marker_size=9,
#         max_swings_to_display=400,
#     )
#     nb.success("Overview figure created")
#     if SAVE_IMAGES:
#         saved = save_figure(
#             fig_overview,
#             "01_overview",
#             output_dir=str(OUTPUT_DIR),
#             prefer=SAVE_IMAGE_FORMAT,
#         )
#         if saved:
#             nb.log(f"Saved: {saved}")
# nb.wait()

# ---------------------------------------------------------------------
# Step 3.1: Overview Visualization with Indicators
# ---------------------------------------------------------------------
nb.step("Overview Visualization with Indicators")
# Демонстрация нового функционала - отображение индикаторов в отдельной панели
# Автоматическое определение индикатора из зон (macd_hist) и выбор типа отображения
# with nb.error_handling("Creating overview figure with indicators"):
#     fig_overview_indicators = result.visualize(
#         "overview", 
#         title="Zones Overview with MACD Histogram (auto-detected)",
#         show_indicators=True,
#         show_aggregate_metrics=True,
#         aggregate_metrics_mode="full",
#         show_swings=True,
#         swing_marker_size=9
#         # Автоматически определяется macd_hist и показывается как bar (гистограмма)
#     )
#     nb.success("Overview figure with indicators created (auto-detected)")
#     if SAVE_IMAGES:
#         saved = save_figure(fig_overview_indicators, "01_overview_with_indicators", prefer=SAVE_IMAGE_FORMAT)
#         if saved:
#             nb.log(f"Saved: {saved}")
# nb.wait()

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
#         show_aggregate_metrics=True,
#         aggregate_metrics_mode="full",
#         show_swings=True,
#         swing_marker_size=9,
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
# Step 4: Overview Visualization for Date Range (Dense vs. Timeseries)
# ---------------------------------------------------------------------
# nb.step("Overview Visualization (Date Range: 25.06.2025 - 03.07.2025)")
# nb.log(f"Output directory for charts: {OUTPUT_DIR.resolve()}")

# with nb.error_handling("Creating overview figure for date range"):
#     # Создаем даты с тем же timezone, что и данные
#     tz = result.data.index.tz
#     start_date = pd.Timestamp('2025-06-25', tz=tz) if tz else pd.Timestamp('2025-06-25')
#     end_date = pd.Timestamp('2025-07-03', tz=tz) if tz else pd.Timestamp('2025-07-03')
    
#     # 1. Создаем график в режиме 'dense' (по умолчанию)
#     title_dense = f"Zones Overview (Dense Mode) - {start_date.strftime('%d.%m.%Y')} to {end_date.strftime('%d.%m.%Y')}"
#     fig_overview_dense = result.visualize(
#         "overview",
#         date_range=(start_date, end_date),
#         title=title_dense,
#         show_aggregate_metrics=True,
#         aggregate_metrics_mode="full",
#         show_swings=True,
#         swing_marker_size=9,
#         show_indicators=True,
#         time_axis_mode='dense' # Явно указываем для наглядности
#     )
#     nb.success("Created DENSE overview for date range.")
#     if SAVE_IMAGES:
#         saved = save_figure(fig_overview_dense, "01_overview_date_range_dense", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#         if saved:
#             nb.log(f"Saved dense chart: {saved}")

    # 2. Создаем график в режиме 'timeseries'
    # title_timeseries = f"Zones Overview (Timeseries Mode) - {start_date.strftime('%d.%m.%Y')} to {end_date.strftime('%d.%m.%Y')}"
    # fig_overview_timeseries = result.visualize(
    #     "overview",
    #     date_range=(start_date, end_date),
    #     title=title_timeseries,
    #     show_indicators=True,
    #     time_axis_mode='timeseries' # Используем новый режим
    # )
    # nb.success("Created TIMESERIES overview for date range.")
    # if SAVE_IMAGES:
    #     saved = save_figure(fig_overview_timeseries, "01_overview_date_range_timeseries", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
    #     if saved:
    #         nb.log(f"Saved timeseries chart: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 4: Detail Visualization (single zone by median duration)
# ---------------------------------------------------------------------
nb.step("Detail Visualization (single zone)")
# Детальный просмотр по одной зоне. Выбор делаем детерминированно: медианная длительность.
with nb.error_handling("Selecting median-duration zone and rendering detail"):
    # Получить медиану из статистики
    median_val = result.statistics['duration_distribution']['overall']['median']
    nb.log(f"Median duration: {median_val}")
    
    # Найти зону с длительностью, ближайшей к медиане
    candidates = [(z, z.features['duration']) for z in result.zones]
    base_zone, median_dur = min(candidates, key=lambda t: abs(t[1] - median_val))
    nb.log(f"Base zone: {base_zone}, median duration: {median_dur}")
    
    # z_id = getattr(base_zone, "zone_id", 0)
    # ZoneInfo — это @dataclass с обязательным полем zone_id: int, поэтому zone_id всегда есть.
    z_id = base_zone.zone_id
    nb.log(f"Selected Base zone - Zone ID: {z_id}")
    fig_detail_1 = result.visualize(
        "detail",
        zone_id=z_id,
        context_bars=20,  # количество баров слева/справа от зоны для контекста
        max_zone_detail_bars=500,  # ограничение на размер окна (предотвращает излишне длинные графики)
        title=f"Zone #{z_id} (≈ median duration: {median_dur:.1f} bars)",
        show_zone_metrics=True,  # новый текстовый блок с swing/shape метриками
        show_zone_stats=True,  # классическая статистика зоны (BC)
        metrics_annotation_position="top-left",  # положение текстового блока (paper-координаты)
        show_indicators=True,  # отдельная панель с индикаторами
        indicator_chart_types={"macd_hist": "bar"},  # принудительный тип отображения для выбранного индикатора
        indicator_palette=["#ff9900", "#3366cc"],  # кастомная палитра линий/баров индикаторов
        indicator_panel_height=0.28,  # доля высоты фигуры под индикаторы
        show_volume=True,  # отображать панель объёма
        volume_panel_height=0.22,  # доля высоты фигуры под объём
        show_swings=True,  # включаем новые маркеры swing-точек поверх графика
        swing_marker_size=12,  # размер треугольников свингов
        max_swings_to_display=250,  # ограничение по числу отображаемых свингов (prev. для производительности)
        time_axis_mode="dense",  # режим оси времени (dense/timeseries)
        xaxis_num_ticks=18,  # количество подписей на оси X в dense режиме
        chart_info={  # дополнительный блок с описание инструмента (если нужно)
            "symbol": "XAUUSD",
            "timeframe": "1H",
            "source": "TradingView via OANDA",
        },
    )
    nb.success(f"Detail figure for zone #{z_id} created (duration≈{median_dur:.1f} bars)")
    if SAVE_IMAGES:
        saved = save_figure(fig_detail_1, f"02_detail_{z_id}", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
        if saved:
            nb.log(f"Saved: {saved}")
nb.wait()

# ---------------------------------------------------------------------
# Step 5: Detail Visualization (second zone) and Comparison (minimal pair)
# ---------------------------------------------------------------------
# nb.step("Detail (second zone) and Comparison")
# # Для сравнения берём ещё одну «соседнюю» зону и строим минимальную пару.
# with nb.error_handling("Selecting an additional zone for comparison"):
#     # Получить медиану из статистики
#     median_val = result.statistics['duration_distribution']['overall']['median']
#     nb.log(f"Median duration: {median_val}")
    
#     # Найти зону с длительностью, ближайшей к медиане
#     candidates = [(z, z.features['duration']) for z in result.zones]
#     base_zone, median_dur = min(candidates, key=lambda t: abs(t[1] - median_val))
#     nb.log(f"Base zone: {base_zone}, median duration: {median_dur}")

#     if base_zone:

#         base_id = base_zone.zone_id
#         # Найти индекс base_zone в списке и взять следующую зону (или предыдущую, если это последняя)
#         base_idx = result.zones.index(base_zone)
#         z2 = result.zones[base_idx + 1].zone_id if base_idx + 1 < len(result.zones) else result.zones[base_idx - 1].zone_id
        
#         # Detail for the second zone
#         fig_detail_2 = result.visualize("detail", zone_id=z2, context_bars=5, title=f"Zone #{z2} (second for demo)")
#         if SAVE_IMAGES:
#             save_figure(fig_detail_2, f"02_detail_{z2}")
        
#         # Comparison for two zones

#         selected_zones = [z for z in result.zones if z.zone_id in [base_id, z2]]

#         visualizer = ZoneVisualizer(backend='plotly')
#         fig_cmp = visualizer.plot_zones_comparison(
#             result.data,  # ← price_data (OHLCV)
#             selected_zones,  # ← отфильтрованный список зон
#             max_zones=2,  # Максимальное количество зон для сравнения (по умолчанию 5)
#             title="Zones Comparison (2 zones)",  # Заголовок графика
#             # date_range=None,  # Опционально: фильтрация зон по диапазону дат (start, end)
#             show_indicators=True,  # Показывать индикаторы на отдельной панели (по умолчанию True)
#             show_volume=True,  # Показывать панель volume (по умолчанию True)
#             # indicator_columns=None,  # Опционально: явный список колонок индикаторов для отображения
#             # indicator_chart_types=None,  # Опционально: словарь {колонка: тип} для указания типа отображения
#             #                              # Типы: 'line' (линия) или 'bar' (столбики)
#             #                              # Пример: {'macd_hist': 'bar', 'rsi': 'line'}
#             #                              # Если не указано, автоматически определяется: 'bar' для колонок с 'hist', иначе 'line'
#             comparison_context=5,  # Количество контекстных баров вокруг каждой зоны (по умолчанию 30)
#             #                         # Контекстные бары - это бары до и после зоны для лучшего контекста
#             time_axis_mode='dense',  # Режим формирования меток оси X: 'dense' (по умолчанию) или 'timeseries'
#             #                         # 'dense' - позиционные индексы с метками времени (быстро, без анализа gaps)
#             #                         # 'timeseries' - datetime с rangebreaks (медленно, требует анализа gaps)
#             # volume_panel_height=0.25,  # Высота панели volume (0.0-1.0, по умолчанию 0.25)
#             # indicator_panel_height=0.3,  # Высота панели индикаторов (0.0-1.0, по умолчанию 0.3)
#         )
#         nb.success(f"Comparison figure created for zones #{base_id} and #{z2}")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_cmp, "03_comparison_pair", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")
        
#         # Comparison for 5 zones closest to median duration
#         nb.log("Finding 5 zones closest to median duration...")
#         candidates_sorted = sorted(candidates, key=lambda t: abs(t[1] - median_val))
#         median_zones = [z for z, _ in candidates_sorted[:5]]
#         median_zone_ids = [z.zone_id for z in median_zones]
#         nb.log(f"Selected 5 zones closest to median: {median_zone_ids}")
        
#         fig_cmp_5 = visualizer.plot_zones_comparison(
#             result.data,
#             median_zones,
#             max_zones=5,
#             title="Zones Comparison (5 zones closest to median duration)",
#             show_indicators=True,
#             show_volume=True,
#             comparison_context=5,
#             time_axis_mode='dense',
#         )
#         nb.success(f"Comparison figure created for 5 zones closest to median: {median_zone_ids}")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_cmp_5, "04_comparison_5_median", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")
#     else:
#         nb.warning("Skipping comparison due to missing base_zone")
# nb.wait()

# ---------------------------------------------------------------------
# Step 6: Statistics Visualization
# ---------------------------------------------------------------------
# nb.step("Statistics Visualization")
# # Агрегированные статистики по зонам (распределения, соотношения и т.п.).
# with nb.error_handling("Creating statistics figure"):
#     fig_stats = result.visualize("statistics", title="Zones Statistics")
#     nb.success("Statistics figure created")
#     if SAVE_IMAGES:
#         saved = save_figure(fig_stats, "04_statistics")
#         if saved:
#             nb.log(f"Saved: {saved}")
# nb.wait()

# ---------------------------------------------------------------------
# Step 7: Alternative Interfaces (ZoneVisualizer and Convenience Functions)
# ---------------------------------------------------------------------
# nb.step("Alternative Interfaces (Visualizer & Convenience)")
# # Полное покрытие интерфейсов визуализации с демонстрацией всех параметров:
# # - Прямой вызов методов ZoneVisualizer (overview, detail, comparison)
# # - Convenience-функции (те же визуализации без явного создания инстанса)
# with nb.error_handling("Creating figures via ZoneVisualizer and convenience functions"):
#     # Получить медиану из статистики для выбора зоны
#     median_val = result.statistics['duration_distribution']['overall']['median']
#     nb.log(f"Median duration: {median_val}")
    
#     # Найти зону с длительностью, ближайшей к медиане
#     candidates = [(z, z.features['duration']) for z in result.zones]
#     base_zone, median_dur = min(candidates, key=lambda t: abs(t[1] - median_val))
#     nb.log(f"Base zone: {base_zone}, median duration: {median_dur}")
    
#     if base_zone is not None:
#         median_zone = base_zone
#         z_id = getattr(base_zone, "zone_id", 0)
#         visualizer = ZoneVisualizer(backend='plotly')
        
#         # ============================================================
#         # 1. plot_zones_on_price_chart() - Overview режим
#         # ============================================================
#         nb.substep("Overview Chart (plot_zones_on_price_chart)")
#         nb.log("Creating overview chart with full parameters...")
#         fig_overview = visualizer.plot_zones_on_price_chart(
#             result.data,  # ← price_data (OHLCV DataFrame)
#             result.zones,  # ← zones_data (список зон для отображения)
#             title="Zones Overview - Full Parameters Demo",  # Заголовок графика
#             show_indicators=True,  # Показывать индикаторы на отдельной панели (по умолчанию False)
#             # indicator_columns=None,  # Опционально: явный список колонок индикаторов для отображения
#             #                          # Если None, автоматически определяется из indicator_context зон
#             # indicator_chart_types=None,  # Опционально: словарь {колонка: тип} для указания типа отображения
#             #                              # Типы: 'line' (линия) или 'bar' (столбики)
#             #                              # Пример: {'macd_hist': 'bar', 'rsi': 'line'}
#             #                              # Если не указано, автоматически определяется: 'bar' для колонок с 'hist', иначе 'line'
#             show_gap_lines=False,  # Показывать вертикальные пунктирные линии для разрывов (выходные) (по умолчанию False)
#             xaxis_num_ticks=16,  # Количество меток на оси X (по умолчанию 16). Автоматически корректируется на основе диапазона данных
#             time_axis_mode='dense',  # Режим оси времени: 'dense' (по умолчанию) или 'timeseries'
#             #                          # 'dense' - позиционные индексы с метками времени (быстро, без анализа gaps)
#             #                          # 'timeseries' - datetime с rangebreaks (медленно, требует анализа gaps)
#             # chart_info=None,  # Опционально: словарь с метаданными {'symbol': str, 'timeframe': str, 'source': str}
#             #                     # Автоматически отображается на графике, если указан
#         )
#         nb.success("Overview chart created")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_overview, "05_overview_full_params", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")
        
#         # ============================================================
#         # 2. plot_zone_detail() via ZoneVisualizer - Детальная визуализация
#         # ============================================================
#         nb.substep("Detail Chart via ZoneVisualizer (plot_zone_detail)")
#         nb.log("Creating detail chart via ZoneVisualizer with full parameters...")
#         fig_detail_v = visualizer.plot_zone_detail(
#             result.data,  # ← price_data (OHLCV DataFrame)
#             median_zone,  # ← zone (зона для детального просмотра)
#             context_bars=30,  # Количество баров до/после зоны для контекста (по умолчанию 20)
#             title=f"Zone #{z_id} Detail - Visualizer (Full Params)",  # Заголовок графика
#             show_indicators=True,  # Показывать индикаторы на отдельной панели (по умолчанию True)
#             show_volume=True,  # Показывать панель volume (по умолчанию True)
#             time_axis_mode='dense',  # Режим оси времени: 'dense' (по умолчанию) или 'timeseries'
#             #                          # 'dense' - позиционные индексы с метками времени (быстро, без анализа gaps)
#             #                          # 'timeseries' - datetime с rangebreaks (медленно, требует анализа gaps)
#             xaxis_num_ticks=16,  # Количество меток на оси X (по умолчанию 16). Используется только в dense режиме
#             #                      # Автоматически корректируется на основе диапазона данных для оптимальной читаемости
#             # indicator_columns=None,  # Опционально: явный список колонок индикаторов для отображения
#             #                          # Если None, автоматически определяются из zone.indicator_context и zone.features
#             # indicator_chart_types=None,  # Опционально: словарь {колонка: тип} для указания типа отображения
#             #                              # Типы: 'line' (линия) или 'bar' (столбики)
#             #                              # Пример: {'macd_hist': 'bar', 'rsi': 'line'}
#             # max_zone_detail_bars=500,  # Максимальное количество баров (truncate если больше, по умолчанию 500)
#             # volume_panel_height=0.25,  # Высота панели volume (0.0-1.0, по умолчанию 0.25)
#             # indicator_panel_height=0.3,  # Высота панели индикаторов (0.0-1.0, по умолчанию 0.3)
#             # chart_info=None,  # Опционально: словарь с метаданными {'symbol': str, 'timeframe': str, 'source': str}
#         )
#         nb.success(f"Detail chart created for zone #{z_id}")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_detail_v, "05_detail_visualizer", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")

#         # ============================================================
#         # 3. plot_zone_detail() via Convenience Function
#         # ============================================================
#         nb.substep("Detail Chart via Convenience Function (plot_zone_detail)")
#         nb.log("Creating detail chart via convenience function...")
#         fig_detail_c = plot_zone_detail(
#             result.data,  # ← price_data (OHLCV DataFrame)
#             median_zone,  # ← zone (зона для детального просмотра)
#             context_bars=15,  # Количество баров до/после зоны для контекста
#             title=f"Zone #{z_id} Detail - Convenience Function",  # Заголовок графика
#             backend='plotly',  # Backend визуализации: 'plotly' (по умолчанию) или 'matplotlib'
#             show_indicators=True,  # Показывать индикаторы на отдельной панели
#             show_volume=True,  # Показывать панель volume
#             # Все остальные параметры аналогичны plot_zone_detail() метода ZoneVisualizer
#             # (см. пример выше)
#         )
#         nb.success("Detail chart created via convenience function")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_detail_c, "05_detail_convenience", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")

#         # ============================================================
#         # 4. plot_zones_comparison() via ZoneVisualizer - Сравнение зон
#         # ============================================================
#         nb.substep("Comparison Chart via ZoneVisualizer (plot_zones_comparison)")
#         nb.log("Creating comparison chart via ZoneVisualizer with full parameters...")
#         selected_zones_for_comparison = result.zones[:4]  # Берем первые 4 зоны для примера
#         fig_cmp_v = visualizer.plot_zones_comparison(
#             result.data,  # ← price_data (OHLCV DataFrame)
#             selected_zones_for_comparison,  # ← zones_data (список зон для сравнения)
#             max_zones=4,  # Максимальное количество зон для сравнения (по умолчанию 5)
#             # date_range=None,  # Опционально: фильтрация зон по диапазону дат (start, end)
#             #                   # Формат: (datetime, datetime) - зоны вне диапазона отфильтровываются
#             title="Zones Comparison - Visualizer (Full Params)",  # Заголовок графика
#             show_indicators=True,  # Показывать индикаторы на отдельной панели (по умолчанию True)
#             show_volume=True,  # Показывать панель volume (по умолчанию True)
#             # indicator_columns=None,  # Опционально: явный список колонок индикаторов для отображения
#             # indicator_chart_types=None,  # Опционально: словарь {колонка: тип} для указания типа отображения
#             #                              # Типы: 'line' (линия) или 'bar' (столбики)
#             #                              # Пример: {'macd_hist': 'bar', 'rsi': 'line'}
#             #                              # Если не указано, автоматически определяется: 'bar' для колонок с 'hist', иначе 'line'
#             comparison_context=5,  # Количество контекстных баров вокруг каждой зоны (по умолчанию 30)
#             #                         # Контекстные бары - это бары до и после зоны для лучшего контекста
#             #                         # В comparison mode каждая зона отображается в своем отдельном вертикальном блоке
#             time_axis_mode='dense',  # Режим формирования меток оси X: 'dense' (по умолчанию) или 'timeseries'
#             #                         # 'dense' - позиционные индексы с метками времени (быстро, без анализа gaps)
#             #                         # 'timeseries' - datetime с rangebreaks (медленно, требует анализа gaps)
#             # volume_panel_height=0.25,  # Высота панели volume (0.0-1.0, по умолчанию 0.25)
#             # indicator_panel_height=0.3,  # Высота панели индикаторов (0.0-1.0, по умолчанию 0.3)
#             # chart_info=None,  # Опционально: словарь с метаданными {'symbol': str, 'timeframe': str, 'source': str}
#         )
#         nb.success("Comparison chart created via ZoneVisualizer")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_cmp_v, "05_comparison_visualizer", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")

#         # ============================================================
#         # 5. plot_zones_comparison() via Convenience Function
#         # ============================================================
#         nb.substep("Comparison Chart via Convenience Function (plot_zones_comparison)")
#         nb.log("Creating comparison chart via convenience function...")
#         fig_cmp_c = plot_zones_comparison(
#             result.data,  # ← price_data (OHLCV DataFrame)
#             result.zones[:3],  # ← zones_data (список зон для сравнения)
#             max_zones=3,  # Максимальное количество зон для сравнения
#             # date_range=None,  # Опционально: фильтрация зон по диапазону дат
#             title="Zones Comparison - Convenience Function",  # Заголовок графика
#             backend='plotly',  # Backend визуализации: 'plotly' (по умолчанию) или 'matplotlib'
#             show_indicators=True,  # Показывать индикаторы на отдельной панели
#             show_volume=True,  # Показывать панель volume
#             comparison_context=5,  # Количество контекстных баров вокруг каждой зоны
#             time_axis_mode='dense',  # Режим формирования меток оси X
#             # Все остальные параметры аналогичны plot_zones_comparison() метода ZoneVisualizer
#             # (см. пример выше)
#         )
#         nb.success("Comparison chart created via convenience function")
#         if SAVE_IMAGES:
#             saved = save_figure(fig_cmp_c, "05_comparison_convenience", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")
#     else:
#         nb.warning("Skipping visualization due to missing base_zone")
# nb.wait()

# ---------------------------------------------------------------------
# Step 8: Custom Configuration Demo - Comprehensive Example
# ---------------------------------------------------------------------
# nb.step("Custom Configuration - Full API Demo")
# # Полная демонстрация всех параметров настройки ZoneVisualizer.
# # Этот пример служит справочником по всем доступным опциям кастомизации.
# with nb.error_handling("Creating fully customized visualizations"):
#     if result.zones:
#         # Выбираем зону для демонстрации
#         target_zone = result.zones[2] if len(result.zones) > 2 else result.zones[0]
#         z_id = target_zone.zone_id
#         nb.log(f"Using zone #{z_id} for custom configuration demo")

#         # ============================================================
#         # 1. ZoneVisualizer __init__: Параметры инициализации
#         # ============================================================
#         nb.substep("Creating Custom ZoneVisualizer")
#         custom_vis = ZoneVisualizer(
#             # --- Backend ---
#             backend='plotly',  # 'plotly' (default) | 'matplotlib'
#             #                  # Plotly: интерактивные графики, экспорт в HTML/PNG
#             #                  # Matplotlib: статические графики, больше контроля над стилем

#             # --- Размеры графика ---
#             width=1400,        # Ширина в пикселях (default: 1200)
#             #                  # Рекомендуется: 1200-1600 для detail, 1600-2000 для comparison
#             height=900,        # Высота в пикселях (default: 800)
#             #                  # Автоматически масштабируется для multi-panel (price+indicators+volume)

#             # --- Отображение зон ---
#             show_zone_labels=True,   # Показывать метки "Zone N" над зонами (default: False)
#             #                        # True: добавляет аннотацию с zone_id над зоной
#             #                        # Полезно при сравнении нескольких зон
#             show_zone_stats=True,    # Показывать статистику зоны в углу (default: True)
#             #                        # Отображает: Type, Duration, Strength (если есть)
#             #                        # Позиция: левый верхний угол графика
#             opacity=0.4,             # Прозрачность заливки зон: 0.0-1.0 (default: 0.3)
#             #                        # 0.0: полностью прозрачная (видны только границы)
#             #                        # 0.3-0.4: оптимально для чтения свечей
#             #                        # 1.0: полностью непрозрачная (скрывает свечи)

#             # --- Контекстные бары (дефолты для методов) ---
#             zone_detail_context=25,       # Кол-во баров до/после зоны в plot_zone_detail (default: 40)
#             #                             # Переопределяется параметром context_bars метода
#             #                             # Рекомендуется: 20-50 для краткосрочных, 50-100 для долгосрочных
#             max_zone_detail_bars=500,     # Максимум баров в detail (default: 500)
#             #                             # Если зона+контекст превышает лимит - обрезается с обеих сторон
#             #                             # Защита от перегрузки при очень длинных зонах
#             comparison_context=30,        # Контекстные бары для comparison (default: 30)
#             max_comparison_zones=6,       # Максимум зон в comparison (default: 6)
#             #                             # Больше 6 зон: график становится нечитаемым

#             # --- Высота панелей (относительные значения 0.0-1.0) ---
#             volume_panel_height=0.25,     # Высота панели volume: 0.0-1.0 (default: 0.25)
#             #                             # 0.0: volume не отображается (даже если show_volume=True)
#             #                             # 0.15-0.20: минимально для читаемости
#             #                             # 0.25-0.30: оптимально
#             #                             # Остаток делится между price и indicators
#             # indicator_panel_height=0.3, # Высота панели индикаторов (default: 0.3)
#             #                             # Закомментировано - используется дефолт
#             #                             # При наличии indicators: price получает 1.0 - volume - indicator

#             # --- Палитра цветов для индикаторов ---
#             indicator_palette=[           # Список цветов для множественных индикаторов (default: plotly default)
#                 '#1f77b4',  # Синий
#                 '#ff7f0e',  # Оранжевый
#                 '#2ca02c',  # Зелёный
#                 '#d62728',  # Красный
#                 '#9467bd',  # Фиолетовый
#                 '#8c564b',  # Коричневый
#                 '#e377c2',  # Розовый
#                 '#7f7f7f',  # Серый
#                 '#bcbd22',  # Жёлто-зелёный
#                 '#17becf',  # Бирюзовый
#             ],
#             #                             # Цвета применяются циклически если индикаторов больше
#             #                             # Формат: hex-код '#RRGGBB'
#         )
#         nb.success(f"Created ZoneVisualizer with custom configuration")

#         # ============================================================
#         # 2. plot_zone_detail: Детальный просмотр одной зоны
#         # ============================================================
#         nb.substep("plot_zone_detail with Full Parameters")
#         fig_detail = custom_vis.plot_zone_detail(
#             # --- Обязательные параметры ---
#             price_data=result.data,      # OHLCV DataFrame с колонками: time, open, high, low, close, volume
#             #                            # Может содержать дополнительные колонки индикаторов (macd, rsi, etc)
#             zone=target_zone,            # ZoneInfo | Dict | объект с атрибутами start/end
#             #                            # Должен содержать: start_time, end_time, type
#             #                            # Опционально: zone_id, duration, features, indicator_context

#             # --- Параметры отображения ---
#             context_bars=25,             # Кол-во баров до/после зоны для контекста (default: 20)
#             #                            # Переопределяет zone_detail_context из __init__
#             #                            # None: использует дефолт из конфигурации
#             #                            # 0: только зона, без контекста
#             #                            # 10-20: минимальный контекст
#             #                            # 30-50: оптимальный контекст
#             #                            # >100: может быть обрезано до max_zone_detail_bars
#             title=f'Custom Zone #{z_id} Detail - Full Configuration',  # Заголовок графика
#             show_indicators=True,        # Показывать индикаторы на отдельной панели (default: True)
#             #                            # True: создаёт отдельную панель под графиком цены
#             #                            # False: только цена и volume (если show_volume=True)
#             #                            # Индикаторы auto-определяются из zone.indicator_context и zone.features
#             show_volume=True,            # Показывать панель volume (default: True)
#             #                            # True: создаёт панель volume внизу
#             #                            # False: только цена и indicators
#             #                            # Автоматически отключается если volume колонки нет или все NaN

#             # --- Режим оси времени ---
#             time_axis_mode='dense',      # Режим отображения оси X: 'dense' | 'timeseries' (default: 'dense')
#             #                            # 'dense': позиционные индексы (0,1,2...) с метками времени
#             #                            #          Быстро, без gap анализа, равномерное распределение
#             #                            #          Рекомендуется для большинства случаев
#             #                            # 'timeseries': реальные datetime значения с rangebreaks
#             #                            #               Медленно, требует анализа gaps (weekends, holidays)
#             #                            #               Используйте когда важна точная временная шкала
#             xaxis_num_ticks=16,          # Количество меток на оси X (default: 16)
#             #                            # Используется только в 'dense' режиме
#             #                            # Автоматически корректируется для оптимальной читаемости
#             #                            # 10-15: для коротких диапазонов (<50 баров)
#             #                            # 16-20: для средних диапазонов (50-200 баров)
#             #                            # 20-30: для длинных диапазонов (>200 баров)

#             # --- Дополнительные параметры (через kwargs) ---
#             # indicator_columns=['macd_hist', 'macd_signal'],  # Явный список колонок индикаторов
#             #                            # None (default): автоопределение из zone.indicator_context и features
#             #                            # ['col1', 'col2']: использовать только указанные колонки
#             #                            # []: отключить индикаторы (эквивалентно show_indicators=False)

#             indicator_chart_types={      # Словарь {column_name: chart_type} для типов графиков
#                 'macd_hist': 'bar',      # 'bar': столбчатая гистограмма (для hist, volume-like)
#                 # 'macd_signal': 'line', # 'line': линейный график (default для всех остальных)
#                 # 'rsi': 'line',
#             },
#             #                            # None (default): auto-определение ('bar' для колонок с 'hist', иначе 'line')
#             #                            # Полезно для переопределения автоматического поведения

#             # max_zone_detail_bars=500,  # Переопределить лимит баров (default: из __init__)
#             #                            # Если зона+контекст > max_bars: обрезается равномерно с обеих сторон

#             # volume_panel_height=0.25,  # Переопределить высоту volume панели (default: из __init__)
#             # indicator_panel_height=0.3,# Переопределить высоту indicator панели (default: 0.3)

#             chart_info={                 # Метаданные для отображения на графике
#                 'symbol': 'XAUUSD',      # Символ инструмента
#                 'timeframe': '1H',       # Таймфрейм
#                 'source': 'OANDA via TradingView',  # Источник данных
#             },
#             #                            # Отображается в правом верхнем углу графика
#             #                            # None (default): метаданные не показываются
#             #                            # Словарь может содержать любые ключи, отображаются: symbol, timeframe, source
#         )
#         nb.success(f"Created detailed zone chart with full configuration")

#         if SAVE_IMAGES:
#             saved = save_figure(
#                 fig_detail,
#                 "08_custom_detail_full",
#                 output_dir=str(OUTPUT_DIR),
#                 prefer=SAVE_IMAGE_FORMAT,
#                 # width=1400,  # Переопределить ширину для PNG экспорта
#                 # height=900,  # Переопределить высоту для PNG экспорта
#             )
#             if saved:
#                 nb.log(f"Saved: {saved}")

#         # ============================================================
#         # 3. plot_zones_on_price_chart: Overview с несколькими зонами
#         # ============================================================
#         nb.substep("plot_zones_on_price_chart - Custom Overview")
#         # Выбираем первые 3 зоны для overview
#         overview_zones = result.zones[:3] if len(result.zones) >= 3 else result.zones

#         fig_overview = custom_vis.plot_zones_on_price_chart(
#             # --- Обязательные параметры ---
#             price_data=result.data,      # OHLCV DataFrame
#             zones_data=overview_zones,   # List[ZoneInfo] | List[Dict] | DataFrame
#             #                            # Может быть списком зон или DataFrame с колонками зон

#             # --- Параметры отображения ---
#             title='Custom Overview - Multiple Zones',
#             show_indicators=False,       # Индикаторы обычно не показывают в overview (слишком загружено)
#             #                            # True: добавить панель индикаторов (берутся из первой зоны)
#             show_volume=False,           # Volume также часто отключают в overview
#             time_axis_mode='dense',      # 'dense' быстрее для больших диапазонов
#             xaxis_num_ticks=20,          # Больше меток для overview (длинный диапазон)

#             # indicator_columns=None,    # Если show_indicators=True, можно указать колонки
#             # indicator_chart_types=None,
#             chart_info={
#                 'symbol': 'XAUUSD',
#                 'timeframe': '1H',
#                 'source': 'Sample Data',
#             },
#         )
#         nb.success(f"Created overview chart with {len(overview_zones)} zones")

#         if SAVE_IMAGES:
#             saved = save_figure(fig_overview, "08_custom_overview", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")

#         # ============================================================
#         # 4. plot_zones_comparison: Сравнение зон
#         # ============================================================
#         nb.substep("plot_zones_comparison - Zone Comparison")
#         # Выбираем 2-3 зоны для сравнения
#         comparison_zones = result.zones[:3] if len(result.zones) >= 3 else result.zones

#         fig_comparison = custom_vis.plot_zones_comparison(
#             # --- Обязательные параметры ---
#             price_data=result.data,      # OHLCV DataFrame
#             zones_data=comparison_zones, # List[ZoneInfo] | List[Dict]
#             #                            # Рекомендуется: 2-4 зоны для читаемости
#             #                            # Максимум: max_comparison_zones (default: 6)

#             # --- Параметры отображения ---
#             title='Custom Comparison - Zone Analysis',
#             show_indicators=True,        # Индикаторы полезны в comparison для анализа паттернов
#             show_volume=True,            # Volume помогает оценить силу зон
#             time_axis_mode='dense',
#             xaxis_num_ticks=16,

#             # context_bars=30,           # Переопределить comparison_context из __init__
#             indicator_chart_types={'macd_hist': 'bar'},
#             chart_info={'symbol': 'XAUUSD', 'timeframe': '1H'},
#         )
#         nb.success(f"Created comparison chart with {len(comparison_zones)} zones")

#         if SAVE_IMAGES:
#             saved = save_figure(fig_comparison, "08_custom_comparison", output_dir=str(OUTPUT_DIR), prefer=SAVE_IMAGE_FORMAT)
#             if saved:
#                 nb.log(f"Saved: {saved}")
#     else:
#         nb.warning("No zones found, skipping custom configuration demo")
# nb.wait()

nb.finish(message="Done")

