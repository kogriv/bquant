"""Валидирует примеры из docs/api/visualization/README.md."""

import os
import sys
import traceback
import warnings
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, List, Tuple

import pandas as pd

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("PLOTLY_RENDERER", "json")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Подключаем заглушки pandas-ta и общие хелперы
from devref.gaps.zo.zodoctest import test_indicators_readme_validation as indicator_helpers  # noqa: E402

try:  # noqa: SIM105 - диагностический импорт
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - информация для отладки
    go = None
else:
    if not getattr(go.Figure, "_zoval_patched", False):
        original_show = go.Figure.show

        def _safe_show(self, *args, **kwargs):  # type: ignore[override]
            """Подавляет попытки открытия UI, возвращая краткую сводку."""
            return {"traces": len(self.data), "has_layout": self.layout is not None}

        go.Figure.show = _safe_show  # type: ignore[assignment]
        go.Figure._zoval_patched = True  # type: ignore[attr-defined]
        go.Figure._zoval_original_show = original_show  # type: ignore[attr-defined]


def _print_result(title: str, success: bool) -> None:
    status = "✅" if success else "❌"
    print(f"{status} {title}")


@lru_cache(maxsize=1)
def _load_sample_data() -> pd.DataFrame:
    from bquant.data.samples import get_sample_data

    frame = get_sample_data("tv_xauusd_1h").copy()
    return frame


@lru_cache(maxsize=1)
def _pipeline_result():
    from bquant.analysis.zones import analyze_zones

    data = _load_sample_data()
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .analyze(clustering=True)
        .build()
    )


def _ensure_plotly(figures: List[object]) -> bool:
    for fig in figures:
        if fig is None:
            print("  ❌ Один из графиков не создан")
            return False
        if hasattr(fig, "show"):
            fig.show()
    return True


def test_financial_charts_examples() -> bool:
    print("\n📊 Тест: Создание финансовых графиков")

    try:
        from bquant.visualization import FinancialCharts
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт FinancialCharts: {exc}")
        traceback.print_exc()
        return False

    data = _load_sample_data()

    charts = FinancialCharts()
    try:
        candlestick_fig = charts.create_candlestick_chart(
            data,
            title="XAUUSD 1H - Candlestick Chart",
            volume=True,
            theme="dark",
        )
        ohlc_fig = charts.create_ohlc_chart(
            data,
            title="XAUUSD 1H - OHLC Chart",
            theme="light",
        )
        line_fig = charts.create_line_chart(
            data[["close"]],
            title="XAUUSD 1H - Close Price",
            theme="blue",
        )
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка при создании графиков: {exc}")
        traceback.print_exc()
        return False

    return _ensure_plotly([candlestick_fig, ohlc_fig, line_fig])


def test_pipeline_visualization_example() -> bool:
    print("\n🧭 Тест: Universal Pipeline visualization")

    result = _pipeline_result()

    if not result.zones:
        print("  ❌ Анализ зон не вернул результатов")
        return False

    try:
        overview = result.visualize("overview")
        detail = result.visualize("detail", zone_id=result.zones[0].zone_id)
        comparison = result.visualize(
            "comparison",
            max_zones=min(5, len(result.zones)),
        )
        statistics = result.visualize("statistics")
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка визуализации pipeline: {exc}")
        traceback.print_exc()
        return False

    return _ensure_plotly([overview, detail, comparison, statistics])


def test_advanced_zone_visualization() -> bool:
    print("\n🎯 Тест: Advanced Zone Visualization")

    try:
        from datetime import datetime
        from bquant.visualization import ZoneVisualizer
    except Exception as exc:  # pragma: no cover - диагностика импортов
        print(f"  ❌ Импорт ZoneVisualizer: {exc}")
        traceback.print_exc()
        return False

    data = _load_sample_data()
    result = _pipeline_result()
    if not result.zones:
        print("  ❌ Нет зон для визуализации")
        return False

    zone_viz = ZoneVisualizer()
    try:
        detail_fig = zone_viz.plot_zone_detail(
            data,
            result.zones[0],
            context_bars=15,
            show_indicators=True,
            title="Zone Detail Analysis",
        )
        comparison_fig = zone_viz.plot_zones_comparison(
            data,
            result.zones,
            date_range=(datetime(2024, 1, 1), datetime(2024, 3, 1)),
            max_zones=min(5, len(result.zones)),
            title="Zones Comparison",
        )
        price_fig = zone_viz.plot_zones_on_price_chart(
            data,
            result.zones,
        )
    except Exception as exc:  # pragma: no cover - диагностика выполнения
        print(f"  ❌ Ошибка продвинутой визуализации: {exc}")
        traceback.print_exc()
        return False

    return _ensure_plotly([detail_fig, comparison_fig, price_fig])


def test_statistical_plots_example() -> bool:
    print("\n📈 Тест: Статистические графики")

    try:
        from bquant.visualization import StatisticalPlots
    except Exception as exc:
        print(f"  ❌ Импорт StatisticalPlots: {exc}")
        traceback.print_exc()
        return False

    data = _load_sample_data()
    result = _pipeline_result()

    plots = StatisticalPlots()
    try:
        corr_fig = plots.plot_correlation_matrix(
            data[["open", "high", "low", "close", "volume"]],
            title="Correlation Matrix",
            theme="heatmap",
        )
        dist_fig = plots.plot_distribution(
            data["close"],
            title="Close Price Distribution",
            plot_type="histogram",
            theme="blue",
        )
    except Exception as exc:
        print(f"  ❌ Ошибка при построении базовых графиков: {exc}")
        traceback.print_exc()
        return False

    figures = [corr_fig, dist_fig]

    if result.hypothesis_tests:
        try:
            hypothesis_fig = plots.plot_hypothesis_results(
                result.hypothesis_tests.results,
                title="Hypothesis Test Results",
                theme="dark",
            )
        except Exception as exc:
            print(f"  ❌ Ошибка вывода результатов гипотез: {exc}")
            traceback.print_exc()
            return False
        else:
            figures.append(hypothesis_fig)

    bull_volatility = [
        zone.features.get("volatility_score", 0)
        for zone in result.zones
        if zone.features and zone.type == "bull"
    ]
    bear_volatility = [
        zone.features.get("volatility_score", 0)
        for zone in result.zones
        if zone.features and zone.type == "bear"
    ]
    if not bull_volatility:
        bull_volatility = [0.0]
    if not bear_volatility:
        bear_volatility = [0.0]

    try:
        box_fig = plots.plot_box_plot(
            data=[bull_volatility, bear_volatility],
            labels=["Bull Zones", "Bear Zones"],
            title="Volatility Comparison",
            theme="light",
        )
    except Exception as exc:
        print(f"  ❌ Ошибка построения box plot: {exc}")
        traceback.print_exc()
        return False

    figures.append(box_fig)
    return _ensure_plotly(figures)


def test_chart_themes_example() -> bool:
    print("\n🎨 Тест: Настройка тем")

    try:
        from bquant.visualization import FinancialCharts
        from bquant.visualization.themes import (
            ChartThemes,
            create_custom_theme,
            apply_theme,
            apply_theme_to_figure,
        )
    except Exception as exc:
        print(f"  ❌ Импорт тем или графиков: {exc}")
        traceback.print_exc()
        return False

    themes = ChartThemes()
    available = themes.get_available_themes()
    if "bquant_dark" not in available:
        print(f"  ❌ Тема bquant_dark отсутствует: {available}")
        return False

    apply_theme("bquant_dark")
    custom_created = create_custom_theme(
        name="my_theme",
        colors={
            "background": "#f8f9fa",
            "paper": "#ffffff",
            "text": "#2c3e50",
            "grid": "#d1d5db",
            "bullish": "#1f77b4",
            "bearish": "#ff7f0e",
            "volume": "#2c3e50",
        },
        layout={
            "font_family": "Arial",
            "font_size": 12,
            "title_font_size": 16,
            "show_legend": True,
        },
    )
    if not custom_created:
        print("  ❌ Создание кастомной темы вернуло False")
        return False

    apply_theme("my_theme")

    charts = FinancialCharts()
    data = _load_sample_data()
    try:
        themed_fig = charts.create_candlestick_chart(
            data,
            title="Custom Theme Chart",
        )
        themed_fig = apply_theme_to_figure(themed_fig, "my_theme")
    except Exception as exc:
        print(f"  ❌ Ошибка применения темы: {exc}")
        traceback.print_exc()
        return False

    return _ensure_plotly([themed_fig])


def test_combined_visualization_example() -> bool:
    print("\n🧩 Тест: Комбинированная визуализация")

    from bquant.visualization import FinancialCharts, ZoneVisualizer, StatisticalPlots

    data = _load_sample_data()
    result = _pipeline_result()

    def create_comprehensive_analysis(data_frame, pipeline_result):
        """Создание комплексной визуализации анализа с Universal Pipeline."""

        charts = FinancialCharts()
        zone_viz = ZoneVisualizer()
        stat_plots = StatisticalPlots()

        price_fig = zone_viz.plot_zones_on_price_chart(
            data_frame,
            pipeline_result.zones,
            title="Price Analysis with Universal Zones",
            theme="dark",
        )

        detail_fig = zone_viz.plot_zone_detail(
            data_frame,
            pipeline_result.zones[0],
            context_bars=20,
            title="Zone Detail Analysis",
            theme="dark",
        )

        comparison_fig = zone_viz.plot_zones_comparison(
            data_frame,
            pipeline_result.zones,
            max_zones=min(5, len(pipeline_result.zones)),
            title="Zones Comparison",
            theme="blue",
        )

        hypothesis_fig = None
        if pipeline_result.hypothesis_tests:
            hypothesis_fig = stat_plots.plot_hypothesis_results(
                pipeline_result.hypothesis_tests.results,
                title="Statistical Test Results",
                theme="dark",
            )

        return {
            "price_chart": price_fig,
            "detail_chart": detail_fig,
            "comparison_chart": comparison_fig,
            "hypothesis_results": hypothesis_fig,
        }

    try:
        figures = create_comprehensive_analysis(data, result)
    except Exception as exc:
        print(f"  ❌ Ошибка при создании комплексной визуализации: {exc}")
        traceback.print_exc()
        return False

    for name, fig in figures.items():
        if fig is None:
            continue
        print(f"  ℹ️ График {name} создан")
        if hasattr(fig, "show"):
            fig.show()

    return True


def test_export_example() -> bool:
    print("\n💾 Тест: Экспорт графиков")

    try:
        from bquant.visualization import FinancialCharts
    except Exception as exc:
        print(f"  ❌ Импорт FinancialCharts: {exc}")
        traceback.print_exc()
        return False

    data = _load_sample_data()
    charts = FinancialCharts()
    try:
        fig = charts.create_candlestick_chart(
            data,
            title="XAUUSD 1H Analysis",
            theme="dark",
        )
    except Exception as exc:
        print(f"  ❌ Ошибка создания графика для экспорта: {exc}")
        traceback.print_exc()
        return False

    with TemporaryDirectory() as tmp_dir:
        export_dir = Path(tmp_dir)
        try:
            fig.write_html(export_dir / "chart.html")
            fig.write_json(export_dir / "chart.json")
        except Exception as exc:
            print(f"  ❌ Ошибка экспорта графиков: {exc}")
            traceback.print_exc()
            return False

        if not (export_dir / "chart.html").exists():
            print("  ❌ HTML файл не создан")
            return False
        if not (export_dir / "chart.json").exists():
            print("  ❌ JSON файл не создан")
            return False

    return _ensure_plotly([fig])


def test_custom_chart_example() -> bool:
    print("\n🛠️ Тест: Кастомный график волатильности")

    try:
        from bquant.visualization.charts import ChartBuilder
        from bquant.visualization.themes import ChartThemes
        import plotly.graph_objects as go
    except Exception as exc:
        print(f"  ❌ Импорт компонентов для кастомного графика: {exc}")
        traceback.print_exc()
        return False

    class CustomVolatilityChart(ChartBuilder):
        """Реализация примера CustomVolatilityChart из документации."""

        def __init__(self, theme: str = "bquant_dark"):
            super().__init__(backend="plotly")
            self.theme_manager = ChartThemes()
            self.theme_name = theme
            self.theme_config = self.theme_manager.get_theme(self.theme_name)

        def create_chart(self, data: pd.DataFrame, window_size: int = 20, title: str = "Volatility Chart"):
            self.validate_data(data, ["close"])
            data = self._prepare_datetime_index(data.copy())

            returns = data["close"].pct_change()
            volatility = returns.rolling(window=window_size).std()

            colors = self.theme_config.get("colors", {})
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=volatility,
                    mode="lines",
                    name="Volatility",
                    line=dict(color=colors.get("neutral", "#3498db")),
                )
            )
            fig.update_layout(
                title=title,
                xaxis_title="Date",
                yaxis_title="Volatility",
                height=600,
            )

            return self.theme_manager.apply_theme_to_figure(fig, self.theme_name)

    data = _load_sample_data()
    chart = CustomVolatilityChart(theme="bquant_dark")
    try:
        figure = chart.create_chart(data, window_size=20)
    except Exception as exc:
        print(f"  ❌ Ошибка построения кастомного графика: {exc}")
        traceback.print_exc()
        return False

    return _ensure_plotly([figure])


def test_interactive_elements_example() -> bool:
    print("\n🕹️ Тест: Интерактивные элементы")

    try:
        from bquant.visualization import FinancialCharts
    except Exception as exc:
        print(f"  ❌ Импорт FinancialCharts: {exc}")
        traceback.print_exc()
        return False

    data = _load_sample_data()
    charts = FinancialCharts()
    try:
        fig = charts.create_candlestick_chart(
            data,
            title="Interactive XAUUSD Chart",
            theme="dark",
            interactive=True,
        )
        fig.update_layout(
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )
        fig.update_layout(
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    x=0.1,
                    y=1.1,
                    showactive=False,
                    buttons=[
                        dict(
                            label="1H",
                            method="relayout",
                            args=[{"xaxis.range": [data.index[-100], data.index[-1]]}],
                        ),
                        dict(
                            label="1D",
                            method="relayout",
                            args=[{"xaxis.range": [data.index[-24], data.index[-1]]}],
                        ),
                        dict(
                            label="1W",
                            method="relayout",
                            args=[{"xaxis.range": [data.index[-168], data.index[-1]]}],
                        ),
                        dict(
                            label="All",
                            method="relayout",
                            args=[{"xaxis.range": [data.index[0], data.index[-1]]}],
                        ),
                    ],
                )
            ]
        )
    except Exception as exc:
        print(f"  ❌ Ошибка настройки интерактивного графика: {exc}")
        traceback.print_exc()
        return False

    return _ensure_plotly([fig])


def test_cross_references() -> bool:
    print("\n🔗 Тест: Cross-references visualization README")

    targets = [
        PROJECT_ROOT / "docs" / "api" / "analysis" / "pipeline.md",
        PROJECT_ROOT / "docs" / "api" / "analysis" / "zones.md",
        PROJECT_ROOT / "docs" / "api" / "analysis" / "strategies.md",
        PROJECT_ROOT / "docs" / "api" / "core" / "README.md",
        PROJECT_ROOT / "docs" / "api" / "indicators" / "README.md",
    ]

    missing = [str(path) for path in targets if not path.exists()]
    if missing:
        print("  ❌ Отсутствуют ссылки:")
        for path in missing:
            print(f"    - {path}")
        return False

    print("  ✅ Все связанные документы найдены")
    return True


def main() -> int:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

    tests: Tuple[Tuple[str, Callable[[], bool]], ...] = (
        ("Финансовые графики", test_financial_charts_examples),
        ("Pipeline visualization", test_pipeline_visualization_example),
        ("Advanced zone visualization", test_advanced_zone_visualization),
        ("Статистические графики", test_statistical_plots_example),
        ("Настройка тем", test_chart_themes_example),
        ("Комбинированная визуализация", test_combined_visualization_example),
        ("Экспорт графиков", test_export_example),
        ("Кастомный график", test_custom_chart_example),
        ("Интерактивные элементы", test_interactive_elements_example),
        ("Cross-reference", test_cross_references),
    )

    all_ok = True
    results = []
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
