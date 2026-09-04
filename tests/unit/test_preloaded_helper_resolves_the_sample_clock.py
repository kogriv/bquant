"""``load_preloaded_zones()`` works on the bundled sample exactly as the pipeline does.

The pipeline resolves the time index before any detector sees the data (G30). The
helper handed the caller's frame to the detector as it came, and the bundled samples
carry time as a column: the merge compared timestamps against positions and died
inside pandas — ``TypeError: '>=' not supported between instances of 'numpy.ndarray'
and 'Timestamp'`` — while the same zones through ``analyze_zones()`` loaded fine.
"""

import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.detection import load_preloaded_zones
from bquant.data.samples import get_sample_data


def _sample_and_zones():
    df = get_sample_data('tv_xauusd_1h')
    t = df['time']
    zones = pd.DataFrame({
        'zone_id': [0, 1, 2],
        'type': ['bull', 'bear', 'bull'],
        'start_time': [t.iloc[100], t.iloc[300], t.iloc[600]],
        'end_time': [t.iloc[140], t.iloc[330], t.iloc[650]],
    })
    return df, zones


def test_the_helper_loads_the_same_zones_as_the_pipeline(tmp_path):
    df, zones = _sample_and_zones()
    path = tmp_path / 'expert_zones.csv'
    zones.to_csv(path, index=False)

    through_helper = load_preloaded_zones(path, df)
    through_pipeline = (
        analyze_zones(df)
        .detect_zones('preloaded', zones_data=zones)
        .analyze(clustering=False)
        .build()
    ).zones

    assert [z.duration for z in through_helper] == [z.duration for z in through_pipeline]
    assert [z.start_time for z in through_helper] == [z.start_time for z in through_pipeline]


def test_a_frame_without_any_time_axis_is_refused_by_name(tmp_path):
    df, zones = _sample_and_zones()
    positional = df.drop(columns=['time'])
    path = tmp_path / 'expert_zones.csv'
    zones.to_csv(path, index=False)

    with pytest.raises(ValueError, match=r"has no time axis"):
        load_preloaded_zones(path, positional)
