"""
Zone Detection - Base Protocol and Configuration

Этот модуль определяет базовый интерфейс для стратегий детекции зон:
- ZoneDetectionStrategy: Protocol для всех стратегий
- ZoneDetectionConfig: Универсальная конфигурация правил
"""

from typing import Protocol, runtime_checkable, List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd

from ..models import ZoneInfo


@runtime_checkable
class ZoneDetectionStrategy(Protocol):
    """
    Протокол для стратегий определения зон.
    
    Все стратегии детекции должны реализовать метод detect_zones().
    
    CONTRACT (v2.1 - REQUIRED):
        All detection strategies MUST populate indicator_context in each ZoneInfo.
        
        REQUIRED fields in indicator_context:
        - 'detection_strategy': str - name of this strategy
        - 'detection_indicator': str - primary indicator column name
        
        OPTIONAL fields:
        - 'signal_line': Optional[str] - secondary indicator (if 2-line strategy)
        - 'detection_rules': dict - full rules dict (for reference)
        - Any other strategy-specific metadata
        
        Strategy is RESPONSIBLE for deciding:
        - Which of its parameters is the "primary indicator"
        - Which (if any) is the "signal line"
        - What metadata to include
        
        This enables:
        - Self-description (strategies interpret their own rules)
        - Agnosticism (Pipeline doesn't need to know parameter names)
        - Extensibility (new strategies can use ANY parameters)
    
    Example:
        class MyCustomDetection:
            def detect_zones(self, data: pd.DataFrame, 
                           config: ZoneDetectionConfig) -> List[ZoneInfo]:
                # Interpret your rules (strategy decides semantics)
                my_indicator = config.rules['my_custom_param']
                
                # Your detection logic
                # ...
                
                # Create ZoneInfo with indicator_context (REQUIRED!)
                zone = ZoneInfo(
                    zone_id=0,
                    type='bull',
                    start_idx=0,
                    end_idx=10,
                    start_time=data.index[0],
                    end_time=data.index[10],
                    duration=11,
                    data=data.iloc[0:11],
                    indicator_context={
                        'detection_strategy': 'my_custom',      # REQUIRED
                        'detection_indicator': my_indicator,    # REQUIRED
                        'signal_line': None,                    # OPTIONAL
                        'detection_rules': config.rules         # OPTIONAL
                    }
                )
                return [zone]
    """
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: 'ZoneDetectionConfig') -> List[ZoneInfo]:
        """
        Определить зоны на основе данных и правил.
        
        Args:
            data: DataFrame с OHLCV + индикаторами
            config: Конфигурация правил детекции
            
        Returns:
            List[ZoneInfo] - список обнаруженных зон с заполненным indicator_context
            
        Raises:
            ValueError: Если конфигурация некорректна
            
        Note:
            Implementation MUST populate indicator_context in each ZoneInfo
            according to v2.1 contract (see class docstring).
        """
        ...


@dataclass
class ZoneDetectionConfig:
    """
    Универсальная конфигурация правил определения зон.

    Здесь **нет** ``min_duration``, и это осознанно. Детекция обязана выдавать
    полное мощение: каждый бар принадлежит ровно одной зоне, зона ``i+1``
    начинается там, где кончилась зона ``i``. Отбрасывание коротких зон делало
    из мощения решето — соседи выброшенной зоны переставали примыкать, — а
    анализ последовательностей читал их как соседей. Порог длительности стал
    фильтром **отчётности**: его принимает стадия анализа
    (:meth:`UniversalZoneAnalyzer.analyze_zones`), которая сообщает, что именно
    исключила. Разбор: ``devref/gaps/sequence/``.

    Attributes:
        zone_types: Типы зон для поиска. ``None`` = **не фильтровать**: стратегия
            отдаёт все типы, которые находит.

            Раньше ``None`` молча подменялся на ``['bull', 'bear']`` — словарь
            MACD-подобных детекторов. Каждый детектор фильтрует свой вывод через
            этот список, поэтому ``threshold`` (``overbought``/``neutral``/
            ``oversold``) и ``combined`` (типы задаёт вызывающий) возвращали
            **пустой успешный результат**: зоны находились и тут же отбрасывались,
            а лог сообщал «Detected 0 zones», неотличимо от «порогам нечего было
            ловить». Разбор: ``devref/gaps/detection/``.
        rules: Специфичные правила для стратегии (Dict[str, Any])
        strategy_name: Имя стратегии для registry
        metadata: Дополнительная информация (для логирования, отладки)
    
    Example:
        # MACD zero crossing
        config = ZoneDetectionConfig(
            zone_types=['bull', 'bear'],
            # Прямой вызов детектора адресуется именем колонки; роль
            # (`rules={'indicator_role': 'hist'}`) резолвит пайплайн по схеме.
            rules={'indicator_col': 'macd_12_26_9__hist'},
            strategy_name='zero_crossing'
        )

        # RSI thresholds
        config = ZoneDetectionConfig(
            zone_types=['overbought', 'oversold'],
            rules={
                'indicator_col': 'rsi_14',
                'upper_threshold': 70,
                'lower_threshold': 30
            },
            strategy_name='threshold'
        )
    """
    zone_types: Optional[List[str]] = None
    rules: Dict[str, Any] = field(default_factory=dict)
    strategy_name: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def accepts(self, zone_type: str) -> bool:
        """Проходит ли зона этого типа фильтр конфигурации.
        
        ``zone_types is None`` означает отсутствие фильтра, а не пустой белый
        список: стратегия отдаёт всё, что нашла.
        """
        if self.zone_types is None:
            return True
        return zone_type in self.zone_types
    
    def validate(self, required_rules: List[str]) -> None:
        """
        Валидация наличия обязательных правил.
        
        Args:
            required_rules: Список обязательных ключей в self.rules
            
        Raises:
            ValueError: Если отсутствуют обязательные правила
        """
        missing = [r for r in required_rules if r not in self.rules]
        if missing:
            raise ValueError(
                f"Missing required rules for {self.strategy_name}: {missing}"
            )


def defined_segments(values: "np.ndarray") -> List[tuple]:
    """Полуинтервалы ``[start, stop)``, на которых индикатор **определён**.

    Бар, на котором у индикатора значения нет (разогрев скользящего окна),
    зоной не является — ни одного типа. Это не придирка: знак ``NaN`` ложен для
    любого сравнения, поэтому ``mean() > 0`` на разогреве даёт ``False``, и
    участок, где индикатор ещё не существует, получал уверенную метку ``bear``.
    Пока порог длительности стоял в детекции, такие короткие участки чаще всего
    отсеивались и дефект оставался невидимым; теперь детекция обязана вернуть
    полное мощение, и умолчать об этом больше нельзя.

    Мостится, следовательно, область определения индикатора, а не весь кадр.
    Бары вне её не принадлежат никакой зоне — и это видно по границам.
    """
    import numpy as np

    finite = np.isfinite(np.asarray(values, dtype=float))
    if not finite.any():
        return []

    segments = []
    start = None
    for position, is_finite in enumerate(finite):
        if is_finite and start is None:
            start = position
        elif not is_finite and start is not None:
            segments.append((start, position))
            start = None
    if start is not None:
        segments.append((start, len(finite)))
    return segments


# Экспорт
__all__ = [
    'ZoneDetectionStrategy',
    'ZoneDetectionConfig',
    'defined_segments'
]


