"""``clean_ohlcv_data(fill_method='interpolate')`` has to survive a text column.

The embedded samples carry signal labels next to OHLCV. pandas 2 interpolated the
frame and quietly skipped the text; pandas 3 refuses the whole frame with
``TypeError: DataFrame cannot interpolate with object dtype``, and the research
notebook that demonstrates the cleaner died on its first sample. Interpolation is
a numeric operation, so the cleaner applies it to the numeric columns and leaves
the rest as they are — on every pandas.
"""

import numpy as np
import pandas as pd

from bquant.data.processor import clean_ohlcv_data


def _bars_with_a_gap_and_a_label() -> pd.DataFrame:
    index = pd.date_range("2025-01-06 09:00", periods=6, freq="1h")
    close = [10.0, 11.0, np.nan, 13.0, 14.0, 15.0]
    return pd.DataFrame(
        {
            "open": close, "high": close, "low": close, "close": close,
            "volume": [100.0, 100.0, np.nan, 100.0, 100.0, 100.0],
            "label": ["", "Regular Bullish", "", "", "Regular Bearish", ""],
        },
        index=index,
    )


def test_interpolation_fills_the_numbers_and_keeps_the_text():
    cleaned = clean_ohlcv_data(_bars_with_a_gap_and_a_label(), fill_method="interpolate",
                               remove_outliers=False)

    assert cleaned["close"].iloc[2] == 12.0
    assert cleaned["volume"].iloc[2] == 100.0
    assert cleaned["label"].tolist() == ["", "Regular Bullish", "", "", "Regular Bearish", ""]
