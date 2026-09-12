"""Levers of the data path must change the answer — or refuse, or say they did not look.

Third area of the §7.3 lever table, and the one whose defects cost the most: a knob
on loading or validation feeds every number computed afterwards. Three findings:

* `get_data_path` validated `timeframe` loudly and substituted `data_source` and
  `quote_provider` silently — a typo in the provider returned a path to somebody
  else's file (G77);
* `load_ohlcv_data` caught the timeframe refusal and wrote it to the log as a
  warning, so an invalid timeframe loaded happily (G77);
* `validate_time_series_continuity` checked for gaps only when an expected frequency
  was passed, and otherwise answered `is_continuous: True` without looking — on a
  sample whose index has 482 missing hourly stamps (G78).
"""

from __future__ import annotations

import inspect

import pandas as pd
import pytest

from bquant.core.config import get_data_path
from bquant.data.loader import load_ohlcv_data
from bquant.data.processor import normalize_prices, resample_ohlcv, resolve_time_index
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_time_series_continuity


@pytest.fixture(scope="module")
def hourly() -> pd.DataFrame:
    return resolve_time_index(get_sample_data("tv_xauusd_1h"))


# --- G77 -------------------------------------------------------------------

def test_a_known_quote_provider_changes_the_path():
    """Positive control: the refusals below must not be a blanket refusal."""
    oanda = get_data_path("XAUUSD", "1h", quote_provider="oanda").name
    forexcom = get_data_path("XAUUSD", "1h", quote_provider="forexcom").name
    assert oanda != forexcom
    assert get_data_path("XAUUSD", "1h", data_source="metatrader").name != oanda


@pytest.mark.parametrize(
    "kwargs, word",
    [
        ({"data_source": "no_such_source"}, "data source"),
        ({"quote_provider": "no_such_provider"}, "quote provider"),
    ],
)
def test_an_unknown_path_argument_is_refused_and_names_the_options(kwargs, word):
    with pytest.raises(ValueError) as excinfo:
        get_data_path("XAUUSD", "1h", **kwargs)
    message = str(excinfo.value)
    assert word in message.lower()
    assert "Supported" in message


def test_an_invalid_timeframe_is_refused_by_the_loader(tmp_path, hourly):
    csv = tmp_path / "probe.csv"
    hourly.head(300).reset_index().to_csv(csv, index=False)

    assert load_ohlcv_data(str(csv), timeframe="1h").shape[0] > 0  # control

    with pytest.raises(ValueError, match="Unsupported timeframe"):
        load_ohlcv_data(str(csv), timeframe="not_a_timeframe")


# --- G78 -------------------------------------------------------------------

def test_continuity_is_measured_without_an_expected_frequency(hourly):
    inferred = validate_time_series_continuity(hourly)
    explicit = validate_time_series_continuity(hourly, expected_frequency="1h")

    assert inferred["gap_basis"] == "inferred_spacing"
    assert explicit["gap_basis"] == "expected_frequency"
    assert inferred["is_continuous"] is False
    assert len(inferred["gaps"]) > 0
    assert len(inferred["gaps"]) == len(explicit["gaps"]), (
        "the inferred grid must agree with the declared one on this sample"
    )


def test_a_frame_without_gaps_is_still_called_continuous():
    """Positive control: an implementation that always says False would pass above."""
    index = pd.date_range("2025-01-06", periods=120, freq="h")
    frame = pd.DataFrame({"close": range(len(index))}, index=index)

    report = validate_time_series_continuity(frame)
    assert report["is_continuous"] is True
    assert report["gaps"] == []
    assert report["gap_basis"] == "inferred_spacing"


def test_continuity_says_so_when_it_could_not_look():
    """One row: no spacing to infer, so the answer must not be a verdict."""
    frame = pd.DataFrame({"close": [1.0]}, index=pd.DatetimeIndex(["2025-01-06"]))
    report = validate_time_series_continuity(frame)
    assert report["gap_basis"] is None


# --- pinned limits, not defects --------------------------------------------

def test_base_column_acts_only_for_the_first_value_method(hourly):
    frame = hourly.head(200)

    by_close = normalize_prices(frame, base_column="close")
    by_open = normalize_prices(frame, base_column="open")
    assert not by_close.equals(by_open), "first_value must honour base_column"

    z_close = normalize_prices(frame, base_column="close", method="z_score")
    z_open = normalize_prices(frame, base_column="open", method="z_score")
    assert z_close.equals(z_open), "z_score normalises each column by itself"

    with pytest.raises(Exception, match="Unknown normalization method"):
        normalize_prices(frame, method="no_such_method")


def test_resample_no_longer_offers_a_method_that_did_nothing():
    assert "method" not in inspect.signature(resample_ohlcv).parameters
