"""`min_duration` фильтрует отчёт, а не детекцию (G21, вариант (c)).

Вариант (a), закрытый 2026-08-24, снял **ложь** о разрывах: пара зон,
разделённая пропуском, перестала считаться переходом. Сами разрывы при этом
никуда не делись — их по-прежнему создавал фильтр длительности, стоявший внутри
детекции с ничем не обоснованным значением `2`.

Здесь закрывается остаток. Детекция обязана вернуть полное мощение области
определения индикатора; порог длительности стал явным параметром стадии анализа
и сообщает о себе в `metadata['duration_filter']`.

По дороге вскрылись два дефекта, которые прежний фильтр прятал — оба того же
рода «хорошо сформированная неправда»:

1. **Признаки приписывались чужим зонам.** `analyze_zones` сшивал зоны с
   признаками через `zip` по позиции, а `extract_all_zones_features` возвращал
   только удачи. Первая же неизмеренная зона сдвигала всё остальное. На
   встроенном сэмпле при `min_duration=1` чужие числа несли 66 зон из 83 — и
   результат выглядел совершенно нормальным.

2. **Зона типа `None` и зона типа `bear` на разогреве.** У порогового детектора
   массив классов — `np.empty(dtype=object)`, то есть заполнен `None`; бары, на
   которых у индикатора ещё нет значения, ни одному сравнению не удовлетворяют
   и остаются `None`. У детектора пересечения нуля хуже: `mean() > 0` на `NaN`
   даёт `False`, и участок, где индикатора не существует, получал уверенную
   метку `bear`.

Разбор: ``devref/gaps/sequence/g21_min_duration_breaks_tiling_2026-08-24.md``.
"""

import numpy as np
import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.detection.base import defined_segments
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


def _macd(data, **analyze_kwargs):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .with_cache(enable=False)
        .analyze(clustering=False, **analyze_kwargs)
        .build()
    )


# --------------------------------------------------------------------------- #
# 1. Детекция ничего не выбрасывает
# --------------------------------------------------------------------------- #
class TestDetectionTiles:

    def test_detection_config_has_no_duration_threshold(self):
        """Порога нет в конфигурации детекции — не «по умолчанию 1», а нет."""
        assert not hasattr(ZoneDetectionConfig(), "min_duration")
        with pytest.raises(TypeError):
            ZoneDetectionConfig(min_duration=2)

    def test_zones_tile_the_frame_exactly(self, data):
        """Каждый бар с определённым индикатором принадлежит ровно одной зоне.

        Мостится не весь кадр, а его **определённая часть**: после G45 индикатор
        не публикует значений на неполном окне, и голова ряда зонам не
        принадлежит — принадлежать там нечему. Требование к детекции от этого не
        слабеет: внутри определённой области ни один бар не выброшен и зазоров
        между зонами нет.
        """
        result = _macd(data)
        zones = sorted(result.zones, key=lambda z: z.start_idx)

        hist = result.data[result.column_schema.column("hist")]
        defined = hist.notna().to_numpy().nonzero()[0]
        first_defined, last_defined = int(defined[0]), int(defined[-1])

        assert zones[0].start_idx == first_defined
        assert zones[-1].end_idx == last_defined
        for previous, following in zip(zones, zones[1:]):
            assert following.start_idx == previous.end_idx + 1, (
                f"разрыв между зонами {previous.zone_id} и {following.zone_id}"
            )
        assert sum(z.duration for z in zones) == last_defined - first_defined + 1

    def test_zero_crossing_alternates_when_nothing_is_dropped(self, data):
        """Детектор режет по смене знака, поэтому типы обязаны чередоваться."""
        zones = sorted(_macd(data).zones, key=lambda z: z.start_idx)
        same = [(a.zone_id, b.zone_id) for a, b in zip(zones, zones[1:])
                if a.type == b.type]
        assert not same, f"соседи одного типа при точном мощении: {same}"

    def test_sequence_analysis_counts_every_pair(self, data):
        summary = _macd(data).sequence_analysis["sequence_summary"]
        assert summary["discarded_transitions"] == 0
        assert summary["bars_missing"] == 0
        assert summary["contiguous_segments"] == 1


# --------------------------------------------------------------------------- #
# 2. Отсев — на стадии отчёта, и он себя называет
# --------------------------------------------------------------------------- #
class TestReportingFilter:

    def test_filter_narrows_the_aggregates_and_says_by_how_much(self, data):
        result = _macd(data, min_duration=2)
        reported = result.metadata["duration_filter"]

        assert reported["min_duration"] == 2
        assert reported["zones_excluded"] > 0
        assert reported["bars_excluded"] > 0
        excluded_ids = set(reported["excluded_zone_ids"])
        assert len(excluded_ids) == reported["zones_excluded"]

        by_id = {z.zone_id: z for z in result.zones}
        assert all(by_id[zid].duration < 2 for zid in excluded_ids)

    def test_excluded_zones_are_still_there_with_their_features(self, data):
        """Отчётный фильтр сужает выборку, а не уничтожает данные."""
        everything = _macd(data)
        filtered = _macd(data, min_duration=3)

        assert len(filtered.zones) == len(everything.zones)
        reported = filtered.metadata["duration_filter"]
        for zone_id in reported["excluded_zone_ids"]:
            zone = next(z for z in filtered.zones if z.zone_id == zone_id)
            assert zone.features is not None, (
                "исключённая зона обязана остаться измеренной"
            )
            assert zone.features["duration"] == zone.duration

    def test_filtered_aggregates_match_the_old_detection_time_filter(self, data):
        """Перенос порога не меняет ответа — только делает его видимым.

        Прежде фильтр стоял в детекции; отбрасывание короткой зоны не сдвигало
        границ остальных, поэтому выживший набор обязан совпасть до зоны.
        """
        filtered = _macd(data, min_duration=2)
        survivors = [z for z in filtered.zones if z.duration >= 2]

        assert filtered.metadata["duration_filter"]["zones_analysed"] == len(survivors)
        assert filtered.statistics["total_statistics"]["total_zones"] == len(survivors)

    def test_default_filters_nothing(self, data):
        reported = _macd(data).metadata["duration_filter"]
        assert reported["min_duration"] == 1
        assert reported["zones_excluded"] == 0

    def test_a_threshold_below_one_is_refused(self, data):
        with pytest.raises(ValueError, match="at least 1"):
            _macd(data, min_duration=0)


# --------------------------------------------------------------------------- #
# 3. Признаки принадлежат своей зоне
# --------------------------------------------------------------------------- #
class TestFeaturesStayWithTheirZone:

    def test_extraction_result_is_aligned_with_the_input(self, data):
        """Длина совпадает с числом зон; неудача — None на своём месте."""
        zones = _macd(data).zones
        broken = zones[3]
        broken.data = broken.data.iloc[0:0]  # измерить нечего

        features = ZoneFeaturesAnalyzer().extract_all_zones_features(zones)

        assert len(features) == len(zones)
        assert features[3] is None
        for index, (zone, measured) in enumerate(zip(zones, features)):
            if measured is None:
                continue
            assert measured.duration == zone.duration, (
                f"зона {index} получила признаки чужой зоны"
            )

    def test_every_zone_carries_its_own_numbers(self, data):
        """Сквозная проверка через пайплайн, на дефолте с однобаровыми зонами."""
        result = _macd(data)
        assert any(z.duration == 1 for z in result.zones), (
            "на сэмпле есть однобаровые зоны; без них тест ничего не проверяет"
        )
        for zone in result.zones:
            assert zone.features is not None
            assert zone.features["duration"] == zone.duration
            assert zone.features["zone_type"] == zone.type


# --------------------------------------------------------------------------- #
# 4. Бар без значения индикатора — не зона
# --------------------------------------------------------------------------- #
class TestUndefinedBarsBelongToNoZone:

    def test_defined_segments_splits_on_gaps(self):
        assert defined_segments(np.array([np.nan, 1.0, 2.0])) == [(1, 3)]
        assert defined_segments(np.array([1.0, np.nan, 2.0])) == [(0, 1), (2, 3)]
        assert defined_segments(np.array([np.nan, np.nan])) == []
        assert defined_segments(np.array([1.0, 2.0])) == [(0, 2)]

    def test_warm_up_is_not_a_zone_of_any_type(self, data):
        """RSI не определён на первом баре — и это не «нейтральная» зона."""
        result = (
            analyze_zones(data)
            .with_indicator("custom", "rsi", period=14)
            .detect_zones("threshold", indicator_col="rsi_14",
                          upper_threshold=70, lower_threshold=30)
            .with_cache(enable=False)
            .analyze(clustering=False)
            .build()
        )

        assert all(zone.type is not None for zone in result.zones)
        undefined = int(result.data["rsi_14"].isna().sum())
        assert undefined > 0, "сэмпл обязан иметь разогрев, иначе тест пуст"
        covered = sum(z.duration for z in result.zones)
        assert covered == len(data) - undefined

    def test_zero_crossing_does_not_call_a_warm_up_bearish(self):
        """`mean() > 0` на NaN даёт False, то есть уверенное `bear`."""
        frame = pd.DataFrame({
            "open": np.arange(10.0, 20.0),
            "high": np.arange(10.0, 20.0) + 1,
            "low": np.arange(10.0, 20.0) - 1,
            "close": np.arange(10.0, 20.0),
            "osc": [np.nan, np.nan, np.nan, 1.0, 2.0, 3.0, -1.0, -2.0, 1.0, 2.0],
        }, index=pd.date_range("2024-01-01", periods=10, freq="h"))

        result = (
            analyze_zones(frame)
            .detect_zones("zero_crossing", indicator_col="osc")
            .with_cache(enable=False)
            .analyze(clustering=False)
            .build()
        )

        assert min(z.start_idx for z in result.zones) == 3, (
            "зона не может начинаться там, где у индикатора нет значения"
        )
        assert sum(z.duration for z in result.zones) == 7
