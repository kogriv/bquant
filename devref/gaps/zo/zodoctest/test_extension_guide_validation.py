"""Validation of docs/api/extension_guide.md examples.

This module re-creates the code blocks from the extension guide with the
minimum adjustments necessary to work against the current BQuant API.  The
focus is on verifying that every documented example can be executed without
runtime errors and still mirrors the structure shown in the documentation.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from bquant.indicators.base import (  # noqa: E402
    BaseIndicator,
    CustomIndicator as BQuantCustomIndicator,
    IndicatorResult,
    IndicatorSource,
    IndicatorFactory,
)
from bquant.analysis import BaseAnalyzer, AnalysisResult  # noqa: E402
from bquant.analysis.zones.zone_features import ZoneFeaturesAnalyzer  # noqa: E402
from bquant.analysis.zones.strategies.base import (  # noqa: E402
    SwingMetrics,
    ShapeMetrics,
    DivergenceMetrics,
)
from bquant.analysis.zones.strategies.registry import StrategyRegistry  # noqa: E402
from bquant.visualization.charts import ChartBuilder, PLOTLY_AVAILABLE  # noqa: E402
from bquant.visualization.themes import ChartThemes  # noqa: E402
from bquant.data import loader, processor  # noqa: E402


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
        rolling = data["close"].rolling(window=10, min_periods=3).mean().fillna(method="bfill")
        return {
            "data": rolling,
            "statistics": {
                "mean_close": float(data["close"].mean()),
                "std_close": float(data["close"].std()),
            },
        }


@StrategyRegistry.register_swing_strategy("my_custom")
class MyCustomSwingStrategy:
    """Упрощенная реализация стратегии свингов из документации."""

    def __init__(self, threshold: float = 0.02):
        self.threshold = threshold

    def calculate_swings(self, data: pd.DataFrame) -> SwingMetrics:
        if len(data) < 3:
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

        count = int(series.count())
        return {
            "count": count,
            "avg": float(series.mean()),
            "max": float(series.max()),
            "min": float(series.min()),
            "std": float(series.std(ddof=0)) if count > 1 else 0.0,
            "median": float(series.median()),
            "duration": float(len(series) / max(count, 1)),
            "max_duration": int(len(series)),
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
        }


@StrategyRegistry.register_shape_strategy("my_shape")
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


@StrategyRegistry.register_divergence_strategy("my_divergence")
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


class CustomChart(ChartBuilder):
    """Пример пользовательской визуализации."""

    def __init__(self, backend: str = "plotly", theme: str = "bquant_dark"):
        super().__init__(backend)
        self.themes = ChartThemes()
        self.theme_name = theme

    def create_chart(self, data: pd.DataFrame, title: str = "Custom Chart", **kwargs):
        self.validate_data(data, ["close"])
        prepared = self._prepare_datetime_index(data)

        import plotly.graph_objects as go  # local import respecting PLOTLY_AVAILABLE

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=prepared.index,
                y=prepared["close"],
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
        self.themes.apply_theme_to_figure(fig, self.theme_name)
        return fig


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
        normalized = data.rename(columns=mapping)
        if "time" in normalized.columns:
            normalized["time"] = pd.to_datetime(normalized["time"])
            normalized = normalized.set_index("time").sort_index()
        return normalized


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
        enriched["sma_20"] = enriched["close"].rolling(window=20).mean()
        enriched["sma_50"] = enriched["close"].rolling(window=50).mean()
        enriched["rsi_14"] = self._calculate_rsi(enriched["close"])
        return enriched

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def _normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        normalized = data.copy()
        for column in ["open", "high", "low", "close"]:
            if column in normalized.columns:
                normalized[column] = (normalized[column] - normalized[column].mean()) / normalized[column].std()
        return normalized


ANALYZERS_REGISTRY: dict[str, type[BaseAnalyzer]] = {}


def register_extensions():
    """Реализация примера автоматической регистрации."""
    IndicatorFactory.register_indicator("custom_indicator", CustomIndicator)
    ANALYZERS_REGISTRY["CustomAnalyzer"] = CustomAnalyzer


# --- динамическая упаковка примера my_bquant_extension ---
my_extension_pkg = types.ModuleType("my_bquant_extension")
my_extension_pkg.__all__ = ["CustomIndicator", "CustomAnalyzer", "CustomChart", "register_extensions"]
my_extension_pkg.CustomIndicator = CustomIndicator
my_extension_pkg.CustomAnalyzer = CustomAnalyzer
my_extension_pkg.CustomChart = CustomChart
my_extension_pkg.register_extensions = register_extensions

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

sys.modules["my_bquant_extension"] = my_extension_pkg
sys.modules["my_bquant_extension.indicators"] = indicators_module
sys.modules["my_bquant_extension.analyzers"] = analyzers_module
sys.modules["my_bquant_extension.visualizations"] = visualizations_module
sys.modules["my_bquant_extension.indicators.custom_indicator"] = indicators_custom_module
sys.modules["my_bquant_extension.analyzers.custom_analyzer"] = analyzers_custom_module
sys.modules["my_bquant_extension.visualizations.custom_chart"] = visualizations_custom_module


register_extensions()


def test_my_custom_strategy():
    """Пример из раздела Testing Your Strategy."""
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
    assert result.strategy_name == "MyCustomSwing"
    assert "threshold" in result.strategy_params


class ExtensionGuideExamplesTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(42)
        dates = pd.date_range("2024-01-01", periods=120, freq="h")
        close = rng.normal(loc=0.1, scale=1.0, size=len(dates)).cumsum() + 100
        high = close + rng.random(len(dates))
        low = close - rng.random(len(dates))
        volume = rng.integers(1_000, 5_000, size=len(dates))
        macd_hist = rng.normal(scale=0.05, size=len(dates))

        self.sample_data = pd.DataFrame(
            {
                "open": close,
                "high": np.maximum(high, close),
                "low": np.minimum(low, close),
                "close": close,
                "volume": volume,
                "macd_hist": macd_hist,
            },
            index=dates,
        )

    def test_indicator_and_factory(self):
        indicator = CustomIndicator(param1=12, param2=24)
        result = indicator.calculate(self.sample_data)

        self.assertIsInstance(result, IndicatorResult)
        self.assertEqual(result.name, "CustomIndicator")
        self.assertIn("custom_indicator", result.data.columns)
        self.assertEqual(len(result.data), len(self.sample_data))

        created = IndicatorFactory.create("custom", "custom_indicator", param1=5, param2=10)
        created_result = created.calculate(self.sample_data)
        self.assertGreaterEqual(created_result.data["custom_indicator"].notna().sum(), 1)

    def test_custom_analyzer(self):
        analyzer = CustomAnalyzer(analysis_type="volatility")
        result = analyzer.analyze(self.sample_data[["close"]])

        self.assertIsInstance(result, AnalysisResult)
        self.assertIn("mean_volatility", result.results)
        self.assertGreaterEqual(result.results["mean_volatility"], 0)

    def test_strategy_registry_and_zone_features(self):
        self.assertIn("my_custom", StrategyRegistry.list_swing_strategies())
        zone_data = self.sample_data[["high", "low", "close", "macd_hist"]].head(50)

        analyzer = ZoneFeaturesAnalyzer(
            swing_strategy="my_custom",
            shape_strategy="my_shape",
            divergence_strategy="my_divergence",
        )
        zone_dict = {
            "zone_id": "test_zone",
            "type": "bull",
            "duration": len(zone_data),
            "data": zone_data,
            "indicator_context": {"detection_indicator": "macd_hist"},
        }
        features = analyzer.extract_zone_features(zone_dict)
        self.assertIn("swing_metrics", features.metadata)
        swing_metrics = features.metadata["swing_metrics"]
        self.assertIsInstance(swing_metrics, dict)
        self.assertEqual(swing_metrics.get("strategy_name"), "MyCustomSwing")

        shape_strategy = StrategyRegistry.get_shape_strategy("my_shape")
        shape_metrics = shape_strategy.calculate_shape(zone_data, indicator_col="macd_hist")
        self.assertIsInstance(shape_metrics, ShapeMetrics)

        divergence_strategy = StrategyRegistry.get_divergence_strategy("my_divergence")
        divergence_metrics = divergence_strategy.calculate_divergence(zone_data, indicator_col="macd_hist")
        self.assertIsInstance(divergence_metrics, DivergenceMetrics)

    def test_visualization_example(self):
        if not PLOTLY_AVAILABLE:
            self.skipTest("Plotly is not available in the environment")
        chart = CustomChart(theme="bquant_light")
        fig = chart.create_chart(self.sample_data, title="Custom Analysis")
        self.assertEqual(fig.layout.title.text, "Custom Analysis")

    def test_data_loader_and_processor(self):
        loader_adapter = CustomDataLoader()
        sample = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", periods=5, freq="D"),
                "Open": np.linspace(1, 5, 5),
                "High": np.linspace(2, 6, 5),
                "Low": np.linspace(0.5, 4.5, 5),
                "Close": np.linspace(1.5, 5.5, 5),
                "Volume": np.arange(100, 600, 100),
            }
        )
        standardized = loader_adapter._standardize_columns(sample)
        self.assertIn("close", standardized.columns)

        processor_adapter = CustomDataProcessor(normalize=True)
        processed = processor_adapter.process(self.sample_data)
        self.assertIn("sma_20", processed.columns)

    def test_register_extensions(self):
        self.assertIn("CustomAnalyzer", ANALYZERS_REGISTRY)
        factory_indicator = IndicatorFactory.create("custom", "custom_indicator", param1=8, param2=16)
        self.assertIsInstance(factory_indicator, CustomIndicator)

    def test_testing_snippet_runs(self):
        # Ensures the pytest-style snippet from the documentation is executable.
        test_my_custom_strategy()


if __name__ == "__main__":
    unittest.main()
