"""Границы зоны — время, если время в кадре есть (G30).

Откуда
======

Два входа данных одного пакета отдавали кадры с разными контрактами индекса:
``get_sample_data()`` — ``RangeIndex`` со временем в колонке ``time``,
``load_ohlcv_data()`` — ``DatetimeIndex``. Пайплайн не нормализовал ничего, поэтому
``ZoneInfo.start_time`` оказывался то временем, то позицией — в зависимости от того,
каким входом воспользовался вызывающий.

Само поле при этом честное: оно отражает индекс, который ему дали. Виноват был вход.

Это дважды выстрелило: зоны на графике CLI уехали в 1970 год (позиции на временной
оси), и упал написанный для документации пример (`PriceLevelAnalyzer` считает
длительность разницей дат). Оба случая шли через ``get_sample_data``.

Решающее свидетельство — обход «поставить время на индекс» написан в нашем коде
**шестнадцать раз** независимо, а семнадцатый добавил агент, не зная о предыдущих.
Когда одну и ту же подготовку пишут семнадцать вызывающих, она принадлежит тому,
кого они вызывают.

Разбор: ``devref/gaps/detection/g30_two_entry_points_two_index_contracts_2026-08.md``.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones import analyze_zones  # noqa: E402
from bquant.data.samples import get_sample_data  # noqa: E402


def _zones(df):
    return (
        analyze_zones(df)
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .analyze()
        .build()
    ).zones


def test_a_frame_with_a_time_column_yields_zones_bounded_by_time():
    """`get_sample_data()` отдаёт время в колонке — границы всё равно временные.

    До правки здесь были позиции (`0`, `2`, …) под именем `start_time`, и именно
    они уезжали на временной оси графика в 1970 год.
    """
    zones = _zones(get_sample_data("tv_xauusd_1h"))

    first = zones[0]
    assert isinstance(first.start_time, pd.Timestamp), (
        f"граница зоны — {type(first.start_time).__name__}, а не время: "
        "кадр нёс время в колонке, и пайплайн обязан был его увидеть"
    )
    assert isinstance(first.end_time, pd.Timestamp)
    assert first.end_time >= first.start_time


def test_both_entry_points_agree_on_the_type_of_a_zone_boundary():
    """Ради этого всё и делается: два входа — один контракт на выходе.

    Раньше `get_sample_data` давал позиции, а `load_ohlcv_data` — времена, и
    потребитель получал разный тип границ в зависимости от того, чем загрузил.
    """
    positional = get_sample_data("tv_xauusd_1h")
    temporal = positional.set_index(pd.to_datetime(positional["time"])).drop(columns=["time"])

    a = _zones(positional)[0]
    b = _zones(temporal)[0]

    assert type(a.start_time) is type(b.start_time), (
        f"вход через колонку даёт {type(a.start_time).__name__}, "
        f"вход через индекс — {type(b.start_time).__name__}"
    )
    assert a.start_time == b.start_time, "и это должно быть одно и то же время"


def test_a_frame_without_any_time_still_works_and_says_so_by_giving_positions():
    """Нормализация не обязана выдумывать время там, где его нет.

    Кадр без распознаваемого времени продолжает работать; границы остаются
    позициями — честно, потому что ничего другого в данных нет. Ошибкой было бы
    не это, а синтез дат (что и делала визуализация до 0.0.8).
    """
    n = 300
    frame = pd.DataFrame({
        "open": [100 + (i % 17) for i in range(n)],
        "high": [101 + (i % 17) for i in range(n)],
        "low": [99 + (i % 17) for i in range(n)],
        "close": [100 + (i % 19) for i in range(n)],
    })

    zones = _zones(frame)
    assert zones, "кадр без времени должен по-прежнему давать зоны"
    assert not isinstance(zones[0].start_time, pd.Timestamp), (
        "времени в кадре нет — выдумывать его нельзя"
    )


def test_the_normaliser_is_shared_with_the_chart_layer():
    """Один помощник, а не две копии логики.

    У визуализации была своя версия этого же разбора
    (`ChartBuilder._prepare_datetime_index`), и чинилась она отдельно в 0.0.8.
    Две копии расходятся: одна научится понимать колонку, другая нет.
    """
    from bquant.data.processor import resolve_time_index
    from bquant.visualization.charts import ChartBuilder

    assert ChartBuilder._prepare_datetime_index.__wrapped_helper__ is resolve_time_index, (
        "слой графиков перестал пользоваться общим помощником"
    )


@pytest.mark.parametrize("column", ["time", "timestamp", "date", "datetime"])
def test_every_documented_time_column_name_is_recognised(column):
    """Имя `time` — из стандарта проекта, остальные встречаются в чужих выгрузках."""
    from bquant.data.processor import resolve_time_index

    n = 50
    frame = pd.DataFrame({
        column: pd.date_range("2024-01-01", periods=n, freq="h"),
        "close": range(n),
    })
    resolved = resolve_time_index(frame)
    assert isinstance(resolved.index, pd.DatetimeIndex)
    assert column not in resolved.columns, "колонка времени переехала на индекс"
