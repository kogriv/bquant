"""Заглушка объявляет себя свойством, а не прозой (G31).

Откуда
======

«Заглушка» была написана в пакете четыре раза словами — в докстроке модуля,
в докстроке класса, в строке описания внутри перечня — и один раз
машиночитаемо, в ``metadata['implementation_status']`` результата. То есть
узнать, что анализатор ничего не анализирует, можно было **только вызвав** его.
У класса не было ни одного атрибута, по которому программа отличила бы заглушку
от рабочего анализатора.

Это тот же принцип, что вывели на G20 и применяли в G8: **закрыто то, на чём
дискриминирует универсальный код; открыто то, что придумывает предметная
область.** Статус реализации предметной областью не является — его нельзя
оставлять прозой.

Что проверяется
===============

Связь между маркером и поведением — **в обе стороны**. Односторонняя проверка
здесь бесполезна ровно так же, как была бесполезна в G32: там сьют пинил, что
каталог содержит имя, и отдельно — что фабрика работает, а связать их было
нечем. Поэтому:

* класс с ``is_stub = True`` обязан возвращать ``implementation_status: 'stub'``;
* класс без маркера обязан **не** возвращать этот признак.

Так реализованный анализатор, у которого забыли снять маркер, покраснеет — и
наоборот, снятый маркер при неубранной заглушке тоже.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis import BaseAnalyzer  # noqa: E402
from bquant.analysis.candlestick import CandlestickAnalyzer  # noqa: E402
from bquant.analysis.chart import ChartAnalyzer  # noqa: E402
from bquant.analysis.technical import TechnicalAnalyzer  # noqa: E402
from bquant.analysis.timeseries import TimeseriesAnalyzer  # noqa: E402


#: Все анализаторы пакета, у которых есть собственный ``analyze()``.
ANALYZERS = [
    CandlestickAnalyzer,
    ChartAnalyzer,
    TechnicalAnalyzer,
    TimeseriesAnalyzer,
]

FRAME = pd.DataFrame({
    "open": [100.0, 101.0, 102.0],
    "high": [101.0, 102.0, 103.0],
    "low": [99.0, 100.0, 101.0],
    "close": [100.5, 101.5, 102.5],
})


def test_the_base_analyzer_is_not_a_stub_by_default():
    """Маркер по умолчанию отрицательный — иначе он объявлял бы заглушкой всё."""
    assert BaseAnalyzer.is_stub is False


@pytest.mark.parametrize("cls", ANALYZERS, ids=[c.__name__ for c in ANALYZERS])
def test_the_marker_and_the_result_agree(cls):
    """Маркер и поведение обязаны сходиться — в обе стороны."""
    result = cls().analyze(FRAME)
    says_stub = result.metadata.get("implementation_status") == "stub"

    if cls.is_stub:
        assert says_stub, (
            f"{cls.__name__}.is_stub = True, но результат не помечен "
            "`implementation_status: 'stub'`. Либо анализатор реализовали и "
            "забыли снять маркер, либо заглушка перестала объявлять себя в "
            "результате — оба случая делают признак недостоверным"
        )
    else:
        assert not says_stub, (
            f"{cls.__name__} маркера не несёт, но результат помечен как заглушка. "
            "Маркер снят, а заглушечность осталась"
        )


@pytest.mark.parametrize("cls", ANALYZERS, ids=[c.__name__ for c in ANALYZERS])
def test_a_stub_listing_carries_the_mark_from_the_marker_not_from_prose(cls):
    """Суффикс «(заглушка)» в перечне выводится из маркера, а не вписан руками."""
    from bquant.analysis import mark_if_stub

    plain = {"нечто": "Описание"}
    marked = mark_if_stub(cls, plain)

    if cls.is_stub:
        assert marked["нечто"].endswith("(заглушка)")
    else:
        assert marked == plain

    assert plain == {"нечто": "Описание"}, "помощник не должен править вход"


def test_the_scan_covers_the_stubs_we_know_about():
    """Список анализаторов в этом файле не должен тихо усохнуть."""
    assert sum(1 for c in ANALYZERS if c.is_stub) == 4, (
        "заглушек стало не четыре — если одну реализовали, снимите маркер и "
        "обновите этот пин вместе с докой; если добавили новую, впишите её сюда"
    )
