"""Гигиена репозитория держится сторожем, а не памятью (G67, AQ-048…050, 052, 054, 055).

Замер до правки (2026-09-06):

* мёртвое: `_StubIndicator` (ни одного использования), `bquant.core.exceptions.NotImplementedError`
  (перекрывал встроенное имя, никем не поднимался), `ensure_logging_initialized()` (без
  вызывающих), `try: pass / except: pass` в `indicators/library/__init__.py`, вторая полная
  настройка логирования в `core/utils.py`, ставившая обработчики на импорте — при том, что
  документация называла её «тонкой обёрткой над `setup_logging()`»;
* `calculate_with_cache()` с телом `calculate()` и словом «кэш» в имени;
* `get_zone_features_summary()` знал только `bull`/`bear` и отвечал `{'error': …}`;
* каталог `devref/gaps/zo/zodoctest/` с `test_*.py` под `MACDZoneAnalyzer`, удалённый в 0.0.5,
  и три документа в `tests/` про сьют 2025-10 («670 passed, production-ready») — один из них
  и README архива несли имя личного окружения;
* сканер публичной поверхности разбирал только литерал `__all__ = [...]` и не видел
  `__all__.extend([...])`: 12 имён шли мимо проверки, 9 не были упомянуты в доках;
* `set_default_theme('nope')` возвращал `True`.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "bquant"


def _foreign(path: Path) -> bool:
    """Чужое дерево внутри репозитория: любое окружение, сборка доков, кэши, git."""
    return any(
        part in ("_build", "__pycache__", "site-packages", "node_modules", ".git")
        or part.startswith((".venv", "venv"))
        for part in path.parts
    )


def _python_files(*roots: Path):
    for root in roots:
        for path in root.rglob("*.py"):
            if not _foreign(path):
                yield path


# --- AQ-048 / AQ-054: dead names stay dead -----------------------------------

@pytest.mark.parametrize("name", ["_StubIndicator", "ensure_logging_initialized", "calculate_with_cache"])
def test_a_removed_name_is_not_defined_anywhere_in_the_package(name):
    defined = [
        f"{path.relative_to(ROOT)}:{node.lineno}"
        for path in _python_files(PACKAGE)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    assert defined == [], defined


def test_no_package_exception_shadows_a_builtin():
    import builtins

    import bquant.core.exceptions as exceptions

    shadowing = sorted(
        name for name, obj in vars(exceptions).items()
        if isinstance(obj, type) and issubclass(obj, BaseException)
        and obj.__module__ == exceptions.__name__ and hasattr(builtins, name)
    )
    assert shadowing == [], shadowing


def test_no_module_level_try_pass_block_in_the_package():
    offenders = []
    for path in _python_files(PACKAGE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Try) and all(isinstance(s, ast.Pass) for s in node.body):
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert offenders == [], offenders


def test_setup_project_logging_is_the_thin_wrapper_the_docs_describe():
    import bquant.core.logging_config as logging_config
    from bquant.core.utils import setup_project_logging

    calls = []
    original = logging_config.setup_logging
    logging_config.setup_logging = lambda **kwargs: calls.append(kwargs) or original(**kwargs)
    try:
        logger = setup_project_logging(name="bquant.g67", level="WARNING")
    finally:
        logging_config.setup_logging = original
    assert logger.name == "bquant.g67" and isinstance(logger, logging.Logger)
    assert calls and calls[0]["level"] == "WARNING", "setup_project_logging did not delegate to setup_logging"


def test_core_utils_does_not_set_up_logging_at_import():
    """Модульный логгер — `get_logger()`; настройка логирования на импорте — побочный
    эффект, который до G67 вешал обработчики любому, кто импортировал утилиты."""
    tree = ast.parse((PACKAGE / "core" / "utils.py").read_text(encoding="utf-8"))
    calls = [
        f"{ast.unparse(call.func)}() at line {call.lineno}"
        for node in tree.body
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and ast.unparse(call.func).split(".")[-1] in ("setup_project_logging", "setup_logging")
    ]
    assert calls == [], f"logging is configured at import of bquant.core.utils: {calls}"


# --- AQ-050 -----------------------------------------------------------------

def test_the_zone_summary_groups_every_type_and_refuses_an_empty_list():
    from bquant.analysis.zones import ZoneFeaturesAnalyzer

    rows = [
        {"zone_type": "overbought", "duration": 4, "price_return": 0.01},
        {"zone_type": "oversold", "duration": 6, "price_return": -0.02},
        {"zone_type": "neutral", "duration": 10, "price_return": 0.0},
    ]
    summary = ZoneFeaturesAnalyzer().get_zone_features_summary(rows)
    assert sorted(summary["by_type"]) == ["neutral", "overbought", "oversold"]
    assert summary["by_type"]["oversold"] == {"zones": 1, "avg_duration": 6.0, "avg_return": -0.02}
    assert summary["positive_returns"] == 1 and summary["negative_returns"] == 1
    with pytest.raises(ValueError, match="no zone features"):
        ZoneFeaturesAnalyzer().get_zone_features_summary([])


# --- AQ-052 -----------------------------------------------------------------

def test_no_test_file_lives_outside_the_test_suite():
    strays = sorted(
        str(path.relative_to(ROOT)) for path in ROOT.rglob("test_*.py")
        if not path.is_relative_to(ROOT / "tests")
        and not _foreign(path.relative_to(ROOT))
        and "zodoctest_archive" not in path.parts
    )
    assert strays == [], f"test_*.py outside tests/ reads as a suite that is not run: {strays}"


def test_the_removed_analyzer_is_not_imported_by_any_script():
    imports = []
    for path in _python_files(PACKAGE, ROOT / "tests", ROOT / "examples", ROOT / "research", ROOT / "scripts"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and any(a.name == "MACDZoneAnalyzer" for a in node.names):
                imports.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert imports == [], imports


# --- AQ-049 / AQ-055: exported means documented and working ---------------------

def test_the_doc_guard_reads_the_executed_all():
    from tests.unit.test_public_surface_is_documented import REEXPORTED

    for name in ("plot_macd_zones_chart", "analyze_zones_visually", "DistributionPlotter",
                 "TransitionAnalysis", "cluster_zone_shapes"):
        assert name in REEXPORTED, f"{name} is exported through __all__.extend and the guard must see it"


def test_set_default_theme_refuses_an_unknown_theme():
    from bquant.visualization import set_default_theme
    from bquant.visualization.themes import _theme_manager

    current = _theme_manager._current_theme
    try:
        assert set_default_theme("bquant_light") is True
        with pytest.raises(ValueError, match="Unknown theme"):
            set_default_theme("nope")
    finally:
        _theme_manager._current_theme = current


def test_the_consumer_less_exports_produce_figures():
    pytest.importorskip("plotly")
    from bquant.analysis.zones import analyze_zones
    from bquant.data.samples import get_sample_data
    from bquant.visualization import DistributionPlotter, analyze_zones_visually, plot_macd_zones_chart

    data = get_sample_data("tv_xauusd_1h")
    result = (analyze_zones(data)
              .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
              .detect_zones("zero_crossing", indicator_role="hist")
              .with_cache(enable=False).analyze(clustering=False).build())
    assert len(plot_macd_zones_chart(result.data, result.zones).data) >= 2
    assert len(analyze_zones_visually(result.zones).data) >= 1
    assert DistributionPlotter().plot_multiple_distributions(data, ["open", "close"]) is not None
