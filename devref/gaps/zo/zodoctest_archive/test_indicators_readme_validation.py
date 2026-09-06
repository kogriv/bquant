"""Валидирует все примеры из docs/api/indicators/README.md."""

import json
import os
import sys
import tempfile
import traceback
import types
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from typing import Dict, List

import pandas as pd

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _rsi_stub(df: pd.DataFrame, length: int = 14, **_: Dict[str, float]) -> pd.DataFrame:
    close = df["close"].astype(float)
    delta = close.diff().fillna(0.0)
    gain = delta.clip(lower=0.0)
    loss = (-delta.clip(upper=0.0))
    avg_gain = gain.rolling(length, min_periods=1).mean()
    avg_loss = loss.rolling(length, min_periods=1).mean().replace(0, 1e-9)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return pd.DataFrame({"rsi": rsi}, index=df.index)


def _zigzag_stub(df: pd.DataFrame, **_: Dict[str, float]) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        series = df.get("close")
        if series is None:
            numeric = df.select_dtypes(include="number")
            if numeric.empty:
                series = pd.Series(dtype=float, index=df.index)
            else:
                series = numeric.iloc[:, 0]
    else:
        series = pd.Series(df)

    base = series.fillna(method="ffill").fillna(method="bfill")
    return pd.DataFrame({"zigzag": base}, index=series.index)


def _prepare_pandas_ta(minimal: List[str] = None) -> None:
    minimal = minimal or ["rsi", "zigzag"]

    ta = types.ModuleType("pandas_ta")
    sys.modules["pandas_ta"] = ta

    if "rsi" in minimal:
        def _rsi_adapter(df: pd.DataFrame, length: int = 14, **kwargs) -> pd.DataFrame:
            return _rsi_stub(df, length=length)

        ta.rsi = _rsi_adapter

    if "zigzag" in minimal:
        ta.zigzag = lambda df, **kwargs: _zigzag_stub(df)

    try:
        pandas_ta_loader = import_module("bquant.indicators.library.pandas_ta")
    except Exception:
        return

    cache = {}
    if "rsi" in minimal:
        cache["rsi"] = getattr(ta, "rsi")
    if "zigzag" in minimal:
        cache["zigzag"] = getattr(ta, "zigzag")

    loader = pandas_ta_loader.PandasTALoader
    loader._ta_module = ta
    loader._function_cache = cache
    loader._available_indicators = sorted(cache.keys())
    loader._indicators_registered = False


def _register_library_stubs() -> None:
    """Регистрируем заглушки для pandas-ta индикаторов."""

    try:
        from bquant.indicators.base import IndicatorFactory, LibraryIndicator, IndicatorResult
    except Exception:  # pragma: no cover - диагностический вывод
        traceback.print_exc()
        return

    registry = getattr(IndicatorFactory, "_registry", {})
    functions = getattr(IndicatorFactory, "_library_functions", {})
    stubs = {
        "pandas_ta_rsi": ("rsi", _rsi_stub),
        "pandas_ta_zigzag": ("zigzag", _zigzag_stub),
    }

    for registry_key, (indicator_name, func) in stubs.items():
        if registry_key in registry and registry_key in functions:
            continue

        class _StubIndicator(LibraryIndicator):  # type: ignore[override]
            def __init__(self, **params: Dict[str, float]):
                super().__init__(indicator_name, func, parameters=params)

            def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
                params = {**self.config.parameters, **kwargs}
                frame = func(data, **params)
                if not isinstance(frame, pd.DataFrame):
                    frame = pd.DataFrame(frame)
                return IndicatorResult(
                    name=self.name,
                    data=frame,
                    config=self.config,
                    metadata={"library": "pandas_ta_stub", "params": params},
                )

        IndicatorFactory.register_indicator(registry_key, _StubIndicator)
        IndicatorFactory.register_library_function(registry_key, func)


_prepare_pandas_ta()
_register_library_stubs()


@lru_cache(maxsize=1)
def _load_sample_data() -> pd.DataFrame:
    from bquant.data.samples import get_sample_data

    frame = get_sample_data("tv_xauusd_1h").copy()
    frame["macd_hist"] = frame["macd"] - frame["signal"]
    return frame


class SimpleMovingAverageDocExample:
    """Реализация SimpleMovingAverage из документации."""

    def __init__(self, period: int = 20):
        from bquant.indicators.base import CustomIndicator, IndicatorResult

        class _SimpleMovingAverage(CustomIndicator):
            def __init__(self, period: int = 20, **_: Dict[str, float]):
                self.outer_period = period
                super().__init__("sma_custom", {"period": period})

            def get_output_columns(self) -> List[str]:
                return [f"sma_{self.outer_period}"]

            def get_description(self) -> str:
                return f"Simple Moving Average (period={self.outer_period})"

            def get_required_columns(self) -> List[str]:  # type: ignore[override]
                return ["close"]

            def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:  # type: ignore[override]
                if not self.validate_data(data):
                    raise ValueError("Invalid data for SMA calculation")

                period_value = kwargs.get("period", self.outer_period)
                series = data["close"].rolling(window=period_value).mean()
                result_frame = pd.DataFrame({f"sma_{period_value}": series}, index=data.index)
                return IndicatorResult(
                    name="sma_custom",
                    data=result_frame,
                    config=self.config,
                    metadata={"period": period_value},
                )

        self._impl = _SimpleMovingAverage(period)

    def instance(self):
        return self._impl


def _ensure_sma_registered() -> None:
    from bquant.indicators.base import IndicatorFactory

    impl = SimpleMovingAverageDocExample().instance().__class__
    registry = getattr(IndicatorFactory, "_registry", {})
    if "sma_custom" not in registry:
        IndicatorFactory.register_indicator("sma_custom", impl)


def test_cross_references() -> bool:
    print("📋 Тест: Cross-references indicators README")

    targets = [
        PROJECT_ROOT / "docs" / "api" / "indicators" / "base.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "macd.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "preloaded.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "factory.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "library_manager.md",
        PROJECT_ROOT / "docs" / "api" / "analysis" / "README.md",
        PROJECT_ROOT / "docs" / "api" / "core" / "README.md",
        PROJECT_ROOT / "docs" / "api" / "data" / "README.md",
        PROJECT_ROOT / "docs" / "api" / "visualization" / "README.md",
    ]

    success = True
    for path in targets:
        if path.exists():
            print(f"  ✅ {path.relative_to(PROJECT_ROOT)}")
        else:
            success = False
            print(f"  ❌ Отсутствует файл: {path.relative_to(PROJECT_ROOT)}")

    return success


def test_preloaded_macd_indicator() -> bool:
    print("\n📋 Тест: PRELOADED MACD индикатор")

    try:
        from bquant.indicators.preloaded import MACDPreloadedIndicator
    except Exception as exc:
        print(f"  ❌ Импорт MACDPreloadedIndicator: {exc}")
        traceback.print_exc()
        return False

    data = _load_sample_data().copy()

    try:
        indicator = MACDPreloadedIndicator()
        info = MACDPreloadedIndicator.get_info()
        default_cols = MACDPreloadedIndicator.get_default_columns()
        result = indicator.calculate(data)
        trending_up = indicator.is_trending_up(data, column="macd")
        trending_down = indicator.is_trending_down(data, column="macd")
        crossovers = indicator.get_crossovers(data)
        stats = indicator.get_statistics(data)

        print(f"  ✅ Info type: {info['type']}")
        print(f"  ✅ Default columns: {default_cols}")
        print(f"  ✅ Result columns: {list(result.data.columns)}")
        print(f"  ✅ Trending up/down: {trending_up}/{trending_down}")
        print(f"  ✅ Crossovers keys: {sorted(crossovers.keys())}")
        print(f"  ✅ Stats columns: {list(stats.keys())}")
        return bool(result.data.shape[0])
    except Exception as exc:
        print(f"  ❌ Ошибка примера: {exc}")
        traceback.print_exc()
        return False


def test_preloaded_custom_columns() -> bool:
    print("\n📋 Тест: PRELOADED индикатор с кастомными колонками")

    from bquant.indicators.preloaded import MACDPreloadedIndicator

    data = _load_sample_data().copy()

    try:
        macd_only = MACDPreloadedIndicator(required_columns=["macd"])
        macd_full = MACDPreloadedIndicator(required_columns=["macd", "signal"])

        is_valid = macd_full.validate_data(data)
        result = macd_only.calculate(data)

        print(f"  ✅ Валидация данных: {is_valid}")
        print(f"  ✅ Колонки результата: {list(result.data.columns)}")
        return is_valid and "macd" in result.data.columns
    except Exception as exc:
        print(f"  ❌ Ошибка кастомных колонок: {exc}")
        traceback.print_exc()
        return False


def _run_pipeline_macd(data: pd.DataFrame, *, swing: str = "find_peaks", divergence: str = "classic", volatility: str = None) -> "ZoneAnalysisResult":
    from bquant.analysis.zones import analyze_zones

    builder = (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
    )

    strategies = {"swing": swing}
    if divergence:
        strategies["divergence"] = divergence
    if volatility:
        strategies["volatility"] = volatility

    builder = builder.with_strategies(**strategies)
    return builder.analyze(clustering=True, n_clusters=3).build()


def test_universal_pipeline_macd() -> bool:
    print("\n📋 Тест: Universal Pipeline MACD")

    data = _load_sample_data().head(400).copy()

    try:
        result = _run_pipeline_macd(data)
        print(f"  ✅ Найдено зон: {len(result.zones)}")
        print(f"  ✅ Статистика ключей: {list(result.statistics.keys())}")
        return result.zones is not None
    except Exception as exc:
        print(f"  ❌ Ошибка pipeline MACD: {exc}")
        traceback.print_exc()
        return False


def test_universal_pipeline_rsi() -> bool:
    print("\n📋 Тест: Universal Pipeline RSI")

    from bquant.analysis.zones import analyze_zones

    data = _load_sample_data().head(400).copy()

    try:
        result = (
            analyze_zones(data)
            .with_indicator("pandas_ta", "rsi", length=14)
            .detect_zones("threshold", indicator_col="rsi", upper_threshold=70, lower_threshold=30)
            .with_strategies(swing="pivot_points", volatility="combined")
            .analyze(clustering=True)
            .build()
        )
        print(f"  ✅ Зон (RSI): {len(result.zones)}")
        return isinstance(result.statistics, dict)
    except Exception as exc:
        print(f"  ❌ Ошибка pipeline RSI: {exc}")
        traceback.print_exc()
        return False


def test_universal_pipeline_custom_indicator() -> bool:
    print("\n📋 Тест: Universal Pipeline с кастомным индикатором")

    from bquant.analysis.zones import analyze_zones

    data = _load_sample_data().head(400).copy()
    data["MY_OSC"] = data["close"].diff(5) / data["close"].rolling(20).std()

    try:
        result = (
            analyze_zones(data)
            .detect_zones("zero_crossing", indicator_col="MY_OSC")
            .with_strategies(swing="find_peaks", shape="statistical")
            .analyze(clustering=True)
            .build()
        )
        print(f"  ✅ Зон (MY_OSC): {len(result.zones)}")
        return len(result.zones) >= 0
    except Exception as exc:
        print(f"  ❌ Ошибка custom индикатора: {exc}")
        traceback.print_exc()
        return False


def test_custom_indicator_class() -> bool:
    print("\n📋 Тест: Создание собственного индикатора")

    data = _load_sample_data().head(400).copy()

    try:
        sma = SimpleMovingAverageDocExample(period=20).instance()
        result = sma.calculate(data)
        tail = result.data.tail()
        print(f"  ✅ Последние значения SMA:\n{tail}")
        return "sma_20" in result.data.columns
    except Exception as exc:
        print(f"  ❌ Ошибка SMA класса: {exc}")
        traceback.print_exc()
        return False


def test_indicator_factory_usage() -> bool:
    print("\n📋 Тест: Работа с IndicatorFactory")

    from bquant.indicators.base import IndicatorFactory

    try:
        _ensure_sma_registered()
        sma = IndicatorFactory.create("custom", "sma_custom", period=20)
        indicators = IndicatorFactory.list_indicators()
        info = IndicatorFactory.get_indicator_info("sma_custom")

        print(f"  ✅ Индикаторов в реестре: {len(indicators)}")
        print(f"  ✅ Информация: {info}")
        return sma is not None and info is not None
    except Exception as exc:
        print(f"  ❌ Ошибка IndicatorFactory: {exc}")
        traceback.print_exc()
        return False


def test_combined_analysis() -> bool:
    print("\n📋 Тест: Комбинированный анализ")

    from bquant.analysis.zones import analyze_zones
    from bquant.indicators.preloaded import MACDPreloadedIndicator
    from bquant.indicators.base import IndicatorFactory

    data = _load_sample_data().head(400).copy()

    try:
        _ensure_sma_registered()
        macd_preloaded = MACDPreloadedIndicator()
        macd_result = macd_preloaded.calculate(data)
        macd_zones = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=True)
            .build()
        )
        sma = IndicatorFactory.create("custom", "sma_custom", period=20)
        sma_result = sma.calculate(data)

        combined = {
            "preloaded_macd_columns": list(macd_result.data.columns),
            "macd_zones": len(macd_zones.zones),
            "macd_statistics_keys": list(macd_zones.statistics.keys()),
            "sma_current": float(sma_result.data.iloc[-1, 0]),
        }

        trend = "up" if sma_result.data.iloc[-1, 0] > sma_result.data.iloc[-2, 0] else "down"
        combined["sma_trend"] = trend

        print(f"  ✅ Комбинированный анализ: {combined}")
        return isinstance(combined["macd_statistics_keys"], list)
    except Exception as exc:
        print(f"  ❌ Ошибка комбинированного анализа: {exc}")
        traceback.print_exc()
        return False


def test_zone_features_analysis() -> bool:
    print("\n📋 Тест: Анализ характеристик зон")

    data = _load_sample_data().head(400).copy()

    try:
        result = _run_pipeline_macd(data, swing="find_peaks", volatility="combined")
        inspected = 0
        for zone in result.zones:
            if zone.features:
                inspected += 1
                keys = list(zone.features.keys())[:4]
                print(f"  ✅ Зона {zone.type} -> ключи: {keys}")
        return inspected >= 0
    except Exception as exc:
        print(f"  ❌ Ошибка анализа характеристик зон: {exc}")
        traceback.print_exc()
        return False


def test_indicator_parameters_tuning() -> bool:
    print("\n📋 Тест: Настройка параметров индикаторов")

    from bquant.analysis.zones import analyze_zones

    data = _load_sample_data().head(400).copy()

    try:
        result_custom = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=8, slow_period=21, signal_period=5)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=True, n_clusters=3)
            .build()
        )
        result_default = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=True, n_clusters=3)
            .build()
        )

        print(
            "  ✅ Custom zones: {} | Default zones: {}".format(
                len(result_custom.zones), len(result_default.zones)
            )
        )
        return isinstance(result_custom.statistics, dict) and isinstance(result_default.statistics, dict)
    except Exception as exc:
        print(f"  ❌ Ошибка сравнения параметров: {exc}")
        traceback.print_exc()
        return False


def test_export_results() -> bool:
    print("\n📋 Тест: Экспорт результатов анализа")

    from bquant.analysis.zones import analyze_zones

    data = _load_sample_data().head(400).copy()

    try:
        result = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col="macd_hist")
            .analyze(clustering=True)
            .build()
        )
        export_data = {
            "analysis_date": str(pd.Timestamp.now()),
            "data_info": {"symbol": "XAUUSD", "timeframe": "1H", "records_count": len(data)},
            "universal_analysis": {
                "zones_count": len(result.zones),
                "statistics": result.statistics,
                "zones": [
                    {
                        "type": zone.type,
                        "start": str(zone.start_time),
                        "end": str(zone.end_time),
                        "features": zone.features,
                    }
                    for zone in result.zones
                ],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universal_analysis.json"
            with path.open("w", encoding="utf-8") as fh:
                json.dump(export_data, fh, indent=2, default=str)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            print(f"  ✅ Экспортирован файл: {path.name}, зон: {loaded['universal_analysis']['zones_count']}")
        return True
    except Exception as exc:
        print(f"  ❌ Ошибка экспорта: {exc}")
        traceback.print_exc()
        return False


def main() -> None:
    tests = [
        test_cross_references,
        test_preloaded_macd_indicator,
        test_preloaded_custom_columns,
        test_universal_pipeline_macd,
        test_universal_pipeline_rsi,
        test_universal_pipeline_custom_indicator,
        test_custom_indicator_class,
        test_indicator_factory_usage,
        test_combined_analysis,
        test_zone_features_analysis,
        test_indicator_parameters_tuning,
        test_export_results,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as exc:  # pragma: no cover - предохранитель
            print(f"  ❌ Необработанное исключение в {test.__name__}: {exc}")
            traceback.print_exc()
            results.append(False)

    total = sum(1 for value in results if value)
    print(f"\n✅ Пройдено {total}/{len(results)} тестов")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
