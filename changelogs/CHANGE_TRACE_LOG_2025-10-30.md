# Change Trace Log 2025-10-30

==================== COMMIT DIVIDER ====================

[15:36:00] [not_included] [Changed] Quiet-init: suppressed pandas_ta stdout/stderr during indicator registration
[15:36:05] [not_included] [Changed] Lowered noisy logs to DEBUG for mass registrations (pandas_ta discovery, indicator factory)
[15:36:10] [not_included] [Changed] Consolidated strategy registration logs into single summary INFO
[15:36:15] [not_included] [Added] Summary INFO for external indicators: pandas_ta=<N>, talib=<M>
[15:36:20] [not_included] [Changed] Made analysis.zones init logs DEBUG; kept concise summaries
[15:36:25] [not_included] [Changed] research/notebooks/00_logging_demo.py uses clean profile (no env hacks)
[15:36:30] [not_included] [Added] Docs: logging.md updated with "Quiet Init (Phase 4)" section and before/after examples
[15:36:35] [not_included] [Files Modified] bquant/indicators/library/manager.py; bquant/indicators/library/pandas_ta.py; bquant/indicators/__init__.py; bquant/analysis/zones/detection/registry.py; bquant/analysis/zones/detection/__init__.py; bquant/analysis/zones/__init__.py; research/notebooks/00_logging_demo.py; docs/api/core/logging.md; devref/gaps/logging_design/quiet_init_issue.md
[16:14:00] [not_included] [Changed] Visualization logs: ZoneChartBuilder INFO → DEBUG; keep only summary and warnings
[16:14:05] [not_included] [Changed] Single summary INFO on visualization init in bquant/visualization/__init__.py
[16:14:10] [not_included] [Changed] research/notebooks/04_zones_visualization_demo.py uses clean profile and disables saving by default
[16:14:15] [not_included] [Technical] Verified quiet run with --no-trap; step logs reduced to summaries

