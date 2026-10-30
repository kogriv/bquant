"""Правило, объявленное понятым, обязано влиять на результат (G85).

`ZoneDetectionConfig.validate()` отвергает правила, которых стратегия не понимает, и
каждая стратегия объявляет полный набор понятых — иначе отвергать нечем. Это и
оказалось вторым местом, где можно совершить дефект, против которого проверка заведена:
`smooth_window` объявляли три стратегии, а читала одна. У `threshold` и `line_crossing`
вызов с ним проходил и не делал ничего — «принятый и проигнорированный параметр хуже
удалённого», словами внешнего потребителя в докстроке самой проверки.

Замерено 2026-10-30 на `tv_xauusd_1h`: `smooth_window=50` меняет `zero_crossing` с 30 зон
на 10, а `threshold` (61) и `line_crossing` (77) — никак.

Форма правки — отказ с названной заменой, не сглаживание: сгладить значило бы молча
изменить числа тому, кто параметр уже передавал, тогда как отказ сообщает ему, что
сглаживания и не было.

Два сторожа. Первый — поведенческий, на трёх стратегиях с общим кадром. Второй —
механический, по исходникам: каждое имя из `optional_rules` обязано читаться в теле
той же стратегии, чтобы третий такой случай не появился вместе с новой стратегией.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from bquant.analysis.zones.detection.base import ZoneDetectionConfig
from bquant.analysis.zones.detection.line_crossing import LineCrossingDetection
from bquant.analysis.zones.detection.threshold import ThresholdDetection
from bquant.analysis.zones.detection.zero_crossing import ZeroCrossingDetection
from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory

DETECTION_DIR = Path(__file__).resolve().parents[2] / "bquant" / "analysis" / "zones" / "detection"


@pytest.fixture(scope="module")
def frame():
    data = get_sample_data("tv_xauusd_1h")
    macd = IndicatorFactory.create(
        "custom", "macd", fast_period=12, slow_period=26, signal_period=9
    ).calculate(data)
    return data.join(macd.data)


def _zones(strategy, frame, rules):
    config = ZoneDetectionConfig(zone_types=None, rules=rules, strategy_name="x")
    return strategy.detect_zones(frame, config)


# --------------------------------------------------------------------------- #
# 1. Положительный контроль: у zero_crossing правило живое
# --------------------------------------------------------------------------- #
def test_zero_crossing_reads_smooth_window(frame):
    plain = _zones(ZeroCrossingDetection(), frame, {"indicator_col": "macd_12_26_9__line"})
    smoothed = _zones(
        ZeroCrossingDetection(), frame,
        {"indicator_col": "macd_12_26_9__line", "smooth_window": 50},
    )
    assert len(plain) == 30
    assert len(smoothed) < len(plain) - 1, "окно 50 обязано сгладить заметно, не на одну зону"


# --------------------------------------------------------------------------- #
# 2. Отказ с названной заменой у тех, кто правило не читает
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("strategy", "rules"),
    [
        (ThresholdDetection(), {"indicator_col": "rsi", "upper_threshold": 70, "lower_threshold": 30}),
        (LineCrossingDetection(), {"line1_col": "macd_12_26_9__line", "line2_col": "macd_12_26_9__signal"}),
    ],
    ids=["threshold", "line_crossing"],
)
def test_smooth_window_is_refused_where_it_was_never_read(strategy, frame, rules):
    with pytest.raises(ValueError) as refusal:
        _zones(strategy, frame, {**rules, "smooth_window": 3})
    message = str(refusal.value)
    assert "smooth_window" in message
    assert "zero_crossing" in message, "отказ обязан назвать, кто правило читает"
    assert "rolling" in message, "отказ обязан назвать замену — сглаживание до детекции"


def test_the_refusal_is_not_vacuous(frame):
    """Без правила тот же вызов проходит: отказ — про `smooth_window`, а не про кадр."""
    assert _zones(
        ThresholdDetection(), frame,
        {"indicator_col": "rsi", "upper_threshold": 70, "lower_threshold": 30},
    )


# --------------------------------------------------------------------------- #
# 3. Механический сторож: объявил — читай
# --------------------------------------------------------------------------- #
def _declared_optional_rules(source: str) -> list[str]:
    """Строковые литералы из `optional_rules=[...]` / `(...)` в вызове validate."""
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "optional_rules":
            for element in ast.walk(node.value):
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    names.append(element.value)
    return names


def _strategy_sources() -> list[tuple[str, str]]:
    found = []
    for path in sorted(DETECTION_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "optional_rules=" in source and "def detect_zones" in source:
            found.append((path.name, source))
    return found


def test_the_scan_sees_the_strategies():
    """Положительный контроль сторожа: он обязан найти хотя бы zero_crossing с его правилом."""
    declared = {name: _declared_optional_rules(src) for name, src in _strategy_sources()}
    assert "zero_crossing.py" in declared
    assert "smooth_window" in declared["zero_crossing.py"]
    assert sum(len(v) for v in declared.values()) >= 3, declared


@pytest.mark.parametrize(("filename", "source"), _strategy_sources(), ids=lambda v: v if isinstance(v, str) and v.endswith(".py") else "")
def test_every_declared_optional_rule_is_read_by_its_strategy(filename, source):
    """Имя в `optional_rules` обязано встречаться в теле как чтение правила.

    Ищется `rules.get('<имя>')`, `rules['<имя>']` или `rules["<имя>"]` — три формы,
    которыми стратегии читают `config.rules`. Объявление само по себе чтением не
    считается: именно оно и было дефектом.
    """
    for rule in _declared_optional_rules(source):
        pattern = rf"""rules(?:\.get\(|\[)\s*['"]{re.escape(rule)}['"]"""
        assert re.search(pattern, source), (
            f"{filename}: `{rule}` объявлен в optional_rules, но не читается — "
            f"вызов с ним пройдёт и не сделает ничего (G85)"
        )
