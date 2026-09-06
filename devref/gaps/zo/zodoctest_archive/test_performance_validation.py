#!/usr/bin/env python3
"""Валидация документации docs/api/core/performance.md."""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


def test_monitoring_example() -> bool:
    """Воспроизводит сниппет с декоратором @performance_monitor."""

    print("\n📋 Тест: Мониторинг функции")

    try:
        from bquant.core.performance import get_performance_monitor, performance_monitor
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт API производительности не удался: {exc}")
        traceback.print_exc()
        return False

    monitor = get_performance_monitor()
    monitor.clear_stats()

    @performance_monitor()
    def compute() -> None:
        import time as _time

        _time.sleep(0.2)

    try:
        compute()
        stats = monitor.get_stats()
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка во время выполнения примера: {exc}")
        traceback.print_exc()
        return False
    finally:
        monitor.clear_stats()

    if not stats:
        print("  ❌ Монитор не вернул статистику")
        return False

    sample = next(iter(stats.values()))
    duration_ok = sample.get("total_time", 0) >= 0.2
    count_ok = sample.get("call_count") == 1
    print(f"  ℹ️ total_time={sample.get('total_time'):.3f}, call_count={sample.get('call_count')}")
    return duration_ok and count_ok


def test_context_example() -> bool:
    """Воспроизводит сниппет с performance_context."""

    print("\n📋 Тест: Контекст измерений")

    try:
        from bquant.core.performance import get_performance_monitor, performance_context
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт API контекста не удался: {exc}")
        traceback.print_exc()
        return False

    monitor = get_performance_monitor()
    monitor.clear_stats()

    def process() -> None:
        time.sleep(0.1)

    try:
        with performance_context("data_processing"):
            process()
        stats = monitor.get_stats("data_processing")
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка выполнения контекстного примера: {exc}")
        traceback.print_exc()
        return False
    finally:
        monitor.clear_stats()

    if not stats:
        print("  ❌ Статистика для контекста отсутствует")
        return False

    duration_ok = stats.get("total_time", 0) >= 0.1
    count_ok = stats.get("call_count") == 1
    print(f"  ℹ️ total_time={stats.get('total_time'):.3f}, call_count={stats.get('call_count')}")
    return duration_ok and count_ok


def test_optimized_indicators() -> bool:
    """Воспроизводит пример с OptimizedIndicators."""

    print("\n📋 Тест: OptimizedIndicators (NumPy)")

    try:
        from bquant.core.performance import OptimizedIndicators
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт OptimizedIndicators не удался: {exc}")
        traceback.print_exc()
        return False

    rng = np.random.default_rng(42)
    prices = rng.random(1000)

    try:
        sma = OptimizedIndicators.sma(prices, 20)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при вызове SMA: {exc}")
        traceback.print_exc()
        return False

    length_ok = sma.shape == prices.shape
    leading_nans = np.isnan(sma[:19]).all()
    print(f"  ℹ️ Длина массива: {sma.shape[0]}, первые значения NaN: {leading_nans}")
    return length_ok and leading_nans


def test_benchmark_example() -> bool:
    """Воспроизводит сниппет с compare_implementations."""

    print("\n📋 Тест: Бенчмарк реализаций")

    try:
        from bquant.core.performance import compare_implementations
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт compare_implementations не удался: {exc}")
        traceback.print_exc()
        return False

    impls = {
        "py_impl": lambda arr: float(sum(arr) / len(arr)),
        "np_impl": lambda arr: float(arr.mean()),
    }

    arr = np.random.rand(10_000)

    try:
        df = compare_implementations(impls, arr, iterations=20)
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка сравнения реализаций: {exc}")
        traceback.print_exc()
        return False

    if df.empty:
        print("  ❌ Таблица результатов пуста")
        return False

    required_columns = {"implementation", "avg_time", "iterations"}
    missing = required_columns.difference(df.columns)
    print(f"  ℹ️ Колонки: {sorted(df.columns)}")
    return not missing and df["iterations"].ge(1).all()


def test_language() -> bool:
    """Проверяет, что текст раздела остается русскоязычным."""

    print("\n📋 Тест: Язык документа")

    path = Path("docs/api/core/performance.md")
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - диагностика чтения
        print(f"  ❌ Не удалось прочитать {path}: {exc}")
        traceback.print_exc()
        return False

    russian_markers = ["производительность", "монитор", "бенчмар", "контекст"]
    markers_found = sum(1 for marker in russian_markers if marker in content.lower())
    code_blocks = content.count("```python")
    print(f"  ℹ️ Русских маркеров: {markers_found}, python-блоков: {code_blocks}")
    return markers_found >= len(russian_markers) - 1 and code_blocks >= 4


def run_all_tests() -> Iterable[Tuple[str, bool]]:
    yield "Мониторинг функции", test_monitoring_example()
    yield "Контекст измерений", test_context_example()
    yield "OptimizedIndicators", test_optimized_indicators()
    yield "Бенчмарк реализаций", test_benchmark_example()
    yield "Проверка языка", test_language()


def main() -> int:
    print("🔍 Валидация docs/api/core/performance.md")
    print("=" * 60)

    results: Dict[str, bool] = {}
    for title, success in run_all_tests():
        _print_result(title, success)
        results[title] = success

    all_passed = all(results.values())
    print("=" * 60)
    print("Итог: ", "✅ УСПЕХ" if all_passed else "❌ НЕУСПЕХ")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

