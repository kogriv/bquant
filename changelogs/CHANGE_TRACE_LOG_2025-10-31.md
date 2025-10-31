# Change Trace Log 2025-10-31


[10:00:00] [not_included] [Added] docs/api/visualization/zones.md - comprehensive zone visualization documentation (2105 lines)
[10:00:05] [not_included] [Changed] docs/api/visualization/README.md - added link to detailed zones.md documentation
[10:00:10] [not_included] [Changed] docs/api/analysis/zones.md - added visualize() method and link to visualization docs
[10:00:15] [not_included] [Technical] Documented ZoneVisualizer class with all 7 methods, backend configuration, export options
[10:00:20] [not_included] [Technical] Documented result.visualize() 4 modes (overview/detail/comparison/statistics), convenience functions
[10:00:25] [not_included] [Technical] Cross-linked with analysis, tutorials, examples; included full usage examples

[15:45:00] [feature] [Added] bquant/visualization/export.py - universal save_figure utility (Plotly/Matplotlib) with smart defaults
    - Default output dir: ./outputs/vis/<script_name>/ (auto-created)
    - Default format: PNG for Plotly (HTML fallback if no kaleido), PNG for Matplotlib
    - Default size: width=1400, height=900 (Plotly); dpi=150 (Matplotlib)

[15:45:05] [docs] [Changed] docs/api/visualization/zones.md - export section now references bquant.visualization.export.save_figure and documents defaults

[15:45:10] [refactor] [Changed] research/notebooks/04_zones_visualization_demo.py - switched to package save_figure; removed local path/format config; logs actual saved path

[16:05:00] [refactor] [Changed] research/notebooks/04_zones_visualization_demo.py - simplified median-zone selection using result.statistics; removed helper functions

[16:10:00] [style] [Changed] research/notebooks/04_zones_visualization_demo.py - removed main() wrapper; moved execution to top-level for script-notebook style

==================== COMMIT DIVIDER ====================