"""
Модуль анализа последовательностей зон BQuant

Адаптировано из scripts/research/macd_analysis.py с улучшениями для новой архитектуры.
Предоставляет функции для анализа переходов между зонами и кластеризации.
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass

from ...core.logging_config import get_logger
from ...core.exceptions import AnalysisError
from .. import AnalysisResult, BaseAnalyzer
from .zone_features import ZoneFeatures
from .models import ZoneVocabulary

# Получаем логгер для модуля
logger = get_logger(__name__)


@dataclass
class TransitionAnalysis:
    """
    Результат анализа переходов между зонами.
    
    Attributes:
        transition_type: Тип перехода (e.g., 'bull_to_bear')
        count: Количество таких переходов
        probability: Вероятность такого перехода
        avg_duration_before: Средняя длительность предыдущей зоны
        avg_duration_after: Средняя длительность следующей зоны
        avg_return_before: Средняя доходность предыдущей зоны
        avg_return_after: Средняя доходность следующей зоны
        metadata: Дополнительные метаданные
    """
    transition_type: str
    count: int
    probability: float
    avg_duration_before: Optional[float] = None
    avg_duration_after: Optional[float] = None
    avg_return_before: Optional[float] = None
    avg_return_after: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ClusterAnalysis:
    """
    Результат кластеризации зон.
    
    Attributes:
        cluster_id: ID кластера
        size: Количество зон в кластере
        centroid: Центроид кластера (средние значения признаков)
        characteristics: Основные характеристики кластера
        dominant_type: Преобладающий тип зон в кластере
        avg_duration: Средняя длительность зон в кластере
        avg_return: Средняя доходность зон в кластере
        metadata: Дополнительные метаданные
    """
    cluster_id: int
    size: int
    centroid: Dict[str, float]
    characteristics: Dict[str, Any]
    dominant_type: str
    avg_duration: float
    avg_return: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}



def _polarity_ratio(cluster_data: pd.DataFrame, vocabulary: ZoneVocabulary,
                    polarity: int) -> float:
    """Доля зон кластера, чей тип объявлен с данной полярностью."""
    if 'zone_type' not in cluster_data.columns or cluster_data.empty:
        return 0.0
    matching = cluster_data['zone_type'].map(
        lambda name: vocabulary.polarity_of(name) == polarity
    )
    return float(matching.mean())

class ZoneSequenceAnalyzer(BaseAnalyzer):
    """
    Анализатор последовательностей торговых зон.
    
    Предоставляет методы для:
    - Анализа переходов между зонами
    - Вычисления вероятностей переходов
    - Кластеризации зон по форме и характеристикам
    - Выявления паттернов в последовательностях
    """
    
    def __init__(self, min_sequence_length: int = 3,
                 vocabulary: Optional[ZoneVocabulary] = None):
        """
        Инициализация анализатора.
        
        Args:
            min_sequence_length: Минимальная длина последовательности для анализа
            vocabulary: Объявленный словарь типов зон. Нужен там, где анализ
                опирается на **направление** (runs-test бинаризует
                последовательность). Раньше направление определялось сравнением
                имени с литералом ``'bull'``, из-за чего любой другой словарь
                давал константный ряд. Если словарь не передан, он выводится из
                зон при вызове :meth:`analyze_zone_transitions`; если и там нет —
                собирается голый по встреченным именам, и направленные тесты
                честно сообщают о неприменимости.
        """
        super().__init__("ZoneSequenceAnalyzer")
        self.min_sequence_length = min_sequence_length
        self.vocabulary = vocabulary
        self.logger = get_logger(f"{__name__}.ZoneSequenceAnalyzer")
        
        self.logger.info(f"Initialized zone sequence analyzer with min_sequence_length={min_sequence_length}")
    
    def analyze_zone_transitions(self, zones_features: List[Union[ZoneFeatures, Dict[str, Any]]],
                                 vocabulary: Optional[ZoneVocabulary] = None) -> AnalysisResult:
        """
        Анализ переходов между зонами.
        
        Args:
            zones_features: Список объектов ZoneFeatures или словарей
            vocabulary: Объявленный словарь типов зон. Если не передан, берётся
                переданный в конструктор, иначе собирается голый по встреченным
                именам — тогда переходы и матрица считаются, а направленные тесты
                сообщают о неприменимости вместо того, чтобы угадывать.
        
        Returns:
            AnalysisResult с анализом переходов
        """
        try:
            self.logger.info(f"Analyzing transitions for {len(zones_features)} zones")
            
            if len(zones_features) < self.min_sequence_length:
                raise AnalysisError(f"Need at least {self.min_sequence_length} zones for sequence analysis")
            
            # Конвертируем в DataFrame
            features_dicts = []
            for zone in zones_features:
                if isinstance(zone, ZoneFeatures):
                    features_dicts.append(zone.to_dict())
                elif isinstance(zone, dict):
                    features_dicts.append(zone)
                else:
                    raise AnalysisError(f"Invalid zone features type: {type(zone)}")
            
            df_features = pd.DataFrame(features_dicts)
            
            # Создаем последовательность типов зон
            zone_sequence = df_features['zone_type'].tolist()
            
            # Словарь типов: аргумент → конструктор → голый по наблюдённым именам
            if vocabulary is None:
                vocabulary = self.vocabulary
            if vocabulary is None:
                vocabulary = ZoneVocabulary.coerce(sorted(set(zone_sequence)))
                self.logger.debug(
                    "No declared zone vocabulary supplied; falling back to the "
                    "observed names without properties. Directional tests will "
                    "report themselves as not applicable."
                )
            
            # Примыкание проверяется, а не предполагается: пара зон, разделённая
            # пропуском, переходом не является (см. _contiguous_segments).
            segments = self._contiguous_segments(df_features)
            adjacency = self._adjacency_summary(df_features, segments)
            
            # Анализируем переходы
            transitions = self._calculate_transitions(df_features, segments)
            transition_probabilities = self._calculate_transition_probabilities(transitions)
            transition_details = self._analyze_transition_details(df_features, transitions, segments)
            
            # Анализ паттернов
            patterns = self._find_sequence_patterns(zone_sequence, segments)
            
            # Статистические тесты
            randomness_tests = self._test_sequence_randomness(zone_sequence, segments, vocabulary)
            
            # Марковский анализ
            markov_analysis = self._markov_chain_analysis(zone_sequence, segments)
            
            if adjacency['discarded_transitions']:
                self.logger.info(
                    "%d of %d consecutive zone pairs are separated by a gap "
                    "(%d bars missing, typically zones dropped by min_duration) and "
                    "are not counted as transitions.",
                    adjacency['discarded_transitions'],
                    len(zone_sequence) - 1,
                    adjacency['bars_missing'],
                )
            
            results = {
                'sequence_summary': {
                    'total_zones': len(zone_sequence),
                    'total_transitions': adjacency['adjacent_transitions'],
                    'unique_transition_types': len(transitions),
                    'sequence_length': len(zone_sequence),
                    'zone_types_observed': sorted(set(zone_sequence)),
                    'vocabulary_declared': vocabulary.is_declared,
                    **adjacency,
                },
                'transitions': transitions,
                'transition_probabilities': transition_probabilities,
                'transition_details': transition_details,
                'patterns': patterns,
                'randomness_tests': randomness_tests,
                'markov_analysis': markov_analysis
            }
            
            metadata = {
                'analyzer': 'ZoneSequenceAnalyzer',
                'analysis_method': 'zone_transitions',
                'min_sequence_length': self.min_sequence_length,
                'timestamp': datetime.now().isoformat()
            }
            
            return AnalysisResult(
                analysis_type='zone_transitions',
                results=results,
                data_size=len(zones_features),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Zone transitions analysis failed: {e}")
            raise AnalysisError(f"Zone transitions analysis failed: {e}")
    
    def cluster_zones(self, zones_features: List[Union[ZoneFeatures, Dict[str, Any]]], 
                     n_clusters: int = 3, 
                     features_to_use: Optional[List[str]] = None,
                     vocabulary: Optional[ZoneVocabulary] = None) -> AnalysisResult:
        """
        Кластеризация зон по характеристикам.
        
        Args:
            zones_features: Список объектов ZoneFeatures или словарей
            n_clusters: Количество кластеров
            features_to_use: Список признаков для кластеризации (если None, используются по умолчанию)
        
        Returns:
            AnalysisResult с результатами кластеризации
        """
        try:
            self.logger.info(f"Clustering {len(zones_features)} zones into {n_clusters} clusters")
            
            if len(zones_features) < n_clusters:
                raise AnalysisError(f"Cannot create {n_clusters} clusters from {len(zones_features)} zones")
            
            # Конвертируем в DataFrame
            features_dicts = []
            for zone in zones_features:
                if isinstance(zone, ZoneFeatures):
                    features_dicts.append(zone.to_dict())
                elif isinstance(zone, dict):
                    features_dicts.append(zone)
            
            df_features = pd.DataFrame(features_dicts)
            
            # Выбираем признаки для кластеризации
            if features_to_use is None:
                features_to_use = [
                    'duration', 'line_amplitude', 'oscillator_amplitude', 
                    'price_range_pct', 'correlation_price_oscillator'
                ]
                # Добавляем дополнительные признаки если они доступны
                if 'num_peaks' in df_features.columns:
                    features_to_use.append('num_peaks')
                if 'num_troughs' in df_features.columns:
                    features_to_use.append('num_troughs')
            
            # Проверяем доступность признаков
            available_features = [f for f in features_to_use if f in df_features.columns]
            if not available_features:
                raise AnalysisError("No clustering features available in data")
            
            self.logger.info(f"Using features for clustering: {available_features}")
            
            # Подготавливаем данные для кластеризации
            clustering_data = df_features[available_features].fillna(0)
            
            # Нормализация признаков
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(clustering_data)
            
            # Кластеризация
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Добавляем метки кластеров
            df_features['cluster'] = cluster_labels
            
            # Анализ кластеров
            if vocabulary is None:
                vocabulary = self.vocabulary
            if vocabulary is None and 'zone_type' in df_features.columns:
                vocabulary = ZoneVocabulary.coerce(sorted(set(df_features['zone_type'])))
            
            clusters_analysis = self._analyze_clusters(
                df_features, available_features, kmeans, scaler,
                vocabulary or ZoneVocabulary()
            )
            
            # Валидация кластеризации
            clustering_quality = self._evaluate_clustering_quality(features_scaled, cluster_labels, n_clusters)
            
            results = {
                'clustering_summary': {
                    'n_clusters': n_clusters,
                    'features_used': available_features,
                    'total_zones': len(df_features),
                    'clustering_quality': clustering_quality
                },
                'cluster_labels': cluster_labels.tolist(),
                'clusters_analysis': clusters_analysis,
                'feature_importance': self._calculate_feature_importance(features_scaled, cluster_labels, available_features)
            }
            
            metadata = {
                'analyzer': 'ZoneSequenceAnalyzer',
                'analysis_method': 'zone_clustering',
                'n_clusters': n_clusters,
                'features_used': available_features,
                'timestamp': datetime.now().isoformat()
            }
            
            return AnalysisResult(
                analysis_type='zone_clustering',
                results=results,
                data_size=len(zones_features),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Zone clustering failed: {e}")
            raise AnalysisError(f"Zone clustering failed: {e}")
    
    @staticmethod
    def _contiguous_segments(df_features: pd.DataFrame) -> List[List[int]]:
        """Разбить зоны на максимальные серии **примыкающих** зон.

        Детекторы выдают зоны, мостящие таймлайн: зона ``i+1`` начинается там, где
        кончилась зона ``i``. Анализ последовательностей на этом и построен — он
        читает соседние элементы списка как переход. Но ``min_duration`` отбрасывает
        короткие зоны, и соседи отброшенной перестают примыкать: при дефолтном
        ``min_duration=2`` на встроенном сэмпле 8 из 71 «переходов» MACD-детектора
        соединяют зоны через пропуск, включая структурно невозможные ``bull → bull``
        (детектор по пересечению нуля обязан чередовать типы). Разбор:
        ``devref/gaps/sequence/``.

        Здесь примыкание проверяется по границам зон, а не предполагается. Если
        границы неизвестны (``start_idx``/``end_idx`` отсутствуют — например, фичи
        пришли из старого сохранённого артефакта), последовательность считается
        одной серией: это прежнее поведение, и оно отмечается в сводке
        ``adjacency_verified=False``, чтобы допущение было видно.

        Returns:
            Список серий; каждая — список позиций строк ``df_features`` подряд.
        """
        n = len(df_features)
        if n == 0:
            return []

        has_bounds = (
            'start_idx' in df_features.columns
            and 'end_idx' in df_features.columns
            and df_features['start_idx'].notna().all()
            and df_features['end_idx'].notna().all()
        )
        if not has_bounds:
            return [list(range(n))]

        starts = df_features['start_idx'].tolist()
        ends = df_features['end_idx'].tolist()

        segments = [[0]]
        for i in range(1, n):
            if starts[i] == ends[i - 1] + 1:
                segments[-1].append(i)
            elif starts[i] <= ends[i - 1]:
                # Overlap or reverse order. `<=` used to accept both as
                # adjacency (G57): a zone starting inside — or before — its
                # predecessor is not its neighbour, and a sequence built on
                # it is not a sequence. Tiling detectors never produce this;
                # preloaded zones and hand-built features can.
                raise ValueError(
                    f"Zones are not in tiling order: zone at position {i} starts at bar "
                    f"{starts[i]} while the previous one ends at bar {ends[i - 1]}. "
                    "Adjacent zones must satisfy start == previous end + 1; sort the "
                    "zones and remove overlaps before sequence analysis."
                )
            else:
                segments.append([i])
        return segments

    @staticmethod
    def _adjacency_summary(df_features: pd.DataFrame,
                           segments: List[List[int]]) -> Dict[str, Any]:
        """Сколько «переходов» отброшено как соединяющие непримыкающие зоны."""
        verified = (
            'start_idx' in df_features.columns
            and 'end_idx' in df_features.columns
            and df_features['start_idx'].notna().all()
            and df_features['end_idx'].notna().all()
        )
        n = len(df_features)
        counted = sum(len(seg) - 1 for seg in segments)
        summary = {
            'adjacency_verified': bool(verified),
            'contiguous_segments': len(segments),
            'segment_lengths': [len(seg) for seg in segments],
            'adjacent_transitions': counted,
            'discarded_transitions': max(n - 1, 0) - counted,
        }
        if verified and len(segments) > 1:
            starts = df_features['start_idx'].tolist()
            ends = df_features['end_idx'].tolist()
            gaps = [
                starts[seg[0]] - ends[prev[-1]] - 1
                for prev, seg in zip(segments, segments[1:])
            ]
            summary['bars_missing'] = int(sum(gaps))
            summary['gap_sizes'] = [int(g) for g in gaps]
        else:
            summary['bars_missing'] = 0
            summary['gap_sizes'] = []
        return summary

    def _calculate_transitions(self, df_features: pd.DataFrame,
                               segments: List[List[int]]) -> Dict[str, int]:
        """Подсчет переходов между **примыкающими** зонами.

        Пара, разделённая пропуском, переходом не является: между этими зонами
        было что-то, чего в выборке нет. Такие пары не считаются, а их количество
        сообщается в ``sequence_summary``.
        """
        zone_sequence = df_features['zone_type'].tolist()
        transitions = {}
        
        for segment in segments:
            for i, j in zip(segment, segment[1:]):
                transition = f"{zone_sequence[i]}_to_{zone_sequence[j]}"
                transitions[transition] = transitions.get(transition, 0) + 1
        
        return transitions
    
    def _calculate_transition_probabilities(self, transitions: Dict[str, int]) -> Dict[str, float]:
        """Вычисление вероятностей переходов."""
        total_transitions = sum(transitions.values())
        if total_transitions == 0:
            return {}
        
        return {transition: count / total_transitions 
                for transition, count in transitions.items()}
    
    def _analyze_transition_details(self, df_features: pd.DataFrame, 
                                  transitions: Dict[str, int],
                                  segments: List[List[int]]) -> Dict[str, TransitionAnalysis]:
        """Детальный анализ переходов (только между примыкающими зонами)."""
        zone_sequence = df_features['zone_type'].tolist()
        transition_details = {}
        
        # Собираем данные о переходах
        transition_data = {transition: {'before': [], 'after': []} 
                          for transition in transitions.keys()}
        
        for segment in segments:
            for i, j in zip(segment, segment[1:]):
                transition = f"{zone_sequence[i]}_to_{zone_sequence[j]}"
                
                if transition in transition_data:
                    transition_data[transition]['before'].append(i)
                    transition_data[transition]['after'].append(j)
        
        # Анализируем каждый тип перехода
        total_transitions = sum(transitions.values())
        
        for transition, count in transitions.items():
            before_indices = transition_data[transition]['before']
            after_indices = transition_data[transition]['after']
            
            avg_duration_before = None
            avg_duration_after = None
            avg_return_before = None
            avg_return_after = None
            
            if before_indices and 'duration' in df_features.columns:
                avg_duration_before = float(df_features.iloc[before_indices]['duration'].mean())
            
            if after_indices and 'duration' in df_features.columns:
                avg_duration_after = float(df_features.iloc[after_indices]['duration'].mean())
            
            if before_indices and 'price_return' in df_features.columns:
                avg_return_before = float(df_features.iloc[before_indices]['price_return'].mean())
            
            if after_indices and 'price_return' in df_features.columns:
                avg_return_after = float(df_features.iloc[after_indices]['price_return'].mean())
            
            transition_details[transition] = TransitionAnalysis(
                transition_type=transition,
                count=count,
                probability=count / total_transitions,
                avg_duration_before=avg_duration_before,
                avg_duration_after=avg_duration_after,
                avg_return_before=avg_return_before,
                avg_return_after=avg_return_after,
                metadata={
                    'before_indices': before_indices,
                    'after_indices': after_indices
                }
            )
        
        return {k: v.__dict__ for k, v in transition_details.items()}
    
    def _find_sequence_patterns(self, zone_sequence: List[str],
                                segments: List[List[int]]) -> Dict[str, Any]:
        """Поиск паттернов в последовательностях.

        Серии и триплеты считаются **внутри примыкающих отрезков**: серия из двух
        зон одного типа, разделённых пропуском, — не серия, а триплет через
        пропуск склеивает то, что рядом не стояло.
        """
        patterns = {}
        
        # Анализ длин серий
        series_lengths: Dict[str, List[int]] = {}
        
        for segment in segments:
            current_type = zone_sequence[segment[0]]
            current_length = 1
            series_lengths.setdefault(current_type, [])
            
            for position in segment[1:]:
                zone_type = zone_sequence[position]
                if zone_type == current_type:
                    current_length += 1
                else:
                    series_lengths[current_type].append(current_length)
                    current_type = zone_type
                    series_lengths.setdefault(current_type, [])
                    current_length = 1
            
            # Последняя серия отрезка
            series_lengths[current_type].append(current_length)
        
        # Статистика серий
        patterns['series_analysis'] = {}
        for zone_type, lengths in series_lengths.items():
            if lengths:
                patterns['series_analysis'][zone_type] = {
                    'avg_series_length': np.mean(lengths),
                    'max_series_length': max(lengths),
                    'min_series_length': min(lengths),
                    'total_series': len(lengths),
                    'std_series_length': np.std(lengths)
                }
        
        # Поиск триплетов (последовательности из 3 примыкающих зон)
        triplets: Dict[str, int] = {}
        for segment in segments:
            for a, b, c in zip(segment, segment[1:], segment[2:]):
                triplet = f"{zone_sequence[a]}-{zone_sequence[b]}-{zone_sequence[c]}"
                triplets[triplet] = triplets.get(triplet, 0) + 1
        
        if triplets:
            patterns['triplet_patterns'] = triplets
        
        return patterns

    def _test_sequence_randomness(self, zone_sequence: List[str],
                                  segments: List[List[int]],
                                  vocabulary: ZoneVocabulary) -> Dict[str, Any]:
        """Тестирование случайности последовательности.

        Раньше здесь стояло ``1 if zone == 'bull' else 0`` — бинаризация по имени.
        На любом другом словаре ряд получался константным, и тест отвечал на
        вопрос о величине, которая не меняется. Теперь бинаризация идёт по
        **объявленной полярности**: приподнятые зоны против подавленных.

        Кроме того, тест считается на **самом длинном примыкающем отрезке**, а не
        на всей выборке: прогон, прерванный пропуском, — не тот прогон. Если
        полярность не объявлена ни для одного встреченного типа или подходящего
        отрезка нет, возвращается ``not_applicable`` с причиной, а не число.
        """
        randomness_tests: Dict[str, Any] = {}
        
        observed = sorted(set(zone_sequence))
        directional = [t for t in observed if vocabulary.polarity_of(t) in (-1, 1)]
        
        if not directional:
            reason = (
                "no observed zone type declares a polarity, so there is no "
                f"direction to test; observed types: {observed}"
            )
            randomness_tests['runs_test'] = {'not_applicable': reason}
            randomness_tests['uniformity_test'] = {'not_applicable': reason}
            return randomness_tests
        
        longest = max(segments, key=len) if segments else []
        elevated = [
            position for position in longest
            if vocabulary.polarity_of(zone_sequence[position]) == 1
        ]
        depressed = [
            position for position in longest
            if vocabulary.polarity_of(zone_sequence[position]) == -1
        ]
        directional_positions = sorted(elevated + depressed)
        
        if len(directional_positions) < 2:
            reason = (
                "the longest contiguous run of zones holds fewer than two "
                f"directional zones ({len(directional_positions)}); the sequence is "
                "too fragmented to test"
            )
            randomness_tests['runs_test'] = {'not_applicable': reason}
        else:
            binary_sequence = [
                1 if vocabulary.polarity_of(zone_sequence[position]) == 1 else 0
                for position in directional_positions
            ]
            runs_result = self._runs_test(binary_sequence)
            runs_result['basis'] = {
                'segment_length': len(longest),
                'directional_zones_used': len(directional_positions),
                'total_zones': len(zone_sequence),
                'binarised_by': 'declared polarity (+1 vs -1)',
            }
            randomness_tests['runs_test'] = runs_result
        
        # Chi-square на равномерность — по всей выборке: он не про порядок,
        # поэтому пропуски ему не мешают.
        elevated_count = sum(1 for z in zone_sequence if vocabulary.polarity_of(z) == 1)
        depressed_count = sum(1 for z in zone_sequence if vocabulary.polarity_of(z) == -1)
        
        if elevated_count > 0 and depressed_count > 0:
            total = elevated_count + depressed_count
            expected = total / 2
            chi2_stat = ((elevated_count - expected) ** 2 / expected +
                        (depressed_count - expected) ** 2 / expected)
            chi2_p = 1 - stats.chi2.cdf(chi2_stat, df=1)
            
            randomness_tests['uniformity_test'] = {
                'chi2_statistic': chi2_stat,
                'p_value': chi2_p,
                'is_uniform': chi2_p > 0.05,
                'elevated_count': elevated_count,
                'depressed_count': depressed_count,
                'elevated_types': [t for t in observed if vocabulary.polarity_of(t) == 1],
                'depressed_types': [t for t in observed if vocabulary.polarity_of(t) == -1],
            }
        else:
            randomness_tests['uniformity_test'] = {
                'not_applicable': (
                    "only one polarity is present among the observed zones "
                    f"(elevated={elevated_count}, depressed={depressed_count}); "
                    "there is nothing to compare"
                )
            }
        
        return randomness_tests

    def _runs_test(self, binary_sequence: List[int]) -> Dict[str, Any]:
        """Runs test для проверки случайности."""
        n = len(binary_sequence)
        n1 = sum(binary_sequence)
        n0 = n - n1
        
        if n1 == 0 or n0 == 0:
            return {'error': 'All values are the same'}
        
        # Подсчет runs
        runs = 1
        for i in range(1, n):
            if binary_sequence[i] != binary_sequence[i-1]:
                runs += 1
        
        # Ожидаемое количество runs
        expected_runs = (2 * n1 * n0) / n + 1
        
        # Дисперсия
        variance = (2 * n1 * n0 * (2 * n1 * n0 - n)) / (n**2 * (n - 1))
        
        if variance <= 0:
            return {'error': 'Cannot calculate variance'}
        
        # Z-статистика
        z = (runs - expected_runs) / np.sqrt(variance)
        
        # p-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        return {
            'runs_count': runs,
            'expected_runs': expected_runs,
            'z_statistic': z,
            'p_value': p_value,
            'is_random': p_value > 0.05
        }
    
    def _markov_chain_analysis(self, zone_sequence: List[str],
                               segments: List[List[int]]) -> Dict[str, Any]:
        """Анализ последовательности как цепи Маркова.

        Две правки против прежней версии, и обе меняют ответ, а не оформление.

        **Состояния берутся из наблюдённых данных, а не из литералов.** Раньше
        здесь стояло ``states = ['bull', 'bear']`` с матрицей 2×2 и жёстким
        отображением имён в индексы. На словаре из других имён ни один переход не
        попадал в матрицу, и функция возвращала нули как успех — вместе с
        ``states: ['bull','bear']`` и стационарным распределением ``[1.0, 0.0]``,
        то есть уверенным утверждением о состоянии, ни разу не встретившемся в
        выборке. Соседний ``_calculate_transitions`` при этом считал те же данные
        верно, не зная словаря.

        **Считаются только переходы между примыкающими зонами.** Пара, разделённая
        пропуском, переходом не является.
        """
        if len(zone_sequence) < 2:
            return {'error': 'Sequence too short for Markov analysis'}
        
        states = sorted(set(zone_sequence))
        state_to_index = {state: i for i, state in enumerate(states)}
        n_states = len(states)
        transition_matrix = np.zeros((n_states, n_states))
        
        for segment in segments:
            for i, j in zip(segment, segment[1:]):
                current_idx = state_to_index[zone_sequence[i]]
                next_idx = state_to_index[zone_sequence[j]]
                transition_matrix[current_idx, next_idx] += 1
        
        observed_transitions = int(transition_matrix.sum())
        if observed_transitions == 0:
            return {
                'error': (
                    'no transitions between adjacent zones: every consecutive pair '
                    'is separated by a gap, so no transition was actually observed'
                ),
                'states': states,
            }
        
        # Нормализация для получения вероятностей
        row_sums = transition_matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # Избегаем деления на ноль
        transition_probabilities = transition_matrix / row_sums
        
        # Стационарное распределение (если цепь эргодична)
        try:
            eigenvalues, eigenvectors = np.linalg.eig(transition_probabilities.T)
            stationary_idx = np.argmax(eigenvalues.real)
            stationary_distribution = np.abs(eigenvectors[:, stationary_idx].real)
            stationary_distribution = stationary_distribution / stationary_distribution.sum()
        except Exception:
            stationary_distribution = None
        
        return {
            'transition_matrix': transition_matrix.tolist(),
            'transition_probabilities': transition_probabilities.tolist(),
            'states': states,
            'observed_transitions': observed_transitions,
            'stationary_distribution': stationary_distribution.tolist() if stationary_distribution is not None else None
        }

    def _analyze_clusters(self, df_features: pd.DataFrame, 
                         available_features: List[str], 
                         kmeans: KMeans, 
                         scaler: StandardScaler,
                         vocabulary: ZoneVocabulary) -> Dict[str, ClusterAnalysis]:
        """Анализ результатов кластеризации."""
        clusters_analysis = {}
        
        for cluster_id in range(kmeans.n_clusters):
            cluster_data = df_features[df_features['cluster'] == cluster_id]
            
            if len(cluster_data) == 0:
                continue
            
            # Центроид (обратная нормализация)
            centroid_scaled = kmeans.cluster_centers_[cluster_id]
            centroid_original = scaler.inverse_transform([centroid_scaled])[0]
            centroid_dict = {feature: float(centroid_original[i]) 
                           for i, feature in enumerate(available_features)}
            
            # Характеристики кластера
            characteristics = {}
            for feature in available_features:
                if feature in cluster_data.columns:
                    characteristics[f'{feature}_mean'] = float(cluster_data[feature].mean())
                    characteristics[f'{feature}_std'] = float(cluster_data[feature].std())
            
            # Преобладающий тип
            type_counts = cluster_data['zone_type'].value_counts()
            dominant_type = type_counts.index[0] if len(type_counts) > 0 else 'unknown'
            
            # Средние метрики
            avg_duration = float(cluster_data['duration'].mean()) if 'duration' in cluster_data.columns else 0
            avg_return = float(cluster_data['price_return'].mean()) if 'price_return' in cluster_data.columns else 0
            
            clusters_analysis[f'cluster_{cluster_id}'] = ClusterAnalysis(
                cluster_id=cluster_id,
                size=len(cluster_data),
                centroid=centroid_dict,
                characteristics=characteristics,
                dominant_type=dominant_type,
                avg_duration=avg_duration,
                avg_return=avg_return,
                metadata={
                    # Раньше здесь считались доли двух захардкоженных имён, и на
                    # любом другом словаре обе выходили нулевыми. Теперь — доли по
                    # объявленной полярности, плюс полное распределение типов,
                    # которое не зависит от словаря вовсе.
                    'type_distribution': (
                        cluster_data['zone_type'].value_counts(normalize=True).to_dict()
                        if 'zone_type' in cluster_data.columns else {}
                    ),
                    'elevated_ratio': _polarity_ratio(cluster_data, vocabulary, 1),
                    'depressed_ratio': _polarity_ratio(cluster_data, vocabulary, -1),
                }
            )
        
        return {k: v.__dict__ for k, v in clusters_analysis.items()}
    
    def _evaluate_clustering_quality(self, features_scaled: np.ndarray, 
                                   cluster_labels: np.ndarray, 
                                   n_clusters: int) -> Dict[str, float]:
        """Оценка качества кластеризации."""
        from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
        
        quality_metrics = {}
        
        try:
            if n_clusters > 1 and len(np.unique(cluster_labels)) > 1:
                quality_metrics['silhouette_score'] = float(silhouette_score(features_scaled, cluster_labels))
                quality_metrics['calinski_harabasz_score'] = float(calinski_harabasz_score(features_scaled, cluster_labels))
                quality_metrics['davies_bouldin_score'] = float(davies_bouldin_score(features_scaled, cluster_labels))
        except Exception as e:
            logger.warning(f"Failed to calculate clustering quality metrics: {e}")
        
        return quality_metrics
    
    def _calculate_feature_importance(self, features_scaled: np.ndarray, 
                                    cluster_labels: np.ndarray, 
                                    feature_names: List[str]) -> Dict[str, float]:
        """Вычисление важности признаков для кластеризации."""
        feature_importance = {}
        
        try:
            for i, feature_name in enumerate(feature_names):
                feature_values = features_scaled[:, i]
                
                # Вычисляем дисперсию между кластерами
                cluster_means = []
                for cluster_id in np.unique(cluster_labels):
                    cluster_mask = cluster_labels == cluster_id
                    if np.sum(cluster_mask) > 0:
                        cluster_mean = np.mean(feature_values[cluster_mask])
                        cluster_means.append(cluster_mean)
                
                if len(cluster_means) > 1:
                    between_cluster_variance = np.var(cluster_means)
                    feature_importance[feature_name] = float(between_cluster_variance)
                else:
                    feature_importance[feature_name] = 0.0
                    
        except Exception as e:
            logger.warning(f"Failed to calculate feature importance: {e}")
        
        return feature_importance


# Удобные функции для быстрого использования
def create_zone_sequence_analysis(zones_features: List[Union[ZoneFeatures, Dict[str, Any]]], 
                                min_sequence_length: int = 3) -> Dict[str, Any]:
    """
    Анализ последовательностей зон (совместимость с оригинальным API).
    
    Args:
        zones_features: Список характеристик зон
        min_sequence_length: Минимальная длина последовательности
    
    Returns:
        Словарь с результатами анализа
    """
    analyzer = ZoneSequenceAnalyzer(min_sequence_length=min_sequence_length)
    analysis_result = analyzer.analyze_zone_transitions(zones_features)
    return analysis_result.results


def cluster_zone_shapes(zones_features: List[Union[ZoneFeatures, Dict[str, Any]]], 
                       n_clusters: int = 3) -> Dict[str, Any]:
    """
    Кластеризация зон по форме (совместимость с оригинальным API).
    
    Args:
        zones_features: Список характеристик зон
        n_clusters: Количество кластеров
    
    Returns:
        Словарь с результатами кластеризации
    """
    analyzer = ZoneSequenceAnalyzer()
    analysis_result = analyzer.cluster_zones(zones_features, n_clusters=n_clusters)
    return analysis_result.results


# Экспорт
__all__ = [
    'TransitionAnalysis',
    'ClusterAnalysis', 
    'ZoneSequenceAnalyzer',
    'create_zone_sequence_analysis',
    'cluster_zone_shapes'
]
