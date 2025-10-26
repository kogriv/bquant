"""Валидирует примеры из docs/api/indicators/macd.md."""

import os
import sys
import traceback
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Dict

import pandas as pd

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Подтягиваем подготовленные заглушки pandas-ta из валидации README
from devref.gaps.zo.zodoctest import test_indicators_readme_validation as readme_helpers  # noqa: E402

DOC_PATH = PROJECT_ROOT / "docs" / "api" / "indicators" / "macd.md"


@lru_cache(maxsize=1)
def _load_dataframe() -> pd.DataFrame:
    """Загружает sample-данные и подготавливает macd_hist."""
    frame = readme_helpers._load_sample_data().copy()
    return frame


@lru_cache(maxsize=1)
def _legacy_result():
    from bquant.indicators.macd import MACDZoneAnalyzer

    df = _load_dataframe()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", DeprecationWarning)
        analyzer = MACDZoneAnalyzer()
        result = analyzer.analyze_complete(df)
    assert any(
        "MACDZoneAnalyzer is deprecated" in str(item.message)
        for item in captured
    ), "Ожидалось предупреждение о депрекации"
    return result


@lru_cache(maxsize=1)
def _pipeline_result():
    from bquant.analysis.zones import analyze_zones

    df = _load_dataframe()
    return (
        analyze_zones(df)
        .with_indicator(
            "custom", "macd", fast_period=12, slow_period=26, signal_period=9
        )
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .with_strategies(swing="find_peaks", divergence="classic")
        .analyze(clustering=True, n_clusters=3)
        .build()
    )


@lru_cache(maxsize=1)
def _preset_result():
    from bquant.indicators.macd import analyze_macd_zones

    df = _load_dataframe()
    return analyze_macd_zones(
        df,
        macd_params={"fast": 12, "slow": 26, "signal": 9},
    )


def test_cross_references() -> bool:
    print("📋 Тест: Cross-references macd.md")

    targets = [
        PROJECT_ROOT / "docs" / "api" / "analysis" / "pipeline.md",
        PROJECT_ROOT / "docs" / "api" / "analysis" / "zones.md",
        PROJECT_ROOT / "docs" / "api" / "analysis" / "strategies.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "base.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "preloaded.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "factory.md",
    ]

    missing = [str(path) for path in targets if not path.exists()]
    if missing:
        print("  ❌ Отсутствуют файлы:")
        for path in missing:
            print(f"    - {path}")
        return False

    print("  ✅ Все ссылки ведут на существующие файлы")
    return True


def test_deprecation_decorator() -> bool:
    print("📋 Тест: Deprecation decorator")

    from bquant.indicators.macd import MACDZoneAnalyzer

    message = getattr(MACDZoneAnalyzer, "__deprecation_message__", "")
    if "MACDZoneAnalyzer is deprecated" not in message:
        print("  ❌ Сообщение о депрекации не совпадает")
        return False

    if not getattr(MACDZoneAnalyzer, "__deprecated__", False):
        print("  ❌ Декоратор @deprecated не активирован")
        return False

    print("  ✅ Декоратор соответствует документации")
    return True


def test_migration_examples() -> bool:
    print("📋 Тест: Migration guide")

    legacy_result = _legacy_result()
    if not legacy_result.zones:
        print("  ❌ Legacy анализ не вернул зон")
        return False

    zone_dict = legacy_result.zones[0].to_analyzer_format()
    expected_keys = {"zone_id", "type", "duration", "indicator_context"}
    if not expected_keys.issubset(zone_dict.keys()):
        print("  ❌ Устаревший словарь не содержит ожидаемых ключей")
        return False

    from bquant.analysis.zones import analyze_zones

    df = _load_dataframe()
    new_result = (
        analyze_zones(df)
        .with_indicator(
            "custom", "macd", fast_period=12, slow_period=26, signal_period=9
        )
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .analyze(clustering=True)
        .build()
    )

    if not new_result.zones:
        print("  ❌ Universal Pipeline не вернул зон")
        return False

    feature_value = new_result.zones[0].features.get("zone_type")
    print(f"  ℹ️ feature zone_type: {feature_value}")
    return True


def test_zone_iteration_example() -> bool:
    print("📋 Тест: Итерация по зонам")

    result = _pipeline_result()
    try:
        for zone in result.zones[:3]:
            line = f"Зона {zone.type}: {zone.start_time} - {zone.end_time}"
            print(f"  → {line}")
            if zone.features:
                swings = zone.features.get("num_swings", 0)
                divergence = zone.features.get("has_classic_divergence", False)
                print(f"     Swings: {swings}, Divergence: {divergence}")
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка при обходе зон: {exc}")
        traceback.print_exc()
        return False

    return True


def test_preset_example() -> bool:
    print("📋 Тест: Preset analyze_macd_zones")

    preset = _preset_result()
    if not preset.zones:
        print("  ❌ Пресет не вернул зон")
        return False

    print(f"  ✅ Найдено зон: {len(preset.zones)}")
    return True


def test_legacy_snippet() -> bool:
    print("📋 Тест: Legacy API")

    legacy_result = _legacy_result()
    print(f"  ✅ Legacy зон: {len(legacy_result.zones)}")
    return True


def test_preloaded_indicator_example() -> bool:
    print("📋 Тест: PRELOADED MACD индикатор")

    from bquant.indicators.preloaded import MACDPreloadedIndicator
    from bquant.data.samples import get_sample_data

    data = get_sample_data("tv_xauusd_1h")

    macd_indicator = MACDPreloadedIndicator()
    info = MACDPreloadedIndicator.get_info()
    if "macd" not in info.get("required_fields", {}):
        print("  ❌ Некорректное описание required_fields")
        return False

    result = macd_indicator.calculate(data)
    if result.data.empty:
        print("  ❌ calculate() вернул пустой результат")
        return False

    trending_up = macd_indicator.is_trending_up(data, column="macd")
    trending_down = macd_indicator.is_trending_down(data, column="macd")
    crossovers: Dict[str, object] = macd_indicator.get_crossovers(data)

    print(f"  ℹ️ Trending up: {trending_up}, trending down: {trending_down}")
    print(f"  ℹ️ Keys: {sorted(crossovers.keys())}")
    return True


def test_preloaded_custom_columns_example() -> bool:
    print("📋 Тест: PRELOADED c кастомными колонками")

    from bquant.indicators.preloaded import MACDPreloadedIndicator
    from bquant.data.samples import get_sample_data

    data = get_sample_data("tv_xauusd_1h")

    macd_only = MACDPreloadedIndicator(required_columns=["macd"])
    if not macd_only.validate_data(data):
        print("  ❌ validate_data() должен возвращать True для ['macd']")
        return False

    macd_full = MACDPreloadedIndicator(
        required_columns=["macd", "signal", "histogram"]
    )
    try:
        is_valid = macd_full.validate_data(data)
    except ValueError as exc:
        print(f"  ❌ Неожиданное исключение: {exc}")
        return False

    print(f"  ℹ️ validate_data(['macd','signal','histogram']) -> {is_valid}")
    return bool(is_valid)


def main() -> None:
    tests = [
        test_cross_references,
        test_deprecation_decorator,
        test_migration_examples,
        test_zone_iteration_example,
        test_preset_example,
        test_legacy_snippet,
        test_preloaded_indicator_example,
        test_preloaded_custom_columns_example,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as exc:  # pragma: no cover - страховка
            print(f"  ❌ Необработанное исключение в {test.__name__}: {exc}")
            traceback.print_exc()
            results.append(False)

    total = sum(1 for value in results if value)
    print(f"\n✅ Пройдено {total}/{len(results)} тестов")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
