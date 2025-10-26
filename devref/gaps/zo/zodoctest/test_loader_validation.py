import os
import sys
import traceback
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterable, List, Tuple

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCUMENT_PATH = PROJECT_ROOT / "docs" / "api" / "data" / "loader.md"


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def _build_demo_dataframe(rows: int = 120) -> pd.DataFrame:
    """Создаёт OHLCV DataFrame, совместимый с проверками loader."""

    index = pd.date_range("2024-01-01", periods=rows, freq="H", name="time")
    base = np.linspace(1900.0, 1950.0, rows)
    oscillation = np.sin(np.linspace(0, 8 * np.pi, rows))
    close = base + oscillation
    open_ = close - 0.4
    high = np.maximum(open_, close) + 0.7
    low = np.minimum(open_, close) - 0.7
    volume = np.linspace(800, 1800, rows)

    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=index,
    )


def test_code_examples() -> bool:
    print("\n📥 Тест: Примеры загрузки и перечисления данных")

    try:
        from bquant.data.loader import (
            load_ohlcv_data,
            get_data_info,
            load_symbol_data,
            load_all_data_files,
        )
        from bquant.core.config import get_data_dir, set_data_dir
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта loader/config: {exc}")
        traceback.print_exc()
        return False

    demo_df = _build_demo_dataframe()

    with TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        data_dir = tmp_root / "data"
        data_dir.mkdir()

        manual_csv = data_dir / "XAUUSD_1h.csv"
        tradingview_csv = data_dir / "OANDA_XAUUSD, 60.csv"

        demo_df.to_csv(manual_csv)
        demo_df.to_csv(tradingview_csv)

        original_dir = get_data_dir()
        original_cwd = os.getcwd()

        try:
            set_data_dir(data_dir)
            os.chdir(tmp_root)

            df = load_ohlcv_data('data/XAUUSD_1h.csv', symbol='XAUUSD', timeframe='1h')
            info = get_data_info(df)
            tv_df = load_symbol_data(
                'XAUUSD',
                '1h',
                data_source='tradingview',
                quote_provider='oanda',
            )
            datasets = load_all_data_files()
        except Exception as exc:  # pragma: no cover - диагностика выполнения
            print(f"  ❌ Ошибка при исполнении примеров: {exc}")
            traceback.print_exc()
            return False
        finally:
            os.chdir(original_cwd)
            set_data_dir(original_dir)

    if df.empty or tv_df.empty:
        print("  ❌ Один из DataFrame пуст")
        return False

    if info.get('rows', 0) != len(df):
        print(f"  ❌ Некорректная статистика get_data_info: {info}")
        return False

    if not set(['XAUUSD_1h', 'XAUUSD_60']).issubset(datasets.keys()):
        print(f"  ❌ Не все наборы данных загружены: {datasets.keys()}")
        return False

    if any(data.empty for data in datasets.values()):
        print("  ❌ Найден пустой датасет в load_all_data_files")
        return False

    print(
        "  ℹ️ Загружено наборов:",
        f"{len(datasets)}, строки: {len(df)}, таймфрейм: 1h",
    )
    return True


def test_logging_snippet() -> bool:
    print("\n🪵 Тест: Управление логированием")

    import logging

    try:
        logging.getLogger('bquant.data.loader').setLevel(logging.WARNING)
        logging.getLogger('bquant.data').setLevel(logging.WARNING)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при настройке логгера: {exc}")
        traceback.print_exc()
        return False

    loader_level = logging.getLogger('bquant.data.loader').level
    data_level = logging.getLogger('bquant.data').level
    print(f"  ℹ️ Уровни логгера: loader={loader_level}, data={data_level}")
    return loader_level == logging.WARNING and data_level == logging.WARNING


def test_cross_reference() -> bool:
    print("\n🔗 Тест: Проверка ссылок")

    targets: Iterable[Tuple[str, Path]] = [
        ("core logging", PROJECT_ROOT / 'docs' / 'api' / 'core' / 'logging.md'),
    ]

    missing: List[str] = []
    for name, path in targets:
        if not path.exists():
            missing.append(name)

    if missing:
        print(f"  ❌ Отсутствуют файлы: {missing}")
        return False

    if not DOCUMENT_PATH.exists():
        print("  ❌ Сам документ loader.md отсутствует")
        return False

    print("  ℹ️ Все ссылки доступны")
    return True


def main() -> int:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

    tests: Tuple[Tuple[str, Callable[[], bool]], ...] = (
        ("Примеры кода", test_code_examples),
        ("Логирование", test_logging_snippet),
        ("Ссылки", test_cross_reference),
    )

    all_success = True
    for title, func in tests:
        success = func()
        _print_result(title, success)
        all_success &= success

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
