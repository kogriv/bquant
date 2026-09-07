"""Скрипт тестов гипотез обязан отчитываться о том, что посчитано (G69).

`scripts/analysis/run_hypothesis_tests.py` печатал «Successful Tests: 2» на семи
тестах, ни один из которых не выполнился. Механизм — две ошибки, каждая безобидная
по отдельности:

1. в `run_all_hypothesis_tests` уезжал **конверт** `zones_info` (четыре ключа), а не
   список признаков зон: pandas отвечал «Mixing dicts with non-Series may lead to
   ambiguous ordering», и все семь тестов падали;
2. счётчик спрашивал «нет ли у записи ключа `error`» **у верхнего уровня ответа** —
   этому условию удовлетворяли обе записи конверта (`tests` и `summary`), отсюда
   двойка.

Результат: отчёт с нулём посчитанных тестов, `significance_rate` = 0, **рекомендации
по торговле**, выведенные из пустоты, и код возврата 0. Прежний интеграционный тест
этого не видел: он проверял, что в выводе есть заголовок «hypothesis testing results»,
и заранее прощал ненулевой код («may be expected»).

Проверки ниже спрашивают ЧИСЛО посчитанных тестов и требуют отказа там, где считать
нечего.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "analysis" / "run_hypothesis_tests.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("run_hypothesis_tests_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script_module()


@pytest.mark.integration
def test_every_declared_test_actually_runs(script):
    """Семь объявленных тестов — семь посчитанных, а не два ключа конверта."""
    runner = script.HypothesisTestingScript()
    results = runner.test_hypotheses(
        symbol="XAUUSD",
        timeframe="1h",
        use_sample_data=True,
        all_tests=True,
        alpha=0.05,
    )

    summary = results["testing_summary"]
    assert summary["total_tests"] == 7
    assert summary["successful_tests"] == 7, summary.get("failed_reasons")
    assert summary["failed_tests"] == 0
    # Значимых должно быть строго между нулём и всеми: ноль означал бы, что
    # p-value снова не доезжают, «все» — что сравнение с alpha не работает.
    assert 0 < summary["significant_results"] < 7

    # Каждый результат несёт число, а не только форму.
    for name, payload in results["test_results"].items():
        assert isinstance(payload.get("p_value"), float), name


@pytest.mark.integration
def test_the_selected_tests_branch_counts_the_same_way(script):
    """Ветка `--tests` возвращала объект, а счётчик проверял `isinstance(dict)`."""
    runner = script.HypothesisTestingScript()
    results = runner.test_hypotheses(
        symbol="XAUUSD",
        timeframe="1h",
        use_sample_data=True,
        tests=["duration", "asymmetry", "sequence"],
        alpha=0.05,
    )

    assert results["testing_summary"]["successful_tests"] == 3
    assert set(results["test_results"]) == {"duration", "asymmetry", "sequence"}


@pytest.mark.integration
def test_a_report_over_zero_executed_tests_is_refused(script):
    """Отчёт по нулю посчитанных тестов — не отчёт, а рекомендации из пустоты."""
    runner = script.HypothesisTestingScript()
    all_failed = {
        "zone_duration": {"error": "Mixing dicts with non-Series"},
        "histogram_slope": {"error": "Mixing dicts with non-Series"},
    }

    with pytest.raises(ValueError) as exc:
        runner._format_results(
            symbol="XAUUSD",
            timeframe="1h",
            test_results=all_failed,
            zones_info={"zones_features": [{"zone_type": "bull", "duration": 5}]},
            testing_start=script.datetime.now(),
            alpha=0.05,
            verbose=False,
        )

    # Отказ обязан назвать причины, иначе он неотличим от поломки самого скрипта.
    assert "Mixing dicts" in str(exc.value)


@pytest.mark.integration
def test_the_zone_summary_counts_zones_by_their_declared_type(script):
    """Считалось `z['type'] == 'Bull'`: ни ключа, ни написания — обе группы нули."""
    runner = script.HypothesisTestingScript()
    summary = runner._summarize_zones(
        {
            "zones_features": [
                {"zone_type": "bull", "duration": 10, "price_return": 0.01},
                {"zone_type": "bear", "duration": 6, "price_return": -0.02},
                {"zone_type": "bull", "duration": 8, "price_return": 0.03},
            ]
        }
    )

    assert summary["total_zones"] == 3
    assert summary["zones_by_type"] == {"bull": 2, "bear": 1}


@pytest.mark.integration
def test_the_json_output_carries_the_numbers(tmp_path):
    """JSON-выгрузка падала на `significant` (np.bool_) — но только когда есть что писать.

    Пока ни один тест не считался, в отчёт ехали одни строки ошибок, и запись
    проходила. Первый же настоящий результат дал
    `Object of type bool is not JSON serializable`.
    """
    out = tmp_path / "hypotheses.json"
    run = subprocess.run(
        [
            sys.executable, str(SCRIPT), "XAUUSD", "1h",
            "--sample-data", "--all-tests", "--output", str(out),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert run.returncode == 0, run.stderr[-800:]
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["testing_summary"]["successful_tests"] == 7
    assert payload["zones_summary"]["zones_by_type"]
    for name, result in payload["test_results"].items():
        assert isinstance(result["p_value"], float), name
        assert isinstance(result["significant"], bool), name


@pytest.mark.integration
def test_the_printed_number_is_the_computed_number():
    """То же число, что в отчёте, должно печататься пользователю."""
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "XAUUSD", "1h", "--sample-data", "--all-tests"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert run.returncode == 0, run.stderr[-800:]
    assert "Successful Tests: 7" in run.stdout, run.stdout
