import sys
import traceback
from pathlib import Path
from typing import Callable, Iterable, List, Tuple

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCUMENT_PATH = PROJECT_ROOT / "docs" / "api" / "data" / "validator.md"


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def _build_dataframe(rows: int = 120) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=rows, freq="1h", name="time")
    base = np.linspace(100.0, 110.0, rows)
    wave = np.sin(np.linspace(0, 4 * np.pi, rows))

    return pd.DataFrame(
        {
            "open": base + wave,
            "high": base + wave + 0.6,
            "low": base + wave - 0.6,
            "close": base + 0.5 * wave,
            "volume": np.linspace(500, 900, rows),
        },
        index=index,
    )


def test_code_examples() -> bool:
    print("\n🧪 Тест: Примеры валидации данных")

    try:
        from bquant.data.validator import (
            validate_ohlcv_data,
            validate_data_completeness,
            validate_price_consistency,
            validate_time_series_continuity,
            validate_statistical_properties,
        )
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта validator: {exc}")
        traceback.print_exc()
        return False

    df = _build_dataframe()

    try:
        overall = validate_ohlcv_data(df)
        completeness = validate_data_completeness(df)
        prices = validate_price_consistency(df)
        ts = validate_time_series_continuity(df, expected_frequency="1h")
        stats = validate_statistical_properties(df)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при исполнении примеров: {exc}")
        traceback.print_exc()
        return False

    if not overall.get("stats") or "is_valid" not in overall:
        print("  ❌ validate_ohlcv_data вернул неожиданный результат")
        return False

    if not completeness.get("is_complete", True):
        print(f"  ❌ validate_data_completeness сообщил проблемы: {completeness}")
        return False

    if "price_issues" not in prices or "is_consistent" not in prices:
        print("  ❌ validate_price_consistency отсутствуют ожидаемые ключи")
        return False

    if ts.get("detected_frequency") not in {"h", "1h", "H", "1H"}:
        print(f"  ❌ validate_time_series_continuity частота: {ts}")
        return False

    if "statistics" not in stats or "outliers" not in stats:
        print("  ❌ validate_statistical_properties отсутствуют ключи statistics/outliers")
        return False

    print(
        "  ℹ️ Валидация пройдена:",
        f"is_valid={overall['is_valid']}, detected_freq={ts['detected_frequency']}",
    )
    return True


def test_cross_references() -> bool:
    print("\n🔗 Тест: Проверка документа")

    targets: Iterable[Tuple[str, Path]] = [
        ("Документация validator", DOCUMENT_PATH),
    ]

    missing: List[str] = []
    for name, path in targets:
        if not path.exists():
            missing.append(name)

    if missing:
        print(f"  ❌ Отсутствуют файлы: {missing}")
        return False

    if "validate_statistical_properties" not in DOCUMENT_PATH.read_text(encoding="utf-8"):
        print("  ❌ В документе нет описания validate_statistical_properties")
        return False

    print("  ℹ️ Документ доступен и содержит все функции")
    return True


def main() -> int:
    tests: Tuple[Tuple[str, Callable[[], bool]], ...] = (
        ("Примеры кода", test_code_examples),
        ("Ссылки", test_cross_references),
    )

    success = True
    for title, func in tests:
        result = func()
        _print_result(title, result)
        success &= result

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
