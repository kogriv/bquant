"""Валидация не имеет права выносить вердикт по метрике, которой не нашла.

G39. `ValidationSuite` извлекал метрики из результата анализа через `to_dict()`, а у
`AnalysisResult` этот метод кладёт их **на уровень глубже** — под ключ `results`. Для
собственного типа результата пакета запрошенная метрика не находилась ни разу, и
вместо отказа подставлялся ноль: ноль сравнивался с нулём и давал «деградация 0%,
модель устойчива».

Это худший вид отказа именно здесь: модуль отвечает на вопрос «держится ли модель», и
вместо «не знаю» отвечал «держится».

Почему не поймал сьют: все его проверки передавали `analyze_func`, возвращающий обычный
`dict`, — то есть ровно тот тип, с которым у извлечения проблем нет.

После G55 метрика описывается `MetricSpec`; здесь она — частота зон на бар, потому что
сама функция даёт ровно одну «зону» на десять баров, и сравнивать между окнами разной
длины можно только частоту.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.analysis import AnalysisResult
from bquant.analysis.validation import MetricSpec, ValidationSuite
from bquant.core.exceptions import AnalysisError

ZONE_RATE = MetricSpec("total_zones", direction="stable", per_bar=True)


@pytest.fixture(scope="module")
def data() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({"close": 2000 + np.cumsum(rng.normal(0, 2, 400))})


def analysis_result_func(window: pd.DataFrame) -> AnalysisResult:
    """Возвращает тип пакета, а не голый словарь — в этом и была вся разница."""

    return AnalysisResult(
        "t",
        results={"total_zones": float(len(window) // 10)},
        data_size=len(window),
    )


def test_the_package_own_result_type_is_read_correctly(data):
    suite = ValidationSuite()

    result = suite.out_of_sample_test(
        analysis_result_func, data, ZONE_RATE, train_ratio=0.7
    )

    assert result.train_metrics["total_zones"] == 28.0
    assert result.test_metrics["total_zones"] == 12.0


def test_a_real_degradation_is_reported_as_such(data):
    """Раньше здесь стояло 0% и `success=True` — вердикт из ничего.

    Функция кладёт вдвое меньше зон на бар в тестовое окно (120 баров), чем в
    обучающее (280): это настоящее падение частоты, а не артефакт длины окна.
    """

    def halves_on_test(window: pd.DataFrame) -> AnalysisResult:
        per_ten = 1.0 if len(window) > 200 else 0.5
        return AnalysisResult(
            "t", results={"total_zones": len(window) / 10 * per_ten}, data_size=len(window)
        )

    result = ValidationSuite().out_of_sample_test(
        halves_on_test, data, ZONE_RATE, train_ratio=0.7
    )

    assert result.degradation_pct == pytest.approx(50.0, abs=0.1)
    assert result.success is False


def test_a_missing_metric_is_refused_by_name(data):
    """Отказ обязан называть и то, чего нет, и то, что есть."""

    with pytest.raises(AnalysisError) as excinfo:
        ValidationSuite().out_of_sample_test(
            analysis_result_func, data, MetricSpec("нет_такой_метрики", "stable")
        )

    message = str(excinfo.value)
    assert "нет_такой_метрики" in message
    assert "total_zones" in message, "сообщение обязано перечислить доступные ключи"


def test_a_plain_dict_still_works(data):
    """Обратная сторона: тип, с которым и раньше было хорошо, не должен пострадать."""

    result = ValidationSuite().out_of_sample_test(
        lambda window: {"total_zones": float(len(window) // 10)},
        data,
        ZONE_RATE,
        train_ratio=0.7,
    )

    assert result.train_metrics["total_zones"] == 28.0


def test_a_non_numeric_metric_is_refused(data):
    """Сравнивать между окнами можно только число."""

    with pytest.raises(AnalysisError, match="must be a number"):
        ValidationSuite().out_of_sample_test(
            lambda window: {"total_zones": "много"}, data, ZONE_RATE
        )
