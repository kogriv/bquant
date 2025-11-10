import pandas as pd
import pytest

from bquant.analysis.zones.pipeline import (
    ZoneAnalysisBuilder,
    ZoneDetectionConfig,
)


def _empty_dataframe() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=5, freq="H")
    return pd.DataFrame(
        {
            "open": [1, 1, 1, 1, 1],
            "high": [1, 1, 1, 1, 1],
            "low": [1, 1, 1, 1, 1],
            "close": [1, 1, 1, 1, 1],
        },
        index=index,
    )


def test_with_strategies_rejects_multiple_swing_strategies():
    builder = ZoneAnalysisBuilder(_empty_dataframe())
    config = ZoneDetectionConfig(strategy_name="preloaded", rules={}, min_duration=1)
    builder.detect_zones(config.strategy_name, min_duration=config.min_duration, **config.rules)

    with pytest.raises(ValueError, match="Only one swing strategy is supported"):
        builder.with_strategies(swing=["zigzag", "find_peaks"])

