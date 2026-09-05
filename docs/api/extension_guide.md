# Руководство по расширению

Как добавить в пакет свой индикатор, анализатор, стратегию метрик зон или график, не
трогая базовые модули. Каждый пример на странице самодостаточен и исполняется слоем
проверок; контракты сверены с кодом 2026-09-05, числа — из прогона.

## Принцип

Расширение подключается **по имени** через реестр или фабрику, а не правкой ядра. Ядро
дискриминирует на закрытых словарях (роли колонок, свойства типов зон, статус
реализации), расширение приносит открытое — имена, параметры, алгоритм. Отказ лучше
правдоподобного числа: индикатор на коротком кадре поднимает `DataValidationError`, а не
возвращает `NaN`; стратегия без нужного метода отвергается при создании анализатора, а не
даёт `None` в каждой зоне.

## Свой индикатор

Наследник `CustomIndicator` объявляет входные и выходные колонки, минимум строк **для
параметров вызова** и считает. `validate_data()` поднимает `DataValidationError` — колонки,
число строк, числовой dtype, отсутствие `inf` — и возвращать `False` не умеет; проверять её
результат не нужно.

```python
import pandas as pd

from bquant.indicators.base import CustomIndicator, IndicatorFactory, IndicatorResult


class VolumeWeightedClose(CustomIndicator):
    """Скользящее среднее close, взвешенное объёмом."""

    def __init__(self, period: int = 10):
        self.period = period
        super().__init__("vwclose", {"period": period})

    def get_output_columns(self):
        return [f"vwclose_{self.period}"]

    def get_required_columns(self):
        return ["close", "volume"]

    def get_min_records(self, **params):
        return params.get("period", self.period)

    def get_description(self):
        return "Volume-weighted moving average of close"

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        period = kwargs.get("period", self.period)
        self.validate_data(data, period=period)
        weighted = (data["close"] * data["volume"]).rolling(period).sum() / data["volume"].rolling(period).sum()
        frame = pd.DataFrame({f"vwclose_{period}": weighted}, index=data.index)
        return IndicatorResult(name=self.name, data=frame, config=self.config,
                               metadata={"period": period})


IndicatorFactory.register_indicator("vwclose", VolumeWeightedClose)
indicator = IndicatorFactory.create("custom", "vwclose", period=3)

frame = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0], "volume": [1.0, 1.0, 2.0, 2.0]})
print(indicator.calculate(frame).data["vwclose_3"].round(3).tolist())
# [nan, nan, 11.25, 12.2]

try:
    indicator.calculate(frame.head(2))
except Exception as exc:
    print(type(exc).__name__, str(exc).startswith("vwclose: 2 rows, but at least 3 are needed"))
# DataValidationError True
```

Колонки индикатора в пайплайне называются по его **идентичности** (`get_indicator_id()`,
`slug` из имени и параметров) и роли — см. [custom.md](indicators/custom.md); чтобы
потребители адресовались по роли, объявите `get_output_roles()`.

## Свой анализатор

Наследник `BaseAnalyzer` реализует `analyze(data, **kwargs) -> AnalysisResult`. Своя
`validate_data()` возвращает `bool` — это контракт анализаторов, не индикаторов.

```python
import numpy as np
import pandas as pd

from bquant.analysis import AnalysisResult, BaseAnalyzer


class RollingVolatilityAnalyzer(BaseAnalyzer):
    def __init__(self, window: int = 20):
        super().__init__("RollingVolatilityAnalyzer", {"window": window})

    def validate_data(self, data: pd.DataFrame) -> bool:
        return "close" in data.columns and len(data) > self.config["window"]

    def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
        if not self.validate_data(data):
            raise ValueError("need a 'close' column longer than the window")
        vol = data["close"].pct_change().rolling(self.config["window"]).std().dropna()
        return AnalysisResult(
            analysis_type="rolling_volatility",
            results={"mean": float(vol.mean()), "max": float(vol.max()), "last": float(vol.iloc[-1])},
            data_size=len(data),
            metadata={"window": self.config["window"]},
        )


rng = np.random.default_rng(0)
prices = pd.DataFrame({"close": 100 + np.cumsum(rng.normal(0, 1, 200))})
result = RollingVolatilityAnalyzer(window=20).analyze(prices)
print(result.analysis_type, sorted(result.results), result.data_size)
# rolling_volatility ['last', 'max', 'mean'] 200
```

В каталог фабрики `create_analyzer()` попадает только то, что она умеет собрать
(`get_available_analyzers()`); свой анализатор в неё не регистрируется — он вызывается
напрямую.

## Своя стратегия метрик зон

`ZoneFeaturesAnalyzer` считает признаки каждой зоны пятью семействами стратегий. Для
каждого есть протокол в `bquant.analysis.zones.strategies.base` и dataclass метрик с
`validate()`:

| Семейство | Что зовёт анализатор | Метрик |
|---|---|---|
| `swing` — `SwingCalculationStrategy` | `calculate(zone_data)`; в `global`-режиме — `calculate_global(full_data)` и `aggregate_for_zone(zone, context)` | 23 (`SwingMetrics`) |
| `shape` — `ShapeCalculationStrategy` | `calculate(zone_data, indicator_col)` | 3 (`ShapeMetrics`) |
| `divergence` — `DivergenceCalculationStrategy` | `calculate_divergence(zone_data, indicator_col, indicator_line_col=None)` | 4 (`DivergenceMetrics`) |
| `volatility` — `VolatilityCalculationStrategy` | `calculate_volatility(zone_data)` | 10 (`VolatilityMetrics`) |
| `volume` — `VolumeCalculationStrategy` | `calculate_volume(zone_data, baseline_volume=None, indicator_col=None)` | 4 (`VolumeMetrics`) |

Плюс `get_metadata()` у всех. Анализатор проверяет наличие этих методов **при создании**
и отказывает `TypeError` по имени. До 2026-09-05 протоколы объявляли другие сигнатуры
(`calculate_shape(zone_data)`, `calculate_divergence(zone_data)`, у объёма — вовсе
`calculate_volatility`), стратегия, написанная по ним, падала внутри анализатора, и
падение превращалось в `None` в каждой зоне (G68).

### Пример: свинги по порогу изменения close

Стратегия регистрируется декоратором, после чего доступна по имени и в
`ZoneFeaturesAnalyzer(swing_strategy=...)`, и в `.with_strategies(swing=...)`.

```python
import numpy as np
import pandas as pd

from bquant.analysis.zones import ZoneFeaturesAnalyzer, analyze_zones
from bquant.analysis.zones.models import SwingContext, SwingPoint
from bquant.analysis.zones.strategies.base import SwingMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry
from bquant.data.samples import get_sample_data


@StrategyRegistry.register_swing_strategy('close_threshold')
class CloseThresholdSwingStrategy:
    """Свинг — любой сдвиг close от бара к бару больше `threshold` (доля)."""

    def __init__(self, threshold: float = 0.002):
        self.threshold = threshold

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        returns = zone_data['close'].pct_change().dropna()
        return self._metrics(returns[returns >= self.threshold], -returns[returns <= -self.threshold])

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        close = full_data['close'].to_numpy(dtype=float)
        idx = np.flatnonzero(np.abs(np.diff(close) / close[:-1]) >= self.threshold) + 1
        points = [SwingPoint(point_id=i, timestamp=full_data.index[j], index=int(j), price=float(close[j]),
                             swing_type='peak' if close[j] > close[j - 1] else 'trough',
                             strategy_name='close_threshold', strategy_params={'threshold': self.threshold},
                             confirmation_index=int(j))
                  for i, j in enumerate(idx)]
        return SwingContext(swing_points=points, indices=np.asarray(idx, dtype=int),
                            full_data_length=len(full_data), strategy_name='close_threshold',
                            strategy_params={'threshold': self.threshold})

    def aggregate_for_zone(self, zone, context: SwingContext) -> SwingMetrics:
        inside = [p for p in context.slice(zone.start_idx, zone.end_idx)
                  if zone.start_idx <= p.index <= zone.end_idx]
        moves = pd.Series([abs(p.price / context.swing_points[p.point_id - 1].price - 1)
                           if p.point_id else 0.0 for p in inside])
        ups = pd.Series([m for p, m in zip(inside, moves) if p.swing_type == 'peak'])
        downs = pd.Series([m for p, m in zip(inside, moves) if p.swing_type == 'trough'])
        return self._metrics(ups, downs)

    def get_metadata(self) -> dict:
        return {'strategy': 'close_threshold', 'threshold': self.threshold}

    def _metrics(self, rallies: pd.Series, drops: pd.Series) -> SwingMetrics:
        def stats(s):
            if s.empty:
                return dict(count=0, avg=0.0, mx=0.0, mn=0.0, std=0.0, med=0.0)
            return dict(count=int(len(s)), avg=float(s.mean()), mx=float(s.max()), mn=float(s.min()),
                        std=float(s.std(ddof=0)) if len(s) > 1 else 0.0, med=float(s.median()))
        r, d = stats(rallies), stats(drops)
        metrics = SwingMetrics(
            num_swings=r['count'] + d['count'], avg_rally_pct=r['avg'], avg_drop_pct=d['avg'],
            max_rally_pct=r['mx'], max_drop_pct=d['mx'],
            rally_to_drop_ratio=(r['avg'] / d['avg']) if d['avg'] else 1.0,
            rally_count=r['count'], drop_count=d['count'], min_rally_pct=r['mn'], min_drop_pct=d['mn'],
            rally_amplitude_std=r['std'], drop_amplitude_std=d['std'],
            rally_amplitude_median=r['med'], drop_amplitude_median=d['med'],
            avg_rally_duration_bars=1.0 if r['count'] else 0.0, avg_drop_duration_bars=1.0 if d['count'] else 0.0,
            max_rally_duration_bars=1 if r['count'] else 0, max_drop_duration_bars=1 if d['count'] else 0,
            avg_rally_speed_pct_per_bar=r['avg'], avg_drop_speed_pct_per_bar=d['avg'],
            max_rally_speed_pct_per_bar=r['mx'], max_drop_speed_pct_per_bar=d['mx'],
            duration_symmetry=1.0, strategy_name='close_threshold',
            strategy_params={'threshold': self.threshold},
        )
        metrics.validate()
        return metrics


print(StrategyRegistry.list_swing_strategies())
print(StrategyRegistry.get_registry_stats())
# ['zigzag', 'find_peaks', 'pivot_points', 'close_threshold']
# {'swing': 4, 'divergence': 1, 'shape': 1, 'volume': 1, 'volatility': 1, 'total': 8}

data = get_sample_data('tv_xauusd_1h')
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='close_threshold')
    .with_swing_scope('per_zone')
    .with_cache(enable=False)
    .analyze(clustering=False)
    .build()
)
swings = result.zones[3].features['metadata']['swing_metrics']
print(len(result.zones), swings['strategy_name'], swings['num_swings'], round(swings['avg_rally_pct'], 4))
print(result.metadata['swing_coverage'])
# 77 close_threshold 1 0.0046
# {'strategy': 'CloseThresholdSwingStrategy', 'zones': 77, 'zones_with_swings': 53}

analyzer = ZoneFeaturesAnalyzer(swing_strategy=CloseThresholdSwingStrategy(threshold=0.001))
zone = result.zones[3]
features = analyzer.extract_zone_features({
    'zone_id': zone.zone_id, 'type': zone.type, 'duration': zone.duration,
    'data': zone.data, 'indicator_context': zone.indicator_context,
})
print(features.metadata['swing_metrics']['num_swings'], features.metadata['swing_metrics']['strategy_params'])
# 4 {'threshold': 0.001}
```

Что здесь важно:

- **`aggregate_for_zone` обязателен для `global`-режима** (умолчание пайплайна). Стратегия
  с одним `calculate_global` отвергается `RuntimeError` при сборке — до G68 она проходила и
  давала `zones_with_swings: 0` из 77 без ошибки. `calculate()` — для `per_zone`.
- **`SwingMetrics` — все 23 поля**, `validate()` проверяет их согласованность. Нули для
  короткой зоны допустимы — ноль свингов законный результат; `result.metadata['swing_coverage']`
  показывает, сколько зон получили хоть один (G35).
- **`strategy_params` в метриках** — то, по чему потом отличают прогон от прогона.
- `indicator_context` в `zone_dict` — колонка индикатора для метрик осциллятора; без неё они
  `None`, не угадываются (G61).

### Стратегии других семейств

Тот же путь: класс с методами из таблицы, декоратор
`@StrategyRegistry.register_shape_strategy(name)` / `register_divergence_strategy` /
`register_volatility_strategy` / `register_volume_strategy`, dataclass метрик с
`validate()`. `indicator_col` приходит из контекста зоны — сохраняйте его в
`strategy_params`, это трассируемость.

```python
import pandas as pd

from bquant.analysis.zones import ZoneFeaturesAnalyzer
from bquant.analysis.zones.strategies.base import ShapeMetrics
from bquant.analysis.zones.strategies.registry import StrategyRegistry


@StrategyRegistry.register_shape_strategy('sign_share')
class SignShareShape:
    """Доля баров с положительным осциллятором вместо асимметрии; остальное — нули."""

    def calculate(self, zone_data: pd.DataFrame, indicator_col: str) -> ShapeMetrics:
        series = zone_data[indicator_col].dropna()
        metrics = ShapeMetrics(hist_skewness=float((series > 0).mean()), hist_kurtosis=0.0,
                               hist_smoothness=0.0, strategy_name='sign_share',
                               strategy_params={'indicator_col': indicator_col})
        metrics.validate()
        return metrics

    def get_metadata(self) -> dict:
        return {'strategy': 'sign_share'}


frame = pd.DataFrame({'open': [1.0, 1.1, 1.2, 1.1], 'high': [1.1, 1.2, 1.3, 1.2],
                      'low': [0.9, 1.0, 1.1, 1.0], 'close': [1.0, 1.1, 1.2, 1.1],
                      'osc': [-1.0, 0.5, 0.7, -0.2]},
                     index=pd.date_range('2024-01-01', periods=4, freq='h'))
analyzer = ZoneFeaturesAnalyzer(shape_strategy='sign_share')
features = analyzer.extract_zone_features({
    'zone_id': 0, 'type': 'bull', 'duration': 4, 'data': frame,
    'indicator_context': {'detection_strategy': 'demo', 'detection_indicator': 'osc'},
})
print(features.metadata['shape_metrics']['hist_skewness'], features.metadata['shape_metrics']['strategy_params'])
# 0.5 {'indicator_col': 'osc'}
```

Что **не** работает: стратегия без метода из таблицы — `TypeError` при создании
анализатора; попытка задать стратегию через `ANALYSIS_CONFIG` с полем `class` — такого
поля нет, конфиг знает `{'type': <имя из реестра>, 'params': {...}}`, и `create_*_strategy()`
из `bquant.core.config` резолвит имя через реестр.

Реестр: `list_*_strategies()`, `get_*_strategy(name, **params)` — возвращает **экземпляр**,
`get_registry_stats()`. Встроенных стратегий семь (три свинговых и по одной остальных) —
[strategies.md](analysis/strategies.md); их тесты — `tests/unit/test_*_strategy.py`.

## Свой график

`ChartBuilder` даёт бэкенд (`'plotly'` | `'matplotlib'`), `validate_data(data, required_columns)`
и менеджер тем `theme_manager` (`ChartThemes`); тема применяется
`apply_theme_to_figure(fig, theme_name)` — имена `bquant_light`, `bquant_dark`, `financial`,
`minimal`, `professional`; с G47 применение проверяется — фигуры разных тем различаются.

```python
import plotly.graph_objects as go
import pandas as pd

from bquant.visualization.charts import ChartBuilder


class CloseLineChart(ChartBuilder):
    def create_chart(self, data: pd.DataFrame, title: str = "Close", theme: str = "bquant_light") -> go.Figure:
        self.validate_data(data, ["close"])
        fig = go.Figure(go.Scatter(x=data.index, y=data["close"], mode="lines", name="close"))
        fig.update_layout(title=title)
        return self.theme_manager.apply_theme_to_figure(fig, theme)


frame = pd.DataFrame({"close": [1.0, 1.1, 1.05]}, index=pd.date_range("2024-01-01", periods=3, freq="h"))
light = CloseLineChart(backend="plotly").create_chart(frame, theme="bquant_light")
dark = CloseLineChart(backend="plotly").create_chart(frame, theme="bquant_dark")
print(len(light.data), light.layout.paper_bgcolor != dark.layout.paper_bgcolor)
# 1 True
```

## Свои загрузчик и обработка данных

Пакет не требует наследования: адаптер зовёт `load_ohlcv_data(...)` и функции
`bquant.data.processor` (`clean_ohlcv_data`, `resolve_time_index`, `calculate_true_range`,
`calculate_atr`, …) и отдаёт кадр с колонками `open/high/low/close[/volume]` и временем на
индексе — ровно то, что ждёт `analyze_zones()`. Контракты — [loader.md](data/loader.md),
[processor.md](data/processor.md).

## Тесты расширения

Тест обязан утверждать **поведение**, а не тип результата: `isinstance(result, X)` зелен и
на нулях. Для индикатора — значения на известном входе и отказ на коротком кадре
(`pytest.raises(DataValidationError)`); для стратегии — метрики на известной зоне и
`validate()`; для анализатора — результат на синтетике с известным ответом. Пакетные
стратегии проверяются ещё и **мутацией**: сторож обязан покраснеть, если починку откатить, —
без этого он не сторож (`devref/gaps/`).

## См. также

- [Индикаторы](indicators/README.md) · [Стратегии](analysis/strategies.md) ·
  [Пайплайн](analysis/pipeline.md) · [Визуализация](visualization/README.md)
- [Стратегии детекции зон](../developer_guide/zone_detection_strategies.md) — отдельный
  слой со своим реестром
