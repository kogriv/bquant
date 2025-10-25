#!/usr/bin/env python3
"""Валидация docs/api/core/README.md"""

import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pandas as pd

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def test_config_example() -> bool:
    """Проверяем пример с конфигурацией."""
    print("📋 Тест: Конфигурация")
    try:
        from bquant.core.config import get_data_path, validate_timeframe
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Импорт не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        timeframe = validate_timeframe("1h")
        path = Path(get_data_path("XAUUSD", "1h", data_source="tradingview", quote_provider="oanda"))
        print(f"  ✅ Таймфрейм: {timeframe}")
        print(f"  ✅ Путь: {path}")
        return timeframe == "1h" and path.suffix == ".csv"
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка выполнения примера: {exc}")
        traceback.print_exc()
        return False


def test_logging_example() -> bool:
    """Воспроизводим пример настройки логирования."""
    print("\n📋 Тест: Логирование")
    try:
        from bquant.core.logging_config import setup_logging, get_logger
    except Exception as exc:
        print(f"  ❌ Импорт логирования: {exc}")
        traceback.print_exc()
        return False

    try:
        setup_logging(level="INFO", log_file="bquant.log")
        logger = get_logger(__name__)
        logger.info("Starting analysis...")
        logger.debug("Processing data...")
        logger.warning("Data validation failed")
        logger.error("Analysis failed")
        print("  ✅ Логирование выполнено")
        return True
    except Exception as exc:
        print(f"  ❌ Ошибка логирования: {exc}")
        traceback.print_exc()
        return False


def test_performance_example() -> bool:
    """Проверяем пример с мониторингом производительности."""
    print("\n📋 Тест: Производительность")
    try:
        from bquant.core.performance import (
            get_performance_monitor,
            performance_context,
            performance_monitor,
        )
    except Exception as exc:
        print(f"  ❌ Импорт performance: {exc}")
        traceback.print_exc()
        return False

    try:
        @performance_monitor()
        def slow_function():
            time.sleep(0.05)
            return "result"

        def process_large_dataset():
            return sum(range(100))

        result = slow_function()
        with performance_context("data_processing"):
            process_large_dataset()

        stats = get_performance_monitor().get_stats()
        print(f"  ✅ Результат slow_function: {result}")
        print(f"  ✅ Количество функций в статистике: {len(stats)}")
        return result == "result" and any("slow_function" in key for key in stats.keys())
    except Exception as exc:
        print(f"  ❌ Ошибка примера производительности: {exc}")
        traceback.print_exc()
        return False


def test_exceptions_example() -> bool:
    """Проверяем обработку исключений."""
    print("\n📋 Тест: Исключения")
    try:
        from bquant.core.exceptions import AnalysisError, BQuantError, DataError
        from bquant.core.logging_config import get_logger
    except Exception as exc:
        print(f"  ❌ Импорты исключений: {exc}")
        traceback.print_exc()
        return False

    logger = get_logger(__name__)

    def load_data(_: str):
        raise DataError("invalid file")

    handled = SimpleNamespace(data=False, base=False)

    try:
        load_data("invalid_file.csv")
    except DataError as exc:
        logger.error(f"Data error: {exc}")
        handled.data = True
    except BQuantError as exc:
        logger.error(f"BQuant error: {exc}")
        handled.base = True
    except AnalysisError:
        logger.error("Analysis error")

    print(f"  ✅ Обработчики: data={handled.data}, base={handled.base}")
    return handled.data and not handled.base


def test_utils_example() -> bool:
    """Проверяем утилиты."""
    print("\n📋 Тест: Утилиты")
    try:
        from bquant.core.utils import calculate_returns, validate_ohlcv_columns
    except Exception as exc:
        print(f"  ❌ Импорт утилит: {exc}")
        traceback.print_exc()
        return False

    try:
        df = pd.DataFrame(
            {
                "open": [1, 2, 3],
                "high": [2, 3, 4],
                "low": [0.5, 1.5, 2.5],
                "close": [1.2, 2.2, 3.2],
                "volume": [100, 110, 120],
            }
        )
        check = validate_ohlcv_columns(df)
        returns = calculate_returns(df["close"], method="log")
        print(f"  ✅ Валидация: {check['is_valid']}, сообщения: {check['messages']}")
        print(f"  ✅ Доходности: {returns.dropna().tolist()}")
        return check["is_valid"] and len(returns.dropna()) == 2
    except Exception as exc:
        print(f"  ❌ Ошибка утилит: {exc}")
        traceback.print_exc()
        return False


def test_notebook_example() -> bool:
    """Воспроизводим пример Notebook-style API."""
    print("\n📋 Тест: Notebook-style скрипт")
    try:
        from unittest import mock

        from bquant.core.nb import NotebookSimulator
    except Exception as exc:
        print(f"  ❌ Импорт NotebookSimulator: {exc}")
        traceback.print_exc()
        return False

    try:
        runner = NotebookSimulator("Data Analysis Script", auto_setup=False)
        runner.setup_logging("analysis.log")
        runner.step("Loading Data")
        with mock.patch("builtins.input", return_value=""):
            runner.wait()
        runner.success("Data loaded successfully")
        runner.step("Processing Data")
        with mock.patch("builtins.input", return_value=""):
            runner.wait()
        runner.success("Processing completed")
        try:
            runner.finish()
        except SystemExit as exc:
            print(f"  ✅ Finish вызвал SystemExit({exc.code})")
            return exc.code == 0
        return False
    except Exception as exc:
        print(f"  ❌ Ошибка NotebookSimulator: {exc}")
        traceback.print_exc()
        return False


def test_cross_references() -> bool:
    """Убеждаемся, что все ссылки из раздела существуют."""
    print("\n📋 Тест: Cross-references")
    references: List[Path] = [
        Path("docs/api/core/config.md"),
        Path("docs/api/core/exceptions.md"),
        Path("docs/api/core/logging.md"),
        Path("docs/api/core/performance.md"),
        Path("docs/api/core/utils.md"),
        Path("docs/api/core/nb.md"),
        Path("docs/api/data/README.md"),
        Path("docs/api/indicators/README.md"),
        Path("docs/api/analysis/README.md"),
        Path("docs/api/visualization/README.md"),
    ]

    missing = [ref for ref in references if not ref.exists()]
    if missing:
        for ref in missing:
            print(f"  ❌ Нет файла: {ref}")
        return False

    for ref in references:
        print(f"  ✅ {ref}")
    return True


def test_language() -> bool:
    """Проверяем, что текст раздела остается русским."""
    print("\n📋 Тест: Язык")
    try:
        content = Path("docs/api/core/README.md").read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  ❌ Не удалось прочитать документ: {exc}")
        traceback.print_exc()
        return False

    markers = ["модули", "конфигурация", "исключения", "логирование", "производительность", "утилиты"]
    found = sum(1 for marker in markers if marker in content.lower())
    print(f"  ✅ Найдено русских маркеров: {found}/{len(markers)}")
    code_blocks = content.count("```python")
    print(f"  ✅ Python-блоков: {code_blocks}")
    return found >= len(markers) - 1 and code_blocks >= 5


def main() -> bool:
    print("🔍 Валидация docs/api/core/README.md")
    print("=" * 60)

    tests = [
        ("Конфигурация", test_config_example),
        ("Логирование", test_logging_example),
        ("Производительность", test_performance_example),
        ("Исключения", test_exceptions_example),
        ("Утилиты", test_utils_example),
        ("Notebook", test_notebook_example),
        ("Cross-references", test_cross_references),
        ("Язык", test_language),
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
