"""Кросс одного уровня: `upper == lower`, и бар ровно на уровне сторону не меняет.

Заявка bquant#121 от внешнего потребителя: `threshold` не умел выразить пересечение
**одного** уровня — «RSI относительно 50». Полоса 55/45 рядом, но это не то же самое:
между порогами появляется `neutral`, и на их данных в зонах оставалось 67 % ленты
против 97 % у честного кросса. Форма выбрана владельцем (форма 1 заявки): `upper == lower`
означает ровно кросс уровня, отказ остаётся для `upper < lower`.

**Правило ничьей — каузальное, и оно здесь главное.** Бар ровно на уровне остаётся в
зоне предыдущего бара; касание сторону не переключает. Строгий порог без памяти
(`>= level` вверх) тоже был приемлем для потребителя, но тогда их советник и пакет
расходились бы ровно на касании — а побарное совпадение с эталонной реализацией и есть
то, зачем заявка заведена. Замерено 30.10.2026 (уровень 50): на полной точности колонки
ничьих нет вовсе и обе формы дают 107 зон, на целочисленной сетке строгий порог дробит
зоны на 12–20 %.

**Почему проверки синтетические.** На встроенных датасетах при полной точности колонки
ничьих **нуль** — проверка правила ничьей на них не проверяет правило вовсе, это
вакуумный зелёный. Поэтому кадры строятся вручную, а число ничьих в них утверждается
отдельной проверкой: фикстура, в которой ничья пропала, обязана валить тест, а не
тихо делать его бессмысленным.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones.detection.base import ZoneDetectionConfig
from bquant.analysis.zones.detection.threshold import ThresholdDetection
from bquant.data.samples import get_sample_data

LEVEL = 50.0

#: Ряд с тремя касаниями уровня: два внутри зоны и одно на переломе.
#: Ожидаемые стороны выписаны рядом, чтобы расхождение читалось без отладчика.
SERIES_WITH_TIES = [
    (60.0, 'overbought'),
    (50.0, 'overbought'),   # касание: сторона предыдущего бара
    (55.0, 'overbought'),
    (40.0, 'oversold'),
    (50.0, 'oversold'),     # касание сразу после перелома: по-прежнему предыдущая
    (50.0, 'oversold'),     # два касания подряд
    (45.0, 'oversold'),
    (70.0, 'overbought'),
]


def _frame(values: list[float]) -> pd.DataFrame:
    """Минимальный кадр: детекции нужны индекс и колонка индикатора."""
    index = pd.date_range('2026-01-01', periods=len(values), freq='1h')
    return pd.DataFrame(
        {
            'open': 1.0, 'high': 1.0, 'low': 1.0, 'close': 1.0, 'volume': 1.0,
            'osc': values,
        },
        index=index,
    )


def _detect(values: list[float], *, level: float = LEVEL, zone_types=None):
    config = ZoneDetectionConfig(
        zone_types=zone_types,
        rules={
            'indicator_col': 'osc',
            'upper_threshold': level,
            'lower_threshold': level,
        },
        strategy_name='threshold',
    )
    return ThresholdDetection().detect_zones(_frame(values), config)


def _side_per_bar(values: list[float], **kwargs) -> list:
    """Сторона каждого бара по зонам: `None` там, где бар не в зоне.

    Собирается из зон, а не из внутренностей классификатора: проверять надо то,
    что увидит читатель результата.
    """
    sides: list = [None] * len(values)
    for zone in _detect(values, **kwargs):
        for position in range(zone.start_idx, zone.end_idx + 1):
            sides[position] = zone.type
    return sides


# --------------------------------------------------------------------------- #
# 1. Положительный контроль фикстур: ничьи в них есть
# --------------------------------------------------------------------------- #
def test_the_fixture_actually_contains_ties():
    """Без ничьих все проверки ниже зелены на любом правиле ничьей."""
    values = [value for value, _ in SERIES_WITH_TIES]
    assert values.count(LEVEL) == 3, "фикстура потеряла касания уровня"


def test_the_sample_data_contains_no_ties_which_is_why_fixtures_are_synthetic():
    """Замер, из-за которого проверки не на реальных данных.

    Полная точность колонки делает ничью недостижимой практически: 0 баров ровно
    на 50.0 из 1000. Если это однажды перестанет быть правдой, проверка покраснеет
    и скажет, что синтетика больше не единственный способ увидеть ничью.
    """
    column = get_sample_data('tv_xauusd_1h')['rsi'].to_numpy(dtype=float)
    assert int(np.sum(column == LEVEL)) == 0


# --------------------------------------------------------------------------- #
# 2. Сам режим: upper == lower больше не отказ
# --------------------------------------------------------------------------- #
def test_equal_thresholds_detect_zones_instead_of_refusing():
    zones = _detect([60.0, 40.0, 60.0])
    assert [zone.type for zone in zones] == ['overbought', 'oversold', 'overbought']


def test_level_crossing_produces_no_neutral_zone_and_covers_the_whole_band():
    """Два типа и полное мощение — ровно то, чего потребителю не хватало."""
    values = [value for value, _ in SERIES_WITH_TIES]
    zones = _detect(values)

    assert {zone.type for zone in zones} == {'overbought', 'oversold'}
    assert sum(zone.duration for zone in zones) == len(values)


def test_the_measured_number_of_zones_on_sample_data():
    """Число из пред-регистрации: замер вне пакета дал 107 до правки.

    Утверждение здесь — не «107 вообще», а «пакет считает то же, что независимый
    замер»: именно это расхождение и ловится, если классификация поедет.
    """
    data = get_sample_data('tv_xauusd_1h')
    config = ZoneDetectionConfig(
        zone_types=None,
        rules={'indicator_col': 'rsi', 'upper_threshold': LEVEL,
               'lower_threshold': LEVEL},
        strategy_name='threshold',
    )
    zones = ThresholdDetection().detect_zones(data, config)

    assert len(zones) == 107
    assert sum(zone.duration for zone in zones) == len(data)
    assert not [zone for zone in zones if zone.type == 'neutral']


def test_the_mode_and_the_tie_rule_are_readable_from_the_zone():
    """Правило ничьей — часть того, как зона получена, и должно читаться из неё."""
    zone = _detect([60.0, 50.0, 40.0])[0]
    assert zone.indicator_context['threshold_mode'] == 'level'
    assert zone.indicator_context['tie_rule'] == 'previous_side'


def test_a_band_still_declares_itself_a_band():
    data = get_sample_data('tv_xauusd_1h')
    config = ZoneDetectionConfig(
        zone_types=None,
        rules={'indicator_col': 'rsi', 'upper_threshold': 70, 'lower_threshold': 30},
        strategy_name='threshold',
    )
    zones = ThresholdDetection().detect_zones(data, config)

    assert zones[0].indicator_context['threshold_mode'] == 'band'
    assert zones[0].indicator_context['tie_rule'] is None
    assert [zone for zone in zones if zone.type == 'neutral']


# --------------------------------------------------------------------------- #
# 3. Правило ничьей
# --------------------------------------------------------------------------- #
def test_a_bar_on_the_level_keeps_the_previous_bars_side():
    values = [value for value, _ in SERIES_WITH_TIES]
    expected = [side for _, side in SERIES_WITH_TIES]
    assert _side_per_bar(values) == expected


def test_a_touch_does_not_cut_a_one_bar_zone():
    """Касание внутри зоны не обязано её разрезать — иначе зачем память.

    Касание берётся внутри **нижней** зоны намеренно. Первая версия этой проверки
    стояла внутри верхней (`60, 50, 55`), и строгий порог без памяти (`>= level`
    вверх) оставлял её зелёной: там он с памятью совпадает. Проверка, зелёная на
    том правиле, против которого заведена, не проверяет своего утверждения —
    тот же урок, что на мутации M1 в G84.
    """
    zones = _detect([40.0, 50.0, 45.0])
    assert len(zones) == 1
    assert zones[0].duration == 3


def test_bars_before_the_first_move_off_the_level_belong_to_no_zone():
    """Приписать голове сторону значило бы её выдумать: предыдущей зоны нет."""
    values = [50.0, 50.0, 60.0, 40.0]
    assert _side_per_bar(values) == [None, None, 'overbought', 'oversold']


def test_a_series_entirely_on_the_level_yields_no_zones_at_all():
    """Нуль зон, а не одна пустая: сторону не из чего вывести ни для одного бара."""
    assert _detect([50.0, 50.0, 50.0]) == []


def test_memory_does_not_reach_across_a_gap_in_the_indicator():
    """За разрывом предыдущего бара нет, и догадка через пропуск — не память.

    Бар, на котором индикатора нет, зоной не является (разогрев окна); ничья
    сразу за ним наследовать не от кого.
    """
    values = [60.0, 55.0, float('nan'), 50.0, 45.0]
    assert _side_per_bar(values) == [
        'overbought', 'overbought', None, None, 'oversold'
    ]


# --------------------------------------------------------------------------- #
# 4. Где отказ обязан прозвучать
# --------------------------------------------------------------------------- #
def test_upper_below_lower_is_still_refused():
    with pytest.raises(ValueError, match=r"upper_threshold \(30\) must be >="):
        _detect_with(upper=30, lower=70)


def test_asking_for_neutral_in_level_mode_is_refused_with_the_replacement_named():
    """Пустой успешный результат здесь был бы той же породой, что G19.

    Нейтральных зон в режиме уровня не бывает по построению. Отказ обязан назвать
    замену — полосу, — а не просто вернуть ноль зон и выглядеть успехом.
    """
    with pytest.raises(ValueError) as refusal:
        _detect([60.0, 40.0], zone_types=['overbought', 'neutral', 'oversold'])

    message = str(refusal.value)
    assert 'neutral' in message
    assert 'upper_threshold > lower_threshold' in message


def _detect_with(*, upper: float, lower: float):
    config = ZoneDetectionConfig(
        zone_types=None,
        rules={'indicator_col': 'osc', 'upper_threshold': upper,
               'lower_threshold': lower},
        strategy_name='threshold',
    )
    return ThresholdDetection().detect_zones(_frame([60.0, 40.0]), config)
