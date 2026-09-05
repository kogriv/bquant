"""Публичный API анализаторов обещает только то, что исполняется (G59).

Две находки аудита (AQ-031, AQ-032), обе воспроизведены до правки:

* `create_analyzer()` принимал шесть имён каталога и на каждое возвращал
  `BaseAnalyzer`, чей `analyze()` поднимает `NotImplementedError` — каталог сходился
  с фабрикой (G32), а фабрика ни с чем; `'statistical'` не строил
  `StatisticalAnalyzer`;
* четыре заглушки возвращали из `analyze()` **успешный** `AnalysisResult` со словом
  «stub» внутри — честно для того, кто заглянет в `results`, и успех для всех
  остальных.

Теперь каталог фабрики — только исполняемое, каждое имя отображено на настоящий класс;
запланированное — отдельный перечень; заглушка отказывает `NotImplementedError` с
перечнем запланированного.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.analysis import (
    PLANNED_ANALYSIS_TYPES,
    SUPPORTED_ANALYSIS_TYPES,
    AnalysisResult,
    BaseAnalyzer,
    create_analyzer,
    get_available_analyzers,
    get_planned_analyzers,
)
from bquant.analysis.candlestick import CandlestickAnalyzer
from bquant.analysis.chart import ChartAnalyzer
from bquant.analysis.statistical import StatisticalAnalyzer
from bquant.analysis.technical import TechnicalAnalyzer
from bquant.analysis.timeseries import TimeseriesAnalyzer
from bquant.analysis.zones import PriceLevelAnalyzer
from bquant.data.samples import get_sample_data

STUBS = [CandlestickAnalyzer, ChartAnalyzer, TechnicalAnalyzer, TimeseriesAnalyzer]


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return get_sample_data("tv_xauusd_1h")[["open", "high", "low", "close"]].head(200)


def test_every_catalogued_analyzer_is_built_as_its_real_class_and_runs(frame):
    """Раньше все шесть имён давали `BaseAnalyzer` с `NotImplementedError`."""

    expected = {"statistical": StatisticalAnalyzer, "price_levels": PriceLevelAnalyzer}
    assert set(get_available_analyzers()) == set(expected)

    for name, cls in expected.items():
        analyzer = create_analyzer(name, alpha=0.05)
        assert type(analyzer) is cls
        assert analyzer.is_stub is False
        assert analyzer.config == {"alpha": 0.05}
        result = analyzer.analyze(frame)
        assert isinstance(result, AnalysisResult)
        assert result.results, f"{name} ran and returned nothing"


def test_the_executable_catalog_holds_no_stub_and_the_planned_one_holds_only_stubs():
    assert set(get_planned_analyzers()) == set(PLANNED_ANALYSIS_TYPES) == {
        "technical", "chart", "candlestick", "timeseries"
    }
    assert not set(SUPPORTED_ANALYSIS_TYPES) & set(PLANNED_ANALYSIS_TYPES)
    assert all(cls.is_stub for cls in STUBS)


def test_a_planned_name_is_refused_as_planned_not_as_unknown():
    with pytest.raises(NotImplementedError, match="'candlestick' is planned, not implemented"):
        create_analyzer("candlestick")
    with pytest.raises(ValueError, match="Unsupported analyzer type: zones") as excinfo:
        create_analyzer("zones")
    assert "analyze_zones" in str(excinfo.value)


@pytest.mark.parametrize("cls", STUBS, ids=[c.__name__ for c in STUBS])
def test_a_stub_refuses_and_names_what_is_planned(cls, frame):
    """Успешного результата у не написанного анализа быть не может."""

    with pytest.raises(NotImplementedError) as excinfo:
        cls().analyze(frame)
    message = str(excinfo.value)
    assert "is a stub" in message
    assert cls.PLANNED_FEATURES and cls.PLANNED_FEATURES[0] in message


def test_the_base_analyzer_itself_is_abstract(frame):
    with pytest.raises(NotImplementedError):
        BaseAnalyzer("nothing").analyze(frame)
