# AGENTS.md

Single source of truth for agent/developer instructions in this repository. Agent-specific
entry files (`CLAUDE.md`, `GEMINI.md`, `VIBE.md`) are thin pointers that import this file;
Cursor and other tools read `AGENTS.md` directly. Edit instructions **here**, not in the pointers.

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
- **`processor.py`**: Cleaning, resampling, derived values (`calculate_true_range`, `calculate_atr`), `resolve_time_index`
- **`samples/`**: Embedded sample datasets for testing and examples
- **`validator.py`**: Data validation and quality checks
- **`schemas.py`**: Data structure definitions

### Indicators (`bquant/indicators/`)
- **`base.py`**: Base classes and `IndicatorFactory` for custom and library-backed indicators
- **`calculators.py`**: Core indicator calculation functions
- **`MACDZoneAnalyzer` was removed** (module `indicators/macd.py` deleted; deprecated since v2.1). MACD zone analysis is now the Universal Pipeline — `analyze_zones(...)` or the `analyze_macd_zones(...)` preset in `bquant.analysis.zones`. The MACD *indicator* itself is unchanged (`custom/macd.py`, `preloaded/macd.py`, calculators).
- **`library/`**: Integration with pandas-ta and TA-Lib (`manager.py`, `pandas_ta.py`, `talib.py`) — a package, not a single module

### Analysis (`bquant/analysis/`)
- **`zones/`**: **Universal Zone Analysis Pipeline v2.1** — `analyze_zones()` fluent builder (`pipeline.py`); pluggable zone-detection strategies (`detection/`: zero_crossing, threshold, line_crossing, preloaded, combined); metric strategies (`strategies/`: swing, shape, divergence, volatility, volume); zone models (`models.py`), presets (`presets.py`), feature extraction (`zone_features.py`), sequence analysis (`sequence_analysis.py`)
- **`statistical/`**: Statistical analysis and hypothesis testing
- **`validation/`**: `ValidationSuite` (out-of-sample, walk-forward, sensitivity, Monte Carlo) over a `MetricSpec`
- **`technical/`, `chart/`, `candlestick/`, `timeseries/`**: stubs (`is_stub = True`); `analyze()` raises `NotImplementedError`, and the factory catalog lists only executable analyzers

### Visualization (`bquant/visualization/`)
- **`charts.py`**: Financial chart creation with Plotly
- **`zones.py`**: Zone-specific visualization tools
- **`themes.py`**: Chart themes and styling

## Key Design Patterns

### Universal Zone Analysis Pipeline (flagship API)
The primary way to analyze zones is the `analyze_zones()` fluent builder — indicator-agnostic,
works with any oscillator. It replaced `MACDZoneAnalyzer` (removed).

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')       # swing/shape/divergence/volatility/volume
    .with_swing_preset('narrow_zone')      # optional: 'narrow_zone' (default) | 'wide_zone'
    .analyze(clustering=True)
    .build()
)

print(f"Zones: {len(result.zones)}")
# result.data is the indicator-augmented frame; pass it (not the raw input) to visualizers.
```

**📖 Full Documentation:** `docs/api/analysis/pipeline.md` (builder reference),
`docs/user_guide/swing_strategies.md` (swing config).

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

# Get the path a symbol's data file would have
data_file = get_data_path('XAUUSD', '1h')

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

@performance_monitor()          # a decorator *factory*: the parentheses are required (G43)
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
- `tests/integration/`: Tests for module interactions (includes the docs-example runner)
- `tests/analysis/`, `tests/performance/`, `tests/visualization/`: topic suites
- `tests/fixtures/`: Shared test data and utilities

Every guard test written for a gap record is **mutation-verified**: revert the fix and the
test must go red. A test that passes on the defect is not a test (`devref/gaps/`).

### Performance Tests
Include performance validation in tests, especially for indicator calculations and data processing.

### Documentation Parity
Four layers keep the docs from drifting: `tests/unit/test_docs_parity.py` (links resolve,
imported names exist), call-signature checks, `tests/integration/test_docs_examples_run.py`
(every **self-contained** python block executes), and
`tests/unit/test_public_surface_is_documented.py` (every re-exported name is mentioned
somewhere). Renaming or moving an API therefore fails the suite until the docs change in
the same commit. Numbers in prose come from running the example, never transcribed.

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

## This Is a Public Repository — No Internal Infrastructure

**BQuant is public (GitHub + GitLab + PyPI). Nothing about the owner's private infrastructure
belongs in it — not in code, not in docs, not in `devref/`, and not in `changelogs/`.**

Never commit:
- **Credentials of any kind** — keys, tokens, passwords, `.pypirc` contents, `authorized_keys`.
- **Access topology** — hostnames, IPs, ports, SSH aliases or `ProxyJump` chains, tunnel setups,
  VM/container names, names of private machines or build stands.
- **Personal filesystem paths** — `C:\Users\<name>\...`, `/home/<name>/...`. Use repo-relative
  paths or neutral placeholders in examples and scripts.
- **The contents of private sibling projects** — their research, data, findings, and
  internal reasoning. The *name* of a sibling repository is fine: it is a repo name on the
  owner's own account, it appears in this repo's history already, and referring to "the
  external consumer" while everyone knows which one it is buys nothing. What must stay out
  is what happens inside it.

This applies to trace logs too. A trace log records *what changed in this repository* — the fact
that a measurement ran on some other machine is infrastructure, not project history. If a hardware
detail is genuinely needed to read a number (e.g. "single-threaded, so core count does not help"),
state the **property**, not the machine.

Internal infrastructure documentation lives outside the repo, in `/data/infra/`.

**Before committing, grep the diff** for: your own username, `ssh`, `ProxyJump`, host names,
`C:\Users`, `/home/`, `token`, `.pypirc`, and the names of private machines. Sibling *repository*
names are not on this list — see above.

If something already slipped through, say so plainly and treat removing it as its own task —
redacting `HEAD` does not remove it from history that has already been pushed.

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