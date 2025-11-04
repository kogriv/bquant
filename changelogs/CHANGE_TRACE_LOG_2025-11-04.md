# Change Trace Log 2025-11-04

[19:30:00] [feature] [Changed] bquant/visualization/zones.py - Changed from DatetimeIndex to positional indices for dense charts (no weekend gaps)
[19:30:00] [feature] [Changed] bquant/visualization/zones.py - Added show_gap_lines parameter to display vertical dotted lines for data gaps (weekends)
[19:30:00] [feature] [Changed] bquant/visualization/zones.py - X-axis now shows dates as labels on positional indices (dense chart with date labels)
[19:45:00] [feature] [Changed] bquant/visualization/zones.py - Improved X-axis labels: two-level format (date on top, time below) with horizontal alignment
[19:45:00] [feature] [Changed] bquant/visualization/zones.py - Smart tick count determination based on data range (8-20 ticks, optimal 12-16)
[19:45:00] [feature] [Changed] bquant/visualization/zones.py - Added xaxis_num_ticks parameter (default 16) for user control over tick count
[20:00:00] [feature] [Changed] bquant/visualization/zones.py - For large ranges (>1 month): year shown separately on first level (at start and when year changes), date without year on second level
[20:15:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed vertical grid lines not showing on indicator panel (added explicit showgrid=True and grid settings for xaxis2)
[20:30:00] [feature] [Changed] bquant/visualization/utils.py - Implemented find_all_gaps function: analyzes DatetimeIndex, finds gaps, returns ISO strings for Plotly rangebreaks
[20:30:00] [feature] [Changed] bquant/visualization/zones.py - Implemented timeseries mode: DatetimeIndex-based charts with rangebreaks for preserving temporal proportionality
[20:30:00] [feature] [Changed] bquant/visualization/zones.py - Added time_axis_mode parameter (default 'dense') to choose between dense and timeseries visualization modes
[20:30:00] [feature] [Changed] bquant/visualization/zones.py - Added indicator support in timeseries mode (second panel with bars/lines using DatetimeIndex)
[20:30:00] [bugfix] [Changed] research/notebooks/04_zones_sample.py - Fixed HTML saving: use SAVE_IMAGE_FORMAT parameter in save_figure calls
[20:45:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed timeseries mode: proper rangebreaks format (list of dicts with bounds), explicit type='date' for x-axis
[20:00:00] [changed] [Changed] research/notebooks/04_zones_sample.py - Added show_gap_lines=True to demo visualization

==================== COMMIT DIVIDER ====================

[17:40:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed indicators not showing in detail mode: added show_indicators parameter (default True) to plot_zone_detail; indicators now displayed on separate panel (row=2) with proper row assignment; added indicator_chart_types support (bar for 'hist' columns, line for others); added vertical grid lines for all panels
[17:40:00] [bugfix] [Changed] research/notebooks/04_zones_sample.py - Fixed save_figure call for detail visualization: added output_dir and prefer parameters
[17:50:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed indicators in detail mode: indicators now taken from full window range (window_df) instead of zone data only, ensuring indicators are displayed for entire displayed range including context bars
[17:50:00] [feature] [Changed] bquant/visualization/zones.py - Added show_volume parameter (default True) to plot_zone_detail for optional volume panel display in detail mode
[18:00:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed comparison mode: indicators now displayed on separate panel (row=2) instead of price panel (row=1), preventing price chart compression; added support for indicator_chart_types (bar for 'hist' columns, line for others)
[18:00:00] [feature] [Changed] bquant/visualization/zones.py - Added show_indicators, show_volume, indicator_columns, indicator_chart_types parameters to plot_zones_comparison for full control over comparison visualization
[18:15:00] [feature] [Changed] bquant/visualization/zones.py - Implemented separate vertical blocks for each zone in comparison mode: each zone with context displayed in its own block with gaps between blocks (dense mode with positional indices)
[18:15:00] [feature] [Changed] bquant/visualization/zones.py - Zone rectangles in comparison mode now capture only the zone itself (not the entire context block), using zone start_time and end_time for precise positioning
[18:15:00] [feature] [Changed] bquant/visualization/zones.py - Indicators in comparison mode displayed for full block range (with context), not just the zone
[18:20:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed detail mode: indicators now displayed on separate panel (row=2/3) instead of price panel, preventing price chart compression; added dynamic panel creation based on show_indicators and show_volume
[18:20:00] [bugfix] [Changed] bquant/visualization/zones.py - Fixed detail mode: indicators now taken from full window range (window_df) ensuring indicators displayed for entire displayed range including context bars
[18:30:00] [feature] [Changed] bquant/visualization/zones.py - Added time_axis_mode parameter (default 'dense') to plot_zones_comparison for choosing between dense (positional indices) and timeseries (datetime with rangebreaks) visualization modes
[18:30:00] [feature] [Changed] research/notebooks/04_zones_sample.py - Added comprehensive parameter documentation with comments in plot_zones_comparison call
[18:30:00] [feature] [Changed] research/notebooks/04_zones_sample.py - Added comparison visualization for 5 zones closest to median duration as example of multi-zone comparison
[18:23:00] [bugfix] [Changed] bquant/indicators/library/manager.py - Fixed indentation error in _load_library method



