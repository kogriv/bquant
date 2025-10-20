# План достижения полной универсальности аналитического инструментария

**Версия:** 1.0  
**Дата:** 2025-10-18  
**Статус:** Roadmap для полной универсальности  
**Цель:** 100% универсальный аналитический инструментарий без hardcoded зависимостей от конкретных индикаторов

---

## Executive Summary

**Текущее состояние:** 75% универсальности (после bugfixes #1-3)  
**Целевое состояние:** 95%+ универсальности (полностью функциональный)  
**Требуется:** 3 критических bugfix + архитектурные улучшения

### Критические проблемы:

1. 🔴 **Shape Strategy** - hardcoded `macd_hist` (блокирует RSI/AO shape analysis)
2. 🔴 **Divergence Strategy** - hardcoded `macd_hist`/`macd` (блокирует RSI/AO divergence detection)
3. 🟡 **Volume Strategy** - hardcoded `volume_macd_corr` (теряется 1 метрика для non-MACD)

### План действий:

- **Bugfix #4:** Shape Strategy (2 hours) - CRITICAL
- **Bugfix #5:** Divergence Strategy (3 hours) - CRITICAL  
- **Bugfix #6:** Volume Strategy (1 hour) - LOW
- **Architecture:** Унификация интерфейсов (4 hours) - MEDIUM
- **Total effort:** ~10 hours для полной универсальности

---

## Часть 1: Критические исправления (Priority 0)

### Bugfix #4: StatisticalShapeStrategy - универсализация

**Файл:** `bquant/analysis/zones/strategies/shape/statistical.py`

#### Проблема:

```python
# Текущий код (lines 53-60):
if 'macd_hist' not in zone_data.columns:
    raise ValueError("zone_data must contain 'macd_hist' column")

if len(zone_data) == 0:
    raise ValueError("zone_data cannot be empty")

try:
    hist = zone_data['macd_hist'].dropna()  # ❌ Hardcoded
```

**Impact:**
- ❌ RSI zones: `ValueError: zone_data must contain 'macd_hist' column`
- ❌ AO zones: 36 warnings (по 1 на каждую зону)
- ❌ Stochastic/Williams %R: не работает shape analysis

#### Решение:

**Шаг 1: Добавить auto-detection индикаторной колонки**

```python
# New method (add after line 35):
def _detect_oscillator_column(self, zone_data: pd.DataFrame) -> str:
    """
    Auto-detect oscillator column for shape analysis.
    
    Priority order:
    1. macd_hist (legacy compatibility)
    2. RSI_* (any RSI period)
    3. AO_* (Awesome Oscillator)
    4. CCI_* (Commodity Channel Index)
    5. STOCH* (Stochastic)
    6. WILLR_* (Williams %R)
    
    Returns:
        str: Detected column name
        
    Raises:
        ValueError: If no suitable oscillator column found
    """
    # Check priority order
    oscillator_patterns = [
        ('macd_hist', lambda col: col == 'macd_hist'),
        ('RSI', lambda col: col.startswith('RSI_')),
        ('AO', lambda col: col.startswith('AO_')),
        ('CCI', lambda col: col.startswith('CCI_')),
        ('STOCH', lambda col: col.startswith('STOCH')),
        ('WILLR', lambda col: col.startswith('WILLR_')),
    ]
    
    for pattern_name, pattern_func in oscillator_patterns:
        matching_cols = [col for col in zone_data.columns if pattern_func(col)]
        if matching_cols:
            detected = matching_cols[0]  # Use first match
            logger.debug(f"Auto-detected oscillator column: {detected}")
            return detected
    
    # Fallback: try any numeric column that's not OHLCV
    excluded = {'open', 'high', 'low', 'close', 'volume', 'atr'}
    numeric_cols = zone_data.select_dtypes(include=[np.number]).columns
    candidate_cols = [col for col in numeric_cols if col not in excluded]
    
    if candidate_cols:
        detected = candidate_cols[0]
        logger.warning(
            f"No standard oscillator found, using fallback column: {detected}. "
            f"Consider passing indicator_col explicitly."
        )
        return detected
    
    raise ValueError(
        "No suitable oscillator column found for shape analysis. "
        "Available columns: " + str(list(zone_data.columns))
    )
```

**Шаг 2: Обновить сигнатуру метода calculate**

```python
# Update method signature (line 39):
def calculate(self, zone_data: pd.DataFrame, indicator_col: str = None) -> ShapeMetrics:
    """
    Calculate shape metrics from oscillator data.
    
    Args:
        zone_data: DataFrame with oscillator column
        indicator_col: Explicit indicator column name (optional, will auto-detect if None)
    
    Returns:
        ShapeMetrics with skewness, kurtosis, and optionally smoothness
    
    Raises:
        ValueError: If zone_data is empty or no suitable oscillator column found
    
    Example:
        # Auto-detection (for MACD zones)
        strategy = StatisticalShapeStrategy()
        metrics = strategy.calculate(macd_zone_data)
        
        # Explicit column (for RSI zones)
        metrics = strategy.calculate(rsi_zone_data, indicator_col='RSI_14')
        
        # Works with any oscillator
        metrics = strategy.calculate(ao_zone_data, indicator_col='AO_5_34')
    """
    # Validate input
    if len(zone_data) == 0:
        raise ValueError("zone_data cannot be empty")
    
    # Auto-detect or use provided column
    if indicator_col is None:
        indicator_col = self._detect_oscillator_column(zone_data)
    
    if indicator_col not in zone_data.columns:
        raise ValueError(
            f"Indicator column '{indicator_col}' not found in data. "
            f"Available: {list(zone_data.columns)}"
        )
    
    try:
        hist = zone_data[indicator_col].dropna()  # ✅ Universal
        
        if len(hist) < 3:
            # Need at least 3 points for meaningful statistics
            logger.debug(f"Not enough data points for shape analysis: {len(hist)}")
            return self._minimal_metrics()
        
        # Calculate skewness
        hist_skewness = float(skew(hist, bias=self.bias_correction))
        
        # Calculate kurtosis
        hist_kurtosis_excess = float(kurtosis(hist, bias=self.bias_correction))
        hist_kurtosis = hist_kurtosis_excess + 3.0
        
        # Calculate smoothness (optional)
        hist_smoothness = None
        if self.calculate_smoothness:
            hist_diff = hist.diff().dropna()
            if len(hist_diff) > 0:
                hist_smoothness = float(hist_diff.std())
            else:
                hist_smoothness = 0.0
        
        # Create result
        metrics = ShapeMetrics(
            hist_skewness=hist_skewness,
            hist_kurtosis=hist_kurtosis,
            hist_smoothness=hist_smoothness,
            strategy_name='statistical',
            strategy_params={
                'calculate_smoothness': self.calculate_smoothness,
                'bias_correction': self.bias_correction,
                'indicator_col': indicator_col  # ✅ Track which column was used
            }
        )
        
        # Validate
        metrics.validate()
        
        smoothness_str = f"{hist_smoothness:.4f}" if hist_smoothness is not None else "N/A"
        logger.debug(
            f"Shape metrics calculated for '{indicator_col}': "
            f"skewness={hist_skewness:.2f}, kurtosis={hist_kurtosis:.2f}, "
            f"smoothness={smoothness_str}"
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Statistical shape calculation failed: {e}", exc_info=True)
        return self._minimal_metrics()
```

**Шаг 3: Обновить docstring класса**

```python
# Update class docstring (lines 24-35):
@dataclass
class StatisticalShapeStrategy:
    """
    Shape analysis using statistical moments (skewness and kurtosis).
    
    Analyzes the shape of oscillator "bump" to classify zone archetypes:
    - Skewness: asymmetry of the distribution (early vs late impulse)
    - Kurtosis: peakedness (sharp spike vs smooth wave)
    - Smoothness: standard deviation of the derivative (choppy vs smooth)
    
    Universal support:
        - MACD histogram (macd_hist)
        - RSI (RSI_14, RSI_*)
        - Awesome Oscillator (AO_5_34, AO_*)
        - CCI, Stochastic, Williams %R, etc.
        - Auto-detection or explicit indicator_col
    
    Attributes:
        calculate_smoothness: Whether to calculate smoothness metric (default: True)
        bias_correction: Whether to use bias correction in skewness/kurtosis (default: True)
    """
```

**Шаг 4: Обновить get_metadata**

```python
# Update get_metadata (lines 133-171):
def get_metadata(self) -> Dict[str, Any]:
    """Get strategy metadata for logging and traceability."""
    return {
        'name': 'Statistical',
        'description': 'Shape analysis via skewness, kurtosis, and smoothness',
        'universal': True,  # ✅ Now universal!
        'supported_indicators': [
            'macd_hist',
            'RSI_*',
            'AO_*',
            'CCI_*',
            'STOCH*',
            'WILLR_*',
            'Any numeric oscillator'
        ],
        'params': {
            'calculate_smoothness': self.calculate_smoothness,
            'bias_correction': self.bias_correction
        },
        'source': 'scipy.stats (skew, kurtosis)',
        'metrics': {
            'hist_skewness': {
                'interpretation': {
                    '> 0.5': 'Early impulse (peak at beginning)',
                    '≈ 0': 'Symmetric shape',
                    '< -0.5': 'Late impulse (peak at end)'
                }
            },
            'hist_kurtosis': {
                'interpretation': {
                    '> 5': 'Sharp spike (leptokurtic)',
                    '≈ 3': 'Normal distribution',
                    '< 1': 'Flat wave (platykurtic)'
                }
            },
            'hist_smoothness': {
                'interpretation': {
                    'low': 'Smooth curve',
                    'high': 'Choppy/erratic'
                }
            }
        },
        'use_cases': [
            'Zone archetype classification',
            'Improved clustering (K-Means)',
            'Pattern recognition',
            'Quality assessment'
        ]
    }
```

#### Шаг 5: Обновить вызов из ZoneFeaturesAnalyzer

**Файл:** `bquant/analysis/zones/zone_features.py`

```python
# Update call in extract_zone_features (around line 285):
if self.shape_strategy is not None:
    try:
        # ✅ Pass detected indicator column
        indicator_col = None
        if 'macd_hist' in data.columns:
            indicator_col = 'macd_hist'
        elif 'RSI_14' in data.columns:
            indicator_col = 'RSI_14'
        elif any(col.startswith('RSI_') for col in data.columns):
            indicator_col = next(col for col in data.columns if col.startswith('RSI_'))
        elif any(col.startswith('AO_') for col in data.columns):
            indicator_col = next(col for col in data.columns if col.startswith('AO_'))
        
        # Call with explicit or None (for auto-detection)
        shape_metrics = self.shape_strategy.calculate(data, indicator_col=indicator_col)
        metadata['shape_metrics'] = shape_metrics.to_dict()
        self.logger.debug(
            f"Shape metrics calculated: skewness={shape_metrics.hist_skewness:.2f}, "
            f"kurtosis={shape_metrics.hist_kurtosis:.2f}"
        )
    except Exception as e:
        # ✅ No more warnings for non-MACD zones!
        self.logger.debug(f"Shape metrics not available: {e}")
        metadata['shape_metrics'] = None
```

#### Тесты для Bugfix #4:

**Файл:** `tests/unit/test_shape_strategy_universal.py` (создать новый)

```python
"""
Unit tests for universal StatisticalShapeStrategy.

Verifies that shape analysis works with MACD, RSI, AO, and any oscillator.
"""
import pytest
import pandas as pd
import numpy as np
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy


class TestStatisticalShapeStrategyUniversal:
    """Test universal support for shape strategy."""
    
    @pytest.fixture
    def strategy(self):
        return StatisticalShapeStrategy()
    
    @pytest.fixture
    def macd_zone_data(self):
        """Sample MACD zone data."""
        return pd.DataFrame({
            'close': np.linspace(100, 110, 20),
            'macd_hist': np.sin(np.linspace(0, np.pi, 20)) * 5
        })
    
    @pytest.fixture
    def rsi_zone_data(self):
        """Sample RSI zone data."""
        return pd.DataFrame({
            'close': np.linspace(100, 110, 20),
            'RSI_14': np.linspace(30, 70, 20)
        })
    
    @pytest.fixture
    def ao_zone_data(self):
        """Sample AO zone data."""
        return pd.DataFrame({
            'close': np.linspace(100, 110, 20),
            'AO_5_34': np.sin(np.linspace(0, np.pi, 20)) * 2
        })
    
    def test_macd_zones_explicit(self, strategy, macd_zone_data):
        """Test MACD zones with explicit column."""
        metrics = strategy.calculate(macd_zone_data, indicator_col='macd_hist')
        
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert metrics.strategy_name == 'statistical'
        assert 'macd_hist' in metrics.strategy_params['indicator_col']
    
    def test_macd_zones_auto_detect(self, strategy, macd_zone_data):
        """Test MACD zones with auto-detection."""
        metrics = strategy.calculate(macd_zone_data)  # No indicator_col
        
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        # Should auto-detect macd_hist
        assert 'macd_hist' in metrics.strategy_params['indicator_col']
    
    def test_rsi_zones_explicit(self, strategy, rsi_zone_data):
        """Test RSI zones with explicit column."""
        metrics = strategy.calculate(rsi_zone_data, indicator_col='RSI_14')
        
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert 'RSI_14' in metrics.strategy_params['indicator_col']
    
    def test_rsi_zones_auto_detect(self, strategy, rsi_zone_data):
        """Test RSI zones with auto-detection."""
        metrics = strategy.calculate(rsi_zone_data)
        
        assert metrics.hist_skewness is not None
        # Should auto-detect RSI_14
        assert 'RSI_14' in metrics.strategy_params['indicator_col']
    
    def test_ao_zones_explicit(self, strategy, ao_zone_data):
        """Test AO zones with explicit column."""
        metrics = strategy.calculate(ao_zone_data, indicator_col='AO_5_34')
        
        assert metrics.hist_skewness is not None
        assert metrics.hist_kurtosis is not None
        assert 'AO_5_34' in metrics.strategy_params['indicator_col']
    
    def test_ao_zones_auto_detect(self, strategy, ao_zone_data):
        """Test AO zones with auto-detection."""
        metrics = strategy.calculate(ao_zone_data)
        
        assert metrics.hist_skewness is not None
        assert 'AO_5_34' in metrics.strategy_params['indicator_col']
    
    def test_multiple_indicators_priority(self, strategy):
        """Test auto-detection priority when multiple indicators present."""
        # macd_hist should have priority over RSI
        data = pd.DataFrame({
            'close': np.linspace(100, 110, 20),
            'macd_hist': np.sin(np.linspace(0, np.pi, 20)) * 5,
            'RSI_14': np.linspace(30, 70, 20)
        })
        
        metrics = strategy.calculate(data)
        
        # Should prefer macd_hist (highest priority)
        assert 'macd_hist' in metrics.strategy_params['indicator_col']
    
    def test_no_suitable_column_raises(self, strategy):
        """Test that missing oscillator raises informative error."""
        data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200]
        })
        
        with pytest.raises(ValueError, match="No suitable oscillator column found"):
            strategy.calculate(data)
    
    def test_invalid_explicit_column_raises(self, strategy, macd_zone_data):
        """Test that invalid explicit column raises error."""
        with pytest.raises(ValueError, match="Indicator column 'invalid' not found"):
            strategy.calculate(macd_zone_data, indicator_col='invalid')
    
    def test_empty_data_raises(self, strategy):
        """Test that empty data raises error."""
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="zone_data cannot be empty"):
            strategy.calculate(empty_data)
    
    def test_insufficient_data_returns_minimal(self, strategy):
        """Test that insufficient data returns minimal metrics."""
        # Only 2 points (need at least 3)
        data = pd.DataFrame({
            'macd_hist': [1.0, 2.0]
        })
        
        metrics = strategy.calculate(data)
        
        # Should return minimal metrics
        assert metrics.hist_skewness == 0.0
        assert metrics.hist_kurtosis == 3.0
    
    def test_metadata_shows_universal(self, strategy):
        """Test that metadata indicates universal support."""
        metadata = strategy.get_metadata()
        
        assert metadata['universal'] is True
        assert 'RSI_*' in metadata['supported_indicators']
        assert 'AO_*' in metadata['supported_indicators']
        assert 'macd_hist' in metadata['supported_indicators']
```

#### Результат Bugfix #4:

✅ **Shape analysis работает для:**
- MACD zones (backward compatible)
- RSI zones (новая поддержка)
- AO zones (новая поддержка)
- Stochastic, CCI, Williams %R (новая поддержка)
- Любой numeric oscillator (fallback)

✅ **Warnings исчезли:**
- Было: 36 warnings при анализе AO zones
- Стало: 0 warnings

✅ **Тесты:**
- 12 новых unit tests
- Coverage: 100% новой функциональности

---

## Bugfix #5: ClassicDivergenceStrategy - универсализация

**Файл:** `bquant/analysis/zones/strategies/divergence/classic.py`

#### Проблема:

```python
# Текущий код (lines 60-66):
required_cols = ['close', 'high', 'low', 'macd_hist']
if self.use_macd_line:
    required_cols.append('macd')

missing_cols = [col for col in required_cols if col not in zone_data.columns]
if missing_cols:
    raise ValueError(f"Zone data must contain columns: {missing_cols}")
```

**Концептуальная проблема:**
- Дивергенция = расхождение между ценой и **любым** индикатором
- Но реализация работает только с MACD
- RSI/Price divergence, AO/Price divergence - валидные паттерны

#### Решение:

**Шаг 1: Добавить auto-detection индикаторных колонок**

```python
# New method (add after line 40):
def _detect_indicator_columns(self, zone_data: pd.DataFrame) -> tuple:
    """
    Auto-detect indicator columns for divergence analysis.
    
    Returns:
        tuple: (indicator_col, indicator_line_col or None)
        
    Priority for main indicator:
    1. macd_hist (legacy)
    2. RSI_* (most common oscillator)
    3. AO_* (Awesome Oscillator)
    4. CCI_* (Commodity Channel Index)
    5. STOCH* (Stochastic)
    
    For signal line (optional):
    - macd_hist → macd
    - RSI_14 → RSI_MA (if exists)
    """
    # Main indicator detection
    indicator_col = None
    indicator_line_col = None
    
    # Check for MACD (priority 1)
    if 'macd_hist' in zone_data.columns:
        indicator_col = 'macd_hist'
        if 'macd' in zone_data.columns:
            indicator_line_col = 'macd'
        logger.debug("Detected MACD divergence setup")
        return indicator_col, indicator_line_col
    
    # Check for RSI (priority 2)
    rsi_cols = [col for col in zone_data.columns if col.startswith('RSI_')]
    if rsi_cols:
        indicator_col = rsi_cols[0]
        # Check for RSI moving average
        rsi_ma_candidates = [col for col in zone_data.columns 
                            if 'RSI' in col and 'MA' in col.upper()]
        if rsi_ma_candidates:
            indicator_line_col = rsi_ma_candidates[0]
        logger.debug(f"Detected RSI divergence setup: {indicator_col}")
        return indicator_col, indicator_line_col
    
    # Check for AO (priority 3)
    ao_cols = [col for col in zone_data.columns if col.startswith('AO_')]
    if ao_cols:
        indicator_col = ao_cols[0]
        logger.debug(f"Detected AO divergence setup: {indicator_col}")
        return indicator_col, indicator_line_col
    
    # Check for CCI (priority 4)
    cci_cols = [col for col in zone_data.columns if col.startswith('CCI_')]
    if cci_cols:
        indicator_col = cci_cols[0]
        logger.debug(f"Detected CCI divergence setup: {indicator_col}")
        return indicator_col, indicator_line_col
    
    # Check for Stochastic (priority 5)
    stoch_cols = [col for col in zone_data.columns if col.startswith('STOCH')]
    if stoch_cols:
        indicator_col = stoch_cols[0]
        # Check for signal line (STOCHk vs STOCHd)
        if 'STOCHk' in indicator_col:
            signal_candidate = indicator_col.replace('STOCHk', 'STOCHd')
            if signal_candidate in zone_data.columns:
                indicator_line_col = signal_candidate
        logger.debug(f"Detected Stochastic divergence setup: {indicator_col}")
        return indicator_col, indicator_line_col
    
    raise ValueError(
        "No suitable indicator found for divergence analysis. "
        "Supported: MACD, RSI, AO, CCI, Stochastic. "
        f"Available columns: {list(zone_data.columns)}"
    )
```

**Шаг 2: Обновить сигнатуру метода calculate_divergence**

```python
# Update method signature (line 43):
def calculate_divergence(self, 
                        zone_data: pd.DataFrame,
                        indicator_col: str = None,
                        indicator_line_col: str = None) -> DivergenceMetrics:
    """
    Calculate divergence metrics for a zone.
    
    Universal support for price vs any oscillator divergence detection.
    
    Args:
        zone_data: DataFrame with columns: close, high, low, and oscillator
        indicator_col: Explicit indicator column (optional, will auto-detect if None)
                      Examples: 'macd_hist', 'RSI_14', 'AO_5_34', 'CCI_14'
        indicator_line_col: Optional signal line (for 2-line divergence)
                           Examples: 'macd' (for macd_hist), 'STOCHd_14_3_3' (for STOCHk)
    
    Returns:
        DivergenceMetrics with validated data
    
    Raises:
        ValueError: If required columns are missing or data is insufficient
    
    Examples:
        # Auto-detection (MACD zones)
        strategy = ClassicDivergenceStrategy()
        metrics = strategy.calculate_divergence(macd_zone_data)
        
        # Explicit RSI
        metrics = strategy.calculate_divergence(rsi_zone_data, indicator_col='RSI_14')
        
        # Explicit AO
        metrics = strategy.calculate_divergence(ao_zone_data, indicator_col='AO_5_34')
        
        # 2-line divergence (Stochastic)
        metrics = strategy.calculate_divergence(
            stoch_zone_data, 
            indicator_col='STOCHk_14_3_3',
            indicator_line_col='STOCHd_14_3_3'
        )
    """
    # Validate input
    if zone_data.empty:
        raise ValueError("Zone data cannot be empty")
    
    # Auto-detect if not provided
    if indicator_col is None:
        indicator_col, detected_line = self._detect_indicator_columns(zone_data)
        if indicator_line_col is None:
            indicator_line_col = detected_line
    
    # Validate required columns
    required_cols = ['close', 'high', 'low', indicator_col]
    if indicator_line_col:
        required_cols.append(indicator_line_col)
    
    missing_cols = [col for col in required_cols if col not in zone_data.columns]
    if missing_cols:
        raise ValueError(
            f"Zone data must contain columns: {missing_cols}. "
            f"Available: {list(zone_data.columns)}"
        )
    
    if len(zone_data) < self.min_peak_distance * 2:
        logger.debug(f"Insufficient data for divergence detection: {len(zone_data)} bars")
        return self._empty_metrics()
    
    try:
        # Find extrema
        price_peaks, price_troughs = self._find_price_extrema(zone_data)
        
        # ✅ Universal: find indicator extrema (not just MACD)
        indicator_peaks, indicator_troughs = self._find_indicator_extrema(
            zone_data, indicator_col
        )
        
        # Detect divergences
        divergences = self._detect_divergences(
            zone_data, price_peaks, price_troughs, 
            indicator_peaks, indicator_troughs,
            indicator_col  # ✅ Pass column name
        )
        
        # Calculate metrics
        if not divergences:
            return self._empty_metrics()
        
        metrics = self._calculate_metrics(divergences)
        
        # ✅ Track which indicator was used
        metrics.strategy_params['indicator_col'] = indicator_col
        if indicator_line_col:
            metrics.strategy_params['indicator_line_col'] = indicator_line_col
        
        return metrics
        
    except Exception as e:
        logger.error(f"Divergence calculation failed: {e}", exc_info=True)
        return self._empty_metrics()
```

**Шаг 3: Заменить _find_macd_extrema на универсальный _find_indicator_extrema**

```python
# Replace _find_macd_extrema (lines 118-146) with:
def _find_indicator_extrema(self, zone_data: pd.DataFrame, 
                           indicator_col: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find indicator peaks and troughs using scipy.signal.find_peaks.
    
    Universal method that works with any oscillator.
    
    Args:
        zone_data: DataFrame with indicator column
        indicator_col: Name of indicator column to analyze
    
    Returns:
        Tuple of (peak_indices, trough_indices)
    """
    indicator_values = zone_data[indicator_col].values
    
    # Find peaks (high values)
    peaks, _ = find_peaks(
        indicator_values,
        distance=self.min_peak_distance,
        prominence=np.std(indicator_values) * 0.5  # Auto prominence
    )
    
    # Find troughs (low values) - invert signal
    troughs, _ = find_peaks(
        -indicator_values,
        distance=self.min_peak_distance,
        prominence=np.std(indicator_values) * 0.5
    )
    
    logger.debug(
        f"Found {len(peaks)} indicator peaks and {len(troughs)} troughs "
        f"in {indicator_col}"
    )
    
    return peaks, troughs
```

**Шаг 4: Обновить _detect_divergences для универсальности**

```python
# Update _detect_divergences (lines 148-234) - добавить indicator_col параметр:
def _detect_divergences(self, zone_data: pd.DataFrame,
                       price_peaks: np.ndarray, price_troughs: np.ndarray,
                       indicator_peaks: np.ndarray, indicator_troughs: np.ndarray,
                       indicator_col: str) -> List[Dict[str, Any]]:  # ✅ Add parameter
    """
    Detect bullish and bearish divergences.
    
    Args:
        zone_data: DataFrame with price and indicator data
        price_peaks: Indices of price peaks
        price_troughs: Indices of price troughs
        indicator_peaks: Indices of indicator peaks
        indicator_troughs: Indices of indicator troughs
        indicator_col: Name of indicator column (for universal access)
    
    Returns:
        List of divergence dictionaries
    """
    divergences = []
    
    # Bullish divergence: price makes lower low, indicator makes higher low
    for i in range(len(price_troughs) - 1):
        price_low1_idx = price_troughs[i]
        price_low2_idx = price_troughs[i + 1]
        
        # Find corresponding indicator troughs
        indicator_low1 = self._find_closest_extremum(
            price_low1_idx, indicator_troughs
        )
        indicator_low2 = self._find_closest_extremum(
            price_low2_idx, indicator_troughs
        )
        
        if indicator_low1 is None or indicator_low2 is None:
            continue
        
        # Check divergence conditions
        price_low1 = zone_data['low'].iloc[price_low1_idx]
        price_low2 = zone_data['low'].iloc[price_low2_idx]
        
        # ✅ Universal: use indicator_col instead of hardcoded 'macd_hist'
        ind_low1 = zone_data[indicator_col].iloc[indicator_low1]
        ind_low2 = zone_data[indicator_col].iloc[indicator_low2]
        
        # Bullish divergence: price ↓, indicator ↑
        if price_low2 < price_low1 and ind_low2 > ind_low1:
            strength = abs((ind_low2 - ind_low1) / ind_low1) if ind_low1 != 0 else 0
            
            if strength >= self.min_divergence_strength:
                divergences.append({
                    'type': 'bullish',
                    'price_idx': (price_low1_idx, price_low2_idx),
                    'indicator_idx': (indicator_low1, indicator_low2),
                    'strength': strength
                })
    
    # Bearish divergence: price makes higher high, indicator makes lower high
    for i in range(len(price_peaks) - 1):
        price_high1_idx = price_peaks[i]
        price_high2_idx = price_peaks[i + 1]
        
        # Find corresponding indicator peaks
        indicator_high1 = self._find_closest_extremum(
            price_high1_idx, indicator_peaks
        )
        indicator_high2 = self._find_closest_extremum(
            price_high2_idx, indicator_peaks
        )
        
        if indicator_high1 is None or indicator_high2 is None:
            continue
        
        # Check divergence conditions
        price_high1 = zone_data['high'].iloc[price_high1_idx]
        price_high2 = zone_data['high'].iloc[price_high2_idx]
        
        # ✅ Universal: use indicator_col instead of hardcoded 'macd_hist'
        ind_high1 = zone_data[indicator_col].iloc[indicator_high1]
        ind_high2 = zone_data[indicator_col].iloc[indicator_high2]
        
        # Bearish divergence: price ↑, indicator ↓
        if price_high2 > price_high1 and ind_high2 < ind_high1:
            strength = abs((ind_high2 - ind_high1) / ind_high1) if ind_high1 != 0 else 0
            
            if strength >= self.min_divergence_strength:
                divergences.append({
                    'type': 'bearish',
                    'price_idx': (price_high1_idx, price_high2_idx),
                    'indicator_idx': (indicator_high1, indicator_high2),
                    'strength': strength
                })
    
    logger.debug(
        f"Detected {len([d for d in divergences if d['type'] == 'bullish'])} bullish and "
        f"{len([d for d in divergences if d['type'] == 'bearish'])} bearish divergences"
    )
    
    return divergences
```

**Шаг 5: Обновить docstring класса**

```python
# Update class docstring (lines 17-36):
@dataclass
class ClassicDivergenceStrategy:
    """
    Classic divergence detection between price and oscillator.
    
    Universal support for divergence analysis with any oscillator:
    - MACD histogram vs price (classic)
    - RSI vs price (common)
    - Awesome Oscillator vs price
    - Stochastic vs price
    - CCI vs price
    - Any oscillator vs price
    
    Detects:
    - Bullish divergence: price makes lower low, indicator makes higher low
    - Bearish divergence: price makes higher high, indicator makes lower high
    
    Attributes:
        min_peak_distance: Minimum bars between peaks/troughs (default: 5)
        min_divergence_strength: Minimum strength threshold (default: 0.01, i.e. 1%)
        use_macd_line: [DEPRECATED] Use indicator_line_col parameter instead
    """
```

**Шаг 6: Обновить DivergenceMetrics dataclass**

```python
# In base.py, update DivergenceMetrics to track indicator:
@dataclass
class DivergenceMetrics:
    """
    Divergence metrics between price and indicator.
    
    Attributes:
        divergence_count: Total number of divergences detected
        bullish_divergence_count: Count of bullish divergences
        bearish_divergence_count: Count of bearish divergences
        divergence_type: Most common type ('bullish', 'bearish', or 'none')
        divergence_strength: Average strength of divergences
        divergence_direction: Overall direction ('bullish', 'bearish', 'mixed', 'none')
        strategy_name: Name of strategy used
        strategy_params: Parameters used (including indicator_col)  # ✅ NEW
    """
    divergence_count: int
    bullish_divergence_count: int
    bearish_divergence_count: int
    divergence_type: str
    divergence_strength: float
    divergence_direction: str
    strategy_name: str
    strategy_params: Dict[str, Any] = field(default_factory=dict)  # ✅ NEW
```

#### Тесты для Bugfix #5:

**Файл:** `tests/unit/test_divergence_strategy_universal.py` (создать новый)

```python
"""
Unit tests for universal ClassicDivergenceStrategy.

Verifies divergence detection works with MACD, RSI, AO, and any oscillator.
"""
import pytest
import pandas as pd
import numpy as np
from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy


class TestClassicDivergenceStrategyUniversal:
    """Test universal support for divergence strategy."""
    
    @pytest.fixture
    def strategy(self):
        return ClassicDivergenceStrategy()
    
    @pytest.fixture
    def bullish_divergence_macd(self):
        """
        Sample data with bullish divergence:
        - Price: lower low
        - MACD: higher low
        """
        return pd.DataFrame({
            'close': [100, 95, 90, 92, 88, 93, 95],  # Lower lows
            'high': [101, 96, 91, 93, 89, 94, 96],
            'low': [99, 94, 89, 91, 87, 92, 94],
            'macd_hist': [-2, -3, -4, -2, -3, -1, 0]  # Higher lows (divergence!)
        })
    
    @pytest.fixture
    def bearish_divergence_rsi(self):
        """
        Sample data with bearish divergence:
        - Price: higher high
        - RSI: lower high
        """
        return pd.DataFrame({
            'close': [100, 105, 110, 108, 112, 110, 108],  # Higher highs
            'high': [101, 106, 111, 109, 113, 111, 109],
            'low': [99, 104, 109, 107, 111, 109, 107],
            'RSI_14': [70, 75, 80, 75, 75, 70, 65]  # Lower highs (divergence!)
        })
    
    @pytest.fixture
    def no_divergence_ao(self):
        """Sample data with no divergence."""
        return pd.DataFrame({
            'close': np.linspace(100, 110, 20),
            'high': np.linspace(101, 111, 20),
            'low': np.linspace(99, 109, 20),
            'AO_5_34': np.linspace(-2, 2, 20)  # Trending together (no divergence)
        })
    
    def test_macd_divergence_explicit(self, strategy, bullish_divergence_macd):
        """Test MACD divergence with explicit column."""
        metrics = strategy.calculate_divergence(
            bullish_divergence_macd,
            indicator_col='macd_hist'
        )
        
        assert metrics.divergence_count > 0
        assert metrics.bullish_divergence_count > 0
        assert metrics.divergence_direction in ['bullish', 'mixed']
        assert 'macd_hist' in metrics.strategy_params['indicator_col']
    
    def test_macd_divergence_auto_detect(self, strategy, bullish_divergence_macd):
        """Test MACD divergence with auto-detection."""
        metrics = strategy.calculate_divergence(bullish_divergence_macd)
        
        assert metrics.divergence_count > 0
        # Should auto-detect macd_hist
        assert 'macd_hist' in metrics.strategy_params['indicator_col']
    
    def test_rsi_divergence_explicit(self, strategy, bearish_divergence_rsi):
        """Test RSI divergence with explicit column."""
        metrics = strategy.calculate_divergence(
            bearish_divergence_rsi,
            indicator_col='RSI_14'
        )
        
        assert metrics.divergence_count > 0
        assert metrics.bearish_divergence_count > 0
        assert metrics.divergence_direction in ['bearish', 'mixed']
        assert 'RSI_14' in metrics.strategy_params['indicator_col']
    
    def test_rsi_divergence_auto_detect(self, strategy, bearish_divergence_rsi):
        """Test RSI divergence with auto-detection."""
        metrics = strategy.calculate_divergence(bearish_divergence_rsi)
        
        assert metrics.divergence_count > 0
        assert 'RSI_14' in metrics.strategy_params['indicator_col']
    
    def test_ao_no_divergence(self, strategy, no_divergence_ao):
        """Test AO zones with no divergence."""
        metrics = strategy.calculate_divergence(no_divergence_ao)
        
        # No divergences should be found
        assert metrics.divergence_count == 0
        assert metrics.divergence_type == 'none'
        # Should still auto-detect column
        assert 'AO_5_34' in metrics.strategy_params['indicator_col']
    
    def test_multiple_indicators_priority(self, strategy):
        """Test that MACD has priority over RSI in auto-detection."""
        data = pd.DataFrame({
            'close': [100, 95, 90, 92, 88],
            'high': [101, 96, 91, 93, 89],
            'low': [99, 94, 89, 91, 87],
            'macd_hist': [-2, -3, -4, -2, -1],
            'RSI_14': [40, 35, 30, 35, 40]
        })
        
        metrics = strategy.calculate_divergence(data)
        
        # Should prefer macd_hist
        assert 'macd_hist' in metrics.strategy_params['indicator_col']
    
    def test_no_suitable_indicator_raises(self, strategy):
        """Test that missing oscillator raises informative error."""
        data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200]
        })
        
        with pytest.raises(ValueError, match="No suitable indicator found"):
            strategy.calculate_divergence(data)
    
    def test_invalid_explicit_column_raises(self, strategy, bullish_divergence_macd):
        """Test that invalid explicit column raises error."""
        with pytest.raises(ValueError, match="Zone data must contain columns"):
            strategy.calculate_divergence(
                bullish_divergence_macd,
                indicator_col='invalid_column'
            )
    
    def test_insufficient_data_returns_empty(self, strategy):
        """Test that insufficient data returns empty metrics."""
        # Only 3 bars (need more for peak detection)
        data = pd.DataFrame({
            'close': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'macd_hist': [1, 2, 3]
        })
        
        metrics = strategy.calculate_divergence(data)
        
        assert metrics.divergence_count == 0
        assert metrics.divergence_type == 'none'
```

#### Результат Bugfix #5:

✅ **Divergence detection работает для:**
- MACD vs Price (backward compatible)
- RSI vs Price (новая поддержка)
- AO vs Price (новая поддержка)
- Stochastic vs Price (новая поддержка)
- CCI vs Price (новая поддержка)
- Любой oscillator vs Price

✅ **Концептуальная универсальность достигнута:**
- Дивергенция теперь по определению универсальна
- Работает с любым осциллятором

✅ **Тесты:**
- 11 новых unit tests
- Coverage: 100% новой функциональности

---

## Bugfix #6: StandardVolumeStrategy - универсализация (Low Priority)

**Файл:** `bquant/analysis/zones/strategies/volume/standard.py`

#### Проблема:

```python
# Текущий код (lines 87-97):
# Calculate volume-MACD correlation (if macd_hist available)
volume_macd_corr = None
if 'macd_hist' in zone_data.columns and len(zone_data) >= self.correlation_min_periods:
    try:
        volume_macd_corr = float(volume.corr(zone_data['macd_hist']))
        # Handle NaN correlation
        if pd.isna(volume_macd_corr):
            volume_macd_corr = None
    except Exception as e:
        logger.debug(f"Failed to calculate volume-MACD correlation: {e}")
        volume_macd_corr = None
```

**Impact:** Minor - основная функциональность работает, теряется 1 optional метрика.

#### Решение:

**Шаг 1: Обновить сигнатуру метода**

```python
# Update signature (line 41):
def calculate_volume(self, 
                    zone_data: pd.DataFrame, 
                    baseline_volume: Optional[float] = None,
                    indicator_col: str = None) -> VolumeMetrics:  # ✅ Add parameter
    """
    Calculate volume metrics for a zone.
    
    Args:
        zone_data: DataFrame with column: volume (and optionally oscillator)
        baseline_volume: Pre-calculated baseline volume (if None, will attempt to estimate)
        indicator_col: Oscillator column for volume-indicator correlation (optional)
                      Examples: 'macd_hist', 'RSI_14', 'AO_5_34'
                      If None, will auto-detect.
    
    Returns:
        VolumeMetrics with validated data
    
    Raises:
        ValueError: If volume column is missing
    
    Note:
        If baseline_volume is not provided and cannot be calculated,
        volume_zone_ratio and volume_at_entry_change will be None.
        
        If indicator_col is not found, volume_indicator_corr will be None.
    """
```

**Шаг 2: Добавить auto-detection + универсальный расчет correlation**

```python
# Replace lines 87-97 with:
# Calculate volume-indicator correlation (universal)
volume_indicator_corr = None

# Auto-detect indicator if not provided
if indicator_col is None:
    # Try to auto-detect (similar to shape strategy)
    if 'macd_hist' in zone_data.columns:
        indicator_col = 'macd_hist'
    elif any(col.startswith('RSI_') for col in zone_data.columns):
        indicator_col = next(col for col in zone_data.columns if col.startswith('RSI_'))
    elif any(col.startswith('AO_') for col in zone_data.columns):
        indicator_col = next(col for col in zone_data.columns if col.startswith('AO_'))
    # Don't raise error if not found - this is optional metric

if indicator_col and indicator_col in zone_data.columns:
    if len(zone_data) >= self.correlation_min_periods:
        try:
            volume_indicator_corr = float(volume.corr(zone_data[indicator_col]))
            # Handle NaN correlation
            if pd.isna(volume_indicator_corr):
                volume_indicator_corr = None
            else:
                logger.debug(
                    f"Volume-{indicator_col} correlation: {volume_indicator_corr:.3f}"
                )
        except Exception as e:
            logger.debug(f"Failed to calculate volume-indicator correlation: {e}")
            volume_indicator_corr = None

result = VolumeMetrics(
    volume_zone_ratio=volume_zone_ratio,
    volume_at_entry_change=volume_at_entry_change,
    volume_indicator_corr=volume_indicator_corr,  # ✅ Renamed
    avg_volume_zone=avg_volume_zone,
    strategy_name='standard',
    strategy_params={
        'baseline_window': self.baseline_window,
        'correlation_min_periods': self.correlation_min_periods,
        'indicator_col': indicator_col  # ✅ Track which was used
    }
)
```

**Шаг 3: Обновить VolumeMetrics dataclass**

```python
# In base.py, rename field:
@dataclass
class VolumeMetrics:
    """
    Volume metrics for a zone.
    
    Attributes:
        volume_zone_ratio: Ratio of average zone volume to baseline volume
        volume_at_entry_change: Percentage change in volume at zone entry vs baseline
        volume_indicator_corr: Correlation between volume and oscillator (universal)  # ✅ RENAMED
        avg_volume_zone: Average volume within the zone
        strategy_name: Name of strategy used
        strategy_params: Parameters used (including indicator_col)
    """
    volume_zone_ratio: Optional[float] = None
    volume_at_entry_change: Optional[float] = None
    volume_indicator_corr: Optional[float] = None  # ✅ Renamed from volume_macd_corr
    avg_volume_zone: float = 0.0
    strategy_name: str = 'standard'
    strategy_params: Dict[str, Any] = field(default_factory=dict)
```

**Шаг 4: Обновить docstring**

```python
# Update class docstring (lines 24-36):
@dataclass
class StandardVolumeStrategy:
    """
    Standard volume analysis strategy.
    
    Calculates:
    - Volume zone ratio: zone volume vs baseline
    - Volume at entry change: spike detection at zone entry
    - Volume-indicator correlation: volume confirmation (universal for any oscillator)
    - Average volume in zone
    
    Universal support:
        Works with any oscillator (MACD, RSI, AO, etc.) for correlation metric.
        If no oscillator found, volume_indicator_corr will be None (graceful degradation).
    
    Attributes:
        baseline_window: Number of bars before zone to calculate baseline (default: 50)
        correlation_min_periods: Minimum periods for correlation calculation (default: 3)
    """
```

#### Результат Bugfix #6:

✅ **Volume-indicator correlation работает для:**
- MACD (backward compatible, but renamed metric)
- RSI (новая поддержка)
- AO (новая поддержка)
- Любой oscillator (auto-detection)

✅ **API change (breaking, but minor):**
- `volume_macd_corr` → `volume_indicator_corr` (более точное название)
- Старый код сломается, но это редко используемая метрика

✅ **Graceful degradation:**
- Если indicator не найден, метрика = None (без errors/warnings)

---

## Часть 2: Архитектурные улучшения (Priority 1)

### Improvement #1: Создать StrategyConfig для унификации

**Файл:** `bquant/analysis/zones/strategies/base.py` (добавить)

```python
@dataclass
class StrategyConfig:
    """
    Universal configuration for all strategy types.
    
    Provides unified interface for indicator column specification,
    eliminating need for different parameter names across strategies.
    
    Attributes:
        indicator_col: Primary oscillator column (e.g., 'macd_hist', 'RSI_14', 'AO_5_34')
        indicator_line_col: Optional signal line (e.g., 'macd', 'RSI_MA', 'STOCHd')
        auto_detect: If True and indicator_col is None, auto-detect from data (default: True)
        fallback_to_price: If no indicator found, use price action (default: False)
    
    Example:
        # Explicit configuration
        config = StrategyConfig(
            indicator_col='RSI_14',
            auto_detect=False
        )
        
        # Auto-detection
        config = StrategyConfig(auto_detect=True)
        
        # 2-line configuration (Stochastic)
        config = StrategyConfig(
            indicator_col='STOCHk_14_3_3',
            indicator_line_col='STOCHd_14_3_3'
        )
    """
    indicator_col: Optional[str] = None
    indicator_line_col: Optional[str] = None
    auto_detect: bool = True
    fallback_to_price: bool = False
    
    def __post_init__(self):
        if not self.auto_detect and self.indicator_col is None:
            raise ValueError(
                "indicator_col must be specified when auto_detect=False"
            )
```

**Использование:** (опционально, можно интегрировать постепенно)

```python
# Вместо:
shape_metrics = shape_strategy.calculate(zone_data, indicator_col='RSI_14')

# Можно:
config = StrategyConfig(indicator_col='RSI_14')
shape_metrics = shape_strategy.calculate(zone_data, config=config)

# Или оставить backward compatibility:
shape_metrics = shape_strategy.calculate(zone_data, indicator_col='RSI_14')  # Still works
```

---

### Improvement #2: Создать IndicatorDetector utility

**Файл:** `bquant/analysis/zones/utils/indicator_detector.py` (создать новый)

```python
"""
Indicator column auto-detection utility.

Provides centralized logic for detecting oscillator columns in DataFrames,
eliminating code duplication across strategies.
"""

from typing import Optional, Tuple, List
import pandas as pd
from ....core.logging_config import get_logger

logger = get_logger(__name__)


class IndicatorDetector:
    """
    Utility for auto-detecting indicator columns in DataFrames.
    
    Provides consistent priority order and detection logic across all strategies.
    """
    
    # Priority order for main oscillator detection
    OSCILLATOR_PATTERNS = [
        ('macd_hist', lambda col: col == 'macd_hist'),
        ('RSI', lambda col: col.startswith('RSI_') and 'MA' not in col.upper()),
        ('AO', lambda col: col.startswith('AO_')),
        ('CCI', lambda col: col.startswith('CCI_')),
        ('STOCH', lambda col: col.startswith('STOCH') and 'k' in col.lower()),
        ('WILLR', lambda col: col.startswith('WILLR_')),
        ('MFI', lambda col: col.startswith('MFI_')),
    ]
    
    # Signal line patterns (for 2-line strategies like divergence)
    SIGNAL_LINE_MAPPING = {
        'macd_hist': 'macd',
        'RSI': lambda col: col.replace('RSI_', 'RSI_MA_') if 'RSI_' in col else None,
        'STOCH': lambda col: col.replace('STOCHk', 'STOCHd') if 'STOCHk' in col else None,
    }
    
    @classmethod
    def detect_oscillator(cls, data: pd.DataFrame, 
                         include_fallback: bool = True) -> Optional[str]:
        """
        Auto-detect primary oscillator column.
        
        Args:
            data: DataFrame to search
            include_fallback: If True, try any numeric column as fallback
        
        Returns:
            str: Detected column name, or None if not found
        
        Example:
            col = IndicatorDetector.detect_oscillator(zone_data)
            if col:
                values = zone_data[col]
        """
        # Check priority patterns
        for pattern_name, pattern_func in cls.OSCILLATOR_PATTERNS:
            matching_cols = [col for col in data.columns if pattern_func(col)]
            if matching_cols:
                detected = matching_cols[0]
                logger.debug(f"Auto-detected oscillator: {detected} (pattern: {pattern_name})")
                return detected
        
        # Fallback to any numeric column (excluding OHLCV)
        if include_fallback:
            excluded = {'open', 'high', 'low', 'close', 'volume', 'atr', 
                       'time', 'timestamp', 'date', 'datetime'}
            numeric_cols = data.select_dtypes(include=['number']).columns
            candidate_cols = [col for col in numeric_cols 
                            if col.lower() not in excluded]
            
            if candidate_cols:
                detected = candidate_cols[0]
                logger.warning(
                    f"No standard oscillator found, using fallback: {detected}"
                )
                return detected
        
        logger.debug("No suitable oscillator column found")
        return None
    
    @classmethod
    def detect_signal_line(cls, data: pd.DataFrame, 
                          oscillator_col: str) -> Optional[str]:
        """
        Auto-detect signal line for a given oscillator.
        
        Args:
            data: DataFrame to search
            oscillator_col: The main oscillator column
        
        Returns:
            str: Detected signal line column, or None if not found
        
        Example:
            osc_col = 'macd_hist'
            signal_col = IndicatorDetector.detect_signal_line(zone_data, osc_col)
            # Returns: 'macd'
        """
        # Try exact mappings first
        for pattern_name, signal_mapping in cls.SIGNAL_LINE_MAPPING.items():
            if pattern_name in oscillator_col or oscillator_col == pattern_name:
                if callable(signal_mapping):
                    candidate = signal_mapping(oscillator_col)
                else:
                    candidate = signal_mapping
                
                if candidate and candidate in data.columns:
                    logger.debug(
                        f"Auto-detected signal line for {oscillator_col}: {candidate}"
                    )
                    return candidate
        
        # Try heuristics
        # Pattern 1: RSI_14 → RSI_MA_14 or RSI_14_MA
        if 'RSI_' in oscillator_col:
            candidates = [
                col for col in data.columns 
                if 'RSI' in col and 'MA' in col.upper()
            ]
            if candidates:
                return candidates[0]
        
        # Pattern 2: STOCHk → STOCHd
        if 'STOCHk' in oscillator_col:
            candidate = oscillator_col.replace('STOCHk', 'STOCHd')
            if candidate in data.columns:
                return candidate
        
        logger.debug(f"No signal line found for {oscillator_col}")
        return None
    
    @classmethod
    def detect_both(cls, data: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
        """
        Auto-detect both oscillator and signal line.
        
        Args:
            data: DataFrame to search
        
        Returns:
            tuple: (oscillator_col, signal_line_col or None)
        
        Example:
            osc, signal = IndicatorDetector.detect_both(zone_data)
            if osc:
                # Use osc and optionally signal
        """
        oscillator = cls.detect_oscillator(data)
        signal = cls.detect_signal_line(data, oscillator) if oscillator else None
        return oscillator, signal
    
    @classmethod
    def list_available_oscillators(cls, data: pd.DataFrame) -> List[str]:
        """
        List all detected oscillator columns in data.
        
        Args:
            data: DataFrame to search
        
        Returns:
            list: All detected oscillator columns
        
        Example:
            oscillators = IndicatorDetector.list_available_oscillators(zone_data)
            print(f"Found {len(oscillators)} oscillators: {oscillators}")
        """
        found = []
        
        for pattern_name, pattern_func in cls.OSCILLATOR_PATTERNS:
            matching = [col for col in data.columns if pattern_func(col)]
            found.extend(matching)
        
        return found
```

**Использование:**

```python
# В shape strategy:
from ...utils.indicator_detector import IndicatorDetector

def _detect_oscillator_column(self, zone_data: pd.DataFrame) -> str:
    """Auto-detect oscillator column."""
    col = IndicatorDetector.detect_oscillator(zone_data)
    if col is None:
        raise ValueError("No suitable oscillator column found")
    return col

# В divergence strategy:
def _detect_indicator_columns(self, zone_data: pd.DataFrame) -> tuple:
    """Auto-detect indicator columns."""
    return IndicatorDetector.detect_both(zone_data)
```

**Преимущества:**
- ✅ Единый источник истины для detection logic
- ✅ Легко добавлять новые индикаторы (один раз в OSCILLATOR_PATTERNS)
- ✅ Консистентность между всеми strategies
- ✅ Легко тестировать (isolated utility)

---

## Часть 3: План тестирования

### Integration Tests

**Файл:** `tests/integration/test_universal_zone_analysis.py` (создать новый)

```python
"""
Integration tests for universal zone analysis.

Tests full pipeline with different indicators (MACD, RSI, AO, Stochastic).
"""
import pytest
import pandas as pd
import numpy as np
from bquant.analysis.zones import analyze_zones, analyze_macd_zones, analyze_rsi_zones, analyze_ao_zones
from bquant.data.samples import get_sample_data


class TestUniversalZoneAnalysisIntegration:
    """Integration tests across all zone analysis components."""
    
    @pytest.fixture
    def sample_data_macd(self):
        """Sample data with MACD indicator."""
        df = get_sample_data('tv_xauusd_1h')
        # Ensure MACD is calculated
        from bquant.indicators import IndicatorFactory
        macd = IndicatorFactory.create_indicator('custom', 'macd')
        result = macd.calculate(df)
        df['macd'] = result.data['macd']
        df['macd_signal'] = result.data['signal']
        df['macd_hist'] = result.data['histogram']
        return df.set_index('time')
    
    @pytest.fixture
    def sample_data_rsi(self):
        """Sample data with RSI indicator."""
        df = get_sample_data('tv_xauusd_1h')
        from bquant.indicators import IndicatorFactory
        rsi = IndicatorFactory.create_indicator('pandas_ta', 'rsi', length=14)
        result = rsi.calculate(df)
        df['RSI_14'] = result.data.iloc[:, 0]
        return df.set_index('time')
    
    @pytest.fixture
    def sample_data_ao(self):
        """Sample data with AO indicator."""
        df = get_sample_data('tv_xauusd_1h')
        from bquant.indicators import IndicatorFactory
        ao = IndicatorFactory.create_indicator('pandas_ta', 'ao', fast=5, slow=34)
        result = ao.calculate(df)
        df['AO_5_34'] = result.data.iloc[:, 0]
        return df.set_index('time')
    
    def test_macd_zones_full_pipeline(self, sample_data_macd):
        """Test full pipeline with MACD zones."""
        result = analyze_macd_zones(sample_data_macd, enable_cache=False)
        
        # Verify zones detected
        assert len(result.zones) > 0
        
        # Verify all analytics ran successfully
        assert result.statistics is not None
        assert 'total_statistics' in result.statistics
        
        # Verify shape metrics available (bugfix #4)
        zone_features = result.statistics.get('zone_features', [])
        if zone_features:
            first_zone = zone_features[0]
            assert 'shape_metrics' in first_zone.get('metadata', {})
            shape = first_zone['metadata']['shape_metrics']
            assert shape is not None
            assert 'hist_skewness' in shape
    
    def test_rsi_zones_full_pipeline(self, sample_data_rsi):
        """Test full pipeline with RSI zones - including shape metrics."""
        result = analyze_rsi_zones(
            sample_data_rsi,
            upper_threshold=70,
            lower_threshold=30,
            enable_cache=False
        )
        
        # Zones may or may not be detected depending on thresholds
        # But pipeline should run without errors
        assert result.statistics is not None
        
        # If zones detected, shape metrics should be available (bugfix #4)
        if len(result.zones) > 0:
            # Get first zone data
            first_zone = result.zones[0]
            assert first_zone.data is not None
            
            # Shape metrics should be calculated for RSI
            # (previously would fail with "zone_data must contain 'macd_hist' column")
            # Now should work or gracefully skip
    
    def test_ao_zones_full_pipeline(self, sample_data_ao):
        """Test full pipeline with AO zones - NO WARNINGS."""
        result = analyze_ao_zones(sample_data_ao, enable_cache=False)
        
        assert len(result.zones) > 0
        
        # ✅ Bugfix #4: No more warnings about macd_hist
        # Shape metrics should be calculated for AO zones
        zone_features = result.statistics.get('zone_features', [])
        if zone_features:
            first_zone = zone_features[0]
            metadata = first_zone.get('metadata', {})
            shape = metadata.get('shape_metrics')
            
            # Shape metrics should be present (not None)
            assert shape is not None
            assert 'hist_skewness' in shape
            assert 'hist_kurtosis' in shape
            
            # Verify it used AO column
            strategy_params = shape.get('strategy_params', {})
            assert 'AO_5_34' in strategy_params.get('indicator_col', '')
    
    def test_divergence_across_indicators(self, sample_data_macd, 
                                          sample_data_rsi, sample_data_ao):
        """Test divergence detection works across all indicators."""
        # MACD divergence
        result_macd = analyze_zones(sample_data_macd)\
            .with_indicator('custom', 'macd')\
            .detect_zones('zero_crossing', indicator_col='macd_hist')\
            .analyze()\
            .build()
        
        # RSI divergence (bugfix #5)
        result_rsi = analyze_zones(sample_data_rsi)\
            .with_indicator('pandas_ta', 'rsi', length=14)\
            .detect_zones('threshold', indicator_col='RSI_14', 
                         upper_threshold=70, lower_threshold=30)\
            .analyze()\
            .build()
        
        # AO divergence (bugfix #5)
        result_ao = analyze_zones(sample_data_ao)\
            .with_indicator('pandas_ta', 'ao', fast=5, slow=34)\
            .detect_zones('zero_crossing', indicator_col='AO_5_34')\
            .analyze()\
            .build()
        
        # All should complete without errors
        assert result_macd.zones is not None
        assert result_rsi.zones is not None
        assert result_ao.zones is not None
        
        # ✅ Bugfix #5: Divergence metrics available for all
        # (previously only worked for MACD)
    
    def test_no_warnings_for_non_macd_zones(self, sample_data_ao, caplog):
        """Test that AO zones don't produce MACD-related warnings."""
        import logging
        caplog.set_level(logging.WARNING)
        
        result = analyze_ao_zones(sample_data_ao, enable_cache=False)
        
        # Should have zones
        assert len(result.zones) > 0
        
        # ✅ No warnings about 'macd_hist' column
        warnings = [record for record in caplog.records 
                   if record.levelname == 'WARNING']
        macd_warnings = [w for w in warnings if 'macd' in w.message.lower()]
        
        assert len(macd_warnings) == 0, \
            f"Found MACD-related warnings for AO zones: {macd_warnings}"
```

---

## Часть 4: Документация и миграция

### Migration Guide

**Файл:** `docs/migration/universal_strategies.md` (создать)

```markdown
# Migration Guide: Universal Analytical Strategies

**Version:** Post-Bugfixes #4-6  
**Date:** 2025-10-18

## Overview

Analytical strategies (Shape, Divergence, Volume) are now fully universal,
supporting any oscillator (MACD, RSI, AO, Stochastic, etc.) instead of being
hardcoded for MACD.

## Breaking Changes

### 1. VolumeMetrics field renamed

**Old:**
```python
volume_metrics.volume_macd_corr  # ❌ Removed
```

**New:**
```python
volume_metrics.volume_indicator_corr  # ✅ Universal
```

**Impact:** If you accessed `volume_macd_corr` directly, update to `volume_indicator_corr`.

**Fix:**
```python
# Old code
corr = zone.metadata['volume_metrics']['volume_macd_corr']

# New code
corr = zone.metadata['volume_metrics']['volume_indicator_corr']
```

## New Features

### 1. Shape Strategy - Auto-detection

**Old behavior:** Only worked with MACD zones.

```python
# This would fail for RSI zones:
shape_strategy = StatisticalShapeStrategy()
metrics = shape_strategy.calculate(rsi_zone_data)  # ❌ ValueError: must contain 'macd_hist'
```

**New behavior:** Works with any oscillator.

```python
# Auto-detection (works for MACD, RSI, AO, etc.)
shape_strategy = StatisticalShapeStrategy()
metrics = shape_strategy.calculate(rsi_zone_data)  # ✅ Auto-detects RSI_14

# Explicit column
metrics = shape_strategy.calculate(rsi_zone_data, indicator_col='RSI_14')  # ✅ Explicit

# Check which column was used
print(metrics.strategy_params['indicator_col'])  # 'RSI_14'
```

### 2. Divergence Strategy - Universal Support

**Old behavior:** Only worked with MACD.

```python
# This would fail for RSI zones:
divergence_strategy = ClassicDivergenceStrategy()
metrics = divergence_strategy.calculate_divergence(rsi_zone_data)  # ❌ ValueError
```

**New behavior:** Works with any oscillator.

```python
# Auto-detection
divergence_strategy = ClassicDivergenceStrategy()
metrics = divergence_strategy.calculate_divergence(rsi_zone_data)  # ✅ Auto-detects RSI_14

# Explicit
metrics = divergence_strategy.calculate_divergence(
    rsi_zone_data, 
    indicator_col='RSI_14'
)  # ✅ Explicit

# 2-line divergence (Stochastic)
metrics = divergence_strategy.calculate_divergence(
    stoch_zone_data,
    indicator_col='STOCHk_14_3_3',
    indicator_line_col='STOCHd_14_3_3'
)  # ✅ Full support
```

### 3. Volume Strategy - Universal Correlation

**Old behavior:** Only `volume_macd_corr` metric.

```python
# Only worked with MACD
volume_strategy = StandardVolumeStrategy()
metrics = volume_strategy.calculate_volume(macd_zone_data)
print(metrics.volume_macd_corr)  # Only for MACD
```

**New behavior:** `volume_indicator_corr` for any oscillator.

```python
# Works with any indicator
volume_strategy = StandardVolumeStrategy()

# MACD zones (backward compatible)
metrics = volume_strategy.calculate_volume(macd_zone_data)
print(metrics.volume_indicator_corr)  # MACD correlation

# RSI zones
metrics = volume_strategy.calculate_volume(rsi_zone_data, indicator_col='RSI_14')
print(metrics.volume_indicator_corr)  # RSI correlation

# AO zones (auto-detect)
metrics = volume_strategy.calculate_volume(ao_zone_data)
print(metrics.volume_indicator_corr)  # AO correlation
```

## Benefits

1. **No more warnings:** AO/RSI zones no longer produce 36+ warnings about 'macd_hist'
2. **Full functionality:** Shape, divergence, volume metrics available for all indicators
3. **Backward compatible:** MACD zones work exactly as before
4. **Auto-detection:** No need to specify indicator column (but can if needed)
5. **Extensible:** Easy to add new indicators to detection priority

## Testing Your Code

Run these tests to verify compatibility:

```python
# Test 1: MACD zones (should work as before)
result = analyze_macd_zones(df)
assert len(result.zones) > 0

# Test 2: RSI zones (should now have shape metrics)
result = analyze_rsi_zones(df)
# Check for shape metrics in zone metadata
assert result.zones[0].metadata.get('shape_metrics') is not None

# Test 3: AO zones (should have no warnings)
import logging
logging.basicConfig(level=logging.WARNING)
result = analyze_ao_zones(df)
# Check logs - should be no "macd_hist" warnings

# Test 4: Volume metric rename
if hasattr(result.zones[0].metadata.get('volume_metrics'), 'volume_macd_corr'):
    print("WARNING: Update to volume_indicator_corr")
```

## Need Help?

- See `/docs/api/analysis/zones_universal.md` for full API reference
- See `/examples/universal_zones.py` for usage examples
- File issues at: github.com/yourorg/bquant/issues
```

---

## Часть 5: Checklist для реализации

### Phase 1: Critical Bugfixes (Priority 0) - 6 hours

- [ ] **Bugfix #4: Shape Strategy** (~2 hours)
  - [ ] Добавить `_detect_oscillator_column()` method
  - [ ] Обновить `calculate()` signature + implementation
  - [ ] Обновить docstrings
  - [ ] Создать 12 unit tests
  - [ ] Обновить вызов из `ZoneFeaturesAnalyzer`
  - [ ] Проверить: 0 warnings для AO zones

- [ ] **Bugfix #5: Divergence Strategy** (~3 hours)
  - [ ] Добавить `_detect_indicator_columns()` method
  - [ ] Обновить `calculate_divergence()` signature
  - [ ] Заменить `_find_macd_extrema` → `_find_indicator_extrema`
  - [ ] Обновить `_detect_divergences()` для универсальности
  - [ ] Обновить `DivergenceMetrics` dataclass
  - [ ] Создать 11 unit tests
  - [ ] Проверить: divergence работает для RSI/AO

- [ ] **Bugfix #6: Volume Strategy** (~1 hour)
  - [ ] Rename `volume_macd_corr` → `volume_indicator_corr`
  - [ ] Добавить auto-detection + универсальный расчет
  - [ ] Обновить `VolumeMetrics` dataclass
  - [ ] Обновить docstrings
  - [ ] Создать 5 unit tests

### Phase 2: Architecture (Priority 1) - 4 hours

- [ ] **Improvement #1: StrategyConfig** (~1 hour)
  - [ ] Создать `StrategyConfig` dataclass
  - [ ] Добавить в `base.py`
  - [ ] Опционально: интегрировать в strategies
  - [ ] Документировать

- [ ] **Improvement #2: IndicatorDetector** (~3 hours)
  - [ ] Создать `indicator_detector.py` utility
  - [ ] Реализовать `detect_oscillator()`
  - [ ] Реализовать `detect_signal_line()`
  - [ ] Реализовать `detect_both()`
  - [ ] Реализовать `list_available_oscillators()`
  - [ ] Создать 10 unit tests
  - [ ] Рефакторить strategies для использования utility

### Phase 3: Testing & Documentation (Priority 2) - 3 hours

- [ ] **Integration Tests** (~2 hours)
  - [ ] Создать `test_universal_zone_analysis.py`
  - [ ] Тест: MACD zones full pipeline
  - [ ] Тест: RSI zones full pipeline (with shape)
  - [ ] Тест: AO zones full pipeline (no warnings)
  - [ ] Тест: Divergence across all indicators
  - [ ] Тест: Volume correlation across all indicators

- [ ] **Documentation** (~1 hour)
  - [ ] Создать `universal_strategies.md` migration guide
  - [ ] Обновить API docs
  - [ ] Обновить примеры
  - [ ] Добавить troubleshooting раздел

### Phase 4: Validation (~2 hours)

- [ ] Запустить полный test suite
- [ ] Проверить backward compatibility (MACD zones)
- [ ] Проверить RSI zones: shape + divergence доступны
- [ ] Проверить AO zones: 0 warnings
- [ ] Проверить Stochastic zones: работают
- [ ] Проверить coverage: 95%+
- [ ] Code review
- [ ] Update CHANGELOG.md

---

## Total Effort Estimate

| Phase | Tasks | Time | Priority |
|-------|-------|------|----------|
| Phase 1: Critical Bugfixes | 3 bugfixes | 6 hours | 🔴 P0 |
| Phase 2: Architecture | 2 improvements | 4 hours | 🟡 P1 |
| Phase 3: Testing & Docs | Tests + docs | 3 hours | 🟢 P2 |
| Phase 4: Validation | QA + review | 2 hours | 🟢 P2 |
| **TOTAL** | **~15 hours** | **~2 days** | - |

**Реалистично:** 2-3 рабочих дня для полной универсальности.

---

## Expected Results

### Metrics

**Current State (Post-Bugfix #1-3):**
- Universality: 75%
- Zone Detection: 100% ✅
- Analytical Strategies: 60% ⚠️
- Warnings for AO zones: 36+
- Shape metrics for RSI: ❌ Not available
- Divergence for AO: ❌ Not available

**Target State (Post-All Bugfixes):**
- **Universality: 95%+** ✅
- Zone Detection: 100% ✅
- Analytical Strategies: 95%+ ✅
- **Warnings for AO zones: 0** ✅
- **Shape metrics for RSI: ✅ Available**
- **Divergence for AO: ✅ Available**
- **Volume-indicator correlation: ✅ Universal**

### User Experience

**Before:**
```python
# ❌ Warnings для AO zones
result = analyze_ao_zones(df)
# WARNING: Failed to calculate shape metrics: zone_data must contain 'macd_hist' column (×36)

# ❌ Shape недоступен для RSI
shape_strategy.calculate(rsi_zone_data)
# ValueError: zone_data must contain 'macd_hist' column

# ❌ Divergence только для MACD
divergence_strategy.calculate_divergence(rsi_zone_data)
# ValueError: Zone data must contain columns: ['macd_hist']
```

**After:**
```python
# ✅ Без warnings для AO zones
result = analyze_ao_zones(df)
# 36 zones detected, shape metrics available for all

# ✅ Shape доступен для RSI
shape_metrics = shape_strategy.calculate(rsi_zone_data)
# ShapeMetrics(hist_skewness=0.5, hist_kurtosis=3.2, indicator_col='RSI_14')

# ✅ Divergence для любого индикатора
divergence_metrics = divergence_strategy.calculate_divergence(rsi_zone_data)
# DivergenceMetrics(divergence_count=2, indicator_col='RSI_14')

# ✅ Volume correlation универсальна
volume_metrics = volume_strategy.calculate_volume(ao_zone_data)
# VolumeMetrics(volume_indicator_corr=0.65, indicator_col='AO_5_34')
```

---

## Conclusion

После реализации всех bugfixes и improvements, аналитический инструментарий BQuant станет **полностью универсальным (95%+)**, поддерживающим любые осцилляторы (MACD, RSI, AO, Stochastic, CCI, Williams %R, и т.д.) **без hardcoded зависимостей, без warnings, без заглушек, без обходных путей**.

**Ключевые принципы достигнутой универсальности:**
1. ✅ Auto-detection индикаторных колонок
2. ✅ Explicit параметры для контроля
3. ✅ Graceful degradation (если индикатор не найден)
4. ✅ Консистентные интерфейсы
5. ✅ Backward compatibility с MACD
6. ✅ Extensibility (легко добавлять новые индикаторы)

**Roadmap статус:** 
- Phase 1 (Bugfixes #4-6): 🔴 CRITICAL - начать немедленно
- Phase 2 (Architecture): 🟡 MEDIUM - после Phase 1
- Phase 3 (Testing/Docs): 🟢 LOW - финализация
- Phase 4 (Validation): 🟢 LOW - перед релизом

**Рекомендация:** Начать с Phase 1 (6 hours) для быстрого достижения 95% универсальности.

