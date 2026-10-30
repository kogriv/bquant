"""`deviation_pct` — проценты, как читает pandas-ta; подтверждение — свой рычаг (G86).

Что было. Пресеты задавали `deviation=0.008` (`narrow_zone`) и `0.05` (`wide_zone`), и у
нас это была доля: докстрока говорила «0.05 = 5%», `_confirmation_index` считал
`price * (1 ± deviation)`. `pandas_ta.zigzag` читает тот же параметр процентами —
умолчание `5.0`, `current_dev > 0.01 * deviation` в теле, и **знак процента в имени
колонки, которую мы получаем обратно**: `ZIGZAGs_0.008%_3`. Порог обнаружения был
0.008 %, не 0.8 %, а подтверждение применяло 0.8 % — две половины одного детектора в
единицах, различающихся в 100 раз.

Форма правки — назвать правду, сохранить объект. Цифры пресетов не меняются: 0.008 и
0.05 — это то, что библиотека всегда читала, и этот объект измерен в G35/G38/G48/G54 и
принят внешним потребителем. Меняется имя (`deviation_pct`), появляется отдельный порог
подтверждения (`confirmation_retrace_pct`, равный той доле, за которую старый код
принимал `deviation`), и уходит адаптивная половина zigzag — рычаг, измеренный мёртвым.

**Почему улика два месяца лежала на виду.** G16 (22.08) закрывал аудит единиц этого
слоя: zigzag там проверен и помечен галочкой, а таблица результата показывала
`401 | 401 | 401` в трёх конфигурациях — прочитано как «не задет», тогда как это признак
мёртвого рычага. Поэтому первый сторож здесь — **рычаг обязан двигать результат**.

Оракул единицы — имя колонки библиотеки, не наша докстрока: оно печатает число ровно
так, как библиотека его прочла.
"""

from __future__ import annotations

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.analysis.zones.strategies.swing import SWING_PRESETS
from bquant.analysis.zones.strategies.swing.thresholds import (
    AdaptiveSwingStrategy,
    SwingThresholds,
    auto_swing_thresholds,
)
from bquant.analysis.zones.strategies.swing.zigzag import ZigZagSwingStrategy
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


def _points(data, **kwargs):
    return ZigZagSwingStrategy(legs=3, **kwargs).calculate_global(data).swing_points


# --------------------------------------------------------------------------- #
# 1. Единица: то, что мы передали, библиотека печатает со знаком процента
# --------------------------------------------------------------------------- #
def test_the_library_prints_the_number_we_passed_as_a_percent(data):
    """Если бы мы делили или умножали на 100 на границе, имя колонки сказало бы это первым."""
    import pandas_ta as ta

    frame = ta.zigzag(data["high"], data["low"], data["close"], legs=3, deviation=0.008, backtest=True)
    assert any(column.startswith("ZIGZAGs_0.008%_3") for column in frame.columns), list(frame.columns)

    from bquant.indicators import LibraryManager

    ours = LibraryManager.create_indicator(
        "pandas_ta", "zigzag", legs=3,
        deviation=SWING_PRESETS["narrow_zone"].zigzag["deviation_pct"], backtest=True,
    ).calculate(data)
    assert any("0.008%" in column for column in ours.data.columns), list(ours.data.columns)


# --------------------------------------------------------------------------- #
# 2. Рычаг обязан двигать результат — и объект пресета обязан остаться
# --------------------------------------------------------------------------- #
def test_the_lever_moves_the_result_by_more_than_one_pivot(data):
    """Замер 30.10.2026: 0.008 → 402 пивота, 0.8 → 132. G16 видел 401/401/401 и счёл это нормой."""
    shipped = _points(data, deviation_pct=0.008, confirmation_retrace_pct=0.8)
    honest = _points(data, deviation_pct=0.8, confirmation_retrace_pct=0.8)
    assert len(shipped) == 402
    assert len(honest) == 132
    assert len(shipped) - len(honest) > 100


def test_the_preset_object_did_not_move(data):
    """Цифры пресетов те же, объект тот же: 402 пивота и 41 раннее подтверждение из 401 пар —
    числа, выписанные до правки на старом коде."""
    preset = SWING_PRESETS["narrow_zone"].zigzag
    assert preset == {"legs": 3, "deviation_pct": 0.008, "confirmation_retrace_pct": 0.8}
    points = ZigZagSwingStrategy(**preset).calculate_global(data).swing_points
    early = sum(
        1 for a, b in zip(points, points[1:])
        if a.confirmation_index is not None and a.confirmation_index < b.index
    )
    assert len(points) == 402
    assert early == 41


def test_the_pipeline_object_did_not_move(data):
    result = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing="zigzag")
        .with_swing_preset("narrow_zone")
        .analyze()
        .build()
    )
    swings = sum(
        (zone.features or {}).get("metadata", {}).get("swing_metrics", {}).get("num_swings", 0) or 0
        for zone in result.zones
    )
    assert len(result.zones) == 30
    assert swings == 193
    params = result.zones[0].features["metadata"]["swing_metrics"]["strategy_params"]
    assert params == {"legs": 3, "deviation_pct": 0.008, "confirmation_retrace_pct": 0.8}


# --------------------------------------------------------------------------- #
# 3. Подтверждение — свой рычаг, не тот же номер
# --------------------------------------------------------------------------- #
def test_the_confirmation_retrace_is_a_separate_lever(data):
    """Меняем откат, не меняя порог обнаружения: пивоты те же, подтверждения — другие.

    Если бы подтверждение считалось от `deviation_pct` (как до правки — от того же
    числа, принятого за долю), этот тест не отличил бы правку от её отката.
    """
    base = _points(data, deviation_pct=0.008, confirmation_retrace_pct=0.8)
    tighter = _points(data, deviation_pct=0.008, confirmation_retrace_pct=0.2)
    assert [p.index for p in base] == [p.index for p in tighter]
    changed = sum(1 for a, b in zip(base, tighter) if a.confirmation_index != b.confirmation_index)
    assert changed > 100, changed
    assert all(
        b.confirmation_index <= a.confirmation_index
        for a, b in zip(base, tighter)
        if a.confirmation_index is not None and b.confirmation_index is not None
    ), "меньший откат обязан подтверждать не позже, чем больший"


# --------------------------------------------------------------------------- #
# 4. Отказы с названной заменой
# --------------------------------------------------------------------------- #
def test_the_old_name_is_refused_through_the_registry_with_the_replacement_named():
    with pytest.raises(ValueError) as refusal:
        StrategyRegistry.get_swing_strategy("zigzag", legs=3, deviation=0.008)
    message = str(refusal.value)
    assert "deviation_pct" in message and "confirmation_retrace_pct" in message
    assert "0.008" in message and "%" in message


def test_the_old_attribute_is_refused_on_read_and_on_write():
    strategy = ZigZagSwingStrategy(legs=3)
    with pytest.raises(AttributeError, match="deviation_pct"):
        _ = strategy.deviation
    with pytest.raises(AttributeError, match="deviation_pct"):
        strategy.deviation = 0.5


def test_the_adaptive_layer_refuses_zigzag_and_names_what_it_adapts():
    with pytest.raises(ValueError) as refusal:
        AdaptiveSwingStrategy("zigzag", SWING_PRESETS["narrow_zone"].zigzag)
    message = str(refusal.value)
    assert "find_peaks" in message and "pivot_points" in message
    assert "deviation_pct" in message


def test_the_pipeline_refuses_the_toggle_with_zigzag_active(data):
    with pytest.raises(ValueError, match="nothing to adapt"):
        (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_role="line")
            .with_strategies(swing="zigzag")
            .with_auto_swing_thresholds(True)
            .analyze()
            .build()
        )


def test_the_adaptive_layer_no_longer_carries_a_zigzag_threshold(data):
    assert "zigzag_deviation" not in SwingThresholds.__dataclass_fields__
    with pytest.raises(TypeError):
        auto_swing_thresholds(data, base_deviation=0.01, amplitude_k=0.3)  # type: ignore[call-arg]
    thresholds = auto_swing_thresholds(data, amplitude_k=0.3)
    assert 0 < thresholds.min_amplitude_pct < 1


# --------------------------------------------------------------------------- #
# 5. G87: ноль — не «без порога», а чужое умолчание под нашим именем
# --------------------------------------------------------------------------- #
def test_the_library_substitutes_its_default_for_zero(data):
    """Факт о библиотеке, на котором стоит отказ ниже: `deviation=0.0` → 5.0 %."""
    import pandas_ta as ta

    frame = ta.zigzag(data["high"], data["low"], data["close"], legs=3, deviation=0.0, backtest=True)
    assert any(column.startswith("ZIGZAGs_5.0%_3") for column in frame.columns), list(frame.columns)


@pytest.mark.parametrize("value", [0.0, -0.5])
def test_a_non_positive_threshold_is_refused_naming_the_substitution(value):
    with pytest.raises(ValueError) as refusal:
        ZigZagSwingStrategy(legs=3, deviation_pct=value)
    message = str(refusal.value)
    assert "5.0" in message and "ZIGZAGs_5.0%_3" in message


def test_direct_construction_with_the_old_name_names_the_replacement_and_the_rule():
    """Потребитель строит стратегию напрямую, не через реестр; голый TypeError там не
    назвал бы ни замену, ни правило побитового переноса."""
    with pytest.raises(ValueError) as refusal:
        ZigZagSwingStrategy(legs=3, deviation=0.008)
    message = str(refusal.value)
    assert "deviation_pct" in message
    assert "100" in message and "confirmation_retrace_pct=0.8" in message


def test_an_unknown_keyword_is_still_a_type_error():
    with pytest.raises(TypeError):
        ZigZagSwingStrategy(legs=3, legz=4)  # type: ignore[call-arg]


def test_the_dataclass_surface_survived_the_custom_init():
    a = ZigZagSwingStrategy(legs=3, deviation_pct=0.008, confirmation_retrace_pct=0.8)
    b = ZigZagSwingStrategy(legs=3, deviation_pct=0.008, confirmation_retrace_pct=0.8)
    assert a == b
    assert repr(a) == "ZigZagSwingStrategy(legs=3, deviation_pct=0.008, confirmation_retrace_pct=0.8)"
