"""
MACD Zone Analyzer for BQuant

Современный MACD анализатор с поддержкой определения зон, статистических тестов,
кластеризации и анализа последовательностей. Адаптировано из scripts/research/macd_analysis.py
с использованием новой архитектуры BQuant.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import warnings
from scipy import stats
from scipy.signal import find_peaks
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# BQuant imports
from ..core.config import get_indicator_params, get_analysis_params
from ..core.exceptions import AnalysisError, StatisticalAnalysisError, create_indicator_calculation_error
from ..core.logging_config import get_logger
from ..core.performance import performance_monitor, performance_context, OptimizedIndicators
from ..core.cache import cached
from ..indicators.calculators import calculate_macd
from ..data.processor import calculate_derived_indicators

# Получаем логгер для модуля
logger = get_logger(__name__)

warnings.filterwarnings('ignore')


@dataclass
class ZoneInfo:
    """
    Информация о зоне MACD.
    
    Attributes:
        zone_id: Уникальный идентификатор зоны
        type: Тип зоны ('bull' или 'bear')
        start_idx: Начальный индекс
        end_idx: Конечный индекс
        start_time: Время начала зоны
        end_time: Время окончания зоны
        duration: Длительность в барах
        data: DataFrame с данными зоны
        features: Рассчитанные признаки зоны
    """
    zone_id: int
    type: str  # 'bull' or 'bear'
    start_idx: int
    end_idx: int
    start_time: datetime
    end_time: datetime
    duration: int
    data: pd.DataFrame
    features: Optional[Dict[str, Any]] = None


@dataclass
class ZoneAnalysisResult:
    """
    Результат анализа зон MACD.
    
    Attributes:
        zones: Список обнаруженных зон
        statistics: Статистики распределения зон
        hypothesis_tests: Результаты тестов гипотез
        clustering: Результаты кластеризации
        sequence_analysis: Анализ последовательностей зон
        data: DataFrame с MACD индикаторами (для визуализации)
        metadata: Метаданные анализа
    """
    zones: List[ZoneInfo]
    statistics: Dict[str, Any]
    hypothesis_tests: Dict[str, Any]
    clustering: Optional[Dict[str, Any]] = None
    sequence_analysis: Optional[Dict[str, Any]] = None
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MACDZoneAnalyzer:
    """
    Современный анализатор зон MACD с полной интеграцией в BQuant.
    
    Предоставляет методы для:
    - Расчета MACD с использованием встроенных индикаторов
    - Определения бычьих и медвежьих зон
    - Расчета признаков зон
    - Статистического анализа и тестирования гипотез
    - Кластеризации зон по форме
    - Анализа последовательностей зон
    """
    
    def __init__(self, 
                 macd_params: Optional[Dict[str, Any]] = None,
                 zone_params: Optional[Dict[str, Any]] = None):
        """
        Инициализация анализатора.
        
        Args:
            macd_params: Параметры MACD (fast, slow, signal)
            zone_params: Параметры анализа зон (min_duration, min_amplitude)
        """
        self.macd_params = macd_params or get_indicator_params('macd')
        self.zone_params = zone_params or get_analysis_params('zone_analysis')
        
        logger.info(f"MACD Zone Analyzer initialized with params: "
                   f"MACD={self.macd_params}, Zones={self.zone_params}")
    
    @performance_monitor()
    @cached(ttl=3600, disk=True, key_prefix="macd_atr_")
    def calculate_macd_with_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитать MACD и ATR используя BQuant индикаторы.
        Оптимизированная версия с кэшированием и мониторингом производительности.
        
        Args:
            df: DataFrame с OHLCV данными
            
        Returns:
            DataFrame с MACD и ATR данными
            
        Raises:
            AnalysisError: При ошибке расчета индикаторов
        """
        try:
            with performance_context("MACD and ATR calculation"):
                logger.info("Calculating MACD and ATR indicators (optimized)")
                
                # Начинаем с исходных OHLCV данных
                df_with_indicators = df.copy()
                
                # Используем оптимизированную реализацию для больших датасетов
                if len(df) > 1000:
                    logger.debug("Using optimized NumPy implementation for large dataset")
                    close_prices = df['close'].values
                    macd_line, signal_line, histogram = OptimizedIndicators.macd(
                        close_prices,
                        fast=self.macd_params['fast'],
                        slow=self.macd_params['slow'],
                        signal=self.macd_params['signal']
                    )
                    
                    df_with_indicators['macd'] = macd_line
                    df_with_indicators['macd_signal'] = signal_line
                    df_with_indicators['macd_hist'] = histogram
                else:
                    # Для малых датасетов используем обычную версию
                    logger.debug("Using standard implementation for small dataset")
                    macd_data = calculate_macd(
                        df, 
                        fast=self.macd_params['fast'],
                        slow=self.macd_params['slow'],
                        signal=self.macd_params['signal']
                    )
                    
                    # Добавляем MACD колонки к исходным данным
                    for col in macd_data.columns:
                        df_with_indicators[col] = macd_data[col]
                
                # Добавляем производные индикаторы (включая ATR)
                derived_data = calculate_derived_indicators(df_with_indicators)
                
                # Объединяем производные индикаторы
                for col in derived_data.columns:
                    if col not in df_with_indicators.columns:
                        df_with_indicators[col] = derived_data[col]
                
                logger.info(f"Successfully calculated indicators. Shape: {df_with_indicators.shape}")
            return df_with_indicators
            
        except Exception as e:
            raise AnalysisError(
                f"Failed to calculate MACD and ATR: {e}",
                {'macd_params': self.macd_params}
            )
    
    @performance_monitor()
    def identify_zones(self, df: pd.DataFrame) -> List[ZoneInfo]:
        """
        Определить зоны MACD (бычьи и медвежьи).
        
        Args:
            df: DataFrame с рассчитанным MACD
            
        Returns:
            Список объектов ZoneInfo
            
        Raises:
            AnalysisError: При ошибке определения зон
        """
        try:
            logger.info("Identifying MACD zones")
            
            if 'macd' not in df.columns:
                raise ValueError("MACD data not found in DataFrame")
            
            min_duration = self.zone_params['min_duration']
            zones = []
            
            # Определяем знак MACD
            df_zones = df.copy()
            df_zones['macd_sign'] = np.where(df_zones['macd'] > 0, 1, -1)
            
            # Находим точки смены знака
            sign_changes = df_zones['macd_sign'].diff().fillna(0)
            change_points = df_zones[sign_changes != 0].index.tolist()
            
            # Добавляем начало и конец данных
            if df_zones.index[0] not in change_points:
                change_points.insert(0, df_zones.index[0])
            if df_zones.index[-1] not in change_points:
                change_points.append(df_zones.index[-1])
            
            # Создаем зоны
            for i in range(len(change_points) - 1):
                start_time = change_points[i]
                end_time = change_points[i + 1]
                
                # Получаем позиции в DataFrame
                start_idx = df_zones.index.get_loc(start_time)
                end_idx = df_zones.index.get_loc(end_time)
                
                duration = end_idx - start_idx
                
                # Пропускаем слишком короткие зоны
                if duration < min_duration:
                    continue
                
                # Получаем данные зоны
                zone_data = df_zones.iloc[start_idx:end_idx + 1]
                zone_type = 'bull' if zone_data['macd'].iloc[0] > 0 else 'bear'
                
                zone_info = ZoneInfo(
                    zone_id=len(zones),
                    type=zone_type,
                    start_idx=start_idx,
                    end_idx=end_idx,
                    start_time=start_time,
                    end_time=end_time,
                    duration=len(zone_data),
                    data=zone_data
                )
                
                zones.append(zone_info)
            
            logger.info(f"Identified {len(zones)} zones: "
                       f"{sum(1 for z in zones if z.type == 'bull')} bull, "
                       f"{sum(1 for z in zones if z.type == 'bear')} bear")
            
            return zones
            
        except Exception as e:
            raise AnalysisError(
                f"Failed to identify zones: {e}",
                {'zone_params': self.zone_params}
            )
    
    @performance_monitor()
    def calculate_zone_features(self, zone: ZoneInfo) -> Dict[str, Any]:
        """
        Рассчитать признаки для зоны.
        
        Args:
            zone: Объект ZoneInfo
            
        Returns:
            Словарь с признаками зоны
            
        Raises:
            AnalysisError: При ошибке расчета признаков
        """
        try:
            data = zone.data
            zone_type = zone.type
            
            # Базовые признаки
            features = {
                'zone_id': zone.zone_id,
                'type': zone_type,
                'duration': zone.duration,
                'start_price': data['close'].iloc[0],
                'end_price': data['close'].iloc[-1],
                'price_return': (data['close'].iloc[-1] / data['close'].iloc[0]) - 1,
            }
            
            # MACD признаки
            features.update({
                'max_macd': data['macd'].max(),
                'min_macd': data['macd'].min(),
                'macd_amplitude': data['macd'].max() - data['macd'].min(),
                'avg_macd': data['macd'].mean(),
                'macd_std': data['macd'].std(),
            })
            
            # Гистограмма MACD
            features.update({
                'max_hist': data['macd_hist'].max(),
                'min_hist': data['macd_hist'].min(),
                'hist_amplitude': data['macd_hist'].max() - data['macd_hist'].min(),
                'avg_hist': data['macd_hist'].mean(),
                'hist_std': data['macd_hist'].std(),
            })
            
            # ATR признаки
            if 'atr' in data.columns:
                features.update({
                    'atr_start': data['atr'].iloc[0],
                    'atr_end': data['atr'].iloc[-1],
                    'avg_atr': data['atr'].mean()
                })
                
                # Нормализованные метрики
                if features['atr_start'] > 0:
                    features['price_return_atr'] = features['price_return'] / features['atr_start']
                    features['macd_amplitude_atr'] = features['macd_amplitude'] / features['atr_start']
            
            # Ценовые метрики
            features.update({
                'max_price': data['high'].max(),
                'min_price': data['low'].min(),
                'price_range': data['high'].max() - data['low'].min(),
                'price_range_pct': (data['high'].max() / data['low'].min()) - 1,
            })
            
            # Нормализация по ATR
            if 'avg_atr' in features and features['avg_atr'] > 0:
                features['price_range_atr'] = features['price_range'] / features['avg_atr']
            
            # Специфичные метрики для типа зоны
            if zone_type == 'bull':
                features['drawdown_from_peak'] = (data['close'].iloc[-1] / data['high'].max()) - 1
                peak_idx = data['high'].idxmax()
                peak_pos = data.index.get_loc(peak_idx)
                features['peak_time_ratio'] = peak_pos / len(data)
            else:  # bear
                features['rally_from_trough'] = (data['close'].iloc[-1] / data['low'].min()) - 1
                trough_idx = data['low'].idxmin()
                trough_pos = data.index.get_loc(trough_idx)
                features['trough_time_ratio'] = trough_pos / len(data)
            
            # Корреляционные метрики
            features['price_hist_corr'] = data['close'].corr(data['macd_hist'])
            
            # Анализ экстремумов
            if len(data) > 3:
                features['num_peaks'] = len(find_peaks(data['high'].values)[0])
                features['num_troughs'] = len(find_peaks(-data['low'].values)[0])
            else:
                features['num_peaks'] = 0
                features['num_troughs'] = 0
            
            return features
            
        except Exception as e:
            raise AnalysisError(
                f"Failed to calculate zone features: {e}",
                {'zone_id': zone.zone_id, 'zone_type': zone.type}
            )
    
    def analyze_zones_distribution(self, zones: List[ZoneInfo]) -> Dict[str, Any]:
        """
        Анализ распределения характеристик зон.
        
        Args:
            zones: Список зон с рассчитанными признаками
            
        Returns:
            Словарь со статистиками распределения
        """
        try:
            logger.info("Analyzing zones distribution")
            
            # Собираем признаки всех зон
            features_list = [zone.features for zone in zones if zone.features]
            if not features_list:
                raise ValueError("No zone features found")
            
            df_features = pd.DataFrame(features_list)
            
            # Разделяем по типу
            bull_zones = df_features[df_features['type'] == 'bull']
            bear_zones = df_features[df_features['type'] == 'bear']
            
            # Рассчитываем статистики
            stats_dict = {
                'total_zones': len(df_features),
                'bull_zones': len(bull_zones),
                'bear_zones': len(bear_zones),
                'bull_ratio': len(bull_zones) / len(df_features) if len(df_features) > 0 else 0,
            }
            
            # Статистики по длительности
            if len(bull_zones) > 0:
                stats_dict.update({
                    'bull_duration_mean': bull_zones['duration'].mean(),
                    'bull_duration_median': bull_zones['duration'].median(),
                    'bull_duration_std': bull_zones['duration'].std(),
                    'bull_price_return_mean': bull_zones['price_return'].mean(),
                    'bull_macd_amplitude_mean': bull_zones['macd_amplitude'].mean(),
                })
            
            if len(bear_zones) > 0:
                stats_dict.update({
                    'bear_duration_mean': bear_zones['duration'].mean(),
                    'bear_duration_median': bear_zones['duration'].median(),
                    'bear_duration_std': bear_zones['duration'].std(),
                    'bear_price_return_mean': bear_zones['price_return'].mean(),
                    'bear_macd_amplitude_mean': bear_zones['macd_amplitude'].mean(),
                })
            
            logger.info(f"Distribution analysis completed: {stats_dict['total_zones']} zones analyzed")
            return stats_dict
            
        except Exception as e:
            raise StatisticalAnalysisError(
                f"Failed to analyze zones distribution: {e}",
                {'zones_count': len(zones)}
            )
    
    def test_hypotheses(self, zones: List[ZoneInfo]) -> Dict[str, Any]:
        """
        Проверка торговых гипотез.
        
        Args:
            zones: Список зон с рассчитанными признаками
            
        Returns:
            Словарь с результатами тестов гипотез
        """
        try:
            logger.info("Testing trading hypotheses")
            
            features_list = [zone.features for zone in zones if zone.features]
            if not features_list:
                raise ValueError("No zone features found")
            
            df_features = pd.DataFrame(features_list)
            results = {}
            
            # Гипотеза 1: Длинные зоны чаще заканчиваются сильным движением
            if len(df_features) >= 10:  # Минимум данных для статистического теста
                duration_80 = df_features['duration'].quantile(0.8)
                duration_20 = df_features['duration'].quantile(0.2)
                
                long_zones = df_features[df_features['duration'] > duration_80]
                short_zones = df_features[df_features['duration'] < duration_20]
                
                if len(long_zones) > 0 and len(short_zones) > 0:
                    t_stat, p_value = stats.ttest_ind(
                        abs(long_zones['price_return']), 
                        abs(short_zones['price_return'])
                    )
                    results['hypothesis_1_long_zones_strong_moves'] = {
                        'description': 'Long zones end with stronger price moves',
                        't_statistic': float(t_stat),
                        'p_value': float(p_value),
                        'significant': p_value < 0.05,
                        'long_zones_avg_return': float(abs(long_zones['price_return']).mean()),
                        'short_zones_avg_return': float(abs(short_zones['price_return']).mean())
                    }
            
            # Гипотеза 2: Корреляция амплитуды гистограммы и длительности
            if len(df_features) >= 3:
                correlation, p_value = stats.pearsonr(
                    df_features['hist_amplitude'].fillna(0), 
                    df_features['duration']
                )
                results['hypothesis_2_hist_duration_correlation'] = {
                    'description': 'Histogram amplitude correlates with zone duration',
                    'correlation': float(correlation),
                    'p_value': float(p_value),
                    'significant': p_value < 0.05
                }
            
            # Гипотеза 3: Высокая корреляция цены и гистограммы влияет на просадку
            bull_zones = df_features[df_features['type'] == 'bull']
            if len(bull_zones) >= 6:
                high_corr = bull_zones[bull_zones['price_hist_corr'] > 0.7]
                low_corr = bull_zones[bull_zones['price_hist_corr'] < 0.3]
                
                if len(high_corr) > 0 and len(low_corr) > 0:
                    t_stat, p_value = stats.ttest_ind(
                        abs(high_corr['drawdown_from_peak'].fillna(0)), 
                        abs(low_corr['drawdown_from_peak'].fillna(0))
                    )
                    results['hypothesis_3_correlation_drawdown'] = {
                        'description': 'Price-histogram correlation affects drawdown',
                        't_statistic': float(t_stat),
                        'p_value': float(p_value),
                        'significant': p_value < 0.05,
                        'high_corr_avg_drawdown': float(abs(high_corr['drawdown_from_peak']).mean()),
                        'low_corr_avg_drawdown': float(abs(low_corr['drawdown_from_peak']).mean())
                    }
            
            logger.info(f"Hypothesis testing completed: {len(results)} tests performed")
            return results
            
        except Exception as e:
            raise StatisticalAnalysisError(
                f"Failed to test hypotheses: {e}",
                {'zones_count': len(zones)}
            )
    
    def analyze_zone_sequences(self, zones: List[ZoneInfo]) -> Dict[str, Any]:
        """
        Анализ последовательностей зон.
        
        Args:
            zones: Список зон
            
        Returns:
            Результаты анализа последовательностей
        """
        try:
            logger.info("Analyzing zone sequences")
            
            if len(zones) < 2:
                return {
                    'transitions': {},
                    'transition_probabilities': {},
                    'total_transitions': 0
                }
            
            # Создаем последовательность типов зон
            zone_sequence = [zone.type for zone in zones]
            
            # Анализ переходов
            transitions = {}
            for i in range(len(zone_sequence) - 1):
                current = zone_sequence[i]
                next_zone = zone_sequence[i + 1]
                transition = f"{current}_to_{next_zone}"
                
                transitions[transition] = transitions.get(transition, 0) + 1
            
            # Вероятности переходов
            total_transitions = sum(transitions.values())
            transition_probs = {k: v/total_transitions for k, v in transitions.items()}
            
            logger.info(f"Sequence analysis completed: {total_transitions} transitions analyzed")
            
            return {
                'transitions': transitions,
                'transition_probabilities': transition_probs,
                'total_transitions': total_transitions
            }
            
        except Exception as e:
            raise StatisticalAnalysisError(
                f"Failed to analyze zone sequences: {e}",
                {'zones_count': len(zones)}
            )
    
    def cluster_zones_by_shape(self, zones: List[ZoneInfo], n_clusters: int = 3) -> Dict[str, Any]:
        """
        Кластеризация зон по форме.
        
        Args:
            zones: Список зон с рассчитанными признаками
            n_clusters: Количество кластеров
            
        Returns:
            Результаты кластеризации
        """
        try:
            logger.info(f"Clustering zones by shape into {n_clusters} clusters")
            
            features_list = [zone.features for zone in zones if zone.features]
            if len(features_list) < n_clusters:
                raise ValueError(f"Not enough zones ({len(features_list)}) for {n_clusters} clusters")
            
            df_features = pd.DataFrame(features_list)
            
            # Выбираем признаки для кластеризации
            shape_features = [
                'duration', 'macd_amplitude', 'hist_amplitude', 
                'price_range_pct', 'price_hist_corr', 'num_peaks', 'num_troughs'
            ]
            
            # Фильтруем доступные признаки
            available_features = [f for f in shape_features if f in df_features.columns]
            
            if len(available_features) < 2:
                raise ValueError("Not enough features for clustering")
            
            # Нормализуем признаки
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(df_features[available_features].fillna(0))
            
            # Кластеризация
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Добавляем метки кластеров к зонам
            for i, zone in enumerate(zones):
                if zone.features and i < len(cluster_labels):
                    zone.features['shape_cluster'] = int(cluster_labels[i])
            
            # Анализ кластеров
            df_features['shape_cluster'] = cluster_labels
            cluster_analysis = {}
            
            for i in range(n_clusters):
                cluster_data = df_features[df_features['shape_cluster'] == i]
                cluster_analysis[f'cluster_{i}'] = {
                    'size': len(cluster_data),
                    'avg_duration': float(cluster_data['duration'].mean()),
                    'avg_price_return': float(cluster_data['price_return'].mean()),
                    'bull_ratio': float((cluster_data['type'] == 'bull').mean())
                }
            
            logger.info(f"Clustering completed: {len(features_list)} zones clustered into {n_clusters} groups")
            
            return {
                'cluster_labels': cluster_labels.tolist(),
                'cluster_analysis': cluster_analysis,
                'n_clusters': n_clusters,
                'features_used': available_features
            }
            
        except Exception as e:
            raise StatisticalAnalysisError(
                f"Failed to cluster zones: {e}",
                {'zones_count': len(zones), 'n_clusters': n_clusters}
            )
    
    def _zone_to_dict(self, zone: ZoneInfo) -> Dict[str, Any]:
        """
        Конвертация ZoneInfo в формат для модульных анализаторов.
        
        Вспомогательный метод для интеграции с bquant.analysis.zones модулями.
        
        Args:
            zone: Объект ZoneInfo для конвертации
            
        Returns:
            Словарь с данными зоны в формате для анализаторов
        """
        return {
            'zone_id': zone.zone_id,
            'type': zone.type,
            'duration': zone.duration,
            'data': zone.data,
            # Добавляем features если есть
            **(zone.features or {})
        }
    
    def _features_to_dict(self, features) -> Dict[str, Any]:
        """
        Конвертация ZoneFeatures в словарь.
        
        Args:
            features: Объект ZoneFeatures или объект с методом to_dict()
            
        Returns:
            Словарь с признаками зоны
        """
        if hasattr(features, 'to_dict'):
            return features.to_dict()
        return dict(features)
    
    def _adapt_statistics_format(self, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Адаптация формата статистик из модульного анализатора в формат старой версии.
        
        Преобразует вложенную структуру из ZoneFeaturesAnalyzer в плоский формат,
        совместимый с analyze_complete().
        
        Args:
            stats_data: Вложенная структура статистик из ZoneFeaturesAnalyzer
            
        Returns:
            Плоский словарь статистик в формате старой версии
        """
        adapted = {}
        
        # Общая статистика (распаковываем из total_statistics)
        if 'total_statistics' in stats_data:
            total = stats_data['total_statistics']
            adapted['total_zones'] = total.get('total_zones', 0)
            adapted['bull_zones'] = total.get('bull_zones_count', 0)
            adapted['bear_zones'] = total.get('bear_zones_count', 0)
            adapted['bull_ratio'] = total.get('bull_ratio', 0)
            adapted['bear_ratio'] = total.get('bear_ratio', 0)
        
        # Статистика по длительности
        if 'duration_distribution' in stats_data:
            adapted['duration_stats'] = stats_data['duration_distribution']
        
        # Статистика по доходности
        if 'return_distribution' in stats_data:
            adapted['return_stats'] = stats_data['return_distribution']
        
        # Статистика по амплитуде MACD
        if 'macd_amplitude_distribution' in stats_data:
            adapted['macd_amplitude_stats'] = stats_data['macd_amplitude_distribution']
        
        # Статистика по амплитуде гистограммы
        if 'hist_amplitude_distribution' in stats_data:
            adapted['hist_amplitude_stats'] = stats_data['hist_amplitude_distribution']
        
        # Дополнительные метрики
        if 'additional_metrics' in stats_data:
            adapted.update(stats_data['additional_metrics'])
        
        return adapted
    
    @performance_monitor()
    def analyze_complete(self, df: pd.DataFrame, 
                        perform_clustering: bool = True,
                        n_clusters: int = 3) -> ZoneAnalysisResult:
        """
        Полный анализ зон MACD.
        
        Args:
            df: DataFrame с OHLCV данными
            perform_clustering: Выполнять ли кластеризацию
            n_clusters: Количество кластеров для кластеризации
            
        Returns:
            Объект ZoneAnalysisResult с полными результатами анализа
        """
        try:
            logger.info("Starting complete MACD zone analysis")
            
            # 1. Рассчитываем индикаторы
            df_with_indicators = self.calculate_macd_with_atr(df)
            
            # 2. Определяем зоны
            zones = self.identify_zones(df_with_indicators)
            
            if not zones:
                logger.warning("No zones identified")
                return ZoneAnalysisResult(
                    zones=[],
                    statistics={},
                    hypothesis_tests={},
                    data=df_with_indicators,
                    metadata={'warning': 'No zones identified'}
                )
            
            # 3. Рассчитываем признаки для каждой зоны
            for zone in zones:
                zone.features = self.calculate_zone_features(zone)
            
            # 4. Анализ распределения
            statistics = self.analyze_zones_distribution(zones)
            
            # 5. Тестирование гипотез
            hypothesis_tests = self.test_hypotheses(zones)
            
            # 6. Анализ последовательностей
            sequence_analysis = self.analyze_zone_sequences(zones)
            
            # 7. Кластеризация (опционально)
            clustering = None
            if perform_clustering and len(zones) >= n_clusters:
                clustering = self.cluster_zones_by_shape(zones, n_clusters)
            
            # Метаданные
            metadata = {
                'analysis_timestamp': datetime.now().isoformat(),
                'data_period': {
                    'start': df.index[0].isoformat() if hasattr(df.index[0], 'isoformat') else str(df.index[0]),
                    'end': df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1]),
                    'total_bars': len(df)
                },
                'macd_params': self.macd_params,
                'zone_params': self.zone_params,
                'clustering_performed': perform_clustering and clustering is not None
            }
            
            result = ZoneAnalysisResult(
                zones=zones,
                statistics=statistics,
                hypothesis_tests=hypothesis_tests,
                clustering=clustering,
                sequence_analysis=sequence_analysis,
                data=df_with_indicators,
                metadata=metadata
            )
            
            logger.info(f"Complete analysis finished: {len(zones)} zones, "
                       f"{len(hypothesis_tests)} hypothesis tests, "
                       f"clustering: {clustering is not None}")
            
            return result
            
        except Exception as e:
            raise AnalysisError(
                f"Failed to complete MACD zone analysis: {e}",
                {
                    'data_shape': df.shape,
                    'macd_params': self.macd_params,
                    'zone_params': self.zone_params
                }
            )
    
    @performance_monitor()
    def analyze_complete_modular(self, df: pd.DataFrame,
                                 perform_clustering: bool = True,
                                 n_clusters: int = 3) -> ZoneAnalysisResult:
        """
        Полный анализ зон с использованием модульных анализаторов.
        
        Новая версия - использует bquant.analysis.* вместо внутренних методов.
        Предназначена для постепенного перехода на модульную архитектуру.
        
        Args:
            df: DataFrame с OHLCV данными
            perform_clustering: Выполнять ли кластеризацию
            n_clusters: Количество кластеров для кластеризации
            
        Returns:
            Объект ZoneAnalysisResult с полными результатами анализа
            
        Note:
            Этот метод использует те же алгоритмы что и analyze_complete(),
            но делегирует работу модульным анализаторам из bquant.analysis.*
        """
        try:
            logger.info("Starting modular MACD zone analysis")
            
            # 1. Расчет индикаторов и определение зон (без изменений)
            df_with_indicators = self.calculate_macd_with_atr(df)
            zones = self.identify_zones(df_with_indicators)
            
            if not zones:
                logger.warning("No zones identified")
                return ZoneAnalysisResult(
                    zones=[],
                    statistics={},
                    hypothesis_tests={},
                    data=df_with_indicators,
                    metadata={
                        'warning': 'No zones identified',
                        'modular_version': True
                    }
                )
            
            # 2. Расчет признаков через ZoneFeaturesAnalyzer
            from ..analysis.zones import ZoneFeaturesAnalyzer
            features_analyzer = ZoneFeaturesAnalyzer(
                min_duration=self.zone_params['min_duration']
            )
            
            zones_features = []
            for zone in zones:
                zone_dict = self._zone_to_dict(zone)
                zone_features = features_analyzer.extract_zone_features(zone_dict)
                zone.features = self._features_to_dict(zone_features)  # Сохраняем в zone
                zones_features.append(zone_features)
            
            # 3. Статистический анализ через ZoneFeaturesAnalyzer
            statistics_result = features_analyzer.analyze_zones_distribution(
                [self._features_to_dict(f) for f in zones_features]
            )
            # Извлекаем данные из AnalysisResult и адаптируем формат
            if hasattr(statistics_result, 'results'):
                stats_data = statistics_result.results
                # Преобразуем вложенную структуру в плоский формат для совместимости
                statistics = self._adapt_statistics_format(stats_data)
            else:
                statistics = statistics_result
            
            # 4. Тестирование гипотез через HypothesisTestSuite
            from ..analysis.statistical import HypothesisTestSuite
            test_suite = HypothesisTestSuite(alpha=0.05)
            
            hypothesis_tests = {}
            # Подготавливаем данные для тестов с маппингом полей
            features_dicts = []
            for f in zones_features:
                f_dict = self._features_to_dict(f)
                # Добавляем 'type' как alias для 'zone_type' для совместимости с HypothesisTestSuite
                if 'zone_type' in f_dict and 'type' not in f_dict:
                    f_dict['type'] = f_dict['zone_type']
                features_dicts.append(f_dict)
            
            # H1: Длительность vs доходность
            try:
                h1_result = test_suite.test_zone_duration_hypothesis(features_dicts)
                hypothesis_tests['zone_duration'] = h1_result.to_dict()
            except Exception as e:
                logger.warning(f"H1 test failed: {e}")
                hypothesis_tests['zone_duration'] = {'error': str(e)}
            
            # H3: Асимметрия bull/bear
            try:
                h3_result = test_suite.test_bull_bear_asymmetry_hypothesis(features_dicts)
                hypothesis_tests['bull_bear_asymmetry'] = h3_result.to_dict()
            except Exception as e:
                logger.warning(f"H3 test failed: {e}")
                hypothesis_tests['bull_bear_asymmetry'] = {'error': str(e)}
            
            # 5. Анализ последовательностей через ZoneSequenceAnalyzer
            from ..analysis.zones import ZoneSequenceAnalyzer
            sequence_analyzer = ZoneSequenceAnalyzer(min_sequence_length=3)
            
            sequence_result = sequence_analyzer.analyze_zone_transitions(zones_features)
            sequence_analysis = sequence_result.results
            
            # 6. Кластеризация через ZoneSequenceAnalyzer
            clustering = None
            if perform_clustering and len(zones) >= n_clusters:
                try:
                    cluster_result = sequence_analyzer.cluster_zones(
                        zones_features,
                        n_clusters=n_clusters
                    )
                    clustering = cluster_result.results
                except Exception as e:
                    logger.warning(f"Clustering failed: {e}")
                    clustering = None
            
            # 7. Формирование результата (тот же формат!)
            metadata = {
                'analysis_timestamp': datetime.now().isoformat(),
                'data_period': {
                    'start': df.index[0].isoformat() if hasattr(df.index[0], 'isoformat') else str(df.index[0]),
                    'end': df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1]),
                    'total_bars': len(df)
                },
                'macd_params': self.macd_params,
                'zone_params': self.zone_params,
                'clustering_performed': clustering is not None,
                'modular_version': True  # Флаг новой версии
            }
            
            result = ZoneAnalysisResult(
                zones=zones,
                statistics=statistics,
                hypothesis_tests=hypothesis_tests,
                clustering=clustering,
                sequence_analysis=sequence_analysis,
                data=df_with_indicators,
                metadata=metadata
            )
            
            logger.info(f"Modular analysis finished: {len(zones)} zones, "
                       f"{len(hypothesis_tests)} hypothesis tests, "
                       f"clustering: {clustering is not None}")
            
            return result
            
        except Exception as e:
            raise AnalysisError(
                f"Failed to complete modular MACD zone analysis: {e}",
                {
                    'data_shape': df.shape,
                    'macd_params': self.macd_params,
                    'zone_params': self.zone_params,
                    'modular_version': True
                }
            )


def create_macd_analyzer(macd_params: Optional[Dict[str, Any]] = None,
                        zone_params: Optional[Dict[str, Any]] = None) -> MACDZoneAnalyzer:
    """
    Удобная функция для создания MACD анализатора.
    
    Args:
        macd_params: Параметры MACD
        zone_params: Параметры анализа зон
        
    Returns:
        Настроенный MACDZoneAnalyzer
    """
    return MACDZoneAnalyzer(macd_params, zone_params)


def analyze_macd_zones(df: pd.DataFrame,
                      macd_params: Optional[Dict[str, Any]] = None,
                      zone_params: Optional[Dict[str, Any]] = None,
                      perform_clustering: bool = True,
                      n_clusters: int = 3) -> ZoneAnalysisResult:
    """
    Удобная функция для полного анализа зон MACD.
    
    Args:
        df: DataFrame с OHLCV данными
        macd_params: Параметры MACD
        zone_params: Параметры анализа зон
        perform_clustering: Выполнять ли кластеризацию
        n_clusters: Количество кластеров
        
    Returns:
        Полный результат анализа зон
    """
    analyzer = MACDZoneAnalyzer(macd_params, zone_params)
    return analyzer.analyze_complete(df, perform_clustering, n_clusters)
