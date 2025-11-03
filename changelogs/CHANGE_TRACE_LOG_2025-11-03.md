# Change Trace Log 2025-11-03

[18:35:00] [bugfix] [Changed] bquant/analysis/zones/models.py - Fixed zone filtering for date_range: exclude zones that end exactly at or before range start (changed from `>= start_date` to `> start_date`)
[18:35:00] [cleanup] [Changed] bquant/visualization/zones.py - Cleaned up indicator bar rendering code (removed unnecessary bargap/width calculations)
[18:35:00] [changed] [Changed] research/notebooks/04_zones_sample.py - Set explicit output directory: research/notebooks/outputs/vis/script_name
[18:50:00] [feature] [Changed] bquant/analysis/zones/models.py - Added symbol, timeframe, source parameters to visualize() method
[18:50:00] [feature] [Changed] bquant/visualization/zones.py - Added chart metadata display (symbol, timeframe, source) in top-right corner as annotation
[19:00:00] [feature] [Changed] bquant/data/samples/utils.py - Auto-populate DataFrame.attrs with metadata (symbol, timeframe, source) from dataset registry
[19:00:00] [feature] [Changed] bquant/analysis/zones/analyzer.py - Auto-extract metadata from DataFrame.attrs into ZoneAnalysisResult.metadata
[19:00:00] [feature] [Changed] bquant/analysis/zones/pipeline.py - Update metadata from df.attrs for cached results (ensures fresh metadata even with cache)
[19:00:00] [changed] [Changed] research/notebooks/04_zones_sample.py - Removed explicit symbol/timeframe/source params (now auto-detected)

Note: "Gaps" in MACD histogram are real data gaps (weekends/trading halts in sample data), not visualization bugs

==================== COMMIT DIVIDER ====================


