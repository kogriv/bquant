#!/usr/bin/env python3
"""Валидация docs/api/core/exceptions.md."""

import os
import sys
import traceback
from pathlib import Path
from typing import List, Tuple

import pandas as pd

# Ускоряем выполнение окружения
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

# Добавляем корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_class_hierarchy() -> bool:
    """Проверяем, что все классы исключений задокументированы и наследуются корректно."""

    print("📋 Тест: Классы исключений")

    try:
        from bquant.core.exceptions import (
            AnalysisError,
            BQuantError,
            ConfigurationError,
            DataError,
            DataLoadingError,
            DataProcessingError,
            DataValidationError,
            FeatureExtractionError,
            FileOperationError,
            IndicatorCalculationError,
            InvalidIndicatorParametersError,
            InvalidTimeframeError,
            MLError,
            ModelTrainingError,
            StatisticalAnalysisError,
            VisualizationError,
            ZoneAnalysisError,
        )
        from bquant.core.exceptions import NotImplementedError as BQuantNotImplementedError
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Импорт классов исключений не удался: {exc}")
        traceback.print_exc()
        return False

    checks: List[Tuple[str, bool]] = [
        ("DataError", issubclass(DataError, BQuantError)),
        ("DataValidationError", issubclass(DataValidationError, DataError)),
        ("DataLoadingError", issubclass(DataLoadingError, DataError)),
        ("DataProcessingError", issubclass(DataProcessingError, DataError)),
        ("ConfigurationError", issubclass(ConfigurationError, BQuantError)),
        ("InvalidTimeframeError", issubclass(InvalidTimeframeError, ConfigurationError)),
        (
            "InvalidIndicatorParametersError",
            issubclass(InvalidIndicatorParametersError, ConfigurationError),
        ),
        ("AnalysisError", issubclass(AnalysisError, BQuantError)),
        ("IndicatorCalculationError", issubclass(IndicatorCalculationError, AnalysisError)),
        ("ZoneAnalysisError", issubclass(ZoneAnalysisError, AnalysisError)),
        (
            "StatisticalAnalysisError",
            issubclass(StatisticalAnalysisError, AnalysisError),
        ),
        ("VisualizationError", issubclass(VisualizationError, BQuantError)),
        ("MLError", issubclass(MLError, BQuantError)),
        ("FeatureExtractionError", issubclass(FeatureExtractionError, MLError)),
        ("ModelTrainingError", issubclass(ModelTrainingError, MLError)),
        ("FileOperationError", issubclass(FileOperationError, BQuantError)),
        ("NotImplementedError", issubclass(BQuantNotImplementedError, BQuantError)),
    ]

    success = True
    for name, result in checks:
        print(f"  {'✅' if result else '❌'} Наследование {name}")
        success &= result

    return success


def test_factory_and_context_example() -> bool:
    """Воспроизводим пример из документации с фабрикой и контекстом."""

    print("\n📋 Тест: Фабрика и контекст")

    try:
        from bquant.core.exceptions import (
            BQuantError,
            BQuantErrorContext,
            DataValidationError,
            create_data_validation_error,
        )
        from bquant.core.logging_config import get_logger
    except Exception as exc:
        print(f"  ❌ Импорт фабрики/контекста не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        try:
            raise create_data_validation_error(
                "Неверный формат", expected_type="DataFrame", actual_type="dict"
            )
        except DataValidationError as err:
            message = str(err)
            print(f"  ✅ Исключение фабрики: {message}")
            factory_ok = "Неверный формат" in message and "actual_type=dict" in message

        logger = get_logger(__name__)
        try:
            with BQuantErrorContext("load data", logger=logger):
                1 / 0
        except BQuantError as wrapped:
            print(f"  ✅ Контекст обернул ошибку: {wrapped}")
            context_ok = "Неожиданная ошибка" in str(wrapped)
        else:
            print("  ❌ Контекст не выбросил BQuantError")
            context_ok = False

        return factory_ok and context_ok
    except Exception as exc:
        print(f"  ❌ Ошибка выполнения примера: {exc}")
        traceback.print_exc()
        return False


def test_validators_examples() -> bool:
    """Проверяем валидаторы, перечисленные в документации."""

    print("\n📋 Тест: Валидаторы")

    try:
        from bquant.core.exceptions import (
            DataValidationError,
            InvalidIndicatorParametersError,
            InvalidTimeframeError,
            validate_indicator_parameters,
            validate_ohlcv_data,
            validate_timeframe,
        )
    except Exception as exc:
        print(f"  ❌ Импорт валидаторов не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        supported = ["1h", "4h"]
        validate_timeframe("1h", supported)
        try:
            validate_timeframe("2d", supported)
        except InvalidTimeframeError as err:
            print(f"  ✅ Ошибка таймфрейма: {err}")
            timeframe_ok = "Неподдерживаемый таймфрейм" in str(err)
        else:
            print("  ❌ Не выброшен InvalidTimeframeError")
            timeframe_ok = False

        parameters = {"fast": 12, "slow": 26}
        validate_indicator_parameters("macd", parameters, ["fast", "slow"])
        try:
            validate_indicator_parameters("macd", {"fast": 12}, ["fast", "slow"])
        except InvalidIndicatorParametersError as err:
            print(f"  ✅ Ошибка параметров индикатора: {err}")
            indicator_ok = "Отсутствуют обязательные параметры" in str(err)
        else:
            print("  ❌ Не выброшен InvalidIndicatorParametersError")
            indicator_ok = False

        df = pd.DataFrame(
            {
                "open": [1.0, 2.0],
                "high": [1.5, 2.5],
                "low": [0.5, 1.5],
                "close": [1.2, 2.2],
            }
        )
        validate_ohlcv_data(df)
        try:
            validate_ohlcv_data(pd.DataFrame({"close": [1.0, 2.0]}))
        except DataValidationError as err:
            print(f"  ✅ Ошибка структуры данных: {err}")
            data_ok = "Отсутствуют обязательные колонки" in str(err)
        else:
            print("  ❌ Не выброшен DataValidationError")
            data_ok = False

        return timeframe_ok and indicator_ok and data_ok
    except Exception as exc:
        print(f"  ❌ Ошибка валидации валидаторов: {exc}")
        traceback.print_exc()
        return False


def test_language_and_format() -> bool:
    """Проверяем язык текста и структуру файла."""

    print("\n📋 Тест: Язык и структура документа")

    doc_path = project_root / "docs" / "api" / "core" / "exceptions.md"
    try:
        content = doc_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  ❌ Не удалось прочитать документацию: {exc}")
        traceback.print_exc()
        return False

    cyrillic_markers = ["Исключения", "Фабрики", "Контекст", "Валидаторы"]
    marker_hits = sum(1 for marker in cyrillic_markers if marker.lower() in content.lower())
    code_blocks = content.count("```python")

    print(f"  ✅ Найдено русскоязычных маркеров: {marker_hits}")
    print(f"  ✅ Кодовых блоков в документе: {code_blocks}")

    return marker_hits == len(cyrillic_markers) and code_blocks == 1


def main() -> bool:
    print("🔍 Валидация docs/api/core/exceptions.md")
    print("=" * 60)

    tests = [
        ("Классы", test_class_hierarchy),
        ("Фабрика и контекст", test_factory_and_context_example),
        ("Валидаторы", test_validators_examples),
        ("Язык и структура", test_language_and_format),
    ]

    results = []
    for name, func in tests:
        print(f"\n➡️ {name}")
        ok = func()
        results.append(ok)
        print(f"✔️ {name}: {'успех' if ok else 'ошибка'}")

    total = sum(1 for passed in results if passed)
    print("=" * 60)
    print(f"Итого: {total}/{len(tests)} тестов успешно")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

