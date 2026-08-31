# BQuant — Quantitative Research Toolkit

**BQuant** is a toolkit for quantitative research of financial markets. Its core is a
universal zone-analysis pipeline: it is not tied to any particular indicator and works
with any oscillator.

- **Documentation:** <https://bquant.readthedocs.io/>
- **Source:** <https://github.com/kogriv/bquant>

## Install

```bash
pip install bquant
```

Python 3.12+.

## Quick start

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

data = get_sample_data('tv_xauusd_1h')

# The pipeline is indicator-agnostic: swap the `.with_indicator()` call,
# everything else stays the same.
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_role='value',
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

print(len(result.zones))                              # 64
print(sorted({zone.type for zone in result.zones}))   # ['neutral', 'overbought', 'oversold']
```

A zone is addressed by **role** (`indicator_role='value'`), not by column name. Column
names depend on the library and on the call parameters and change with them; roles do not.

MACD zones in one line — a preset over the same pipeline:

```python
from bquant.analysis.zones import analyze_macd_zones
from bquant.data.samples import get_sample_data

result = analyze_macd_zones(get_sample_data('tv_xauusd_1h'))

print(len(result.zones))                              # 32
print(sorted({zone.type for zone in result.zones}))   # ['bear', 'bull']
```

Note that the zone vocabulary follows the indicator: an oscillator crossing zero yields
`bull`/`bear`, a bounded one yields `overbought`/`neutral`/`oversold`.

## What is in the box

**Zone analysis.** Five detection strategies (`zero_crossing`, `threshold`,
`line_crossing`, `preloaded`, `combined`) and five metric families (swing, shape,
divergence, volatility, volume), plus hypothesis testing and clustering over the
resulting zones.

**Indicators.** Built-in implementations (SMA, EMA, RSI, MACD, Bollinger Bands) and
anything from `pandas-ta` or TA-Lib through one factory:

```python
from bquant.data.samples import get_sample_data
from bquant.indicators import LibraryManager

data = get_sample_data('tv_xauusd_1h')

LibraryManager.load_all_libraries()
rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)

print(rsi.calculate(data).data.columns.tolist())   # ['RSI_14']
```

**Data.** OHLCV loading, processing and validation, with sample datasets embedded in the
package so that every example runs without external files.

**Visualization.** Interactive financial charts and statistical plots (Plotly, Matplotlib).

**Performance.** Vectorized computation and a two-level cache (memory + disk).

## Command line

```bash
bquant list                                  # available sample datasets
bquant analyze tv_xauusd_1h                  # zones, MACD by default
bquant analyze tv_xauusd_1h --indicator rsi  # any supported oscillator
bquant analyze --json --no-chart             # structured output, for programs
bquant analyze mt_xauusd_m15 -o chart.html   # save the chart
```

Every flag and the JSON schema: [CLI guide](https://bquant.readthedocs.io/en/latest/user_guide/cli.html).

## Documentation

| | |
|---|---|
| [Quick start](https://bquant.readthedocs.io/en/latest/user_guide/quick_start.html) | first result in five minutes |
| [Zone analysis pipeline](https://bquant.readthedocs.io/en/latest/api/analysis/pipeline.html) | the full builder reference |
| [Tutorials](https://bquant.readthedocs.io/en/latest/tutorials/README.html) | step-by-step scenarios |
| [API reference](https://bquant.readthedocs.io/en/latest/api/README.html) | module by module |
| [Developer guide](https://bquant.readthedocs.io/en/latest/developer_guide/README.html) | extending the package |

## Development

```bash
git clone https://github.com/kogriv/bquant.git
cd bquant
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[full]
pytest
```

Extras: `dev`, `docs`, `notebooks`, `research`, `full`.

Repository layout: `bquant/` is the package itself; `tests/`, `docs/` and `examples/`
support it; `research/` and `scripts/` hold notebook-style studies and automation.

## Status

Beta. The public API changes between releases without deprecation windows — renames are
carried through in one change, and `CHANGELOG.md` records every breaking change with its
replacement. Pin an exact version if you need stability.

Not in the package: machine learning. The `bquant.ml` placeholder was removed in 0.0.7
because both of its public functions only ever raised `NotImplementedError`.

## License

MIT — see [LICENSE](https://github.com/kogriv/bquant/blob/main/LICENSE).

## Contact

Author: kogriv · <kogriv@gmail.com>
