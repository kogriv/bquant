"""Тест последовательностей не вправе фабриковать словарь типов зон (G26).

Три теста гипотез направленные: `contrast_asymmetry`, `correlation_drawdown` и
`sequence_patterns`. Первые два без объявленного словаря **отказываются считать** и
называют причину. Третий до 2026-09-07 отказ обходил: при `vocabulary=None` он строил
словарь из наблюдаемых **имён** (`ZoneVocabulary.coerce`). Такой словарь не объявляет
полярности, поэтому runs-половина теста всегда пропускалась, а chi2-половина
возвращалась под именем и p-value полного теста.

Цена измерена на встроенном сэмпле (`tv_xauusd_1h`, MACD, 77 зон): без словаря
`p = 1.0` — «последовательность случайна», со словарём `p = 0.0` — «неслучайна» при
`alpha = 0.05`. На синтетическом ряду ниже те же две стороны дают 0.873 против
2.3e-09: числа другие, вывод тот же — деградировавший ответ это ровно chi2-половина.
Ряд зон MACD строго чередуется, то есть это максимально неслучайная
последовательность из возможных, и молчаливый ответ был не более слабым, а
**противоположным**. Сводка при этом считала тест выполненным: `tests_executed: 5`.

Ниже пинится и отказ, и то, ради чего он нужен: на одних и тех же данных словарь без
полярности и словарь с полярностью дают разные вердикты, и вердикт **называет**, какой
тест на самом деле посчитан.
"""

import pytest

from bquant.analysis.statistical import run_all_hypothesis_tests
from bquant.analysis.statistical.hypothesis_testing import HypothesisTestSuite
from bquant.analysis.zones import ZoneType, ZoneVocabulary
from bquant.core.exceptions import StatisticalAnalysisError


def _alternating_zones(n=40):
    """Строго чередующиеся зоны — самая неслучайная последовательность из возможных."""
    zones = []
    for i in range(n):
        zones.append(
            {
                "zone_type": "bull" if i % 2 == 0 else "bear",
                "duration": 10 + (i % 5),
                "price_return": 0.01 if i % 2 == 0 else -0.01,
                "start_idx": i * 10,
                "end_idx": i * 10 + 9,
            }
        )
    return zones


@pytest.fixture
def suite():
    return HypothesisTestSuite(alpha=0.05)


@pytest.fixture
def declared():
    """Словарь, объявляющий полярность и контрастную пару."""
    return ZoneVocabulary.coerce(
        [
            ZoneType("bull", polarity=+1, counterpart="bear"),
            ZoneType("bear", polarity=-1, counterpart="bull"),
        ]
    )


@pytest.fixture
def names_only():
    """Словарь из одних имён: свойств нет, направления взять неоткуда."""
    return ZoneVocabulary.coerce(["bull", "bear"])


def test_without_a_vocabulary_the_sequence_test_refuses(suite):
    """Отказ, а не chi2-половина под именем полного теста."""
    with pytest.raises(StatisticalAnalysisError) as exc:
        suite.test_sequence_hypothesis(_alternating_zones())

    message = str(exc.value)
    assert "vocabulary" in message
    # Отказ обязан называть способ его снять, иначе он неотличим от поломки.
    assert "resolve_vocabulary" in message


def test_the_refusal_is_not_cosmetic_the_two_verdicts_are_opposite(suite, declared, names_only):
    """Ровно те же данные, разные словари — противоположные ответы."""
    zones = _alternating_zones()

    with_polarity = suite.test_sequence_hypothesis(zones, vocabulary=declared)
    without_polarity = suite.test_sequence_hypothesis(zones, vocabulary=names_only)

    assert bool(with_polarity.significant) is True
    assert with_polarity.p_value < 0.05
    assert bool(without_polarity.significant) is False
    assert without_polarity.p_value > 0.05
    # Сигнал целиком в runs-половине: chi2 по переходам на чередующемся ряду
    # почти равномерен, и деградировавший ответ — это ровно chi2.
    assert without_polarity.p_value == pytest.approx(
        with_polarity.metadata["chi2_p_value"]
    )
    assert with_polarity.metadata["runs_p_value"] < 0.05


def test_the_verdict_names_which_test_actually_ran(suite, declared, names_only):
    """`test_type` — часть ответа: chi2 без runs не вправе носить имя полного теста."""
    zones = _alternating_zones()

    assert suite.test_sequence_hypothesis(zones, vocabulary=declared).test_type == (
        "Chi-square and runs tests"
    )

    degraded = suite.test_sequence_hypothesis(zones, vocabulary=names_only)
    assert degraded.test_type == (
        "Chi-square only (runs test skipped: no directional zone types)"
    )
    assert degraded.metadata["runs_test_skipped"]
    assert degraded.metadata["runs_p_value"] is None


def test_the_summary_counts_the_refusal_instead_of_calling_it_executed(declared):
    """Сводка самостоятельного пути: три отказа названы, а не спрятаны в выполненных."""
    zones = _alternating_zones()

    without = run_all_hypothesis_tests(zones, alpha=0.05)
    # Синтетические зоны несут не все поля, поэтому сравнивается не общее число
    # отказов, а судьба именно этого теста: он должен быть среди названных, а не
    # среди выполненных.
    assert "sequence_patterns" in without["summary"]["failed_tests"]
    assert without["tests"]["sequence_patterns"].get("p_value") is None

    with_vocab = run_all_hypothesis_tests(zones, alpha=0.05, vocabulary=declared)
    assert "sequence_patterns" not in with_vocab["summary"]["failed_tests"]
    assert with_vocab["tests"]["sequence_patterns"]["p_value"] < 0.05
