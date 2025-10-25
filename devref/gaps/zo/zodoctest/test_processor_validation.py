import sys
import traceback
import warnings
from pathlib import Path
from typing import Callable, Tuple

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCUMENT_PATH = PROJECT_ROOT / "docs" / "api" / "data" / "processor.md"


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def _build_demo_dataframe(rows: int = 240) -> pd.DataFrame:
    """Создаёт OHLCV DataFrame для проверки примеров processor."""

    rng = np.random.default_rng(42)
    index = pd.date_range("2024-01-01", periods=rows, freq="H", name="time")

    base = np.linspace(1800.0, 1860.0, rows)
    drift = np.sin(np.linspace(0, 6 * np.pi, rows)) * 5
    noise = rng.normal(0.0, 1.2, size=rows)

    close = base + drift + noise
    open_ = close + rng.normal(0.0, 0.6, size=rows)
    high = np.maximum(open_, close) + rng.uniform(0.1, 1.5, size=rows)
    low = np.minimum(open_, close) - rng.uniform(0.1, 1.5, size=rows)
    volume = rng.integers(900, 1900, size=rows).astype(float)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=index,
    )

    # Добавляем несколько пропусков и выброс для проверки очистки
    df.iloc[12, df.columns.get_loc("close")] = np.nan
    df.iloc[36, df.columns.get_loc("open")] = np.nan
    df.iloc[48, df.columns.get_loc("high")] = df["high"].iloc[48] * 1.35

    return df


def test_code_examples() -> bool:
    print("\n🧪 Тест: Примеры очистки, подготовки, ресемплинга и индикаторов")

    try:
        from bquant.data.processor import (
            clean_ohlcv_data,
            prepare_data_for_analysis,
            resample_ohlcv,
            calculate_derived_indicators,
        )
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта processor: {exc}")
        traceback.print_exc()
        return False

    df = _build_demo_dataframe()

    try:
        clean = clean_ohlcv_data(df, fill_method='forward', remove_outliers=True)
        prepared = prepare_data_for_analysis(
            clean,
            add_tech_features=True,
            normalize=True,
        )
        hourly = resample_ohlcv(df, '1h')
        daily = resample_ohlcv(df, '1d')
        derived = calculate_derived_indicators(df)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при выполнении примеров: {exc}")
        traceback.print_exc()
        return False

    if clean.empty:
        print("  ❌ Результат clean_ohlcv_data пустой")
        return False

    if prepared.empty or 'close_zscore' not in prepared.columns:
        print("  ❌ prepare_data_for_analysis вернул неожиданную структуру")
        return False

    if hourly.empty or daily.empty:
        print("  ❌ Результаты resample_ohlcv пустые")
        return False

    if len(daily) >= len(df):
        print("  ❌ Суточный ресемплинг не уменьшил количество строк")
        return False

    expected_columns = {'hl_avg', 'typical_price', 'gap', 'gap_pct'}
    if not expected_columns.issubset(set(derived.columns)):
        print(f"  ❌ Не все индикаторы рассчитаны: {expected_columns - set(derived.columns)}")
        return False

    print(
        "  ℹ️ prepared shape=",
        prepared.shape,
        ", daily rows=",
        len(daily),
        ", derived columns=",
        len(derived.columns),
    )
    return True


def test_function_exports() -> bool:
    print("\n🧾 Тест: Упомянутые функции доступны в модуле")

    try:
        import bquant.data.processor as processor
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта bquant.data.processor: {exc}")
        traceback.print_exc()
        return False

    required = [
        'clean_ohlcv_data',
        'remove_price_outliers',
        'calculate_derived_indicators',
        'resample_ohlcv',
        'normalize_prices',
        'detect_market_sessions',
        'add_technical_features',
        'create_lagged_features',
        'prepare_data_for_analysis',
    ]

    missing = [name for name in required if not hasattr(processor, name)]
    if missing:
        print(f"  ❌ Не найдены функции: {missing}")
        return False

    print("  ℹ️ Все перечисленные функции доступны")
    return True


def test_document_presence() -> bool:
    print("\n📄 Тест: Документ и язык")

    if not DOCUMENT_PATH.exists():
        print("  ❌ Отсутствует файл processor.md")
        return False

    text = DOCUMENT_PATH.read_text(encoding='utf-8')
    if '```python' not in text:
        print("  ❌ В документе отсутствуют python-блоки")
        return False

    if any(word in text for word in ['TODO', 'TBD']):
        print("  ❌ Найдены маркеры TODO/TBD")
        return False

    print("  ℹ️ Документ доступен, кодовые блоки найдены")
    return True


def main() -> int:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

    tests: Tuple[Tuple[str, Callable[[], bool]], ...] = (
        ("Примеры кода", test_code_examples),
        ("Экспорт функций", test_function_exports),
        ("Документ", test_document_presence),
    )

    all_success = True
    for title, func in tests:
        success = func()
        _print_result(title, success)
        all_success &= success

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
