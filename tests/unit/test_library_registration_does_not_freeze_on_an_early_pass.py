"""Ранний проход по недостроенной библиотеке не имеет права заморозить пустой каталог.

Что было (G84). `PandasTALoader` обнаруживает индикаторы перебором `dir(pandas_ta)`.
Если этот перебор случается, пока модуль **ещё импортируется**, видно почти ничего:
замерено 2026-10-15 — `dir()` отдавал 16 имён вместо сотен, `hasattr(ta, 'zigzag')`
был False. Ноль найденных записывался как **состоявшаяся регистрация**
(`_indicators_registered = True`, пустой список доступных), и дальше в этом процессе
любой запрос библиотечного индикатора получал «the library is not installed or has no
indicator by that name» — при установленной библиотеке.

Следствия были видны снаружи и выглядели не тем, чем были:

* `IndicatorFactory.list_indicators()` продолжал перечислять `pandas_ta_zigzag`
  (каталог собирается из двух корзин, и вторая не пустела) — каталог обещал то, чего
  фабрика не создаст;
* `load_all_indicators()` отвечал `{'pandas_ta': 158}` при нуле достижимых — успешный
  отчёт над пустотой;
* `ZigZag` в режиме `global` отказывал, называя ложную причину, а в `per_zone`
  продолжал и помечал зоны `degraded='detector_unavailable'`.

**Почему сьют этого не видел.** Дефект наступает только в **холодном** процессе и зависит
от порядка импортов. В сьюте сотни тестов в одном процессе: к моменту запроса zigzag
библиотека давно импортирована целиком. Поэтому главная проверка здесь запускается
**отдельным процессом** — иначе она зелёная и на сломанном коде.

Разбор: `devref/gaps/swing/g84_…`.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def loader_state():
    """Снять и вернуть состояние загрузчика: проверки его намеренно портят."""
    from bquant.indicators.library.pandas_ta import PandasTALoader as loader

    saved = {
        name: getattr(loader, name)
        for name in ("_function_cache", "_available_indicators",
                     "_indicators_registered", "_registered_keys")
    }
    saved = {k: (dict(v) if isinstance(v, dict)
                 else set(v) if isinstance(v, set)
                 else list(v) if isinstance(v, list) else v)
             for k, v in saved.items()}
    try:
        yield loader
    finally:
        for name, value in saved.items():
            setattr(loader, name, value)


class _HalfBuiltModule:
    """Модуль pandas-ta, застигнутый на середине импорта.

    Шестнадцать атрибутов — замеренное число, а не круглое: ровно столько отдавал
    `dir(pandas_ta)` в момент, когда дефект наступал.
    """

    def __init__(self) -> None:
        for i in range(16):
            setattr(self, f"placeholder_{i}", i)


def test_discovery_that_found_nothing_is_not_recorded_as_success(loader_state):
    """Ноль найденных при живой библиотеке — повод попробовать снова, а не вывод.

    Отдельно требуется **диагностика**, и это не украшение. Поведение «не записывать
    пустоту как успех» держится и вторым предохранителем в `register_indicators`, что
    мутация и показала: без сообщения проверка оставалась зелёной на откаченной правке,
    то есть проверяла не то, что заявляла. Несущей здесь является именно названная
    причина: без неё оператор видит пустой каталог и не знает, что модуль застали
    недостроенным. Это сообщение — единственное место, где причина называется вслух.
    """
    import logging

    # `caplog` здесь не годится и это проверено: логгеры пакета не пробрасывают записи
    # в корень (свой профиль логирования), поэтому фикстура ловила пустоту и проверка
    # краснела на верном коде. Обработчик вешается на тот самый логгер.
    said: list[str] = []

    class _Catch(logging.Handler):
        def emit(self, record):
            said.append(record.getMessage())

    catcher = _Catch(level=logging.WARNING)
    logging.getLogger("bquant.indicators.library.pandas_ta").addHandler(catcher)

    loader = loader_state
    loader._function_cache = {}
    loader._available_indicators = []
    loader._indicators_registered = False
    loader._registered_keys = set()

    original_load_module = loader._load_module
    loader._load_module = classmethod(lambda cls: _HalfBuiltModule()).__get__(None, type(loader))
    try:
        registered = loader.register_indicators()
    finally:
        loader._load_module = original_load_module
        logging.getLogger("bquant.indicators.library.pandas_ta").removeHandler(catcher)

    assert registered == 0, "по недостроенному модулю регистрировать нечего"
    assert not loader._indicators_registered, (
        "пустая регистрация записана как состоявшаяся — именно это и замораживало "
        "каталог на весь процесс"
    )
    assert not loader._function_cache, "пустое обнаружение не должно кэшироваться"

    heard = " ".join(said)
    assert "partially initialised" in heard, (
        "причина не названа: оператор увидит пустой каталог и не узнает, что модуль "
        f"застали недостроенным. Сказано было: {heard!r}"
    )


def test_an_empty_registration_is_not_mistaken_for_an_absent_library(loader_state):
    """«Записей нет» — два разных состояния, и смешивать их нельзя.

    Библиотеки нет — терять нечего. Библиотека есть, а записей нет — регистрация не
    состоялась, и повторить её обязательно. До правки оба читались как «держится».
    """
    loader = loader_state
    loader._registered_keys = set()
    assert loader.is_available(), "проверка предполагает установленную pandas-ta"
    assert not loader.registration_still_holds(), (
        "при живой библиотеке пустой реестр обязан означать «надо повторить»"
    )


def test_a_cleared_registry_is_repaired(loader_state):
    """Записи, пропавшие из фабрики, обязаны восстанавливаться следующим запросом."""
    from bquant.indicators import IndicatorFactory
    from bquant.indicators.library.manager import LibraryManager, load_all_indicators

    load_all_indicators()
    assert loader_state._registered_keys, "ожидали, что pandas-ta что-то зарегистрировала"

    saved_registry = dict(IndicatorFactory._registry)
    try:
        IndicatorFactory._registry.clear()
        assert not loader_state.registration_still_holds()
        LibraryManager.ensure_loaded()
        indicator = LibraryManager.create_indicator(
            "pandas_ta", "zigzag", legs=3, deviation=0.008
        )
        assert indicator is not None
    finally:
        IndicatorFactory._registry.clear()
        IndicatorFactory._registry.update(saved_registry)


#: Сценарий читателя: свежий процесс, пайплайн, рекомендуемая стратегия.
_COLD_SCENARIO = textwrap.dedent(
    """
    import warnings
    warnings.filterwarnings("ignore")
    from bquant.analysis.zones import analyze_zones
    from bquant.data.samples import get_sample_data

    result = (
        analyze_zones(get_sample_data("tv_xauusd_1h"))
        .with_cache(enable=False)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="line")
        .with_strategies(swing="zigzag")
        .with_swing_preset("narrow_zone")
        .analyze()
        .build()
    )
    with_swings = sum(
        1 for zone in result.zones
        if (zone.features or {}).get("metadata", {}).get("swing_metrics", {}).get("num_swings", 0) > 0
    )
    print(f"COLD {len(result.zones)} {with_swings}")
    """
)


@pytest.mark.integration
def test_a_cold_process_gets_the_recommended_strategy(tmp_path):
    """Холодный процесс обязан получить zigzag — и свинги, а не отказ.

    Запускается **отдельным процессом** намеренно: в общем процессе сьюта библиотека
    давно импортирована целиком, дефект не наступает, и проверка была бы зелёной на
    сломанном коде. Числа (30 зон, 29 со свингами) — замеренные на `tv_xauusd_1h` с
    пресетом `narrow_zone`; они же стоят в таблице покрытия в доке.
    """
    script = tmp_path / "cold.py"
    script.write_text(_COLD_SCENARIO, encoding="utf-8")

    finished = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env={"PYTHONPATH": str(PROJECT_ROOT), "MPLBACKEND": "Agg", "PATH": "/usr/bin:/bin"},
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600,
    )
    marker = next(
        (line for line in finished.stdout.splitlines() if line.startswith("COLD ")), None
    )
    assert marker, (
        "холодный прогон не дошёл до результата:\n"
        f"stdout хвост: {finished.stdout[-400:]}\n"
        f"stderr хвост: {finished.stderr[-600:]}"
    )
    zones, with_swings = (int(part) for part in marker.split()[1:3])
    assert zones == 30, f"зон {zones}, ожидалось 30"
    assert with_swings == 29, (
        f"со свингами {with_swings} из {zones}; ноль здесь означает, что детектор не "
        f"получен — ровно дефект G84"
    )
