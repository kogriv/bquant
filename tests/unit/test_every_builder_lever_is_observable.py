"""Каждая ручка билдера обязана менять наблюдаемое — или объявить, что не должна (G71).

Так `validation=True` и прожил как no-op: сьют проверял, что параметр **принимается**,
а не что он что-то делает (AQ-009). Узкие сторожа есть на каждую находку по отдельности —
G53 (кэш), G54 (один детектор), G55 (валидация исполняется), G35 (ноль свингов громкий),
G48 (авто-порог), G21 (`min_duration`), G36 (стратегии в ключе кэша), — но одного места,
где каждая ручка проверяется одинаково, не было. Пока такого места нет, следующая
добавленная ручка снова может приниматься и ничего не делать.

**Что здесь утверждается — различие, а не числа.** Пиннинг конкретных величин («30 зон
против 77») превратил бы файл в музей цифр, который краснеет от любой честной правки и
который начнут молча обновлять — то есть в ту же проверку, которая ничего не проверяет.
Поэтому каждая строка говорит только: наблюдаемое **разошлось** — или **обязано совпасть**,
и тогда рядом написано почему.

Область — флагманский путь `analyze_zones → build()`, а не 362 публичных имени.
Расширение на CLI и пресеты — отдельная работа.
"""

from typing import Any, Callable, Dict, List, Tuple

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def data():
    # 400 баров: достаточно для зон, свингов и кластеризации, но втрое дешевле
    # полного сэмпла — таблица гоняет два прогона на строку.
    return get_sample_data("tv_xauusd_1h").head(400)


def _run(data, *, indicator=None, role="line", strategies=None, preset="narrow_zone",
         auto_thresholds=False, atr_period=14, scope="global", cache=False,
         analyze_kwargs=None):
    """Один прогон флагманского пути с явно названными ручками."""
    indicator = indicator or {"fast_period": 12, "slow_period": 26, "signal_period": 9}
    strategies = strategies if strategies is not None else {"swing": "zigzag"}
    analyze_kwargs = analyze_kwargs or {"clustering": False}

    builder = (
        analyze_zones(data)
        .with_indicator("custom", "macd", **indicator)
        .detect_zones("zero_crossing", indicator_role=role)
        .with_strategies(**strategies)
        .with_swing_preset(preset)
        .with_auto_swing_thresholds(auto_thresholds)
        .with_atr_period(atr_period)
        .with_swing_scope(scope)
        .with_cache(enable=cache)
    )
    return builder.analyze(**analyze_kwargs).build()


# --- наблюдаемые: только структура и относительные величины, без пиннинга чисел


def zone_count(result) -> int:
    return len(result.zones)


def swings_per_zone(result) -> Tuple[int, ...]:
    return tuple(
        ((z.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}).get("num_swings", 0)
        for z in result.zones
    )


def swing_strategy(result) -> str:
    for zone in result.zones:
        name = ((zone.features or {}).get("metadata", {}).get("swing_metrics", {}) or {}).get(
            "strategy_name"
        )
        if name:
            return name
    return "none"


def metric_blocks(result) -> Tuple[str, ...]:
    seen = set()
    for zone in result.zones:
        seen.update((zone.features or {}).get("metadata", {}).keys())
    return tuple(sorted(seen))


def atr_normalised(result) -> Tuple[Any, ...]:
    return tuple((z.features or {}).get("atr_normalized_return") for z in result.zones)


def clustering_shape(result):
    return None if result.clustering is None else tuple(sorted(result.clustering))


def cluster_label_count(result) -> int:
    if not result.clustering:
        return 0
    labels = result.clustering.get("cluster_labels")
    if isinstance(labels, dict):
        labels = list(labels.values())
    return len(set(labels or []))


def regression_flag(result):
    """Статус, а не булев флаг: «просили и не смогли» — не то же, что «не просили»."""
    return ((result.metadata or {}).get("regression") or {}).get("status")


def validation_state(result):
    return ((result.metadata or {}).get("validation") or {}).get("status")


def duration_filter(result):
    filtered = (result.metadata or {}).get("duration_filter") or {}
    return (filtered.get("min_duration"), filtered.get("zones_excluded"))


#: имя, конфигурация A, конфигурация B, наблюдаемое, ожидание
LEVERS: List[Dict[str, Any]] = [
    {
        "name": "with_indicator(parameters)",
        "a": {"indicator": {"fast_period": 12, "slow_period": 26, "signal_period": 9}},
        "b": {"indicator": {"fast_period": 8, "slow_period": 21, "signal_period": 5}},
        "observable": zone_count,
    },
    {
        "name": "detect_zones(indicator_role)",
        "a": {"role": "line"},
        "b": {"role": "hist"},
        "observable": zone_count,
    },
    {
        "name": "with_strategies(swing)",
        "a": {"strategies": {"swing": "zigzag"}},
        "b": {"strategies": {"swing": "find_peaks"}},
        "observable": swing_strategy,
    },
    {
        "name": "with_swing_scope",
        "a": {"scope": "global"},
        "b": {"scope": "per_zone"},
        "observable": swings_per_zone,
    },
    {
        "name": "with_swing_preset",
        "a": {"preset": "narrow_zone"},
        "b": {"preset": "wide_zone"},
        "observable": swings_per_zone,
    },
    {
        "name": "with_auto_swing_thresholds",
        "a": {"strategies": {"swing": "find_peaks"}, "auto_thresholds": False},
        "b": {"strategies": {"swing": "find_peaks"}, "auto_thresholds": True},
        "observable": swings_per_zone,
    },
    {
        "name": "with_atr_period",
        "a": {"atr_period": 14},
        "b": {"atr_period": 28},
        "observable": atr_normalised,
    },
    {
        "name": "analyze(clustering)",
        "a": {"analyze_kwargs": {"clustering": False}},
        "b": {"analyze_kwargs": {"clustering": True, "n_clusters": 3}},
        "observable": clustering_shape,
    },
    {
        "name": "analyze(n_clusters)",
        "a": {"analyze_kwargs": {"clustering": True, "n_clusters": 2}},
        "b": {"analyze_kwargs": {"clustering": True, "n_clusters": 4}},
        "observable": cluster_label_count,
    },
    {
        "name": "analyze(regression)",
        "a": {"analyze_kwargs": {"clustering": False, "regression": False}},
        "b": {"analyze_kwargs": {"clustering": False, "regression": True}},
        "observable": regression_flag,
    },
    {
        "name": "analyze(validation)",
        "a": {"analyze_kwargs": {"clustering": False, "validation": False}},
        "b": {"analyze_kwargs": {"clustering": False, "validation": True}},
        "observable": validation_state,
    },
    {
        "name": "analyze(min_duration)",
        "a": {"analyze_kwargs": {"clustering": False, "min_duration": 1}},
        "b": {"analyze_kwargs": {"clustering": False, "min_duration": 6}},
        "observable": duration_filter,
    },
    {
        "name": "with_strategies(volume)",
        "a": {"strategies": {"swing": "zigzag"}},
        "b": {"strategies": {"swing": "zigzag", "volume": "standard"}},
        "observable": metric_blocks,
    },
    {
        "name": "with_strategies(volatility)",
        "a": {"strategies": {"swing": "zigzag"}},
        "b": {"strategies": {"swing": "zigzag", "volatility": "combined"}},
        "observable": metric_blocks,
    },
    {
        "name": "with_strategies(divergence)",
        "a": {"strategies": {"swing": "zigzag"}},
        "b": {"strategies": {"swing": "zigzag", "divergence": "classic"}},
        "observable": metric_blocks,
    },
]

#: Ручки, которые совпадать ОБЯЗАНЫ, и причина — иначе «не различается» читается
#: как дефект, а это осознанное свойство.
DELIBERATELY_IDENTICAL: List[Dict[str, Any]] = [
    {
        "name": "with_strategies(shape)",
        "a": {"strategies": {"swing": "zigzag"}},
        "b": {"strategies": {"swing": "zigzag", "shape": "statistical"}},
        "observable": metric_blocks,
        "why": "`shape=None` — это умолчание конфигурации, а не выключатель: "
               "`StatisticalShapeStrategy` подставляется в обоих случаях. Выключить "
               "форму билдер не даёт, и это его свойство, а не дефект.",
    },
    {
        "name": "with_cache",
        "a": {"cache": False},
        "b": {"cache": True},
        "observable": swings_per_zone,
        "why": "Кэш обязан отдавать тот же ответ, что и расчёт. Различие здесь было бы "
               "дефектом ключа (G53), а не действием ручки.",
    },
]


@pytest.mark.parametrize("lever", LEVERS, ids=lambda item: item["name"])
def test_the_lever_changes_something_observable(data, lever):
    """Два прогона, одна разница в конфигурации — наблюдаемое обязано разойтись."""
    first = lever["observable"](_run(data, **lever["a"]))
    second = lever["observable"](_run(data, **lever["b"]))

    assert first != second, (
        f"{lever['name']}: наблюдаемое не изменилось ({first!r}). Либо ручка ничего не "
        f"делает, либо наблюдаемое выбрано не то — разберитесь, что именно, прежде чем "
        f"переносить строку в DELIBERATELY_IDENTICAL."
    )


@pytest.mark.parametrize("lever", DELIBERATELY_IDENTICAL, ids=lambda item: item["name"])
def test_the_lever_deliberately_changes_nothing(data, lever):
    """Совпадение здесь — объявленное свойство, и причина написана рядом."""
    first = lever["observable"](_run(data, **lever["a"]))
    second = lever["observable"](_run(data, **lever["b"]))

    assert first == second, f"{lever['name']}: ожидалось совпадение. {lever['why']}"


def test_the_table_covers_the_builder_surface():
    """Новая ручка обязана появиться в таблице, иначе сторож её не заметит."""
    covered = {row["name"].split("(")[0] for row in LEVERS + DELIBERATELY_IDENTICAL}

    from bquant.analysis.zones.pipeline import ZoneAnalysisBuilder

    surface = {
        name
        for name in dir(ZoneAnalysisBuilder)
        if name.startswith("with_") or name in {"detect_zones", "analyze"}
    }
    # `with_indicator` покрыт параметрами, `analyze` — четырьмя своими флагами.
    missing = surface - covered
    assert not missing, (
        f"ручки билдера без строки в таблице: {sorted(missing)}. Добавьте строку с "
        f"наблюдаемым — или в DELIBERATELY_IDENTICAL с причиной."
    )
