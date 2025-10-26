# Руководство по расширению API BQuant

## 📚 Обзор

Это руководство поможет вам расширить функциональность BQuant, создавая собственные индикаторы, анализаторы, визуализации и модули данных.

## 🎯 Принципы расширения

### Модульность
- Каждый новый компонент должен быть независимым
- Используйте интерфейсы и абстрактные классы
- Минимизируйте зависимости между модулями

### Совместимость
- Следуйте существующим паттернам API
- Используйте стандартные типы данных
- Поддерживайте обратную совместимость

### Производительность
- Используйте NumPy для вычислений
- Оптимизируйте для больших данных
- Применяйте кэширование где возможно

## 🏗️ Создание собственного индикатора

### Шаг 1: Наследование от BaseIndicator

```python
from bquant.indicators.base import (
    BaseIndicator,
    CustomIndicator as BQuantCustomIndicator,
    IndicatorResult,
    IndicatorSource,
)
import pandas as pd
import numpy as np


class CustomIndicator(BQuantCustomIndicator):
    """Кастомный индикатор"""

    def __init__(self, param1=10, param2=20):
        parameters = {
            "param1": param1,
            "param2": param2,
        }
        # Наследуемся от BQuant CustomIndicator, чтобы фабрика могла создавать экземпляры
        super().__init__("CustomIndicator", parameters)
        self.params = self.config.parameters

    def get_output_columns(self):
        return ["custom_indicator"]

    def get_description(self):
        return "Документированный пример пользовательского индикатора"

    def get_required_columns(self):
        return ["close", "volume"]

    def calculate(self, data):
        """Расчет индикатора"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for CustomIndicator")

        # Ваша логика расчета
        result = self._calculate_indicator(data)
        result_frame = pd.DataFrame({"custom_indicator": result}, index=data.index)

        return IndicatorResult(
            name=self.name,
            data=result_frame,
            config=self.config,
            metadata={"calculated_at": pd.Timestamp.utcnow()},
        )

    def _calculate_indicator(self, data):
        """Внутренний метод расчета"""
        param1 = self.params["param1"]
        param2 = self.params["param2"]

        # Пример расчета
        indicator = (data["close"] * data["volume"]).rolling(window=param1, min_periods=1).mean()
        return indicator / max(param2, 1)
```

### Шаг 2: Регистрация в фабрике

```python
from bquant.indicators.base import IndicatorFactory

# Регистрация индикатора (обновленный API v2.1 использует классовые методы)
IndicatorFactory.register_indicator("custom_indicator", CustomIndicator)

# Использование
indicator = IndicatorFactory.create('custom', 'custom_indicator', param1=15, param2=25)
result = indicator.calculate(data)
```

## 🔬 Создание собственного анализатора

### Шаг 1: Наследование от BaseAnalyzer

```python
from bquant.analysis import BaseAnalyzer, AnalysisResult
import numpy as np


class CustomAnalyzer(BaseAnalyzer):
    """Кастомный анализатор"""

    def __init__(self, analysis_type='default'):
        super().__init__('CustomAnalyzer', {'analysis_type': analysis_type})
        self.params = self.config  # сохраняем ссылку, как в исходном примере

    def analyze(self, data):
        """Выполнение анализа"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for CustomAnalyzer")

        # Ваша логика анализа
        analysis_result = self._perform_analysis(data)

        return AnalysisResult(
            analysis_type=self.params['analysis_type'],
            results=analysis_result['statistics'],
            data_size=len(data),
            metadata={'series_tail': analysis_result['data'].tail(5).to_dict()}
        )

    def validate_data(self, data):
        """Валидация данных"""
        return len(data) > 0 and 'close' in data.columns

    def _perform_analysis(self, data):
        """Внутренний метод анализа"""
        analysis_type = self.params['analysis_type']

        if analysis_type == 'volatility':
            result = self._analyze_volatility(data)
        elif analysis_type == 'trend':
            result = self._analyze_trend(data)
        else:
            result = self._analyze_default(data)

        return result

    def _analyze_volatility(self, data):
        """Анализ волатильности"""
        returns = data['close'].pct_change().fillna(0)
        volatility = returns.rolling(window=20, min_periods=5).std().fillna(0)

        return {
            'data': volatility,
            'statistics': {
                'mean_volatility': float(volatility.mean()),
                'max_volatility': float(volatility.max()),
                'current_volatility': float(volatility.iloc[-1])
            }
        }
```

### Шаг 2: Интеграция с системой

```python
# Использование анализатора
analyzer = CustomAnalyzer(analysis_type='volatility')
result = analyzer.analyze(data)

print(f"Mean volatility: {result.results['mean_volatility']:.4f}")
```

## 🎨 Creating Custom Strategies (New in Phase 3)

> **API Stability:** 🟢 STABLE - Strategy Pattern API is finalized

### Overview

BQuant uses Strategy Pattern for extensible metrics calculation. You can create custom strategies without modifying core analyzers.

**Benefits:**
- Add new metrics without changing `ZoneFeaturesAnalyzer`
- Switch algorithms via configuration
- A/B test different approaches
- Maintain multiple strategies simultaneously

### Strategy Types

| Strategy Type | Purpose | Protocol |
|---------------|---------|----------|
| **SwingCalculationStrategy** | Detect swings/impulses in price movement | 23 metrics |
| **ShapeCalculationStrategy** | Analyze indicator histogram shape | 3 metrics |
| **DivergenceCalculationStrategy** | Detect price-indicator divergences | 4 metrics |
| **VolatilityCalculationStrategy** | Measure market volatility | 10 metrics |
| **VolumeCalculationStrategy** | Analyze volume patterns | 4 metrics |

### Step-by-Step: Creating a Custom Swing Strategy

#### Step 1: Import Protocol and Dataclass

```python
from bquant.analysis.zones.strategies.base import (
    SwingCalculationStrategy,
    SwingMetrics
)
from bquant.analysis.zones.strategies.registry import StrategyRegistry
import pandas as pd
import numpy as np
```

#### Step 2: Implement Strategy Class

```python
class MyCustomSwingStrategy:
    """My custom swing detection algorithm."""

    def __init__(self, threshold: float = 0.02):
        """
        Initialize strategy.
        
        Args:
            threshold: Minimum price movement to consider as swing (e.g., 0.02 = 2%)
        """
        self.threshold = threshold

    def calculate_swings(self, data: pd.DataFrame) -> SwingMetrics:
        """
        Calculate swing metrics.

        Args:
            data: DataFrame with OHLC columns (high, low, close)
            
        Returns:
            SwingMetrics with all 23 fields populated
        """
        if len(data) < 3:
            # Graceful degradation for short zones
            return self._empty_metrics()

        # Your algorithm here (упрощенная реализация для документации)
        price = data['close']
        returns = price.pct_change().fillna(0)
        rallies = returns[returns >= self.threshold]
        drops = -returns[returns <= -self.threshold]

        rally_stats = self._stats(rallies)
        drop_stats = self._stats(drops)

        duration = max(len(data), 1)
        rally_speed = rally_stats['avg'] / duration if duration else 0.0
        drop_speed = drop_stats['avg'] / duration if duration else 0.0

        metrics = SwingMetrics(
            num_swings=rally_stats['count'] + drop_stats['count'],
            avg_rally_pct=rally_stats['avg'],
            avg_drop_pct=drop_stats['avg'],
            max_rally_pct=rally_stats['max'],
            max_drop_pct=drop_stats['max'],
            rally_to_drop_ratio=(rally_stats['avg'] / drop_stats['avg']) if drop_stats['avg'] else 1.0,
            rally_count=rally_stats['count'],
            drop_count=drop_stats['count'],
            min_rally_pct=rally_stats['min'],
            min_drop_pct=drop_stats['min'],
            rally_amplitude_std=rally_stats['std'],
            drop_amplitude_std=drop_stats['std'],
            rally_amplitude_median=rally_stats['median'],
            drop_amplitude_median=drop_stats['median'],
            avg_rally_duration_bars=rally_stats['duration'],
            avg_drop_duration_bars=drop_stats['duration'],
            max_rally_duration_bars=rally_stats['max_duration'],
            max_drop_duration_bars=drop_stats['max_duration'],
            avg_rally_speed_pct_per_bar=rally_speed,
            avg_drop_speed_pct_per_bar=drop_speed,
            max_rally_speed_pct_per_bar=rally_stats['max_speed'],
            max_drop_speed_pct_per_bar=drop_stats['max_speed'],
            duration_symmetry=(rally_stats['duration'] / drop_stats['duration']) if drop_stats['duration'] else 1.0,
            strategy_name='MyCustomSwing',
            strategy_params={'threshold': self.threshold}
        )

        metrics.validate()
        return metrics

    def calculate(self, data: pd.DataFrame) -> SwingMetrics:
        """Совместимость с ZoneFeaturesAnalyzer (ожидает метод calculate)."""
        return self.calculate_swings(data)

    def _stats(self, series: pd.Series) -> dict:
        if series.empty:
            return {
                'count': 0,
                'avg': 0.0,
                'max': 0.0,
                'min': 0.0,
                'std': 0.0,
                'median': 0.0,
                'duration': 0.0,
                'max_duration': 0,
                'max_speed': 0.0,
            }

        durations = max(1, len(series))
        return {
            'count': int(series.count()),
            'avg': float(series.mean()),
            'max': float(series.max()),
            'min': float(series.min()),
            'std': float(series.std(ddof=0)) if series.count() > 1 else 0.0,
            'median': float(series.median()),
            'duration': float(durations / max(series.count(), 1)),
            'max_duration': int(durations),
            'max_speed': float(series.max()),
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
            strategy_name='MyCustomSwing',
            strategy_params={'threshold': self.threshold}
        )

    def get_metadata(self) -> dict:
        return {
            'strategy': 'MyCustomSwing',
            'threshold': self.threshold,
            'algorithm': 'Custom threshold-based swing detection'
        }
    
    def get_name(self) -> str:
        """Return strategy name."""
        return 'MyCustomSwing'
    
    def get_metadata(self) -> dict:
        """Return strategy metadata."""
        return {
            'strategy': 'MyCustomSwing',
            'threshold': self.threshold,
            'algorithm': 'Custom threshold-based swing detection',
            'description': 'Detects swings when price movement exceeds threshold'
        }
```

#### Step 3: Register Strategy

```python
# Option A: Using decorator (recommended)
@StrategyRegistry.register_swing_strategy('my_custom')
class MyCustomSwingStrategy:
    # ... implementation ...
    pass

# Option B: Manual registration
StrategyRegistry.register_swing_strategy('my_custom')(MyCustomSwingStrategy)

# Verify registration
print(StrategyRegistry.list_swing_strategies())
# Output: ['zigzag', 'find_peaks', 'pivot_points', 'my_custom']
```

#### Step 4: Use Strategy

```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

# By name (from registry)
analyzer = ZoneFeaturesAnalyzer(swing_strategy='my_custom')

# By instance (with custom parameters)
strategy = MyCustomSwingStrategy(threshold=0.03)
analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)

# Extract features
features = analyzer.extract_zone_features(zone_dict)

# Access swing metrics
swing_metrics = features.metadata['swing_metrics']
print(f"Swings detected: {swing_metrics['num_swings']}")
print(f"Avg rally: {swing_metrics['avg_rally_pct']:.2%}")
print(f"Strategy used: {swing_metrics['strategy_name']}")
```

### Creating Other Strategy Types

The process is identical for other strategy types. Just change the protocol and dataclass:

#### Shape Strategy Example

```python
from typing import Optional
from bquant.analysis.zones.strategies.base import ShapeCalculationStrategy, ShapeMetrics

@StrategyRegistry.register_shape_strategy('my_shape')
class MyShapeStrategy:
    def calculate_shape(self, data: pd.DataFrame, indicator_col: Optional[str] = None) -> ShapeMetrics:
        """
        Calculate shape metrics for ANY oscillator (v2.1 universal).
        
        Args:
            data: Zone data with OHLCV + oscillator columns
            indicator_col: Oscillator column name (e.g., 'RSI_14', 'AO_5_34', 'MY_OSC')
                          If None, strategy should auto-detect or raise error
        
        Returns:
            ShapeMetrics with calculated shape characteristics
        
        Examples:
            # Works with ANY oscillator
            metrics = strategy.calculate_shape(data, indicator_col='RSI_14')
            metrics = strategy.calculate_shape(data, indicator_col='macd_hist')
            metrics = strategy.calculate_shape(data, indicator_col='CUSTOM_OSC')
        """
        if indicator_col is None or indicator_col not in data.columns:
            raise ValueError(f"indicator_col required and must exist in data")
        
        # Your universal implementation (works with ANY column!)
        oscillator = data[indicator_col]
        
        # Calculate skewness, kurtosis, smoothness for your indicator
        hist_skewness = oscillator.skew()
        hist_kurtosis = oscillator.kurtosis()
        hist_smoothness = 1.0 - oscillator.diff().abs().mean() / oscillator.abs().mean()
        
        metrics = ShapeMetrics(
            hist_skewness=hist_skewness,
            hist_kurtosis=hist_kurtosis,
            hist_smoothness=hist_smoothness,
            strategy_name='MyShape',
            strategy_params={'indicator_col': indicator_col}  # ← Track which indicator used
        )

        metrics.validate()
        return metrics

    def calculate(self, data: pd.DataFrame, indicator_col: Optional[str] = None) -> ShapeMetrics:
        """Совместимость с ZoneFeaturesAnalyzer (ожидает метод calculate)."""
        return self.calculate_shape(data, indicator_col=indicator_col)

    def get_name(self) -> str:
        return 'MyShape'

    def get_metadata(self) -> dict:
        return {'strategy': 'MyShape', 'algorithm': 'Custom shape analysis'}
```

**v2.1 Best Practice:** Always track `indicator_col` in `strategy_params` for traceability!

#### Divergence Strategy Example

```python
from typing import Optional
from bquant.analysis.zones.strategies.base import DivergenceCalculationStrategy, DivergenceMetrics

@StrategyRegistry.register_divergence_strategy('my_divergence')
class MyDivergenceStrategy:
    def calculate_divergence(self, 
                           data: pd.DataFrame, 
                           indicator_col: Optional[str] = None,
                           indicator_line_col: Optional[str] = None) -> DivergenceMetrics:
        """
        Calculate divergence for ANY oscillator (v2.1 universal).
        
        Args:
            data: Zone data with OHLCV + oscillator columns
            indicator_col: Primary oscillator column (e.g., 'RSI_14', 'macd_hist')
            indicator_line_col: Secondary line for 2-line indicators (e.g., 'macd_signal')
        
        Returns:
            DivergenceMetrics with divergence information
        
        Examples:
            # Single-line oscillator (RSI, AO)
            metrics = strategy.calculate_divergence(data, indicator_col='RSI_14')
            
            # 2-line indicator (MACD with signal)
            metrics = strategy.calculate_divergence(data, 
                                                   indicator_col='macd',
                                                   indicator_line_col='macd_signal')
        """
        if indicator_col is None or indicator_col not in data.columns:
            raise ValueError(f"indicator_col required and must exist in data")
        
        # Your universal implementation (works with ANY oscillator!)
        oscillator = data[indicator_col]
        price = data['close']
        
        # Detect divergences between price and indicator
        # ... your divergence logic here ...

        metrics = DivergenceMetrics(
            divergence_type='regular',  # or 'hidden', 'mixed', 'none'
            divergence_count=1,
            divergence_strength=0.75,
            divergence_direction='bullish',
            strategy_name='MyDivergence',
            strategy_params={
                'indicator_col': indicator_col,              # ← Track primary indicator
                'indicator_line_col': indicator_line_col     # ← Track signal line (if any)
            }
        )

        metrics.validate()
        return metrics
    
    def get_name(self) -> str:
        return 'MyDivergence'
    
    def get_metadata(self) -> dict:
        return {'strategy': 'MyDivergence', 'supports_2line': True}
```

**v2.1 Best Practice:** Track both `indicator_col` and `indicator_line_col` (if applicable) in `strategy_params`!

### Testing Your Strategy

```python
import numpy as np
import pandas as pd
import pytest

def test_my_custom_strategy():
    """Unit test for custom strategy."""
    strategy = MyCustomSwingStrategy(threshold=0.02)
    
    # Create test data
    dates = pd.date_range('2024-01-01', periods=50, freq='1h')
    data = pd.DataFrame({
        'high': np.random.randn(50).cumsum() + 2000,
        'low': np.random.randn(50).cumsum() + 1990,
        'close': np.random.randn(50).cumsum() + 1995
    }, index=dates)
    
    # Calculate swing metrics
    result = strategy.calculate_swings(data)
    
    # Validate contract (all required fields present)
    assert isinstance(result, SwingMetrics)
    assert result.num_swings >= 0
    assert result.rally_count >= 0
    assert result.drop_count >= 0
    assert result.strategy_name == 'MyCustomSwing'
    assert 'threshold' in result.strategy_params
    
    # Validate data quality
    if result.num_swings > 0:
        assert result.avg_rally_pct >= 0
        assert result.avg_drop_pct >= 0
        assert result.rally_to_drop_ratio > 0
```

### Integration Testing

```python
def test_strategy_with_analyzer():
    """Test strategy integration with ZoneFeaturesAnalyzer."""
    from bquant.analysis.zones import ZoneFeaturesAnalyzer
    
    analyzer = ZoneFeaturesAnalyzer(swing_strategy='my_custom')
    
    zone_dict = {
        'zone_id': 'test_1',
        'type': 'bull',
        'duration': 20,
        'data': data  # your test data
    }
    
    features = analyzer.extract_zone_features(zone_dict)
    
    # Verify swing metrics present
    assert 'swing_metrics' in features.metadata
    assert features.metadata['swing_metrics'].strategy_name == 'MyCustomSwing'
```

### Best Practices

#### 1. Graceful Degradation

Handle edge cases gracefully:

```python
def calculate_swings(self, data: pd.DataFrame) -> SwingMetrics:
    # Check data sufficiency
    if len(data) < self.min_required_length:
        return self._empty_metrics()  # Return zeros
    
    # Check required columns
    required_cols = ['high', 'low', 'close']
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"Missing required columns: {required_cols}")
    
    # Your algorithm...
```

#### 2. Meaningful Metadata

Always record strategy configuration:

```python
def get_metadata(self) -> dict:
    return {
        'strategy': self.get_name(),
        'version': '1.0.0',
        'algorithm': 'Description of your algorithm',
        'parameters': {
            'threshold': self.threshold,
            # ... all parameters
        },
        'requirements': ['high', 'low', 'close'],
        'optional_columns': ['volume'],
        'best_for': 'trending markets with clear swings'
    }
```

#### 3. Performance Optimization

```python
# Use NumPy for vectorized operations
amplitudes = np.abs(np.diff(data['close'].values))

# Avoid loops where possible
# BAD:
for i in range(len(data)):
    result.append(calculate_something(data.iloc[i]))

# GOOD:
result = data['close'].rolling(5).apply(calculate_something)
```

#### 4. Validate Inputs

```python
def _validate_data(self, data: pd.DataFrame) -> None:
    """Validate input data."""
    if data.empty:
        raise ValueError("Data is empty")
    
    required = ['high', 'low', 'close']
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    
    if data[required].isnull().any().any():
        raise ValueError("Data contains NaN values")
```

### Strategy Comparison (A/B Testing)

```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

# Test multiple strategies
strategies = ['zigzag', 'find_peaks', 'pivot_points', 'my_custom']
results = {}

for strategy_name in strategies:
    analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy_name)
    features = analyzer.extract_zone_features(zone_dict)
    swing_metrics = features.metadata['swing_metrics']
    
    results[strategy_name] = {
        'num_swings': swing_metrics.num_swings,
        'avg_rally': swing_metrics.avg_rally_pct,
        'avg_drop': swing_metrics.avg_drop_pct
    }

# Compare results
import pandas as pd
comparison = pd.DataFrame(results).T
print(comparison)
```

### Built-in Strategies

For full documentation of all 8 built-in strategies, see:
- [Strategies API Reference](analysis/strategies.md)
- Examples: `tests/unit/test_*_strategy.py`
- Implementations: `bquant/analysis/zones/strategies/`

### Registry API

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

# List available strategies
print(StrategyRegistry.list_swing_strategies())
print(StrategyRegistry.list_shape_strategies())
print(StrategyRegistry.list_divergence_strategies())
print(StrategyRegistry.list_volatility_strategies())
print(StrategyRegistry.list_volume_strategies())

# Get strategy class
SwingClass = StrategyRegistry.get_swing_strategy('zigzag')
strategy_instance = SwingClass(legs=10, deviation=0.05)

# Registry stats
stats = StrategyRegistry.get_registry_stats()
print(f"Total strategies: {stats['total']}")
print(f"By type: {stats['by_type']}")
```

### Factory Configuration

Add your strategy to configuration:

```python
# In bquant/core/config.py

ANALYSIS_CONFIG = {
    'strategies': {
        'swing': {
            'default': 'zigzag',
            'my_custom': {
                'threshold': 0.02,
                'class': 'MyCustomSwingStrategy'
            }
        }
    }
}

# Then use factory
from bquant.core.config import create_swing_strategy
strategy = create_swing_strategy('my_custom')
```

---

## 📊 Создание собственной визуализации

### Шаг 1: Наследование от BaseChart

```python
from bquant.visualization.base import BaseChart
import plotly.graph_objects as go
import plotly.express as px

class CustomChart(BaseChart):
    """Кастомный график"""
    
    def __init__(self, theme='default'):
        super().__init__(theme)
    
    def create_chart(self, data, title="Custom Chart", **kwargs):
        """Создание графика"""
        # Ваша логика создания графика
        fig = self._build_chart(data, title, **kwargs)
        
        # Применение темы
        self._apply_theme(fig)
        
        return fig
    
    def _build_chart(self, data, title, **kwargs):
        """Построение графика"""
        fig = go.Figure()
        
        # Добавление данных
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['close'],
            mode='lines',
            name='Close Price',
            line=dict(color=self.theme.colors['primary'])
        ))
        
        # Настройка макета
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price",
            height=600
        )
        
        return fig
    
    def _apply_theme(self, fig):
        """Применение темы"""
        fig.update_layout(
            template=self.theme.template,
            font=dict(
                family=self.theme.font_family,
                size=self.theme.font_size
            )
        )
```

### Шаг 2: Использование

```python
# Создание и использование графика
chart = CustomChart(theme='dark')
fig = chart.create_chart(data, title="My Custom Chart")
fig.show()
```

## 📥 Создание собственного загрузчика данных

### Шаг 1: Наследование от DataLoader

```python
from bquant.data.loader import DataLoader
import pandas as pd

class CustomDataLoader(DataLoader):
    """Кастомный загрузчик данных"""
    
    def __init__(self, source_type='custom'):
        super().__init__()
        self.source_type = source_type
    
    def load(self, source, **kwargs):
        """Загрузка данных"""
        if self.source_type == 'custom':
            return self._load_custom_data(source, **kwargs)
        else:
            return super().load(source, **kwargs)
    
    def _load_custom_data(self, source, **kwargs):
        """Загрузка кастомных данных"""
        # Ваша логика загрузки
        data = pd.read_csv(source, **kwargs)
        
        # Стандартизация колонок
        data = self._standardize_columns(data)
        
        return data
    
    def _standardize_columns(self, data):
        """Стандартизация колонок"""
        # Маппинг колонок к стандартным именам
        column_mapping = {
            'Date': 'time',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        data = data.rename(columns=column_mapping)
        
        # Установка индекса времени
        if 'time' in data.columns:
            data['time'] = pd.to_datetime(data['time'])
            data.set_index('time', inplace=True)
        
        return data
```

## 🔧 Создание собственного процессора данных

### Шаг 1: Наследование от DataProcessor

```python
from bquant.data.processor import DataProcessor
import pandas as pd
import numpy as np

class CustomDataProcessor(DataProcessor):
    """Кастомный процессор данных"""
    
    def __init__(self, processing_config=None):
        super().__init__()
        self.config = processing_config or {}
    
    def process(self, data):
        """Обработка данных"""
        processed_data = data.copy()
        
        # Применение кастомных обработок
        if self.config.get('remove_outliers', False):
            processed_data = self._remove_outliers(processed_data)
        
        if self.config.get('add_features', False):
            processed_data = self._add_features(processed_data)
        
        if self.config.get('normalize', False):
            processed_data = self._normalize_data(processed_data)
        
        return processed_data
    
    def _remove_outliers(self, data):
        """Удаление выбросов"""
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                data = data[(data[col] >= lower_bound) & (data[col] <= upper_bound)]
        
        return data
    
    def _add_features(self, data):
        """Добавление признаков"""
        # Технические индикаторы
        data['sma_20'] = data['close'].rolling(window=20).mean()
        data['sma_50'] = data['close'].rolling(window=50).mean()
        data['rsi'] = self._calculate_rsi(data['close'])
        
        return data
    
    def _calculate_rsi(self, prices, period=14):
        """Расчет RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _normalize_data(self, data):
        """Нормализация данных"""
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                data[col] = (data[col] - data[col].mean()) / data[col].std()
        
        return data
```

## 🧪 Тестирование расширений

### Создание тестов

```python
import numpy as np
import pandas as pd
import pytest

from my_bquant_extension.indicators.custom_indicator import CustomIndicator
from my_bquant_extension.analyzers.custom_analyzer import CustomAnalyzer

class TestCustomIndicator:
    """Тесты для кастомного индикатора"""
    
    @pytest.fixture
    def sample_data(self):
        """Тестовые данные"""
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        return data
    
    def test_indicator_calculation(self, sample_data):
        """Тест расчета индикатора"""
        indicator = CustomIndicator(param1=10, param2=20)
        result = indicator.calculate(sample_data)

        assert result.name == 'CustomIndicator'
        assert len(result.data) == len(sample_data)
        assert not result.data['custom_indicator'].isna().all()
    
    def test_indicator_validation(self, sample_data):
        """Тест валидации данных"""
        indicator = CustomIndicator()
        
        # Тест с валидными данными
        assert indicator.validate_data(sample_data) is True
        
        # Тест с невалидными данными
        invalid_data = sample_data.drop(columns=['close'])
        assert indicator.validate_data(invalid_data) == False

class TestCustomAnalyzer:
    """Тесты для кастомного анализатора"""
    
    @pytest.fixture
    def sample_data(self):
        """Тестовые данные"""
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        }, index=dates)
        return data
    
    def test_analyzer_volatility(self, sample_data):
        """Тест анализа волатильности"""
        analyzer = CustomAnalyzer(analysis_type='volatility')
        result = analyzer.analyze(sample_data)

        assert result.analysis_type == 'volatility'
        assert 'mean_volatility' in result.results
        assert result.results['mean_volatility'] >= 0
```

### Запуск тестов

```bash
# Запуск всех тестов
pytest tests/test_custom_extensions.py -v

# Запуск с покрытием
pytest tests/test_custom_extensions.py --cov=bquant --cov-report=html
```

## 📦 Упаковка расширений

### Структура пакета

```
my_bquant_extension/
├── setup.py
├── README.md
├── requirements.txt
├── my_bquant_extension/
│   ├── __init__.py
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── custom_indicator.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   └── custom_analyzer.py
│   └── visualizations/
│       ├── __init__.py
│       └── custom_chart.py
└── tests/
    ├── __init__.py
    ├── test_indicators.py
    ├── test_analyzers.py
    └── test_visualizations.py
```

### setup.py

```python
from setuptools import setup, find_packages

setup(
    name="my-bquant-extension",
    version="0.1.0",
    description="Custom extension for BQuant",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "bquant>=0.0.0",
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "plotly>=5.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0"
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ]
)
```

### Автоматическая регистрация

```python
# my_bquant_extension/__init__.py
from .indicators.custom_indicator import CustomIndicator
from .analyzers.custom_analyzer import CustomAnalyzer
from .visualizations.custom_chart import CustomChart

# Локальный реестр анализаторов расширения (пример интеграции)
ANALYZERS_REGISTRY = {}


# Автоматическая регистрация при импорте
def register_extensions():
    """Регистрация расширений"""
    from bquant.indicators.base import IndicatorFactory

    # Регистрация индикаторов в глобальной фабрике BQuant
    IndicatorFactory.register_indicator('custom_indicator', CustomIndicator)

    # Регистрация анализаторов в собственном реестре расширения
    ANALYZERS_REGISTRY['CustomAnalyzer'] = CustomAnalyzer

# Автоматическая регистрация при импорте модуля
register_extensions()
```

## 🔗 Интеграция с существующим API

### Использование в скриптах

```python
# Использование кастомных компонентов
from my_bquant_extension import CustomIndicator, CustomAnalyzer, CustomChart
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# Использование кастомного индикатора
indicator = CustomIndicator(param1=15, param2=25)
indicator_result = indicator.calculate(data)

# Использование кастомного анализатора
analyzer = CustomAnalyzer(analysis_type='volatility')
analysis_result = analyzer.analyze(data)

# Использование кастомного графика
chart = CustomChart(theme='dark')
fig = chart.create_chart(data, title="Custom Analysis")
fig.show()
```

### Интеграция с CLI

```python
# scripts/analysis/custom_analysis.py
import argparse
from my_bquant_extension import CustomIndicator, CustomAnalyzer
from bquant.data.samples import get_sample_data

def main():
    parser = argparse.ArgumentParser(description="Custom analysis script")
    parser.add_argument("--dataset", default="tv_xauusd_1h", help="Dataset name")
    parser.add_argument("--param1", type=int, default=15, help="Parameter 1")
    parser.add_argument("--param2", type=int, default=25, help="Parameter 2")
    
    args = parser.parse_args()
    
    # Загрузка данных
    data = get_sample_data(args.dataset)
    
    # Кастомный анализ
    indicator = CustomIndicator(param1=args.param1, param2=args.param2)
    indicator_result = indicator.calculate(data)
    
    analyzer = CustomAnalyzer(analysis_type='volatility')
    analysis_result = analyzer.analyze(data)
    
    # Вывод результатов
    print(f"Indicator result: {indicator_result.data.tail()}")
    print(f"Analysis result: {analysis_result.results}")

if __name__ == "__main__":
    main()
```

## 🚀 Лучшие практики

### Производительность

```python
# Используйте NumPy для быстрых вычислений
import numpy as np

def fast_calculation(data):
    """Быстрый расчет с NumPy"""
    prices = data['close'].values  # NumPy array
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns)
    return volatility

# Используйте векторизацию
def vectorized_operation(data):
    """Векторизованная операция"""
    return data['close'].rolling(window=20).mean()
```

### Обработка ошибок

```python
from bquant.core.exceptions import BQuantError, DataError

class CustomError(BQuantError):
    """Кастомное исключение"""
    pass

def safe_calculation(data):
    """Безопасный расчет с обработкой ошибок"""
    try:
        if data.empty:
            raise DataError("Empty dataset provided")
        
        if 'close' not in data.columns:
            raise DataError("Missing 'close' column")
        
        result = perform_calculation(data)
        return result
        
    except Exception as e:
        raise CustomError(f"Calculation failed: {str(e)}")
```

### Документация

```python
class CustomIndicator(BaseIndicator):
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
    
    def calculate(self, data):
        """
        Расчет индикатора.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame с OHLCV данными
            
        Returns
        -------
        IndicatorResult
            Результат расчета индикатора
            
        Raises
        ------
        DataError
            Если данные некорректны
        """
        # Реализация
        pass
```

## 📚 Дополнительные ресурсы

- **[Core Modules](../core/)** - Базовые модули для расширения
- **[Indicators](../indicators/)** - Примеры индикаторов
- **[Analysis](../analysis/)** - Примеры анализаторов
- **[Visualization](../visualization/)** - Примеры визуализаций

---

**Следующий шаг:** Изучите существующие модули и создайте свое первое расширение! 🚀
