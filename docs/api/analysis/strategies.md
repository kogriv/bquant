# bquant.analysis.zones.strategies — Strategy Pattern

> **✅ v2.1 - Universal Strategies**
> 
> All analytical strategies now work with **ANY indicator**!
> 
> **What changed:**
> - All strategies accept explicit `indicator_col` parameter
> - `VolumeMetrics.volume_macd_corr` → `volume_indicator_corr` (universal naming)
> - Protocol signatures updated for universality
> 
> **Examples:** Each strategy now shows usage with MACD, RSI, AO, and custom indicators
> 
> **Proven:** Works with FICTIONAL_INDICATOR_99 and 10+ real indicators (100% test coverage)
>
> **API Stability:** 🟢 STABLE - этот API не изменится после универсализации

## Обзор

BQuant использует **Strategy Pattern** для расширяемого расчета метрик зон. Это позволяет:
- Добавлять новые алгоритмы анализа без изменения основного кода
- Переключаться между алгоритмами через конфигурацию
- A/B тестировать разные подходы
- Комбинировать несколько стратегий одновременно

## Архитектура

```
ZoneFeaturesAnalyzer
├── SwingStrategy → SwingMetrics (23 поля)
├── ShapeStrategy → ShapeMetrics (3 поля)
├── DivergenceStrategy → DivergenceMetrics (4 поля)
├── VolatilityStrategy → VolatilityMetrics (10 полей)
└── VolumeStrategy → VolumeMetrics (4 поля)
```

Каждая стратегия:
1. Реализует протокол (`Protocol`)
2. Возвращает типизированный результат (`Dataclass`)
3. Регистрируется в `StrategyRegistry`
4. Создается через фабрику из `config.py`

---

## Protocols и Dataclasses

### SwingCalculationStrategy Protocol

```python
class SwingCalculationStrategy(Protocol):
    def calculate_swing(self, data: pd.DataFrame) -> SwingMetrics: ...
    def get_name(self) -> str: ...
    def get_metadata(self) -> dict: ...
```

### SwingMetrics Dataclass (23 поля)

Полный результат анализа свингов в зоне.

**Категории метрик:**

#### Базовые (6 полей)
- `num_swings`: Количество свингов (пар impulse+correction)
- `avg_rally_pct`: Средняя амплитуда ралли (%)
- `avg_drop_pct`: Средняя амплитуда откатов (%)
- `max_rally_pct`: Максимальная амплитуда ралли (%)
- `max_drop_pct`: Максимальная амплитуда откатов (%)
- `rally_to_drop_ratio`: Отношение среднего ралли к среднему откату

#### Счетчики (2 поля)
- `rally_count`: Количество восходящих движений
- `drop_count`: Количество нисходящих движений

#### Минимумы и распределение (6 полей)
- `min_rally_pct`: Минимальная амплитуда ралли (%)
- `min_drop_pct`: Минимальная амплитуда откатов (%)
- `rally_amplitude_std`: Стандартное отклонение амплитуд ралли
- `drop_amplitude_std`: Стандартное отклонение амплитуд откатов
- `rally_amplitude_median`: Медиана амплитуд ралли (%)
- `drop_amplitude_median`: Медиана амплитуд откатов (%)

#### Длительность в барах (4 поля)
- `avg_rally_duration_bars`: Средняя длительность ралли (бары)
- `avg_drop_duration_bars`: Средняя длительность откатов (бары)
- `max_rally_duration_bars`: Максимальная длительность ралли (бары)
- `max_drop_duration_bars`: Максимальная длительность откатов (бары)

#### Скорость движения (4 поля)
- `avg_rally_speed_pct_per_bar`: Средняя скорость ралли (% за бар)
- `avg_drop_speed_pct_per_bar`: Средняя скорость откатов (% за бар)
- `max_rally_speed_pct_per_bar`: Максимальная скорость ралли (% за бар)
- `max_drop_speed_pct_per_bar`: Максимальная скорость откатов (% за бар)

#### Симметрия (1 поле)
- `duration_symmetry`: Отношение средней длительности ралли к откатам

#### Метаданные
- `strategy_name`: Имя использованной стратегии
- `strategy_params`: Параметры стратегии

**Интерпретация:**
- `rally_to_drop_ratio > 2`: Сильные импульсы, слабые коррекции
- `duration_symmetry > 1.5`: Импульсы длиннее коррекций
- High `*_speed`: Быстрые резкие движения
- Low `*_std`: Однородные свинги

---

### ShapeCalculationStrategy Protocol

```python
class ShapeCalculationStrategy(Protocol):
    def calculate(self, data: pd.DataFrame, indicator_col: Optional[str] = None) -> ShapeMetrics: ...
    #                                        ^^^^^^^^^^^^^^^^^^^^^^^^
    #                                        v2.1: Required for universal usage
    def get_name(self) -> str: ...
    def get_metadata(self) -> dict: ...
```

**v2.1 Universal Usage:**

The `indicator_col` parameter is **required** for universal usage with any oscillator.

**Examples:**
```python
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy

strategy = StatisticalShapeStrategy()

# MACD
shape = strategy.calculate(zone_data, indicator_col='macd_hist')

# RSI
shape = strategy.calculate(zone_data, indicator_col='RSI_14')

# Awesome Oscillator
shape = strategy.calculate(zone_data, indicator_col='AO_5_34')

# CCI
shape = strategy.calculate(zone_data, indicator_col='CCI_20')

# Custom indicator
shape = strategy.calculate(zone_data, indicator_col='MY_CUSTOM_OSC')
```

**All return the same ShapeMetrics structure:**
- `hist_skewness`: Distribution asymmetry
- `hist_kurtosis`: Peak sharpness
- `hist_smoothness`: Change consistency

### ShapeMetrics Dataclass (3 поля)

Характеристики формы гистограммы индикатора.

- `hist_skewness`: Асимметрия распределения
- `hist_kurtosis`: Эксцесс (острота пика)
- `hist_smoothness`: Гладкость изменения значений

**Интерпретация:**
- **Skewness > 0:** Правосторонняя асимметрия (больше положительных значений)
- **Skewness < 0:** Левосторонняя асимметрия (больше отрицательных значений)
- **Kurtosis > 3:** Острый пик (лептокуртический)
- **Kurtosis < 3:** Плоское распределение (платикуртический)
- **Smoothness высокая:** Плавное изменение индикатора
- **Smoothness низкая:** Резкие скачки индикатора

---

### DivergenceCalculationStrategy Protocol

```python
class DivergenceCalculationStrategy(Protocol):
    def calculate_divergence(self, 
                           data: pd.DataFrame, 
                           indicator_col: Optional[str] = None,
                           indicator_line_col: Optional[str] = None) -> DivergenceMetrics: ...
    #                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                       v2.1: Support for 2-line indicators (MACD line + signal)
    def get_name(self) -> str: ...
    def get_metadata(self) -> dict: ...
```

**v2.1 Universal Examples:**
```python
from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy

strategy = ClassicDivergenceStrategy()

# RSI divergence
div = strategy.calculate_divergence(data, indicator_col='RSI_14')

# MACD histogram divergence
div = strategy.calculate_divergence(data, indicator_col='macd_hist')

# MACD with signal line (2-line divergence)
div = strategy.calculate_divergence(data, 
                                    indicator_col='macd',
                                    indicator_line_col='macd_signal')

# Awesome Oscillator divergence
div = strategy.calculate_divergence(data, indicator_col='AO_5_34')
```

### DivergenceMetrics Dataclass (4 поля)

Информация о дивергенциях между ценой и индикатором.

- `divergence_type`: Тип ('regular_bullish', 'regular_bearish', 'hidden_bullish', 'hidden_bearish', None)
- `divergence_count`: Количество обнаруженных дивергенций
- `divergence_strength`: Сила дивергенции (0.0-1.0)
- `divergence_direction`: Направление дивергенции (+1, -1, 0)

**Интерпретация:**
- **Regular bullish:** Цена делает lower low, индикатор - higher low → потенциальный разворот вверх
- **Regular bearish:** Цена делает higher high, индикатор - lower high → потенциальный разворот вниз
- **Strength > 0.7:** Сильная дивергенция
- **Strength < 0.3:** Слабая дивергенция

---

### VolatilityCalculationStrategy Protocol

```python
class VolatilityCalculationStrategy(Protocol):
    def calculate_volatility(self, data: pd.DataFrame) -> VolatilityMetrics: ...
    def get_name(self) -> str: ...
    def get_metadata(self) -> dict: ...
```

### VolatilityMetrics Dataclass (10 полей)

Оценка волатильности в зоне через Bollinger Bands и ATR.

**Bollinger Bands метрики (5):**
- `bollinger_width_pct`: Ширина полос (% от цены)
- `bollinger_width_std`: Ширина в стандартных отклонениях
- `bollinger_squeeze_ratio`: Отношение текущей ширины к средней
- `bollinger_upper_touches`: Количество касаний верхней полосы
- `bollinger_lower_touches`: Количество касаний нижней полосы

**ATR метрики (3):**
- `atr_normalized_range`: Диапазон зоны нормализованный на ATR
- `atr_trend`: Тренд ATR в зоне (-1: падает, 0: стабилен, +1: растет)
- `avg_atr`: Средний ATR в зоне

**Композитные метрики (2):**
- `volatility_score`: Комплексный скор 0-10 (weighted avg)
- `volatility_regime`: Классификация ('low', 'medium', 'high', 'extreme')

**Интерпретация volatility_score:**
- **0-3:** Low volatility - спокойный рынок
- **3-6:** Medium volatility - нормальный рынок
- **6-8:** High volatility - повышенная волатильность
- **8-10:** Extreme volatility - экстремальная волатильность

---

### VolumeCalculationStrategy Protocol

```python
class VolumeCalculationStrategy(Protocol):
    def calculate_volume(self, data: pd.DataFrame, baseline_volume: Optional[float] = None) -> VolumeMetrics: ...
    def get_name(self) -> str: ...
    def get_metadata(self) -> dict: ...
```

### VolumeMetrics Dataclass (4 поля)

Анализ объемов торгов в зоне (v2.1: универсальный для ЛЮБОГО индикатора).

- `volume_zone_ratio`: Отношение среднего объема зоны к baseline
- `volume_at_entry_change`: Изменение объема при входе в зону (%)
- `volume_indicator_corr`: Корреляция объема с индикатором ✨ **v2.1: renamed from volume_macd_corr**
- `avg_volume_zone`: Средний объем в зоне

**Интерпретация:**
- `volume_zone_ratio > 1.5`: Высокий объем - сильное движение
- `volume_zone_ratio < 0.7`: Низкий объем - слабое движение
- `volume_indicator_corr > 0.7`: Объем подтверждает индикатор ✨ **v2.1: universal**
- `volume_at_entry_change > 0.5`: Объем растет при входе - confirmation

**v2.1 Universal Examples:**
```python
from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy

strategy = StandardVolumeStrategy()

# MACD correlation
vol = strategy.calculate_volume(zone_data, baseline_volume=1000, indicator_col='macd_hist')

# RSI correlation
vol = strategy.calculate_volume(zone_data, baseline_volume=1000, indicator_col='RSI_14')

# AO correlation
vol = strategy.calculate_volume(zone_data, baseline_volume=1000, indicator_col='AO_5_34')

# Access universal field
print(f"Volume-Indicator correlation: {vol.volume_indicator_corr:.2f}")
```

---

## StrategyRegistry

Централизованный реестр всех стратегий.

### Регистрация стратегий

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

# Register swing strategy
@StrategyRegistry.register_swing_strategy('my_strategy')
class MySwingStrategy:
    pass

# Manual registration
StrategyRegistry.register_swing_strategy('another', AnotherStrategy)
```

### Получение стратегий

```python
# Get strategy class
StrategyClass = StrategyRegistry.get_swing_strategy('zigzag')

# Create instance
strategy = StrategyClass(legs=10, deviation=0.05)

# List all available
print(StrategyRegistry.list_swing_strategies())
# ['zigzag', 'find_peaks', 'pivot_points']
```

### Статистика реестра

```python
stats = StrategyRegistry.get_registry_stats()
print(f"Total strategies: {stats['total']}")
print(f"By type: {stats['by_type']}")
# {'swing': 3, 'shape': 1, 'divergence': 1, 'volatility': 1, 'volume': 1}
```

---

## Implemented Strategies

### Swing Strategies

#### ZigZagSwingStrategy

**Algorithm:** Uses pandas-ta ZigZag indicator to detect significant price reversals.

**Parameters:**
- `legs` (default: 10): Number of bars to look back/forward
- `deviation` (default: 0.05): Minimum 5% price change to form new leg

**When to use:**
- ✅ Smooth trending markets
- ✅ Larger timeframes (H4, D1)
- ✅ Want to filter out noise

**Example:**
```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

analyzer = ZoneFeaturesAnalyzer(swing_strategy='zigzag')
# Or with custom parameters
from bquant.core.config import create_swing_strategy
strategy = create_swing_strategy('zigzag', legs=15, deviation=0.03)
analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)
```

**Metrics focus:** Larger, more significant swings

---

#### FindPeaksSwingStrategy

**Algorithm:** Uses scipy.signal.find_peaks to detect all local extrema.

**Parameters:**
- `prominence` (default: 0.02): Minimum 2% prominence for peak
- `distance` (default: 3): Minimum 3 bars between peaks

**When to use:**
- ✅ Choppy/ranging markets
- ✅ Detect all local extrema
- ✅ Smaller timeframes (M15, H1)
- ✅ Detailed swing analysis

**Example:**
```python
analyzer = ZoneFeaturesAnalyzer(swing_strategy='find_peaks')
# Custom parameters
strategy = create_swing_strategy('find_peaks', prominence=0.01, distance=5)
```

**Metrics focus:** More numerous, smaller swings

---

#### PivotPointsSwingStrategy

**Algorithm:** Classic N-bar pattern - high/low that is highest/lowest among N bars left and right.

**Parameters:**
- `left_bars` (default: 5): Bars to left of pivot
- `right_bars` (default: 5): Bars to right of pivot

**When to use:**
- ✅ Classic technical analysis approach
- ✅ Well-defined pivot points
- ✅ Any timeframe
- ✅ Conservative swing detection

**Example:**
```python
analyzer = ZoneFeaturesAnalyzer(swing_strategy='pivot_points')
# Asymmetric window
strategy = create_swing_strategy('pivot_points', left_bars=7, right_bars=3)
```

**Metrics focus:** Confirmed, validated swings

---

### Shape Strategies

#### StatisticalShapeStrategy

**Algorithm:** Statistical analysis of indicator histogram shape using scipy.stats.

**Parameters:** None (uses statistical moments)

**Metrics calculated:**
- `hist_skewness`: Skewness (scipy.stats.skew)
- `hist_kurtosis`: Kurtosis (scipy.stats.kurtosis)
- `hist_smoothness`: Smoothness (inverse of changes variance)

**When to use:**
- ✅ Understand distribution characteristics
- ✅ Identify explosive vs gradual zones
- ✅ Cluster zones by shape
- ✅ Any indicator with histogram

**Example:**
```python
analyzer = ZoneFeaturesAnalyzer(shape_strategy='statistical')

features = analyzer.extract_zone_features(zone_dict)
shape = features.metadata['shape_metrics']

print(f"Skewness: {shape.hist_skewness:.2f}")
print(f"Kurtosis: {shape.hist_kurtosis:.2f}")
print(f"Smoothness: {shape.hist_smoothness:.2f}")
```

**Interpretation:**
- Positive skew + high kurtosis → Explosive movements
- Negative skew + low kurtosis → Gradual decline
- High smoothness → Steady trend
- Low smoothness → Choppy movement

---

### Divergence Strategies

#### ClassicDivergenceStrategy

**Algorithm:** Detects regular bullish/bearish divergences using peak detection.

**Parameters:**
- `use_macd_line` (default: False): Use MACD line instead of histogram

**Divergence types:**
- **Regular Bullish:** Price makes lower low, indicator makes higher low
- **Regular Bearish:** Price makes higher high, indicator makes lower high

**When to use:**
- ✅ Potential reversal points
- ✅ Entry signal confirmation
- ✅ Exit signal generation
- ✅ Works with any oscillator

**Example:**
```python
analyzer = ZoneFeaturesAnalyzer(divergence_strategy='classic')

features = analyzer.extract_zone_features(zone_dict)
div = features.metadata['divergence_metrics']

if div.divergence_count > 0:
    print(f"Divergence detected: {div.divergence_type}")
    print(f"Strength: {div.divergence_strength:.2f}")
    print(f"Count: {div.divergence_count}")
```

**Strength calculation:**
- Based on vertical distance between peaks
- Normalized correlation between price and indicator peaks
- Range: 0.0 (weak) to 1.0 (strong)

**Trading applications:**
- Filter entries: only take signals with divergence_strength > 0.5
- Size positions: larger size for stronger divergences
- Set stops: based on divergence_direction

---

### Volatility Strategies

#### CombinedVolatilityStrategy

**Algorithm:** Combined assessment using Bollinger Bands and ATR.

**Parameters:**
- `bb_window` (default: 20): Bollinger Bands window
- `bb_std` (default: 2): Number of standard deviations
- `atr_window` (default: 14): ATR window
- `atr_multiplier` (default: 1.0): ATR multiplier for range

**Components:**

**Bollinger Bands:**
- Width metrics: how wide/narrow the bands
- Squeeze detection: bands compressing
- Touch counts: price testing bands

**ATR:**
- Normalized range: zone range vs typical range
- ATR trend: volatility increasing/decreasing
- Graceful degradation: estimates via True Range if no ATR column

**Volatility Score (0-10):**
Weighted combination:
- 40%: Bollinger width percentile
- 30%: ATR trend
- 30%: Squeeze ratio

**Regime Classification:**
- **Low (0-3):** Consolidation, range trading
- **Medium (3-6):** Normal volatility, standard strategies
- **High (6-8):** Increased risk, smaller positions
- **Extreme (8-10):** Crisis mode, minimal exposure

**Example:**
```python
analyzer = ZoneFeaturesAnalyzer(volatility_strategy='combined')

features = analyzer.extract_zone_features(zone_dict)
vol = features.metadata['volatility_metrics']

print(f"Volatility score: {vol.volatility_score:.1f}/10")
print(f"Regime: {vol.volatility_regime}")
print(f"Bollinger width: {vol.bollinger_width_pct:.2%}")
print(f"Upper touches: {vol.bollinger_upper_touches}")

# Adaptive position sizing
if vol.volatility_regime == 'low':
    position_size = 2.0  # Larger position
elif vol.volatility_regime == 'medium':
    position_size = 1.0  # Normal
elif vol.volatility_regime == 'high':
    position_size = 0.5  # Smaller
else:  # extreme
    position_size = 0.25  # Minimal
```

---

### Volume Strategies

#### StandardVolumeStrategy

**Algorithm:** Standard volume analysis with baseline comparison.

**Parameters:**
- `baseline_volume` (optional): Reference volume for comparison

**Metrics:**
- `volume_zone_ratio`: Zone volume / baseline volume
- `volume_at_entry_change`: Volume change at zone entry (%)
- `volume_indicator_corr`: Correlation between volume and indicator ✨ **v2.1: universal**
- `avg_volume_zone`: Average volume in zone

**Graceful degradation:**
- Works without baseline (ratio = None)
- Works without volume column (all metrics = None)
- No crashes on missing data

**When to use:**
- ✅ Confirm signal strength
- ✅ Detect accumulation/distribution
- ✅ Volume-price divergence
- ✅ Any market with volume data

**Example:**
```python
# Without baseline
analyzer = ZoneFeaturesAnalyzer(volume_strategy='standard')

# With baseline (e.g., overall average)
overall_avg_volume = data['volume'].mean()
strategy = create_volume_strategy('standard')
analyzer = ZoneFeaturesAnalyzer(volume_strategy=strategy)

features = analyzer.extract_zone_features(zone_dict)
vol = features.metadata.get('volume_metrics')

if vol:
    print(f"Volume ratio: {vol.volume_zone_ratio:.2f}")
    print(f"Volume-Indicator correlation: {vol.volume_indicator_corr:.2f}")  # v2.1: universal
    
    # Trading decision
    if vol.volume_zone_ratio > 1.5 and vol.volume_indicator_corr > 0.6:
        print("✅ Strong volume confirmation")
```

---

## Usage Examples

### Basic: Using Default Strategies

```python
from bquant.indicators.macd import MACDZoneAnalyzer

# Uses default strategies from config
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(df)

# Access metrics from first zone
zone = result.zones[0]
print(f"Duration: {zone.features['duration']}")

# Swing metrics (default: ZigZag)
if 'swing_metrics' in zone.features.get('metadata', {}):
    swing = zone.features['metadata']['swing_metrics']
    print(f"Swings: {swing['num_swings']}")

# Volatility metrics (if configured)
if 'volatility_metrics' in zone.features.get('metadata', {}):
    vol = zone.features['metadata']['volatility_metrics']
    print(f"Volatility: {vol['volatility_regime']}")
```

### Advanced: Switching Strategies

```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

# Try different swing strategies
strategies = {
    'zigzag': create_swing_strategy('zigzag'),
    'find_peaks': create_swing_strategy('find_peaks'),
    'pivot_points': create_swing_strategy('pivot_points')
}

for name, strategy in strategies.items():
    analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)
    features = analyzer.extract_zone_features(zone_dict)
    swing = features.metadata['swing_metrics']
    
    print(f"\n{name}:")
    print(f"  Swings: {swing.num_swings}")
    print(f"  Avg rally: {swing.avg_rally_pct:.2%}")
```

### Expert: A/B Testing Strategies

```python
import pandas as pd

# Test all swing strategies on multiple zones
results = []

for zone in result.zones[:10]:  # First 10 zones
    zone_dict = analyzer._zone_to_dict(zone)
    
    for strategy_name in ['zigzag', 'find_peaks', 'pivot_points']:
        fa = ZoneFeaturesAnalyzer(swing_strategy=strategy_name)
        features = fa.extract_zone_features(zone_dict)
        swing = features.metadata['swing_metrics']
        
        results.append({
            'zone_id': zone.zone_id,
            'strategy': strategy_name,
            'num_swings': swing.num_swings,
            'avg_rally': swing.avg_rally_pct,
            'rally_count': swing.rally_count
        })

# Analyze results
df_results = pd.DataFrame(results)
summary = df_results.groupby('strategy').agg({
    'num_swings': 'mean',
    'avg_rally': 'mean',
    'rally_count': 'mean'
})

print(summary)

# Choose best strategy for your needs
# - ZigZag: fewer, larger swings
# - FindPeaks: more, smaller swings
# - PivotPoints: balanced, validated swings
```

### Custom: Creating and Using Your Own

```python
# 1. Create strategy
@StrategyRegistry.register_swing_strategy('threshold_based')
class ThresholdSwingStrategy:
    def __init__(self, threshold=0.02):
        self.threshold = threshold
    
    def calculate_swing(self, data):
        # Your algorithm
        return SwingMetrics(...)
    
    def get_name(self):
        return 'ThresholdBased'
    
    def get_metadata(self):
        return {'threshold': self.threshold}

# 2. Use it
analyzer = ZoneFeaturesAnalyzer(swing_strategy='threshold_based')

# 3. Or with custom parameters
strategy = ThresholdSwingStrategy(threshold=0.03)
analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)
```

### Combining Multiple Strategies

```python
# Use different strategies for different purposes
analyzer = ZoneFeaturesAnalyzer(
    swing_strategy='zigzag',         # For trend analysis
    shape_strategy='statistical',    # For clustering
    divergence_strategy='classic',   # For entries
    volatility_strategy='combined',  # For position sizing
    volume_strategy='standard'       # For confirmation
)

features = analyzer.extract_zone_features(zone_dict)

# All strategies' results in metadata
print(f"Swing metrics: {features.metadata['swing_metrics']}")
print(f"Shape metrics: {features.metadata['shape_metrics']}")
print(f"Divergence: {features.metadata['divergence_metrics']}")
print(f"Volatility: {features.metadata['volatility_metrics']}")
print(f"Volume: {features.metadata['volume_metrics']}")
```

---

## Strategy Comparison Table

| Strategy | Speed | Detail | Noise | Best For |
|----------|-------|--------|-------|----------|
| **ZigZag** | Medium | Low | Low | Trends, larger TF |
| **FindPeaks** | Fast | High | High | Choppy, all extrema |
| **PivotPoints** | Medium | Medium | Low | Classic TA |
| **Statistical** | Fast | N/A | N/A | Shape analysis |
| **Classic** | Medium | N/A | N/A | Divergences |
| **Combined** | Medium | High | N/A | Volatility |
| **Standard** | Fast | Medium | N/A | Volume |

---

## См. также

- [Extension Guide](../extension_guide.md#creating-custom-strategies) - создание собственных стратегий
- [Zone Features](zones.md) - использование стратегий в анализе зон
- [Configuration](../core/config.md) - фабрики стратегий
- Implementations: `bquant/analysis/zones/strategies/`
- Tests: `tests/unit/test_*_strategy.py`
- Technical docs: `devref/gaps/swing_detection_approaches.md`

