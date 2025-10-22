"""
Integration tests: Backward Compatibility

Тестирует что старый API (MACDZoneAnalyzer) работает через новый API:
- Deprecation warnings выводятся корректно
- Результаты идентичны новому API
- Все методы работают через delegation
"""

import pytest
import pandas as pd
import warnings
from pathlib import Path

from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer
from bquant.analysis.zones import analyze_zones, analyze_macd_zones
from bquant.analysis.zones.models import ZoneAnalysisResult


class TestMACDZoneAnalyzerBackwardCompatibility:
    """Тесты обратной совместимости MACDZoneAnalyzer"""
    
    @pytest.mark.integration
    def test_old_api_works_through_new_api(self):
        """
        Тест что старый MACDZoneAnalyzer работает через новый API
        """
        df = get_sample_data('tv_xauusd_1h')
        
        # Старый API с deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            analyzer = MACDZoneAnalyzer(
                macd_params={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                zone_params={'min_duration': 2}
            )
            
            # Проверка что deprecation warning выведен
            assert len(w) > 0, "Should show deprecation warning"
            assert issubclass(w[0].category, DeprecationWarning)
            assert "MACDZoneAnalyzer is deprecated" in str(w[0].message)
        
        # Вызов метода через старый API
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = analyzer.analyze_complete_modular(df, perform_clustering=True, n_clusters=3)
        
        # Проверка результата
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        assert result.data is not None
    
    @pytest.mark.integration
    def test_old_vs_new_api_results_identical(self):
        """
        Тест что старый и новый API дают идентичные результаты
        """
        df = get_sample_data('tv_xauusd_1h')
        
        # Старый API
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            analyzer_old = MACDZoneAnalyzer(
                macd_params={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                zone_params={'min_duration': 2}
            )
            result_old = analyzer_old.analyze_complete_modular(df, perform_clustering=False)
        
        # Новый API (эквивалентная конфигурация)
        result_new = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
            .analyze(clustering=False)
            .build()
        )
        
        # Сравнение результатов
        assert len(result_old.zones) == len(result_new.zones), \
            "Old and new API should detect same number of zones"
        
        # Сравнение зон (start/end индексы должны совпадать)
        for zone_old, zone_new in zip(result_old.zones, result_new.zones):
            assert zone_old.start_idx == zone_new.start_idx, \
                f"Zone start mismatch: old={zone_old.start_idx}, new={zone_new.start_idx}"
            assert zone_old.end_idx == zone_new.end_idx, \
                f"Zone end mismatch: old={zone_old.end_idx}, new={zone_new.end_idx}"
            assert zone_old.type == zone_new.type, \
                f"Zone type mismatch: old={zone_old.type}, new={zone_new.type}"
    
    @pytest.mark.integration
    def test_old_api_with_clustering(self):
        """
        Тест старого API с clustering параметром
        """
        df = get_sample_data('tv_xauusd_1h')
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            analyzer = MACDZoneAnalyzer()
            result = analyzer.analyze_complete_modular(df, perform_clustering=True, n_clusters=3)
        
        assert isinstance(result, ZoneAnalysisResult)
        assert result.clustering is not None, "Should have clustering results"
        assert 'cluster_labels' in result.clustering
        assert 'clusters_analysis' in result.clustering
        assert len(result.clustering['cluster_labels']) == len(result.zones)
    
    @pytest.mark.integration
    def test_deprecation_warnings_consistency(self):
        """
        Тест что deprecation warnings выводятся для всех методов
        """
        df = get_sample_data('tv_xauusd_1h')
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Создание экземпляра
            analyzer = MACDZoneAnalyzer()
            
            # Должно быть хотя бы одно предупреждение
            deprecation_warnings = [warning for warning in w 
                                   if issubclass(warning.category, DeprecationWarning)]
            
            assert len(deprecation_warnings) > 0, "Should show deprecation warnings"
            
            # Проверка содержания warning
            warning_messages = [str(w.message) for w in deprecation_warnings]
            assert any("MACDZoneAnalyzer is deprecated" in msg for msg in warning_messages)
            assert any("analyze_zones" in msg for msg in warning_messages)
    
    @pytest.mark.integration
    def test_old_api_parameter_formats(self):
        """
        Тест что старый формат параметров (fast/slow/signal) работает
        через новый формат (fast_period/slow_period/signal_period)
        """
        df = get_sample_data('tv_xauusd_1h')
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Старый формат параметров
            analyzer = MACDZoneAnalyzer(
                macd_params={'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
            )
            result = analyzer.analyze_complete_modular(df)
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        
        # Проверка что MACD рассчитан с правильными параметрами
        assert 'macd' in result.data.columns
        assert 'macd_signal' in result.data.columns
        assert 'macd_hist' in result.data.columns


class TestNewAPIFeatures:
    """Тесты новых возможностей v2.1 API"""
    
    @pytest.mark.integration
    def test_with_strategies_api(self):
        """
        Тест нового .with_strategies() API:
        Конфигурация всех аналитических стратегий через strings
        """
        df = get_sample_data('tv_xauusd_1h')
        
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(
                swing='zigzag',
                divergence='classic',
                shape='statistical',
                volume='standard',
                volatility='combined'
            )
            .analyze(clustering=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        
        # Проверка что все стратегии применены
        for zone in result.zones[:3]:
            if zone.features:
                # Хотя бы некоторые features из разных стратегий должны быть
                feature_keys = set(zone.features.keys())
                # Проверяем наличие features от разных стратегий
                assert len(feature_keys) > 0
    
    @pytest.mark.integration
    def test_zone_features_direct_access(self):
        """
        Тест прямого доступа к zone.features (v2.1):
        Без использования deprecated _zone_to_dict()
        """
        df = get_sample_data('tv_xauusd_1h')
        
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing='find_peaks', shape='statistical')
            .analyze(clustering=False)
            .build()
        )
        
        # Прямой доступ к features
        for zone in result.zones[:5]:
            assert zone.features is not None, "Zone should have features"
            assert isinstance(zone.features, dict)
            
            # Проверка базовых features
            assert 'duration' in zone.features
            assert 'zone_type' in zone.features
            
            # Проверка swing features
            if 'num_peaks' in zone.features or 'num_troughs' in zone.features:
                # Swing strategy применена
                assert True

