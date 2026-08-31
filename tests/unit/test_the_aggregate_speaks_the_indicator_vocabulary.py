"""Сводка по зонам обязана говорить на языке того индикатора, по которому считана.

G34. `total_statistics` фильтровал зоны по двум литералам `'bull'`/`'bear'` и на
пороговом прогоне RSI отдавал четыре нуля при 64 найденных зонах. Ноль там читался
как измерение, тогда как верное утверждение — «такого деления у этого индикатора не
существует».

Проверка двусторонняя, и это существенно: односторонняя (только «на RSI нет нулей»)
разрешила бы заодно выбросить `bull_*` у MACD, чем сломала бы внешнего потребителя.
"""

from __future__ import annotations

import pytest

from bquant.analysis.zones import analyze_macd_zones, analyze_zones
from bquant.data.samples import get_sample_data


DIRECTIONAL_FIELDS = ("bull_zones_count", "bear_zones_count", "bull_ratio", "bear_ratio")


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture(scope="module")
def macd_totals(data):
    return analyze_macd_zones(data).statistics["total_statistics"]


@pytest.fixture(scope="module")
def rsi_totals(data):
    result = (
        analyze_zones(data)
        .with_indicator("pandas_ta", "rsi", length=14)
        .detect_zones(
            "threshold", indicator_role="value", upper_threshold=70, lower_threshold=30
        )
        .analyze()
        .build()
    )
    return result.statistics["total_statistics"]


def test_every_vocabulary_gets_its_own_distribution(macd_totals, rsi_totals):
    """Основной ответ — по фактически встреченным типам, каким бы ни был словарь."""

    assert sorted(macd_totals["zones_by_type"]) == ["bear", "bull"]
    assert sorted(rsi_totals["zones_by_type"]) == ["neutral", "overbought", "oversold"]

    for totals in (macd_totals, rsi_totals):
        assert sum(totals["zones_by_type"].values()) == totals["total_zones"]
        assert pytest.approx(sum(totals["ratios_by_type"].values()), abs=1e-9) == 1.0


def test_a_vocabulary_without_direction_reports_no_direction(rsi_totals):
    """Отсутствие поля — не то же самое, что поле со значением 0.

    `.get(field, 0)` у потребителя вернёт тот же ноль, но ключа в структуре больше
    нет, и это различимо: программа может спросить, есть ли такое деление вообще.
    """

    assert rsi_totals["total_zones"] == 64

    for field in DIRECTIONAL_FIELDS:
        assert field not in rsi_totals, (
            f"{field} присутствует в сводке по RSI. У этого словаря типов нет "
            "направления, и любое число здесь будет выдумкой."
        )


def test_a_directional_vocabulary_keeps_its_fields(macd_totals):
    """Обратная сторона: MACD-путь не должен пострадать от универсальности."""

    for field in DIRECTIONAL_FIELDS:
        assert field in macd_totals

    assert macd_totals["bull_zones_count"] == macd_totals["zones_by_type"]["bull"]
    assert macd_totals["bear_zones_count"] == macd_totals["zones_by_type"]["bear"]
    assert (
        pytest.approx(macd_totals["bull_ratio"])
        == macd_totals["bull_zones_count"] / macd_totals["total_zones"]
    )


def test_the_cli_schema_number_moved_with_the_shape():
    """Потребитель `--json` — программа; смена формы обязана менять номер."""

    from bquant.cli import SUMMARY_SCHEMA_VERSION

    assert SUMMARY_SCHEMA_VERSION >= 2
