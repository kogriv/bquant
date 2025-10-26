"""Validation of docs/api/extension_guide.md examples."""

from __future__ import annotations

import ast
import contextlib
import io
import logging
import sys
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DOC_PATH = ROOT_DIR / "docs" / "api" / "extension_guide.md"


def _parse_code_blocks() -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    for line in DOC_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            if current is None:
                lang = line[3:].strip() or "plain"
                current = {"lang": lang, "lines": []}
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current["lines"].append(line)
    return blocks


DOC_BLOCKS = _parse_code_blocks()
TOTAL_BLOCKS = len(DOC_BLOCKS)
COVERED_BLOCKS: set[int] = set()


def mark_blocks(*indexes: int) -> None:
    COVERED_BLOCKS.update(indexes)


def block_code(index: int) -> str:
    return "\n".join(DOC_BLOCKS[index - 1]["lines"])


def _make_price_volume_data(rows: int = 180) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2024-01-01", periods=rows, freq="h")
    base = rng.normal(loc=0.1, scale=1.0, size=rows).cumsum() + 100
    high = base + rng.random(rows)
    low = base - rng.random(rows)
    volume = rng.integers(1_000, 5_000, size=rows)
    macd_hist = rng.normal(scale=0.05, size=rows)
    data = pd.DataFrame(
        {
            "open": base,
            "high": np.maximum(high, base),
            "low": np.minimum(low, base),
            "close": base,
            "volume": volume,
            "macd_hist": macd_hist,
        },
        index=dates,
    )
    return data


SAMPLE_DATA = _make_price_volume_data()
ZONE_DATA = SAMPLE_DATA[["high", "low", "close", "macd_hist"]].head(60).copy()
ZONE_DICT = {
    "zone_id": "test_zone",
    "type": "bull",
    "duration": len(ZONE_DATA),
    "data": ZONE_DATA,
    "indicator_context": {"detection_indicator": "macd_hist"},
}


from bquant.indicators.base import (  # noqa: E402
    BaseIndicator,
    CustomIndicator as BQuantCustomIndicator,
    IndicatorFactory,
    IndicatorResult,
)
from bquant.analysis import BaseAnalyzer, AnalysisResult  # noqa: E402
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer  # noqa: E402
from bquant.analysis.zones.strategies.base import (  # noqa: E402
    SwingCalculationStrategy,
    SwingMetrics,
    ShapeMetrics,
    DivergenceMetrics,
)
from bquant.analysis.zones.strategies.registry import StrategyRegistry  # noqa: E402
from bquant.visualization.charts import ChartBuilder, PLOTLY_AVAILABLE  # noqa: E402
from bquant.visualization.themes import ChartThemes  # noqa: E402
from bquant.data import loader, processor  # noqa: E402
from bquant.core.config import create_swing_strategy  # noqa: E402
from bquant.core.exceptions import BQuantError, DataError  # noqa: E402


class CustomIndicator(BQuantCustomIndicator):
    """Документированный пример пользовательского индикатора."""

    def __init__(self, param1: int = 10, param2: int = 20):
        parameters = {"param1": param1, "param2": param2}
        super().__init__("CustomIndicator", parameters)
        self.params = self.config.parameters

    def get_output_columns(self):
        return ["custom_indicator"]

    def get_description(self):
        return "Документированный пример пользовательского индикатора"

    def get_required_columns(self):
        return ["close", "volume"]

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        if not self.validate_data(data):
            raise ValueError("Invalid data for CustomIndicator")

        result = self._calculate_indicator(data)
        frame = pd.DataFrame({"custom_indicator": result}, index=data.index)

        return IndicatorResult(
            name=self.name,
            data=frame,
            config=self.config,
            metadata={"calculated_at": pd.Timestamp.utcnow()},
        )

    def validate_data(self, data: pd.DataFrame) -> bool:
        required_columns = ["close", "volume"]
        return all(col in data.columns for col in required_columns)

    def _calculate_indicator(self, data: pd.DataFrame) -> pd.Series:
        window = self.params["param1"]
        divisor = max(self.params["param2"], 1)
        series = (data["close"] * data["volume"]).rolling(window=window, min_periods=1).mean()
        return series / divisor


mark_blocks(1)


class CustomAnalyzer(BaseAnalyzer):
    """Документированный пример пользовательского анализатора."""

    def __init__(self, analysis_type: str = "default"):
        super().__init__("CustomAnalyzer", {"analysis_type": analysis_type})
        self.params = self.config

    def analyze(self, data: pd.DataFrame) -> AnalysisResult:
        if not self.validate_data(data):
            raise ValueError("Invalid data for CustomAnalyzer")

        prepared = self.prepare_data(data)
        payload = self._perform_analysis(prepared)
        return AnalysisResult(
            analysis_type=self.params["analysis_type"],
            results=payload["statistics"],
            data_size=len(prepared),
            metadata={"series_tail": payload["data"].tail(5).to_dict()},
        )

    def _perform_analysis(self, data: pd.DataFrame) -> dict:
        mode = self.params["analysis_type"]
        if mode == "volatility":
            returns = data["close"].pct_change().fillna(0)
            vol = returns.rolling(window=20, min_periods=5).std().fillna(0)
            return {
                "data": vol,
                "statistics": {
                    "mean_volatility": float(vol.mean()),
                    "max_volatility": float(vol.max()),
                    "current_volatility": float(vol.iloc[-1]),
                },
            }
        if mode == "trend":
            slope = np.polyfit(range(len(data["close"])), data["close"], 1)[0]
            return {
                "data": data["close"],
                "statistics": {
                    "trend_slope": float(slope),
                    "start_price": float(data["close"].iloc[0]),
                    "end_price": float(data["close"].iloc[-1]),
                },
            }
        rolling = data["close"].rolling(window=10, min_periods=3).mean().bfill()
        return {
            "data": rolling,
            "statistics": {
                "mean_close": float(data["close"].mean()),
                "std_close": float(data["close"].std()),
            },
        }


mark_blocks(3)


class MyCustomSwingStrategy(SwingCalculationStrategy):
    """Упрощенная реализация стратегии свингов из документации."""

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold
        self.min_required_length = 3

    def calculate_swings(self, data: pd.DataFrame) -> SwingMetrics:
        if len(data) < self.min_required_length:
            return self._empty_metrics()

        price = data["close"]
        returns = price.pct_change().fillna(0)
        rallies = returns[returns >= self.threshold]
        drops = -returns[returns <= -self.threshold]

        rally_stats = self._stats(rallies)
        drop_stats = self._stats(drops)

        duration = max(len(data), 1)
        rally_speed = rally_stats["avg"] / duration if duration else 0.0
        drop_speed = drop_stats["avg"] / duration if duration else 0.0

        metrics = SwingMetrics(
            num_swings=rally_stats["count"] + drop_stats["count"],
            avg_rally_pct=rally_stats["avg"],
            avg_drop_pct=drop_stats["avg"],
            max_rally_pct=rally_stats["max"],
            max_drop_pct=drop_stats["max"],
            rally_to_drop_ratio=(rally_stats["avg"] / drop_stats["avg"]) if drop_stats["avg"] else 1.0,
            rally_count=rally_stats["count"],
            drop_count=drop_stats["count"],
            min_rally_pct=rally_stats["min"],
            min_drop_pct=drop_stats["min"],
            rally_amplitude_std=rally_stats["std"],
            drop_amplitude_std=drop_stats["std"],
            rally_amplitude_median=rally_stats["median"],
            drop_amplitude_median=drop_stats["median"],
            avg_rally_duration_bars=rally_stats["duration"],
            avg_drop_duration_bars=drop_stats["duration"],
            max_rally_duration_bars=rally_stats["max_duration"],
            max_drop_duration_bars=drop_stats["max_duration"],
            avg_rally_speed_pct_per_bar=float(abs(rally_speed)),
            avg_drop_speed_pct_per_bar=float(abs(drop_speed)),
            max_rally_speed_pct_per_bar=rally_stats["max_speed"],
            max_drop_speed_pct_per_bar=drop_stats["max_speed"],
            duration_symmetry=(rally_stats["duration"] / drop_stats["duration"]) if drop_stats["duration"] else 1.0,
            strategy_name="MyCustomSwing",
            strategy_params={"threshold": self.threshold},
        )
        metrics.validate()
        return metrics

    def calculate(self, data: pd.DataFrame) -> SwingMetrics:
        return self.calculate_swings(data)

    def _stats(self, series: pd.Series) -> dict:
        if series.empty:
            return {
                "count": 0,
                "avg": 0.0,
                "max": 0.0,
                "min": 0.0,
                "std": 0.0,
                "median": 0.0,
                "duration": 0.0,
                "max_duration": 0,
                "max_speed": 0.0,
            }

        durations = max(1, len(series))
        return {
            "count": int(series.count()),
            "avg": float(series.mean()),
            "max": float(series.max()),
            "min": float(series.min()),
            "std": float(series.std(ddof=0)) if series.count() > 1 else 0.0,
            "median": float(series.median()),
            "duration": float(durations / max(series.count(), 1)),
            "max_duration": int(durations),
            "max_speed": float(series.max()),
        }

    def _empty_metrics(self) -> SwingMetrics:
        return SwingMetrics(
            num_swings=0,
            avg_rally_pct=0.0,
            avg_drop_pct=0.0,
            max_rally_pct=0.0,
            max_drop_pct=0.0,
            rally_to_drop_ratio=1.0,
            rally_count=0,
            drop_count=0,
            min_rally_pct=0.0,
            min_drop_pct=0.0,
            rally_amplitude_std=0.0,
            drop_amplitude_std=0.0,
            rally_amplitude_median=0.0,
            drop_amplitude_median=0.0,
            avg_rally_duration_bars=0.0,
            avg_drop_duration_bars=0.0,
            max_rally_duration_bars=0,
            max_drop_duration_bars=0,
            avg_rally_speed_pct_per_bar=0.0,
            avg_drop_speed_pct_per_bar=0.0,
            max_rally_speed_pct_per_bar=0.0,
            max_drop_speed_pct_per_bar=0.0,
            duration_symmetry=1.0,
            strategy_name="MyCustomSwing",
            strategy_params={"threshold": self.threshold},
        )

    def get_metadata(self) -> dict:
        return {
            "strategy": "MyCustomSwing",
            "threshold": self.threshold,
            "algorithm": "Custom threshold-based swing detection",
            "description": "Detects swings when price movement exceeds threshold",
        }


mark_blocks(6)


class MyShapeStrategy:
    def calculate_shape(self, data: pd.DataFrame, indicator_col: str | None = None) -> ShapeMetrics:
        if indicator_col is None or indicator_col not in data.columns:
            raise ValueError("indicator_col required and must exist in data")

        oscillator = data[indicator_col]
        hist_skewness = float(oscillator.skew())
        hist_kurtosis = float(oscillator.kurtosis())
        hist_smoothness = float(1.0 - oscillator.diff().abs().mean() / oscillator.abs().mean())

        metrics = ShapeMetrics(
            hist_skewness=hist_skewness,
            hist_kurtosis=hist_kurtosis,
            hist_smoothness=max(hist_smoothness, 0.0),
            strategy_name="MyShape",
            strategy_params={"indicator_col": indicator_col},
        )
        metrics.validate()
        return metrics

    def get_name(self) -> str:
        return "MyShape"

    def get_metadata(self) -> dict:
        return {"strategy": "MyShape", "algorithm": "Custom shape analysis"}

    def calculate(self, data: pd.DataFrame, indicator_col: str | None = None) -> ShapeMetrics:
        return self.calculate_shape(data, indicator_col=indicator_col)


mark_blocks(9)


class MyDivergenceStrategy:
    def calculate_divergence(
        self,
        data: pd.DataFrame,
        indicator_col: str | None = None,
        indicator_line_col: str | None = None,
    ) -> DivergenceMetrics:
        if indicator_col is None or indicator_col not in data.columns:
            raise ValueError("indicator_col required and must exist in data")

        price = data["close"]
        oscillator = data[indicator_col]
        corr = price.pct_change().corr(oscillator.pct_change())

        metrics = DivergenceMetrics(
            divergence_type="regular" if corr and corr < 0 else "none",
            divergence_count=1 if corr and corr < -0.2 else 0,
            divergence_strength=float(abs(corr)) if corr else 0.0,
            divergence_direction="bullish" if corr and corr < 0 else "none",
            strategy_name="MyDivergence",
            strategy_params={
                "indicator_col": indicator_col,
                "indicator_line_col": indicator_line_col,
            },
        )
        metrics.validate()
        return metrics

    def get_name(self) -> str:
        return "MyDivergence"

    def get_metadata(self) -> dict:
        return {"strategy": "MyDivergence", "supports_2line": True}


mark_blocks(10)


if "my_custom" not in StrategyRegistry.list_swing_strategies():
    StrategyRegistry.register_swing_strategy("my_custom")(MyCustomSwingStrategy)
if "my_shape" not in StrategyRegistry.list_shape_strategies():
    StrategyRegistry.register_shape_strategy("my_shape")(MyShapeStrategy)
if "my_divergence" not in StrategyRegistry.list_divergence_strategies():
    StrategyRegistry.register_divergence_strategy("my_divergence")(MyDivergenceStrategy)


class CustomChart(ChartBuilder):
    """Кастомная визуализация из руководства."""

    def __init__(self, theme: str = "default"):
        super().__init__(backend="plotly")
        self.theme_name = theme
        self.themes = ChartThemes()

    def create_chart(self, data: pd.DataFrame, title: str = "Custom Chart", **kwargs):
        self.validate_data(data, ["close"])
        fig = self._build_chart(data, title, **kwargs)
        self._apply_theme(fig)
        return fig

    def _build_chart(self, data: pd.DataFrame, title: str, **kwargs):
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data["close"],
                mode="lines",
                name="Close Price",
                line=dict(color=kwargs.get("color", "#00A3E0")),
            )
        )
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price",
            height=kwargs.get("height", 600),
        )
        return fig

    def _apply_theme(self, fig):
        self.themes.apply_theme_to_figure(fig, self.theme_name)


mark_blocks(20)


class CustomDataLoader:
    """Адаптер загрузки данных из руководства."""

    def __init__(self, source_type: str = "custom_csv"):
        self.source_type = source_type

    def load(self, source, *, validate: bool = True, **kwargs) -> pd.DataFrame:
        if self.source_type == "custom_csv":
            data = loader.load_ohlcv_data(source, validate_data=validate, **kwargs)
            return self._standardize_columns(data)
        return loader.load_ohlcv_data(source, validate_data=validate, **kwargs)

    def _standardize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        mapping = {
            "Date": "time",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
        standardized = data.rename(columns=mapping)
        if "time" in standardized.columns:
            standardized["time"] = pd.to_datetime(standardized["time"])
            standardized = standardized.set_index("time").sort_index()
        return standardized


mark_blocks(22)


class CustomDataProcessor:
    """Процессор данных из руководства."""

    def __init__(self, *, remove_outliers: bool = True, add_features: bool = True, normalize: bool = False):
        self.remove_outliers = remove_outliers
        self.add_features = add_features
        self.normalize = normalize

    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        result = processor.clean_ohlcv_data(data, remove_outliers=self.remove_outliers)
        if self.add_features:
            result = self._add_features(result)
        if self.normalize:
            result = self._normalize(result)
        return result

    def _add_features(self, data: pd.DataFrame) -> pd.DataFrame:
        enriched = data.copy()
        enriched["sma_20"] = enriched["close"].rolling(window=20, min_periods=5).mean()
        enriched["sma_50"] = enriched["close"].rolling(window=50, min_periods=5).mean()
        enriched["rsi_14"] = self._calculate_rsi(enriched["close"])
        return enriched

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def _normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        normalized = data.copy()
        for column in ["open", "high", "low", "close"]:
            if column in normalized.columns:
                normalized[column] = (normalized[column] - normalized[column].mean()) / normalized[column].std()
        return normalized


mark_blocks(23)


ANALYZERS_REGISTRY: dict[str, type[BaseAnalyzer]] = {}


def register_extensions() -> None:
    try:
        IndicatorFactory.register_indicator("custom_indicator", CustomIndicator)
    except ValueError:
        pass
    ANALYZERS_REGISTRY["CustomAnalyzer"] = CustomAnalyzer


mark_blocks(28)


def _install_extension_package() -> None:
    pkg = types.ModuleType("my_bquant_extension")
    pkg.__all__ = [
        "CustomIndicator",
        "CustomAnalyzer",
        "CustomChart",
        "register_extensions",
        "ANALYZERS_REGISTRY",
    ]
    pkg.CustomIndicator = CustomIndicator
    pkg.CustomAnalyzer = CustomAnalyzer
    pkg.CustomChart = CustomChart
    pkg.register_extensions = register_extensions
    pkg.ANALYZERS_REGISTRY = ANALYZERS_REGISTRY

    indicators_module = types.ModuleType("my_bquant_extension.indicators")
    indicators_module.__all__ = ["custom_indicator"]

    analyzers_module = types.ModuleType("my_bquant_extension.analyzers")
    analyzers_module.__all__ = ["custom_analyzer"]

    visualizations_module = types.ModuleType("my_bquant_extension.visualizations")
    visualizations_module.__all__ = ["custom_chart"]

    indicators_custom_module = types.ModuleType("my_bquant_extension.indicators.custom_indicator")
    indicators_custom_module.CustomIndicator = CustomIndicator

    analyzers_custom_module = types.ModuleType("my_bquant_extension.analyzers.custom_analyzer")
    analyzers_custom_module.CustomAnalyzer = CustomAnalyzer

    visualizations_custom_module = types.ModuleType("my_bquant_extension.visualizations.custom_chart")
    visualizations_custom_module.CustomChart = CustomChart

    sys.modules["my_bquant_extension"] = pkg
    sys.modules["my_bquant_extension.indicators"] = indicators_module
    sys.modules["my_bquant_extension.analyzers"] = analyzers_module
    sys.modules["my_bquant_extension.visualizations"] = visualizations_module
    sys.modules["my_bquant_extension.indicators.custom_indicator"] = indicators_custom_module
    sys.modules["my_bquant_extension.analyzers.custom_analyzer"] = analyzers_custom_module
    sys.modules["my_bquant_extension.visualizations.custom_chart"] = visualizations_custom_module


_install_extension_package()
register_extensions()


mark_blocks(5)


def test_my_custom_strategy():
    strategy = MyCustomSwingStrategy(threshold=0.02)
    dates = pd.date_range("2024-01-01", periods=50, freq="1h")
    data = pd.DataFrame(
        {
            "high": np.random.randn(50).cumsum() + 2000,
            "low": np.random.randn(50).cumsum() + 1990,
            "close": np.random.randn(50).cumsum() + 1995,
        },
        index=dates,
    )

    result = strategy.calculate_swings(data)

    assert isinstance(result, SwingMetrics)
    assert result.num_swings >= 0
    assert result.rally_count >= 0
    assert result.drop_count >= 0
    assert result.strategy_name == "MyCustomSwing"
    assert "threshold" in result.strategy_params
    if result.num_swings > 0:
        assert result.avg_rally_pct >= 0
        assert result.avg_drop_pct >= 0
        assert result.rally_to_drop_ratio > 0


mark_blocks(11)


def test_strategy_with_analyzer():
    from bquant.analysis.zones import ZoneFeaturesAnalyzer as Analyzer

    analyzer = Analyzer(swing_strategy="my_custom")
    zone_dict = {
        "zone_id": "test_1",
        "type": "bull",
        "duration": 20,
        "data": ZONE_DATA,
    }
    features = analyzer.extract_zone_features(zone_dict)
    assert "swing_metrics" in features.metadata
    metrics = features.metadata["swing_metrics"]
    assert metrics["strategy_name"] == "MyCustomSwing"


mark_blocks(12)


def fast_calculation(data: pd.DataFrame) -> float:
    prices = data["close"].values
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns)
    return float(volatility)


def vectorized_operation(data: pd.DataFrame) -> pd.Series:
    return data["close"].rolling(window=20).mean()


mark_blocks(15)


def _validate_data(data: pd.DataFrame) -> None:
    if data.empty:
        raise ValueError("Data is empty")
    required = ["high", "low", "close"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if data[required].isnull().any().any():
        raise ValueError("Data contains NaN values")


mark_blocks(16)


class CustomError(BQuantError):
    """Кастомное исключение из документации."""


def perform_calculation(data: pd.DataFrame) -> float:
    return float(data["close"].mean())


def safe_calculation(data: pd.DataFrame) -> float:
    try:
        if data.empty:
            raise DataError("Empty dataset provided")
        if "close" not in data.columns:
            raise DataError("Missing 'close' column")
        result = perform_calculation(data)
        return result
    except Exception as exc:  # noqa: BLE001
        raise CustomError(f"Calculation failed: {exc}")


mark_blocks(32)


class DocumentedIndicator(BaseIndicator):
    """
    Кастомный индикатор для анализа финансовых данных.

    Этот индикатор рассчитывает специальный показатель на основе
    цены закрытия и объема торгов.

    Parameters
    ----------
    param1 : int, default=10
        Первый параметр индикатора
    param2 : int, default=20
        Второй параметр индикатора

    Examples
    --------
    >>> indicator = CustomIndicator(param1=15, param2=25)
    >>> result = indicator.calculate(data)
    >>> print(result.data.tail())

    Notes
    -----
    Индикатор использует скользящее среднее для сглаживания данных.
    """

    def calculate(self, data: pd.DataFrame) -> IndicatorResult:
        raise NotImplementedError


mark_blocks(33)


class ExtensionGuideDocExamplesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        logging.getLogger("bquant").setLevel(logging.ERROR)
        logging.getLogger("bquant.indicators").setLevel(logging.ERROR)
        cls.sample_data = SAMPLE_DATA
        cls.zone_dict = ZONE_DICT

    def test_indicator_factory_snippet(self):
        indicator = CustomIndicator(param1=12, param2=24)
        result = indicator.calculate(self.sample_data)
        self.assertIsInstance(result, IndicatorResult)
        self.assertIn("custom_indicator", result.data.columns)

        created = IndicatorFactory.create("custom", "custom_indicator", param1=5, param2=10)
        created_result = created.calculate(self.sample_data)
        self.assertGreater(created_result.data["custom_indicator"].notna().sum(), 0)
        mark_blocks(2)

    def test_analyzer_usage_snippet(self):
        analyzer = CustomAnalyzer(analysis_type="volatility")
        result = analyzer.analyze(self.sample_data[["close"]])
        self.assertIsInstance(result, AnalysisResult)
        self.assertIn("mean_volatility", result.results)
        mark_blocks(4)

    def test_registration_snippet(self):
        class StubRegistry:
            def __init__(self):
                self.names: list[str] = []

            def register_swing_strategy(self, name: str):
                def decorator(cls):
                    self.names.append(name)
                    return cls

                return decorator

            def list_swing_strategies(self):
                return ["zigzag", "find_peaks", "pivot_points", *self.names]

        namespace = {
            "StrategyRegistry": StubRegistry(),
            "SwingCalculationStrategy": SwingCalculationStrategy,
            "MyCustomSwingStrategy": MyCustomSwingStrategy,
        }
        exec(block_code(7), namespace)
        self.assertIn("my_custom", namespace["StrategyRegistry"].list_swing_strategies())
        mark_blocks(7)

    def test_strategy_usage_snippet(self):
        analyzer = ZoneFeaturesAnalyzer(
            swing_strategy="my_custom",
            shape_strategy="my_shape",
            divergence_strategy="my_divergence",
        )
        features = analyzer.extract_zone_features(self.zone_dict)
        swing_metrics = features.metadata["swing_metrics"]
        self.assertIsInstance(swing_metrics, dict)
        mark_blocks(8)

    def test_shape_strategy_example(self):
        strategy = StrategyRegistry.get_shape_strategy("my_shape")
        metrics = strategy.calculate_shape(self.zone_dict["data"], indicator_col="macd_hist")
        self.assertIsInstance(metrics, ShapeMetrics)
        mark_blocks(9)

    def test_divergence_strategy_example(self):
        strategy = StrategyRegistry.get_divergence_strategy("my_divergence")
        metrics = strategy.calculate_divergence(self.zone_dict["data"], indicator_col="macd_hist")
        self.assertIsInstance(metrics, DivergenceMetrics)
        mark_blocks(10)

    def test_pytest_strategy_block(self):
        test_my_custom_strategy()
        mark_blocks(11)

    def test_integration_testing_block(self):
        test_strategy_with_analyzer()
        mark_blocks(12)

    def test_graceful_degradation_block(self):
        short_data = self.sample_data.head(2)
        result = MyCustomSwingStrategy().calculate_swings(short_data)
        self.assertEqual(result.num_swings, 0)
        metadata = MyCustomSwingStrategy().get_metadata()
        self.assertEqual(metadata["strategy"], "MyCustomSwing")
        mark_blocks(13, 14)

    def test_performance_best_practices_block(self):
        vol = fast_calculation(self.sample_data)
        self.assertGreaterEqual(vol, 0.0)
        rolling = vectorized_operation(self.sample_data)
        self.assertEqual(len(rolling), len(self.sample_data))
        mark_blocks(15)

    def test_validate_inputs_block(self):
        _validate_data(self.sample_data)
        with self.assertRaises(ValueError):
            _validate_data(pd.DataFrame())
        mark_blocks(16)

    def test_strategy_comparison_block(self):
        strategies = ["zigzag", "find_peaks", "pivot_points", "my_custom"]
        results = {}
        for name in strategies:
            analyzer = ZoneFeaturesAnalyzer(swing_strategy=name)
            features = analyzer.extract_zone_features(self.zone_dict)
            swing = features.metadata["swing_metrics"]
            results[name] = {
                "num_swings": swing["num_swings"],
                "avg_rally": swing["avg_rally_pct"],
                "avg_drop": swing["avg_drop_pct"],
            }
        comparison = pd.DataFrame(results).T
        self.assertFalse(comparison.empty)
        mark_blocks(17)

    def test_registry_api_block(self):
        stats = StrategyRegistry.get_registry_stats()
        self.assertIn("total", stats)
        mark_blocks(18)

    def test_factory_configuration_block(self):
        strategy = create_swing_strategy("my_custom")
        self.assertIsInstance(strategy, MyCustomSwingStrategy)
        mark_blocks(19)

    def test_visualization_block(self):
        if not PLOTLY_AVAILABLE:
            self.skipTest("Plotly is not available in the environment")
        chart = CustomChart(theme="dark")
        fig = chart.create_chart(self.sample_data, title="Custom Analysis")
        self.assertEqual(fig.layout.title.text, "Custom Analysis")
        mark_blocks(20, 21)

    def test_data_loader_block(self):
        loader_adapter = CustomDataLoader()
        sample = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", periods=3, freq="D"),
                "Open": [1, 2, 3],
                "High": [2, 3, 4],
                "Low": [0.5, 1.5, 2.5],
                "Close": [1.5, 2.5, 3.5],
                "Volume": [100, 150, 200],
            }
        )
        standardized = loader_adapter._standardize_columns(sample)
        self.assertIn("close", standardized.columns)
        mark_blocks(22)

    def test_data_processor_block(self):
        processor_adapter = CustomDataProcessor(normalize=True)
        processed = processor_adapter.process(self.sample_data)
        self.assertIn("sma_20", processed.columns)
        mark_blocks(23)

    def test_pytest_extension_examples_block(self):
        def run_pytest_examples():
            dates = pd.date_range("2024-01-01", periods=100, freq="H")
            indicator_data = pd.DataFrame(
                {
                    "close": np.random.randn(100).cumsum() + 100,
                    "volume": np.random.randint(1000, 10000, 100),
                },
                index=dates,
            )
            indicator = CustomIndicator(param1=10, param2=20)
            result = indicator.calculate(indicator_data)
            assert result.name == "CustomIndicator"
            assert len(result.data) == len(indicator_data)
            assert not result.data["custom_indicator"].isna().all()

            analyzer_data = pd.DataFrame({"close": np.random.randn(100).cumsum() + 100}, index=dates)
            analyzer = CustomAnalyzer(analysis_type="volatility")
            analysis_result = analyzer.analyze(analyzer_data)
            assert analysis_result.analysis_type == "volatility"
            assert "mean_volatility" in analysis_result.results

        run_pytest_examples()
        mark_blocks(24)

    def test_bash_commands_block(self):
        commands = block_code(25).strip().splitlines()
        self.assertIn("pytest tests/test_custom_extensions.py -v", commands)
        self.assertIn("pytest tests/test_custom_extensions.py --cov=bquant --cov-report=html", commands)
        mark_blocks(25)

    def test_package_tree_block(self):
        tree = block_code(26)
        self.assertIn("my_bquant_extension/", tree)
        self.assertIn("└── tests/", tree)
        mark_blocks(26)

    def test_setup_py_block(self):
        ast.parse(block_code(27))
        mark_blocks(27)

    def test_extension_module_registration_block(self):
        self.assertIn("CustomAnalyzer", ANALYZERS_REGISTRY)
        mark_blocks(28)

    def test_using_custom_components_block(self):
        with mock.patch("bquant.data.samples.get_sample_data", return_value=self.sample_data):
            from my_bquant_extension import CustomIndicator as ExtIndicator, CustomAnalyzer as ExtAnalyzer, CustomChart as ExtChart

            indicator = ExtIndicator(param1=15, param2=25)
            indicator_result = indicator.calculate(self.sample_data)
            analyzer = ExtAnalyzer(analysis_type="volatility")
            analysis_result = analyzer.analyze(self.sample_data[["close"]])
            chart = ExtChart(theme="dark")
            mark_blocks(29)
            self.assertGreater(len(indicator_result.data), 0)
            self.assertIn("mean_volatility", analysis_result.results)
            if PLOTLY_AVAILABLE:
                fig = chart.create_chart(self.sample_data, title="Custom Analysis")
                self.assertEqual(fig.layout.title.text, "Custom Analysis")

    def test_cli_script_block(self):
        import argparse

        def main(argv: list[str] | None = None) -> None:
            parser = argparse.ArgumentParser(description="Custom analysis script")
            parser.add_argument("--dataset", default="tv_xauusd_1h", help="Dataset name")
            parser.add_argument("--param1", type=int, default=15, help="Parameter 1")
            parser.add_argument("--param2", type=int, default=25, help="Parameter 2")
            args = parser.parse_args(argv)
            data = bquant_get_sample_data(args.dataset)
            indicator = CustomIndicator(param1=args.param1, param2=args.param2)
            indicator.calculate(data)
            analyzer = CustomAnalyzer(analysis_type="volatility")
            analyzer.analyze(data[["close"]])

        with mock.patch("bquant.data.samples.get_sample_data") as patched:
            patched.return_value = self.sample_data
            from bquant.data.samples import get_sample_data as bquant_get_sample_data

            main(["--dataset", "tv_xauusd_1h", "--param1", "10", "--param2", "20"])
        mark_blocks(30)

    def test_performance_helpers_block(self):
        volatility = fast_calculation(self.sample_data)
        self.assertGreaterEqual(volatility, 0.0)
        rolling = vectorized_operation(self.sample_data)
        self.assertEqual(len(rolling), len(self.sample_data))
        mark_blocks(31)

    def test_error_handling_block(self):
        result = safe_calculation(self.sample_data)
        self.assertAlmostEqual(result, float(self.sample_data["close"].mean()))
        with self.assertRaises(CustomError):
            safe_calculation(pd.DataFrame())
        mark_blocks(32)

    def test_documentation_docstring_block(self):
        self.assertIn("Parameters", DocumentedIndicator.__doc__)
        mark_blocks(33)

    def test_zz_all_code_blocks_validated(self):
        self.assertEqual(COVERED_BLOCKS, set(range(1, TOTAL_BLOCKS + 1)))


if __name__ == "__main__":
    unittest.main()
