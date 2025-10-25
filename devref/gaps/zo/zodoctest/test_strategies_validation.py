#!/usr/bin/env python3
"""
Тест валидации docs/api/analysis/strategies.md
Проверяет примеры кода, работу стратегий и cross-references
"""

import sys
import os
import traceback
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

# Ускоряем работу pandas-ta в тестовой среде
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def _prepare_pandas_ta(minimal_functions: Iterable[str] = ("rsi", "ao", "stoch")) -> None:
    """Ограничиваем регистрацию pandas-ta минимумом индикаторов."""

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


def _create_synthetic_zone_data() -> pd.DataFrame:
    """Создаёт синтетический DataFrame с колонками, используемыми в документации."""
    index = pd.date_range("2024-01-01", periods=120, freq="H")
    base = 100 + np.sin(np.linspace(0, 6, len(index)))
    trend = np.linspace(-0.5, 0.5, len(index))
    close = base + trend
    high = close + 0.3 + np.linspace(0.0, 0.1, len(index))
    low = close - 0.3 - np.linspace(0.0, 0.1, len(index))
    open_ = np.concatenate(([close[0]], close[:-1]))
    volume = 1200 + np.linspace(0, 1, len(index)) * 150

    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=index)

    # Простейшие индикаторы
    df["macd"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    df["RSI_14"] = np.linspace(35, 65, len(df))
    df["AO_5_34"] = np.sin(np.linspace(0, 3 * np.pi, len(df)))
    df["atr"] = (df["high"] - df["low"]).rolling(14, min_periods=1).mean()

    return df


def test_imports_from_docs() -> bool:
    """Проверяем все импорты из документации."""
    print("📋 Тест: Импорты из документации")

    targets = [
        ("bquant.analysis.zones", "ZoneFeaturesAnalyzer"),
        ("bquant.analysis.zones", "analyze_zones"),
        ("bquant.analysis.zones.strategies.shape", "StatisticalShapeStrategy"),
        ("bquant.analysis.zones.strategies.divergence", "ClassicDivergenceStrategy"),
        ("bquant.analysis.zones.strategies.volume", "StandardVolumeStrategy"),
        ("bquant.analysis.zones.strategies.volatility", "CombinedVolatilityStrategy"),
        ("bquant.analysis.zones.strategies.registry", "StrategyRegistry"),
        ("bquant.core.config", "create_swing_strategy"),
    ]

    success = 0
    for module_name, attr_name in targets:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            getattr(module, attr_name)
            print(f"  ✅ {module_name}.{attr_name}")
            success += 1
        except Exception as exc:
            print(f"  ❌ {module_name}.{attr_name}: {exc}")
            traceback.print_exc()

    print(f"  Результат: {success}/{len(targets)} импортов успешно")
    return success == len(targets)


def test_strategy_examples() -> bool:
    """Проверяем примеры прямого вызова стратегий из документации."""
    print("\n📋 Тест: Прямые вызовы стратегий")

    try:
        from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy
        from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy
        from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy
        from bquant.analysis.zones.strategies.volatility import CombinedVolatilityStrategy

        zone_data = _create_synthetic_zone_data()
        baseline_volume = float(zone_data["volume"].iloc[:50].mean())

        shape_strategy = StatisticalShapeStrategy()
        shape_macd = shape_strategy.calculate(zone_data, indicator_col="macd_hist")
        shape_rsi = shape_strategy.calculate(zone_data, indicator_col="RSI_14")
        shape_ao = shape_strategy.calculate(zone_data, indicator_col="AO_5_34")
        print(f"  ✅ Shape metrics: MACD skew={shape_macd.hist_skewness:.2f}, RSI skew={shape_rsi.hist_skewness:.2f}, AO skew={shape_ao.hist_skewness:.2f}")

        divergence_strategy = ClassicDivergenceStrategy()
        div_rsi = divergence_strategy.calculate_divergence(zone_data, indicator_col="RSI_14")
        div_macd_hist = divergence_strategy.calculate_divergence(zone_data, indicator_col="macd_hist")
        div_macd_two_line = divergence_strategy.calculate_divergence(
            zone_data,
            indicator_col="macd",
            indicator_line_col="macd_signal",
        )
        print(f"  ✅ Divergence metrics: RSI count={div_rsi.divergence_count}, MACD strength={div_macd_hist.divergence_strength:.2f}, Two-line type={div_macd_two_line.divergence_type}")

        volume_strategy = StandardVolumeStrategy()
        volume_metrics = volume_strategy.calculate_volume(
            zone_data,
            baseline_volume=baseline_volume,
            indicator_col="macd_hist",
        )
        ratio = volume_metrics.volume_zone_ratio
        ratio_display = f"{ratio:.2f}" if ratio is not None else "None"
        print(f"  ✅ Volume metrics: ratio={ratio_display}, corr={volume_metrics.volume_indicator_corr}")

        volatility_strategy = CombinedVolatilityStrategy()
        volatility_metrics = volatility_strategy.calculate_volatility(zone_data)
        print(f"  ✅ Volatility metrics: score={volatility_metrics.volatility_score:.2f}, regime={volatility_metrics.volatility_regime}")

        return True

    except Exception as exc:
        print(f"  ❌ Strategy examples: {exc}")
        traceback.print_exc()
        return False


def test_zone_features_analyzer_example() -> bool:
    """Проверяем пример с ZoneFeaturesAnalyzer."""
    print("\n📋 Тест: ZoneFeaturesAnalyzer")

    try:
        from bquant.analysis.zones import ZoneFeaturesAnalyzer

        zone_data = _create_synthetic_zone_data()
        zone_dict = {
            "zone_id": "synthetic_bull",
            "type": "bull",
            "duration": len(zone_data),
            "data": zone_data,
            "indicator_context": {
                "detection_indicator": "macd_hist",
                "signal_line": "macd_signal",
            },
        }

        analyzer = ZoneFeaturesAnalyzer(
            swing_strategy="zigzag",
            shape_strategy="statistical",
            divergence_strategy="classic",
            volatility_strategy="combined",
            volume_strategy="standard",
        )

        features = analyzer.extract_zone_features(zone_dict)
        metadata = features.metadata

        swing_available = metadata.get("swing_metrics") is not None
        shape_available = metadata.get("shape_metrics") is not None
        divergence_available = metadata.get("divergence_metrics") is not None
        volatility_available = metadata.get("volatility_metrics") is not None
        volume_available = metadata.get("volume_metrics") is not None

        print(f"  ✅ Swing metrics: {'есть' if swing_available else 'нет'}")
        print(f"  ✅ Shape metrics: {'есть' if shape_available else 'нет'}")
        print(f"  ✅ Divergence metrics: {'есть' if divergence_available else 'нет'}")
        print(f"  ✅ Volatility metrics: {'есть' if volatility_available else 'нет'}")
        print(f"  ✅ Volume metrics: {'есть' if volume_available else 'нет'}")

        return all([swing_available, shape_available, divergence_available, volatility_available, volume_available])

    except Exception as exc:
        print(f"  ❌ ZoneFeaturesAnalyzer example: {exc}")
        traceback.print_exc()
        return False


def test_pipeline_combination() -> bool:
    """Проверяем пример с Universal Pipeline и комбинацией стратегий."""
    print("\n📋 Тест: Universal Pipeline со стратегиями")

    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.data.samples import get_sample_data

        df = get_sample_data("tv_xauusd_1h")

        result = (
            analyze_zones(df)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist", min_duration=2)
            .with_strategies(
                swing="zigzag",
                shape="statistical",
                divergence="classic",
                volatility="combined",
                volume="standard",
            )
            .analyze(clustering=True)
            .build()
        )

        print(f"  ✅ Universal Pipeline выполнен: {len(result.zones)} зон")

        if not result.zones:
            print("  ⚠️ Нет зон для проверки признаков")
            return True

        zone = result.zones[0]
        if zone.features:
            print(f"  ✅ zone.features содержит ключи: {list(zone.features.keys())[:6]}")
            print(f"  ✅ volatility_regime: {zone.features.get('volatility_regime', 'N/A')}")
            print(f"  ✅ volume_indicator_corr: {zone.features.get('volume_indicator_corr', 'N/A')}")
            return True

        print("  ⚠️ zone.features отсутствует")
        return False

    except Exception as exc:
        print(f"  ❌ Universal Pipeline example: {exc}")
        traceback.print_exc()
        return False


def test_strategy_registry_usage() -> bool:
    """Проверяем примеры с StrategyRegistry."""
    print("\n📋 Тест: StrategyRegistry")

    try:
        from bquant.analysis.zones.strategies.registry import StrategyRegistry

        swing_before = set(StrategyRegistry.list_swing_strategies())
        shape_before = set(StrategyRegistry.list_shape_strategies())
        volume_before = set(StrategyRegistry.list_volume_strategies())

        print(f"  ✅ Зарегистрированные swing стратегии: {sorted(swing_before)}")
        print(f"  ✅ Зарегистрированные shape стратегии: {sorted(shape_before)}")
        print(f"  ✅ Зарегистрированные volume стратегии: {sorted(volume_before)}")

        # Регистрация и получение пользовательской стратегии
        @StrategyRegistry.register_swing_strategy("doc_test_swing")
        class _DocTestSwingStrategy:
            def __init__(self, threshold: float = 0.02):
                self.threshold = threshold

            def calculate_swing(self, zone_data):  # pragma: no cover - синтетическая реализация
                from bquant.analysis.zones.strategies.base import SwingMetrics

                return SwingMetrics(
                    num_swings=0,
                    avg_rally_pct=0.0,
                    avg_drop_pct=0.0,
                    max_rally_pct=0.0,
                    max_drop_pct=0.0,
                    rally_to_drop_ratio=0.0,
                    rally_count=0,
                    drop_count=0,
                    min_rally_pct=0.0,
                    min_drop_pct=0.0,
                    rally_amplitude_std=0.0,
                    drop_amplitude_std=0.0,
                    rally_amplitude_median=0.0,
                    drop_amplitude_median=0.0,
                    avg_rally_duration_bars=0.0,
                    avg_drop_duration_bars=0.0,
                    max_rally_duration_bars=0,
                    max_drop_duration_bars=0,
                    avg_rally_speed_pct_per_bar=0.0,
                    avg_drop_speed_pct_per_bar=0.0,
                    max_rally_speed_pct_per_bar=0.0,
                    max_drop_speed_pct_per_bar=0.0,
                    duration_symmetry=0.0,
                    strategy_name="doc_test_swing",
                    strategy_params={"threshold": self.threshold},
                )

            def get_name(self):  # pragma: no cover - синтетическая реализация
                return "doc_test_swing"

            def get_metadata(self):  # pragma: no cover - синтетическая реализация
                return {"threshold": self.threshold}

        custom_entry = StrategyRegistry.get_swing_strategy("doc_test_swing")
        instance = custom_entry() if isinstance(custom_entry, type) else custom_entry
        metrics = instance.calculate_swing(_create_synthetic_zone_data().head(20))
        print(f"  ✅ Пользовательская стратегия: {instance.get_name()}, threshold={instance.threshold}")
        print(f"  ✅ Возвращены метрики: strategy_name={metrics.strategy_name}, num_swings={metrics.num_swings}")

        return True

    except Exception as exc:
        print(f"  ❌ StrategyRegistry: {exc}")
        traceback.print_exc()
        return False


def test_language_check() -> bool:
    """Проверяем, что текст документа на русском."""
    print("\n📋 Тест: Язык текста")

    try:
        content = Path("docs/api/analysis/strategies.md").read_text(encoding="utf-8")
        russian_markers = ["стратегии", "индикатор", "волатильность", "корреляция", "универсальные"]
        found = sum(1 for word in russian_markers if word in content.lower())
        code_blocks = content.count("```python")

        print(f"  ✅ Найдено русских маркеров: {found}")
        print(f"  ✅ Количество python-блоков: {code_blocks}")
        return found >= len(russian_markers) - 1 and code_blocks >= 5

    except Exception as exc:
        print(f"  ❌ Language check: {exc}")
        return False


def test_cross_references() -> bool:
    """Проверяем, что ссылки из документа существуют."""
    print("\n📋 Тест: Cross-references")

    references = [
        Path("docs/api/analysis/zones.md"),
        Path("docs/api/analysis/pipeline.md"),
        Path("docs/api/analysis/statistical.md"),
        Path("docs/api/extension_guide.md"),
        Path("docs/user_guide/quick_start.md"),
        Path("docs/examples/README.md"),
        Path("docs/api/visualization/README.md"),
        Path("docs/api/indicators/README.md"),
        Path("examples/02_macd_zone_analysis.py"),
        Path("research/notebooks/03_zones_universal.py"),
        Path("research/notebooks/03_analysis_new_features.py"),
        Path("devref/gaps/swing_detection_approaches.md"),
        Path("tests/integration"),
        Path("tests/unit/test_classic_divergence_strategy.py"),
        Path("tests/unit/test_combined_volatility_strategy.py"),
    ]

    success = 0
    for ref in references:
        if ref.exists():
            print(f"  ✅ {ref}")
            success += 1
        else:
            print(f"  ❌ {ref} — отсутствует")

    return success == len(references)


def main() -> bool:
    print("🔍 Валидация docs/api/analysis/strategies.md")
    print("=" * 60)

    tests = [
        ("Импорты", test_imports_from_docs),
        ("Примеры стратегий", test_strategy_examples),
        ("ZoneFeaturesAnalyzer", test_zone_features_analyzer_example),
        ("Universal Pipeline", test_pipeline_combination),
        ("StrategyRegistry", test_strategy_registry_usage),
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

