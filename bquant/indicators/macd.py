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
from ..core.utils import deprecated
from ..indicators.calculators import calculate_macd
from ..data.processor import calculate_derived_indicators
from ..analysis.zones.models import ZoneInfo, ZoneAnalysisResult

# Получаем логгер для модуля
logger = get_logger(__name__)

warnings.filterwarnings('ignore')

# NOTE: ZoneInfo and ZoneAnalysisResult moved to bquant/analysis/zones/models.py
# Imported above for backward compatibility


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
        
        Note:
            Этот метод теперь использует модульные анализаторы из bquant.analysis.*
            через вызов analyze_complete_modular(). Старая реализация сохранена
            в методах calculate_zone_features(), test_hypotheses() и других,
            которые помечены как deprecated.
        
        Args:
            df: DataFrame с OHLCV данными
            perform_clustering: Выполнять ли кластеризацию
            n_clusters: Количество кластеров для кластеризации
            
        Returns:
            Объект ZoneAnalysisResult с полными результатами анализа
        """
        logger.info("Using modular analyzers (via analyze_complete_modular)")
        return self.analyze_complete_modular(df, perform_clustering, n_clusters)
    
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
