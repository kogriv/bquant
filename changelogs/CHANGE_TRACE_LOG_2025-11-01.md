# Change Trace Log 2025-11-01


[12:35:00] [bugfix] [Changed] bquant/analysis/zones/models.py - ZoneInfo.to_analyzer_format() now includes start_idx, end_idx, start_time, end_time for visualization

[12:35:05] [bugfix] [Changed] research/notebooks/04_zones_sample.py - added df.set_index('time') to ensure DatetimeIndex (fixes zone visualization)

[12:35:10] [debug] [Changed] bquant/visualization/zones.py - added DEBUG logging in _prepare_zone_data() for diagnostic purposes

[12:50:00] [config] [Changed] bquant/visualization/zones.py - show_zone_labels default changed from True to False (reduces chart clutter)

[13:15:00] [feature] [Changed] bquant/analysis/zones/models.py - ZoneAnalysisResult.visualize() now supports date_range parameter for 'overview' mode

[13:45:00] [feature] [Changed] bquant/visualization/zones.py - plot_zones_on_price_chart() now supports indicators display with show_indicators, indicator_columns, indicator_chart_types parameters

==================== COMMIT DIVIDER ====================

