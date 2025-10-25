"""Валидация документации docs/api/data/schemas.md."""

from __future__ import annotations

import sys
import traceback
from dataclasses import asdict
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def test_imports_and_models() -> bool:
    print("\n📦 Тест: Импорты и модели")

    try:
        from bquant.data import schemas
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта модуля schemas: {exc}")
        traceback.print_exc()
        return False

    try:
        record = schemas.OHLCVRecord(
            timestamp=pd.Timestamp("2024-01-01T00:00:00Z").to_pydatetime(),
            open=1900.0,
            high=1905.0,
            low=1898.0,
            close=1902.0,
            volume=1_000.0,
        )
        if not record.validate():
            print("  ❌ Валидация OHLCVRecord вернула False")
            return False

        config = schemas.DataSourceConfig(
            name="demo",
            file_pattern="*.csv",
            timeframe_mapping={"1h": "60"},
            quote_providers=["tradingview"],
        )
        config_payload = asdict(config)
        if config_payload["timeframe_mapping"].get("1h") != "60":
            print("  ❌ DataSourceConfig не сохранил маппинг таймфрейма")
            return False

        validation = schemas.ValidationResult(
            is_valid=True,
            issues=[],
            warnings=[],
            stats={"rows": 0},
            recommendations=["Schema validation is not yet implemented"],
        )
        if not validation.is_valid or "rows" not in validation.stats:
            print("  ❌ ValidationResult не соответствует документации")
            return False

        base_schema = schemas.DataSchema("demo")
        result = base_schema.validate_dataframe(pd.DataFrame())
        if not isinstance(result, schemas.ValidationResult):
            print("  ❌ validate_dataframe должен возвращать ValidationResult")
            return False
    except Exception as exc:  # pragma: no cover - диагностика
        print(f"  ❌ Неожиданное исключение: {exc}")
        traceback.print_exc()
        return False

    return True


def test_validate_with_schema_example() -> bool:
    print("\n🧪 Тест: Пример validate_with_schema")

    try:
        from bquant.data.schemas import validate_with_schema
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта validate_with_schema: {exc}")
        traceback.print_exc()
        return False

    df = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [2.0, 3.0],
            "low": [1.0, 2.0],
            "close": [1.5, 2.5],
        }
    )

    try:
        result = validate_with_schema(df, "ohlcv")
    except Exception as exc:  # pragma: no cover - диагностика
        print(f"  ❌ Пример validate_with_schema завершился исключением: {exc}")
        traceback.print_exc()
        return False

    if not result.is_valid:
        print("  ❌ validate_with_schema должен возвращать is_valid=True для корректного df")
        return False

    expected_stats = {"rows": 2, "columns": 4}
    if result.stats != expected_stats:
        print(f"  ❌ Ожидались статистики {expected_stats}, получено {result.stats}")
        return False

    if "Schema validation is not yet implemented" not in result.recommendations:
        print("  ❌ Примечание о заготовке схем должно присутствовать в recommendations")
        return False

    return True


def test_available_schemas_listing() -> bool:
    print("\n📚 Тест: Предопределённые схемы")

    try:
        from bquant.data import schemas
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Ошибка импорта модуля schemas: {exc}")
        traceback.print_exc()
        return False

    expected_keys = {"ohlcv", "macd", "rsi"}
    available = getattr(schemas, "AVAILABLE_SCHEMAS", {})

    if set(available.keys()) != expected_keys:
        print(f"  ❌ AVAILABLE_SCHEMAS должен содержать {expected_keys}, получено {set(available.keys())}")
        return False

    if not isinstance(available["ohlcv"], schemas.OHLCVSchema):
        print("  ❌ AVAILABLE_SCHEMAS['ohlcv'] должен быть экземпляром OHLCVSchema")
        return False

    macd_schema = available["macd"]
    rsi_schema = available["rsi"]
    if macd_schema.schema_type != "indicators" or rsi_schema.schema_type != "indicators":
        print("  ❌ Индикаторные схемы должны иметь тип 'indicators'")
        return False

    if schemas.get_schema("bollinger_bands") is not None:
        print("  ❌ get_schema не должен возвращать схему для неизвестного имени")
        return False

    ohlcv_result = schemas.validate_with_schema(
        pd.DataFrame(
            {
                "open": [10.0],
                "high": [10.5],
                "low": [9.8],
                "close": [10.2],
            }
        ),
        "ohlcv",
    )
    if not ohlcv_result.is_valid:
        print("  ❌ Повторная проверка validate_with_schema должна быть успешной")
        return False

    return True


def main() -> int:
    tests = (
        ("Импорты и модели", test_imports_and_models),
        ("Пример validate_with_schema", test_validate_with_schema_example),
        ("Предопределённые схемы", test_available_schemas_listing),
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
