"""Tests for cache key generation and invalidation in the zone analysis pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd
import pytest

from bquant.analysis.zones.pipeline import (
    IndicatorConfig,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
)
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.data.samples import get_sample_data


def _make_test_config() -> ZoneAnalysisConfig:
    return ZoneAnalysisConfig(
        indicator=IndicatorConfig(
            source="custom",
            name="macd",
            params={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ),
        zone_detection=ZoneDetectionConfig(
            min_duration=2,
            zone_types=["bull"],
            rules={"indicator_col": "macd_hist"},
            strategy_name="zero_crossing",
        ),
        perform_clustering=False,
        n_clusters=3,
        run_regression=False,
        run_validation=False,
    )


def _make_small_dataframe() -> pd.DataFrame:
    data = {
        "open": [1.0, 1.1, 1.2, 1.1, 1.0],
        "high": [1.1, 1.2, 1.3, 1.2, 1.1],
        "low": [0.9, 1.0, 1.1, 1.0, 0.9],
        "close": [1.05, 1.15, 1.18, 1.12, 1.02],
    }
    return pd.DataFrame(data)


def test_cache_key_changes_on_strategy_update() -> None:
    df = _make_small_dataframe()
    pipeline = ZoneAnalysisPipeline(_make_test_config(), enable_cache=True)

    original_key = pipeline._generate_cache_key(df)

    pipeline.swing_strategies["zigzag"].deviation = 0.02
    pipeline._swing_preset_params["zigzag"]["deviation"] = 0.02

    updated_key = pipeline._generate_cache_key(df)

    assert original_key != updated_key


class _RecordingCache:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, str]] = []
        self.storage: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        self.calls.append(("get", key))
        return self.storage.get(key)

    def put(self, key: str, value: Any, ttl: int | None = None, disk: bool = True) -> None:
        self.calls.append(("put", key))
        self.storage[key] = value

    def invalidate(self, key: str) -> None:
        self.calls.append(("invalidate", key))
        self.storage.pop(key, None)


@pytest.mark.slow
def test_pipeline_recomputes_after_preset_switch() -> None:
    df = get_sample_data("tv_xauusd_1h").set_index("time")

    pipeline = ZoneAnalysisPipeline(_make_test_config(), enable_cache=True)
    recording_cache = _RecordingCache()
    pipeline.cache_manager = recording_cache

    default_result = pipeline.run(df)

    pipeline.with_swing_preset("narrow_zone")
    narrow_result = pipeline.run(df)

    get_calls = [key for action, key in recording_cache.calls if action == "get"]

    assert len(get_calls) == 2
    assert get_calls[0] != get_calls[1]
    assert default_result is not narrow_result
    assert len(recording_cache.storage) == 2
