"""
Тест валидации docs/api/analysis/pipeline.md
Проверяет примеры pipeline, работу Fluent Builder и cross-references
"""

import sys
import os
import traceback
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import pandas as pd

# Ускоряем работу pandas-ta и numba в тестовой среде
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def _prepare_pandas_ta(minimal_functions: Iterable[str] = ("rsi", "ao", "stoch")) -> None:
    """Ограничиваем регистрацию pandas-ta минимальным набором индикаторов."""

    try:
        from bquant.indicators.library import pandas_ta as pandas_ta_loader
    except Exception:
        return

    try:
        import pandas_ta as ta
    except Exception:
        return

    loader = pandas_ta_loader.PandasTALoader
    selected = {}
    for name in minimal_functions:
        func = getattr(ta, name, None)
        if func is not None:
            selected[name] = func

    if not selected:
        return

    loader._function_cache = selected
    loader._available_indicators = sorted(selected.keys())
    loader._indicators_registered = False


_prepare_pandas_ta()


@lru_cache(maxsize=1)
def _load_sample_data() -> pd.DataFrame:
    from bquant.data.samples import get_sample_data

    return get_sample_data("tv_xauusd_1h")


def test_imports_from_docs() -> bool:
    """Проверяем все импорты, указанные в документации."""

    print("📋 Тест: Импорты из документации")

    imports_to_test = [
        ("bquant.analysis.zones", "analyze_zones"),
        ("bquant.analysis.zones.pipeline", "ZoneAnalysisBuilder"),
        ("bquant.analysis.zones.pipeline", "ZoneAnalysisPipeline"),
        ("bquant.analysis.zones.analyzer", "UniversalZoneAnalyzer"),
        ("bquant.analysis.zones.pipeline", "ZoneAnalysisConfig"),
        ("bquant.analysis.zones.pipeline", "ZoneAnalysisResult"),
        ("bquant.data.samples", "get_sample_data"),
    ]

    success = 0
    for module_name, attr_name in imports_to_test:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            getattr(module, attr_name)
            print(f"  ✅ {module_name}.{attr_name}")
            success += 1
        except Exception as exc:
            print(f"  ❌ {module_name}.{attr_name}: {exc}")
            traceback.print_exc()

    print(f"  Результат: {success}/{len(imports_to_test)} импортов успешно")
    return success == len(imports_to_test)


def test_fluent_builder_example() -> bool:
    """Воспроизводим пример Fluent Builder Pattern."""

    print("\n📋 Тест: Fluent Builder Pattern")

    try:
        from bquant.analysis.zones import analyze_zones

        data = _load_sample_data().copy()

        result = (
            analyze_zones(data)
            .with_indicator("pandas_ta", "rsi", length=14)
            .detect_zones(
                "threshold",
                indicator_col="rsi",
                upper_threshold=70,
                lower_threshold=30,
            )
            .with_strategies(swing="find_peaks", shape="statistical")
            .analyze(clustering=True, n_clusters=3)
            .build()
        )

        print(f"  ✅ Pipeline выполнен, найдено зон: {len(result.zones)}")
        if result.zones and result.zones[0].features:
            keys = list(result.zones[0].features.keys())[:6]
            print(f"  ✅ zone.features содержит ключи: {keys}")

        return True

    except Exception as exc:
        print(f"  ❌ Fluent Builder пример: {exc}")
        traceback.print_exc()
        return False


def test_pipeline_core_engine() -> bool:
    """Воспроизводим пример ZoneAnalysisPipeline с автоматической интеграцией."""

    print("\n📋 Тест: ZoneAnalysisPipeline core engine")

    try:
        from bquant.analysis.zones import analyze_zones

        data = _load_sample_data().copy()

        result = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=True)
            .build()
        )

        print(f"  ✅ Core engine: {len(result.zones)} зон")

        if result.zones:
            zone = result.zones[0]
            print(f"  ✅ indicator_context: {zone.indicator_context.get('indicator_name')}")
            print(f"  ✅ Стратегия детекции: {zone.indicator_context.get('detection_strategy')}")

        return True

    except Exception as exc:
        print(f"  ❌ ZoneAnalysisPipeline пример: {exc}")
        traceback.print_exc()
        return False


def test_indicator_context_contract() -> bool:
    """Проверяем стандартные поля indicator_context из документации."""

    print("\n📋 Тест: indicator_context contract")

    try:
        from bquant.analysis.zones import analyze_zones

        data = _load_sample_data().copy()

        result = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .with_strategies(swing="zigzag")
            .analyze(clustering=True)
            .build()
        )

        if not result.zones:
            print("  ⚠️ Нет зон для проверки контракта")
            return True

        context = result.zones[0].indicator_context or {}
        required_keys = [
            "detection_indicator",
            "detection_strategy",
            "detection_rules",
            "signal_line",
        ]

        missing = [key for key in required_keys if key not in context]
        print(f"  ✅ indicator_context ключи: {sorted(context.keys())[:6]}")
        if missing:
            print(f"  ❌ Отсутствуют ключи: {missing}")
            return False

        return True

    except Exception as exc:
        print(f"  ❌ indicator_context contract: {exc}")
        traceback.print_exc()
        return False


def test_practical_examples() -> bool:
    """Проверяем практические примеры (MACD, RSI, AO, caching)."""

    print("\n📋 Тест: Практические примеры")

    try:
        from bquant.analysis.zones import analyze_zones

        data = _load_sample_data().copy()

        # Пример 1: MACD analysis
        macd_result = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .with_strategies(swing="find_peaks", divergence="classic")
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
        print(f"  ✅ MACD пример: {len(macd_result.zones)} зон")

        # Пример 2: RSI analysis
        rsi_result = (
            analyze_zones(data)
            .with_indicator("pandas_ta", "rsi", length=14)
            .detect_zones(
                "threshold",
                indicator_col="rsi",
                upper_threshold=70,
                lower_threshold=30,
            )
            .with_strategies(swing="pivot_points", volatility="combined")
            .analyze(clustering=True)
            .build()
        )
        print(f"  ✅ RSI пример: {len(rsi_result.zones)} зон")

        # Пример 3: AO analysis
        ao_result = (
            analyze_zones(data)
            .with_indicator("pandas_ta", "ao", fast=5, slow=34)
            .detect_zones("zero_crossing", indicator_col="AO_5_34")
            .with_strategies(swing="zigzag", shape="statistical")
            .analyze(clustering=True)
            .build()
        )
        print(f"  ✅ AO пример: {len(ao_result.zones)} зон")

        # Пример 4: Кэширование
        cache_result = (
            analyze_zones(data)
            .with_cache(enable=True, ttl=7200)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=True)
            .build()
        )
        print(f"  ✅ Кэширование: {len(cache_result.zones)} зон")

        return True

    except Exception as exc:
        print(f"  ❌ Практические примеры: {exc}")
        traceback.print_exc()
        return False


def test_migration_example() -> bool:
    """Проверяем раздел Migration Guide."""

    print("\n📋 Тест: Migration Guide")

    try:
        from bquant.indicators import MACDZoneAnalyzer
        from bquant.data.samples import get_sample_data

        analyzer = MACDZoneAnalyzer()
        data = get_sample_data("tv_xauusd_1h")
        legacy_result = analyzer.analyze_complete(data.head(200))
        zones = legacy_result.zones
        print(f"  ✅ Legacy analyze_complete: зон={len(zones)}")

        if zones:
            zone = zones[0]
            print(f"  ✅ Первая зона: id={zone.zone_id}, type={zone.type}, duration={zone.duration}")

        return True

    except Exception as exc:
        print(f"  ❌ Migration Guide пример: {exc}")
        traceback.print_exc()
        return False


def test_cross_references() -> bool:
    """Проверяем, что все cross-reference ссылки существуют."""

    print("\n📋 Тест: Cross-references")

    references = [
        Path("docs/api/analysis/strategies.md"),
        Path("docs/api/analysis/statistical.md"),
        Path("docs/api/analysis/zones.md"),
        Path("docs/user_guide/quick_start.md"),
        Path("docs/examples/README.md"),
        Path("research/notebooks/03_zones_universal.py"),
        Path("research/notebooks/03_analysis_new_features.py"),
        Path("examples/02_macd_zone_analysis.py"),
        Path("docs/developer_guide/README.md"),
        Path("docs/api/visualization/README.md"),
        Path("docs/api/indicators/README.md"),
        Path("tests/integration"),
    ]

    success = 0
    for ref in references:
        if ref.exists():
            print(f"  ✅ {ref}")
            success += 1
        else:
            print(f"  ❌ {ref} — отсутствует")

    return success == len(references)


def test_language_check() -> bool:
    """Проверяем, что текст документа на русском языке."""

    print("\n📋 Тест: Язык текста")

    try:
        content = Path("docs/api/analysis/pipeline.md").read_text(encoding="utf-8")
        lowered = content.lower()
        russian_markers = ["архитектур", "стратег", "контекст", "универсаль", "кэш"]
        found = sum(1 for word in russian_markers if word in lowered)
        code_blocks = content.count("```python")

        print(f"  ✅ Найдено русских маркеров: {found}")
        print(f"  ✅ Количество python-блоков: {code_blocks}")
        return found >= len(russian_markers) - 1 and code_blocks >= 6

    except Exception as exc:
        print(f"  ❌ Language check: {exc}")
        return False


def main() -> bool:
    print("🔍 Валидация docs/api/analysis/pipeline.md")
    print("=" * 60)

    tests = [
        ("Импорты", test_imports_from_docs),
        ("Fluent Builder", test_fluent_builder_example),
        ("Core Engine", test_pipeline_core_engine),
        ("indicator_context", test_indicator_context_contract),
        ("Практические примеры", test_practical_examples),
        ("Migration Guide", test_migration_example),
        ("Cross-references", test_cross_references),
        ("Язык текста", test_language_check),
    ]

    results = []
    for label, func in tests:
        try:
            result = func()
        except Exception as exc:
            print(f"  ❌ Тест {func.__name__} упал: {exc}")
            traceback.print_exc()
            result = False
        results.append((label, result))

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ВАЛИДАЦИИ:")
    for label, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"  {label}: {status}")

    print(f"\n🎯 Итого: {passed}/{total} тестов пройдено")
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True

    print("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

