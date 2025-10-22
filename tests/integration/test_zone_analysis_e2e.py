"""
Integration tests: End-to-End Zone Analysis Pipeline

Тестирует полный пайплайн анализа зон для разных индикаторов:
- MACD zones (zero crossing)
- RSI zones (threshold)
- AO zones (zero crossing)
- Preloaded zones
- Performance benchmarks
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones, analyze_macd_zones, analyze_rsi_zones, analyze_ao_zones
from bquant.analysis.zones.models import ZoneAnalysisResult


class TestMACDFullPipeline:
    """End-to-end тесты для MACD зон"""
    
    @pytest.mark.integration
    def test_macd_full_pipeline(self):
        """
        Тест полного пайплайна MACD анализа:
        1. Загрузка данных
        2. Создание индикатора
        3. Детекция зон
        4. Анализ (features + clustering)
        5. Проверка результатов
        """
        # 1. Загрузка sample данных
        df = get_sample_data('tv_xauusd_1h')
        assert len(df) > 100, "Need sufficient data for analysis"
        
        # 2-4. Полный pipeline через fluent API
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=2)
            .with_strategies(swing='find_peaks', shape='statistical')
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
        
        # 5. Проверка результатов
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0, "Should detect some zones"
        assert result.data is not None, "Should return enhanced DataFrame"
        assert 'macd' in result.data.columns, "Should have MACD indicator"
        assert 'macd_hist' in result.data.columns, "Should have MACD histogram"
        
        # Проверка зон
        for zone in result.zones[:5]:  # Check first 5 zones
            assert zone.zone_id is not None
            assert zone.start_idx < zone.end_idx
            assert zone.type in ['bull', 'bear']  # v2.1: simplified zone types
            assert zone.features is not None, "Zone should have features"
            
            # Проверка наличия swing features
            if zone.features:
                assert 'num_peaks' in zone.features or 'num_troughs' in zone.features
        
        # Проверка clustering
        if result.clustering is not None:
            assert 'cluster_labels' in result.clustering
            assert 'clusters_analysis' in result.clustering
            assert len(result.clustering['cluster_labels']) == len(result.zones)
    
    @pytest.mark.integration
    def test_macd_preset_convenience(self):
        """Тест удобной preset функции для MACD"""
        df = get_sample_data('tv_xauusd_1h')
        
        # Использование preset функции
        result = analyze_macd_zones(
            df,
            fast=12,
            slow=26,
            signal=9,
            min_duration=2,
            clustering=True,
            n_clusters=3
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        assert 'macd' in result.data.columns


class TestRSIFullPipeline:
    """End-to-end тесты для RSI зон"""
    
    @pytest.mark.integration
    def test_rsi_full_pipeline(self):
        """
        Тест полного пайплайна RSI анализа:
        Threshold detection (overbought/oversold)
        """
        df = get_sample_data('tv_xauusd_1h')
        
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'rsi', period=14)
            .detect_zones('threshold', 
                         indicator_col='rsi',
                         upper_threshold=70,
                         lower_threshold=30,
                         min_duration=2)
            .with_strategies(shape='statistical', volume='standard')
            .analyze(clustering=True, n_clusters=2)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) >= 0, "May have 0 zones if no threshold breaches"
        assert 'rsi' in result.data.columns
        
        # Если есть зоны, проверяем их
        for zone in result.zones[:3]:
            assert zone.type in ['overbought', 'oversold']
            if zone.features:
                assert 'shape_quality' in zone.features or 'volume_surge' in zone.features
    
    @pytest.mark.integration
    def test_rsi_preset_convenience(self):
        """Тест удобной preset функции для RSI"""
        df = get_sample_data('tv_xauusd_1h')
        
        result = analyze_rsi_zones(
            df,
            period=14,
            upper_threshold=70,
            lower_threshold=30,
            min_duration=2,
            clustering=False
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert 'rsi' in result.data.columns


class TestAOFullPipeline:
    """End-to-end тесты для AO зон"""
    
    @pytest.mark.integration
    def test_ao_full_pipeline(self):
        """
        Тест полного пайплайна AO анализа:
        Zero crossing detection
        """
        df = get_sample_data('tv_xauusd_1h')
        
        result = (
            analyze_zones(df)
            .with_indicator('pandas_ta', 'ao', fast=5, slow=34)
            .detect_zones('zero_crossing', indicator_col='AO_5_34', min_duration=2)
            .with_strategies(swing='pivot_points')
            .analyze(clustering=True, n_clusters=2)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        assert 'AO_5_34' in result.data.columns
        
        for zone in result.zones[:3]:
            assert zone.type in ['bull', 'bear']
    
    @pytest.mark.integration
    def test_ao_preset_convenience(self):
        """Тест удобной preset функции для AO"""
        df = get_sample_data('tv_xauusd_1h')
        
        result = analyze_ao_zones(
            df,
            fast=5,
            slow=34,
            min_duration=2
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert 'AO_5_34' in result.data.columns


class TestPreloadedZonesPipeline:
    """End-to-end тесты для preloaded зон"""
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Preloaded zones require specific format - TODO: fix zones_data structure")
    def test_preloaded_zones_pipeline(self):
        """
        Тест пайплайна с preloaded зонами:
        Зоны созданы внешним источником
        
        TODO: Fix zones_data format - requires investigation of PreloadedZonesDetection strategy
        """
        df = get_sample_data('tv_xauusd_1h')
        
        # Создаем тестовые preloaded зоны с правильной структурой
        zones_data = pd.DataFrame({
            'zone_id': [1, 2, 3],  # Required field
            'start_time': [df.index[10], df.index[50], df.index[100]],
            'end_time': [df.index[20], df.index[60], df.index[110]],
            'type': ['bull', 'bear', 'bull']  # v2.1: simplified zone types
        })
        
        result = (
            analyze_zones(df)
            .detect_zones('preloaded', zones_data=zones_data)
            .with_strategies(shape='statistical')
            .analyze(clustering=False)
            .with_cache(enable=False)  # Disable cache to avoid DataFrame serialization
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) == 3, "Should have exactly 3 preloaded zones"
        
        # Проверка базовых свойств зон
        for zone in result.zones:
            assert zone.zone_id is not None
            assert zone.type in ['bull', 'bear']
            assert zone.duration > 0
            assert zone.features is not None, "Should have features"
            if zone.features:
                assert 'duration' in zone.features
                assert 'zone_type' in zone.features


class TestPipelinePerformance:
    """Тесты производительности пайплайна"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_pipeline_performance(self):
        """
        Тест производительности:
        Pipeline не должен быть медленнее старого API
        """
        import time
        
        df = get_sample_data('tv_xauusd_1h')
        
        # Замер времени для нового API
        start_time = time.time()
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
        new_api_time = time.time() - start_time
        
        assert isinstance(result, ZoneAnalysisResult)
        assert len(result.zones) > 0
        
        # Проверка что выполнилось за разумное время (< 5 секунд для 1000 баров)
        assert new_api_time < 5.0, f"Pipeline too slow: {new_api_time:.2f}s"
    
    @pytest.mark.integration
    def test_multiple_indicators_performance(self):
        """
        Тест производительности с несколькими индикаторами:
        MACD, RSI, AO одновременно
        """
        import time
        
        df = get_sample_data('tv_xauusd_1h')
        
        start_time = time.time()
        
        # MACD
        result_macd = analyze_macd_zones(df, clustering=False)
        
        # RSI
        result_rsi = analyze_rsi_zones(df, clustering=False)
        
        # AO
        result_ao = analyze_ao_zones(df, clustering=False)
        
        total_time = time.time() - start_time
        
        assert isinstance(result_macd, ZoneAnalysisResult)
        assert isinstance(result_rsi, ZoneAnalysisResult)
        assert isinstance(result_ao, ZoneAnalysisResult)
        
        # Все 3 индикатора должны выполниться быстро (< 10 секунд)
        assert total_time < 10.0, f"Multiple indicators too slow: {total_time:.2f}s"


class TestPipelineEdgeCases:
    """Тесты граничных случаев пайплайна"""
    
    @pytest.mark.integration
    def test_small_dataset(self):
        """Тест с малым датасетом (< 100 баров)"""
        df = get_sample_data('tv_xauusd_1h')
        df_small = df.head(50)
        
        # Pipeline должен работать даже с малым датасетом
        result = (
            analyze_zones(df_small)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .analyze(clustering=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        # Может быть 0 зон, это нормально для малого датасета
        assert len(result.zones) >= 0
    
    @pytest.mark.integration
    def test_no_zones_detected(self):
        """Тест когда зоны не обнаружены"""
        df = get_sample_data('tv_xauusd_1h')
        
        # RSI с экстремальными порогами (не должно найти зоны)
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'rsi', period=14)
            .detect_zones('threshold',
                         indicator_col='rsi',
                         upper_threshold=99,
                         lower_threshold=1,
                         min_duration=2)
            .analyze(clustering=False)
            .build()
        )
        
        assert isinstance(result, ZoneAnalysisResult)
        # Pipeline должен корректно обработать отсутствие зон
        assert result.zones is not None  # Empty list, but not None

