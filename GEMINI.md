# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BQuant is a quantitative research toolkit for financial markets, starting with MACD zone analysis but designed for extensibility. The project follows a modular architecture with clear separation between data processing, indicators, analysis, and visualization.


## Architecture Overview

### Core Modules (`bquant/core/`)
- **`config.py`**: Universal configuration system with timeframe mapping for different data providers
- **`nb.py`**: NotebookSimulator class for creating notebook-style Python scripts with step-by-step execution
- **`cache.py`**: Two-level caching system (memory + disk) for performance optimization
- **`performance.py`**: Performance monitoring and optimization utilities
- **`logging_config.py`**: Centralized logging configuration
- **`exceptions.py`**: Custom exception hierarchy for different error types

### Data Layer (`bquant/data/`)
- **`loader.py`**: CSV data loading with automatic format detection (OANDA, MetaTrader)
- **`processor.py`**: Data processing and indicator calculation pipeline
- **`samples/`**: Embedded sample datasets for testing and examples
- **`validator.py`**: Data validation and quality checks
- **`schemas.py`**: Data structure definitions

### Indicators (`bquant/indicators/`)
- **`macd.py`**: Advanced MACD analyzer with zone detection, clustering, and statistical analysis
- **`calculators.py`**: Core indicator calculation functions
- **`base.py`**: Base classes for custom indicators
- **`library.py`**: Integration with pandas-ta and TA-Lib

### Analysis (`bquant/analysis/`)
- **`zones/`**: Zone analysis algorithms (sequence analysis, feature extraction)
- **`statistical/`**: Statistical analysis and hypothesis testing
- **`technical/`**: Technical analysis modules (mostly stubs for future implementation)

### Visualization (`bquant/visualization/`)
- **`charts.py`**: Financial chart creation with Plotly
- **`zones.py`**: Zone-specific visualization tools
- **`themes.py`**: Chart themes and styling

## Key Design Patterns

### NotebookSimulator Pattern
For research scripts, use the NotebookSimulator class to create notebook-style execution with step-by-step execution, automatic CLI argument parsing, and rich logging.

**Quick example:**
```python
from bquant.core.nb import NotebookSimulator

nb = NotebookSimulator("My Analysis Description")
nb.step("Data Loading")
# your code here
nb.wait()
nb.finish()
```

**📖 Full Documentation:** See `docs/api/core/nb.md` for complete API reference, examples, and best practices.

### Configuration Pattern
Use the centralized configuration system:

```python
from bquant.core.config import get_data_path, get_indicator_params, PROJECT_ROOT

# Get configured paths
data_dir = get_data_path()

# Get indicator parameters
macd_params = get_indicator_params('macd')
```

### Sample Data Pattern
Always use sample data for examples and tests:

```python
from bquant.data.samples import get_sample_data, list_datasets

# Load sample data
data = get_sample_data('tv_xauusd_1h')  # TradingView OANDA data
data = get_sample_data('mt_xauusd_m15')  # MetaTrader data

# List available datasets
datasets = list_datasets()
```

### Performance Monitoring
Use built-in performance monitoring for analysis functions:

```python
from bquant.core.performance import performance_monitor, performance_context

@performance_monitor
def my_analysis_function(data):
    # your code here
    pass

# Or use as context manager
with performance_context("My Operation"):
    # time-intensive code
    pass
```

## Data Handling

### Supported Data Sources
- **OANDA** (via TradingView): `OANDA_SYMBOL, TIMEFRAME.csv`
- **MetaTrader**: `SYMBOLTIMEFRAME.csv` (e.g., `XAUUSDH1.csv`)

### Timeframe Conventions
The system uses universal timeframe mapping:
- Minutes: `1m`, `5m`, `15m`, `30m`
- Hours: `1h`, `4h`, `12h`
- Daily+: `1d`, `1w`, `1M`

### Column Standards
Expected OHLCV columns: `['time', 'open', 'high', 'low', 'close', 'volume']`
Additional columns preserved but not required.

## Testing Strategy

### Sample Data Usage
All examples and tests should use embedded sample data from `bquant.data.samples`. Never hardcode paths to external CSV files.

### Test Structure
- `tests/unit/`: Fast tests for individual modules
- `tests/integration/`: Tests for module interactions
- `tests/fixtures/`: Shared test data and utilities

### Performance Tests
Include performance validation in tests, especially for indicator calculations and data processing.

## Common Patterns to Avoid

### Don't Create External Dependencies
- Always use sample data for examples
- Don't hardcode file paths 
- Don't assume external data files exist

### Don't Skip Error Handling
- Use the custom exception hierarchy from `bquant.core.exceptions`
- Wrap critical operations in try-catch blocks
- Use the NotebookSimulator's `error_handling()` context manager for research scripts

### Don't Ignore Performance
- Use caching for expensive operations
- Monitor performance with the built-in tools
- Prefer vectorized pandas operations over loops

## Research Scripts

Research scripts in `research/notebooks/` use the NotebookSimulator pattern. These are Python files that simulate Jupyter notebook behavior with automatic CLI argument parsing, step-by-step execution, rich logging, error handling, and automatic cleanup.

**📖 Full Documentation:** See `docs/api/core/nb.md` for complete API reference, detailed examples, and advanced usage patterns.

## Changelog Management

BQuant uses a two-level changelog system:
1. **Daily Change Trace Logs** - Detailed real-time tracking in `changelogs/CHANGE_TRACE_LOG_YYYY-MM-DD.md`
2. **Main Changelog** - Curated user-facing changelog in `CHANGELOG.md`

**Key Rules:**
- One file per date (append to existing file, never create duplicates)
- Use structured format: `[HH:MM:SS] [status] [type] [description]`
- Transfer to main changelog when 5+ significant changes accumulate

**📖 Complete Documentation:** See `changelogs/README.md` for detailed format specifications, workflow, transfer criteria, and examples.