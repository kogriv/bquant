# Swing strategy tuning checklist

This reference collects the decisions made while restoring swing metrics and
highlights the validation routine we expect to run after every adjustment.

## Preset catalog

| Preset | ZigZag | Find Peaks | Pivot Points | Typical usage |
| --- | --- | --- | --- | --- |
| `default` | `legs=10`, `deviation=0.05` | `prominence=0.015`, `distance=5`, `min_amplitude_pct=0.02` | `min_amplitude_pct=0.015`, `left/right_bars=2` | Matches historical behaviour. Use as the baseline export when comparing KPI deltas. |
| `narrow_zone` | `legs=3`, `deviation=0.008` | `prominence=0.004`, `distance=3`, `min_amplitude_pct=0.006` | `min_amplitude_pct=0.006`, `left/right_bars=2` | Focuses on zones with price oscillations under 1 %. Expect swing density > 1.0 for `tv_xauusd_1h`. |

Both presets live in `bquant/core/config.py` and are applied uniformly to the
registered swing strategies through `ZoneAnalysisPipeline.with_swing_preset`.

## KPI guard-rails

* Target dataset: `tv_xauusd_1h` (TradingView extract bundled in
  `bquant.data.samples`).
* Success criteria: the mean number of swings per bull zone should stay above
  1.0, with the tuned preset (`narrow_zone`) clustering around 55 swings for the
  23 reference zones identified in the MACD zero-crossing workflow.
* Cache must be disabled for interactive experiments to surface configuration
  changes immediately.

## Validation workflow

1. Export the baseline metrics using the default preset:
   ```bash
   poetry run python research/notebooks/validate_swing_pivots.py \
       --dataset tv_xauusd_1h \
       --preset default \
       --export outputs/reports/swing_default.json
   ```
   The command writes a JSON snapshot that contains the zone metadata, swing
   metrics (via `SwingMetrics.to_dict()`), and pivot statistics for archival.
2. Re-run the helper with the tuned preset and enforce pivot validation:
   ```bash
   poetry run python research/notebooks/validate_swing_pivots.py \
       --dataset tv_xauusd_1h \
       --preset narrow_zone \
       --check \
       --export outputs/reports/swing_narrow.json
   ```
   `--check` escalates any pivot ordering or range violations to a non-zero exit
   status so CI picks up regressions.
3. Compare the JSON exports (for example with `jq` or `meld`) and note the swing
   density delta in the issue log. The tuned preset should report a materially
   higher pivot count while keeping every point inside the original price band.

Running these two commands after every tweak keeps the KPI history aligned with
our empirical observations from `devref/gaps/swing/strat_issue.md`.
