"""
Universal Zone Analyzer

Универсальный оркестратор для анализа зон любых индикаторов.

Особенности:
- Агностичен к источнику зон (MACD, RSI, preloaded, custom)
- Использует Dependency Injection для гибкости
- Чистая координация без адаптеров
"""

from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime

from .models import ZoneInfo, ZoneAnalysisResult
from bquant.core.logging_config import get_logger

logger = get_logger(__name__)


class UniversalZoneAnalyzer:
    """
    Универсальный оркестратор анализа зон.
    
    НЕ ЗНАЕТ:
    - Откуда зоны (MACD, AO, preloaded, кастомные)
    - Как зоны были созданы
    
    ЗНАЕТ ТОЛЬКО:
    - Как анализировать List[ZoneInfo]
    
    Example:
        # С default компонентами
        analyzer = UniversalZoneAnalyzer()
        result = analyzer.analyze_zones(zones, data)
        
        # С кастомными компонентами (DI)
        from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
        from bquant.analysis.statistical import HypothesisTestSuite
        
        analyzer = UniversalZoneAnalyzer(
            features_analyzer=ZoneFeaturesAnalyzer(swing_strategy='pivot_points'),
            hypothesis_suite=HypothesisTestSuite(alpha=0.01)
        )
        result = analyzer.analyze_zones(zones, data, perform_clustering=True)
    """
    
    def __init__(self,
                 features_analyzer=None,
                 hypothesis_suite=None,
                 sequence_analyzer=None,
                 regression_analyzer=None,
                 validation_suite=None,
                 swing_strategy=None,
                 shape_strategy=None,
                 divergence_strategy=None,
                 volatility_strategy=None,
                 volume_strategy=None):
        """
        Инициализация с Dependency Injection.
        
        Args:
            features_analyzer: Анализатор признаков зон (default: ZoneFeaturesAnalyzer)
            hypothesis_suite: Набор статистических тестов (default: HypothesisTestSuite)
            sequence_analyzer: Анализатор последовательностей (default: ZoneSequenceAnalyzer)
            regression_analyzer: Регрессионный анализ (default: ZoneRegressionAnalyzer)
            validation_suite: Валидация моделей (default: ValidationSuite)
            swing_strategy: Стратегия для swing анализа (передается в features_analyzer)
            shape_strategy: Стратегия для shape анализа (передается в features_analyzer)
            divergence_strategy: Стратегия для divergence анализа (передается в features_analyzer)
            volatility_strategy: Стратегия для volatility анализа (передается в features_analyzer)
            volume_strategy: Стратегия для volume анализа (передается в features_analyzer)
        """
        self.logger = logger
        
        # DI для features analyzer
        if features_analyzer is None:
            from .zone_features import ZoneFeaturesAnalyzer
            features_analyzer = ZoneFeaturesAnalyzer(
                swing_strategy=swing_strategy,
                shape_strategy=shape_strategy,
                divergence_strategy=divergence_strategy,
                volatility_strategy=volatility_strategy,
                volume_strategy=volume_strategy
            )
        
        # DI для остальных компонентов
        if hypothesis_suite is None:
            from bquant.analysis.statistical import HypothesisTestSuite
            hypothesis_suite = HypothesisTestSuite()
        
        if sequence_analyzer is None:
            from .sequence_analysis import ZoneSequenceAnalyzer
            sequence_analyzer = ZoneSequenceAnalyzer()
        
        if regression_analyzer is None:
            try:
                from bquant.analysis.timeseries import ZoneRegressionAnalyzer
                regression_analyzer = ZoneRegressionAnalyzer()
            except ImportError:
                self.logger.warning("ZoneRegressionAnalyzer not available")
                regression_analyzer = None
        
        if validation_suite is None:
            try:
                from bquant.analysis.validation import ValidationSuite
                validation_suite = ValidationSuite()
            except ImportError:
                self.logger.warning("ValidationSuite not available")
                validation_suite = None
        
        # Сохранить компоненты
        self.features = features_analyzer
        self.hypotheses = hypothesis_suite
        self.sequences = sequence_analyzer
        self.regression = regression_analyzer
        self.validation = validation_suite
        
        self.logger.info("UniversalZoneAnalyzer initialized with DI components")
    
    def analyze_zones(self, 
                      zones: List[ZoneInfo],
                      data: pd.DataFrame,
                      perform_clustering: bool = True,
                      n_clusters: int = 3,
                      run_regression: bool = False,
                      run_validation: bool = False) -> ZoneAnalysisResult:
        """
        Анализ готовых зон.
        
        ЧИСТАЯ КООРДИНАЦИЯ - только вызовы делегатов!
        
        Args:
            zones: Список зон для анализа
            data: Исходный DataFrame с OHLCV + индикаторами
            perform_clustering: Выполнять ли кластеризацию
            n_clusters: Количество кластеров
            run_regression: Выполнять ли регрессионный анализ
            run_validation: Выполнять ли валидацию
            
        Returns:
            ZoneAnalysisResult с полными результатами анализа
        """
        if not zones:
            return self._empty_result(data)
        
        self.logger.info(f"Starting analysis of {len(zones)} zones")
        
        # 1. Извлечение признаков (БЕЗ адаптеров!)
        zones_features = self.features.extract_all_zones_features(zones)
        
        # 2. Статистический анализ
        statistics = self.features.analyze_zones_distribution([f.to_dict() for f in zones_features])
        
        # 3. Тестирование гипотез
        hypothesis_tests = self.hypotheses.run_all_tests([f.to_dict() for f in zones_features])
        
        # 4. Анализ последовательностей (требует минимум 3 зоны)
        sequence_analysis = None
        if len(zones_features) >= 3:
            try:
                sequence_analysis = self.sequences.analyze_zone_transitions(zones_features)
            except Exception as e:
                self.logger.error(f"Failed to perform sequence analysis: {e}")
                sequence_analysis = {'error': str(e)}
        
        # 5. Кластеризация (опционально)
        clustering = None
        if perform_clustering and len(zones) >= n_clusters:
            clustering = self.sequences.cluster_zones(zones_features, n_clusters=n_clusters)
            self.logger.info(f"Performed clustering: {n_clusters} clusters")
        
        # 6. Регрессия (опционально)
        regression_results = None
        if run_regression and self.regression and len(zones) > 10:
            regression_results = {
                'duration': self.regression.predict_zone_duration([f.to_dict() for f in zones_features]),
                'return': self.regression.predict_price_return([f.to_dict() for f in zones_features])
            }
            self.logger.info("Performed regression analysis")
        
        # 7. Валидация (опционально)
        validation_results = None
        if run_validation and self.validation and len(zones) > 20:
            # Валидация требует функцию анализа и DataFrame
            # Это будет реализовано позже в integration тестах
            self.logger.info("Validation requested but not executed (need analyze_func)")
        
        # Сборка результата
        result = ZoneAnalysisResult(
            zones=zones,
            statistics=statistics.results if hasattr(statistics, 'results') else statistics,
            hypothesis_tests=hypothesis_tests,
            sequence_analysis=sequence_analysis.results if hasattr(sequence_analysis, 'results') else sequence_analysis,
            clustering=clustering.results if clustering and hasattr(clustering, 'results') else clustering,
            regression_results=regression_results,
            validation_results=validation_results,
            data=data,
            metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'total_zones': len(zones),
                'zone_types': list(set(z.type for z in zones)),
                'clustering_performed': clustering is not None,
                'regression_performed': regression_results is not None
            }
        )
        
        self.logger.info(
            f"Analysis complete: {len(zones)} zones, "
            f"clustering={clustering is not None}, "
            f"regression={regression_results is not None}"
        )
        
        return result
    
    def _empty_result(self, data: pd.DataFrame) -> ZoneAnalysisResult:
        """Создать пустой результат."""
        self.logger.warning("No zones provided, returning empty result")
        
        return ZoneAnalysisResult(
            zones=[],
            statistics={},
            hypothesis_tests={},
            sequence_analysis=None,
            clustering=None,
            regression_results=None,
            data=data,
            metadata={
                'analysis_timestamp': datetime.now().isoformat(),
                'total_zones': 0,
                'zone_types': []
            }
        )


# Экспорт
__all__ = [
    'UniversalZoneAnalyzer'
]

