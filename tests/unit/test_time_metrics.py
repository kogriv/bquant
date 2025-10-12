"""
Unit tests for time metrics (peak_time_ratio, trough_time_ratio).

Tests the timing of peaks and troughs within zones.
"""

import pytest
import pandas as pd
import numpy as np

from bquant.analysis.zones.zone_features import ZoneFeatures


class TestTimeMetrics:
    """Test suite for time metrics in ZoneFeatures dataclass."""
    
    def test_zone_features_has_time_ratio_fields(self):
        """Test that ZoneFeatures dataclass has time ratio fields."""
        # Create minimal zone features
        features = ZoneFeatures(
            zone_id='test',
            zone_type='bull',
            duration=100,
            start_price=3000.0,
            end_price=3050.0,
            price_return=0.0167,
            macd_amplitude=5.0,
            hist_amplitude=3.0,
            price_range_pct=0.02,
            peak_time_ratio=0.25,  # NEW: time metric for bull zones
            trough_time_ratio=None  # Should be None for bull zones
        )
        
        assert hasattr(features, 'peak_time_ratio')
        assert hasattr(features, 'trough_time_ratio')
        assert features.peak_time_ratio == 0.25
        assert features.trough_time_ratio is None
    
    def test_bull_zone_has_peak_time_ratio(self):
        """Test that bull zones have peak_time_ratio."""
        features = ZoneFeatures(
            zone_id='test_bull',
            zone_type='bull',
            duration=100,
            start_price=3000.0,
            end_price=3050.0,
            price_return=0.0167,
            macd_amplitude=5.0,
            hist_amplitude=3.0,
            price_range_pct=0.02,
            peak_time_ratio=0.80,  # Late peak
            trough_time_ratio=None
        )
        
        assert features.peak_time_ratio is not None
        assert features.trough_time_ratio is None
    
    def test_bear_zone_has_trough_time_ratio(self):
        """Test that bear zones have trough_time_ratio."""
        features = ZoneFeatures(
            zone_id='test_bear',
            zone_type='bear',
            duration=100,
            start_price=3000.0,
            end_price=2950.0,
            price_return=-0.0167,
            macd_amplitude=5.0,
            hist_amplitude=3.0,
            price_range_pct=0.02,
            peak_time_ratio=None,
            trough_time_ratio=0.35  # Early trough
        )
        
        assert features.trough_time_ratio is not None
        assert features.peak_time_ratio is None
    
    def test_time_ratio_valid_range(self):
        """Test that time ratios are in valid range [0.0, 1.0]."""
        test_ratios = [0.0, 0.25, 0.50, 0.75, 1.0]
        
        for ratio in test_ratios:
            features = ZoneFeatures(
                zone_id=f'test_{ratio}',
                zone_type='bull',
                duration=100,
                start_price=3000.0,
                end_price=3050.0,
                price_return=0.0167,
                macd_amplitude=5.0,
                hist_amplitude=3.0,
                price_range_pct=0.02,
                peak_time_ratio=ratio
            )
            
            assert 0.0 <= features.peak_time_ratio <= 1.0
    
    def test_time_ratio_interpretation(self):
        """Test interpretation of time ratios."""
        # Early peak (20%)
        early = ZoneFeatures(
            zone_id='early',
            zone_type='bull',
            duration=100,
            start_price=3000.0,
            end_price=3050.0,
            price_return=0.0167,
            macd_amplitude=5.0,
            hist_amplitude=3.0,
            price_range_pct=0.02,
            peak_time_ratio=0.20
        )
        
        # Late peak (85%)
        late = ZoneFeatures(
            zone_id='late',
            zone_type='bull',
            duration=100,
            start_price=3000.0,
            end_price=3050.0,
            price_return=0.0167,
            macd_amplitude=5.0,
            hist_amplitude=3.0,
            price_range_pct=0.02,
            peak_time_ratio=0.85
        )
        
        # Interpretation logic
        early_timing = "early" if early.peak_time_ratio < 0.33 else "mid"
        late_timing = "late" if late.peak_time_ratio > 0.67 else "mid"
        
        assert early_timing == "early"
        assert late_timing == "late"
        
        # Early peak suggests early exhaustion
        # Late peak suggests sustained momentum


def run_tests():
    """Run all time metrics tests."""
    pytest.main([__file__, '-v'])


if __name__ == '__main__':
    run_tests()
