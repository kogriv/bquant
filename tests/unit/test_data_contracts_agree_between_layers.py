"""Контракты данных обязаны совпадать между слоями и не молчать на краях (G57).

Десять находок аудита (AQ-014–020, 024–026), каждая воспроизведена на коде до правки:

* пустой кадр с правильными колонками проходил схему — «is_valid=True»;
* схема не знала отношений OHLC: `high < low` в каждой строке — «валидно», хотя
  валидатор те же строки отклонял;
* `validate_data_completeness` на пустом кадре делил на ноль и отдавал `NaN`-доли;
* шестиколоночный MetaTrader CSV без заголовка читался с первой строкой данных в роли
  заголовка: колонки `['3336.94', '3344.77', …]`, индекс — строки;
* колонка времени, где разобралось одно значение из пяти, становилась индексом с
  четырьмя `NaT`;
* preloaded-зоны: непорядок и пересечения принимались, строки-даты отклонялись
  (вопреки докстрингу), `time_tolerance='2h'` расширял зону 31 → 35 баров, дубликаты
  на оси данных не проверялись;
* анализ последовательностей считал соседними зоны, начинающиеся внутри — или до —
  предыдущей;
* постоянная цена: фильтр выбросов удалял **все** строки (`0/0 = NaN`, `NaN <= 3` — ложь);
* `london_ny_overlap` — `object` с `NaN` вместо `False`;
* две функции писали разные величины под именем `true_range`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.detection.preloaded import PreloadedZonesDetection
from bquant.analysis.zones.sequence_analysis import ZoneSequenceAnalyzer
from bquant.data.loader import load_ohlcv_data
from bquant.data.processor import (
    add_technical_features,
    calculate_derived_indicators,
    calculate_true_range,
    detect_market_sessions,
    remove_price_outliers,
    resolve_time_index,
)
from bquant.data.samples import get_sample_data
from bquant.data.schemas import OHLCV_SCHEMA, OHLCVRecord, ohlc_violations
from bquant.data.validator import validate_data_completeness, validate_ohlcv_data


@pytest.fixture(scope="module")
def ohlc() -> pd.DataFrame:
    sample = get_sample_data("tv_xauusd_1h")
    return sample[["time", "open", "high", "low", "close", "volume"]].copy()


# --- AQ-014 / AQ-015 / AQ-016: schema, validator, completeness ------------------------


def test_an_empty_frame_with_the_right_columns_is_refused(ohlc):
    verdict = OHLCV_SCHEMA.validate_dataframe(ohlc.iloc[0:0])

    assert verdict.is_valid is False
    assert any("0 rows" in issue for issue in verdict.issues)


def test_a_required_column_with_no_values_is_refused(ohlc):
    frame = ohlc.head(5).copy()
    frame["close"] = np.nan

    verdict = OHLCV_SCHEMA.validate_dataframe(frame)

    assert verdict.is_valid is False
    assert any("'close' has no values" in issue for issue in verdict.issues)


def test_the_three_layers_agree_on_ohlc_relations(ohlc):
    """Схема, валидатор и проверка одной записи — одни и те же три отношения."""

    frame = ohlc.head(5).copy()
    frame["high"], frame["low"] = frame["low"] - 1, frame["high"] + 1

    counts = ohlc_violations(frame)
    assert counts == {
        "high_below_low": 5,
        "high_below_open_or_close": 5,
        "low_above_open_or_close": 5,
    }
    assert OHLCV_SCHEMA.validate_dataframe(frame).is_valid is False
    assert validate_ohlcv_data(frame)["is_valid"] is False
    row = frame.iloc[0]
    assert OHLCVRecord(pd.Timestamp("2025-01-01"), row.open, row.high, row.low, row.close).validate() is False


def test_a_frame_that_passes_the_record_check_passes_the_schema(ohlc):
    verdict = OHLCV_SCHEMA.validate_dataframe(ohlc.head(50))
    assert verdict.is_valid is True, verdict.issues
    assert verdict.stats["frame_violations"] == {}


def test_completeness_on_an_empty_frame_has_no_nan_ratios(ohlc):
    report = validate_data_completeness(ohlc.iloc[0:0])

    assert report["is_complete"] is False
    assert report["missing_data_ratio"] == {}
    assert any("no rows" in r for r in report["recommendations"])


# --- AQ-017: MetaTrader CSV without a header --------------------------------------


def _write_mt_csv(path: Path, rows: pd.DataFrame, extra: str = "") -> None:
    with open(path, "w") as handle:
        for _, row in rows.iterrows():
            stamp = pd.Timestamp(row["time"]).strftime("%Y.%m.%d %H:%M:%S")
            handle.write(
                f"{stamp},{row['open']},{row['high']},{row['low']},{row['close']},{int(row['volume'])}{extra}\n"
            )


@pytest.mark.parametrize("extra", ["", ",3"], ids=["six_columns", "seven_columns"])
def test_a_headerless_metatrader_csv_keeps_its_first_row(ohlc, extra):
    """Шестиколоночный файл терял первую строку в заголовок и получал цены именами колонок."""

    rows = ohlc.head(20)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "XAUUSDH1.csv"
        _write_mt_csv(path, rows, extra)
        loaded = load_ohlcv_data(path, validate_data=False)

    assert len(loaded) == 20
    assert list(loaded.columns[:5]) == ["open", "high", "low", "close", "volume"]
    assert isinstance(loaded.index, pd.DatetimeIndex)
    assert loaded.index[0] == pd.Timestamp(rows["time"].iloc[0]).tz_localize(None)
    assert loaded["close"].iloc[0] == pytest.approx(rows["close"].iloc[0])


def test_a_csv_with_a_header_is_not_mistaken_for_metatrader(ohlc):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "with_header.csv"
        ohlc.head(20).to_csv(path, index=False)
        loaded = load_ohlcv_data(path, validate_data=False)

    assert len(loaded) == 20
    assert "open" in loaded.columns and "col_6" not in loaded.columns


# --- AQ-018: a time column that only partly parses ----------------------------------


def test_a_partly_parsed_time_column_is_refused_not_indexed_with_nat(ohlc):
    frame = ohlc.head(5).copy()
    frame["time"] = ["2025-01-01 00:00", "garbage", "x", "y", "z"]

    with pytest.raises(ValueError, match="4 of 5 values did not parse") as excinfo:
        resolve_time_index(frame)
    assert "'garbage'" in str(excinfo.value)


def test_a_column_that_is_not_time_at_all_still_leaves_positions(ohlc):
    frame = ohlc.head(5).copy()
    frame["time"] = ["a", "b", "c", "d", "e"]

    prepared = resolve_time_index(frame)
    assert not isinstance(prepared.index, pd.DatetimeIndex)


# --- AQ-019: preloaded zones -----------------------------------------------------------


def _detect(ohlc, zones, **rules):
    config = ZoneDetectionConfig(zone_types=None, rules={"zones_data": zones, **rules},
                                 strategy_name="preloaded")
    return PreloadedZonesDetection().detect_zones(ohlc, config)


@pytest.fixture(scope="module")
def clock(ohlc) -> pd.Series:
    return pd.to_datetime(ohlc["time"])


def test_overlapping_preloaded_zones_are_refused_by_name(ohlc, clock):
    zones = pd.DataFrame({"zone_id": [0, 1], "type": ["bull", "bear"],
                          "start_time": [clock.iloc[10], clock.iloc[30]],
                          "end_time": [clock.iloc[40], clock.iloc[60]]})
    with pytest.raises(ValueError, match="Zones overlap: zone_id 1"):
        _detect(ohlc, zones)


def test_unsorted_disjoint_preloaded_zones_come_back_in_time_order(ohlc, clock):
    zones = pd.DataFrame({"zone_id": [0, 1], "type": ["bull", "bear"],
                          "start_time": [clock.iloc[50], clock.iloc[10]],
                          "end_time": [clock.iloc[70], clock.iloc[40]]})
    found = _detect(ohlc, zones)
    assert [(z.zone_id, z.start_idx, z.end_idx) for z in found] == [(1, 10, 40), (0, 50, 70)]


def test_string_dates_are_accepted_as_the_docstring_promises(ohlc, clock):
    zones = pd.DataFrame({"zone_id": [1], "type": ["bear"],
                          "start_time": [str(clock.iloc[10])], "end_time": [str(clock.iloc[40])]})
    found = _detect(ohlc, zones)
    assert [(z.start_idx, z.end_idx) for z in found] == [(10, 40)]


def test_tolerance_snaps_to_the_nearest_bar_and_does_not_widen(ohlc, clock):
    """`'2h'` на часовых барах давал 35 баров вместо объявленных 31."""

    zones = pd.DataFrame({"zone_id": [1], "type": ["bear"],
                          "start_time": [clock.iloc[10]], "end_time": [clock.iloc[40]]})
    exact = _detect(ohlc, zones, time_tolerance="1min")[0]
    wide = _detect(ohlc, zones, time_tolerance="2h")[0]
    assert (exact.start_idx, exact.end_idx) == (wide.start_idx, wide.end_idx) == (10, 40)
    assert wide.indicator_context["declared_start_time"] == clock.iloc[10].isoformat()

    off_grid = zones.copy()
    off_grid["start_time"] = [clock.iloc[10] + pd.Timedelta("20min")]
    snapped = _detect(ohlc, off_grid, time_tolerance="30min")[0]
    assert snapped.start_idx == 10
    assert _detect(ohlc, off_grid, time_tolerance="1min") == []


def test_a_duplicated_time_axis_is_refused(ohlc, clock):
    doubled = pd.concat([ohlc.head(60), ohlc.iloc[35:38]]).sort_values("time")
    zones = pd.DataFrame({"zone_id": [1], "type": ["bear"],
                          "start_time": [clock.iloc[10]], "end_time": [clock.iloc[40]]})
    with pytest.raises(ValueError, match="duplicate timestamps"):
        _detect(doubled, zones)


def test_duplicate_zone_ids_and_reversed_boundaries_are_refused(ohlc, clock):
    dup = pd.DataFrame({"zone_id": [1, 1], "type": ["a", "b"],
                        "start_time": [clock.iloc[10], clock.iloc[50]],
                        "end_time": [clock.iloc[40], clock.iloc[60]]})
    with pytest.raises(ValueError, match="zone_id must be unique"):
        _detect(ohlc, dup)
    reversed_ = pd.DataFrame({"zone_id": [1], "type": ["a"],
                              "start_time": [clock.iloc[40]], "end_time": [clock.iloc[10]]})
    with pytest.raises(ValueError, match="end_time is before start_time"):
        _detect(ohlc, reversed_)


# --- AQ-020: adjacency ------------------------------------------------------------------


def test_overlapping_or_reversed_zones_are_not_adjacent():
    features = pd.DataFrame({"start_idx": [0, 5, 3], "end_idx": [9, 14, 20], "zone_type": list("aba")})
    with pytest.raises(ValueError, match="not in tiling order"):
        ZoneSequenceAnalyzer._contiguous_segments(features)


def test_tiling_and_gaps_are_still_read_correctly():
    features = pd.DataFrame({"start_idx": [0, 10, 15, 30], "end_idx": [9, 14, 20, 40]})
    assert ZoneSequenceAnalyzer._contiguous_segments(features) == [[0, 1, 2], [3]]


# --- AQ-024: outliers ---------------------------------------------------------------------


def test_a_constant_price_series_has_no_outliers():
    constant = pd.DataFrame({c: [100.0] * 50 for c in ("open", "high", "low", "close")})
    assert len(remove_price_outliers(constant)) == 50
    assert len(remove_price_outliers(constant, method="iqr")) == 50


def test_masks_are_judged_on_the_original_frame_and_nan_is_not_an_outlier():
    frame = pd.DataFrame({"close": [100.0] * 30 + [np.nan] + [100.0] * 18 + [500.0]})
    kept = remove_price_outliers(frame, columns=["close"])
    assert len(kept) == 49
    assert kept["close"].isna().sum() == 1


# --- AQ-025: sessions ------------------------------------------------------------------------


def test_the_overlap_flag_is_a_boolean_column_without_nulls(ohlc):
    sessions = detect_market_sessions(resolve_time_index(ohlc.head(48)))
    flag = sessions["london_ny_overlap"]
    assert flag.dtype == bool
    assert flag.isna().sum() == 0
    assert flag.sum() > 0 and (~flag).sum() > 0


# --- AQ-026: one true range -------------------------------------------------------------------


def test_true_range_is_one_number_under_one_name(ohlc):
    frame = resolve_time_index(ohlc.head(60))
    derived = calculate_derived_indicators(frame)
    featured = add_technical_features(frame)

    assert derived["true_range"].equals(featured["true_range"])
    assert derived["true_range"].equals(calculate_true_range(frame))
    assert derived["intrabar_range"].equals(frame["high"] - frame["low"])
    # On a bar that gaps past the previous close the two differ — that was the bug.
    gapped = pd.DataFrame({"high": [10, 20], "low": [9, 19], "close": [9.5, 19.5]})
    assert calculate_true_range(gapped).tolist() == [1.0, 10.5]
