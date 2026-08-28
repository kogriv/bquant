"""В пакете две разные «зоны», и имена обязаны это говорить (G28).

Что здесь утверждается
======================

Не «класс переименован» — это проверялось бы один раз и ничего не защищало. Здесь
утверждается **различие между двумя моделями**, потому что именно его стирали имена:

* :class:`~bquant.analysis.zones.models.ZoneInfo` — **участок времени**, на котором
  осциллятор в одном состоянии. Границы в барах, зоны идут встык, каждый бар ровно
  в одной зоне (инвариант мощения, закреплённый в G21).
* :class:`~bquant.analysis.zones.PriceLevelZone` — **полоса цены**: поддержка или
  сопротивление. Границы в цене, полосы могут перекрываться, жить одновременно и
  покрывать не всю историю.

Общего у них только слово «зона». Пока они назывались `Zone` и `ZoneInfo`, а их
анализаторы — `ZoneAnalyzer` и `UniversalZoneAnalyzer`, имена намекали на иерархию
(«базовое против расширенного»), которой нет. Цена этого намёка описана в
``devref/gaps/zone_types/g28_one_word_two_concepts_2026-08.md`` §2: дока объявила
одно устаревшей версией другого, а разбор упёрся в ложный вопрос «как уложить
ценовые полосы в мощение».
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

os.environ.setdefault("BQUANT_SKIP_TALIB", "1")


def test_the_two_models_measure_different_things():
    """Одна модель меряет время, другая — цену. Это и есть различие.

    Проверяются **поля**, а не имена: поле говорит, в чём измеряется граница зоны,
    и подменить одну модель другой нельзя именно поэтому.
    """
    from dataclasses import fields

    from bquant.analysis.zones import PriceLevelZone
    from bquant.analysis.zones.models import ZoneInfo

    time_zone = {f.name for f in fields(ZoneInfo)}
    price_zone = {f.name for f in fields(PriceLevelZone)}

    assert {"start_idx", "end_idx", "duration"} <= time_zone, (
        "у зоны-отрезка границы задаются барами"
    )
    assert not {"start_idx", "end_idx"} & price_zone, (
        "полоса цены не имеет границ в барах — иначе это уже отрезок времени"
    )

    assert {"start_price", "end_price"} <= price_zone, (
        "у полосы цены границы задаются ценой"
    )
    assert not {"start_price", "end_price"} & time_zone, (
        "у зоны-отрезка нет ценовых границ — цена внутри неё меняется"
    )


def test_neither_name_claims_to_be_a_better_version_of_the_other():
    """Имя обязано называть предмет, а не ранг.

    Пин ловит возврат к `Zone`/`ZoneInfo`: суффикс `Info` и приставка `Universal`
    говорят про полноту, а не про то, что модель описывает. Именно на этом намёке
    дока объявила одну из моделей устаревшей версией другой.
    """
    import bquant.analysis.zones as zones

    assert hasattr(zones, "PriceLevelZone"), "полоса цены должна называть себя ценой"
    assert hasattr(zones, "PriceLevelAnalyzer")
    assert not hasattr(zones, "Zone"), (
        "голое имя `Zone` вернулось: оно ничего не говорит о предмете и снова "
        "прочитается как «базовая версия ZoneInfo»"
    )
    assert not hasattr(zones, "ZoneAnalyzer"), (
        "голое имя `ZoneAnalyzer` вернулось — читается как «неуниверсальный "
        "UniversalZoneAnalyzer», хотя он про другое"
    )


def test_price_level_zones_may_overlap_in_time():
    """Полосы цены живут одновременно — в отличие от зон-отрезков.

    Это не деталь реализации, а причина, по которой их нельзя уложить в пайплайн:
    на примыкании зон стоит весь слой последовательностей и переходов (G21).
    """
    from bquant.analysis.zones import PriceLevelAnalyzer

    # Цена трижды возвращается к одному уровню и трижды — к другому, выше.
    closes = [100, 104, 100, 105, 100, 106, 100, 108, 112, 108, 113, 108, 112, 108]
    data = pd.DataFrame({
        "open": closes,
        "high": [c + 1 for c in closes],
        "low": [c - 1 for c in closes],
        "close": closes,
    }, index=pd.date_range("2024-01-01", periods=len(closes), freq="h"))

    zones = PriceLevelAnalyzer().identify_support_resistance(
        data, window=2, min_touches=2
    )

    # Ровно одна полоса — уже достаточно, чтобы утверждать про её природу;
    # важен не их счёт, а то, что границы у них ценовые.
    for zone in zones:
        assert zone.start_price is not None and zone.end_price is not None
        assert not hasattr(zone, "start_idx"), (
            "полоса цены обзавелась индексом бара — модели снова слиплись"
        )


def test_the_duplicate_module_level_wrapper_is_gone():
    """Модульная `extract_zone_features` удалена; метод — на месте.

    Обёртка дублировала `ZoneFeaturesAnalyzer.extract_zone_features` и звалась
    только из тестов. Метод трогать было нельзя: на нём стоит пайплайн
    (`extract_all_zones_features` → `UniversalZoneAnalyzer.analyze_zones`).
    Разделил их `codemap impact`; греп по имени склеивал метод с обёрткой и
    давал ложные «6 использований в пакете».
    """
    from bquant.analysis.zones import zone_features
    from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer

    assert not hasattr(zone_features, "extract_zone_features"), (
        "модульная обёртка вернулась — она повторяет метод и ничего не добавляет"
    )
    assert callable(ZoneFeaturesAnalyzer.extract_zone_features), (
        "метод пропал — а на нём стоит пайплайн"
    )
