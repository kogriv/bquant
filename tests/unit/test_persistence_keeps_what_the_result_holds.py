"""JSON и Parquet обязаны возвращать тот результат, который сохраняли (G56).

До 2026-09-04 оба формата теряли структуру и **не падали**:

* `hypothesis_tests` лежал в результате объектом `AnalysisResult`, а JSON-писатели
  стояли на `default=str` — на диск уезжала строка `repr`, все семь тестов гипотез
  исчезали;
* тот же `default=str` превращал `np.False_` в строку `"False"` — **истинную**, так что
  `significant_difference` после загрузки читался как «значимо» на каждом разделе;
* `RegressionResult` уезжал строкой;
* свинг-контекст не писался вовсе: `zone.get_zone_swings()` после загрузки — пустой
  список у результата, посчитанного в `global`;
* `zone.data` не восстанавливался, хотя это срез `result.data`;
* JSON с `include_data=True` терял индекс кадра (`to_dict('records')`): ось времени
  возвращалась `RangeIndex`.

Существующая проверка сериализации подавала рукописный `dict` — тип, с которым ничего
из этого не происходит. Здесь — настоящий результат пайплайна.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bquant.analysis import AnalysisResult
from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.models import ZoneAnalysisResult, _json_default
from bquant.data.samples import get_sample_data

pytest.importorskip("pyarrow")


@pytest.fixture(scope="module")
def result() -> ZoneAnalysisResult:
    return (
        analyze_zones(get_sample_data("tv_xauusd_1h"))
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_strategies(swing="zigzag")
        .with_cache(enable=False)
        .analyze(clustering=True, regression=True, validation=True)
        .build()
    )


def _canon(payload) -> str:
    """Одна и та же структура независимо от `np.float64` против `float` и NaN против NaN."""

    return json.dumps(payload, sort_keys=True, default=_json_default)


def _swings(res: ZoneAnalysisResult):
    return [
        [(p.index, p.price, str(p.timestamp), p.confirmation_index, p.amplitude_to_next)
         for p in zone.get_zone_swings()]
        for zone in res.zones
    ]


@pytest.fixture(scope="module", params=["json", "parquet"])
def reloaded(request, result, tmp_path_factory):
    fmt = request.param
    path = tmp_path_factory.mktemp("persist") / f"result.{fmt}"
    result.save(path, format=fmt, include_data=True)
    return fmt, ZoneAnalysisResult.load(path, format=fmt)


def test_the_hypothesis_tests_come_back_as_the_dict_they_are(result, reloaded):
    _, loaded = reloaded

    assert isinstance(result.hypothesis_tests, dict)
    assert set(result.hypothesis_tests) == {"tests", "summary"}
    assert _canon(loaded.hypothesis_tests) == _canon(result.hypothesis_tests)


def test_numpy_booleans_stay_booleans(result, reloaded):
    """`"False"` — истинная строка; вердикт о значимости менялся на противоположный."""

    _, loaded = reloaded
    comparison = loaded.statistics["duration_distribution"]["comparison"]
    original = result.statistics["duration_distribution"]["comparison"]

    assert isinstance(original["significant_difference"], (bool, np.bool_))
    assert isinstance(comparison["significant_difference"], bool)
    assert comparison["significant_difference"] == bool(original["significant_difference"])
    assert _canon(loaded.statistics) == _canon(result.statistics)


def test_every_section_survives(result, reloaded):
    _, loaded = reloaded

    for section in ("clustering", "sequence_analysis", "regression_results",
                    "validation_results", "metadata"):
        assert _canon(getattr(loaded, section)) == _canon(getattr(result, section)), section
    assert loaded.column_schema.to_dict() == result.column_schema.to_dict()
    assert "error" not in result.regression_results["duration"]


def test_swings_survive_and_the_context_is_shared(result, reloaded):
    """Раньше — пустой список у каждой зоны; контекст пишется один раз на результат."""

    _, loaded = reloaded

    assert sum(len(s) for s in _swings(result)) > 0
    assert _swings(loaded) == _swings(result)
    assert len({id(z.swing_context) for z in loaded.zones}) == 1


def test_the_frame_and_the_zone_slices_come_back_whole(result, reloaded):
    fmt, loaded = reloaded

    assert loaded.data.equals(result.data), fmt
    assert isinstance(loaded.data.index, pd.DatetimeIndex)
    assert loaded.data.index.equals(result.data.index)
    assert all(a.data.equals(b.data) for a, b in zip(result.zones, loaded.zones))
    assert all(isinstance(z.start_time, pd.Timestamp) for z in loaded.zones)
    assert [z.start_time for z in loaded.zones] == [z.start_time for z in result.zones]


def test_without_the_frame_the_zones_are_empty_but_the_swings_are_not(result, tmp_path):
    path = tmp_path / "no_frame.json"
    result.save(path, format="json", include_data=False)
    loaded = ZoneAnalysisResult.load(path, format="json")

    assert loaded.data is None
    assert all(z.data.empty for z in loaded.zones)
    assert _swings(loaded) == _swings(result)


def test_an_object_in_a_structural_field_is_refused_not_stringified(result, tmp_path):
    """`default=str` делал из объекта строку и молчал; теперь — отказ с именем типа."""

    payload = result.to_dict()
    payload["hypothesis_tests"] = AnalysisResult("stray", results={})

    with pytest.raises(TypeError, match="AnalysisResult"):
        json.dumps(payload, default=_json_default)


def test_the_artifact_is_json_native(result, tmp_path):
    """Ни одной строки вида `AnalysisResult(...)`/`RegressionResult(...)` в файле."""

    path = tmp_path / "native.json"
    result.save(path, format="json", include_data=False)
    text = path.read_text(encoding="utf-8")

    assert "AnalysisResult(" not in text
    assert "RegressionResult(" not in text
    assert '"False"' not in text and '"True"' not in text
