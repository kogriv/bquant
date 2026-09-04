"""The cache key has to change whenever something the result reads changes.

Measured before the fix, cache on (the default): the same OHLC with ``RSI_14``
flattened to 50 returned the 64 zones cut on the real RSI from cache — a cold run
gives 1. A volume strategy returned the volume metrics of a frame whose volume was
ten times smaller. The data hash covered ``open/high/low/close`` and nothing else,
while what a strategy reads is its own business: a combined condition reads any
column it likes.

Two more holes in the same key: role resolution popped ``indicator_role`` out of
the caller's rules and wrote ``indicator_col`` in, so one pipeline object built a
different key on its second run; and ``FindPeaksSwingStrategy.config_hash()`` was a
hand-written copy of the strategy's parameters that left ``prominence_warmup`` out.
"""

import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.pipeline import IndicatorSpec, ZoneAnalysisConfig, ZoneAnalysisPipeline
from bquant.analysis.zones.strategies.swing.find_peaks import FindPeaksSwingStrategy
from bquant.core.cache import get_cache_manager
from bquant.data.samples import get_sample_data


@pytest.fixture(autouse=True)
def cold_cache():
    get_cache_manager().clear()
    yield
    get_cache_manager().clear()


def _rsi_frame() -> pd.DataFrame:
    result = (
        analyze_zones(get_sample_data('tv_xauusd_1h'))
        .with_indicator('pandas_ta', 'rsi', length=14)
        .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
        .analyze(clustering=False)
        .build()
    )
    return result.data.copy()


def _threshold_zones(frame: pd.DataFrame):
    return (
        analyze_zones(frame)
        .detect_zones('threshold', indicator_col='RSI_14', upper_threshold=70, lower_threshold=30)
        .analyze(clustering=False)
        .build()
    ).zones


def test_a_different_indicator_column_on_the_same_ohlc_is_not_a_cache_hit():
    frame = _rsi_frame()
    real = _threshold_zones(frame)

    flat = frame.copy()
    flat['RSI_14'] = 50.0                      # never crosses 70 or 30
    flattened = _threshold_zones(flat)

    assert len(real) > 1
    assert len(flattened) == 1, f"flat RSI should give one neutral zone, got {len(flattened)}"


def _volume_metrics(frame: pd.DataFrame, zone: int = 5):
    result = (
        analyze_zones(frame)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_role='hist')
        .with_strategies(volume='standard')
        .analyze(clustering=False)
        .build()
    )
    return result.zones[zone].features['metadata']['volume_metrics']


def test_a_different_volume_on_the_same_ohlc_is_not_a_cache_hit():
    df = get_sample_data('tv_xauusd_1h')
    before = _volume_metrics(df)

    louder = df.copy()
    louder['volume'] = louder['volume'] * 10
    after = _volume_metrics(louder)

    assert before != after


def _combined_zones(frame: pd.DataFrame):
    def regime_is_on(f):
        return f['regime'] > 0

    return (
        analyze_zones(frame)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('combined', conditions=[regime_is_on], logic='AND',
                      zone_type_map={True: 'on', False: 'off'})
        .analyze(clustering=False)
        .build()
    ).zones


def test_a_column_only_a_combined_condition_reads_is_part_of_the_key():
    df = get_sample_data('tv_xauusd_1h')
    always = df.copy()
    always['regime'] = 1
    one_zone = _combined_zones(always)

    alternating = df.copy()
    alternating['regime'] = [i // 100 % 2 for i in range(len(df))]
    many_zones = _combined_zones(alternating)

    assert len(one_zone) < len(many_zones), (len(one_zone), len(many_zones))


def test_resolving_a_role_leaves_the_callers_config_alone_and_the_key_stable():
    df = get_sample_data('tv_xauusd_1h')
    config = ZoneAnalysisConfig(
        indicator=IndicatorSpec('custom', 'macd',
                                {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}),
        zone_detection=ZoneDetectionConfig(strategy_name='zero_crossing',
                                           rules={'indicator_role': 'hist'}),
        perform_clustering=False,
    )
    pipeline = ZoneAnalysisPipeline(config, enable_cache=True)
    rules_before = dict(pipeline.config.zone_detection.rules)
    key_before = pipeline._generate_cache_key(df)

    pipeline.run(df)

    assert pipeline.config.zone_detection.rules == rules_before
    assert 'indicator_role' in pipeline.config.zone_detection.rules
    assert pipeline._generate_cache_key(df) == key_before


def test_find_peaks_warm_up_reaches_the_cache_key():
    short = FindPeaksSwingStrategy(prominence=None, prominence_warmup=100)
    long = FindPeaksSwingStrategy(prominence=None, prominence_warmup=200)

    assert short.config_hash() != long.config_hash()
    assert short.config_hash()['prominence_warmup'] == 100
