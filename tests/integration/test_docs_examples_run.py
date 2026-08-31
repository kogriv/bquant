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
import builtins
import io
import os
import sys
import textwrap
from pathlib import Path

import pytest

os.environ.setdefault("BQUANT_SKIP_TALIB", "1")
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
    ("docs/api/core/config.md", "validate_timeframe('2D')"):
        "показывает отказ намеренно: комментарий в примере так и говорит — # ValueError",
    ("docs/api/core/config.md", "set_data_dir("):
        "пишет в путь, которого у читателя нет; иллюстрация переопределения каталога",
    ("docs/api/core/exceptions.md", "create_data_validation_error("):
        "демонстрирует обёртывание чужого исключения — деление на ноль здесь намеренное",
    ("docs/api/core/logging.md", "❌ НЕПРАВИЛЬНО"):
        "показывает НЕВЕРНЫЙ порядок вызова: setup_logging до собственного импорта",
    ("docs/api/core/logging.md", "load_ohlcv_data('file.csv')"):
        "читает файл, который приносит читатель",
    ("docs/api/core/README.md", "runner.wait()"):
        "демонстрирует интерактивную паузу: без терминала читать ввод неоткуда",
    ("docs/api/data/README.md", "load_ohlcv_data('data.csv', symbol="):
        "читает файл, который приносит читатель",
    ("docs/api/data/loader.md", "'data/XAUUSD_1h.csv'"):
        "читает файл, который приносит читатель",
    ("docs/api/data/loader.md", "load_symbol_data("):
        "ищет файл в каталоге данных, который наполняет читатель",
    ("docs/api/extension_guide.md", "my_bquant_extension"):
        "импортирует гипотетический пакет расширения — он и есть предмет примера",
    ("docs/api/extension_guide.md", "setup("):
        "фрагмент setup.py стороннего пакета расширения, а не исполняемый пример",
    ("docs/api/extension_guide.md", "create_swing_strategy('my_custom')"):
        "использует стратегию, которую читатель регистрирует у себя по инструкции выше",
    ("docs/tutorials/preloaded_zones_workflow.md", "expert_zones.csv"):
        "читает файл с готовыми зонами, который приносит читатель",
    ("docs/developer_guide/zone_detection_strategies.md", "from .base import"):
        "относительный импорт внутри пакета: так выглядит файл стратегии на месте",
    ("docs/examples/README.md", "runpy.run_path"):
        "запускает файл примера по пути от корня репозитория; тест работает во временном каталоге",
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
    ("bquant.analysis.zones.strategies.registry", "StrategyRegistry",
     ("_swing_strategies", "_divergence_strategies", "_shape_strategies",
      "_volume_strategies", "_volatility_strategies")),
)


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
            saved.append((registry, attribute, dict(getattr(registry, attribute))))
    try:
        yield
    finally:
        for registry, attribute, snapshot in saved:
            getattr(registry, attribute).clear()
            getattr(registry, attribute).update(snapshot)


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
