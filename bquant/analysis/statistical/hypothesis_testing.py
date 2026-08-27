"""
Модуль тестирования гипотез для торговых стратегий BQuant

Адаптировано из scripts/research/hypothesis_testing.py с улучшениями для новой архитектуры.
Предоставляет комплексные статистические тесты для анализа зон и торговых паттернов.
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu, chi2_contingency
from typing import Dict, Any, Optional, List, Union
import warnings
from dataclasses import dataclass
from datetime import datetime

from ...core.logging_config import get_logger
from ...core.exceptions import StatisticalAnalysisError
from ..zones.models import ZoneVocabulary
from .. import AnalysisResult

# Получаем логгер для модуля
logger = get_logger(__name__)

warnings.filterwarnings('ignore')


@dataclass
class HypothesisTestResult:
    """
    Результат статистического теста гипотезы.
    
    Attributes:
        hypothesis: Описание тестируемой гипотезы
        test_type: Тип статистического теста
        statistic: Значение тестовой статистики
        p_value: p-значение теста
        significant: Является ли результат значимым (p < alpha)
        alpha: Уровень значимости
        effect_size: Размер эффекта (если применимо)
        confidence_interval: Доверительный интервал (если применимо)
        sample_size: Размер выборки
        metadata: Дополнительные метаданные теста
    """
    hypothesis: str
    test_type: str
    statistic: float
    p_value: float
    significant: bool
    alpha: float = 0.05
    effect_size: Optional[float] = None
    confidence_interval: Optional[tuple] = None
    sample_size: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация результата в словарь."""
        return {
            'hypothesis': self.hypothesis,
            'test_type': self.test_type,
            'statistic': self.statistic,
            'p_value': self.p_value,
            'significant': self.significant,
            'alpha': self.alpha,
            'effect_size': self.effect_size,
            'confidence_interval': self.confidence_interval,
            'sample_size': self.sample_size,
            'metadata': self.metadata
        }


class HypothesisTestSuite:
    """
    Набор статистических тестов для анализа торговых зон и паттернов.
    """
    
    def __init__(self, alpha: float = 0.05):
        """
        Инициализация набора тестов.
        
        Args:
            alpha: Уровень значимости для всех тестов
        """
        self.alpha = alpha
        self.logger = get_logger(f"{__name__}.HypothesisTestSuite")
        
        self.logger.info(f"Initialized hypothesis test suite with alpha={alpha}")
    
    def test_zone_duration_hypothesis(self, zones_features: List[Dict[str, Any]]) -> HypothesisTestResult:
        """
        Тест гипотезы о влиянии длительности зон на последующее движение цены.
        
        H0: Длительность зоны не влияет на доходность
        H1: Длительные зоны дают другую доходность чем короткие
        
        Args:
            zones_features: Список словарей с характеристиками зон
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing zone duration hypothesis")
        
        try:
            df_features = pd.DataFrame(zones_features)
            
            if 'duration' not in df_features.columns or 'price_return' not in df_features.columns:
                raise StatisticalAnalysisError("Missing required columns: 'duration' or 'price_return'")
            
            # Определяем длинные и короткие зоны (верхние и нижние 20%)
            long_threshold = df_features['duration'].quantile(0.8)
            short_threshold = df_features['duration'].quantile(0.2)
            
            long_zones = df_features[df_features['duration'] >= long_threshold]
            short_zones = df_features[df_features['duration'] <= short_threshold]
            
            if len(long_zones) == 0 or len(short_zones) == 0:
                raise StatisticalAnalysisError("Insufficient data: need both long and short zones")
            
            # Выполняем t-тест
            t_stat, p_value = stats.ttest_ind(
                long_zones['price_return'].dropna(),
                short_zones['price_return'].dropna()
            )
            
            # Вычисляем размер эффекта (Cohen's d)
            pooled_std = np.sqrt(
                ((len(long_zones) - 1) * long_zones['price_return'].var() +
                 (len(short_zones) - 1) * short_zones['price_return'].var()) /
                (len(long_zones) + len(short_zones) - 2)
            )
            
            effect_size = (long_zones['price_return'].mean() - short_zones['price_return'].mean()) / pooled_std
            
            # Метаданные теста
            metadata = {
                'long_zones_count': len(long_zones),
                'short_zones_count': len(short_zones),
                'long_zones_mean_return': long_zones['price_return'].mean(),
                'short_zones_mean_return': short_zones['price_return'].mean(),
                'long_threshold': long_threshold,
                'short_threshold': short_threshold,
                'long_zones_std': long_zones['price_return'].std(),
                'short_zones_std': short_zones['price_return'].std()
            }
            
            return HypothesisTestResult(
                hypothesis="Zone duration affects price returns",
                test_type="Independent t-test",
                statistic=t_stat,
                p_value=p_value,
                significant=p_value < self.alpha,
                alpha=self.alpha,
                effect_size=effect_size,
                sample_size=len(long_zones) + len(short_zones),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Zone duration hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Zone duration test failed: {e}")
    
    def test_histogram_slope_hypothesis(self, zones_features: List[Dict[str, Any]]) -> HypothesisTestResult:
        """
        Тест гипотезы о корреляции между наклоном гистограммы MACD и длительностью зоны.
        
        H0: Наклон гистограммы не коррелирует с длительностью зоны
        H1: Существует значимая корреляция
        
        Args:
            zones_features: Список словарей с характеристиками зон
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing histogram slope hypothesis")
        
        try:
            df_features = pd.DataFrame(zones_features)
            
            required_cols = ['oscillator_slope', 'duration']
            missing_cols = [col for col in required_cols if col not in df_features.columns]
            if missing_cols:
                raise StatisticalAnalysisError(f"Missing required columns: {missing_cols}")
            
            # Убираем NaN значения
            clean_data = df_features[['oscillator_slope', 'duration']].dropna()
            
            if len(clean_data) < 3:
                raise StatisticalAnalysisError("Insufficient data for correlation test (need at least 3 points)")
            
            # Вычисляем корреляцию Пирсона
            correlation, p_value = stats.pearsonr(clean_data['oscillator_slope'], clean_data['duration'])
            
            # Вычисляем t-статистику для корреляции
            n = len(clean_data)
            t_stat = correlation * np.sqrt((n - 2) / (1 - correlation**2))
            
            # Доверительный интервал для корреляции (Fisher's z-transform)
            z = np.arctanh(correlation)
            se = 1 / np.sqrt(n - 3)
            z_ci = stats.norm.interval(1 - self.alpha, loc=z, scale=se)
            ci = (np.tanh(z_ci[0]), np.tanh(z_ci[1]))
            
            metadata = {
                'correlation': correlation,
                'sample_size': n,
                'degrees_of_freedom': n - 2,
                'oscillator_slope_mean': clean_data['oscillator_slope'].mean(),
                'oscillator_slope_std': clean_data['oscillator_slope'].std(),
                'duration_mean': clean_data['duration'].mean(),
                'duration_std': clean_data['duration'].std()
            }
            
            return HypothesisTestResult(
                hypothesis="Histogram slope correlates with zone duration",
                test_type="Pearson correlation test",
                statistic=t_stat,
                p_value=p_value,
                significant=p_value < self.alpha,
                alpha=self.alpha,
                effect_size=correlation,  # Корреляция как размер эффекта
                confidence_interval=ci,
                sample_size=n,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Histogram slope hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Histogram slope test failed: {e}")
    
    def test_contrast_asymmetry_hypothesis(self, zones_features: List[Dict[str, Any]],
                                           vocabulary: Optional[ZoneVocabulary] = None
                                           ) -> HypothesisTestResult:
        """
        Тест гипотезы об асимметрии между зонами **контрастной пары**.

        H0: Нет различий между зонами двух контрастных типов
        H1: Существуют значимые различия

        Раньше метод назывался ``test_bull_bear_asymmetry_hypothesis`` и сравнивал
        ``zone_type == 'bull'`` с ``zone_type == 'bear'``. На любом другом словаре
        обе выборки оказывались пустыми, и тест падал с сообщением «Insufficient
        data: need both bull and bear zones» — диагностика указывала на объём
        данных, хотя причина была в словаре.

        Пара берётся из объявления стратегии
        (:meth:`ZoneVocabulary.contrast_pairs`). Если объявленных пар несколько,
        тестируется каждая, а в результат идёт наиболее значимая; полный список —
        в ``metadata['pairs_tested']``.

        Args:
            zones_features: Список словарей с характеристиками зон
            vocabulary: Объявленный словарь типов зон. Без него пара выводится из
                полярностей, а если и это невозможно — тест сообщает о
                неприменимости, а не о нехватке данных.

        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing contrast asymmetry hypothesis")

        try:
            df_features = pd.DataFrame(zones_features)

            required_cols = ['zone_type', 'duration', 'price_return']
            missing_cols = [col for col in required_cols if col not in df_features.columns]
            if missing_cols:
                raise StatisticalAnalysisError(f"Missing required columns: {missing_cols}")

            observed = sorted(set(df_features['zone_type']))
            if vocabulary is None:
                vocabulary = ZoneVocabulary.coerce(observed)

            pairs = [
                (a, b) for a, b in vocabulary.contrast_pairs()
                if a in observed and b in observed
            ]
            if not pairs:
                raise StatisticalAnalysisError(
                    "No contrasting pair of zone types is available: observed types "
                    f"{observed}, declared pairs {vocabulary.contrast_pairs()}. The "
                    "test compares two opposed groups, so it needs a declared "
                    "counterpart (ZoneType.counterpart) with both types present."
                )

            results = []
            for first, second in pairs:
                first_zones = df_features[df_features['zone_type'] == first]
                second_zones = df_features[df_features['zone_type'] == second]

                if len(first_zones) < 2 or len(second_zones) < 2:
                    self.logger.debug(
                        f"Skipping pair {first}/{second}: {len(first_zones)} and "
                        f"{len(second_zones)} zones, need at least 2 of each"
                    )
                    continue

                duration_stat, duration_p = stats.ttest_ind(
                    first_zones['duration'].dropna(),
                    second_zones['duration'].dropna()
                )
                return_stat, return_p = stats.ttest_ind(
                    first_zones['price_return'].dropna(),
                    second_zones['price_return'].dropna()
                )

                # Комбинированный p-value (метод Бонферрони)
                combined_p = min(duration_p * 2, return_p * 2, 1.0)

                # Размер эффекта для длительности (Cohen's d)
                duration_pooled_std = np.sqrt(
                    ((len(first_zones) - 1) * first_zones['duration'].var() +
                     (len(second_zones) - 1) * second_zones['duration'].var()) /
                    (len(first_zones) + len(second_zones) - 2)
                )
                duration_effect = (
                    (first_zones['duration'].mean() - second_zones['duration'].mean())
                    / duration_pooled_std
                ) if duration_pooled_std else float('nan')

                results.append({
                    'pair': (first, second),
                    'combined_p': combined_p,
                    'duration_test': {
                        't_statistic': duration_stat,
                        'p_value': duration_p,
                        'significant': duration_p < self.alpha,
                        f'{first}_mean': first_zones['duration'].mean(),
                        f'{second}_mean': second_zones['duration'].mean(),
                        'effect_size': duration_effect
                    },
                    'return_test': {
                        't_statistic': return_stat,
                        'p_value': return_p,
                        'significant': return_p < self.alpha,
                        f'{first}_mean': first_zones['price_return'].mean(),
                        f'{second}_mean': second_zones['price_return'].mean()
                    },
                    'zone_counts': {first: len(first_zones), second: len(second_zones)},
                    'statistic': max(abs(duration_stat), abs(return_stat)),
                    'effect_size': duration_effect,
                    'sample_size': len(first_zones) + len(second_zones),
                })

            if not results:
                raise StatisticalAnalysisError(
                    "Every contrasting pair has fewer than two zones on one side: "
                    f"pairs {pairs}, counts "
                    f"{df_features['zone_type'].value_counts().to_dict()}"
                )

            best = min(results, key=lambda r: r['combined_p'])
            first, second = best['pair']

            metadata = {
                'pair_tested': [first, second],
                'pairs_available': [list(p) for p in pairs],
                'pairs_tested': [
                    {'pair': list(r['pair']), 'combined_p': r['combined_p']}
                    for r in results
                ],
                'duration_test': best['duration_test'],
                'return_test': best['return_test'],
                'zone_counts': best['zone_counts'],
            }

            return HypothesisTestResult(
                hypothesis=f"Zones of type '{first}' and '{second}' are asymmetric",
                test_type="Multiple t-tests with Bonferroni correction",
                statistic=best['statistic'],
                p_value=best['combined_p'],
                significant=best['combined_p'] < self.alpha,
                alpha=self.alpha,
                effect_size=best['effect_size'],
                sample_size=best['sample_size'],
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"Contrast asymmetry hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Contrast asymmetry test failed: {e}")

    @staticmethod
    def _adjacent_pairs(zones_features: List[Dict[str, Any]]) -> List[tuple]:
        """Пары соседних по списку зон, которые **примыкают** во времени.

        Детекторы мостят таймлайн, но ``min_duration`` отбрасывает короткие зоны,
        и соседи отброшенной перестают примыкать. Переход между ними произошёл не
        между соседями, и считать его переходом нельзя (разбор:
        ``devref/gaps/sequence/``).

        Если границы зон недоступны (старый сохранённый артефакт), возвращаются
        все последовательные пары — прежнее поведение; вызывающий сообщает об этом
        через ``discarded_pairs == 0``.
        """
        bounds = [
            (zone.get('start_idx'), zone.get('end_idx'))
            for zone in zones_features
        ]
        if any(start is None or end is None for start, end in bounds):
            return [(i, i + 1) for i in range(len(zones_features) - 1)]
        return [
            (i, i + 1)
            for i in range(len(zones_features) - 1)
            if bounds[i + 1][0] <= bounds[i][1] + 1
        ]

    def test_sequence_hypothesis(self, zones_features: List[Dict[str, Any]],
                                 vocabulary: Optional[ZoneVocabulary] = None
                                 ) -> HypothesisTestResult:
        """
        Тест гипотезы о неслучайности последовательностей зон.
        
        H0: Последовательности зон случайны
        H1: Последовательности следуют неслучайным паттернам
        
        Args:
            zones_features: Список словарей с характеристиками зон
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing sequence hypothesis")
        
        try:
            if 'zone_type' not in zones_features[0]:
                raise StatisticalAnalysisError("Missing 'zone_type' field in zone features")
            
            # Создаем последовательность типов зон
            zone_types = [zone['zone_type'] for zone in zones_features]
            
            if len(zone_types) < 3:
                raise StatisticalAnalysisError("Need at least 3 zones for sequence analysis")
            
            if vocabulary is None:
                vocabulary = ZoneVocabulary.coerce(sorted(set(zone_types)))
            
            # Примыкание: пара зон, разделённая пропуском (например, короткой зоной,
            # отброшенной по min_duration), переходом не является — между ними было
            # то, чего в выборке нет. Границы приходят в фичах зоны; если их нет,
            # последовательность считается сплошной, и это отмечается в metadata.
            adjacent = self._adjacent_pairs(zones_features)
            
            # Подсчитываем переходы
            transitions = {}
            for i, j in adjacent:
                transition = f"{zone_types[i]}_to_{zone_types[j]}"
                transitions[transition] = transitions.get(transition, 0) + 1
            
            # Тест хи-квадрат на равномерность переходов
            observed_freq = list(transitions.values())
            
            if len(observed_freq) < 2:
                raise StatisticalAnalysisError(
                    f"Need at least 2 different transition types, got {len(observed_freq)} "
                    f"from {len(adjacent)} adjacent zone pairs"
                )
            
            # Ожидаемая частота при равномерном распределении
            total_transitions = sum(observed_freq)
            expected_freq = total_transitions / len(observed_freq)
            
            chi2_stat, chi2_p = stats.chisquare(observed_freq, [expected_freq] * len(observed_freq))
            
            # Дополнительный тест: runs test для проверки случайности.
            #
            # Бинаризация идёт по ОБЪЯВЛЕННОЙ ПОЛЯРНОСТИ типа зоны. Раньше здесь
            # стояло `1 if zone_type == 'bull' else 0`: на любом другом словаре ряд
            # выходил константным, и тест отвечал на вопрос о величине, которая не
            # меняется, — а его p-value входило в комбинированный результат.
            directional = [
                (1 if vocabulary.polarity_of(zone_type) == 1 else 0)
                for zone_type in zone_types
                if vocabulary.polarity_of(zone_type) in (-1, 1)
            ]
            
            if len(directional) >= 2 and len(set(directional)) == 2:
                runs_stat, runs_p = self._runs_test(directional)
                combined_p = min(chi2_p * 2, runs_p * 2, 1.0)
                runs_note = None
            else:
                runs_stat, runs_p = None, None
                combined_p = min(chi2_p, 1.0)
                runs_note = (
                    "runs test skipped: fewer than two directional zone types are "
                    f"present among {sorted(set(zone_types))}, so the binarised "
                    "sequence would not vary"
                )
                self.logger.debug(runs_note)
            
            metadata = {
                'transitions': transitions,
                'total_transitions': total_transitions,
                'chi2_statistic': chi2_stat,
                'chi2_p_value': chi2_p,
                'runs_statistic': runs_stat,
                'runs_p_value': runs_p,
                'runs_test_skipped': runs_note,
                'sequence_length': len(zone_types),
                'adjacent_pairs': len(adjacent),
                'discarded_pairs': len(zone_types) - 1 - len(adjacent),
                'unique_transitions': len(transitions)
            }

            return HypothesisTestResult(
                hypothesis="Zone sequences follow non-random patterns",
                test_type="Chi-square and runs tests",
                statistic=chi2_stat,
                p_value=combined_p,
                significant=combined_p < self.alpha,
                alpha=self.alpha,
                sample_size=len(zone_types),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Sequence hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Sequence test failed: {e}")
    
    def test_volatility_hypothesis(self, zones_features: List[Dict[str, Any]]) -> HypothesisTestResult:
        """
        Тест гипотезы о влиянии волатильности на характеристики зон.
        
        H0: Волатильность не влияет на характеристики зон
        H1: Существует значимая связь
        
        Args:
            zones_features: Список словарей с характеристиками зон
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing volatility hypothesis")
        
        try:
            df_features = pd.DataFrame(zones_features)
            
            # Определяем прокси волатильности
            if 'price_return_atr' in df_features.columns:
                volatility_proxy = df_features['price_return_atr']
                vol_column = 'price_return_atr'
            elif 'atr' in df_features.columns:
                volatility_proxy = df_features['atr']
                vol_column = 'atr'
            else:
                if 'price_return' not in df_features.columns:
                    raise StatisticalAnalysisError(
                        "No price_return data available for volatility proxy"
                    )

                volatility_proxy = df_features['price_return'].abs()
                vol_column = 'abs_price_return'
                df_features[vol_column] = volatility_proxy
            
            correlations = {}
            
            # Тестируем корреляции с различными характеристиками зон
            test_columns = ['duration', 'line_amplitude', 'price_return']
            available_columns = [col for col in test_columns if col in df_features.columns]
            
            if not available_columns:
                raise StatisticalAnalysisError("No suitable columns for volatility correlation test")
            
            significant_correlations = 0
            p_values = []
            
            for col in available_columns:
                clean_data = df_features[[vol_column, col]].dropna()
                
                if len(clean_data) >= 3:
                    corr, p_val = stats.pearsonr(volatility_proxy.dropna(), clean_data[col])
                    correlations[f'volatility_{col}_correlation'] = {
                        'correlation': corr,
                        'p_value': p_val,
                        'significant': p_val < self.alpha,
                        'sample_size': len(clean_data)
                    }
                    
                    if p_val < self.alpha:
                        significant_correlations += 1
                    p_values.append(p_val)
            
            # Объединенный тест: корректировка для множественных сравнений (Holm-Bonferroni)
            if p_values:
                from statsmodels.stats.multitest import multipletests
                corrected_p = multipletests(p_values, alpha=self.alpha, method='holm')[1]
                combined_p = min(corrected_p) if corrected_p.size > 0 else 1.0
            else:
                combined_p = 1.0
            
            # Суммарная статистика
            avg_correlation = np.mean([corr_data['correlation'] for corr_data in correlations.values()])
            
            metadata = {
                'volatility_proxy': vol_column,
                'correlations': correlations,
                'significant_correlations': significant_correlations,
                'total_correlations_tested': len(available_columns),
                'volatility_mean': volatility_proxy.mean(),
                'volatility_std': volatility_proxy.std(),
                'individual_p_values': p_values
            }
            
            return HypothesisTestResult(
                hypothesis="Volatility affects zone characteristics",
                test_type="Multiple correlation tests with Holm-Bonferroni correction",
                statistic=avg_correlation,
                p_value=combined_p,
                significant=combined_p < self.alpha,
                alpha=self.alpha,
                effect_size=avg_correlation,
                sample_size=len(df_features),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Volatility hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Volatility test failed: {e}")
    
    def test_correlation_drawdown_hypothesis(self, zones_features: List[Dict[str, Any]],
                                             vocabulary: Optional[ZoneVocabulary] = None
                                             ) -> HypothesisTestResult:
        """
        Тест гипотезы о влиянии корреляции цены-MACD на просадку.
        
        H0: Корреляция цены и MACD не влияет на просадку
        H1: Высокая корреляция → меньшая просадка
        
        Args:
            zones_features: Список словарей с характеристиками зон
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing correlation-drawdown hypothesis")
        
        try:
            df_features = pd.DataFrame(zones_features)
            
            required_cols = ['correlation_price_oscillator', 'zone_type']
            missing_cols = [col for col in required_cols if col not in df_features.columns]
            if missing_cols:
                raise StatisticalAnalysisError(f"Missing required columns: {missing_cols}")
            
            observed = sorted(set(df_features['zone_type']))
            if vocabulary is None:
                vocabulary = ZoneVocabulary.coerce(observed)
            
            # Какая из двух экскурсий содержательна, решает ОБЪЯВЛЕННАЯ ПОЛЯРНОСТЬ
            # типа зоны, а не его имя: у приподнятой зоны говорящая величина —
            # просадка от максимума, у подавленной — отскок от минимума. Раньше
            # выборки набирались по `zone_type == 'bull'` / `== 'bear'`, поэтому на
            # любом другом словаре обе оказывались пустыми, и тест падал с
            # сообщением про нехватку данных («got 0 zones» на прогоне из 18) —
            # диагностика винила объём, хотя причина была в словаре.
            excursion_by_polarity = {1: 'drawdown_from_peak', -1: 'rally_from_trough'}
            
            missing_metrics = [
                column for column in excursion_by_polarity.values()
                if column not in df_features.columns
            ]
            if missing_metrics:
                raise StatisticalAnalysisError(
                    f"Missing excursion metrics {missing_metrics}; they are computed "
                    "for every zone, so their absence means the features were built "
                    "by an older version"
                )
            
            combined_data = []
            used_types = {}
            
            for zone_type in observed:
                polarity = vocabulary.polarity_of(zone_type)
                column = excursion_by_polarity.get(polarity)
                if column is None:
                    continue
                
                subset = df_features[df_features['zone_type'] == zone_type]
                clean = subset[['correlation_price_oscillator', column]].dropna()
                used_types[zone_type] = len(clean)
                
                for _, row in clean.iterrows():
                    combined_data.append({
                        'correlation': row['correlation_price_oscillator'],
                        # abs() приводит обе экскурсии к одной шкале: просадка
                        # отрицательна, отскок положителен, а сравнивается величина.
                        'drawdown': abs(row[column])
                    })
            
            if not used_types:
                raise StatisticalAnalysisError(
                    "No zone type declares a polarity, so neither excursion metric "
                    f"is meaningful here; observed types: {observed}. Declare "
                    "ZoneType.polarity on the detection strategy to enable this test."
                )
            
            if len(combined_data) < 10:
                raise StatisticalAnalysisError(
                    f"Insufficient data for correlation-drawdown test (need at least "
                    f"10 zones, got {len(combined_data)} usable of {len(df_features)}; "
                    f"per type: {used_types})"
                )
            
            df_combined = pd.DataFrame(combined_data)
            
            # Разделяем на high_corr (>0.7) и low_corr (<0.3)
            high_corr = df_combined[df_combined['correlation'] > 0.7]
            low_corr = df_combined[df_combined['correlation'] < 0.3]
            
            if len(high_corr) == 0 or len(low_corr) == 0:
                # Альтернативный подход: верхние и нижние 20%
                high_threshold = df_combined['correlation'].quantile(0.8)
                low_threshold = df_combined['correlation'].quantile(0.2)
                high_corr = df_combined[df_combined['correlation'] >= high_threshold]
                low_corr = df_combined[df_combined['correlation'] <= low_threshold]
            
            if len(high_corr) == 0 or len(low_corr) == 0:
                raise StatisticalAnalysisError("Cannot separate high and low correlation groups")
            
            # T-test: сравниваем средние drawdown
            t_stat, p_value = stats.ttest_ind(
                high_corr['drawdown'],
                low_corr['drawdown']
            )
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(
                ((len(high_corr) - 1) * high_corr['drawdown'].var() +
                 (len(low_corr) - 1) * low_corr['drawdown'].var()) /
                (len(high_corr) + len(low_corr) - 2)
            )
            
            effect_size = (high_corr['drawdown'].mean() - low_corr['drawdown'].mean()) / pooled_std if pooled_std > 0 else 0
            
            # Также рассчитываем общую корреляцию между correlation и drawdown
            overall_corr, overall_p = stats.pearsonr(
                df_combined['correlation'],
                df_combined['drawdown']
            )
            
            metadata = {
                'high_corr_count': len(high_corr),
                'low_corr_count': len(low_corr),
                'high_corr_mean_drawdown': high_corr['drawdown'].mean(),
                'low_corr_mean_drawdown': low_corr['drawdown'].mean(),
                'high_corr_std_drawdown': high_corr['drawdown'].std(),
                'low_corr_std_drawdown': low_corr['drawdown'].std(),
                'high_corr_threshold': high_corr['correlation'].min(),
                'low_corr_threshold': low_corr['correlation'].max(),
                'overall_correlation': overall_corr,
                'overall_correlation_p': overall_p,
                # Сколько зон каждого типа реально вошло в выборку — вместо двух
                # счётчиков с захардкоженными именами, которые на любом другом
                # словаре показывали бы нули.
                'zones_used_by_type': used_types,
                'zones_used_total': len(combined_data),
                'excursion_by_polarity': {
                    str(polarity): column
                    for polarity, column in excursion_by_polarity.items()
                }
            }
            
            return HypothesisTestResult(
                hypothesis=(
                    "High correlation between price and the detection indicator "
                    "reduces the price excursion within a zone"
                ),
                test_type="Independent t-test",
                statistic=t_stat,
                p_value=p_value,
                significant=p_value < self.alpha,
                alpha=self.alpha,
                effect_size=effect_size,
                sample_size=len(high_corr) + len(low_corr),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Correlation-drawdown hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Correlation-drawdown test failed: {e}")
    
    def test_zone_duration_stationarity(self, zones_features: List[Dict[str, Any]]) -> HypothesisTestResult:
        """
        Augmented Dickey-Fuller тест для проверки стационарности длительности зон.
        
        H0: Ряд длительностей нестационарный (среднее меняется во времени)
        H1: Ряд стационарный (среднее постоянно)
        
        Args:
            zones_features: Список словарей с характеристиками зон (в хронологическом порядке)
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing zone duration stationarity (ADF)")
        
        try:
            from statsmodels.tsa.stattools import adfuller
            
            df_features = pd.DataFrame(zones_features)
            
            if 'duration' not in df_features.columns:
                raise StatisticalAnalysisError("Missing 'duration' column")
            
            # Извлекаем временной ряд длительностей
            durations = df_features['duration'].dropna().values
            
            if len(durations) < 10:
                raise StatisticalAnalysisError(
                    f"Insufficient data for ADF test (need at least 10 zones, got {len(durations)})"
                )
            
            # Применяем ADF тест
            adf_result = adfuller(durations, autolag='AIC')
            
            # Результаты теста
            adf_statistic = adf_result[0]
            adf_p_value = adf_result[1]
            adf_usedlag = adf_result[2]
            adf_nobs = adf_result[3]
            critical_values = adf_result[4]
            
            # Определяем stationarity
            is_stationary = adf_p_value < self.alpha
            
            # Дополнительный анализ: тренд во времени
            time_indices = np.arange(len(durations))
            trend_corr, trend_p = stats.pearsonr(time_indices, durations)
            
            # Доверительный интервал для ADF statistic (не стандартный, но информативный)
            ci_1pct = critical_values.get('1%', None)
            ci_5pct = critical_values.get('5%', None)
            ci_10pct = critical_values.get('10%', None)
            
            metadata = {
                'adf_statistic': adf_statistic,
                'adf_p_value': adf_p_value,
                'adf_usedlag': adf_usedlag,
                'adf_nobs': adf_nobs,
                'critical_values': critical_values,
                'is_stationary': is_stationary,
                'trend_correlation': trend_corr,
                'trend_p_value': trend_p,
                'has_trend': abs(trend_corr) > 0.3 and trend_p < 0.05,
                'mean_duration': float(np.mean(durations)),
                'std_duration': float(np.std(durations)),
                'min_duration': int(np.min(durations)),
                'max_duration': int(np.max(durations)),
                'interpretation': (
                    'Stationary: mean duration is stable over time' if is_stationary 
                    else 'Non-stationary: mean duration changes over time'
                )
            }
            
            return HypothesisTestResult(
                hypothesis="Zone duration time series is stationary",
                test_type="Augmented Dickey-Fuller (ADF) test",
                statistic=adf_statistic,
                p_value=adf_p_value,
                significant=is_stationary,  # Significant = reject H0 = stationary
                alpha=self.alpha,
                effect_size=trend_corr,  # Trend correlation as effect size
                sample_size=len(durations),
                confidence_interval=(ci_1pct, ci_10pct) if ci_1pct and ci_10pct else None,
                metadata=metadata
            )
            
        except ImportError:
            self.logger.error("statsmodels not installed, cannot perform ADF test")
            raise StatisticalAnalysisError(
                "ADF test requires statsmodels package. Install with: pip install statsmodels"
            )
        except Exception as e:
            self.logger.error(f"Zone duration stationarity test failed: {e}")
            raise StatisticalAnalysisError(f"ADF test failed: {e}")
    
    def test_support_resistance_hypothesis(self, 
                                          zones_features: List[Dict[str, Any]],
                                          price_levels: Optional[List[float]] = None,
                                          tolerance_pct: float = 0.5) -> HypothesisTestResult:
        """
        Тест гипотезы о влиянии уровней поддержки/сопротивления на длительность зон.
        
        H0: Близость к уровням не влияет на длительность зоны
        H1: Зоны, начинающиеся у уровней, имеют другую длительность
        
        Args:
            zones_features: Список словарей с характеристиками зон
            price_levels: Список идентифицированных уровней поддержки/сопротивления.
                         Если None, уровни будут определены автоматически.
            tolerance_pct: Допуск для определения близости к уровню (% от цены)
        
        Returns:
            HypothesisTestResult с результатами теста
        """
        self.logger.info("Testing support/resistance hypothesis")
        
        try:
            df_features = pd.DataFrame(zones_features)
            
            required_cols = ['start_price', 'duration']
            missing_cols = [col for col in required_cols if col not in df_features.columns]
            if missing_cols:
                raise StatisticalAnalysisError(f"Missing required columns: {missing_cols}")
            
            # Если уровни не предоставлены, идентифицируем их автоматически
            if price_levels is None:
                price_levels = self._identify_price_levels(df_features)
                self.logger.info(f"Auto-identified {len(price_levels)} price levels")
            
            if len(price_levels) == 0:
                raise StatisticalAnalysisError("No price levels provided or identified")
            
            # Для каждой зоны определяем близость к уровню
            near_level_mask = []
            for _, zone in df_features.iterrows():
                start_price = zone['start_price']
                is_near = self._is_near_level(start_price, price_levels, tolerance_pct)
                near_level_mask.append(is_near)
            
            df_features['near_level'] = near_level_mask
            
            # Разделяем зоны
            near_level = df_features[df_features['near_level'] == True]
            far_from_level = df_features[df_features['near_level'] == False]
            
            if len(near_level) == 0 or len(far_from_level) == 0:
                raise StatisticalAnalysisError(
                    f"Cannot separate zones by proximity to levels "
                    f"(near: {len(near_level)}, far: {len(far_from_level)})"
                )
            
            # Проверяем нормальность распределения (для выбора теста)
            from scipy.stats import shapiro
            
            near_durations = near_level['duration'].dropna()
            far_durations = far_from_level['duration'].dropna()
            
            # Shapiro-Wilk test для нормальности (если достаточно данных)
            use_parametric = True
            if len(near_durations) >= 3 and len(far_durations) >= 3:
                _, p_near = shapiro(near_durations)
                _, p_far = shapiro(far_durations)
                # Если хотя бы одна группа не нормальна, используем непараметрический тест
                if p_near < 0.05 or p_far < 0.05:
                    use_parametric = False
            
            # Выбираем тест
            if use_parametric:
                # Параметрический t-test
                t_stat, p_value = stats.ttest_ind(near_durations, far_durations)
                test_used = "Independent t-test"
            else:
                # Непараметрический Mann-Whitney U test
                u_stat, p_value = stats.mannwhitneyu(near_durations, far_durations, alternative='two-sided')
                t_stat = u_stat
                test_used = "Mann-Whitney U test"
            
            # Effect size (Cohen's d для t-test, rank-biserial для Mann-Whitney)
            if use_parametric:
                pooled_std = np.sqrt(
                    ((len(near_durations) - 1) * near_durations.var() +
                     (len(far_durations) - 1) * far_durations.var()) /
                    (len(near_durations) + len(far_durations) - 2)
                )
                effect_size = (near_durations.mean() - far_durations.mean()) / pooled_std if pooled_std > 0 else 0
            else:
                # Rank-biserial correlation для Mann-Whitney
                n1, n2 = len(near_durations), len(far_durations)
                effect_size = 1 - (2 * t_stat) / (n1 * n2)
            
            # Метаданные
            metadata = {
                'near_level_count': len(near_level),
                'far_from_level_count': len(far_from_level),
                'near_level_mean_duration': near_durations.mean(),
                'far_from_level_mean_duration': far_durations.mean(),
                'near_level_std_duration': near_durations.std(),
                'far_from_level_std_duration': far_durations.std(),
                'near_level_median_duration': near_durations.median(),
                'far_from_level_median_duration': far_durations.median(),
                'price_levels_count': len(price_levels),
                'price_levels': price_levels,
                'tolerance_pct': tolerance_pct,
                'test_used': test_used,
                'is_parametric': use_parametric,
                'duration_difference': near_durations.mean() - far_durations.mean(),
                'duration_difference_pct': (
                    (near_durations.mean() - far_durations.mean()) / far_durations.mean() * 100
                    if far_durations.mean() > 0 else 0
                )
            }
            
            return HypothesisTestResult(
                hypothesis="Zones starting near support/resistance levels have different duration",
                test_type=test_used,
                statistic=t_stat,
                p_value=p_value,
                significant=p_value < self.alpha,
                alpha=self.alpha,
                effect_size=effect_size,
                sample_size=len(near_durations) + len(far_durations),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Support/resistance hypothesis test failed: {e}")
            raise StatisticalAnalysisError(f"Support/resistance test failed: {e}")
    
    def _identify_price_levels(self, df_features: pd.DataFrame, 
                               min_touches: int = 2,
                               cluster_tolerance_pct: float = 1.0) -> List[float]:
        """
        Идентифицирует уровни поддержки/сопротивления на основе start_price и end_price зон.
        
        Args:
            df_features: DataFrame с характеристиками зон
            min_touches: Минимальное количество касаний для идентификации уровня
            cluster_tolerance_pct: Допуск для кластеризации близких уровней (%)
        
        Returns:
            Список идентифицированных ценовых уровней
        """
        # Собираем все ценовые точки (начало и конец зон)
        prices = []
        
        if 'start_price' in df_features.columns:
            prices.extend(df_features['start_price'].dropna().tolist())
        
        if 'end_price' in df_features.columns:
            prices.extend(df_features['end_price'].dropna().tolist())
        
        if len(prices) < min_touches:
            return []
        
        prices = np.array(sorted(prices))
        
        # Кластеризуем близкие цены
        levels = []
        current_cluster = [prices[0]]
        
        for price in prices[1:]:
            # Проверяем близость к текущему кластеру
            cluster_mean = np.mean(current_cluster)
            tolerance = cluster_mean * (cluster_tolerance_pct / 100)
            
            if abs(price - cluster_mean) <= tolerance:
                current_cluster.append(price)
            else:
                # Завершаем текущий кластер если достаточно касаний
                if len(current_cluster) >= min_touches:
                    levels.append(np.mean(current_cluster))
                # Начинаем новый кластер
                current_cluster = [price]
        
        # Обрабатываем последний кластер
        if len(current_cluster) >= min_touches:
            levels.append(np.mean(current_cluster))
        
        return levels
    
    def _is_near_level(self, price: float, levels: List[float], tolerance_pct: float) -> bool:
        """
        Проверяет, находится ли цена вблизи какого-либо уровня.
        
        Args:
            price: Проверяемая цена
            levels: Список уровней
            tolerance_pct: Допуск в процентах
        
        Returns:
            True если цена близка к уровню, False иначе
        """
        for level in levels:
            tolerance = level * (tolerance_pct / 100)
            if abs(price - level) <= tolerance:
                return True
        return False
    
    def _runs_test(self, binary_sequence: List[int]) -> tuple:
        """
        Runs test для проверки случайности бинарной последовательности.
        
        Args:
            binary_sequence: Последовательность из 0 и 1
        
        Returns:
            Tuple (z_statistic, p_value)
        """
        n = len(binary_sequence)
        n1 = sum(binary_sequence)
        n0 = n - n1
        
        if n1 == 0 or n0 == 0:
            return 0.0, 1.0
        
        # Подсчет runs (серий)
        runs = 1
        for i in range(1, n):
            if binary_sequence[i] != binary_sequence[i-1]:
                runs += 1
        
        # Ожидаемое количество runs
        expected_runs = (2 * n1 * n0) / n + 1
        
        # Дисперсия
        variance = (2 * n1 * n0 * (2 * n1 * n0 - n)) / (n**2 * (n - 1))
        
        if variance <= 0:
            return 0.0, 1.0
        
        # Z-статистика
        z = (runs - expected_runs) / np.sqrt(variance)
        
        # p-value (двусторонний тест)
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        return z, p_value
    
    def run_all_tests(self, zones_features: List[Dict[str, Any]],
                      vocabulary: Optional[ZoneVocabulary] = None) -> AnalysisResult:
        """
        Выполнить все тесты гипотез.
        
        Args:
            zones_features: Список словарей с характеристиками зон
            vocabulary: Объявленный словарь типов зон — нужен тестам, которые
                опираются на направление или на контрастную пару. Без него они
                сообщат о неприменимости, а не выдадут число.
        
        Returns:
            AnalysisResult с результатами всех тестов
        """
        self.logger.info("Running all hypothesis tests")
        
        if not zones_features:
            raise StatisticalAnalysisError("No zone features provided")
        
        tests = {}
        
        # Выполняем все тесты. Тесты, которым нужен словарь типов зон, получают
        # его явно — остальные о нём не знают и знать не должны.
        test_methods = [
            ('zone_duration', self.test_zone_duration_hypothesis, False),
            ('histogram_slope', self.test_histogram_slope_hypothesis, False),
            ('contrast_asymmetry', self.test_contrast_asymmetry_hypothesis, True),
            ('sequence_patterns', self.test_sequence_hypothesis, True),
            ('volatility_effects', self.test_volatility_hypothesis, False),
            ('correlation_drawdown', self.test_correlation_drawdown_hypothesis, True),
            ('duration_stationarity', self.test_zone_duration_stationarity, False)
        ]
        
        for test_name, test_method, needs_vocabulary in test_methods:
            try:
                if needs_vocabulary:
                    result = test_method(zones_features, vocabulary=vocabulary)
                else:
                    result = test_method(zones_features)
                tests[test_name] = result.to_dict()
            except Exception as e:
                self.logger.warning(f"Test {test_name} failed: {e}")
                tests[test_name] = {
                    'error': str(e),
                    'test_type': test_name,
                    'significant': False
                }
        
        # Тест, который не выполнился, не является незначимым результатом — он не
        # является результатом вовсе. Раньше такие тесты попадали в знаменатель
        # `significance_rate` наравне с выполненными, разбавляя её: на пороговом
        # прогоне два теста падали из-за словаря, а сводка показывала 3/7 = 0.429,
        # ничего не сообщая о том, что два из семи не считались.
        executed = {name: r for name, r in tests.items() if 'error' not in r}
        failed = {name: r['error'] for name, r in tests.items() if 'error' in r}
        
        significant_count = sum(1 for test_result in executed.values() 
                              if test_result.get('significant', False))
        
        if failed:
            self.logger.info(
                "%d of %d hypothesis tests did not run: %s",
                len(failed), len(tests), ', '.join(sorted(failed))
            )
        
        # Сводка
        summary = {
            'total_tests': len(tests),
            'tests_executed': len(executed),
            'tests_failed': len(failed),
            'failed_tests': failed,
            'significant_tests': significant_count,
            'significance_rate': significant_count / len(executed) if executed else 0,
            'alpha_level': self.alpha,
            'total_zones': len(zones_features)
        }
        
        results = {
            'tests': tests,
            'summary': summary
        }
        
        metadata = {
            'analyzer': 'HypothesisTestSuite',
            'alpha': self.alpha,
            'timestamp': datetime.now().isoformat()
        }
        
        return AnalysisResult(
            analysis_type='hypothesis_testing',
            results=results,
            data_size=len(zones_features),
            metadata=metadata
        )


# Удобные функции для быстрого использования
def run_all_hypothesis_tests(zones_features: List[Dict[str, Any]], alpha: float = 0.05,
                             vocabulary: Optional[ZoneVocabulary] = None) -> Dict[str, Any]:
    """
    Выполнить все тесты гипотез (совместимость с оригинальным API).
    
    Args:
        zones_features: Список словарей с характеристиками зон
        alpha: Уровень значимости
        vocabulary: Объявленный словарь типов зон. Тесты, опирающиеся на
            направление или контрастную пару, без него сообщат о неприменимости —
            вывести эти свойства из имён нельзя, и попытка была бы тем самым
            хардкодом, ради снятия которого словарь и заведён.
    
    Returns:
        Словарь с результатами всех тестов
    """
    test_suite = HypothesisTestSuite(alpha=alpha)
    analysis_result = test_suite.run_all_tests(zones_features, vocabulary=vocabulary)
    return analysis_result.results


def run_single_hypothesis_test(zones_features: List[Dict[str, Any]], 
                          test_type: str, 
                          alpha: float = 0.05,
                          price_levels: Optional[List[float]] = None,
                          tolerance_pct: float = 0.5,
                          vocabulary: Optional[ZoneVocabulary] = None) -> HypothesisTestResult:
    """
    Выполнить один конкретный тест гипотезы.
    
    Args:
        zones_features: Список словарей с характеристиками зон
        test_type: Тип теста ('duration', 'slope', 'asymmetry', 'sequence', 'volatility',
                   'correlation_drawdown', 'stationarity', 'support_resistance')
        alpha: Уровень значимости
        price_levels: Список уровней для теста 'support_resistance' (опционально)
        tolerance_pct: Допуск для теста 'support_resistance' (% от цены)
        vocabulary: Объявленный словарь типов зон — нужен тестам 'asymmetry',
            'sequence' и 'correlation_drawdown'
    
    Returns:
        HypothesisTestResult с результатами теста
    """
    test_suite = HypothesisTestSuite(alpha=alpha)
    
    # Special handling for support_resistance test (requires additional parameters)
    if test_type == 'support_resistance':
        return test_suite.test_support_resistance_hypothesis(
            zones_features,
            price_levels=price_levels,
            tolerance_pct=tolerance_pct
        )
    
    test_mapping = {
        'duration': (test_suite.test_zone_duration_hypothesis, False),
        'slope': (test_suite.test_histogram_slope_hypothesis, False),
        'asymmetry': (test_suite.test_contrast_asymmetry_hypothesis, True),
        'sequence': (test_suite.test_sequence_hypothesis, True),
        'volatility': (test_suite.test_volatility_hypothesis, False),
        'correlation_drawdown': (test_suite.test_correlation_drawdown_hypothesis, True),
        'stationarity': (test_suite.test_zone_duration_stationarity, False)
    }
    
    if test_type not in test_mapping:
        raise ValueError(f"Unknown test type: {test_type}. Available: {list(test_mapping.keys()) + ['support_resistance']}")
    
    test_method, needs_vocabulary = test_mapping[test_type]
    if needs_vocabulary:
        return test_method(zones_features, vocabulary=vocabulary)
    return test_method(zones_features)


# Экспорт
__all__ = [
    'HypothesisTestResult',
    'HypothesisTestSuite',
    'run_all_hypothesis_tests',
    'run_single_hypothesis_test'
]
