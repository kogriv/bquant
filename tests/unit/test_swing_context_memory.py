import sys
from datetime import datetime, timedelta, timezone

import numpy as np

from bquant.analysis.zones.models import SwingContext, SwingPoint


def test_swing_context_memory_footprint_within_expected_bounds():
    point_count = 1_000
    base_time = datetime.now(timezone.utc)
    swing_points = [
        SwingPoint(
            point_id=i,
            timestamp=base_time + timedelta(minutes=i),
            index=i,
            price=float(100 + i),
            swing_type="peak" if i % 2 == 0 else "trough",
            strategy_name="zigzag",
        )
        for i in range(point_count)
    ]

    context = SwingContext(
        swing_points=swing_points,
        indices=np.arange(point_count),
        full_data_length=point_count,
        strategy_name="zigzag",
        strategy_params={"legs": 10, "deviation": 0.05},
    )

    total_bytes = (
        sys.getsizeof(context)
        + sys.getsizeof(context.indices)
        + sys.getsizeof(context.swing_points)
        + sum(sys.getsizeof(point) for point in swing_points)
    )

    avg_bytes_per_point = total_bytes / point_count

    # Allow generous tolerance for interpreter differences.
    assert 40 <= avg_bytes_per_point <= 450, avg_bytes_per_point

