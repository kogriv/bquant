#!/usr/bin/env python3
"""Валидация раздела docs/user_guide/quick_start.md."""

from __future__ import annotations

import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

QUICK_START_PATH = PROJECT_ROOT / "docs/user_guide/quick_start.md"


def _extract_links(markdown_text: str) -> List[str]:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    return pattern.findall(markdown_text)


def _extract_python_blocks(markdown_text: str) -> List[str]:
    pattern = re.compile(r"```python\n(.*?)```", re.DOTALL)
    return [textwrap.dedent(block).strip() for block in pattern.findall(markdown_text)]


def _prepare_pandas_ta(minimal_functions: Iterable[str] = ("rsi",)) -> None:
    """Ограничиваем регистрацию pandas-ta базовым набором индикаторов."""

    try:
        from bquant.indicators.library import pandas_ta as pandas_ta_loader  # type: ignore
    except Exception:  # noqa: BLE001
        return

    try:
        import pandas_ta as ta  # type: ignore
    except Exception:  # noqa: BLE001
        return

    loader = pandas_ta_loader.PandasTALoader
    selected: Dict[str, object] = {}
    for name in minimal_functions:
        func = getattr(ta, name, None)
        if func is not None:
            selected[name] = func

    if not selected:
        return

    loader._function_cache = selected  # type: ignore[attr-defined]
    loader._available_indicators = sorted(selected.keys())  # type: ignore[attr-defined]
    loader._indicators_registered = False  # type: ignore[attr-defined]


def _ensure_stub_zigzag_registered() -> None:
    """Регистрируем упрощенный zigzag, если он отсутствует."""

    try:
        from bquant.indicators.base import IndicatorFactory, LibraryIndicator  # type: ignore
    except Exception:  # noqa: BLE001
        return

    registry = getattr(IndicatorFactory, "_registry", {})
    if "pandas_ta_zigzag" in registry:
        return

    def _zigzag_stub(df: pd.DataFrame, **kwargs: object) -> pd.DataFrame:
        if isinstance(df, pd.DataFrame):
            series = df.get("close")
            if series is None:
                numeric = df.select_dtypes(include=["number"])
                series = numeric.iloc[:, 0] if not numeric.empty else pd.Series(dtype=float)
        else:
            series = pd.Series(df)

        return pd.DataFrame({"zigzag": series.to_numpy(copy=True)})

    class _StubZigZagIndicator(LibraryIndicator):  # type: ignore[misc]
        def __init__(self, **params: object) -> None:
            super().__init__("zigzag", _zigzag_stub, parameters=params)

    IndicatorFactory.register_indicator("pandas_ta_zigzag", _StubZigZagIndicator)
    IndicatorFactory.register_library_function("pandas_ta_zigzag", _zigzag_stub)


def test_relative_links() -> bool:
    print("🔗 Проверяем ссылки quick_start.md")
    content = QUICK_START_PATH.read_text(encoding="utf-8")
    links = _extract_links(content)

    relative_links = [link for link in links if not link.startswith("http") and not link.startswith("mailto:")]
    all_exist = True
    for link in relative_links:
        target = link.split("#", 1)[0]
        if not target:
            continue
        target_path = (QUICK_START_PATH.parent / target).resolve()
        exists = target_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {link} → {target_path}")
        if not exists:
            all_exist = False

    return all_exist


def test_language_presence() -> bool:
    print("🗣️ Проверяем наличие русскоязычных формулировок")
    content = QUICK_START_PATH.read_text(encoding="utf-8")
    markers = ["быстрый старт", "анализ", "зоны", "визуализация", "гид"]
    found = sum(1 for marker in markers if marker in content.lower())
    print(f"  Найдено {found} маркеров из {len(markers)}")
    return found >= 3


def _execute_python_examples(code_blocks: List[str]) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Выполняем python-блоки и возвращаем промежуточные результаты."""

    import plotly.io as pio  # noqa: WPS433
    from plotly.graph_objs import Figure  # noqa: WPS433

    pio.renderers.default = "json"

    original_show = Figure.show

    def _patched_show(self, *args, **kwargs):  # noqa: ANN001, D401
        """Безопасный вывод графика в тестовой среде."""

        print("  📈 Figure.show() перехвачен (renderer=json)")
        return {"rendered": True}

    Figure.show = _patched_show

    globals_dict: Dict[str, object] = {"__name__": "__main__"}
    stored: Dict[str, object] = {}

    try:
        for idx, block in enumerate(code_blocks, 1):
            print(f"  ▶️ Выполняем блок {idx}")
            exec(block, globals_dict)  # noqa: S102

            if idx == 4 and "result" in globals_dict:
                stored["rsi_pipeline_result"] = globals_dict["result"]
            if idx == 7 and "rsi_result" in globals_dict:
                stored["rsi_indicator_df"] = globals_dict["rsi_result"].data
            if idx == 9 and "result" in globals_dict:
                stored["macd_pipeline_result"] = globals_dict["result"]

    finally:
        Figure.show = original_show

    return stored, globals_dict


def test_python_examples() -> bool:
    print("🧪 Выполняем python-примеры quick_start.md")
    if not QUICK_START_PATH.exists():
        print("  ❌ Файл quick_start.md не найден")
        return False

    content = QUICK_START_PATH.read_text(encoding="utf-8")
    code_blocks = _extract_python_blocks(content)

    expected_blocks = 11
    print(f"  Найдено {len(code_blocks)} python-блоков")
    if len(code_blocks) < expected_blocks:
        print(f"  ❌ Ожидалось не менее {expected_blocks} блоков кода")
        return False

    _prepare_pandas_ta()
    _ensure_stub_zigzag_registered()

    stored, globals_dict = _execute_python_examples(code_blocks)

    rsi_pipeline = stored.get("rsi_pipeline_result")
    macd_pipeline = stored.get("macd_pipeline_result")
    rsi_indicator_df = stored.get("rsi_indicator_df")

    success = True

    if rsi_pipeline is None:
        print("  ❌ После блока 4 не найден результат RSI pipeline")
        success = False
    else:
        zones = getattr(rsi_pipeline, "zones", [])
        print(f"  ✅ RSI pipeline выполнен (зон: {len(zones)})")

    if not isinstance(rsi_indicator_df, pd.DataFrame):
        print("  ❌ Не удалось получить DataFrame индикатора RSI")
        success = False
    else:
        has_column = "RSI_14" in rsi_indicator_df.columns
        print(f"  {'✅' if has_column else '❌'} Колонка RSI_14 присутствует в расчётах")
        success = success and has_column

    if macd_pipeline is None:
        print("  ❌ После блока 9 не найден результат MACD pipeline")
        success = False
    else:
        macd_zones = len(getattr(macd_pipeline, "zones", []))
        print(f"  ✅ MACD pipeline выполнен (зон: {macd_zones})")
        if macd_zones == 0:
            success = False
            print("  ❌ Ожидалось наличие найденных зон для MACD")

    # Проверяем, что troubleshooting-блоки выполнялись в той же среде
    version_again = globals_dict.get("bquant")
    if version_again is None:
        print("  ⚠️ Итоговая проверка версии BQuant не выполнена (не критично)")

    return success


def main() -> bool:
    print("🔍 Валидация docs/user_guide/quick_start.md")
    print("=" * 60)

    tests = [
        ("Ссылки quick_start", test_relative_links),
        ("Русскоязычный текст", test_language_presence),
        ("Python-примеры", test_python_examples),
    ]

    results = []
    for name, func in tests:
        print(f"\n📋 Тест: {name}")
        try:
            result = func()
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ Критическая ошибка: {exc}")
            result = False
        results.append((name, result))

    print("\n" + "=" * 60)
    print("📊 РЕЗЮМЕ ТЕСТОВ:")
    passed = 0
    for name, status in results:
        flag = "✅" if status else "❌"
        print(f"  {flag} {name}")
        if status:
            passed += 1

    total = len(results)
    print(f"\n🎯 Итог: {passed}/{total} тестов пройдено")
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
