"""Публичное имя пакета обязано быть упомянуто в доках (G31).

Откуда
======

Три слоя проверок доки смотрят на **то, что написано**: ссылка ведёт куда надо
(`test_docs_parity.py`), аргументы совпадают с сигнатурой
(`test_docs_call_signatures.py`), самодостаточный пример запускается
(`test_docs_examples_run.py`).

Ни один не смотрит на **то, что не написано.** Публичная функция, про которую в
доках нет ни строчки, не нарушает ни одного из трёх утверждений: молчание — не
расхождение. Замер 2026-08-29: из 167 имён, реэкспортируемых пакетами, **30 не
упомянуты в доках ни разу**, и все проверки при этом зелёные.

Свежее доказательство, что дыра не историческая: ``resolve_time_index`` появился
накануне (G30) и не упомянут нигде.

Что проверяется и почему именно это
====================================

Проверяется **уровень реэкспорта** — имена из ``__all__`` пакетных ``__init__``,
то есть ровно то, что человек пишет в ``from bquant.X import ...``. Публичное
внутри модуля, но не поднятое в пакет, сюда не входит: такое импортируют по
полному пути и обычно вслед за чтением кода, а не доки.

Критерий «упомянуто» намеренно щедрый — имя встречается подстрокой где-либо в
корпусе доки. Это не проверка качества описания, это проверка **наличия**.
Строже здесь нельзя: требование «у каждого имени свой раздел» — вкусовое, а
требование «имя вообще встречается» — нет.

Исключения объявляются, а не получаются
========================================

Образец — ``KNOWN_COLLISIONS`` в ``test_public_name_collisions.py`` и
``EXPECTED_TO_FAIL`` в ``test_docs_examples_run.py``. Запись в ``UNDOCUMENTED``
говорит, **почему** имя не описано. Имя, выпавшее из доки без записи, обязано
покраснеть; имя с записью, которое вдруг описали, — тоже (реестр не должен
превращаться в свалку).

Разбор: ``devref/gaps/docs/g31_the_checks_watch_what_is_written_2026-08.md``.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.unit.test_docs_parity import PROJECT_ROOT, _iter_docs  # noqa: E402


#: Публичные имена, которые в доках намеренно не описаны, и причина у каждого.
#:
#: Две группы, и обе — вопрос не к доке, а к тому, что пакет предъявляет наружу.
#: Пока имя стоит в ``__all__``, оно часть публичной поверхности; запись здесь
#: фиксирует, что описывать нечего, а не что описать забыли.
UNDOCUMENTED = {
    # --- Заглушки: в коде прямым текстом «СТАТУС: Заглушка». ------------------
    # Описать их в доке значило бы описать пустоту: `analyze()` возвращает
    # `status: 'stub_implementation'` и список планов. Открытый вопрос владельцу
    # (см. G31) — оставлять ли их в `__all__` вообще. Сопутствующие им
    # `get_*_analyzers()` из реестра ушли: они описаны в `api/analysis/base.md`
    # как перечни видов анализа — это не заглушка, а честный перечень.
    "CandlestickAnalyzer": "заглушка bquant.analysis.candlestick — не реализован",
    "ChartAnalyzer": "заглушка bquant.analysis.chart — не реализован",
    "TechnicalAnalyzer": "заглушка bquant.analysis.technical — не реализован",
    "TimeseriesAnalyzer": "заглушка bquant.analysis.timeseries — не реализован",
    # --- Совместимость с numpy: внутренняя механика, поднятая в bquant.core. --
    # Вызываются пакетом при инициализации; читателю доки делать с ними нечего.
    "apply_numpy_fixes": "шим совместимости numpy, применяется пакетом сам",
    "check_numpy_compatibility": "шим совместимости numpy, внутренняя проверка",
    "ensure_numpy_compatibility": "шим совместимости numpy, внутренняя проверка",
}


def _dunder_all(init: Path) -> set[str]:
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    try:
                        return set(ast.literal_eval(node.value))
                    except (ValueError, SyntaxError):
                        return set()
    return set()


def _reexported() -> dict[str, set[str]]:
    """{имя: {пакеты, которые его реэкспортируют}}."""
    out: dict[str, set[str]] = {}
    for init in sorted((PROJECT_ROOT / "bquant").glob("**/__init__.py")):
        package = init.parent.relative_to(PROJECT_ROOT).as_posix().replace("/", ".")
        for name in _dunder_all(init):
            if not name.startswith("_"):
                out.setdefault(name, set()).add(package)
    return out


REEXPORTED = _reexported()

DOC_TEXT = "\n".join(
    doc.read_text(encoding="utf-8", errors="ignore") for doc in _iter_docs()
)


#: Пол, замеренный 2026-08-29: 167 реэкспортируемых имён. Сканер, нашедший
#: заметно меньше, сломался — а сломанный сканер даёт зелёный отчёт ни о чём.
MIN_REEXPORTED = 140


@pytest.mark.parametrize("name", sorted(REEXPORTED), ids=sorted(REEXPORTED))
def test_a_reexported_name_is_mentioned_in_the_docs(name):
    """Имя, которое пакет предъявляет наружу, обязано где-то в доках встречаться."""
    if name in UNDOCUMENTED:
        pytest.skip(f"объявлено неописуемым: {UNDOCUMENTED[name]}")

    assert name in DOC_TEXT, (
        f"`{name}` реэкспортируется из {', '.join(sorted(REEXPORTED[name]))}, "
        "но в доках не упомянут ни разу.\n"
        "Либо опишите его, либо — если описывать нечего — внесите в UNDOCUMENTED "
        "с причиной. Молчаливого третьего варианта здесь нет: имя в `__all__` "
        "пакет предъявляет наружу, а наружу предъявленное читают по доке."
    )


def test_the_scan_actually_found_the_surface():
    """Пустой — и просто похудевший — сканер оба дают зелёный отчёт ни о чём."""
    assert len(REEXPORTED) >= MIN_REEXPORTED, (
        f"найдено {len(REEXPORTED)} реэкспортируемых имён при пороге "
        f"{MIN_REEXPORTED} — похоже, сканер `__all__` сломался"
    )


@pytest.mark.parametrize("name", sorted(UNDOCUMENTED), ids=sorted(UNDOCUMENTED))
def test_the_undocumented_registry_is_not_a_dumping_ground(name):
    """Запись обязана оставаться нужной: и имя живо, и описания по-прежнему нет."""
    assert name in REEXPORTED, (
        f"`{name}` числится в UNDOCUMENTED, но пакетами больше не реэкспортируется — "
        "запись протухла, удалите её"
    )
    assert name not in DOC_TEXT, (
        f"`{name}` объявлен неописуемым ({UNDOCUMENTED[name]}), но в доках "
        "встречается. Реестр исключений — не свалка: если описание появилось, "
        "запись должна уйти, иначе она прикроет следующее выпавшее имя"
    )
