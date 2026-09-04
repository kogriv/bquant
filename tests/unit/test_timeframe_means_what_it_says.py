"""A project timeframe handed to pandas has to keep its meaning.

``resample_ohlcv(df, '5m')`` used to hand the string to pandas unchanged, and pandas
reads ``m`` as month-end: five-*month* bars came back, logged as a success. Measured
on the embedded samples before the fix: ``'1m'`` on hourly data gave 3 rows 31 days
apart, ``'30m'`` on quarter-hour data gave a single row. The same pass-through sat in
``validate_time_series_continuity``, where an expected spacing of ``'15m'`` compared
the index against a fifteen-month grid and found no gaps.
"""

import pandas as pd
import pytest

from bquant.core.config import pandas_offset_alias
from bquant.data.processor import resample_ohlcv, resolve_time_index
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_time_series_continuity


@pytest.mark.parametrize(
    "timeframe, alias",
    [
        ("1m", "1min"), ("5m", "5min"), ("15m", "15min"), ("30m", "30min"),
        ("1h", "1h"), ("4h", "4h"), ("1d", "1D"), ("1w", "1W"), ("1M", "1ME"),
    ],
)
def test_project_timeframes_translate_to_the_pandas_alias_with_the_same_meaning(timeframe, alias):
    assert pandas_offset_alias(timeframe) == alias


@pytest.mark.parametrize("alias", ["5min", "15min", "D", "1D", "W", "1W", "ME"])
def test_pandas_own_aliases_pass_through_untouched(alias):
    assert pandas_offset_alias(alias) == alias


def _quarter_hour_bars() -> pd.DataFrame:
    return resolve_time_index(get_sample_data("mt_xauusd_m15"))


def test_resampling_to_thirty_minutes_builds_thirty_minute_bars():
    bars = resample_ohlcv(_quarter_hour_bars(), "30m")
    spacing = bars.index.to_series().diff().mode()[0]
    assert spacing == pd.Timedelta("30min"), spacing
    # 1000 quarter-hour bars make about 500 half-hour bars; thirty-month bars made one.
    assert len(bars) > 400, len(bars)


def test_resampling_to_two_hours_builds_two_hour_bars():
    bars = resample_ohlcv(_quarter_hour_bars(), "2h")
    assert bars.index.to_series().diff().mode()[0] == pd.Timedelta("2h")


def test_continuity_check_measures_gaps_in_project_units():
    index = pd.date_range("2025-01-06 09:00", periods=40, freq="15min")
    frame = pd.DataFrame({"close": range(40)}, index=index).drop(index[17])

    report = validate_time_series_continuity(frame, expected_frequency="15m")

    assert report["is_continuous"] is False
    assert report["gaps"] == [index[17]]
