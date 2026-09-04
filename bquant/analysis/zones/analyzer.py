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
                # The class lives in `analysis.statistical.regression`. This used
                # to import it from `analysis.timeseries`, which does not export
                # it — and `except ImportError` swallowed the miss, so
                # `.analyze(regression=True)` quietly produced no regression at
                # all while logging a line that read like an optional dependency
                # was absent. statsmodels was installed the whole time.
                from bquant.analysis.statistical.regression import ZoneRegressionAnalyzer
                regression_analyzer = ZoneRegressionAnalyzer()
            except ImportError as exc:
                self.logger.warning(
                    "ZoneRegressionAnalyzer unavailable (%s); "
                    "regression will be skipped", exc
                )
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
                      column_schema: Optional[Any] = None,
                      min_duration: int = 1) -> ZoneAnalysisResult:
        """
        Анализ готовых зон.

        ЧИСТАЯ КООРДИНАЦИЯ - только вызовы делегатов!

        Args:
            zones: Список зон для анализа
            data: Исходный DataFrame с OHLCV + индикаторами
            perform_clustering: Выполнять ли кластеризацию
            n_clusters: Количество кластеров
            run_regression: Выполнять ли регрессионный анализ
            column_schema: Отображение ``(индикатор, роль) → колонка``, если оно
                известно. Извлечение признаков спрашивает по нему роль вместо
                того, чтобы угадывать имя колонки.
            min_duration: Порог длительности **отчётности**: зоны короче него в
                анализ не берутся. ``1`` (по умолчанию) — не отсеивать ничего.

                Раньше этот порог стоял в детекции со значением ``2``, и это
                молча превращало мощение таймлайна в решето: соседи выброшенной
                зоны переставали примыкать, а список зон об этом не сообщал.
                Здесь отсев виден в результате — ``metadata['duration_filter']``
                называет и порог, и сколько зон и баров он исключил, — а сам
                отсев запрашивается явно. Значение ``2`` нигде и никогда не было
                обосновано; на 1000 барах сэмпла оно давало 8 разрывов на
                флагманском пути, на ~100 тыс. баров H1 — 136 разрывов и 120
                структурно невозможных соседств одного типа.
                Разбор: ``devref/gaps/sequence/``.

        Returns:
            ZoneAnalysisResult с полными результатами анализа
        """
        if not zones:
            return self._empty_result(data)

        if min_duration < 1:
            raise ValueError(
                f"min_duration must be at least 1 (got {min_duration}); "
                "1 means no filtering"
            )

        self.logger.info(f"Starting analysis of {len(zones)} zones")

        # 1. Извлечение признаков (БЕЗ адаптеров!)
        #    Результат выровнен по позиции с `zones`; None = зону не измерили.
        all_features = self.features.extract_all_zones_features(
            zones, column_schema=column_schema
        )

        # ✅ v2.1 FIX: Write features back to ZoneInfo for convenient access
        # This makes features immediately available in zone.features dict
        for zone, features in zip(zones, all_features):
            zone.features = features.to_dict() if features is not None else None

        # 1a. Фильтр отчётности. Он применяется **после** измерения, поэтому
        #     исключённая зона остаётся полноценной зоной со своими признаками —
        #     она просто не участвует в агрегатах.
        duration_filter = self._duration_filter(zones, min_duration)
        analysed_zones = [
            zone for zone in zones if zone.duration >= min_duration
        ]
        zones_features = [
            features for zone, features in zip(zones, all_features)
            if features is not None and zone.duration >= min_duration
        ]
        unmeasured = sum(1 for features in all_features if features is None)

        if not zones_features:
            self.logger.warning(
                "No zone survived measurement and the duration filter "
                "(min_duration=%d); returning an empty result", min_duration
            )
            return self._empty_result(data)

        # 2. Статистический анализ
        statistics = self.features.analyze_zones_distribution([f.to_dict() for f in zones_features])
        
        # Словарь типов зон резолвится из самих зон: его знает стратегия детекции,
        # и её имя лежит в indicator_context. Всё, что ниже, спрашивает объявленные
        # свойства типа (полярность, контрастную пару), а не сравнивает его имя со
        # строковым литералом — дефект G20.
        from .detection import resolve_vocabulary
        vocabulary = resolve_vocabulary(analysed_zones)
        
        # 3. Тестирование гипотез
        hypothesis_tests = self.hypotheses.run_all_tests(
            [f.to_dict() for f in zones_features], vocabulary=vocabulary
        )
        
        # 4. Анализ последовательностей (требует минимум 3 зоны)
        sequence_analysis = None
        if len(zones_features) >= 3:
            try:
                sequence_analysis = self.sequences.analyze_zone_transitions(
                    zones_features, vocabulary=vocabulary
                )
            except Exception as e:
                self.logger.error(f"Failed to perform sequence analysis: {e}")
                sequence_analysis = {'error': str(e)}
        
        # 5. Кластеризация (опционально)
        clustering = None
        if perform_clustering and len(zones_features) >= n_clusters:
            clustering = self.sequences.cluster_zones(
                zones_features, n_clusters=n_clusters, vocabulary=vocabulary
            )
            self.logger.info(f"Performed clustering: {n_clusters} clusters")
        
        # 6. Регрессия (опционально)
        regression_results = None
        if run_regression and self.regression and len(zones_features) > 10:
            # Регрессия — необязательный шаг, и её отказ не повод убивать весь
            # анализ: остальные разделы результата от неё не зависят. Но и молчать
            # нельзя — иначе `regression_results is None` неотличимо от «не
            # просили». Причина едет в результат, как это уже сделано для анализа
            # последовательностей.
            features_dicts = [f.to_dict() for f in zones_features]
            regression_results = {}
            for key, method in (('duration', self.regression.predict_zone_duration),
                                ('return', self.regression.predict_price_return)):
                try:
                    regression_results[key] = method(features_dicts)
                except Exception as e:
                    self.logger.warning("Regression '%s' could not be fitted: %s", key, e)
                    regression_results[key] = {'error': str(e)}
            self.logger.info("Performed regression analysis")
        
        # 7. Валидация здесь не выполняется — и не принимается. Анализатор получает
        # готовые зоны и не владеет детекцией, а валидация обязана заново прогнать
        # детекцию на каждом окне. Это делает пайплайн (`ZoneAnalysisPipeline`) —
        # он и заполняет `validation_results`. До G55 параметр `run_validation`
        # здесь принимался, писал «requested but not executed» в лог и оставлял
        # `None`, неотличимый от «не просили».
        validation_results = None

        # Извлекаем метаданные из DataFrame.attrs (если есть)
        metadata = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_zones': len(zones),
            'zone_types': list(set(z.type for z in zones)),
            'clustering_performed': clustering is not None,
            'regression_performed': regression_results is not None,
            # Что именно попало в агрегаты, а что осталось только в `zones`.
            'duration_filter': {**duration_filter, 'zones_unmeasured': unmeasured},
        }

        swing_coverage = self._swing_coverage(zones)
        if swing_coverage is not None:
            metadata['swing_coverage'] = swing_coverage
        
        # Добавляем метаданные о данных из df.attrs
        if hasattr(data, 'attrs'):
            if 'symbol' in data.attrs:
                metadata['symbol'] = data.attrs['symbol']
            if 'timeframe' in data.attrs:
                metadata['timeframe'] = data.attrs['timeframe']
            if 'source' in data.attrs:
                metadata['source'] = data.attrs['source']
            if 'dataset_name' in data.attrs:
                metadata['dataset_name'] = data.attrs['dataset_name']
        
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
            metadata=metadata
        )
        
        self.logger.info(
            f"Analysis complete: {len(zones_features)} of {len(zones)} zones "
            f"aggregated, clustering={clustering is not None}, "
            f"regression={regression_results is not None}"
        )

        return result

    def _swing_coverage(self, zones: List[ZoneInfo]) -> Optional[Dict[str, Any]]:
        """Сколько зон получили хотя бы один свинг — и громко сказать, если ни одна.

        G35: `swing_metrics` с `num_swings: 0` выглядит ровно так же, когда движения
        действительно не было и когда порог стратегии крупнее самой зоны. На часовом
        золоте `min_amplitude_pct` пресета по умолчанию (2% цены) больше медианного
        размаха зоны (1.2%), и две стратегии из трёх не находят ничего ни в одной
        зоне — молча.

        Отсюда два ответа вместо одного: число в метаданных, чтобы программа могла
        спросить, и предупреждение в лог, чтобы человек не искал причину в рынке.
        """

        strategy = getattr(self.features, "swing_strategy", None)
        if strategy is None or not zones:
            return None

        measured = 0
        for zone in zones:
            metrics = ((zone.features or {}).get("metadata") or {}).get("swing_metrics")
            if metrics and (metrics.get("num_swings") or 0) > 0:
                measured += 1

        coverage = {
            "strategy": type(strategy).__name__,
            "zones": len(zones),
            "zones_with_swings": measured,
        }

        if measured == 0:
            self.logger.warning(
                "Swing strategy %s found no swings in any of %d zones. This is "
                "indistinguishable from 'the market did not move': check the "
                "thresholds before the data. The default preset is calibrated for "
                "wide zones - try .with_swing_preset('narrow_zone'). See "
                "devref/gaps/swing/g35_default_preset_measures_nothing_and_says_nothing_2026-08.md",
                coverage["strategy"],
                len(zones),
            )

        return coverage

    def _duration_filter(self, zones: List[ZoneInfo],
                         min_duration: int) -> Dict[str, Any]:
        """Что исключит порог длительности — посчитано, а не подразумеваемо.

        Порог применяется к агрегатам, но ``result.zones`` продолжает содержать
        **все** зоны с их признаками: отчётный фильтр ничего не уничтожает, он
        сужает выборку, и потребитель видит, насколько.
        """
        excluded = [zone for zone in zones if zone.duration < min_duration]

        if excluded:
            self.logger.info(
                "Duration filter (min_duration=%d) leaves %d of %d zones out of "
                "the aggregates (%d bars); they remain in `result.zones`.",
                min_duration, len(excluded), len(zones),
                sum(zone.duration for zone in excluded),
            )

        return {
            'min_duration': int(min_duration),
            'zones_analysed': len(zones) - len(excluded),
            'zones_excluded': len(excluded),
            'bars_excluded': int(sum(zone.duration for zone in excluded)),
            'excluded_zone_ids': [zone.zone_id for zone in excluded],
        }

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

