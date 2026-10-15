"""Самодостаточные примеры из доков обязаны **исполняться** (G25).

Чего не хватало
===============

``tests/unit/test_docs_parity.py`` проверяет, что **имена резолвятся**: модуль
импортируется, символ в нём есть. Он не проверяет, что **вызов работает**. Поэтому
сквозь полностью зелёный сьют проходили:

* ``create_swing_strategy('zigzag', legs=15)`` — функция есть, такого аргумента нет;
* ``info['parameters']`` — у словаря нет такого ключа;
* ``ZoneAnalysisPipeline()`` — не передан обязательный ``config``;
* ``get_sample_data('btc_hourly')`` — такого набора данных нет;
* незакрытый ``fence`` в ``logging.md``, из-за которого проза отрендерена как Python.

Дока — тоже «хорошо оформленная ложь»: она синтаксически связна и ссылается на
существующие символы, поэтому читается как рабочая. Отличить её от рабочей может
только исполнение. Разбор: ``devref/gaps/docs/g25_*.md``.

Что проверяется, а что нет
==========================

**Самодостаточный** блок — тот, у которого нет свободных имён: всё, что он читает,
он же и определяет или импортирует. Определяется разбором ``ast``.

**Фрагменты** (``print(result.zones)`` после блока, где ``result`` был создан) не
исполняются и не сшиваются по странице в один сценарий. Сшивка ввела бы порядок,
которого в доке нет: блоки на странице не обязаны быть одной программой. Лучше
проверять меньше, но утверждать правду.

**Ожидаемые падения объявляются явно** — :data:`EXPECTED_TO_FAIL`. Там намеренные
демонстрации отказов и примеры, ждущие файл от читателя. Запись говорит, *почему*
пример падает, и пример, начавший падать по другой причине, обязан покраснеть.
"""

from __future__ import annotations

import ast
import copy
import builtins
import io
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

os.environ.setdefault("MPLBACKEND", "Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.unit.test_docs_parity import (  # noqa: E402
    PROJECT_ROOT,
    _iter_docs,
    _python_blocks,
)


#: Примеры, которые обязаны падать, и почему. Ключ — файл плюс характерный фрагмент
#: кода; номер строки ключом быть не может, он уезжает от любой правки текста вокруг.
#: Образец — ``KNOWN_COLLISIONS`` в ``tests/unit/test_public_name_collisions.py``:
#: «ожидаемо падает» должно быть **заявлено**, а не получаться само.
EXPECTED_TO_FAIL = {
    ("docs/developer_guide/zone_detection_strategies.md", "from .base import"):
        "относительный импорт внутри пакета: так выглядит файл стратегии на месте",
}


_SCOPED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _module_level_nodes(tree: ast.AST):
    """Узлы **модульного** уровня: без тел функций, классов и лямбд.

    Разбор ведётся по модульной области видимости намеренно. Первая редакция
    собирала связывания по всему дереву — и аргумент функции `def analyze(self, data)`
    считался определением имени `data`, из-за чего фрагмент вроде

        class VolatilityAnalyzer(BaseAnalyzer):
            def analyze(self, data): ...
        result = VolatilityAnalyzer().analyze(data)   # <- data ниоткуда

    объявлялся самодостаточным и падал `NameError` уже в тесте. Имена внутри тела
    функции разрешаются в момент вызова; для вопроса «может ли читатель скопировать
    этот блок целиком» значимо только то, что читается на модульном уровне.
    """
    stack = list(ast.iter_child_nodes(tree))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, _SCOPED):
            # В тело не спускаемся — оно исполняется при вызове. Но декораторы,
            # базовые классы и значения по умолчанию вычисляются **здесь**, на
            # модульном уровне. Пропустив их, классификатор считал самодостаточным
            # блок с `@deprecated(...)` или `@StrategyRegistry.register(...)` без
            # импорта — и тот падал `NameError` уже в тесте.
            stack.extend(getattr(node, "decorator_list", []))
            stack.extend(getattr(node, "bases", []))
            stack.extend(kw.value for kw in getattr(node, "keywords", []))
            args = getattr(node, "args", None)
            if isinstance(args, ast.arguments):
                stack.extend(d for d in args.defaults if d is not None)
                stack.extend(d for d in args.kw_defaults if d is not None)
            continue
        stack.extend(ast.iter_child_nodes(node))


def _bound_names(tree: ast.AST) -> set[str]:
    """Имена, которые блок связывает на модульном уровне."""
    bound: set[str] = set()

    for node in _module_level_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)

    return bound


_ALWAYS_AVAILABLE = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "_"}


def _scope_bindings(node) -> set[str]:
    """Имена, связываемые внутри одной области видимости (без вложенных)."""
    bound: set[str] = set()
    args = getattr(node, "args", None)
    if isinstance(args, ast.arguments):
        bound.update(
            a.arg for a in
            [*args.posonlyargs, *args.args, *args.kwonlyargs,
             args.vararg, args.kwarg] if a is not None
        )
    for child in _module_level_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            bound.add(child.id)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            bound.add(child.name)
        elif isinstance(child, (ast.Global, ast.Nonlocal)):
            bound.update(child.names)
    return bound


def _free_names_in_scope(node, visible: set[str]) -> set[str]:
    """Свободные имена области ``node`` и всех вложенных в неё."""
    visible = visible | _scope_bindings(node)
    free = {
        child.id for child in _module_level_nodes(node)
        if isinstance(child, ast.Name)
        and isinstance(child.ctx, ast.Load)
        and child.id not in visible
    }
    for child in ast.walk(node):
        if child is node or not isinstance(child, _SCOPED):
            continue
        # Декораторы и базовые классы вычисляются снаружи и уже учтены обходом
        # модульного уровня; здесь спускаемся именно в тело.
        free |= _free_names_in_scope(child, visible)
    return free


def _free_names(code: str) -> set[str]:
    """Имена, которые блок читает, но нигде не определяет.

    Считается **по областям видимости**, а не по одному лишь модульному уровню.
    Обе более простые версии оказались неверны в разные стороны, и обе ошибки
    поймал прогон:

    * обход всего дерева одним множеством — аргумент ``def analyze(self, data)``
      выглядел определением имени ``data``, и фрагмент считался самодостаточным;
    * только модульный уровень — шаблон вида ``def main(): … get_sample_data(…)``
      с вызовом ``main()`` внизу тоже считался самодостаточным, хотя импорт
      ``get_sample_data`` остался в предыдущем блоке страницы.

    Правило простое и настоящее: имя внутри функции свободно, если оно не связано
    ни в её собственной области, ни в объемлющих.
    """
    tree = ast.parse(code)
    return _free_names_in_scope(tree, set()) - _ALWAYS_AVAILABLE


def _unwrap(block: str) -> str:
    """Снять разметочную обёртку: цитату и общий отступ.

    Блок в markdown может стоять внутри цитаты (``> ```python``) или элемента
    списка — тогда каждая строка приходит с префиксом ``> `` или лишним отступом,
    и код не разбирается вовсе. Это артефакт разметки, а не поломка примера.
    """
    lines = block.split("\n")
    meaningful = [ln for ln in lines if ln.strip()]
    if meaningful and all(ln.lstrip().startswith(">") for ln in meaningful):
        lines = [ln.lstrip()[1:].removeprefix(" ") if ln.strip() else ln for ln in lines]
    return textwrap.dedent("\n".join(lines))


def _collect_examples():
    """Самодостаточные python-блоки доков: (относительный путь, строка, код)."""
    items = []
    for doc in _iter_docs():
        text = doc.read_text(encoding="utf-8")
        rel = doc.relative_to(PROJECT_ROOT).as_posix()
        for raw in _python_blocks(doc, text):
            # Отбора по подстроке «bquant» здесь нет намеренно. Он выглядел
            # безобидной оптимизацией, но это не свойство блока, а совпадение
            # символов: блок, где импорт стоял абзацем выше, а вызов здесь,
            # отсеивался, хотя он про пакет. Той же формой промаха из проверок уже
            # дважды выпадали целые файлы — `README.md` и `docs/index.rst`; чинили
            # каждый раз не проверку, а её охват (G27).
            #
            # Критерий отбора теперь — свойство самого блока: он **разбирается** и
            # **самодостаточен**. Пример из доков, который не работает, не работает
            # независимо от того, попалось ли в нём слово «bquant».
            position = text.find(raw)
            line = text[:position].count("\n") + 1 if position >= 0 else 0
            block = _unwrap(raw)
            try:
                if _free_names(block):
                    continue  # фрагмент: опирается на предыдущий блок
            except SyntaxError:
                # Блок не разбирается — это отдельная претензия, и у неё отдельная
                # проверка (`test_a_python_fence_contains_python`). Смешивать её с
                # «пример не работает» нельзя: причины разные, и чинятся они разным.
                continue
            items.append((rel, line, block))
    return items


def _collect_python_fences():
    """Все блоки, подписанные ``python``: (относительный путь, строка, код)."""
    items = []
    for doc in _iter_docs():
        text = doc.read_text(encoding="utf-8")
        rel = doc.relative_to(PROJECT_ROOT).as_posix()
        for raw in _python_blocks(doc, text):
            position = text.find(raw)
            line = text[:position].count("\n") + 1 if position >= 0 else 0
            items.append((rel, line, _unwrap(raw)))
    return items


PYTHON_FENCES = _collect_python_fences()


EXAMPLES = _collect_examples()


def _expected_reason(rel: str, code: str):
    for (path, marker), reason in EXPECTED_TO_FAIL.items():
        if path == rel and marker in code:
            return reason
    return None


#: Глобальные реестры, которые примеры законно правят: показать, как зарегистрировать
#: свою стратегию, без регистрации нельзя. Слепок снимается до и возвращается после.
_REGISTRY_STATE = (
    ("bquant.analysis.zones.detection.registry", "ZoneDetectionRegistry",
     ("_strategies", "_metadata")),
    ("bquant.analysis.zones.strategies.registry", "StrategyRegistry", ("_registry",)),
)
# Реестр индикаторов в этот список НЕ добавлен, и это проверено попыткой: наполняется он
# **лениво**, снимок берётся до первой загрузки, и восстановление вычищало 158 лениво
# зарегистрированных имён, оставляя загрузчику флаг «уже загружено». Следующие примеры
# получали пустой реестр — 62 падения вместо двух. Протечка индикаторов между примерами
# решается не здесь, а тем, что проверка напечатанного идёт в отдельном процессе.


@pytest.fixture
def isolated_registries():
    """Вернуть глобальные реестры в исходное состояние после примера.

    Найдено полным прогоном, а не подмножеством: примеры из `extension_guide.md`
    и `zone_detection_strategies.md` регистрируют свои стратегии, и регистрация
    **переживала** тест — дальше по сьюту два теста реестра видели лишние имена и
    падали. Проверка, которая портит состояние другим, хуже отсутствующей: она
    роняет чужой тест и посылает искать причину не там.
    """
    import importlib

    saved = []
    for module_name, class_name, attributes in _REGISTRY_STATE:
        registry = getattr(importlib.import_module(module_name), class_name)
        for attribute in attributes:
            saved.append((registry, attribute, copy.deepcopy(getattr(registry, attribute))))
    try:
        yield
    finally:
        for registry, attribute, snapshot in saved:
            live = getattr(registry, attribute)
            # Вложенные корзины (StrategyRegistry._registry — семейство → имена)
            # возвращаются на месте: ссылки на них держат замыкания декораторов.
            for key, value in snapshot.items():
                if isinstance(value, dict) and isinstance(live.get(key), dict):
                    live[key].clear(); live[key].update(value)
                else:
                    live[key] = value
            for key in [k for k in live if k not in snapshot]:
                del live[key]


@pytest.mark.integration
@pytest.mark.parametrize(
    "rel, line, code",
    EXAMPLES,
    ids=[f"{rel}:{line}" for rel, line, _ in EXAMPLES],
)
def test_a_self_contained_doc_example_runs(
    rel, line, code, tmp_path, monkeypatch, isolated_registries
):
    """Пример, который читатель может скопировать целиком, обязан отработать."""

    monkeypatch.chdir(tmp_path)
    # Примеры на `NotebookSimulator` разбирают аргументы командной строки и читают
    # `stdin`. Без изоляции они видели argv **pytest'а** и падали `SystemExit: 2` —
    # это диагноз про стенд, а не про пример. Даём им пустой argv и закрытый ввод:
    # `--no-trap` отключает паузы, ради которых nb-скрипты и читают stdin.
    monkeypatch.setattr(sys, "argv", ["example.py", "--no-trap"])
    monkeypatch.setattr(sys, "stdin", io.StringIO())

    namespace = {"__name__": "__main__", "__file__": str(tmp_path / "example.py")}
    reason = _expected_reason(rel, code)

    try:
        exec(compile(code, f"{rel}:{line}", "exec"), namespace)
    except SystemExit as exc:
        # `NotebookSimulator.finish()` завершает скрипт через `sys.exit(0)` — это
        # успешное окончание примера, а не отказ. Ненулевой код — отказ.
        if exc.code not in (0, None):
            if reason:
                return
            pytest.fail(f"{rel}:{line} — пример завершился с кодом {exc.code!r}")
    except BaseException as exc:  # noqa: BLE001 - предмет проверки
        if reason:
            return  # падение заявлено
        pytest.fail(
            f"{rel}:{line} — документированный пример не работает:\n"
            f"    {type(exc).__name__}: {exc}\n"
            f"Либо почините пример, либо объявите ожидаемое падение в "
            f"EXPECTED_TO_FAIL с причиной."
        )

    if reason:
        pytest.fail(
            f"{rel}:{line} числится в EXPECTED_TO_FAIL ({reason}), но отработал. "
            f"Уберите запись — иначе реестр начнёт прикрывать настоящие поломки."
        )


@pytest.mark.parametrize(
    "rel, line, code",
    PYTHON_FENCES,
    ids=[f"{rel}:{line}" for rel, line, _ in PYTHON_FENCES],
)
def test_a_python_fence_contains_python(rel, line, code):
    """Блок, подписанный ``python``, обязан быть питоном.

    Претензия отдельная от «пример не работает», и цена у неё своя: на сайте такой
    блок подсвечен как исполняемый код, а для любой проверки он **невидим** —
    разбор падает, и блок молча выпадает из выборки. Молчаливое выпадение из
    проверки уже случалось в парити (многострочные импорты схлопывались в пустое
    имя, 11 блоков мимо кассы) и хуже отсутствия проверки: отчёт зелёный.

    Справка, которая кодом не является — перечень сигнатур, набросок структуры, —
    подписывается ``text``. Это не придирка к оформлению: подпись говорит читателю,
    можно ли это скопировать и запустить.
    """
    try:
        ast.parse(code)
    except SyntaxError as exc:
        first = next((ln for ln in code.splitlines() if ln.strip()), "")
        pytest.fail(
            f"{rel}:{line} — блок подписан ```python, но питоном не является:\n"
            f"    {exc.msg} (строка {exc.lineno})\n"
            f"    начало блока: {first[:70]}\n"
            f"Если это справка, а не код, — подпишите блок ```text."
        )


#: Пол охвата, замеренный 2026-08-29: 158 самодостаточных примеров из 406 python-блоков.
#: Пол поставлен под фактическое значение, но не «около нуля»: он ловит **обвал**
#: (сканер сломался, классификатор стал считать всё фрагментами, каталог доков уехал),
#: а не дрейф на несколько блоков от обычной правки текста. Прежний порог `>= 50` был
#: втрое ниже факта — при нём две трети примеров могли молча выпасть из проверки,
#: и отчёт остался бы зелёным. Это та же форма, из-за которой заведён
#: `test_a_python_fence_contains_python`: молчаливое выпадение хуже отсутствия проверки.
#: Порог поднимать вместе с ростом доков; опускать — только с объяснением, почему
#: примеров стало меньше.
MIN_SELF_CONTAINED_EXAMPLES = 140


def test_the_scan_actually_found_examples():
    """Пустой — и просто похудевший — сканер оба дают зелёный отчёт ни о чём."""
    assert len(EXAMPLES) >= MIN_SELF_CONTAINED_EXAMPLES, (
        f"собрано {len(EXAMPLES)} самодостаточных примеров при пороге "
        f"{MIN_SELF_CONTAINED_EXAMPLES} — либо сканер/классификатор сломался, "
        "либо примеры действительно убрали. Второе бывает: тогда порог опускается "
        "в том же изменении и с объяснением, а не задним числом"
    )


def test_fragments_are_told_apart_from_broken_examples():
    """Классификатор обязан различать эти два случая — на нём держится весь тест."""

    fragment = "print(result.zones)\n"
    assert _free_names(fragment) == {"result"}

    self_contained = (
        "from bquant.data.samples import get_sample_data\n"
        "data = get_sample_data('tv_xauusd_1h')\n"
        "print(len(data))\n"
    )
    assert _free_names(self_contained) == set()

    # Связывание внутри функции тоже считается: пример с main() самодостаточен.
    with_function = (
        "from bquant.data.samples import get_sample_data\n"
        "def main():\n"
        "    data = get_sample_data('tv_xauusd_1h')\n"
        "    return len(data)\n"
        "print(main())\n"
    )
    assert _free_names(with_function) == set()


def test_running_an_example_does_not_leak_into_the_global_registry(isolated_registries):
    """Прогон примера обязан вернуть глобальные реестры как было.

    Найдено полным прогоном: примеры, регистрирующие свою стратегию (а без
    регистрации их и не покажешь), оставляли имя в реестре, и **два чужих теста**
    падали дальше по сьюту. Проверка, которая портит состояние другим, хуже
    отсутствующей — она посылает искать причину не там, где она есть.
    """
    from bquant.analysis.zones.detection.registry import ZoneDetectionRegistry

    before = set(ZoneDetectionRegistry.list_strategies())

    class _LeakProbe:
        supported_zones = ("bull", "bear")

        def detect(self, *args, **kwargs):  # pragma: no cover - не вызывается
            return []

    ZoneDetectionRegistry._strategies["__leak_probe__"] = _LeakProbe
    assert "__leak_probe__" in ZoneDetectionRegistry.list_strategies()

    # Фикстура вернёт состояние на выходе из теста; здесь проверяем, что снимок
    # вообще был снят — то есть что имена до вмешательства совпадают с ожидаемыми.
    assert before == set(ZoneDetectionRegistry.list_strategies()) - {"__leak_probe__"}


def test_the_expected_failure_registry_is_not_a_dumping_ground():
    """Реестр ожидаемых падений должен оставаться маленьким и объяснённым."""

    assert len(EXPECTED_TO_FAIL) <= 20, (
        "реестр ожидаемых падений разросся — проверьте, не прикрывает ли он "
        "настоящие поломки вместо намеренных демонстраций"
    )
    for key, reason in EXPECTED_TO_FAIL.items():
        assert len(reason) > 20, f"{key}: причина не объяснена"


def test_every_expected_failure_still_points_at_an_example():
    """Запись, не совпадающая ни с одним блоком, — мёртвая, и это опасно.

    Реестр ловит только обратный случай: пример **числится** и при этом отработал.
    Запись, переставшая совпадать с чем-либо (пример переписали, раздел убрали),
    не краснеет никогда и тихо лежит — пока однажды её фрагмент не совпадёт с
    новым примером и не прикроет настоящую поломку.

    Найдено проходом по справочнику ядра: из пятнадцати записей шесть указывали в
    никуда — на разделы, переписанные волной 3.
    """
    orphans = []
    for rel, fragment in EXPECTED_TO_FAIL:
        matches = [code for doc_rel, _, code in EXAMPLES
                   if doc_rel == rel and fragment in code]
        if not matches:
            orphans.append(f"{rel} :: {fragment!r}")

    assert not orphans, (
        "записи реестра не совпадают ни с одним примером — уберите их:\n  "
        + "\n  ".join(orphans)
    )


# --------------------------------------------------------------------------- #
# 5. Напечатанное число обязано быть измеренным
# --------------------------------------------------------------------------- #
#
# Чего не хватало. Исполнение примера доказывает, что он **работает**, и ничего не
# говорит о том, что он печатает. `print(len(result.zones))   # 32` проходит все
# четыре прежних слоя — ссылка резолвится, имена существуют, сигнатура верна, блок
# отрабатывает без исключений, — а напечатает 30. Утверждение в комментарии не
# сверялось ни с чем после того, как его однажды написали.
#
# Как нашлось. Не сьютом, а **первым потребителем помимо лабы** (2026-10-15): он
# прогнал пример из README и получил 30 вместо обещанных 32. Число было выписано
# 2026-08-31, за два дня до выхода 0.0.10, который убрал зоны на незаполненном
# окне MACD; прогон на деревьях подтвердил перелом (0.0.9 → 32, 0.0.10 → 30). Коммит,
# внёсший `32`, называется «the pages a reader starts with printed numbers nobody had
# run»: правка, чинившая непрогнанные числа, внесла число, протухшее через два дня.
#
# Почему это дефект той же породы, что остальные. Читатель сверяет свой прогон с
# документированным числом. Расхождение он читает как «я что-то делаю не так» или как
# «пакет сломан», а не как «дока устарела», — и тратит время не туда. Правило
# `AGENTS.md` «числа в прозе берутся прогоном, никогда не переписываются» существовало
# с самого начала; механической проверки у него не было.
#
# Разбор: `devref/gaps/docs/g83_a_printed_number_nobody_rechecked_2026-10.md`.

#: Утверждение на той же строке: `print(len(result.zones))   # 32`.
_TAIL_CLAIM_RE = re.compile(r"\)\s*#\s*(?P<claim>\S.*?)\s*$")


def _claims(code: str) -> list[tuple[int, int, str]]:
    """`[(первая строка вызова, последняя строка вызова, утверждение), ...]`.

    Берётся **только хвостовая** форма — комментарий в конце самого вызова. Вторая
    форма (комментарий отдельной строкой под вызовом) в доке встречается не реже, и
    попытка брать и её провалилась предметно: под `print` стоит и проза
    («ниже то же через схему»), и ожидание, и отличить их механически нечем. Результат
    был 87 падений, из которых настоящими оказались единицы — остальные привязывали
    ожидание к чужому вызову. Сторож с такой долей ложного хуже отсутствующего: его
    начинают отключать.

    Цена решения названа прямо: **утверждения второй формы не проверяются**, и их в
    доке больше, чем проверяемых. Перенос комментария на строку ниже выводит
    утверждение из-под сторожа. Закрывается это не регуляркой, а соглашением в доке
    (ожидание пишется в хвосте вызова) — отдельным решением, не этой правкой.
    Разбор ``ast`` оставлен: он правильно находит границы многострочного вызова, чего
    строчная регулярка не умела.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # предмет `test_a_python_fence_contains_python`, не этого теста

    lines = code.splitlines()
    calls = sorted(
        (node.lineno, node.end_lineno or node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "print"
    )

    found = []
    for start, end in calls:
        tail = _TAIL_CLAIM_RE.search(lines[end - 1])
        if tail:
            found.append((start, end, tail.group("claim")))
            continue
    return found


def _claim_is_met(claim: str, printed: str) -> bool:
    """Выполнено ли утверждение напечатанным текстом.

    Сравнение **не** построчно-дословное, и это не снисходительность, а форма
    утверждений в доке: `print(f"Найдено зон: {len(result.zones)}")   # 64` печатает
    «Найдено зон: 64», а утверждает про `64`. Поэтому утверждение обязано
    **содержаться** в напечатанном.

    У чистого целого числа containment пришлось бы сузить: `30` нашлось бы в `300`
    и в `0.30`. Для него требуется граница — иначе сторож пропускал бы ровно те
    расхождения, за которыми заведён (протухшие счётчики зон).

    Утверждение, оборванное многоточием (список, который в доке не дописан), сверяется
    по своему началу: дока имеет право сократить вывод, но не переврать его начало.
    """
    expected = " ".join(claim.split())
    actual = " ".join(printed.split())
    if expected.endswith(("...", "…")):
        return expected.rstrip("… .") in actual
    if re.fullmatch(r"-?\d+", expected):
        return re.search(rf"(?<![\w.]){re.escape(expected)}(?![\w.])", actual) is not None
    return expected in actual


#: Обёртка, в которой пример исполняется **отдельным процессом**.
#:
#: Почему не в общем: каталог индикаторов наполняется лениво и общий на процесс, поэтому
#: примеры, регистрирующие свои индикаторы, меняли ответ соседям — пример из
#: `api/README.md` печатал 167 имён вместо 164, и выглядело это протухшим числом в доке.
#: Снимать и восстанавливать этот реестро нельзя (проверено: ленивая загрузка плюс флаг
#: «уже загружено» дают 62 падения). Отдельный процесс снимает вопрос целиком — и, что
#: важнее, совпадает с тем, как пример запускает читатель: с нуля, а не тридцатым в ряду.
_RUNNER = """
import builtins, io, json, sys
sys.argv = ["example.py", "--no-trap"]
_recorded = []
_real = builtins.print


def _rec(*args, **kwargs):
    kwargs.pop("file", None)
    sink = io.StringIO()
    _real(*args, file=sink, **kwargs)
    _recorded.append([sys._getframe(1).f_lineno, sink.getvalue().rstrip("\\n")])


builtins.print = _rec
_code = {code!r}
try:
    exec(compile(_code, "example", "exec"),
         {{"__name__": "__main__", "__file__": "example.py", "print": _rec}})
finally:
    builtins.print = _real
    _real("{marker}" + json.dumps(_recorded, ensure_ascii=False))
"""

_CLAIM_MARKER = "<<<RECORDED-PRINTS>>>"


def _run_and_record(code: str, workdir) -> dict[int, list[str]] | None:
    """Исполнить пример в отдельном процессе и вернуть вывод по строкам вызова.

    ``None`` — пример не доехал до конца; это предмет соседнего теста, не этого.
    """
    script = workdir / "runner.py"
    script.write_text(_RUNNER.format(code=code, marker=_CLAIM_MARKER), encoding="utf-8")

    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    environment["MPLBACKEND"] = "Agg"

    finished = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(workdir), env=environment, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=600,
    )
    for line in finished.stdout.splitlines():
        if line.startswith(_CLAIM_MARKER):
            by_line: dict[int, list[str]] = {}
            for lineno, text in json.loads(line[len(_CLAIM_MARKER):]):
                by_line.setdefault(lineno, []).append(text)
            return by_line
    return None


CLAIMING_EXAMPLES = [
    (rel, line, code, claims)
    for rel, line, code in EXAMPLES
    if (claims := _claims(code))
]

#: Пол охвата, замеренный 2026-10-15: 42 хвостовых утверждения в самодостаточных
#: примерах. Утверждений второй формы (комментарий под вызовом) в доке больше, и они
#: здесь НЕ проверяются — см. докстроку `_claims`.
#: Пол ловит **обвал** разбора, а не дрейф на одно-два утверждения от правки текста:
#: без него сломавшаяся регулярка даёт пустой список, все проверки становятся
#: вырожденно зелёными, и отчёт сообщает ни о чём.
MIN_PRINTED_CLAIMS = 35


def test_the_scan_found_printed_claims():
    """Положительный контроль: пустой разбор не имеет права пройти как чистая дока."""
    total = sum(len(claims) for *_, claims in CLAIMING_EXAMPLES)
    assert total >= MIN_PRINTED_CLAIMS, (
        f"найдено {total} утверждений о напечатанном при поле {MIN_PRINTED_CLAIMS}; "
        f"похоже, сломался разбор, а не похудела дока"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "rel, line, code, claims",
    CLAIMING_EXAMPLES,
    ids=[f"{rel}:{line}" for rel, line, _, _ in CLAIMING_EXAMPLES],
)
def test_a_printed_number_is_a_measured_number(rel, line, code, claims, tmp_path):
    """Что пример печатает, то дока и обязана обещать.

    Исполняется отдельным процессом — см. ``_RUNNER``. Примеры из `EXPECTED_TO_FAIL`
    пропускаются: пример, который обязан упасть, ничего не печатает. Исключение не
    слепое — у реестра есть свои два сторожа: запись, указывающая в никуда, краснеет,
    и пример, числящийся падающим и отработавший, краснеет тоже.
    """
    if _expected_reason(rel, code):
        pytest.skip("пример заявлен падающим — печатать ему нечего")

    recorded = _run_and_record(code, tmp_path)
    if recorded is None:
        pytest.skip(
            "пример не доехал до конца — это предмет "
            "test_a_self_contained_doc_example_runs, здесь дублировать нечего"
        )

    wrong, silent = [], []
    for start, end, claim in claims:
        # Вызов может занимать несколько строк, а номер строки во фрейме указывает
        # не обязательно на первую из них — поэтому ищем по всему диапазону вызова.
        printed = [text for lineno in range(start, end + 1)
                   for text in recorded.get(lineno, [])]
        if not printed:
            silent.append(f"строка {start}: обещано {claim!r}, но ничего не напечатано")
            continue
        if not any(_claim_is_met(claim, text) for text in printed):
            wrong.append(
                f"строка {start}: обещано {claim!r}, напечатано "
                + " | ".join(repr(t[:120]) for t in printed)
            )

    assert not (wrong or silent), (
        f"{rel}:{line} — документированный вывод не совпал с прогоном:\n  "
        + "\n  ".join(wrong + silent)
        + "\nЧисла в доке берутся прогоном (AGENTS.md). Перемерьте и впишите измеренное."
    )
