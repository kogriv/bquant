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


class ZoneSequenceAnalyzer(BaseAnalyzer):
    """
    Анализатор последовательностей торговых зон.
    
    Предоставляет методы для:
    - Анализа переходов между зонами
    - Вычисления вероятностей переходов
    - Кластеризации зон по форме и характеристикам
    - Выявления паттернов в последовательностях
    """
    
    def __init__(self, min_sequence_length: int = 3):
        """
        Инициализация анализатора.
        
        Args:
            min_sequence_length: Минимальная длина последовательности для анализа
        """
        super().__init__("ZoneSequenceAnalyzer")
        self.min_sequence_length = min_sequence_length
        self.logger = get_logger(f"{__name__}.ZoneSequenceAnalyzer")
        
        self.logger.info(f"Initialized zone sequence analyzer with min_sequence_length={min_sequence_length}")
    
    def analyze_zone_transitions(self, zones_features: List[Union[ZoneFeatures, Dict[str, Any]]]) -> AnalysisResult:
        """
        Анализ переходов между зонами.
        
        Args:
            zones_features: Список объектов ZoneFeatures или словарей
        
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
            
            # Анализируем переходы
            transitions = self._calculate_transitions(df_features)
            transition_probabilities = self._calculate_transition_probabilities(transitions)
            transition_details = self._analyze_transition_details(df_features, transitions)
            
            # Анализ паттернов
            patterns = self._find_sequence_patterns(zone_sequence)
            
            # Статистические тесты
            randomness_tests = self._test_sequence_randomness(zone_sequence)
            
            # Марковский анализ
            markov_analysis = self._markov_chain_analysis(zone_sequence)
            
            results = {
                'sequence_summary': {
                    'total_zones': len(zone_sequence),
                    'total_transitions': len(zone_sequence) - 1,
                    'unique_transition_types': len(transitions),
                    'sequence_length': len(zone_sequence)
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
                     features_to_use: Optional[List[str]] = None) -> AnalysisResult:
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
                    'duration', 'macd_amplitude', 'hist_amplitude', 
                    'price_range_pct', 'correlation_price_hist'
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
            clusters_analysis = self._analyze_clusters(df_features, available_features, kmeans, scaler)
            
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
    
    def _calculate_transitions(self, df_features: pd.DataFrame) -> Dict[str, int]:
        """Подсчет переходов между зонами."""
        zone_sequence = df_features['zone_type'].tolist()
        transitions = {}
        
        for i in range(len(zone_sequence) - 1):
            current = zone_sequence[i]
            next_zone = zone_sequence[i + 1]
            transition = f"{current}_to_{next_zone}"
            
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
                                  transitions: Dict[str, int]) -> Dict[str, TransitionAnalysis]:
        """Детальный анализ переходов."""
        zone_sequence = df_features['zone_type'].tolist()
        transition_details = {}
        
        # Собираем данные о переходах
        transition_data = {transition: {'before': [], 'after': []} 
                          for transition in transitions.keys()}
        
        for i in range(len(zone_sequence) - 1):
            current = zone_sequence[i]
            next_zone = zone_sequence[i + 1]
            transition = f"{current}_to_{next_zone}"
            
            if transition in transition_data:
                transition_data[transition]['before'].append(i)
                transition_data[transition]['after'].append(i + 1)
        
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
    
    def _find_sequence_patterns(self, zone_sequence: List[str]) -> Dict[str, Any]:
        """Поиск паттернов в последовательностях."""
        patterns = {}
        
        # Анализ длин серий
        current_type = zone_sequence[0]
        current_length = 1
        series_lengths = {current_type: []}
        
        for i in range(1, len(zone_sequence)):
            if zone_sequence[i] == current_type:
                current_length += 1
            else:
                series_lengths[current_type].append(current_length)
                current_type = zone_sequence[i]
                if current_type not in series_lengths:
                    series_lengths[current_type] = []
                current_length = 1
        
        # Добавляем последнюю серию
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
        
        # Поиск триплетов (последовательности из 3 зон)
        if len(zone_sequence) >= 3:
            triplets = {}
            for i in range(len(zone_sequence) - 2):
                triplet = f"{zone_sequence[i]}-{zone_sequence[i+1]}-{zone_sequence[i+2]}"
                triplets[triplet] = triplets.get(triplet, 0) + 1
            
            patterns['triplet_patterns'] = triplets
        
        return patterns
    
    def _test_sequence_randomness(self, zone_sequence: List[str]) -> Dict[str, Any]:
        """Тестирование случайности последовательности."""
        randomness_tests = {}
        
        # Runs test
        binary_sequence = [1 if zone == 'bull' else 0 for zone in zone_sequence]
        runs_result = self._runs_test(binary_sequence)
        randomness_tests['runs_test'] = runs_result
        
        # Chi-square test для равномерности
        bull_count = zone_sequence.count('bull')
        bear_count = zone_sequence.count('bear')
        
        if bull_count > 0 and bear_count > 0:
            expected = len(zone_sequence) / 2
            chi2_stat = ((bull_count - expected)**2 / expected + 
                        (bear_count - expected)**2 / expected)
            chi2_p = 1 - stats.chi2.cdf(chi2_stat, df=1)
            
            randomness_tests['uniformity_test'] = {
                'chi2_statistic': chi2_stat,
                'p_value': chi2_p,
                'is_uniform': chi2_p > 0.05,
                'bull_count': bull_count,
                'bear_count': bear_count
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
    
    def _markov_chain_analysis(self, zone_sequence: List[str]) -> Dict[str, Any]:
        """Анализ последовательности как цепи Маркова."""
        if len(zone_sequence) < 2:
            return {'error': 'Sequence too short for Markov analysis'}
        
        # Матрица переходов
        states = ['bull', 'bear']
        transition_matrix = np.zeros((2, 2))
        state_to_index = {'bull': 0, 'bear': 1}
        
        # Подсчет переходов
        for i in range(len(zone_sequence) - 1):
            current_state = zone_sequence[i]
            next_state = zone_sequence[i + 1]
            
            if current_state in state_to_index and next_state in state_to_index:
                current_idx = state_to_index[current_state]
                next_idx = state_to_index[next_state]
                transition_matrix[current_idx, next_idx] += 1
        
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
        except:
            stationary_distribution = None
        
        return {
            'transition_matrix': transition_matrix.tolist(),
            'transition_probabilities': transition_probabilities.tolist(),
            'states': states,
            'stationary_distribution': stationary_distribution.tolist() if stationary_distribution is not None else None
        }
    
    def _analyze_clusters(self, df_features: pd.DataFrame, 
                         available_features: List[str], 
                         kmeans: KMeans, 
                         scaler: StandardScaler) -> Dict[str, ClusterAnalysis]:
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
                    'bull_ratio': (cluster_data['zone_type'] == 'bull').mean() if 'zone_type' in cluster_data.columns else 0,
                    'bear_ratio': (cluster_data['zone_type'] == 'bear').mean() if 'zone_type' in cluster_data.columns else 0
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
