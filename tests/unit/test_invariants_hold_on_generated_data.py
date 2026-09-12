"""Правила пакета проверяются формами, которых автор теста не придумал.

Инварианты у нас объявлены и вшиты в модели (G66, G70, G72): зона не может кончаться
раньше, чем началась; длительность обязана сойтись с границами; точки свинг-контекста
отсортированы и совпадают с индексами; ось времени возрастающая и уникальная; в цене нет
дыр. Проверялись они до сих пор **придуманными** входами — встроенными сэмплами и
синтетическими кадрами, которые кто-то сел и сочинил.

Насколько этого мало, показал G72: из восьми придуманных «странных» входов три нашли
дефекты — и придуманы они были только потому, что кто-то догадался их придумать.

Здесь входы генерируются: длина, волатильность, плоские участки, разрывы во времени,
таймфрейм, часовой пояс. Правила те же — **новых свойств этот файл не объявляет**, он
бьёт по уже объявленным. Контрпример печатается минимальным (это делает `hypothesis`),
seed фиксирован, поэтому красный тест воспроизводится.

Бюджет: по умолчанию мало примеров, чтобы сьют не удлинялся вдвое; широкий поиск — под
меткой `slow`, его зовёт релизный гейт и недельный прогон на свежем разрешении.

**Про воспроизводимость — раздельно, потому что это два разных режима.** У бюджета по
умолчанию `derandomize=True`: набор примеров один и тот же, красное воспроизводится. У
широкого поиска `derandomize=False` намеренно — он затем и широкий, чтобы каждый прогон
пробовал новые формы. Цена в том, что его находка **не воспроизводится повторным запуском**,
и если процесс умирает жёстко (а он умеет: `pandas-ta` уводит интерпретатор в abort изнутри
скомпилированного кода, и `except Exception` такого не ловит), вместе с процессом погибает и
контрпример. Поэтому широкий поиск **выгружает каждый пробуемый кадр на диск** до проверки —
см. `_record_wide_example`. Разбор: `devref/gaps/validation/g82_…`.


Разбор и рамка: `devref/architecture/property_based_invariants_backlog_2026-09.md`.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.models import SwingContext, ZoneInfo

# Прогон пайплайна — это секунды, а не микросекунды: дедлайн снят намеренно, число
# примеров мало по умолчанию. Иначе тест либо мигает по таймауту, либо удлиняет сьют.
BUDGET = settings(
    max_examples=12,
    deadline=None,
    derandomize=True,  # один и тот же набор примеров: красное воспроизводится
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
WIDE = settings(
    max_examples=120,
    deadline=None,
    derandomize=False,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)


def _record_wide_example(frame):
    """Записать пробуемый кадр на диск до проверки — иначе жёсткая смерть не оставит следа.

    Файл перезаписывается на каждом примере: нужен **последний**, тот, на котором процесс
    умер. Запись идёт в файл, а не в `print`, потому что захваченный pytest'ом вывод при
    `abort()` теряется вместе с процессом; и с `flush`, потому что буфер тоже.

    Путь берётся из `BQUANT_WIDE_EXAMPLE_DUMP`, чтобы CI выгрузил его как артефакт.
    Без переменной запись не делается: в обычном локальном прогоне мусор в дереве не нужен.
    """
    target = os.environ.get("BQUANT_WIDE_EXAMPLE_DUMP")
    if not target:
        return
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        frame.to_csv(fh)
        fh.flush()
        os.fsync(fh.fileno())


def build_frame(n, start_price, volatility, flat_from, freq, timezone, drop_share, seed):
    """Допустимый OHLCV — и только допустимый.

    Генератор, который строит `low > high`, ловит сам себя, а не пакет: такого кадра не
    бывает, и отказ на нём ничего не доказывает. Поэтому `high`/`low` выводятся из
    `open`/`close`, а не бросаются независимо.

    Отдельная функция, а не тело стратегии, ради положительного контроля ниже: тот же
    построитель зовётся с явными параметрами, и по нему видно, что генератор даёт работу,
    а не пустоту.
    """
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, volatility, size=n)
    steps[flat_from:] = 0.0  # хвост без движения: вырожденный участок — законный вход
    close = start_price * np.exp(np.cumsum(steps))
    open_ = np.concatenate([[start_price], close[:-1]])
    spread = np.abs(rng.normal(0.0, volatility, size=n)) * close

    frame = pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": rng.integers(1, 10_000, size=n).astype(float),
        },
        index=pd.date_range("2024-01-01", periods=n, freq=freq, tz=timezone),
    )

    # Разрывы: выходные, отключения, дыры в выгрузке. Ось остаётся возрастающей и
    # уникальной — это контракт (G72), а не свойство генератора.
    if drop_share > 0:
        keep = rng.random(n) >= drop_share
        keep[0] = keep[-1] = True
        frame = frame[keep]

    return frame


@st.composite
def ohlcv_frames(draw, min_bars=60, max_bars=260):
    """Параметры бросаются, кадр строит `build_frame`."""
    n = draw(st.integers(min_value=min_bars, max_value=max_bars))
    return build_frame(
        n=n,
        start_price=draw(st.floats(min_value=10.0, max_value=5000.0, allow_nan=False)),
        volatility=draw(st.floats(min_value=0.0, max_value=0.02, allow_nan=False)),
        flat_from=draw(st.integers(min_value=0, max_value=n)),
        freq=draw(st.sampled_from(["15min", "1h", "4h", "1D"])),
        timezone=draw(st.sampled_from([None, "UTC", "Europe/Moscow"])),
        drop_share=draw(st.floats(min_value=0.0, max_value=0.2, allow_nan=False)),
        seed=draw(st.integers(min_value=0, max_value=2**16)),
    )


def _run(frame):
    return (
        analyze_zones(frame)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing="zigzag")
        .with_cache(enable=False)
        .analyze(clustering=False)
        .build()
    )


def _check_zone_invariants(result, frame):
    """Те же правила, что объявлены в моделях, — на этих данных."""
    bars = len(result.data) if result.data is not None else len(frame)

    previous_end = None
    for zone in result.zones:
        assert 0 <= zone.start_idx <= zone.end_idx < bars, (
            f"зона {zone.zone_id} вышла за границы кадра: "
            f"[{zone.start_idx}, {zone.end_idx}] при {bars} барах"
        )
        assert zone.duration == zone.end_idx - zone.start_idx + 1, (
            f"зона {zone.zone_id}: duration={zone.duration}, "
            f"а границы дают {zone.end_idx - zone.start_idx + 1}"
        )
        assert zone.start_time <= zone.end_time, f"зона {zone.zone_id} кончается раньше начала"

        # Зоны не перекрываются и идут по возрастанию: мощение, а не набор отрезков.
        if previous_end is not None:
            assert zone.start_idx > previous_end, (
                f"зона {zone.zone_id} начинается на {zone.start_idx}, "
                f"а предыдущая кончилась на {previous_end}"
            )
        previous_end = zone.end_idx

    assert sum(z.duration for z in result.zones) <= bars, (
        "сумма длительностей зон больше, чем баров в кадре"
    )


@given(frame=ohlcv_frames())
@BUDGET
def test_zone_invariants_hold_on_generated_frames(frame):
    """Ни один сгенерированный кадр не должен рождать зону, противоречащую себе."""
    _check_zone_invariants(_run(frame), frame)


@given(frame=ohlcv_frames())
@BUDGET
def test_swings_of_a_zone_are_addressable_in_the_frame(frame):
    """Свинг зоны обязан указывать на бар, который в кадре есть."""
    result = _run(frame)
    bars = len(result.data) if result.data is not None else len(frame)

    for zone in result.zones:
        metrics = (zone.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}
        count = metrics.get("num_swings", 0)
        assert count >= 0
        # Нулевые свинги законны, но тогда причина названа или её нет намеренно (G70).
        if count == 0:
            assert metrics.get("degraded") in (None, "too_short", "degenerate", "detector_unavailable")

    context = getattr(result, "global_swing_context", None)
    if isinstance(context, SwingContext) and context.swing_points:
        assert list(context.indices) == sorted(context.indices)
        assert len(context.indices) == len(context.swing_points)
        assert all(0 <= int(i) < bars for i in context.indices)


@given(frame=ohlcv_frames())
@BUDGET
def test_the_result_never_claims_more_zones_than_it_carries(frame):
    """Сводка и список зон обязаны говорить одно и то же."""
    result = _run(frame)
    metadata = result.metadata or {}

    assert metadata.get("total_zones") == len(result.zones)
    declared = set(metadata.get("zone_types") or [])
    assert declared == {zone.type for zone in result.zones}


@given(
    frame=ohlcv_frames(min_bars=40, max_bars=120),
    hole_at=st.floats(min_value=0.0, max_value=0.99),
)
@BUDGET
def test_a_hole_in_the_price_is_refused_wherever_it_lands(frame, hole_at):
    """Контракт G72 не зависит от того, куда попала дыра."""
    holed = frame.copy()
    position = int(hole_at * (len(holed) - 1))
    holed.iloc[position, holed.columns.get_loc("close")] = np.nan

    with pytest.raises(ValueError, match="missing values"):
        _run(holed)


@given(frame=ohlcv_frames(min_bars=40, max_bars=120), seed=st.integers(0, 2**16))
@BUDGET
def test_an_unsorted_frame_is_refused_wherever_it_is_broken(frame, seed):
    """То же для оси времени: перестановка любых двух баров — отказ."""
    if len(frame) < 3:
        return
    rng = np.random.default_rng(seed)
    order = list(range(len(frame)))
    i = int(rng.integers(0, len(order) - 1))
    order[i], order[i + 1] = order[i + 1], order[i]

    with pytest.raises(ValueError, match="not sorted"):
        _run(frame.iloc[order])


@given(
    start=st.integers(min_value=0, max_value=1000),
    length=st.integers(min_value=1, max_value=500),
    wrong_duration=st.integers(min_value=-5, max_value=5),
)
@settings(max_examples=200, deadline=None, derandomize=True)
def test_the_zone_model_rejects_numbers_that_contradict_each_other(start, length, wrong_duration):
    """Быстрая часть: инвариант модели без прогона пайплайна."""
    end = start + length - 1
    honest = ZoneInfo(
        zone_id=0,
        type="bull",
        start_idx=start,
        end_idx=end,
        duration=length,
        start_time=pd.Timestamp("2024-01-01"),
        end_time=pd.Timestamp("2024-01-02"),
        data=pd.DataFrame(),
    )
    assert honest.duration == honest.end_idx - honest.start_idx + 1

    if wrong_duration == 0:
        return
    with pytest.raises(ValueError):
        ZoneInfo(
            zone_id=0,
            type="bull",
            start_idx=start,
            end_idx=end,
            duration=length + wrong_duration,
            start_time=pd.Timestamp("2024-01-01"),
            end_time=pd.Timestamp("2024-01-02"),
            data=pd.DataFrame(),
        )


@pytest.mark.slow
@given(frame=ohlcv_frames())
@WIDE
def test_zone_invariants_hold_on_a_wide_search(frame):
    """Широкий поиск: тот же предмет, больше форм. Зовётся гейтом и недельным прогоном."""
    _record_wide_example(frame)
    _check_zone_invariants(_run(frame), frame)


def test_the_generator_gives_the_invariants_something_to_check():
    """Положительный контроль: правила, проверенные на пустоте, не проверены.

    Тест, который гоняет инварианты по кадрам без единой зоны, зелен всегда и не значит
    ничего — та же форма, которую этот проект ловит в других местах. Здесь тот же
    построитель зовётся с явными параметрами, и требуется, чтобы работа была: зоны есть у
    большинства кадров, у части — свинги, и попадаются кадры с несколькими зонами.
    """
    shapes = [
        # (баров, волатильность, откуда плоско, таймфрейм, tz, доля выброшенных)
        (200, 0.012, 200, "1h", None, 0.0),
        (200, 0.008, 200, "15min", "UTC", 0.1),
        (150, 0.02, 150, "4h", "Europe/Moscow", 0.0),
        (120, 0.004, 120, "1D", None, 0.05),
        (100, 0.0, 0, "1h", None, 0.0),        # ряд без движения — законный вход
        (260, 0.015, 130, "1h", "UTC", 0.0),   # половина плоская
    ]

    zones_seen, with_swings, multi_zone = 0, 0, 0
    for i, (n, vol, flat, freq, tz, drop) in enumerate(shapes):
        frame = build_frame(n, 1500.0, vol, flat, freq, tz, drop, seed=i)
        result = _run(frame)
        if result.zones:
            zones_seen += 1
        if len(result.zones) >= 3:
            multi_zone += 1
        if any(
            ((z.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}).get("num_swings")
            for z in result.zones
        ):
            with_swings += 1

    assert zones_seen >= len(shapes) - 1, f"зоны нашлись только в {zones_seen} формах из {len(shapes)}"
    assert multi_zone >= 2, f"кадров с тремя и более зонами: {multi_zone}"
    assert with_swings >= 2, f"кадров со свингами: {with_swings}"
