"""Small sequence and numeric helpers.

- ``chunk(seq, n)``: split a sequence into pieces of ``n`` elements.
- ``moving_average(xs, window)``: simple moving average.
- ``pct_change(a, b)``: percentage change from ``a`` to ``b``.
"""


def chunk(seq, n):
    """Split ``seq`` into consecutive pieces of ``n`` elements (the last may be shorter)."""
    if n <= 0:
        raise ValueError("n must be positive")
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def moving_average(xs, window):
    """Simple moving average; returns a list of length ``len(xs) - window + 1``."""
    if window <= 0:
        raise ValueError("window must be positive")
    result = []
    for i in range(len(xs) - window + 1):
        result.append(sum(xs[i:i + window]) / window)
    return result


def pct_change(a, b):
    """Percentage change from ``a`` to ``b``."""
    if a == 0:
        raise ZeroDivisionError("pct_change is undefined for a == 0")
    return (b - a) / a * 100.0
