# BQuant - Quantitative Research Toolkit

**BQuant** is a universal toolkit for quantitative research of financial markets. The project starts with MACD zone analysis as the first use case, but the architecture is designed for exploring various aspects: technical indicators, chart patterns, candlestick formations, time series, and machine learning applications.

## 🔧 Key Features

- **Universal Configuration System**: Flexible settings for data sources, indicators, and analysis.
- **Advanced Analysis Engine**: In-depth statistical analysis, hypothesis testing, and a powerful engine for analyzing trading zones (MACD, Support/Resistance).
- **Extensible Indicator Library**: Includes optimized built-in indicators (MACD, RSI, etc.) and supports external libraries like `pandas-ta` and `TA-Lib`.
- **ML Readiness**: A modular structure prepared for future machine learning integration.
- **Rich Visualization Tools**: Create interactive financial charts (candlestick, line) and statistical plots with Plotly and Matplotlib.
- **Performance-Oriented**: Features a two-level caching system (memory & disk) and performance monitoring tools.
- **Command-Line Interface**: Provides a simple CLI for quick analysis and data management.

## 🚀 Quick Start

### Installation

```bash
# Install in development mode
pip install -e .

# Install with optional dependencies
pip install -e .[dev,notebooks]
```

### Basic Usage

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import MACDZoneAnalyzer

# Load sample data
data = get_sample_data('tv_xauusd_1h')

# Analyze MACD zones
# The analyzer automatically calculates MACD and other required indicators
analyzer = MACDZoneAnalyzer()
zones = analyzer.identify_zones(data)

print(f"Found {len(zones)} MACD zones")
```

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

- [API Documentation](docs/api/)
- [Tutorials](docs/tutorials/)
- [Examples](docs/examples/)

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
