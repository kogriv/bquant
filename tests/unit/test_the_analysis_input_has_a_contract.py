"""Странный вход обязан получить названный отказ, а не правдоподобное число (G72).

Пять «странных» входов прогнаны через флагманский путь и измерены до правки
(`analyze_zones → build`, MACD по линии, ZigZag, сэмпл `tv_xauusd_1h`):

| вход | было | стало |
|---|---|---|
| пустой кадр | отказ индикатора: «0 rows, need 35» | без изменений |
| ряд короче индикатора | отказ индикатора | без изменений |
| ряд без движения | 1 зона, 0 свингов, `degraded='degenerate'` | без изменений (G70) |
| ось со временем в UTC | считается | без изменений |
| **вперемешку** | `ValueError` **тремя слоями ниже**: «zone 5: start_time > end_time» | отказ на входе, названа причина |
| **дубли по времени** | то же сообщение про зону | отказ на входе, названа причина |
| **`NaN` в цене** | **успех: число другое** | отказ на входе, названа причина |

Два последних — разные болезни одной формы. Неотсортированный вход и дубли
доезжали до инварианта зоны (G66) и падали сообщением, которое называет
следствие: зона получилась задом наперёд. Причина — кадр пришёл вперемешку —
в сообщении не упоминалась, и починить по нему было нечего.

`NaN` в цене не падал вовсе. Замер: одна дыра ровно на границе зоны сдвинула её
`price_return` с **−0.000958** на **−0.000651**, `NaN` в выходе не появился,
предупреждения не было. `ewm` пропускает дыру, и метрика считается от соседнего
бара, как будто он и был границей зоны.
"""

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.processor import resolve_time_index
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def sample():
    return get_sample_data("tv_xauusd_1h").head(300).copy()


def _build(df):
    return (
        analyze_zones(df)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing="zigzag")
        .with_cache(enable=False)
        .analyze(clustering=False)
        .build()
    )


def test_an_unsorted_frame_is_refused_by_its_own_cause(sample):
    """Раньше падало на инварианте зоны — сообщением про зону, а не про вход."""
    shuffled = sample.sample(frac=1.0, random_state=42)

    with pytest.raises(ValueError) as exc:
        _build(shuffled)

    message = str(exc.value)
    assert "not sorted" in message
    # Отказ обязан называть выход, иначе он неотличим от поломки пакета.
    assert "sort_index" in message or "sort_values" in message
    # Про зоны сказать можно — но ПОСЛЕ причины, как следствие, а не вместо неё.
    # Прежнее сообщение начиналось с «zone 5: start_time > end_time», и причина в
    # нём не упоминалась вовсе.
    assert message.lower().index("not sorted") < message.lower().index("zone")
    assert not message.lower().startswith("zone")


def test_duplicate_timestamps_are_refused_by_their_own_cause(sample):
    """Сдвоенный бар считается дважды в каждой метрике зоны."""
    doubled = pd.concat([sample, sample.iloc[100:110]]).sort_values("time")

    with pytest.raises(ValueError) as exc:
        _build(doubled)

    message = str(exc.value)
    assert "duplicate" in message
    assert "10" in message  # сколько именно повторов
    assert "duplicated" in message  # способ снять


def test_a_hole_in_the_price_is_refused_instead_of_moving_the_number(sample):
    """Главный случай: молчаливое ДРУГОЕ число вместо пустоты или отказа."""
    clean = _build(sample)
    target = clean.zones[2]
    clean_return = (target.features or {})["price_return"]

    holed = sample.copy()
    holed.iloc[target.start_idx, holed.columns.get_loc("close")] = np.nan

    with pytest.raises(ValueError) as exc:
        _build(holed)

    message = str(exc.value)
    assert "missing values" in message and "close: 1" in message
    assert "clean_ohlcv_data" in message

    # Замер, ради которого отказ и введён: без него число менялось молча.
    assert clean_return == pytest.approx(-0.0009579155757072355, rel=1e-6)


def test_the_contract_does_not_touch_the_healthy_path(sample):
    """Отказ не должен стоить ничего тем, у кого данные в порядке."""
    result = _build(sample)

    assert len(result.zones) == 8
    assert all(z.start_idx <= z.end_idx for z in result.zones)


def test_a_flat_series_is_still_a_measurement_not_a_refusal(sample):
    """Ряд без движения — законный вход: он считается, но пустота названа (G70)."""
    flat = sample.copy()
    for column in ("open", "high", "low", "close"):
        flat[column] = 2000.0

    result = _build(flat)

    assert len(result.zones) == 1
    metrics = (result.zones[0].features or {})["metadata"]["swing_metrics"]
    assert metrics["num_swings"] == 0
    assert metrics["degraded"] == "degenerate"


def test_a_gap_in_the_data_stays_visible_rather_than_forbidden(sample):
    """Дыра в баре — не дефект входа: у рынка есть выходные.

    Запрещать разрывы нельзя (любая недельная свеча их содержит), поэтому
    контракт их не трогает. Но и молчания нет: зона несёт и число баров, и обе
    границы времени, так что разрыв внутри неё читается из результата.
    """
    gapped = pd.concat([sample.iloc[:100], sample.iloc[200:]])

    result = _build(gapped)

    assert result.zones
    zone = max(result.zones, key=lambda z: z.end_time - z.start_time)
    wall_clock_bars = (zone.end_time - zone.start_time) / pd.Timedelta(hours=1) + 1
    # Разрыв виден именно так: часов между границами больше, чем баров в зоне.
    assert wall_clock_bars > zone.duration


def test_the_axis_contract_is_checked_where_the_axis_is_made(sample):
    """`resolve_time_index` — то место, которое владеет осью, там и проверка."""
    with pytest.raises(ValueError, match="not sorted"):
        resolve_time_index(sample.sample(frac=1.0, random_state=1))

    with pytest.raises(ValueError, match="duplicate"):
        resolve_time_index(pd.concat([sample, sample.iloc[:5]]).sort_values("time"))

    # Кадр без времени вовсе остаётся позиционным и проходит: контракт про ось
    # времени, а не про существование времени (G30).
    positional = sample.drop(columns=["time"])
    assert resolve_time_index(positional).index.equals(positional.index)
