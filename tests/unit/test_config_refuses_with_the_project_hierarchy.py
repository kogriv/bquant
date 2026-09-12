"""`bquant.core.config` refuses with the project's exception hierarchy, not with ValueError.

The rule is in AGENTS.md and the classes were defined for exactly this — yet
`InvalidTimeframeError` sat in `bquant/core/exceptions.py` from the beginning with not a
single caller, while `config.validate_timeframe` raised a bare `ValueError`. The backlog
named the deviation on 2026-08-28 and deferred it as "not a passing fix"; by 2026-09-12 it
had grown from five sites to seven, two of them added by G77's own refusals.

This is a **breaking** change and the tests say so out loud: an `except ValueError` written
against the old behaviour no longer catches. Dual inheritance from ValueError would have
kept those handlers working and was rejected — it is the softening this project does not do.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from bquant.core.config import get_data_path, set_data_dir, validate_timeframe
from bquant.core.exceptions import BQuantError, ConfigurationError, InvalidTimeframeError

CONFIG_SOURCE = Path(__file__).resolve().parents[2] / "bquant" / "core" / "config.py"


def test_an_unsupported_timeframe_raises_the_class_defined_for_it():
    with pytest.raises(InvalidTimeframeError) as excinfo:
        validate_timeframe("7x")

    error = excinfo.value
    assert isinstance(error, ConfigurationError)
    assert isinstance(error, BQuantError)
    assert error.details["timeframe"] == "7x"
    assert "1h" in error.details["supported_timeframes"]


@pytest.mark.parametrize(
    "kwargs",
    [{"data_source": "no_such_source"}, {"quote_provider": "no_such_provider"}],
)
def test_an_unknown_path_argument_raises_a_configuration_error(kwargs):
    with pytest.raises(ConfigurationError) as excinfo:
        get_data_path("XAUUSD", "1h", **kwargs)
    assert excinfo.value.details["actual_value"] in kwargs.values()


@pytest.mark.parametrize(
    "call",
    [
        lambda: validate_timeframe("7x"),
        lambda: get_data_path("XAUUSD", "1h", data_source="no_such_source"),
    ],
)
def test_the_old_handler_no_longer_catches_and_that_is_the_break(call):
    """Stated as a test because it is the cost of the change, not a side effect."""
    with pytest.raises(BQuantError):
        try:
            call()
        except ValueError:  # what a caller wrote before 2026-09-12
            pytest.fail("a bare ValueError handler still catches; the hierarchy is not in use")


def test_the_module_raises_no_bare_value_error_anywhere():
    """The check that keeps the deviation from growing back, site by site."""
    tree = ast.parse(CONFIG_SOURCE.read_text(encoding="utf-8"))
    bare = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and isinstance(node.exc.func, ast.Name)
        and node.exc.func.id in {"ValueError", "TypeError", "KeyError", "RuntimeError"}
    ]
    assert not bare, f"builtin exceptions raised in config.py at lines {bare}"


def test_a_valid_call_still_returns(tmp_path):
    """Positive control: the refusals above must not be a blanket refusal."""
    assert validate_timeframe("1h") == "1h"
    assert get_data_path("XAUUSD", "1h").name

    fresh = tmp_path / "fresh"
    assert set_data_dir(fresh) is None
    assert fresh.is_dir()
