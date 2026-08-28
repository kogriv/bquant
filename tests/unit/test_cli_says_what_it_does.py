"""Пины на команду ``bquant``: выход обязан соответствовать имени команды.

Почему этот файл появился (2026-08-28, бэклог `devref/architecture/p2a_cli_backlog_2026-08.md`)
=============================================================================================

``bquant/cli.py`` — это ``[project.scripts] bquant = "bquant.cli:main"``, то есть
исполняемый файл, который появляется в ``PATH`` после ``pip install bquant``, и он же
описан в ``README.md`` — витрине PyPI. Тестов на модуль было **ноль**, поэтому полностью
зелёный сьют ничего не знал о двух дефектах:

1. ``analyze`` считал MACD и **выбрасывал** результат — в график уходил сырой кадр, и в
   HTML не было ни одного вхождения «macd»;
2. ось времени на графике **синтезировалась** (``date_range('2024-01-01', …)``) вместо
   чтения из данных — график утверждал 2024 год там, где данные за 2025-й.

Проверки здесь **чёрного ящика**: они гоняют ``main()`` так же, как его запустит человек
из терминала, и смотрят на то, что он произвёл. Это сделано намеренно — пин должен
переживать любую внутреннюю перестройку модуля и падать ровно тогда, когда команда снова
начнёт выдавать не то, что обещает её имя.
"""

from __future__ import annotations

import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from bquant.data.samples import get_sample_data, list_datasets


DATASET = "tv_xauusd_1h"


def _run_cli(argv: list[str]) -> str:
    """Выполнить команду так, как её выполнит терминал, и вернуть stdout."""

    import sys

    from bquant import cli

    buffer = io.StringIO()
    saved = sys.argv
    sys.argv = ["bquant", *argv]
    try:
        with redirect_stdout(buffer):
            cli.main()
    finally:
        sys.argv = saved
    return buffer.getvalue()


@pytest.fixture(scope="module")
def analyze_run(tmp_path_factory) -> tuple[str, str]:
    """Один прогон ``bquant analyze`` на всех проверках: он не дешёвый."""

    target = tmp_path_factory.mktemp("cli") / "chart.html"
    stdout = _run_cli(["analyze", DATASET, "-o", str(target)])
    assert target.exists(), (
        f"команда отработала, но файл графика не создан: {target}\nstdout:\n{stdout}"
    )
    return stdout, target.read_text(encoding="utf-8")


def _trace_names(chart_html: str) -> list[str]:
    """Имена трасс фигуры — то, что реально нарисовано."""

    return re.findall(r'"name":"([^"]*)"', chart_html)


def _first_x_values(chart_html: str) -> list[str]:
    """Первые значения оси X первой трассы."""

    match = re.search(r'"x":\[([^\]]{0,400})', chart_html)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


# --- Дефект 1: команда, названная анализом, обязана дать анализ --------------


def test_analyze_reports_how_many_zones_it_found(analyze_run):
    """Команда обязана сообщить результат анализа, а не только «готово».

    До правки stdout заканчивался «Анализ завершен успешно!», не назвав ни одного
    числа, полученного из данных. Успех без результата — это отчёт о том, что код
    не упал, а не о том, что что-то посчитано.
    """

    stdout, _ = analyze_run

    zone_lines = [line for line in stdout.splitlines() if "зон" in line.lower()]
    assert zone_lines, "вывод команды не упоминает зоны вовсе:\n" + stdout

    reported = [int(n) for line in zone_lines for n in re.findall(r"\d+", line)]
    assert reported and max(reported) > 0, (
        "команда не назвала число найденных зон (или назвала ноль):\n" + stdout
    )


def test_the_chart_carries_the_indicator_it_computed(analyze_run):
    """Индикатор посчитан — значит, он обязан быть на графике.

    Замер до правки: одна трасса ``Close``, вхождений «macd» без учёта регистра — ноль,
    при том что в лог печаталось ``Calculating MACD (12, 26, 9)``.
    """

    _, chart = analyze_run
    assert "macd" in chart.lower(), (
        "в графике нет ни одного упоминания индикатора — он посчитан и выброшен"
    )
    names = " ".join(_trace_names(chart)).lower()
    assert "macd" in names, f"среди трасс нет индикатора, только: {_trace_names(chart)}"


def test_the_chart_marks_the_zones(analyze_run):
    """Зоны — предмет анализа, они обязаны быть видны на графике."""

    _, chart = analyze_run
    assert '"type":"rect"' in chart or '"shapes":' in chart, (
        "на графике нет ни одной размеченной зоны"
    )


def test_the_zone_marks_land_on_the_data_not_at_epoch_zero(analyze_run):
    """Прямоугольник зоны обязан стоять там, где зона.

    Ловушка, вскрытая уже после починки оси времени: ``ZoneInfo.start_time`` — это
    **позиция**, если кадр пришёл с ``RangeIndex`` (а ``get_sample_data()`` отдаёт
    именно такой, со временем в колонке ``time``). Ось при этом стала временной, и
    plotly читает ``x0=0`` как эпоху — все 32 зоны уезжают в 1970 год, за левый край.

    Форма дефекта прежняя: прямоугольники **есть**, их **ровно столько, сколько
    зон**, и проверка «зоны размечены» проходит — но размечено не то место.
    Поэтому пин смотрит на координаты, а не на факт наличия.
    """

    _, chart = analyze_run
    bounds = re.findall(r'"x0":"?([^",]+)"?,"x1":"?([^",]+)"?', chart)
    assert bounds, "на графике не нашлось координат зон"

    time_column = get_sample_data(DATASET)["time"]
    first_day = str(time_column.iloc[0])[:10]
    last_day = str(time_column.iloc[-1])[:10]

    numeric = [b for b in bounds if re.fullmatch(r"-?\d+(\.\d+)?", b[0])]
    assert not numeric, (
        f"{len(numeric)} зон размечены числовыми координатами на временной оси "
        f"(первая: {numeric[0]}) — plotly прочитает их как эпоху, и зоны уедут в 1970"
    )

    assert all(first_day <= b[0][:10] <= last_day for b in bounds), (
        f"есть зоны вне диапазона данных {first_day}..{last_day}: "
        f"{[b for b in bounds if not (first_day <= b[0][:10] <= last_day)][:3]}"
    )


# --- Дефект 2: ось времени не выдумывается ----------------------------------


def test_the_time_axis_comes_from_the_data_not_from_a_default(analyze_run):
    """Даты на графике обязаны быть датами данных.

    ``_prepare_datetime_index`` не знал про колонку ``time`` — имя из собственного
    стандарта проекта (``AGENTS.md``, «Column Standards»), — и, не найдя ``timestamp``
    или ``date``, **синтезировал** ось ``date_range('2024-01-01', periods=…, freq='1H')``.
    Замер до правки: график начинался с ``2024-01-01T00:00:00``, тогда как данные
    начинаются 2025-06-11. Это опаснее умолчания: график не молчит, он утверждает.
    """

    _, chart = analyze_run
    expected_first = get_sample_data(DATASET)["time"].iloc[0]
    expected_day = str(expected_first)[:10]

    x_values = _first_x_values(chart)
    assert x_values, "на графике не нашлось оси X со значениями"

    assert not x_values[0].startswith("2024-01-01T00:00:00"), (
        "ось времени синтезирована из умолчания date_range('2024-01-01', …), "
        f"а данные начинаются {expected_day}"
    )
    assert x_values[0].startswith(expected_day), (
        f"график начинается с {x_values[0]}, а данные — с {expected_day}"
    )


# --- Прочие команды ---------------------------------------------------------


def test_list_names_every_dataset():
    """``bquant list`` обязан перечислить все встроенные наборы."""

    stdout = _run_cli(["list"])
    for dataset in list_datasets():
        assert dataset["name"] in stdout, f"набор {dataset['name']} не назван в выводе"


# --- Структурный вывод: потребитель здесь программа, а не человек -----------


@pytest.fixture(scope="module")
def json_run() -> dict:
    """``--json --no-chart``: только числа, без отрисовки — поэтому быстро."""

    stdout = _run_cli(["analyze", DATASET, "--json", "--no-chart"])
    return json.loads(stdout)


def test_json_output_is_parseable_and_versioned(json_run):
    """Разбираемый JSON с номером схемы.

    Номер нужен именно потому, что читать это будет программа: без него
    потребитель не отличит смену формы от смены данных.
    """

    assert json_run["schema_version"] >= 1
    assert json_run["dataset"] == DATASET
    assert json_run["indicator"] == "macd"
    assert json_run["zones"]["total"] > 0


def test_json_carries_the_column_schema_not_guessed_names(json_run):
    """Имена колонок отдаются как есть, вместе с ролями.

    Потребитель не должен угадывать, какая колонка что значит, — ровно эту
    угадайку и разбирали в G8.
    """

    columns = json_run["columns"]
    assert columns, "структурный вывод не назвал ни одной колонки индикатора"
    roles = {key.split(":")[-1] for key in columns}
    assert {"line", "signal", "hist"} <= roles, f"роли неполны: {roles}"


def test_text_and_json_report_the_same_zone_count(analyze_run, json_run):
    """Два вида вывода обязаны говорить одно и то же.

    Текст и JSON строятся из одной сводки намеренно: разойдись они, и по одному
    из них можно сделать вывод, которого второй не подтверждает.
    """

    stdout, _ = analyze_run
    zone_lines = [line for line in stdout.splitlines() if "найдено зон" in line.lower()]
    assert zone_lines, "в текстовом выводе нет строки с числом зон:\n" + stdout
    text_total = int(re.search(r"\d+", zone_lines[0]).group())
    assert text_total == json_run["zones"]["total"]


# --- Индикатор — параметр, а не значение слова «анализ» ---------------------


@pytest.mark.parametrize("indicator", ["macd", "rsi", "ao"])
def test_every_supported_indicator_produces_zones(indicator):
    """Пайплайн индикатор-агностичен — CLI обязан это унаследовать.

    Зашить MACD в смысл команды ``analyze`` значило бы вернуть ту же слипшуюся
    идентичность-со-смыслом, которую разводили в G8/G20: RSI и AO объявляют
    роль ``value``, а не тройку MACD, и это не повод отказывать в анализе.
    """

    from bquant import cli

    payload = json.loads(_run_cli(["analyze", DATASET, "-i", indicator, "--json", "--no-chart"]))
    assert payload["indicator"] == indicator
    assert payload["zones"]["total"] > 0, f"по {indicator} не найдено ни одной зоны"
    assert indicator in cli.SUPPORTED_INDICATORS


def test_a_single_role_oscillator_still_gets_a_chart(tmp_path):
    """RSI объявляет одну роль ``value`` — рисовать его всё равно есть чем.

    ``plot_macd_with_zones`` требует тройку ролей и отказывается; поэтому зоны по
    любому не-MACD осциллятору были непоказуемы. Пин следит, чтобы обобщённый путь
    не отвалился обратно к «только MACD».
    """

    target = tmp_path / "rsi.html"
    _run_cli(["analyze", DATASET, "-i", "rsi", "-o", str(target)])
    chart = target.read_text(encoding="utf-8")
    assert "RSI" in chart, "график по RSI не содержит самого RSI"
    assert '"type":"rect"' in chart or '"shapes":' in chart, "зоны не размечены"


# --- Гигиена модуля --------------------------------------------------------


def test_library_functions_raise_instead_of_killing_the_process():
    """Импортировавший модуль обязан получить исключение, а не ``SystemExit``.

    Раньше ``sys.exit(1)`` стоял внутри библиотечных функций: любой, кто
    импортировал ``bquant.cli`` как модуль, получал завершение процесса вместо
    ошибки, которую можно поймать. Решать судьбу процесса вправе точка входа.
    """

    from bquant.cli import run_zone_analysis
    from bquant.core.exceptions import BQuantError

    with pytest.raises(BQuantError):
        run_zone_analysis(DATASET, indicator="определённо-не-индикатор")


def test_quiet_is_short_but_not_silent_about_the_result():
    """``--quiet`` сокращает подробности, а не обязанность назвать посчитанное.

    Прежняя команда в тихом режиме печатала только путь к файлу — то есть
    отчитывалась о том, что не упала, а не о том, что нашла.
    """

    stdout = _run_cli(["analyze", DATASET, "-q", "--no-chart"])
    lines = [line for line in stdout.splitlines() if line.strip()]

    assert len(lines) == 1, f"тихий режим не такой уж тихий:\n{stdout}"
    assert re.search(r"\d+", lines[0]), (
        "тихий режим не назвал ни одного числа: " + lines[0]
    )
    assert "зон" in lines[0].lower(), "тихий режим не сказал, что именно посчитано"


def test_an_unknown_indicator_is_refused_by_the_parser():
    """Опечатку в имени индикатора надо ловить на разборе аргументов."""

    from bquant.cli import build_parser

    with pytest.raises(SystemExit):
        build_parser().parse_args(["analyze", "-i", "нет-такого"])
