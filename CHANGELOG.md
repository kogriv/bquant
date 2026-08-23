# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).



## [Unreleased]

### Fixed
- **Колонки индикаторов из pandas-ta больше не подписаны чужими параметрами (G18).**
  Имена колонок вычислялись **один раз при регистрации** индикатора — на синтетических
  данных, с дефолтными параметрами — и затем подставлялись при каждом расчёте, затирая
  имена, которые вернула сама библиотека. `rsi(length=50)` считался правильно, pandas-ta
  называла результат `RSI_50`, а bquant переименовывал колонку в **`RSI_14`**: значения
  верные, подпись ложная. Плюс два экземпляра с разными параметрами получали одно имя и
  затирали друг друга. Теперь имена берутся из фактического вызова, а объявление
  (`get_output_columns()`) выводится из параметров конкретного экземпляра.
  **Что изменится у вас:** если вы передавали параметры, отличные от дефолтных, колонка теперь
  называется по ним (`RSI_50` вместо `RSI_14`) — обновите обращения к ней. Для вызовов
  без параметров имена не изменились.
  Разбор: `devref/gaps/columns/g8_column_contract_measurement_2026-08-23.md`.

### Added
- **Предупреждение, когда индикатор затирает колонку входных данных (G17).** Пайплайн
  дописывает результат индикатора в кадр безусловным присваиванием. Встроенный сэмпл
  TradingView несёт собственную колонку `macd`, поэтому расчёт MACD подменял её —
  расхождение до 5.84 по ряду, молча (на последнем баре числа совпадают, так что
  проверка по хвосту ничего не замечала). Затирание сохранено — кто-то намеренно
  пересчитывает индикатор, пришедший с данными, — но теперь оно называется вслух, с
  перечислением затронутых колонок. Предупреждение возникает на «холодном» прогоне;
  результат, поднятый из кэша, его не повторяет.


## [0.0.5] - 2026-08-23

### Removed
- **`MACDZoneAnalyzer` удалён (ломающее изменение).** Вместе с ним удалены модуль
  `bquant/indicators/macd.py` и обёртки `create_macd_analyzer` / `analyze_macd_zones`,
  которые из него ре-экспортировались, а также ре-экспорты из `bquant/indicators/__init__.py`.
  Класс был помечен deprecated с v2.1 и представлял собой тонкую обёртку, делегировавшую
  в Universal Zone Analysis pipeline, — сам пайплайн от него никогда не зависел.
  Сам **индикатор** MACD не тронут (`custom/macd.py`, `preloaded/macd.py`, calculators).

  Миграция:
  ```diff
  - from bquant.indicators.macd import MACDZoneAnalyzer      # удалено
  + from bquant.analysis.zones import analyze_macd_zones     # пресет
  + from bquant.analysis.zones import analyze_zones          # полный билдер
  ```
  Пресет считает по тому же пайплайну и даёт тот же результат. Учтите форвардный дефолт
  зон: `analyze_macd_zones` детектирует по **линии MACD**, а не по гистограмме, как делал
  удалённый класс, — при сравнении со старыми артефактами передавайте
  `zone_basis='histogram'`. См. `docs/migration/MIGRATION_v2.md`.

  **О номере версии.** Deprecation-предупреждение класса обещало удаление в «v3.0.0» —
  это была нумерация внутренней ветки разработки, которая до публикации не дожила:
  на PyPI пакет вышел с 0.0.x и туда `MACDZoneAnalyzer` уже попал как deprecated.
  Мажорной версии 3.0.0 у публичного пакета не было и не будет, поэтому удаление
  происходит на 0.0.5. Если вы ориентировались на текст того предупреждения —
  ориентир был неверен, и это наша недоработка, а не смена условий.

### Fixed
- **Адаптивные пороги больше не отключают фильтр проминенции у `find_peaks` (G16).**
  `auto_swing_thresholds` возвращает **относительные** величины, но одна из них
  присваивалась в `strategy.prominence`, который у find_peaks **абсолютный**, в единицах
  цены. Доля ≈0.019 при цене ~3350 $ читалась как порог **меньше двух центов** — фильтр
  переставал фильтровать, и адаптивный режим давал **больше** свингов, чем обычный
  (377 против 295), то есть ровно обратное тому, зачем его включают. Теперь адаптивный
  слой `prominence` **не трогает вовсе**: у find_peaks есть собственный адаптивный к
  диапазону порог, и после G15 он ещё и заморожен на warm-up-окне. Слой отдаёт только
  относительный `min_amplitude_pct`. `zigzag` и `pivot_points` не были затронуты —
  им доли уходили в поля, которые сами относительные.
  Разбор: `devref/gaps/swing/g16_adaptive_threshold_units_2026-08-22.md`.
- **Авто-проминенция `find_peaks` больше не «уплывает» под усечением (G15).** При
  `prominence=None` — это **дефолт** стратегии — порог выводился из всего наблюдённого
  ценового диапазона, а он может только расти. Экстремум, прошедший ранний меньший порог
  и объявленный подтверждённым, позже проваливал больший и **исчезал** из результата.
  `confirmation_index` этого не лечил: двигался сам фильтр. Теперь порог **замораживается
  на первых `prominence_warmup` барах** (новый параметр, по умолчанию 200) и не
  пересчитывается — усечение серии не меняет эти бары, поэтому реплей воспроизводит тот же
  порог. Проверено на **48 конфигурациях** (2 датасета × distance 2/3/5/10 × 6 длин
  прогрева, контрольные точки каждые 5 баров): нарушений 0 в обоих направлениях оракула,
  против **8 из 8** конфигураций со старым поведением (98 исчезающих свингов).
  Замер: `devref/gaps/swing/g15_auto_prominence_measurement_2026-08-22.md`.

### Changed
- **`SwingThresholds.peak_prominence` переименован в `peak_min_amplitude`** — имя провоцировало
  присваивание в `strategy.prominence`, с чего и начался G16. Соответственно переименован ключ
  в метаданных `last_thresholds` (пользовательски видимо). В докстринге датакласса зафиксировано,
  что **все его поля — доли, а не цены**.
- **В адаптивном режиме `find_peaks` детектирует меньше свингов** (377 → 295 на встроенном
  сэмпле) — фильтр проминенции снова работает. Прочие стратегии не затронуты.
- **Детекция на дефолте `find_peaks` немного изменилась — строго в сторону добавления.**
  Замороженный порог ниже того, до которого дорастал прежний, поэтому засчитывается больше
  мелких экстремумов (**+12 % при `prominence_warmup=200`**), но **ни один ранее найденный
  свинг не пропадает** (`removed = 0` во всех 48 конфигурациях). Добавляются хвосты:
  медианная проминенция добавленных 1.66 против 6.26 у сохранённых.
- **Пока баров меньше `prominence_warmup`, `confirmation_index` не выставляется** ни у
  одного свинга, и стратегия пишет предупреждение. Порог по `N` барам нельзя знать раньше,
  чем набралось `N` баров, — обещать доступность в этот момент было бы той же дырой.
  Свинги при этом детектируются как прежде. С **явным `prominence` прогрев не действует**:
  константа не нуждается в оценке, подтверждения не задерживаются.
- **`CACHE_VERSION` 4 → 6, `CACHE_SCHEMA_VERSION` 4 → 6** — изменился сам набор
  детектируемых свингов, а не только их `confirmation_index`. Старые кэши инвалидируются.

### Documentation
- **Документация приведена в соответствие с удалением `MACDZoneAnalyzer`.** Часть страниц
  всё ещё описывала класс как «deprecated», то есть существующий: титульная страница Sphinx
  (`docs/index.rst`) содержала рабочий пример его импорта, `docs/api/README.md` — полное
  описание класса в разделе «как читать документацию», `docs/api/indicators/README.md` —
  раздел «Legacy API (Deprecated)». Всё переведено в «удалён в 0.0.5» с указанием замены;
  миграционные страницы (`docs/migration/MIGRATION_v2.md`, `quick_start.md`) намеренно
  сохраняют старые сниппеты — они там нужны, и помечены как неисполняемые.
- **Убраны фантомные символы из индекса API.** `docs/api/indicators/README.md` перечислял
  `IndicatorRegistry` и `identify_zones()`, которых в пакете нет вообще, а `research/README.md`
  предлагал в качестве рекомендуемого блока импортов `from bquant.indicators import MACDAnalyzer`
  — класс с таким именем не существовал никогда (имя из архивного дизайн-документа).
  `calculate_macd()` уточнён до модуля `bquant.indicators.calculators`, где он и живёт.
- **Версия в документации Sphinx больше не расходится с пакетом.** `docs/conf.py` держал
  `release = '0.0.1'` четыре релиза подряд, потому что ничто не связывало его с реальной
  версией; теперь читается из `bquant.__version__`.
- **Число тестов в README исправлено** — там стояло «115 Tests», фактически 1155.
- **Проверка «документация ↔ код» расширена.** Она не видела ни `.rst` (то есть титульную
  страницу Sphinx), ни markdown вне `docs/` (`examples/README.md`, `research/README.md`),
  а многострочные импорты `from ... import (…)` молча пропускала — 11 блоков в документации
  не проверялись вообще. Всё три дыры закрыты, охват вырос со 401 до 429 проверок.

### Added
- **`FindPeaksSwingStrategy.prominence_warmup`** (по умолчанию 200) — длина окна прогрева
  для авто-порога. Больше — представительнее оценка волатильности, но длиннее «слепое окно»
  в начале истории. См. `docs/user_guide/swing_strategies.md`.

## [0.0.4] - 2026-08-18

Релиз о **честности `confirmation_index`**: в 0.0.2/0.0.3 поле было заявлено как маркер
причинной доступности для leak-free потребителей, но ни одна из трёх свинг-стратегий не
удовлетворяла контракту строго. Теперь удовлетворяют все три — проверено оракулом, который
пере-прогоняет **реальный детектор** под усечением сырого OHLC.

### Fixed
- **ZigZag `confirmation_index` теперь replay-causal (issue #110).** `calculate_global` вызывает
  pandas-ta zigzag с `backtest=True` — не перерисовывающий поток вместо дефолтного центрированного
  `backtest=False`, который под усечением сырого OHLC добавлял/двигал/удалял ранние пивоты.
  `_confirmation_index` — дивиденс-ретрейс без искусственного floor; первый пивот наследует
  confirmation второго (детектор не эмитит ничего до 2-й свинги). Repaint-нарушения на встроенном
  сэмпле: **35% → 0%**, стабильно на legs∈{2,3,5}. (PR #111)
- **`find_peaks` и `pivot_points` доведены до строгой replay-safety (G14).** У `find_peaks`
  причина оказалась не в prominence, как предполагалось изначально, а в **порядке фильтров
  scipy**: `distance` применяется **до** `prominence`, жадно по высоте и по всему множеству сырых
  локальных максимумов, поэтому экстремум, подавленный более высоким соседом, оживает, когда
  сосед сам снимается ещё более высоким справа. Confirmation теперь ждёт устаканивания всей
  цепочки подавления, а не фиксированного окна `index + distance`. У `pivot_points` N-баровый
  паттерн локален и точен, но контекст не эмитится, пока экстремумов меньше двух, — поэтому
  первый пивот наследует confirmation второго, как в ZigZag. Нарушений **0 на 12 конфигурациях**;
  цена — 3 экстремума из 345 подтверждаются позже (в среднем +0.035 бара).

### Changed
- **`CACHE_VERSION` 2 → 4, `CACHE_SCHEMA_VERSION` 3 → 4** — сериализованная семантика свингов и
  значения `confirmation_index` изменились дважды (ZigZag `backtest=True`; устаканивание
  distance-цепочки и warm-up первого свинга). Старые кэши инвалидируются.

### Added
- **`tests/unit/test_swing_replay_causal.py`** — оракул replay-каузальности: пере-прогон реального
  детектора под усечением, а не monkeypatch фиксированного списка пивотов. Покрывает обе стороны
  контракта: свинг, объявленный доступным на баре `t`, обязан (а) уже присутствовать при расчёте
  на `data[:t+1]` и (б) не исчезнуть из полной истории позже.

### Known limitations
- **Авто-prominence `find_peaks` не устойчив к усечению (G15).** При `prominence=None` — это
  **дефолт** стратегии — порог выводится из наблюдённого диапазона цен и растёт по мере прихода
  баров (на встроенном сэмпле 1.275 → 2.071). Экстремум, прошедший ранний меньший порог, позже
  проваливает больший и исчезает. `confirmation_index` это не лечит: движется сам фильтр.
  **Кому нужна replay-safety — задавайте `prominence` явно**, тогда нарушений нет. Исправление
  требует смены семантики детекции и будет отдельным решением.

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
