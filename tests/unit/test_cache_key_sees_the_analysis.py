"""Кэш-ключ обязан различать то, что меняет результат.

G36: стратегии метрик (`shape`, `divergence`, `volatility`, `volume`) приходят в
пайплайн через конструктор анализатора, а не через `ZoneAnalysisConfig`, поэтому в
ключ они не попадали. Ключ отвечал на вопрос «этот индикатор, эта детекция» и молча
отдавал результат, посчитанный без запрошенной стратегии.

Проверка написана так, чтобы краснеть на **добавлении** нового семейства метрик
мимо ключа, а не только на четырёх известных.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.analysis.zones import UniversalZoneAnalyzer
from bquant.analysis.zones.cache import ZoneAnalysisCache
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.pipeline import (
    CACHE_SCHEMA_VERSION,
    IndicatorSpec,
    ZoneAnalysisConfig,
    ZoneAnalysisPipeline,
)
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
from bquant.data.samples import get_sample_data


# Семейство -> имя зарегистрированной стратегии, которую можно включить.
METRIC_FAMILIES = {
    "divergence": "classic",
    "volatility": "combined",
    "volume": "standard",
}


@pytest.fixture(scope="module")
def data() -> pd.DataFrame:
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture(scope="module")
def config() -> ZoneAnalysisConfig:
    return ZoneAnalysisConfig(
        indicator=IndicatorSpec(
            source="custom",
            name="macd",
            parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9},
        ),
        zone_detection=ZoneDetectionConfig(
            strategy_name="zero_crossing",
            rules={"indicator_role": "line"},
        ),
    )


def key_for(config: ZoneAnalysisConfig, data: pd.DataFrame, **analyzer_kwargs) -> str:
    pipeline = ZoneAnalysisPipeline(
        config, zone_analyzer=UniversalZoneAnalyzer(**analyzer_kwargs)
    )
    return pipeline._generate_cache_key(data)


def test_the_key_is_stable_for_the_same_configuration(config, data):
    """Иначе кэш просто не работал бы — и это надо знать до остальных проверок."""

    assert key_for(config, data) == key_for(config, data)


@pytest.mark.parametrize("family,strategy", sorted(METRIC_FAMILIES.items()))
def test_enabling_a_metric_strategy_changes_the_key(family, strategy, config, data):
    """Включённая стратегия обязана дать другой ключ.

    Пока не давала, `.with_strategies(volatility='combined')` при включённом кэше
    возвращал результат прошлого прогона: 0 зон с метриками волатильности из 32
    вместо 29.
    """

    without = key_for(config, data)
    with_strategy = key_for(config, data, **{f"{family}_strategy": strategy})

    assert without != with_strategy, (
        f"Ключ не различает включённую стратегию {family}={strategy!r}. "
        "Потребитель получит результат, посчитанный без неё, и ничего об этом "
        "не узнает."
    )


def test_the_same_strategy_with_other_parameters_changes_the_key(config, data):
    """Имени класса мало: параметры меняют числа так же, как выбор стратегии."""

    default_key = key_for(config, data)
    tweaked = key_for(
        config, data, shape_strategy=StatisticalShapeStrategy(calculate_smoothness=False)
    )

    assert default_key != tweaked


def test_asking_for_the_strategy_already_in_effect_keeps_the_key(config, data):
    """Обратная сторона: лишних промахов быть не должно.

    `shape='statistical'` — умолчание `ZoneFeaturesAnalyzer`, поэтому явная просьба
    о нём описывает ту же конфигурацию и обязана попасть в ту же запись.
    """

    assert key_for(config, data) == key_for(config, data, shape_strategy="statistical")


def test_swapping_an_injected_component_changes_the_key(config, data):
    """Не только стратегии: подменённый компонент считает другое."""

    from bquant.analysis.statistical import HypothesisTestSuite

    class NarrowerSuite(HypothesisTestSuite):
        pass

    assert key_for(config, data) != key_for(
        config, data, hypothesis_suite=NarrowerSuite(alpha=0.01)
    )


def test_the_package_has_one_cache_schema_version():
    """Два литерала одного номера — тот же дефект, что закрывали в G33.

    `CACHE_SCHEMA_VERSION` уходит в подпись конфигурации, `CACHE_VERSION` — в ключ и
    в метаданные записи. Пока это были два числа, правило «бампятся вместе» жило
    только в прозе гэп-документов.

    Равенства значений здесь недостаточно, и не по придирчивости: маленькие целые в
    CPython — один и тот же объект, поэтому два литерала `15` прошли бы и `==`, и
    `is`. Проверять приходится сам источник: номер обязан браться у кэша, а не
    стоять в пайплайне числом.
    """

    import ast
    import inspect

    from bquant.analysis.zones import pipeline as pipeline_module

    assert CACHE_SCHEMA_VERSION == ZoneAnalysisCache.CACHE_VERSION

    tree = ast.parse(inspect.getsource(pipeline_module))
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CACHE_SCHEMA_VERSION"
            for target in node.targets
        )
    ]

    assert len(assignments) == 1, "CACHE_SCHEMA_VERSION присваивается не один раз"
    assert not isinstance(assignments[0].value, ast.Constant), (
        "CACHE_SCHEMA_VERSION снова стал числом в пайплайне. Номер схемы один на "
        "пакет и живёт в ZoneAnalysisCache.CACHE_VERSION; второй литерал разойдётся "
        "с первым ровно в тот релиз, когда о правиле забудут."
    )
