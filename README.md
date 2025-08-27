# BQuant - Quantitative Research Toolkit

**BQuant** is a universal toolkit for quantitative research of financial markets. The project starts with MACD zone analysis as the first use case, but the architecture is designed for exploring various aspects: technical indicators, chart patterns, candlestick formations, time series, and machine learning applications.

## 🔧 Key Features

- **Universal configuration system** - support for multiple data sources and brokers
- **Multi-level analysis** - technical, statistical, graphical, candlestick, time series
- **ML readiness** - structure for machine learning (stubs)
- **Visualization tools** - charts and reports
- **Research environment** - notebooks and experiments
- **Automated pipelines** - ready-to-use analysis scripts

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
from bquant.data import load_symbol_data
from bquant.indicators import MACDAnalyzer

# Load data
data = load_symbol_data('XAUUSD', '1h')

# Analyze MACD zones
analyzer = MACDAnalyzer(data, fast=8, slow=21)
zones = analyzer.identify_zones()

print(f"Found {len(zones)} zones")
```

### Command Line

```bash
# Analyze single instrument
bquant-analyze XAUUSD

# Batch analysis
bquant-batch EURUSD GBPUSD XAUUSD
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
python -m venv venv_bquant_dell

# Activate (Windows)
venv_bquant_dell\Scripts\activate

# Activate (Linux/Mac)
source venv_bquant_dell/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .[dev]
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

- **Phase 1**: Core functionality (data, MACD analysis, statistics)
- **Phase 2**: Extended visualization, time series, other indicators
- **Phase 3**: Full ML, chart patterns, automation

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## 📞 Contact

- **Author**: kogriv
- **Email**: kogriv@gmail.com
- **Repository**: https://github.com/kogriv/bquant
