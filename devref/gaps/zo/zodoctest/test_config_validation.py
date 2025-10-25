#!/usr/bin/env python3
"""Валидация docs/api/core/config.md."""

import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd

# Ускоряем запуск стратегий и индикаторов в тестовой среде
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def _prepare_pandas_ta(minimal_functions: Iterable[str] = ("zigzag",)) -> None:
    """Ограничиваем регистрацию pandas-ta минимальным набором индикаторов."""

    try:
        from bquant.indicators.library import pandas_ta as pandas_ta_loader
    except Exception:
        return

    try:
        import pandas_ta as ta
    except Exception:
        return

    if getattr(ta, "zigzag", None) is None:
        def _zigzag_stub(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
            if isinstance(df, pd.DataFrame):
                series = df.get("close")
                if series is None:
                    numeric = df.select_dtypes(include=[np.number])
                    series = numeric.iloc[:, 0] if not numeric.empty else pd.Series(dtype=float)
            else:
                series = pd.Series(df)

            base_series = series if isinstance(series, pd.Series) else pd.Series(series)
            return pd.DataFrame({"zigzag": base_series.copy()})

        ta.zigzag = _zigzag_stub

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


def _ensure_stub_zigzag_registered() -> None:
    """Гарантируем наличие zigzag в IndicatorFactory для фабрик стратегий."""

    try:
        from bquant.indicators.base import IndicatorFactory, LibraryIndicator
    except Exception:
        return

    registry_key = "pandas_ta_zigzag"
    if registry_key in getattr(IndicatorFactory, "_registry", {}):
        return

    def _zigzag_stub(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        if isinstance(df, pd.DataFrame):
            series = df.get("close")
            if series is None:
                numeric = df.select_dtypes(include=[np.number])
                series = numeric.iloc[:, 0] if not numeric.empty else pd.Series(dtype=float)
        else:
            series = pd.Series(df)

        base_series = series if isinstance(series, pd.Series) else pd.Series(series)
        return pd.DataFrame({"zigzag": base_series.copy()})

    class _StubZigZagIndicator(LibraryIndicator):
        def __init__(self, **params):
            super().__init__("zigzag", _zigzag_stub, parameters=params)

    IndicatorFactory.register_indicator(registry_key, _StubZigZagIndicator)
    IndicatorFactory.register_library_function(registry_key, _zigzag_stub)


_prepare_pandas_ta()
_ensure_stub_zigzag_registered()


def test_data_path_and_timeframe() -> bool:
    """Проверяем пример получения пути к данным и валидации таймфрейма."""

    print("📋 Тест: Пути и таймфреймы")

    try:
        from bquant.core.config import get_data_path, validate_timeframe
    except Exception as exc:
        print(f"  ❌ Импорт функций не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        path = Path(get_data_path("XAUUSD", "1h", data_source="tradingview", quote_provider="oanda"))
        ok_valid = validate_timeframe("1h") == "1h"
        try:
            validate_timeframe("2D")
        except ValueError:
            ok_invalid = True
        else:
            ok_invalid = False

        print(f"  ✅ Путь: {path}")
        print(f"  ✅ Валидация таймфрейма: {ok_valid}")
        print(f"  ✅ Ошибка для 2D: {ok_invalid}")
        return path.suffix == ".csv" and ok_valid and ok_invalid
    except Exception as exc:
        print(f"  ❌ Ошибка выполнения примера: {exc}")
        traceback.print_exc()
        return False


def test_indicator_params_example() -> bool:
    """Проверяем пример получения параметров индикатора."""

    print("\n📋 Тест: Параметры индикатора")

    try:
        from bquant.core.config import get_indicator_params
    except Exception as exc:
        print(f"  ❌ Импорт get_indicator_params не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        default_params = get_indicator_params("macd")
        overridden = get_indicator_params("macd", fast=8)
        print(f"  ✅ Параметры по умолчанию: {default_params}")
        print(f"  ✅ Переопределённый fast: {overridden['fast']}")
        return default_params["slow"] == 26 and overridden["fast"] == 8
    except Exception as exc:
        print(f"  ❌ Ошибка примера с параметрами: {exc}")
        traceback.print_exc()
        return False


def test_results_path_example() -> bool:
    """Проверяем пример получения пути для результатов."""

    print("\n📋 Тест: Путь результатов")

    try:
        from bquant.core.config import get_results_path
    except Exception as exc:
        print(f"  ❌ Импорт get_results_path не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        result_path = Path(get_results_path("zone_analysis_2025-08-29", file_type="csv"))
        print(f"  ✅ Итоговый путь: {result_path}")
        return result_path.name == "zone_analysis_2025-08-29.csv"
    except Exception as exc:
        print(f"  ❌ Ошибка получения пути результатов: {exc}")
        traceback.print_exc()
        return False


def test_strategy_factories_examples() -> bool:
    """Воспроизводим все примеры фабрик стратегий."""

    print("\n📋 Тест: Фабрики стратегий")

    try:
        from bquant.core.config import (
            create_divergence_strategy,
            create_shape_strategy,
            create_swing_strategy,
            create_volatility_strategy,
            create_volume_strategy,
        )
    except Exception as exc:
        print(f"  ❌ Импорт фабрик не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        swing_default = create_swing_strategy()
        swing_named = create_swing_strategy("find_peaks")
        swing_custom = create_swing_strategy({
            "type": "zigzag",
            "params": {"legs": 15, "deviation": 0.03},
        })
        shape = create_shape_strategy("statistical")
        divergence = create_divergence_strategy("classic")
        volatility = create_volatility_strategy({
            "type": "combined",
            "params": {"bb_length": 20, "bb_std": 2.0, "touch_threshold": 0.02},
        })
        volume = create_volume_strategy("standard")

        print(f"  ✅ Swing default: {swing_default.__class__.__name__}")
        print(f"  ✅ Swing find_peaks: {swing_named.__class__.__name__}")
        print(f"  ✅ Swing custom: {swing_custom.__class__.__name__}")
        print(f"  ✅ Shape: {shape}")
        print(f"  ✅ Divergence: {divergence}")
        print(f"  ✅ Volatility: {volatility}")
        print(f"  ✅ Volume: {volume}")

        return all(obj is not None for obj in (
            swing_default,
            swing_named,
            swing_custom,
            shape,
            divergence,
            volatility,
            volume,
        ))
    except Exception as exc:
        print(f"  ❌ Ошибка при создании стратегий: {exc}")
        traceback.print_exc()
        return False


def test_analysis_config_example() -> bool:
    """Проверяем, что ANALYSIS_CONFIG соответствует документации."""

    print("\n📋 Тест: ANALYSIS_CONFIG")

    try:
        from bquant.core.config import ANALYSIS_CONFIG
    except Exception as exc:
        print(f"  ❌ Импорт ANALYSIS_CONFIG не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        expected_zone_analysis = {
            "min_duration": 2,
            "min_amplitude": 0.001,
            "normalization_method": "atr",
            "detection_method": "sign_change",
        }
        expected_zone_features = {
            "swing_strategy": {
                "type": "zigzag",
                "params": {"legs": 10, "deviation": 0.05},
            },
            "divergence_strategy": {"type": "none", "params": {}},
            "shape_strategy": {
                "type": "statistical",
                "params": {"calculate_smoothness": True, "bias_correction": True},
            },
            "volume_strategy": {"type": "none", "params": {}},
        }

        zone_analysis_ok = all(
            ANALYSIS_CONFIG["zone_analysis"].get(key) == value
            for key, value in expected_zone_analysis.items()
        )
        zone_features_block: Dict[str, Dict[str, object]] = ANALYSIS_CONFIG["zone_features"]
        features_ok = all(
            zone_features_block.get(name) == spec
            for name, spec in expected_zone_features.items()
        )
        stats_ok = ANALYSIS_CONFIG.get("statistical_analysis", {}).get("bootstrap_samples") == 1000
        pattern_ok = ANALYSIS_CONFIG.get("pattern_analysis", {}).get("similarity_threshold") == 0.8

        print(f"  ✅ zone_analysis: {zone_analysis_ok}")
        print(f"  ✅ zone_features: {features_ok}")
        print(f"  ✅ statistical_analysis.bootstrap_samples == 1000: {stats_ok}")
        print(f"  ✅ pattern_analysis.similarity_threshold == 0.8: {pattern_ok}")

        return zone_analysis_ok and features_ok and stats_ok and pattern_ok
    except Exception as exc:
        print(f"  ❌ Ошибка проверки ANALYSIS_CONFIG: {exc}")
        traceback.print_exc()
        return False


def test_directory_management_example() -> bool:
    """Проверяем пример управления директориями."""

    print("\n📋 Тест: Управление директориями")

    try:
        from bquant.core import config as cfg
    except Exception as exc:
        print(f"  ❌ Импорт модуля config не удался: {exc}")
        traceback.print_exc()
        return False

    temp_dir = project_root / "devref" / "gaps" / "zo" / "zodoctest" / "_tmp_config_data"

    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    try:
        original_status = cfg.get_directory_status()
        original_data = cfg.get_data_dir()

        cfg.set_data_dir(temp_dir)
        status = cfg.get_directory_status()
        is_custom = status["data_dir"].get("is_custom")

        cfg.reset_directories_to_defaults()
        reset_path = cfg.get_data_dir()

        print(f"  ✅ Кастомный путь создан: {temp_dir.exists()}")
        print(f"  ✅ Флаг is_custom: {is_custom}")
        print(f"  ✅ Сброс восстановил путь: {reset_path == original_data}")

        return temp_dir.exists() and is_custom and reset_path == original_data and original_status is not None
    except Exception as exc:
        print(f"  ❌ Ошибка управления директориями: {exc}")
        traceback.print_exc()
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def test_cross_references() -> bool:
    """Проверяем, что все cross-reference ссылки существуют."""

    print("\n📋 Тест: Cross-references")

    references = [
        Path("docs/api/analysis/strategies.md"),
    ]

    success = 0
    for ref in references:
        if ref.exists():
            print(f"  ✅ {ref}")
            success += 1
        else:
            print(f"  ❌ {ref} отсутствует")

    return success == len(references)


def test_language() -> bool:
    """Убеждаемся, что текст раздела остаётся русскоязычным."""

    print("\n📋 Тест: Язык документа")

    try:
        content = Path("docs/api/core/config.md").read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  ❌ Не удалось прочитать файл: {exc}")
        traceback.print_exc()
        return False

    markers = ["конфигурация", "директории", "стратегий", "таймфрейма"]
    found = sum(1 for marker in markers if marker in content.lower())
    code_blocks = content.count("```python")

    print(f"  ✅ Русскоязычных маркеров: {found}")
    print(f"  ✅ Число кодовых блоков: {code_blocks}")

    return found >= len(markers) - 1 and code_blocks >= 6


def main() -> bool:
    print("🔍 Валидация docs/api/core/config.md")
    print("=" * 60)

    tests = [
        ("Пути и таймфреймы", test_data_path_and_timeframe),
        ("Параметры индикатора", test_indicator_params_example),
        ("Путь результатов", test_results_path_example),
        ("Фабрики стратегий", test_strategy_factories_examples),
        ("ANALYSIS_CONFIG", test_analysis_config_example),
        ("Управление директориями", test_directory_management_example),
        ("Cross-references", test_cross_references),
        ("Язык документа", test_language),
    ]

    results = []
    for name, func in tests:
        print(f"\n➡️ {name}")
        ok = func()
        results.append(ok)
        print(f"✔️ {name}: {'успех' if ok else 'ошибка'}")

    total = sum(results)
    print("=" * 60)
    print(f"Итого: {total}/{len(tests)} тестов успешно")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

