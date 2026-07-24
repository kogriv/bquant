# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [Unreleased]

## [0.0.3] - 2026-07-24

### Added
- **`confirmation_index` для стратегий `find_peaks` и `pivot_points`** — маркер причинной
  доступности свинга теперь заполняется всеми свинг-стратегиями, а не только ZigZag (0.0.2).
  Для `pivot_points` это точное fractal-подтверждение (`index + right_bars`); для `find_peaks` —
  causal leak-free (`max(index + distance, бар prominence-ретрейса справа)`). Позволяет строить
  look-ahead-free потребителей на любой свинг-стратегии. (PR #108)

### Changed
- **`CACHE_SCHEMA_VERSION` повышена 2 → 3** — `find_peaks`/`pivot_points` теперь заполняют
  `confirmation_index`, что меняет семантику кэшируемого вывода; старые кэши инвалидируются.

### Fixed
- **ZigZag: мягкая деградация при отсутствии pandas-ta `zigzag`.** В глобальном режиме
  (`swing_scope='global'`) стратегия теперь возвращает пустой `SwingContext` с понятным
  предупреждением вместо исключения, когда опциональный индикатор pandas-ta `zigzag`
  недоступен — как уже делал per-zone режим. Пайплайн больше не логирует ошибку/traceback
  на этом пути.

## [0.0.2] - 2026-07-20

### Added
- **`SwingPoint.confirmation_index`** — маркер причинной доступности свинга: индекс
  бара, к которому пивот (и его `amplitude_to_next`) причинно подтверждён. Позволяет
  строить leak-free / look-ahead-free потребителей (устранение утечки J1). Реализован
  для ZigZag-стратегии; прочие свинг-стратегии оставляют `None` (контракт допускает
  мягкую деградацию). Сериализуется в `SwingContext.to_dict()`. (PR #107)

### Changed
- **`CACHE_SCHEMA_VERSION` повышена до 2** — ключ дискового кэша зон-анализа теперь
  учитывает версию схемы вывода, инвалидируя старые кэши без `confirmation_index`.
  Инвариант: любое изменение схемы/семантики кэшируемого вывода обязано бампать
  `CACHE_SCHEMA_VERSION`.

## [0.0.1] - 2026-01-12

### Added
- Initial release of BQuant package
- Complete migration from Quanto project
- Comprehensive technical analysis framework
- MACD zone analysis with statistical testing
- Advanced data processing and validation
- Professional visualization system
- Embedded sample data for testing
- CLI scripts for analysis automation
- Complete documentation and examples
- **Zone Metrics Visualization (v1.0)** - 2025-11-11
  - Aggregate metrics display with `show_aggregate_metrics` parameter (compact/full modes)
  - Swing points visualization on charts with `show_swings` parameter
  - Detail mode zone metrics with `show_zone_metrics` parameter
  - Date range filtering with automatic metrics recalculation for selected period
  - Support for unbalanced swings in global swing mode
  - See [docs/api/visualization/zones.md](docs/api/visualization/zones.md) for details


## [0.0.0] - 2024-08-25

### Added
- Foundation for BQuant project
- Basic project structure
- Core configuration system
- Initial test framework
- Initial beta release
- Basic MACD analysis functionality
- Core data processing capabilities
- Preliminary documentation

### Structure

- **Core Modules**: Configuration, exceptions, logging, performance, utilities
- **Data Modules**: Loader, processor, validator, samples, schemas
- **Indicators**: Base classes, MACD analyzer, factory pattern
- **Analysis**: Statistical analysis, zone analysis, hypothesis testing
- **Visualization**: Financial charts, zone visualization, statistical plots, themes
- **Research Structure**: Notebooks, methodology, experiments, studies
- **Scripts**: Analysis automation, data processing, deployment tools
- **Documentation**: Complete API reference, user guide, tutorials, examples

### Technical Features
- **MACD Zone Analysis**: Advanced MACD analysis with zone identification
- **Statistical Testing**: Comprehensive hypothesis testing framework
- **Data Processing**: Robust data loading, cleaning, and validation
- **Performance Optimization**: Caching system and optimized algorithms
- **Visualization**: Professional charts with multiple themes
- **Sample Data**: Embedded financial data for testing and examples

### Architecture
- **Modular Design**: Clean separation of concerns
- **Type Safety**: Full type hints and validation
- **Error Handling**: Comprehensive exception system
- **Logging**: Professional logging with multiple levels
- **Testing**: Complete test coverage with pytest
- **Documentation**: Sphinx-based documentation system

### Dependencies
- **Core**: pandas, numpy, matplotlib, seaborn
- **Analysis**: scipy, scikit-learn, statsmodels
- **Visualization**: plotly, seaborn
- **Development**: pytest, black, flake8, mypy

---

## Version History

### Semantic Versioning
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in backward-compatible manner
- **PATCH**: Backward-compatible bug fixes

### Release Schedule
- **Major releases**: Every 6 months
- **Minor releases**: Every 2-4 weeks
- **Patch releases**: As needed for critical fixes

### Support Policy
- **Current version**: Full support
- **Previous major version**: Bug fixes only
- **Older versions**: No support

---

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- Original Quanto project contributors
- Open source financial analysis community
- Python packaging and documentation tools
