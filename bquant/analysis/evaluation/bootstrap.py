"""Block bootstrap over calendar months.

Trades overlap in time — neighbouring entries, long holds — and a plain bootstrap over
trades treats them as independent, which makes every interval too narrow. Here the
block is the **calendar month of entry**: a replicate draws ``M`` months with
replacement out of the ``M`` months of the segment and takes all trades of the drawn
months; dependence inside a month is kept.

Two rules that are easy to get wrong and are therefore guarded:

* **The block list is the segment's months, empty ones included.** It comes from the
  caller (:func:`~.trades.months_between`), never from ``unique(month of trades)``: a
  month with no trades is a block that contributes nothing when drawn, and dropping it
  would make the bootstrap resample from a shorter, busier segment than the one measured.
* **A replicate with no trades is dropped, not redrawn.** When every drawn month is
  empty the mean is undefined; the replicate is ``NaN`` and every statistic is taken
  over the replicates that remain.

Randomness: ``numpy.random.default_rng(seed)`` and a single call
``integers(0, M, (B, M))`` — so two bootstraps with the same months, ``B`` and seed
share every replicate, and so does the lab's reference implementation.
"""

from __future__ import annotations

import numpy as np


class BlockBootstrap:
    """Weights ``W`` (``B × M``): how many times month ``i`` was drawn in replicate ``b``."""

    def __init__(self, months, B: int = 2000, seed: int = 1):
        months = np.asarray(months, dtype=np.int64)
        if months.ndim != 1 or len(months) == 0:
            raise ValueError("BlockBootstrap needs a non-empty 1-d list of integer month keys")
        if len(np.unique(months)) != len(months):
            raise ValueError("BlockBootstrap: month keys must be unique")
        if B < 1:
            raise ValueError(f"BlockBootstrap: B must be >= 1, got {B}")
        self.months = months
        self.pos = {int(m): i for i, m in enumerate(months)}
        M = len(months)
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, M, (B, M))
        self.W = np.zeros((B, M))
        np.add.at(self.W, (np.repeat(np.arange(B), M), idx.ravel()), 1.0)
        self.B = int(B)
        self.seed = seed

    def means(self, values, month) -> np.ndarray:
        """Replicate means, shape ``(B,)``, ``NaN`` where the replicate drew no trade.

        ``values`` are the per-trade numbers, ``month`` their integer month keys. A
        month outside the block list is refused: the bootstrap cannot resample what
        it was not told exists.
        """
        values = np.asarray(values, dtype=float)
        month = np.asarray(month, dtype=np.int64)
        if values.shape != month.shape:
            raise ValueError(f"values and month differ in shape: {values.shape} vs {month.shape}")
        unknown = sorted({int(m) for m in month} - self.pos.keys())
        if unknown:
            raise ValueError(
                f"trade month(s) {unknown} are outside the bootstrap's block list "
                f"[{int(self.months.min())}..{int(self.months.max())}]; pass the segment's months"
            )
        M = len(self.months)
        col = np.array([self.pos[int(m)] for m in month], dtype=np.int64)
        sums = np.bincount(col, weights=values, minlength=M)
        counts = np.bincount(col, minlength=M).astype(float)
        num, den = self.W @ sums, self.W @ counts
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(den > 0, num / den, np.nan)

    def interval(self, values, month, level: float = 0.95) -> tuple[float, float, float, np.ndarray]:
        """``(lo, hi, se, replicates)`` — quantiles of the surviving replicates at
        ``(1 - level) / 2`` and its mirror (linear interpolation), the standard error
        ``std(ddof=1)`` (``NaN`` with one or no replicate), and the replicates themselves.
        """
        if not 0 < level < 1:
            raise ValueError(f"level must be in (0, 1), got {level}")
        replicates = self.means(values, month)
        replicates = replicates[~np.isnan(replicates)]
        if len(replicates) == 0:
            return np.nan, np.nan, np.nan, replicates
        a = (1 - level) / 2
        se = float(np.std(replicates, ddof=1)) if len(replicates) > 1 else np.nan
        return float(np.quantile(replicates, a)), float(np.quantile(replicates, 1 - a)), se, replicates

    def describe(self) -> dict:
        return {
            "block": "calendar month of entry",
            "months": int(len(self.months)),
            "B": self.B,
            "seed": self.seed,
        }
