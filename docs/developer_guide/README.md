# Руководство разработчика

Как устроен пакет, где его точки расширения и что обязано быть зелёным перед коммитом.
Все примеры на этой странице самодостаточны и исполняются слоем проверок
(`tests/integration/test_docs_examples_run.py`); всё остальное сверено с репозиторием
2026-09-05.

## Что где лежит

| Пакет | Что в нём |
|---|---|
| `bquant.core` | конфигурация (`config.py`), кэш, производительность, логирование, исключения, `NotebookSimulator` |
| `bquant.data` | загрузка CSV, чистка и производные величины (`processor`), валидация, схемы, встроенные сэмплы |
| `bquant.indicators` | базовые классы и фабрика, пять встроенных индикаторов, обёртки pandas-ta/TA-Lib, идентичность колонок (`schema.py`) |
| `bquant.analysis` | пайплайн зон (`zones/`), статистика и регрессия (`statistical/`), валидация (`validation/`), четыре модуля-заглушки |
| `bquant.visualization` | графики и темы |

Архитектура пайплайна зон — два слоя: **детекция** (пять стратегий в
`bquant.analysis.zones.detection`, реестр `ZoneDetectionRegistry`) и **анализ**
(`UniversalZoneAnalyzer` с внедряемыми компонентами: признаки, гипотезы,
последовательности, регрессия, валидация). Вход — билдер `analyze_zones(df)`;
справочник — [pipeline.md](../api/analysis/pipeline.md), механика —
[глубокое погружение](zone_analyzer_deep_dive.md).

## Окружение

Пакет требует **Python ≥ 3.12** (`pyproject.toml`). Зависимости для разработки — extras
`dev` (`pytest`, `pytest-cov`, `black`, `flake8`), `docs` (Sphinx + MyST), `notebooks`,
`full`.

```bash
git clone https://github.com/kogriv/bquant.git
cd bquant
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Конфигурация есть у `black` и `coverage` (секции `[tool.*]` в `pyproject.toml`); файлов
`.flake8`, `mypy.ini`, `.pre-commit-config.yaml` и каталога `.github/workflows` в
репозитории **нет** — линтер зовётся руками, CI не подключён. Гейт релиза — сьют из
чистого клона с зависимостями, как они разрешаются сегодня, плюс контрольное плечо на
нижней поддерживаемой версии pandas (`bquant-release-process` в трейслогах).

## Что обязано быть зелёным

```bash
pytest -q                       # весь сьют
pytest tests/unit/ -q           # только модульные
pytest --cov=bquant             # с покрытием (порог не настроен — число, не гейт)
```

Каталоги: `tests/unit/`, `tests/integration/`, `tests/analysis/`, `tests/performance/`,
`tests/visualization/`, фикстуры в `tests/fixtures/`. Тестов обратной совместимости со
старым API нет — старый API удалён в 0.0.5, совместимость не обещается.

Кроме сьюта, перед релизом фактически исполняются `examples/*.py` и
`research/notebooks/*.py --no-trap` под `MPLBACKEND=Agg` — сьют ловит только их импорты.

Четыре слоя проверок доков: ссылки и имена (`tests/unit/test_docs_parity.py`), вызовы,
исполнение самодостаточных примеров (`tests/integration/test_docs_examples_run.py`),
упоминание каждого публичного имени (`tests/unit/test_public_surface_is_documented.py`).
Переименовали API — те же коммитом правьте доки, иначе покраснеет.

## Точки расширения

### Своя стратегия детекции

Класс с методом `detect_zones(data, config) -> List[ZoneInfo]`; регистрация —
`@ZoneDetectionRegistry.register(...)`. Подробный шаблон и чеклист —
[zone_detection_strategies.md](zone_detection_strategies.md).

```python
from typing import List

import pandas as pd

from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.models import ZoneInfo


class PositiveCloseStrategy:
    """Одна зона: от первого положительного значения до последнего."""

    def detect_zones(self, data: pd.DataFrame, config: ZoneDetectionConfig) -> List[ZoneInfo]:
        config.validate(["indicator_col"])
        indicator = config.rules["indicator_col"]

        positives = data[data[indicator] > 0]
        if positives.empty:
            return []

        start_idx = data.index.get_loc(positives.index[0])
        end_idx = data.index.get_loc(positives.index[-1])
        return [ZoneInfo(
            zone_id=0, type="bull", start_idx=start_idx, end_idx=end_idx,
            start_time=positives.index[0], end_time=positives.index[-1],
            duration=end_idx - start_idx + 1, data=data.iloc[start_idx:end_idx + 1],
            indicator_context={"detection_strategy": "positive_close",
                               "detection_indicator": indicator,
                               "detection_rules": dict(config.rules)},
        )]


sample = pd.DataFrame({"close": [-1.0, 0.2, 0.4, -0.1]},
                      index=pd.date_range("2024-01-01", periods=4, freq="h"))
zones = PositiveCloseStrategy().detect_zones(
    sample, ZoneDetectionConfig(strategy_name="positive_close", rules={"indicator_col": "close"})
)
print(len(zones), zones[0].duration)
# 1 2
```

### Свои компоненты анализа

`UniversalZoneAnalyzer` принимает компоненты конструктором. Контракты: признаки —
`extract_all_zones_features(zones, column_schema=None)` и
`analyze_zones_distribution(features)`; гипотезы — `run_all_tests(features, vocabulary=None)`;
регрессия — `explain_zone_duration`/`explain_price_return`; валидация —
`out_of_sample_test(analyze_func, data, metric, train_ratio=...)`. Полный перечень —
[zone_detection_strategies.md](zone_detection_strategies.md#интерфейсы-расширения).

```python
from typing import List

import pandas as pd

from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
from bquant.analysis.zones.models import ZoneInfo


class _DemoFeaturesAnalyzer:
    def extract_all_zones_features(self, zones: List[ZoneInfo], column_schema=None):
        return [pd.Series({"zone_id": zone.zone_id, "duration": zone.duration}) for zone in zones]

    def analyze_zones_distribution(self, features):
        return {"zones_count": len(features)}


class _DemoHypothesisSuite:
    def run_all_tests(self, features, vocabulary=None):
        return {"tests": {}, "summary": {"total_tests": 0}}


index = pd.date_range("2024-01-01", periods=3, freq="h")
data = pd.DataFrame({"close": [1.0, 1.2, 1.1]}, index=index)
zone = ZoneInfo(zone_id=1, type="bull", start_idx=0, end_idx=2, start_time=index[0],
                end_time=index[-1], duration=3, data=data,
                indicator_context={"detection_strategy": "demo", "detection_indicator": "close"})

analyzer = UniversalZoneAnalyzer(features_analyzer=_DemoFeaturesAnalyzer(),
                                 hypothesis_suite=_DemoHypothesisSuite())
result = analyzer.analyze_zones([zone], data, perform_clustering=False)
print(result.statistics["zones_count"], result.hypothesis_tests["summary"]["total_tests"])
# 1 0
```

`None` в конструкторе означает «компонент по умолчанию», а не «без компонента».

### Свой индикатор

Наследник `CustomIndicator` с `get_output_columns()`, `get_required_columns()`,
`get_min_records(**params)` и `calculate()`. `validate_data()` **поднимает**
`DataValidationError`, а не возвращает `False` — проверять её результат не нужно.

```python
import pandas as pd

from bquant.indicators.base import CustomIndicator, IndicatorFactory, IndicatorResult


class SpreadIndicator(CustomIndicator):
    def __init__(self):
        super().__init__("spread_indicator")

    def get_output_columns(self):
        return ["spread"]

    def get_required_columns(self):
        return ["close"]

    def get_description(self):
        return "Bar-to-bar change of the close"

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        self.validate_data(data)
        frame = pd.DataFrame({"spread": data["close"].diff()}, index=data.index)
        return IndicatorResult(name=self.name, data=frame, config=self.config)


IndicatorFactory.register_indicator("spread_indicator", SpreadIndicator)
indicator = IndicatorFactory.create("custom", "spread_indicator")
print(indicator.calculate(pd.DataFrame({"close": [1.0, 1.2, 1.1]})).data["spread"].tolist())
# [nan, 0.19999999999999996, -0.10000000000000009]
```

Стратегии метрик зон (свинги, форма, дивергенции, волатильность, объём) — в
[extension_guide.md](../api/extension_guide.md): там протоколы, реестр и исполняемый пример.

## Стандарты

- **Типы и докстринги** — на публичном API. Докстринг с примером обязан исполняться:
  пример, называющий несуществующий метод, хуже отсутствия примера.
- **Ошибки** — иерархия `bquant.core.exceptions` (`BQuantError` → `DataError`,
  `AnalysisError`, …). Не превращать отказ в правдоподобный результат: ноль вместо
  метрики, `None` вместо ошибки и `False` в лог вместо исключения — три формы одного
  дефекта, на которых держится реестр гэпов (`devref/gaps/`).
- **Числа в доках — из прогона**, не переписанные. Меняется поведение — меняется число
  тем же коммитом.
- **Логирование** — `setup_logging(level=...)` из `bquant.core.logging_config`; модули
  берут логгер через `get_logger(__name__)`.
- **Производительность** — `performance_monitor()` и `performance_context()` из
  `bquant.core.performance`; в тестах утверждать свойство (счётчик вызовов), а не
  секундомер.

```python
import pandas as pd

from bquant.core.performance import performance_context, performance_monitor


@performance_monitor()
def mean_close(df: pd.DataFrame) -> float:
    return float(df["close"].mean())


with performance_context("demo"):
    print(mean_close(pd.DataFrame({"close": [1.0, 1.1, 1.2]})))
# 1.1
```

## Изменения и релизы

- `CHANGELOG.md` в корне — по Keep a Changelog; подробные трейслоги по дням — в
  `changelogs/`, формат в `changelogs/README.md`.
- Каждый найденный дефект — запись в `devref/gaps/` с замером до и после, мутацией
  сторожа и ценой; строка в `devref/gaps/gap_inventory_2026-07.md`.
- Сборка — `python -m build`, публикация — `twine`; версия в трёх местах
  (`pyproject.toml`, `bquant/__init__.py`, `uv.lock`), тег `vX.Y.Z`.
- Репозиторий публичный: ни адресов, ни имён машин, ни личных путей — правило в
  `AGENTS.md`.

## См. также

- [Пайплайн](../api/analysis/pipeline.md) · [Глубокое погружение](zone_analyzer_deep_dive.md)
  · [Стратегии детекции](zone_detection_strategies.md) · [Расширение](../api/extension_guide.md)
- [User Guide](../user_guide/README.md) · [API Reference](../api/README.md)
