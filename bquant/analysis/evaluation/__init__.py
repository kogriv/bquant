"""Evaluation of a list of trades: is a result consistent, or made by luck and selection?

Everything here reads one object, the **trade frame** (:mod:`.trades`), and answers
four questions a single backtest number cannot:

* how wide is the result, once trades that overlap in time are resampled by
  **calendar month** (:class:`BlockBootstrap`);
* how much of it a **random entry** of the same side, year and holding time would
  have earned anyway (:func:`random_entry_baseline`);
* does the advantage survive the correction for **everything that was tried**
  (:func:`trial_stats`, :func:`benjamini_hochberg`, :class:`Criterion` with its rules);
* does **picking** a run on the back window beat not picking (:func:`evaluate_procedure`),
  and is a run's result spread over **quarters** or made in one stretch
  (:func:`quarterly_summary`).

The package holds no registry of variants, no notion of zones or bars, and no data: the
number of tests corrected for comes from the caller, as does the outcome function the
baseline averages.
"""

from .baseline import attach_random_baseline, random_entry_baseline
from .bootstrap import BlockBootstrap
from .criterion import (
    BeatsRandom,
    Criterion,
    MinEffect,
    MinTrades,
    NetPositive,
    Rule,
    YearsStable,
    apply_rules,
    benjamini_hochberg,
    default_criterion,
    trial_stats,
)
from .procedure import ProcedureResult, evaluate_procedure
from .quarters import (
    QuarterMeanOverStd,
    QuarterMedian,
    QuartersPositive,
    WorstQuarter,
    default_quarter_rules,
    quarterly_summary,
)
from .trades import month_key, month_label, months_between, validate_trades

__all__ = [
    "validate_trades", "month_key", "month_label", "months_between",
    "BlockBootstrap",
    "random_entry_baseline", "attach_random_baseline",
    "trial_stats", "benjamini_hochberg",
    "Rule", "MinTrades", "NetPositive", "YearsStable", "BeatsRandom", "MinEffect",
    "apply_rules", "Criterion", "default_criterion",
    "evaluate_procedure", "ProcedureResult",
    "quarterly_summary", "QuartersPositive", "QuarterMedian", "WorstQuarter",
    "QuarterMeanOverStd", "default_quarter_rules",
]
