"""
Zero Crossing Detection Strategy

Стратегия детекции зон по пересечению индикатором нулевой линии.

Применение:
- MACD histogram
- Awesome Oscillator (AO)
- CCI (Commodity Channel Index)
- Любой осциллятор с нулевой линией
"""

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig, defined_segments
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo, ZoneType
from bquant.core.logging_config import get_logger


@ZoneDetectionRegistry.register(
    'zero_crossing',
    description='Detect bull/bear zones by indicator crossing zero line',
    supported_zones=[
        # Пересечение нуля: гистограмма выше нуля — приподнятое состояние ряда,
        # ниже — подавленное. Полярность объявляется про ось индикатора, а не
        # про направление цены (см. ZoneType.polarity).
        ZoneType('bull', polarity=+1, counterpart='bear', label='Bullish'),
        ZoneType('bear', polarity=-1, counterpart='bull', label='Bearish'),
    ],
    required_rules=['indicator_col']
)
class ZeroCrossingDetection:
    """
    Стратегия: детекция зон по пересечению нулевой линии.
    
    Применение:
        - MACD histogram
        - Awesome Oscillator (AO)
        - CCI (Commodity Channel Index)
        - любой осциллятор с нулевой линией
        
    Правила (config.rules):
        - indicator_col: str (обязательно) - название колонки индикатора
        - smooth_window: int (опционально) - сглаживание перед детекцией
        
    Типы зон:
        - 'bull': индикатор > 0
        - 'bear': индикатор < 0
    
    Example:
        strategy = ZeroCrossingDetection()
        config = ZoneDetectionConfig(
            zone_types=['bull', 'bear'],
            rules={'indicator_col': 'macd_12_26_9__hist'}
        )
        zones = strategy.detect_zones(data, config)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """
        Обнаружить зоны по пересечению нуля.
        
        Алгоритм:
        1. Извлечь колонку индикатора
        2. Опционально сгладить
        3. Найти знаковые переходы (+ -> -, - -> +)
        4. Создать ZoneInfo для каждой зоны

        Зоны мостят **область определения** индикатора: между сменами знака нет
        ничего, что можно было бы не отнести ни к одной зоне, а бары разогрева,
        где значения ещё нет, не принадлежат никакой. Порог длительности здесь
        не применяется — он фильтр отчётности, см. :class:`ZoneDetectionConfig`.

        Args:
            data: DataFrame с OHLCV + индикаторами
            config: Конфигурация правил детекции
            
        Returns:
            List[ZoneInfo] - список обнаруженных зон
        """
        # Валидация
        config.validate(required_rules=['indicator_col'])
        
        indicator_col = config.rules['indicator_col']
        if indicator_col not in data.columns:
            raise ValueError(
                f"Indicator column '{indicator_col}' not found in data. "
                f"Available: {list(data.columns)}"
            )
        
        df = data.copy()
        indicator_values = df[indicator_col].values
        
        # Опциональное сглаживание
        smooth_window = config.rules.get('smooth_window')
        if smooth_window and smooth_window > 1:
            indicator_values = pd.Series(indicator_values).rolling(
                window=smooth_window, 
                center=False
            ).mean().values
            self.logger.debug(f"Applied smoothing: window={smooth_window}")
        
        # Мостим область определения индикатора, а не весь кадр: на разогреве
        # значения нет, и знака у него тоже нет.
        segments = defined_segments(indicator_values)
        if not segments:
            self.logger.warning(
                "Indicator '%s' has no defined values; no zones", indicator_col
            )
            return []

        undefined_bars = len(df) - sum(stop - start for start, stop in segments)
        if undefined_bars:
            self.logger.info(
                "%d of %d bars carry no value for '%s' (warm-up); they belong "
                "to no zone.", undefined_bars, len(df), indicator_col
            )

        # Границы считаются **внутри** каждого сегмента: пара «конец одного —
        # начало следующего» зоной не является, между ними индикатора нет.
        spans = []
        for seg_start, seg_stop in segments:
            signs = np.sign(indicator_values[seg_start:seg_stop])
            signs[signs == 0] = 1  # 0 считаем как положительное
            changes = (np.where(np.diff(signs) != 0)[0] + 1 + seg_start).tolist()
            edges = [seg_start, *changes, seg_stop]
            spans.extend(zip(edges, edges[1:]))

        if len(spans) == 1:
            self.logger.warning("No zero crossings found")

        zones = []
        for start_idx, stop_idx in spans:
            end_idx = stop_idx - 1
            duration = end_idx - start_idx + 1

            # Определить тип зоны
            zone_mean_value = indicator_values[start_idx:end_idx + 1].mean()
            zone_type = 'bull' if zone_mean_value > 0 else 'bear'

            # Фильтр по типам зон
            if not config.accepts(zone_type):
                continue

            # Создать ZoneInfo
            zone_data = df.iloc[start_idx:end_idx + 1].copy()

            zone = ZoneInfo(
                zone_id=len(zones),
                type=zone_type,
                start_idx=start_idx,
                end_idx=end_idx,
                start_time=df.index[start_idx],
                end_time=df.index[end_idx],
                duration=duration,
                data=zone_data,
                indicator_context={
                    'detection_strategy': 'zero_crossing',
                    'detection_indicator': indicator_col,
                    'signal_line': None,
                    'detection_rules': config.rules
                }
            )
            zones.append(zone)

        self.logger.info(
            f"Detected {len(zones)} zones: "
            f"{sum(1 for z in zones if z.type == 'bull')} bull, "
            f"{sum(1 for z in zones if z.type == 'bear')} bear"
        )
        
        return zones


# Экспорт
__all__ = [
    'ZeroCrossingDetection'
]

