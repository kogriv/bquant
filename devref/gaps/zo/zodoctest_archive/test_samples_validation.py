"""Валидация примеров из docs/api/data/samples.md."""

import io
import os
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from typing import List

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("PLOTLY_RENDERER", "json")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _print_section(title: str) -> None:
    print(f"\n📌 {title}")


def _print_status(message: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"  {status} {message}")


def validate_quick_start_examples() -> bool:
    _print_section("Быстрый старт")

    try:
        from bquant.data.samples import get_sample_data, list_datasets
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Импорт API не удался: {exc}", False)
        traceback.print_exc()
        return False

    try:
        datasets = list_datasets()
        if not datasets:
            _print_status("Список датасетов пуст", False)
            return False

        titles = [entry["title"] for entry in datasets]
        _print_status(f"Найдено датасетов: {len(datasets)} ({', '.join(titles)})", True)

        df = get_sample_data("tv_xauusd_1h")
        if df.empty:
            _print_status("DataFrame с sample данными пуст", False)
            return False

        data_dict = get_sample_data("tv_xauusd_1h", format="dict")
        if not isinstance(data_dict, list) or not data_dict:
            _print_status("Список словарей пуст", False)
            return False

        preview_columns = list(data_dict[0].keys())
        _print_status(
            f"DataFrame: {df.shape[0]} строк, dict: {len(data_dict)} записей; колонки: {preview_columns[:4]}…",
            True,
        )
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Ошибка выполнения примеров: {exc}", False)
        traceback.print_exc()
        return False

    return True


def validate_api_functions() -> bool:
    _print_section("API функции")

    try:
        from bquant.data.samples import (
            get_dataset_info,
            get_sample_data,
            list_datasets,
            validate_dataset,
        )
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Импорт API функций не удался: {exc}", False)
        traceback.print_exc()
        return False

    try:
        dataset_info = get_dataset_info("tv_xauusd_1h")
        _print_status(
            f"Информация о датасете: timeframe={dataset_info['timeframe']}, rows={dataset_info['rows']}",
            True,
        )

        df = get_sample_data("mt_xauusd_m15", format="dataframe")
        _print_status(f"mt_xauusd_m15 shape={df.shape}", not df.empty)

        datasets = list_datasets()
        _print_status("list_datasets() вернул записи", bool(datasets))

        validation = validate_dataset("tv_xauusd_1h")
        is_valid = validation.get("is_valid", False)
        errors = validation.get("errors", [])
        _print_status(f"validate_dataset(): is_valid={is_valid}, errors={len(errors)}", is_valid)
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Ошибка выполнения API функций: {exc}", False)
        traceback.print_exc()
        return False

    return True


def validate_additional_functions() -> bool:
    _print_section("Дополнительные функции")

    try:
        from bquant.data.samples import (
            compare_sample_datasets,
            find_datasets,
            get_sample_preview,
            list_dataset_names,
            print_sample_data_status,
            validate_dataset,
        )
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Импорт дополнительных функций не удался: {exc}", False)
        traceback.print_exc()
        return False

    try:
        preview = get_sample_preview("tv_xauusd_1h", 3)
        _print_status(f"Предпросмотр содержит {len(preview)} записи", len(preview) == 3)

        by_symbol = find_datasets(symbol="XAUUSD")
        by_timeframe = find_datasets(timeframe="1h")
        by_source = find_datasets(source="TradingView")
        _print_status(
            f"find_datasets(): symbol={by_symbol}, timeframe={by_timeframe}, source={by_source}",
            all([by_symbol, by_timeframe, by_source]),
        )

        comparison = compare_sample_datasets("tv_xauusd_1h", "mt_xauusd_m15")
        common = comparison.get("common_columns", [])
        _print_status(f"Сравнение датасетов: общих колонок {len(common)}", bool(common))

        names = list_dataset_names()
        status_buffer = io.StringIO()
        with redirect_stdout(status_buffer):
            print_sample_data_status()
        status_output = status_buffer.getvalue()
        _print_status(
            "print_sample_data_status() возвращает информацию",
            "TradingView XAUUSD 1H" in status_output and set(names) >= {"tv_xauusd_1h", "mt_xauusd_m15"},
        )

        # Повторная валидация для блока "Тестирование"
        all_valid = True
        for dataset_name in names:
            result = validate_dataset(dataset_name)
            if not result.get("is_valid", False):
                all_valid = False
        _print_status("Валидация всех датасетов прошла", all_valid)
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Ошибка выполнения дополнительных функций: {exc}", False)
        traceback.print_exc()
        return False

    return True


def _prepare_zone_features(result) -> List[dict]:
    from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer

    analyzer = ZoneFeaturesAnalyzer()
    features = analyzer.extract_all_zones_features(result.zones)
    return [feature.to_dict() for feature in features]


def validate_integrations() -> bool:
    _print_section("Интеграция с модулями")

    try:
        from bquant.data.samples import get_sample_data
        from bquant.indicators.macd import MACDZoneAnalyzer
        from bquant.analysis.statistical import run_all_hypothesis_tests
        from bquant.visualization import FinancialCharts
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Импорт зависимостей не удался: {exc}", False)
        traceback.print_exc()
        return False

    try:
        data = get_sample_data("tv_xauusd_1h")

        macd_analyzer = MACDZoneAnalyzer()
        macd_result = macd_analyzer.analyze_complete(data)
        _print_status(f"MACDZoneAnalyzer: найдено зон {len(macd_result.zones)}", len(macd_result.zones) > 0)

        charts = FinancialCharts()
        figure = charts.create_candlestick_chart(data, title="Sample XAUUSD Data")
        figure.show()
        _print_status("FinancialCharts: candlestick график создан", figure is not None)

        zones_features = _prepare_zone_features(macd_result)
        tests = run_all_hypothesis_tests(zones_features)
        summary = tests.get("summary", {})
        total_tests = summary.get("total_tests", 0)
        _print_status(f"Статистические тесты: total={total_tests}", total_tests > 0)
    except Exception as exc:  # pragma: no cover - диагностический вывод
        _print_status(f"Ошибка интеграционных примеров: {exc}", False)
        traceback.print_exc()
        return False

    return True


def validate_update_commands() -> bool:
    _print_section("Скрипты обновления")

    scripts = [
        PROJECT_ROOT / "scripts" / "data" / "extract_samples.py",
    ]
    missing = [str(path) for path in scripts if not path.exists()]
    if missing:
        _print_status(f"Скрипт(ы) не найдены: {missing}", False)
        return False

    _print_status("Скрипт обновления sample данных существует", True)
    return True


def main() -> None:
    tests = [
        validate_quick_start_examples,
        validate_api_functions,
        validate_additional_functions,
        validate_integrations,
        validate_update_commands,
    ]

    results = [test() for test in tests]
    success_count = sum(results)
    print(f"\n✅ Успешно: {success_count}/{len(tests)}")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
