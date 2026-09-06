"""Пресеты порогов свинг-стратегий.

До G64 (2026-09-06) пресеты лежали в ``bquant.core.config`` — слой-основание знал
имена и параметры трёх стратегий анализа, а пайплайн импортировал их оттуда. Пресет —
это знание о стратегиях, и живёт он рядом с ними.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class SwingPreset:
    """Grouping of parameter dictionaries for swing strategies."""

    zigzag: Dict[str, Any]
    find_peaks: Dict[str, Any]
    pivot_points: Dict[str, Any]


#: Пресет по умолчанию. До 0.0.10 им был `wide_zone` (тогда он назывался `default`), и
#: на типичных зонах часового золота две стратегии свингов из трёх не находили при нём
#: **ничего**: его `min_amplitude_pct` — 2% цены при медианном размахе зоны 1.2%, то есть
#: мерка крупнее измеряемого (G35). Умолчание — свойство, а не имя: пресеты названы по
#: ширине зоны, под которую откалиброваны, и какой из них выбран по умолчанию, сказано
#: здесь одной строкой.
DEFAULT_SWING_PRESET = "narrow_zone"

SWING_PRESETS: Dict[str, SwingPreset] = {
    "wide_zone": SwingPreset(
        zigzag={"legs": 10, "deviation": 0.05},
        find_peaks={
            "prominence": 0.015,
            "distance": 5,
            "min_amplitude_pct": 0.02,
        },
        pivot_points={
            "left_bars": 2,
            "right_bars": 2,
            "min_amplitude_pct": 0.015,
        },
    ),
    "narrow_zone": SwingPreset(
        zigzag={"legs": 3, "deviation": 0.008},
        find_peaks={
            "prominence": 0.004,
            "distance": 3,
            "min_amplitude_pct": 0.006,
        },
        pivot_points={
            "left_bars": 2,
            "right_bars": 2,
            "min_amplitude_pct": 0.006,
        },
    ),
}

__all__ = ["SwingPreset", "DEFAULT_SWING_PRESET", "SWING_PRESETS"]
