"""``detect_zones`` не принимает правил, которых не понимает (G29).

Откуда
======

Сообщил **внешний потребитель**, а не сьют и не замер изнутри. У него порог
длительности входит в контентный хэш профиля, то есть в паспорт изделия. При переходе
между версиями на одном конфиге у него поехали набор зон, минимальная длительность и
отпечаток — при том что конфиг объявлял прежний порог.

Смена имени колонки при этом упала **громко**, и это правильно. А `min_duration=2`
прошёл молча: вызов принят, значение передано, смысл исчез. Его формулировка, с которой
нечего спорить: **принятый и проигнорированный параметр хуже удалённого — удалённый
ломает сборку, проигнорированный ломает выводы.**

Проверка у себя показала, что дело шире одного имени: валидный вызов проглатывал
**любой** незнакомый аргумент. Отсутствие обязательного правила отвергалось корректно —
то есть стратегии проверяли, чего им не хватает, и никто не проверял, что им дали
лишнего.

Разбор: ``devref/gaps/detection/g29_detect_zones_swallows_unknown_rules_2026-08.md``.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

from bquant.analysis.zones import analyze_zones  # noqa: E402
from bquant.data.samples import get_sample_data  # noqa: E402


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


def _builder(data):
    return (
        analyze_zones(data)
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    )


def test_min_duration_on_detection_is_refused_and_names_its_replacement(data):
    """Отменённый параметр обязан отвергаться, а сообщение — вести за руку.

    Докстрока `detect_zones` уже говорила «there is no ``min_duration`` here any
    more», но код его принимал. Расхождение доки с поведением — то же, что чинили
    в G25/G27, только зеркальное: там дока обещала больше, чем умеет код, здесь —
    меньше, чем код принимает.
    """
    with pytest.raises(ValueError) as excinfo:
        _builder(data).detect_zones(
            "zero_crossing", indicator_role="hist", min_duration=2
        ).analyze().build()

    message = str(excinfo.value)
    assert "min_duration" in message
    assert "analyze" in message, (
        "сообщение обязано называть замену, иначе отказ просто перекладывает поиск "
        "на того, кто и так не знал: " + message
    )


def test_a_rule_nobody_understands_is_refused(data):
    """Незнакомое правило — опечатка или отменённое имя. И то и другое громко.

    Раньше отвергалось только **отсутствие обязательного** правила: стратегии
    проверяли, чего им не хватает, и никто не проверял, что им дали лишнего.
    """
    with pytest.raises(ValueError) as excinfo:
        _builder(data).detect_zones(
            "zero_crossing", indicator_role="hist", nonexistent_rule=42
        ).analyze().build()

    assert "nonexistent_rule" in str(excinfo.value)


def test_legitimate_optional_rules_still_pass(data):
    """Отказ не должен превратиться в запрет всего, кроме обязательного."""

    result = (
        _builder(data)
        .detect_zones("zero_crossing", indicator_role="hist", smooth_window=3)
        .analyze()
        .build()
    )
    assert len(result.zones) > 0


def test_roles_are_still_accepted_everywhere_they_were(data):
    """`*_role` — законный способ адресации, он не должен попасть под отказ."""

    result = (
        _builder(data)
        .detect_zones("line_crossing", line1_role="line", line2_role="signal")
        .analyze()
        .build()
    )
    assert len(result.zones) > 0


def test_the_threshold_strategy_keeps_its_own_rules(data):
    """Проверка общая, но набор правил у каждой стратегии свой."""

    result = (
        analyze_zones(data)
        .with_cache(enable=False)
        .with_indicator("pandas_ta", "rsi", length=14)
        .detect_zones(
            "threshold", indicator_col="RSI_14",
            upper_threshold=70, lower_threshold=30,
        )
        .analyze()
        .build()
    )
    assert len(result.zones) > 0


def test_a_missing_required_rule_still_fails_as_before(data):
    """Прежнее поведение сохраняется: не хватает обязательного — отказ."""

    with pytest.raises(ValueError) as excinfo:
        _builder(data).detect_zones("zero_crossing").analyze().build()
    assert "indicator_col" in str(excinfo.value)
