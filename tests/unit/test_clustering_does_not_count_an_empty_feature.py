"""G84: кластеризация не считает нулём признак, которого не было ни в одной зоне.

У осциллятора без линии (RSI) `line_amplitude` пуст во всех зонах по построению.
Раньше `cluster_zones` заполнял его нулём, называл в `features_used` и выдавал
`feature_importance['line_amplitude'] = 0.0` — «измерен и не различает» о признаке,
которого не было. Регрессия по той же колонке (G23) выбрасывает её громко; теперь и
кластеризация.

Положительный контроль — MACD-зоны: у них линия есть, и признак обязан остаться, иначе
«пустой выброшен» неотличимо от «выбрасывается всегда».

Запись: `devref/gaps/sequence/g84_clustering_counted_an_empty_feature_as_zero_2026-09.md`.
"""

import logging
import warnings

import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.sequence_analysis import ZoneSequenceAnalyzer
from bquant.core.exceptions import AnalysisError
from bquant.data.samples import get_sample_data

DEFAULT_FEATURES = [
    "duration", "line_amplitude", "oscillator_amplitude", "price_range_pct",
    "correlation_price_oscillator", "num_peaks", "num_troughs",
]


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture(scope="module")
def rsi_zones(data):
    ta = pytest.importorskip("pandas_ta", reason="pandas-ta not installed")
    frame = data.copy()
    frame["RSI_14"] = ta.rsi(frame["close"], length=14)
    result = (
        analyze_zones(frame)
        .detect_zones("threshold", indicator_col="RSI_14",
                      zone_types=["overbought", "oversold"],
                      upper_threshold=70, lower_threshold=30)
        .with_cache(False)
        .build()
    )
    features = [zone.features for zone in result.zones]
    assert features, "fixture produced no zones"
    assert all(f.get("line_amplitude") is None for f in features), (
        "the premise changed: RSI zones now carry a line amplitude"
    )
    return features


@pytest.fixture(scope="module")
def macd_clustering(data):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(False)
        .analyze(clustering=True)
        .build()
    ).clustering


def _cluster(features, analyzer=None, **kwargs):
    analyzer = analyzer or ZoneSequenceAnalyzer()
    with warnings.catch_warnings():
        # Молчаливое приведение `object`-колонки было симптомом: пусть будет ошибкой.
        warnings.simplefilter("error", FutureWarning)
        return analyzer.cluster_zones(features, n_clusters=3, **kwargs)


def test_an_empty_feature_is_not_reported_as_used(rsi_zones):
    results = _cluster(rsi_zones).results
    summary = results["clustering_summary"]
    assert "line_amplitude" not in summary["features_used"]
    assert "line_amplitude" not in results["feature_importance"]
    assert summary["empty_features"] == ["line_amplitude"]


def test_the_drop_is_said_out_loud(rsi_zones, caplog):
    # Логгеры пакета настроены с `propagate=False`: `caplog` вешается на сам логгер.
    analyzer = ZoneSequenceAnalyzer()
    analyzer.logger.addHandler(caplog.handler)
    try:
        result = _cluster(rsi_zones, analyzer=analyzer)
    finally:
        analyzer.logger.removeHandler(caplog.handler)
    assert result.metadata["empty_features"] == ["line_amplitude"]
    assert any(
        r.levelno == logging.WARNING and "line_amplitude" in r.getMessage()
        for r in caplog.records
    ), "the empty feature was dropped silently"


def test_the_labels_are_those_of_the_old_zero_column(rsi_zones):
    """Правка меняет отчёт, а не кластеры: колонка-константа в расстояния не входила."""
    frame = pd.DataFrame(rsi_zones)[DEFAULT_FEATURES].astype(float).fillna(0)
    scaled = StandardScaler().fit_transform(frame)
    old_labels = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(scaled)

    new_labels = _cluster(rsi_zones).results["cluster_labels"]
    np.testing.assert_array_equal(new_labels, old_labels)


def test_nothing_to_cluster_on_is_a_refusal(rsi_zones):
    with pytest.raises(AnalysisError, match="line_amplitude"):
        _cluster(rsi_zones, features_to_use=["line_amplitude"])


def test_a_feature_that_exists_stays(macd_clustering):
    """Положительный контроль: у MACD линия есть, и признак остаётся со своей важностью."""
    summary = macd_clustering["clustering_summary"]
    assert summary["features_used"] == DEFAULT_FEATURES
    assert summary["empty_features"] == []
    assert macd_clustering["feature_importance"]["line_amplitude"] > 0
