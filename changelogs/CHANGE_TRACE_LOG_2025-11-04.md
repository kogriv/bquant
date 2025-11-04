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



