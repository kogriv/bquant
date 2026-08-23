# BQuant - Quantitative Research Toolkit

**BQuant** is a universal toolkit for quantitative research of financial markets. The project starts with MACD zone analysis as the first use case, but the architecture is designed for exploring various aspects: technical indicators, chart patterns, candlestick formations, time series, and machine learning applications.

## 🔧 Key Features

### Zone Analysis - Universal Pipeline v2.1
- **Universal API**: Works with any indicator (MACD, RSI, AO, custom) through fluent builder pattern
- **5 Detection Strategies**: zero_crossing, threshold, line_crossing, preloaded, combined
- **Advanced Analysis**: Swing, divergence, volume, volatility strategies with automatic feature extraction
- **Statistical Testing**: Automatic hypothesis tests and clustering analysis
- **Caching Support**: Performance optimization with memory and disk caching

### Core Features
- **Universal Configuration System**: Flexible settings for data sources, indicators, and analysis
- **Extensible Indicator Library**: Includes optimized built-in indicators and supports external libraries like `pandas-ta` and `TA-Lib`
- **ML Readiness**: A modular structure prepared for future machine learning integration
- **Rich Visualization Tools**: Create interactive financial charts and statistical plots with Plotly and Matplotlib
- **Performance-Oriented**: Features a two-level caching system and performance monitoring tools
- **Command-Line Interface**: Provides a simple CLI for quick analysis and data management

## 🚀 Quick Start

### Installation

```bash
# Install in development mode
pip install -e .

# Install with optional dependencies
pip install -e .[dev,notebooks]
```

### Basic Usage - Universal Pipeline v2.1

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

# Load sample data
data = get_sample_data('tv_xauusd_1h')

# Universal Pipeline - работает с любым индикатором
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

print(f"Found {len(result.zones)} zones")
print(f"Statistics: {result.statistics}")
```

### MACD-зоны в одну строку

```python
from bquant.analysis.zones import analyze_macd_zones

result = analyze_macd_zones(data)  # пресет поверх того же пайплайна
```

> `MACDZoneAnalyzer` (и обёртки `create_macd_analyzer` / `analyze_macd_zones` из
> `bquant.indicators.macd`) **удалён**. Замена — пресет выше либо полный билдер
> `analyze_zones(...)`. Сам индикатор MACD не менялся.

#### pandas-ta indicators in one line

```python
from bquant.indicators import LibraryManager

# Load external libraries (pandas-ta, TA-Lib when installed)
LibraryManager.load_all_libraries()

# "Simple way" to access any pandas-ta indicator discovered dynamically
rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)
result = rsi.calculate(data)
print(result.data.tail())
```

See the [LibraryManager documentation](docs/api/indicators/library_manager.md) for more examples.

### Command Line

```bash
# List available sample datasets
bquant list

# Analyze a dataset using default settings
bquant analyze tv_xauusd_1h

# Analyze and save the chart to a file
bquant analyze mt_xauusd_m15 -o chart.html
```

## 📋 Project Structure

This is a monorepo that contains:

- **`bquant/`** - Python package (for PyPI)
- **`research/`** - Jupyter notebooks and experiments
- **`scripts/`** - Automation scripts
- **`data/`** - Data storage
- **`tests/`** - Test suite
- **`docs/`** - Documentation

## 🛠️ Development

### Setting up development environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode with all extras
pip install -e .[full]
```

### Running tests

```bash
pytest tests/ -v
```

## 📚 Documentation

### Universal Pipeline v2.1
- **[Quick Start](docs/user_guide/quick_start.md)** - 5 минут до первого результата
- **[API Reference](docs/api/analysis/pipeline.md)** - полная документация Universal Pipeline
- **[Examples](examples/02a_universal_zones.py)** - готовые примеры для всех индикаторов
- **[Migration Guide](examples/02_macd_zone_analysis.py)** - переход с deprecated API

### Complete Documentation
- **[API Documentation](docs/api/)** - Справочник API
- **[Tutorials](docs/tutorials/)** - Обучающие материалы
- **[Examples](docs/examples/)** - Примеры использования
- **[Developer Guide](docs/developer_guide/)** - Руководство разработчика

### Architecture
- **Two-Layer Design**: Simplification from 3 to 2 layers
- **Zero Hardcode**: ZERO hardcoded indicators, full universality
- **Design Patterns**: Strategy, Dependency Injection, Builder, Registry
- **Test Suite**: 1155 tests, green on every release

## 🎯 Roadmap

- **Phase 1 (Completed)**: Core functionality (data loading, processing, validation), advanced MACD analysis, and statistical engine.
- **Phase 2 (In Progress)**: Extended visualization options, implementation of Time Series and other indicator analysis modules (currently stubs).
- **Phase 3 (Planned)**: Full machine learning integration, chart pattern recognition, and enhanced automation pipelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## 📞 Contact

- **Author**: kogriv
- **Email**: kogriv@gmail.com
- **Repository**: https://github.com/kogriv/bquant
