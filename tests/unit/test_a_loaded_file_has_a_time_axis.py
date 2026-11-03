"""A file the loader accepts comes back with a time axis, not with strings (G89).

``read_csv`` with a ``date_format`` that does not fit **does not raise** — it leaves the
column as text. The loader tried three fixed formats in turn and returned the first read
that did not raise, so a file with offsets (``2025-06-11 20:00:00+07:00`` — the shape of
the package's own samples) came back with a text index on every pandas. The fallback
converted only an ``object`` index, and on pandas 3 text is ``str``: the conversion was
skipped there too. Nothing noticed until a test resampled a loaded file (G88's runtime
guard, 2026-11-03).
"""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.data import load_ohlcv_data, resample_ohlcv
from bquant.data.samples import get_sample_data


def _write(tmp_path, frame, name="s.csv"):
    path = tmp_path / name
    frame.to_csv(path, index=False)
    return path


@pytest.fixture(scope="module")
def sample():
    return get_sample_data("tv_xauusd_1h").head(200)


def test_a_file_with_offsets_loads_into_a_time_axis(tmp_path, sample):
    assert "+07:00" in str(sample["time"].iloc[0]), "the sample carries an offset — that is the case under test"
    loaded = load_ohlcv_data(_write(tmp_path, sample))
    assert isinstance(loaded.index, pd.DatetimeIndex), type(loaded.index).__name__
    assert loaded.index.tz is not None
    assert loaded.index[0] == pd.Timestamp(sample["time"].iloc[0])
    assert len(resample_ohlcv(loaded, "4h")) > 0


@pytest.mark.parametrize("stamp, fmt", [
    ("2024-01-02 03:00:00", "%Y-%m-%d %H:%M:%S"),
    ("2024.01.02 03:00:00", "%Y.%m.%d %H:%M:%S"),
    ("2024-01-02", "%Y-%m-%d"),
])
def test_the_fixed_formats_still_load(tmp_path, stamp, fmt):
    times = pd.date_range(pd.to_datetime(stamp, format=fmt), periods=120, freq="D" if len(stamp) == 10 else "h")   # the loader refuses fewer than 100 rows
    frame = pd.DataFrame({
        "time": times.strftime(fmt), "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10,
    })
    loaded = load_ohlcv_data(_write(tmp_path, frame))
    assert isinstance(loaded.index, pd.DatetimeIndex)
    assert list(loaded.index) == list(times)
