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

Regression coverage now lives in the test-suite rather than a standalone research
script (the former `research/notebooks/validate_swing_pivots.py` was removed as
research scratch during the OSS cleanup):

* Smoke test: `tests/integration/test_pipeline_global_swings.py` exercises the
  global-swing pipeline across scopes and preset parameters.
* Helper: `tests/fixtures/swing_coverage.py::compare_swing_coverage` compares
  per-zone vs global swing coverage on `tv_xauusd_1h`.

Run them after every tweak to keep the KPI history aligned with the guard-rails
above:

```bash
pytest tests/integration/test_pipeline_global_swings.py
```

The original tuning analysis is archived in
`devref/archive/gaps/swing/strat_issue.md`.
