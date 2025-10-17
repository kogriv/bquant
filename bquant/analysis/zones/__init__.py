"""
Модуль анализа зон BQuant

Предоставляет функции для анализа различных типов зон в финансовых данных:
- MACD зоны
- Price action зоны
- Поддержка и сопротивление
- Волновой анализ
- Зоны накопления/распределения
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass

from ...core.logging_config import get_logger
from .. import BaseAnalyzer, AnalysisResult

logger = get_logger(__name__)

# Версия модуля анализа зон
__version__ = "0.0.0"


@dataclass
class Zone:
    """
    Базовый класс для представления зоны.
    
    Attributes:
        zone_id: Уникальный идентификатор зоны
        zone_type: Тип зоны (support, resistance, accumulation, etc.)
        start_time: Время начала зоны
        end_time: Время окончания зоны
        start_price: Цена начала зоны
        end_price: Цена окончания зоны
        strength: Сила зоны (0-1)
        confidence: Уверенность в зоне (0-1)
        metadata: Дополнительные метаданные
    """
    zone_id: str
    zone_type: str
    start_time: datetime
    end_time: datetime
    start_price: float
    end_price: float
    strength: float = 0.0
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> timedelta:
        """Длительность зоны."""
        return self.end_time - self.start_time
    
    @property
    def price_range(self) -> float:
        """Ценовой диапазон зоны."""
        return abs(self.end_price - self.start_price)
    
    @property
    def mid_price(self) -> float:
        """Средняя цена зоны."""
        return (self.start_price + self.end_price) / 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь."""
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'start_price': self.start_price,
            'end_price': self.end_price,
            'duration_hours': self.duration.total_seconds() / 3600,
            'price_range': self.price_range,
            'mid_price': self.mid_price,
            'strength': self.strength,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class ZoneAnalyzer(BaseAnalyzer):
    """
    Базовый класс для анализа зон.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация анализатора зон.
        
        Args:
            config: Конфигурация анализатора
        """
        super().__init__("ZoneAnalyzer", config)
        
        # Параметры по умолчанию
        self.min_zone_duration = self.config.get('min_zone_duration', 5)
        self.min_strength_threshold = self.config.get('min_strength_threshold', 0.3)
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.5)
    
    def identify_support_resistance(self, data: pd.DataFrame, 
                                  window: int = 20, 
                                  min_touches: int = 2) -> List[Zone]:
        """
        Определение зон поддержки и сопротивления.
        
        Args:
            data: DataFrame с OHLCV данными
            window: Окно для поиска локальных экстремумов
            min_touches: Минимальное количество касаний для подтверждения зоны
        
        Returns:
            Список зон поддержки и сопротивления
        """
        zones = []
        
        if len(data) < window * 2:
            self.logger.warning(f"Insufficient data for support/resistance analysis: {len(data)} < {window * 2}")
            return zones
        
        # Ищем локальные минимумы (поддержка)
        support_levels = self._find_local_extrema(data['low'], window, 'min')
        support_zones = self._validate_zones(data, support_levels, 'support', min_touches)
        zones.extend(support_zones)
        
        # Ищем локальные максимумы (сопротивление)
        resistance_levels = self._find_local_extrema(data['high'], window, 'max')
        resistance_zones = self._validate_zones(data, resistance_levels, 'resistance', min_touches)
        zones.extend(resistance_zones)
        
        self.logger.debug(f"Identified {len(zones)} support/resistance zones")
        return zones
    
    def _find_local_extrema(self, series: pd.Series, window: int, 
                           extrema_type: str) -> List[Tuple[int, float]]:
        """
        Поиск локальных экстремумов.
        
        Args:
            series: Временной ряд
            window: Размер окна
            extrema_type: Тип экстремума ('min' или 'max')
        
        Returns:
            Список (индекс, значение) экстремумов
        """
        extrema = []
        
        for i in range(window, len(series) - window):
            window_data = series.iloc[i-window:i+window+1]
            center_value = series.iloc[i]
            
            if extrema_type == 'min':
                if center_value == window_data.min():
                    extrema.append((i, center_value))
            elif extrema_type == 'max':
                if center_value == window_data.max():
                    extrema.append((i, center_value))
        
        return extrema
    
    def _validate_zones(self, data: pd.DataFrame, extrema: List[Tuple[int, float]], 
                       zone_type: str, min_touches: int) -> List[Zone]:
        """
        Валидация и создание зон на основе экстремумов.
        
        Args:
            data: DataFrame с данными
            extrema: Список экстремумов
            zone_type: Тип зоны
            min_touches: Минимальное количество касаний
        
        Returns:
            Список валидных зон
        """
        zones = []
        
        if len(extrema) < min_touches:
            return zones
        
        # Группируем близкие экстремумы
        tolerance = data['close'].std() * 0.1  # 10% от стандартного отклонения
        
        grouped_extrema = self._group_extrema(extrema, tolerance)
        
        for group in grouped_extrema:
            if len(group) >= min_touches:
                zone = self._create_zone_from_group(data, group, zone_type)
                if zone:
                    zones.append(zone)
        
        return zones
    
    def _group_extrema(self, extrema: List[Tuple[int, float]], 
                      tolerance: float) -> List[List[Tuple[int, float]]]:
        """
        Группировка близких экстремумов.
        
        Args:
            extrema: Список экстремумов
            tolerance: Допустимое отклонение для группировки
        
        Returns:
            Список групп экстремумов
        """
        if not extrema:
            return []
        
        # Сортируем по цене
        sorted_extrema = sorted(extrema, key=lambda x: x[1])
        
        groups = []
        current_group = [sorted_extrema[0]]
        
        for i in range(1, len(sorted_extrema)):
            curr_price = sorted_extrema[i][1]
            prev_price = sorted_extrema[i-1][1]
            
            if abs(curr_price - prev_price) <= tolerance:
                current_group.append(sorted_extrema[i])
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [sorted_extrema[i]]
        
        # Добавляем последнюю группу
        if len(current_group) > 1:
            groups.append(current_group)
        
        return groups
    
    def _create_zone_from_group(self, data: pd.DataFrame, 
                               group: List[Tuple[int, float]], 
                               zone_type: str) -> Optional[Zone]:
        """
        Создание зоны из группы экстремумов.
        
        Args:
            data: DataFrame с данными
            group: Группа экстремумов
            zone_type: Тип зоны
        
        Returns:
            Объект Zone или None
        """
        if not group:
            return None
        
        # Вычисляем параметры зоны
        indices = [idx for idx, _ in group]
        prices = [price for _, price in group]
        
        start_idx = min(indices)
        end_idx = max(indices)
        
        start_time = data.index[start_idx]
        end_time = data.index[end_idx]
        
        min_price = min(prices)
        max_price = max(prices)
        
        # Вычисляем силу зоны (на основе количества касаний)
        strength = min(len(group) / 5.0, 1.0)  # Нормализуем к 1.0
        
        # Вычисляем уверенность (на основе плотности касаний)
        time_span = (end_time - start_time).total_seconds() / 3600  # в часах
        if time_span > 0:
            touch_density = len(group) / time_span
            confidence = min(touch_density / 2.0, 1.0)  # Нормализуем к 1.0
        else:
            confidence = 1.0
        
        zone_id = f"{zone_type}_{start_time.strftime('%Y%m%d_%H%M')}_{end_time.strftime('%Y%m%d_%H%M')}"
        
        zone = Zone(
            zone_id=zone_id,
            zone_type=zone_type,
            start_time=start_time,
            end_time=end_time,
            start_price=min_price,
            end_price=max_price,
            strength=strength,
            confidence=confidence,
            metadata={
                'touch_count': len(group),
                'price_std': np.std(prices),
                'indices': indices
            }
        )
        
        return zone
    
    def analyze_zone_breaks(self, data: pd.DataFrame, zones: List[Zone]) -> Dict[str, Any]:
        """
        Анализ пробоев зон.
        
        Args:
            data: DataFrame с данными
            zones: Список зон для анализа
        
        Returns:
            Результаты анализа пробоев
        """
        break_analysis = {
            'total_zones': len(zones),
            'broken_zones': 0,
            'false_breaks': 0,
            'clean_breaks': 0,
            'break_details': []
        }
        
        for zone in zones:
            # Найдем данные после окончания зоны
            zone_end_idx = data.index.get_loc(zone.end_time)
            if zone_end_idx >= len(data) - 1:
                continue
            
            post_zone_data = data.iloc[zone_end_idx + 1:]
            
            # Определяем пробой
            if zone.zone_type == 'support':
                # Пробой поддержки - цена идет ниже
                break_condition = post_zone_data['low'] < zone.start_price
            else:  # resistance
                # Пробой сопротивления - цена идет выше
                break_condition = post_zone_data['high'] > zone.end_price
            
            if break_condition.any():
                break_analysis['broken_zones'] += 1
                
                # Анализируем тип пробоя
                break_idx = break_condition.idxmax()
                break_details = {
                    'zone_id': zone.zone_id,
                    'zone_type': zone.zone_type,
                    'break_time': break_idx,
                    'break_price': post_zone_data.loc[break_idx, 'close'],
                    'zone_strength': zone.strength,
                    'zone_confidence': zone.confidence
                }
                
                break_analysis['break_details'].append(break_details)
        
        self.logger.debug(f"Analyzed breaks for {len(zones)} zones")
        return break_analysis
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
        """
        Выполнение комплексного анализа зон.
        
        Args:
            data: DataFrame с OHLCV данными
            **kwargs: Дополнительные параметры
        
        Returns:
            AnalysisResult с результатами анализа зон
        """
        if not self.validate_data(data):
            raise ValueError("Data validation failed")
        
        # Проверяем наличие необходимых колонок
        required_columns = ['open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        results = {}
        
        # Анализ зон поддержки и сопротивления
        window = kwargs.get('window', 20)
        min_touches = kwargs.get('min_touches', 2)
        
        zones = self.identify_support_resistance(data, window, min_touches)
        
        # Фильтруем зоны по силе и уверенности
        strong_zones = [z for z in zones if z.strength >= self.min_strength_threshold]
        confident_zones = [z for z in zones if z.confidence >= self.min_confidence_threshold]
        
        results['zones'] = {
            'all_zones': [zone.to_dict() for zone in zones],
            'strong_zones': [zone.to_dict() for zone in strong_zones],
            'confident_zones': [zone.to_dict() for zone in confident_zones],
            'zone_count': len(zones),
            'strong_zone_count': len(strong_zones),
            'confident_zone_count': len(confident_zones)
        }
        
        # Анализ пробоев зон
        if zones:
            break_analysis = self.analyze_zone_breaks(data, zones)
            results['break_analysis'] = break_analysis
        
        # Статистика зон
        if zones:
            zone_stats = self._calculate_zone_statistics(zones)
            results['zone_statistics'] = zone_stats
        
        metadata = {
            'analyzer': 'ZoneAnalyzer',
            'window': window,
            'min_touches': min_touches,
            'min_strength_threshold': self.min_strength_threshold,
            'min_confidence_threshold': self.min_confidence_threshold,
            'config': self.config
        }
        
        return AnalysisResult(
            analysis_type='zones',
            results=results,
            data_size=len(data),
            metadata=metadata
        )
    
    def _calculate_zone_statistics(self, zones: List[Zone]) -> Dict[str, Any]:
        """
        Вычисление статистик по зонам.
        
        Args:
            zones: Список зон
        
        Returns:
            Статистики зон
        """
        if not zones:
            return {}
        
        # Группируем по типам
        support_zones = [z for z in zones if z.zone_type == 'support']
        resistance_zones = [z for z in zones if z.zone_type == 'resistance']
        
        # Общие статистики
        strengths = [z.strength for z in zones]
        confidences = [z.confidence for z in zones]
        durations = [z.duration.total_seconds() / 3600 for z in zones]  # в часах
        
        stats = {
            'total_zones': len(zones),
            'support_zones': len(support_zones),
            'resistance_zones': len(resistance_zones),
            'avg_strength': np.mean(strengths),
            'avg_confidence': np.mean(confidences),
            'avg_duration_hours': np.mean(durations),
            'max_strength': max(strengths),
            'max_confidence': max(confidences),
            'max_duration_hours': max(durations)
        }
        
        return stats


def get_zone_analyzers() -> Dict[str, str]:
    """
    Получить список доступных анализаторов зон.
    
    Returns:
        Словарь {анализатор: описание}
    """
    return {
        'zone': 'Комплексный анализ зон поддержки/сопротивления',
        'support_resistance': 'Анализ уровней поддержки и сопротивления',
        'macd_zones': 'Анализ MACD зон',
        'price_action': 'Анализ зон price action'
    }


# Удобные функции
def find_support_resistance(data: pd.DataFrame, window: int = 20, 
                           min_touches: int = 2) -> List[Zone]:
    """
    Быстрый поиск уровней поддержки и сопротивления.
    
    Args:
        data: DataFrame с OHLCV данными
        window: Окно для поиска экстремумов
        min_touches: Минимальное количество касаний
    
    Returns:
        Список зон
    """
    analyzer = ZoneAnalyzer()
    return analyzer.identify_support_resistance(data, window, min_touches)


# Импорт универсальных моделей зон (новая архитектура)
try:
    from .models import ZoneInfo, ZoneAnalysisResult
    _models_available = True
    logger.info("Zone models (ZoneInfo, ZoneAnalysisResult) loaded successfully")
except ImportError as e:
    logger.warning(f"Zone models not available: {e}")
    _models_available = False

# Импорт расширенных модулей анализа зон
try:
    from .zone_features import (
        ZoneFeatures,
        ZoneFeaturesAnalyzer, 
        analyze_zones_distribution,
        extract_zone_features
    )
    _zone_features_available = True
    logger.info("Zone features module loaded successfully")
except ImportError as e:
    logger.warning(f"Zone features module not available: {e}")
    _zone_features_available = False

try:
    from .sequence_analysis import (
        TransitionAnalysis,
        ClusterAnalysis,
        ZoneSequenceAnalyzer,
        create_zone_sequence_analysis,
        cluster_zone_shapes
    )
    _sequence_analysis_available = True
    logger.info("Sequence analysis module loaded successfully")
except ImportError as e:
    logger.warning(f"Sequence analysis module not available: {e}")
    _sequence_analysis_available = False


# Экспорт базового функционала
__all__ = [
    'Zone',
    'ZoneAnalyzer',
    'get_zone_analyzers',
    'find_support_resistance',
    '__version__'
]

# Добавляем универсальные модели если доступны
if _models_available:
    __all__.extend([
        'ZoneInfo',
        'ZoneAnalysisResult'
    ])

# Добавляем zone features если доступен
if _zone_features_available:
    __all__.extend([
        'ZoneFeatures',
        'ZoneFeaturesAnalyzer',
        'analyze_zones_distribution',
        'extract_zone_features'
    ])

# Добавляем sequence analysis если доступен  
if _sequence_analysis_available:
    __all__.extend([
        'TransitionAnalysis',
        'ClusterAnalysis',
        'ZoneSequenceAnalyzer',
        'create_zone_sequence_analysis',
        'cluster_zone_shapes'
    ])
