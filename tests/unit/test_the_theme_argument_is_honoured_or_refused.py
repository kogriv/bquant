"""Тема либо применяется, либо отвергается — но не принимается молча.

G47. Аргумент `theme` принимали три класса визуализации и не применял ни один: он
уходил в `**kwargs` и там оставался. `bquant_light` и `bquant_dark` давали **побайтно
одинаковую** фигуру, а `theme='dark'` — темы с таким именем не существует — выглядел
ровно так же, как настоящая.

Проверяется три вещи, и третья важнее первых двух:

1. запрошенная тема меняет фигуру;
2. незнакомое имя темы отвергается с перечнем настоящих;
3. **без явного `theme=` не меняется ничего** — умолчание осталось прежним, иначе
   правка молча перекрасила бы каждый график в пакете.
"""

from __future__ import annotations

import hashlib

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts, StatisticalPlots, ZoneVisualizer
from bquant.visualization.themes import ChartThemes, get_theme


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture(scope="module")
def zones_result(data):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd")
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .analyze(clustering=False)
        .build()
    )


def _fingerprint(figure) -> str:
    return hashlib.sha1(figure.to_json().encode()).hexdigest()


# --------------------------------------------------------------------------- #
# 1. Тема меняет фигуру
# --------------------------------------------------------------------------- #

def test_two_themes_do_not_produce_the_same_figure(data):
    charts = FinancialCharts()

    light = _fingerprint(charts.create_candlestick_chart(data, title="t", theme="bquant_light"))
    dark = _fingerprint(charts.create_candlestick_chart(data, title="t", theme="bquant_dark"))

    assert light != dark


def test_the_theme_can_be_given_to_the_constructor(data):
    per_call = _fingerprint(
        FinancialCharts().create_candlestick_chart(data, title="t", theme="bquant_dark")
    )
    per_object = _fingerprint(
        FinancialCharts(theme="bquant_dark").create_candlestick_chart(data, title="t")
    )

    assert per_call == per_object


def test_the_zone_visualizer_honours_the_theme(zones_result):
    light = ZoneVisualizer(theme="bquant_light")
    dark = ZoneVisualizer(theme="bquant_dark")

    assert _fingerprint(light.plot_zones_on_price_chart(zones_result.data, zones_result.zones)) != \
        _fingerprint(dark.plot_zones_on_price_chart(zones_result.data, zones_result.zones))


def test_the_statistical_plots_honour_the_theme(data):
    plots = StatisticalPlots()

    assert _fingerprint(plots.plot_distribution(data["close"], title="t", theme="bquant_light")) != \
        _fingerprint(plots.plot_distribution(data["close"], title="t", theme="bquant_dark"))


# --------------------------------------------------------------------------- #
# 2. Незнакомое имя — отказ, а не подмена
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", ["dark", "light", "blue", "heatmap", ""])
def test_a_theme_that_does_not_exist_is_refused(name, data):
    """Все пять имён стояли в примерах справочника и ни одно не является темой."""

    if name:
        with pytest.raises(ValueError, match="Unknown theme"):
            get_theme(name)

    with pytest.raises(ValueError, match="Unknown theme"):
        FinancialCharts().create_candlestick_chart(data, title="t", theme=name or "dark")


def test_the_refusal_names_the_themes_that_exist():
    with pytest.raises(ValueError) as excinfo:
        get_theme("nope")

    message = str(excinfo.value)
    for real in ChartThemes().get_available_themes():
        assert real in message


def test_an_unknown_theme_is_refused_at_construction(data):
    with pytest.raises(ValueError, match="Unknown theme"):
        ZoneVisualizer(theme="dark")

    with pytest.raises(ValueError, match="Unknown theme"):
        FinancialCharts(theme="dark")


# --------------------------------------------------------------------------- #
# 3. Умолчание не тронуто
# --------------------------------------------------------------------------- #

def test_without_an_explicit_theme_nothing_is_applied(data, zones_result):
    """Правка не должна была перекрасить графики, о теме не просившие."""

    charts = FinancialCharts()
    plain = _fingerprint(charts.create_candlestick_chart(data, title="t"))

    for theme in ChartThemes().get_available_themes():
        themed = _fingerprint(charts.create_candlestick_chart(data, title="t", theme=theme))
        assert themed != plain, f"тема {theme} совпала с нетематизированной фигурой"

    visualizer = ZoneVisualizer()
    assert visualizer.theme_name == "bquant_light"
    assert visualizer._explicit_theme is None
