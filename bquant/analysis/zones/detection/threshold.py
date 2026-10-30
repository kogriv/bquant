"""
Threshold Detection Strategy

Стратегия детекции зон по пересечению порогов индикатора.

Применение:
- RSI (upper=70, lower=30)
- Stochastic (upper=80, lower=20)
- Williams %R
- RSI относительно середины (upper=lower=50) — кросс **одного** уровня, см.
  ``_classify_by_level`` и раздел «Кросс одного уровня» в
  ``docs/user_guide/zone_analysis.md``
"""

import pandas as pd
import numpy as np
from typing import List

from .base import ZoneDetectionStrategy, ZoneDetectionConfig, defined_segments
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo, ZoneType
from bquant.core.logging_config import get_logger


def _classify_by_level(values: np.ndarray, level: float) -> np.ndarray:
    """Классификация по кроссу **одного** уровня: ``> level`` / ``< level``.

    Правило ничьей (бар ровно на уровне) — каузальное: **бар на уровне остаётся
    в зоне предыдущего бара**, касание уровня сторону не переключает. Пока
    значение не ушло с уровня ни разу, бар не принадлежит ни одной зоне — тем же
    путём, которым ей не принадлежит бар разогрева индикатора (``None`` в массиве
    классов), и по той же причине: приписать ему сторону значило бы её выдумать.

    Память не переходит через участок, где индикатора нет: сторона наследуется от
    предыдущего бара **того же** участка определённости. За разрывом предыдущего
    бара нет, а «последняя известная сторона» из прошлого участка — не предыдущий
    бар, а догадка через пропуск. Это уточнение правила потребителя, а не его буква;
    сверено с ним 2026-10-30 — у его эталонной реализации пропуск сторону тоже
    сбрасывает, то есть уточнение совпало, а не разошлось молча.

    Выбор формы — заявка bquant#121: у внешнего потребителя лента режется по
    уровню последовательно, и бар на уровне у него тоже не переключает сторону.
    Строгий порог без памяти (``>= level`` вверх) дал бы расхождение с его
    эталонной реализацией ровно на касании; замерено (30.10.2026, уровень 50): на
    полной точности колонки ничьих нет вовсе и формы совпадают (107 зон на
    ``tv_xauusd_1h``), на целочисленной сетке строгий порог дробит зоны на 12–20 %.

    Асимметрии «какая сторона забирает уровень» здесь нет вообще — её заменяет
    порядок баров, и это свойство каузально: ответ по бару зависит только от него
    и от прошлых баров. Цена названа: классификация перестаёт быть локальной —
    на срезе ряда, начинающемся прямо с бара на уровне, тот же бар получит
    ``None`` вместо стороны.
    """
    classes = np.empty(len(values), dtype=object)
    for start, stop in defined_segments(values):
        chunk = np.asarray(values[start:stop], dtype=float)
        sides = pd.Series([None] * len(chunk), dtype=object)
        sides[chunk > level] = 'overbought'
        sides[chunk < level] = 'oversold'
        # ffill() переносит сторону на бары ровно на уровне; голова участка, где
        # переносить ещё нечего, остаётся None — это отсутствие зоны, не тип.
        classes[start:stop] = sides.ffill().to_numpy(dtype=object)
    return classes


@ZoneDetectionRegistry.register(
    'threshold',
    description='Detect zones by indicator crossing upper/lower thresholds',
    supported_zones=[
        # Три полосы осциллятора. Нейтральная объявлена наравне с сигнальными:
        # без неё зоны покрывают лишь часть таймлайна и соседние зоны перестают
        # примыкать, а анализ последовательностей читает соседние элементы как
        # переход (замер: devref/gaps/detection/g19_*.md).
        ZoneType('overbought', polarity=+1, counterpart='oversold', label='Overbought'),
        ZoneType('neutral', polarity=0, label='Neutral'),
        ZoneType('oversold', polarity=-1, counterpart='overbought', label='Oversold'),
    ],
    required_rules=['indicator_col', 'upper_threshold', 'lower_threshold']
)
class ThresholdDetection:
    """
    Стратегия: детекция зон по порогам.
    
    Применение:
        - RSI (upper=70, lower=30)
        - Stochastic (upper=80, lower=20)
        - Williams %R
        
    Правила (config.rules):
        - indicator_col: str (обязательно)
        - upper_threshold: float (обязательно) - верхняя граница
        - lower_threshold: float (обязательно) - нижняя граница

    Типы зон (полоса, ``upper > lower``):
        - 'overbought': индикатор > upper_threshold
        - 'neutral': lower_threshold <= индикатор <= upper_threshold
        - 'oversold': индикатор < lower_threshold

    Два режима, и их различает ``upper_threshold`` против ``lower_threshold``:

        - **полоса** (``upper > lower``) — три типа зон, как выше;
        - **кросс одного уровня** (``upper == lower``) — два типа, ``neutral`` не
          порождается ни одной зоной: каждый бар выше или ниже уровня. Бар ровно
          на уровне остаётся в зоне предыдущего бара (``_classify_by_level``).

    ``upper < lower`` отказывает: полосой это не читается ни в каком порядке.

    Example:
        strategy = ThresholdDetection()
        config = ZoneDetectionConfig(
            zone_types=['overbought', 'oversold'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 70,
                'lower_threshold': 30
            }
        )
        zones = strategy.detect_zones(data, config)

        # RSI относительно середины: кросс одного уровня, neutral не бывает
        config = ZoneDetectionConfig(
            zone_types=['overbought', 'oversold'],
            rules={
                'indicator_col': 'rsi',
                'upper_threshold': 50,
                'lower_threshold': 50
            }
        )
        zones = strategy.detect_zones(data, config)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Обнаружить зоны по порогам."""
        # Валидация
        config.validate(
            required_rules=['indicator_col', 'upper_threshold', 'lower_threshold'],
            # `smooth_window` здесь не объявлен намеренно (G85): объявлялся, но не
            # читался — вызов проходил, сглаживания не было. Отказ с заменой в
            # `RETIRED_RULES`.
            optional_rules=(),
        )
        
        indicator_col = config.rules['indicator_col']
        upper = config.rules['upper_threshold']
        lower = config.rules['lower_threshold']
        
        if upper < lower:
            raise ValueError(
                f"upper_threshold ({upper}) must be >= lower_threshold ({lower}). "
                f"Equal values are the single-level crossing mode; "
                f"upper < lower is not a band in any reading."
            )

        level_mode = upper == lower

        if level_mode and 'neutral' in (config.zone_types or ()):
            raise ValueError(
                "Single-level crossing (upper_threshold == lower_threshold == "
                f"{upper}) produces no 'neutral' zones: every bar is above or "
                "below the level, and a bar exactly on it keeps the previous "
                "bar's side. Ask for ['overbought', 'oversold'], or use a band "
                "(upper_threshold > lower_threshold) — that is the form that "
                "produces neutral zones."
            )

        if indicator_col not in data.columns:
            raise ValueError(f"Indicator column '{indicator_col}' not found")

        df = data.copy()
        indicator_values = df[indicator_col].values

        # Классификация по порогам
        if level_mode:
            zone_classes = _classify_by_level(indicator_values, upper)
        else:
            zone_classes = np.empty(len(indicator_values), dtype=object)
            zone_classes[indicator_values > upper] = 'overbought'
            zone_classes[indicator_values < lower] = 'oversold'
            zone_classes[(indicator_values >= lower) & (indicator_values <= upper)] = 'neutral'

        # Найти границы зон (смены класса)
        class_changes = np.where(
            np.concatenate([[True], zone_classes[1:] != zone_classes[:-1]])
        )[0]
        boundaries = np.concatenate([class_changes, [len(df)]])
        
        zones = []
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1] - 1
            duration = end_idx - start_idx + 1
            
            zone_type = zone_classes[start_idx]

            # `np.empty(dtype=object)` заполняется None, и позиции, где у
            # индикатора нет значения, ни одному из трёх сравнений не
            # удовлетворяют — там так и остаётся None. Это не четвёртый тип
            # зоны, а отсутствие зоны: бар разогрева не «нейтрален», индикатора
            # на нём просто нет. Пока порог длительности стоял в детекции,
            # короткий разогрев отсеивался и типа-None никто не видел.
            if zone_type is None:
                continue

            if not config.accepts(zone_type):
                continue

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
                    'detection_strategy': 'threshold',
                    'detection_indicator': indicator_col,
                    'signal_line': None,
                    'thresholds': {
                        'upper': upper,
                        'lower': lower
                    },
                    # Режим читается из зоны, а не выводится заново из порогов:
                    # правило ничьей — часть того, как зона получена, и читателю
                    # отпечатка зоны нужно знать, какое оно было.
                    'threshold_mode': 'level' if level_mode else 'band',
                    'tie_rule': 'previous_side' if level_mode else None,
                    'detection_rules': config.rules
                }
            )
            zones.append(zone)
        
        self.logger.info(
            f"Detected {len(zones)} zones: "
            f"OB={sum(1 for z in zones if z.type == 'overbought')}, "
            f"N={sum(1 for z in zones if z.type == 'neutral')}, "
            f"OS={sum(1 for z in zones if z.type == 'oversold')}"
        )
        
        return zones


# Экспорт
__all__ = [
    'ThresholdDetection'
]

