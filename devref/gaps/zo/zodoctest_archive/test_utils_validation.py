#!/usr/bin/env python3
"""Валидация документации docs/api/core/utils.md."""

from __future__ import annotations

import os
import sys
import traceback
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def _build_dataframe() -> pd.DataFrame:
    """Возвращает DataFrame как в документации."""

    return pd.DataFrame(
        {
            "open": [100.0, 102.0, 105.0],
            "high": [101.0, 103.0, 106.0],
            "low": [99.0, 101.0, 104.0],
            "close": [100.5, 102.5, 105.5],
            "volume": [1200, 1350, 1280],
        }
    )


def test_returns_and_normalization() -> bool:
    """Проверяет пример расчёта доходностей и нормализации."""

    print("\n📋 Тест: Доходности и нормализация")

    try:
        from bquant.core.utils import calculate_returns, normalize_data
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Не удалось импортировать утилиты: {exc}")
        traceback.print_exc()
        return False

    prices = pd.Series([1, 1.1, 1.2])
    frame = _build_dataframe()

    try:
        returns = calculate_returns(prices, method="simple")
        normalized = normalize_data(frame, method="zscore")
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при выполнении примеров: {exc}")
        traceback.print_exc()
        return False

    if returns.shape[0] != prices.shape[0]:
        print("  ❌ Размер Series доходностей не совпадает")
        return False

    if returns.iloc[-1] <= 0:
        print(f"  ❌ Последняя доходность не положительная: {returns.iloc[-1]}")
        return False

    numeric_columns = normalized.select_dtypes(include="number")
    if numeric_columns.isna().any().any():
        print("  ❌ В нормализованных данных присутствуют NaN")
        return False

    close_mean = abs(numeric_columns["close"].mean())
    print(f"  ℹ️ Среднее нормализованных close: {close_mean:.6f}")
    return close_mean < 1e-9


def test_save_results_example() -> bool:
    """Проверяет пример сохранения результатов."""

    print("\n📋 Тест: Сохранение результатов")

    try:
        from bquant.core.utils import save_results
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Не удалось импортировать save_results: {exc}")
        traceback.print_exc()
        return False

    frame = _build_dataframe()

    with TemporaryDirectory() as tmp_dir:
        cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            ok = save_results(frame, "results/out.csv", index=False)
        except Exception as exc:  # pragma: no cover - диагностика выполнения
            print(f"  ❌ Ошибка сохранения: {exc}")
            traceback.print_exc()
            return False
        finally:
            os.chdir(cwd)

        saved_path = Path(tmp_dir) / "results" / "out.csv"
        if not ok or not saved_path.exists():
            print("  ❌ Файл не создан")
            return False

        loaded = pd.read_csv(saved_path)
        volume_sum = loaded["volume"].sum()
        print(f"  ℹ️ Суммарный объём: {volume_sum}")
        return abs(volume_sum - frame["volume"].sum()) < 1e-9


def test_validate_ohlcv_example() -> bool:
    """Проверяет пример validate_ohlcv_columns."""

    print("\n📋 Тест: Валидация OHLCV")

    try:
        from bquant.core.utils import validate_ohlcv_columns
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Не удалось импортировать validate_ohlcv_columns: {exc}")
        traceback.print_exc()
        return False

    frame = _build_dataframe()

    try:
        result = validate_ohlcv_columns(frame)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка проверки OHLCV: {exc}")
        traceback.print_exc()
        return False

    print(f"  ℹ️ Результат: is_valid={result['is_valid']}, messages={result['messages']}")
    return result["is_valid"] and any("валидна" in msg.lower() for msg in result["messages"])


def test_misc_utils_example() -> bool:
    """Проверяет пример create_timestamp и ensure_directory."""

    print("\n📋 Тест: Прочие утилиты")

    try:
        from bquant.core.utils import create_timestamp, ensure_directory
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт create_timestamp/ensure_directory не удался: {exc}")
        traceback.print_exc()
        return False

    with TemporaryDirectory() as tmp_dir:
        cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            ts = create_timestamp("readable")
            ensured = ensure_directory("results/charts")
        except Exception as exc:  # pragma: no cover - диагностика выполнения
            print(f"  ❌ Ошибка утилит: {exc}")
            traceback.print_exc()
            return False
        finally:
            os.chdir(cwd)

        timestamp_ok = isinstance(ts, str) and ":" in ts
        directory_ok = (Path(tmp_dir) / "results" / "charts").exists()
        print(f"  ℹ️ Метка времени: {ts}, директория существует: {directory_ok}")
        return timestamp_ok and directory_ok


def test_deprecated_examples() -> bool:
    """Проверяет оба сниппета с декоратором @deprecated."""

    print("\n📋 Тест: Декоратор @deprecated")

    try:
        from bquant.core.utils import deprecated
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Не удалось импортировать deprecated: {exc}")
        traceback.print_exc()
        return False

    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always", DeprecationWarning)

        @deprecated("Use new_method() instead")
        def old_method() -> str:
            return "legacy"

        first_result = old_method()

        @deprecated("Use ZoneFeaturesAnalyzer.extract_zone_features() from bquant.analysis.zones instead")
        def calculate_zone_features(zone):
            return {"zone": zone}

        second_result = calculate_zone_features("demo")

    messages = [str(warning.message) for warning in records]
    print(f"  ℹ️ Предупреждений: {len(messages)}, тексты: {messages}")

    attributes_ok = getattr(old_method, "__deprecated__", False) and getattr(
        calculate_zone_features, "__deprecation_message__", ""
    ).startswith("Use ZoneFeaturesAnalyzer")

    return (
        first_result == "legacy"
        and second_result == {"zone": "demo"}
        and any("Use new_method() instead" in msg for msg in messages)
        and any("ZoneFeaturesAnalyzer" in msg for msg in messages)
        and attributes_ok
    )


def test_references_and_language() -> bool:
    """Проверяет наличие ссылок и русский язык раздела."""

    print("\n📋 Тест: Ссылки и язык документа")

    doc_path = Path("docs/api/core/utils.md")
    if not doc_path.exists():
        print("  ❌ Файл документации не найден")
        return False

    content = doc_path.read_text(encoding="utf-8")
    reference_ok = "docs/api/indicators/macd.md" in content and Path(
        "docs/api/indicators/macd.md"
    ).exists()

    russian_markers = ["утилиты", "нормализация", "устаревания", "рекомендации"]
    markers_found = sum(1 for marker in russian_markers if marker in content.lower())
    code_blocks = content.count("```python")

    print(
        "  ℹ️ Ссылки найдены: %s, русских маркеров: %s, python-блоков: %s"
        % (reference_ok, markers_found, code_blocks)
    )

    return reference_ok and markers_found >= len(russian_markers) - 1 and code_blocks >= 4


def run_all_tests() -> Iterable[Tuple[str, bool]]:
    yield "Доходности и нормализация", test_returns_and_normalization()
    yield "Сохранение результатов", test_save_results_example()
    yield "Валидация OHLCV", test_validate_ohlcv_example()
    yield "Прочие утилиты", test_misc_utils_example()
    yield "Декоратор @deprecated", test_deprecated_examples()
    yield "Ссылки и язык", test_references_and_language()


def main() -> int:
    print("🔍 Валидация docs/api/core/utils.md")
    print("=" * 60)

    all_ok = True
    for title, success in run_all_tests():
        _print_result(title, success)
        all_ok = all_ok and success

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
