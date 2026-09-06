"""Валидация документации docs/api/data/README.md."""

from __future__ import annotations

import logging
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


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def _build_demo_dataframe(rows: int = 120) -> pd.DataFrame:
    """Создаёт OHLCV DataFrame, совместимый с примерами документации."""

    index = pd.date_range("2024-01-01", periods=rows, freq="H", name="time")
    base = np.linspace(1900.0, 1950.0, rows)
    oscillation = np.sin(np.linspace(0, 6 * np.pi, rows))
    close = base + oscillation
    open_ = close - 0.3
    high = np.maximum(open_, close) + 0.6
    low = np.minimum(open_, close) - 0.6
    volume = np.linspace(1_000, 1_500, rows)

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


def test_loader_examples() -> bool:
    print("\n📥 Тест: Примеры загрузки данных")

    try:
        from bquant.data.loader import (
            load_ohlcv_data,
            load_symbol_data,
            load_xauusd_data,
        )
        from bquant.core.config import get_data_dir, set_data_dir
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта loader/config: {exc}")
        traceback.print_exc()
        return False

    demo_df = _build_demo_dataframe()

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        csv_path = tmp_path / "data.csv"
        demo_df.to_csv(csv_path)

        tradingview_file = tmp_path / "OANDA_XAUUSD, 60.csv"
        demo_df.to_csv(tradingview_file)

        original_dir = get_data_dir()
        try:
            set_data_dir(tmp_path)

            data = load_ohlcv_data(str(csv_path), symbol="XAUUSD", timeframe="1h")
            tv_data = load_symbol_data(
                "XAUUSD",
                "1h",
                data_source="tradingview",
                quote_provider="oanda",
            )
            xau = load_xauusd_data("1h")
        except Exception as exc:  # pragma: no cover - диагностика выполнения
            print(f"  ❌ Ошибка при выполнении примеров загрузки: {exc}")
            traceback.print_exc()
            return False
        finally:
            # Возвращаем runtime директорию данных
            set_data_dir(original_dir)

    if data.empty or tv_data.empty or xau.empty:
        print("  ❌ Один из DataFrame оказался пустым")
        return False

    if not list(data.columns)[:4] == ["open", "high", "low", "close"]:
        print(f"  ❌ Неверные колонки в data: {data.columns}")
        return False

    if not data.index.equals(tv_data.index) or not data.index.equals(xau.index):
        print("  ❌ Индексы DataFrame не совпадают")
        return False

    print(f"  ℹ️ Загружено строк: {len(data)}; timeframe: 1h")
    return True


def test_processor_examples() -> bool:
    print("\n🔄 Тест: Примеры обработки данных")

    try:
        from bquant.data.processor import (
            clean_ohlcv_data,
            prepare_data_for_analysis,
            resample_ohlcv,
        )
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта processor: {exc}")
        traceback.print_exc()
        return False

    demo_df = _build_demo_dataframe()

    try:
        clean_data = clean_ohlcv_data(
            demo_df,
            remove_outliers=True,
            fill_method="forward",
        )
        analysis_data = prepare_data_for_analysis(
            clean_data,
            add_tech_features=True,
            normalize=True,
        )
        hourly_data = resample_ohlcv(demo_df, "1H")
        daily_data = resample_ohlcv(demo_df, "1D")
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при обработке данных: {exc}")
        traceback.print_exc()
        return False

    if clean_data.empty or analysis_data.empty:
        print("  ❌ Результаты очистки или подготовки пустые")
        return False

    if hourly_data.empty or daily_data.empty:
        print("  ❌ Результаты ресемплинга пустые")
        return False

    numeric_cols = analysis_data.select_dtypes(include=["number"])
    if numeric_cols.isna().all().all():
        print("  ❌ Все числовые признаки содержат NaN")
        return False

    print(
        "  ℹ️ Подготовленные признаки:",
        f"{list(numeric_cols.columns)[:5]} … (всего {numeric_cols.shape[1]})",
    )
    return True


def test_validator_examples() -> bool:
    print("\n✅ Тест: Примеры валидации данных")

    try:
        from bquant.data.validator import (
            validate_ohlcv_data,
            validate_data_completeness,
        )
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта validator: {exc}")
        traceback.print_exc()
        return False

    demo_df = _build_demo_dataframe()

    try:
        validation_result = validate_ohlcv_data(demo_df)
        completeness = validate_data_completeness(demo_df)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при валидации данных: {exc}")
        traceback.print_exc()
        return False

    if not validation_result.get("is_valid", False):
        print(f"  ❌ Валидация OHLCV не прошла: {validation_result}")
        return False

    if not completeness.get("is_complete", False):
        print(f"  ❌ Проверка полноты не прошла: {completeness}")
        return False

    print(
        f"  ℹ️ Валидация прошла, предупреждений: {len(validation_result.get('warnings', []))}"
    )
    return True


def test_samples_examples() -> bool:
    print("\n📊 Тест: Примеры работы с sample данными")

    try:
        from bquant.data.samples import (
            SampleDataGenerator,
            convert_to_dataframe,
            convert_to_list_of_dicts,
            get_data_statistics,
            get_dataset_info,
            get_sample_data,
            list_datasets,
            list_dataset_names,
        )
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта samples: {exc}")
        traceback.print_exc()
        return False

    try:
        datasets_summary = list_datasets()
        dataset_names = list_dataset_names()
        info = get_dataset_info("tv_xauusd_1h")
        df = get_sample_data("tv_xauusd_1h")
        data_list = get_sample_data("tv_xauusd_1h", format="dict")
        df_converted = convert_to_dataframe(data_list, "tv_xauusd_1h")
        roundtrip_list = convert_to_list_of_dicts(df, "tv_xauusd_1h")
        stats = get_data_statistics("tv_xauusd_1h")
        generator = SampleDataGenerator()
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при работе с sample данными: {exc}")
        traceback.print_exc()
        return False

    if not datasets_summary or not dataset_names:
        print("  ❌ Список датасетов пустой")
        return False

    if info.get("symbol") != "XAUUSD":
        print(f"  ❌ Неожиданный символ в информации о датасете: {info}")
        return False

    if df.empty or df_converted.empty:
        print("  ❌ Полученные DataFrame пустые")
        return False

    if len(data_list) != len(roundtrip_list):
        print("  ❌ Конвертация списков словарей дала разный размер")
        return False

    if stats.get("total_records", 0) <= 0:
        print(f"  ❌ Статистика датасета некорректна: {stats}")
        return False

    if not isinstance(generator, object):  # pragma: no branch - гарантия инициализации
        print("  ❌ Генератор sample данных не создан")
        return False

    print(
        "  ℹ️ Датасетов доступно:",
        f"{len(dataset_names)}, записей в tv_xauusd_1h: {stats.get('total_records')}",
    )
    return True


def test_logging_snippet() -> bool:
    print("\n🪵 Тест: Настройка логирования из раздела")

    try:
        logging.getLogger("bquant.data").setLevel(logging.WARNING)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при настройке логирования: {exc}")
        traceback.print_exc()
        return False

    current_level = logging.getLogger("bquant.data").level
    print(f"  ℹ️ Текущий уровень логгера bquant.data: {current_level}")
    return current_level == logging.WARNING


def test_cross_references() -> bool:
    print("\n🔗 Тест: Проверка ссылок раздела")

    targets: Iterable[Tuple[str, Path]] = [
        ("core logging", PROJECT_ROOT / "docs" / "api" / "core" / "logging.md"),
        ("core readme", PROJECT_ROOT / "docs" / "api" / "core" / "README.md"),
        ("indicators", PROJECT_ROOT / "docs" / "api" / "indicators" / "README.md"),
        ("analysis", PROJECT_ROOT / "docs" / "api" / "analysis" / "README.md"),
        ("visualization", PROJECT_ROOT / "docs" / "api" / "visualization" / "README.md"),
        ("loader", PROJECT_ROOT / "docs" / "api" / "data" / "loader.md"),
        ("processor", PROJECT_ROOT / "docs" / "api" / "data" / "processor.md"),
        ("validator", PROJECT_ROOT / "docs" / "api" / "data" / "validator.md"),
        ("schemas", PROJECT_ROOT / "docs" / "api" / "data" / "schemas.md"),
        ("samples", PROJECT_ROOT / "docs" / "api" / "data" / "samples.md"),
    ]

    missing: List[str] = []
    for name, path in targets:
        if not path.exists():
            missing.append(name)

    if missing:
        print(f"  ❌ Отсутствуют файлы: {missing}")
        return False

    print("  ℹ️ Все связанные документы присутствуют")
    return True


def main() -> int:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

    tests: Tuple[Tuple[str, Callable[[], bool]], ...] = (
        ("Примеры загрузки", test_loader_examples),
        ("Обработка данных", test_processor_examples),
        ("Валидация данных", test_validator_examples),
        ("Sample данные", test_samples_examples),
        ("Логирование", test_logging_snippet),
        ("Cross-reference", test_cross_references),
    )

    results = []
    all_ok = True
    for title, func in tests:
        success = func()
        _print_result(title, success)
        results.append((title, success))
        all_ok &= success

    print("\nИтоговый отчёт:")
    for title, success in results:
        status = "OK" if success else "FAIL"
        print(f"  - {title}: {status}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
