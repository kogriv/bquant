"""No two public classes in the package may share a name (G8 stage B).

`bquant.analysis.zones` and `bquant.indicators` both exported a class called
`IndicatorConfig`, and they were different dataclasses: one described a
*computed* indicator (`name/parameters/source/columns/description`), the other a
*request to compute* one (`source/name/params`). One called its parameter dict
`parameters`, the other `params`. Both were public — 19 and 15 uses outside the
package — so a reader had to infer from context which one an example meant.

That is the column-name defect one level up: the label carried no identity, and
the mapping from label to meaning lived nowhere. The request-shaped one is now
`IndicatorSpec`, and both use `parameters`.

The sweep below is the general guard: it walks the public API surface and fails
on any name exported from two places with two different objects behind it.

Design: ``devref/gaps/columns/g8_column_contract_design_2026-08-23.md`` §4.6
"""

import importlib
import pkgutil

import pytest

import bquant


def _public_modules():
    """Every importable module under `bquant`, skipping private ones."""
    modules = [bquant]
    for info in pkgutil.walk_packages(bquant.__path__, prefix="bquant."):
        if any(part.startswith("_") for part in info.name.split(".")):
            continue
        try:
            modules.append(importlib.import_module(info.name))
        except Exception:
            # Optional dependencies (talib and friends) may be absent; a module
            # that cannot be imported exports nothing and cannot collide.
            continue
    return modules


# Коллизии, известные на 2026-08-24. Список существует, чтобы падать на НОВЫХ,
# а не чтобы прятать эти: каждая записана с причиной, по которой пока оставлена.
# Разбор — G22 в devref/gaps/gap_inventory_2026-07.md.
KNOWN_COLLISIONS = {
    # Обёртки с мягкой деградацией: родительский пакет отдаёт заглушку, если
    # подмодуль недоступен, и делегирует ему, если доступен. Нормальный приём,
    # в сканер попадают лишь потому, что обёртка — отдельный объект функции.
    "get_available_themes": "wrapper in bquant.visualization delegates to .themes",
    "get_dataset_info": "wrapper in bquant.data.samples delegates to .datasets",
    # Настоящие тёзки — разные функции/классы под одним публичным именем.
    "ValidationResult": "two unrelated dataclasses: analysis.validation.suite and data.schemas",
    "get_data_info": "different signatures: data.loader (a frame) vs data.samples.utils (a dataset)",
    "extract_zone_features": "bquant.ml exports a stub that always raises NotImplementedError",
}


def test_no_new_public_name_collisions():
    """The sweep that caught the IndicatorConfig collision.

    Two public classes with one name is the column-name defect one level up: the
    label carries no identity, and a reader has to infer from context which one
    an example means.

    Dunder names are skipped — `__version__` differs per subpackage by design.
    """
    seen = {}
    collisions = {}

    for module in _public_modules():
        for name in getattr(module, "__all__", []):
            if name.startswith("__"):
                continue
            obj = getattr(module, name, None)
            if obj is None:
                continue
            if name in seen and seen[name][1] is not obj:
                collisions.setdefault(name, [seen[name]]).append((module.__name__, obj))
            else:
                seen.setdefault(name, (module.__name__, obj))

    new = {n: e for n, e in collisions.items() if n not in KNOWN_COLLISIONS}
    assert not new, "public names bound to two different objects:\n" + "\n".join(
        f"  {name}: " + ", ".join(f"{where}.{name}" for where, _ in entries)
        for name, entries in sorted(new.items())
    )


def test_known_collisions_are_still_real():
    """If one gets fixed, drop it from the list rather than leaving it stale.

    Without this the allow-list would quietly outlive the problems it excuses —
    which is how a stale registry entry misled two releases in this project.
    """
    seen = {}
    still_colliding = set()

    for module in _public_modules():
        for name in getattr(module, "__all__", []):
            if name.startswith("__"):
                continue
            obj = getattr(module, name, None)
            if obj is None:
                continue
            if name in seen and seen[name][1] is not obj:
                still_colliding.add(name)
            else:
                seen.setdefault(name, (module.__name__, obj))

    resolved = set(KNOWN_COLLISIONS) - still_colliding
    assert not resolved, (
        f"these no longer collide and should be removed from KNOWN_COLLISIONS: "
        f"{sorted(resolved)}"
    )


def test_indicator_spec_and_indicator_config_are_distinct():
    """The specific case, pinned by name so the intent survives a refactor."""
    from bquant.analysis.zones import IndicatorSpec
    from bquant.indicators import IndicatorConfig

    assert IndicatorSpec is not IndicatorConfig
    assert IndicatorSpec.__name__ == "IndicatorSpec"

    with pytest.raises(ImportError):
        from bquant.analysis.zones import IndicatorConfig  # noqa: F401


def test_both_call_their_parameter_dict_parameters():
    """They disagreed: `params` here, `parameters` there."""
    import dataclasses

    from bquant.analysis.zones import IndicatorSpec
    from bquant.indicators import IndicatorConfig

    for cls in (IndicatorSpec, IndicatorConfig):
        names = {f.name for f in dataclasses.fields(cls)}
        assert "parameters" in names, f"{cls.__name__} fields: {sorted(names)}"
        assert "params" not in names, (
            f"{cls.__name__} still carries the short spelling alongside the long one"
        )
