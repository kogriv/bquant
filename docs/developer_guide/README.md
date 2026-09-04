# Developer Guide - Руководство разработчика BQuant

## 📚 Обзор

Руководство разработчика собирает практические рекомендации по архитектуре Universal Pipeline v2.1, расширяемым точкам входа и качественным стандартам кода. Все примеры проверены на совместимость с текущими модулями `bquant`.

## 🗂️ Содержание

### 🏗️ Architecture — Universal Pipeline v2.1
- **Двухслойная архитектура** (детекция зон + универсальный анализатор) — см. [docs/api/analysis/pipeline.md](../api/analysis/pipeline.md)
- **Fluent Builder Pattern** — цепочка `.with_indicator().detect_zones().analyze().build()` из [ZoneAnalysisPipeline](../api/analysis/pipeline.md)
- **Strategy Pattern** — пять стратегий детекции и набор анализаторов подключаются через протоколы (`bquant.analysis.zones.detection`)
- **Dependency Injection** — `UniversalZoneAnalyzer` принимает кастомные компоненты (features, hypotheses, regression)
- **Registry Pattern** — стратегии и индикаторы регистрируются через реестры, что упрощает расширение
- **Open/Closed Principle** — основные модули закрыты для правок, но открыты для внедрения новых стратегий и индикаторов

### 🧠 Extension Playbooks
- [Создание собственной стратегии детекции зон](zone_detection_strategies.md)

### 🔧 Contributing — Как внести вклад
- Настройка среды разработки и зависимостей из `pyproject.toml`
- Процесс ветвления и ревью (см. раздел «🤝 Вклад» ниже)
- Code Style и стандарты (`black`, `flake8`, `mypy`)
- Создание качественных Pull Request с проверками `pytest`, `pre-commit`

### 🧪 Testing — Universal Pipeline Validation
- **Unit-тесты** проверяют зоны, индикаторы и модели (`tests/unit/`)
- **Integration-тесты** запускают пайплайн end-to-end (`tests/integration/`)
- **Backward compatibility** покрывает legacy API (`tests/unit/test_macd_backward_compatibility.py`)
- **Coverage** отслеживается через `pytest --cov` и HTML отчёт (`tests/` → `htmlcov/`)
- **Запуск локально:** `pytest`, `pytest --cov`, `pytest tests/unit/`, `pytest tests/integration/`

### ⚡ Performance — Caching & Optimization
- **Automatic Caching** — декораторы и `ZoneAnalysisPipeline` используют кеш на память/диск
- **Performance Benchmarks** — пример измерений в `bquant/core/performance.py`
- **Code Simplification** — модули анализа зон избавлены от дублирования, расчёты перенесены в универсальные компоненты
- **Lazy Loading** — показатели и анализаторы инициализируются по требованию

### 🔍 Debugging — Отладка и логирование
- Инструменты для расследования проблем в `bquant/core/logging_config.py`
- Централизованное логирование и форматирование (`setup_logging`)
- Обработка исключений через `bquant.core.exceptions`
- Диагностика пайплайна на основе контекстных логов и предупреждений

### 📦 Packaging — Упаковка и релизы
- Структура пакета описана в `pyproject.toml` и `bquant/__init__.py`
- Настройка `setuptools` и extras (`dev`, `docs`, `full`)
- Создание дистрибутивов: `python -m build`, публикация через `twine`
- Версионирование и CHANGELOG в каталоге `changelogs/`

### 🔄 CI/CD — Непрерывная интеграция
- GitHub Actions конфигурируются в `.github/workflows/` (после подключения CI)
- Автоматические тесты и статический анализ (`pytest`, `flake8`, `mypy`)
- Отслеживание качества: отчёты покрытия, статус чеков, контроль зависимостей

## 🎯 Целевая аудитория

### 👨‍💻 Разработчики
- **Новички** — начните с секций Contributing и Testing
- **Опытные** — изучите архитектуру и производительность
- **Эксперты** — сфокусируйтесь на CI/CD и Packaging

### 🏢 Команды
- **Open Source** — вклад в развитие проекта и обсуждения
- **Enterprise** — адаптация пайплайна под корпоративные требования
- **Research** — расширение аналитических компонентов для исследований

## 📋 Предварительные требования

### Технические навыки
- Python 3.10+
- Git и GitHub
- Тестирование (pytest)
- Документирование (Sphinx + MyST)

### Инструменты
```bash
# Основные инструменты
pip install pytest black flake8 mypy sphinx

# Дополнительные
pip install pre-commit tox coverage
```

## 🚀 Быстрый старт для разработчиков

### 1. Клонирование и настройка

```bash
# Клонируем репозиторий
git clone https://github.com/bquant-team/bquant.git
cd bquant

# Создаем виртуальное окружение
python -m venv venv_dev
source venv_dev/bin/activate  # Linux/Mac
# или
venv_dev\Scripts\activate     # Windows

# Устанавливаем в режиме разработки
pip install -e .[dev]
```

### 2. Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=bquant

# Только unit тесты
pytest tests/unit/

# Только integration тесты
pytest tests/integration/
```

### 3. Проверка качества кода

```bash
# Форматирование
black bquant/

# Линтинг
flake8 bquant/

# Типизация
mypy bquant/

# Все проверки
pre-commit run --all-files
```

## 🏗️ Архитектурные принципы

### Модульность
- **Разделение ответственности** — каждый модуль решает свою задачу (`core`, `data`, `analysis`, `visualization`)
- **Слабая связанность** — зависимости инкапсулированы через протоколы и фабрики
- **Высокая когезия** — логика зон, индикаторов и визуализации сгруппирована в соответствующих пакетах

### Расширяемость
- **Universal Pipeline** — работает с любым индикатором через `IndicatorFactory`
- **Strategy Pattern** — стратегии детекции и анализа подключаются через протоколы
- **Dependency Injection** — `UniversalZoneAnalyzer` принимает внешние анализаторы
- **Registry Pattern** — автоматическая регистрация стратегий и индикаторов

### Производительность
- **Automatic Caching** — кеширование в `ZoneAnalysisPipeline` и `performance_monitor`
- **Performance Benchmarks** — метрики `zones/sec` и отчёты в `bquant/core/performance.py`
- **Code Simplification** — переписанные на v2.1 модули минимизируют повторение кода
- **Lazy Loading** — компоненты и визуализаторы создаются по требованию

### Надежность
- **Обработка ошибок** — исключения из `bquant.core.exceptions`
- **Валидация данных** — схемы и валидаторы в `bquant/data/`
- **Тестирование** — покрытие критических путей unit и integration тестами

## 🔧 Extension Points

### Custom Detection Strategies
```python
from typing import List
from datetime import datetime

import pandas as pd

from bquant.analysis.zones.detection import ZoneDetectionConfig
from bquant.analysis.zones.models import ZoneInfo


class PositiveCloseStrategy:
    """Пример собственной стратегии на основе ZoneDetectionStrategy."""

    # NOTE: пример обновлен под контракт ZoneDetectionStrategy v2.1
    def detect_zones(self, data: pd.DataFrame, config: ZoneDetectionConfig) -> List[ZoneInfo]:
        config.validate(["indicator_col"])
        indicator = config.rules["indicator_col"]

        positives = data[data[indicator] > 0]
        if positives.empty:
            return []

        start_label = positives.index[0]
        end_label = positives.index[-1]
        start_idx = data.index.get_loc(start_label)
        end_idx = data.index.get_loc(end_label)

        zone = ZoneInfo(
            zone_id=0,
            type="bull",
            start_idx=start_idx,
            end_idx=end_idx,
            start_time=start_label.to_pydatetime(),
            end_time=end_label.to_pydatetime(),
            duration=end_idx - start_idx + 1,
            data=data.iloc[start_idx : end_idx + 1],
            indicator_context={
                "detection_strategy": "positive_close",
                "detection_indicator": indicator,
                "detection_rules": config.rules,
            },
        )
        return [zone]


strategy = PositiveCloseStrategy()
config = ZoneDetectionConfig(strategy_name="positive_close", rules={"indicator_col": "close"})
sample = pd.DataFrame(
    {"close": [-1.0, 0.2, 0.4, -0.1]}, index=pd.date_range("2024-01-01", periods=4, freq="h")
)
custom_zones = strategy.detect_zones(sample, config)
print(f"Зон найдено: {len(custom_zones)}")
```

> ℹ️  Подробный алгоритм реализации новых стратегий с шаблонами и чеклистами см. в документе
> [«Zone Detection Strategies — Developer Guide»](zone_detection_strategies.md).

### Custom Analysis Components
```python
from datetime import datetime
from typing import List

import pandas as pd

from bquant.analysis.zones.analyzer import UniversalZoneAnalyzer
from bquant.analysis.zones.models import ZoneInfo


class _DemoFeaturesAnalyzer:
    """Минимальная реализация извлечения признаков."""

    # NOTE: пример обновлен для демонстрации Dependency Injection.
    # `column_schema` обязателен: анализатор передаёт его именованным аргументом,
    # чтобы признаки резолвили колонки по ролям, а не по угаданным именам.
    def extract_all_zones_features(self, zones: List[ZoneInfo], column_schema=None):
        return [pd.Series({"zone_id": zone.zone_id, "duration": zone.duration}) for zone in zones]

    def analyze_zones_distribution(self, features):
        return {"zones_count": len(features)}


class _DemoHypothesisSuite:
    # `vocabulary` обязателен: анализатор передаёт словарь типов зон, чтобы тесты
    # знали объявленные свойства (polarity, counterpart), а не угадывали их по имени
    def run_all_tests(self, features, vocabulary=None):
        return {"duration_vs_return": {"significant": False, "alpha": 0.05}}


index = pd.date_range("2024-01-01", periods=3, freq="h")
data = pd.DataFrame({"close": [1.0, 1.2, 1.1]}, index=index)
zone = ZoneInfo(
    zone_id=1,
    type="bull",
    start_idx=0,
    end_idx=2,
    start_time=index[0].to_pydatetime(),
    end_time=index[-1].to_pydatetime(),
    duration=3,
    data=data,
    indicator_context={"detection_strategy": "demo", "detection_indicator": "close"},
)

analyzer = UniversalZoneAnalyzer(
    features_analyzer=_DemoFeaturesAnalyzer(),
    hypothesis_suite=_DemoHypothesisSuite(),
    sequence_analyzer=None,
    regression_analyzer=None,
    validation_suite=None,
)
analysis_result = analyzer.analyze_zones([zone], data, perform_clustering=False)
print(analysis_result.statistics["zones_count"])
```

### Custom Indicators
```python
import pandas as pd

from bquant.indicators.base import CustomIndicator, IndicatorFactory, IndicatorResult


class SpreadIndicator(CustomIndicator):
    """Пользовательский индикатор, рассчитывающий разницу между ценами."""

    # NOTE: пример обновлен под актуальный API IndicatorFactory.register_indicator
    def __init__(self):
        super().__init__("spread_indicator")

    def get_output_columns(self):
        return ["spread"]

    def get_description(self):
        return "Разница текущей цены и сглаженного значения"

    def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
        spread = data["close"].diff().fillna(0.0)
        frame = pd.DataFrame({"spread": spread}, index=data.index)
        return IndicatorResult(name=self.name, data=frame, config=self.config)


IndicatorFactory.register_indicator("spread_indicator", SpreadIndicator)
indicator = IndicatorFactory.create("custom", "spread_indicator")
sample_prices = pd.DataFrame({"close": [1.0, 1.2, 1.1]})
spread_result = indicator.calculate(sample_prices)
print(spread_result.data.tail(1))
```

## 📏 Code Quality Standards

### Type Hints
```python
from typing import Any, Dict

import pandas as pd

from bquant.analysis.zones.models import ZoneAnalysisResult


def analyze_zones(
    data: pd.DataFrame,
    indicator_config: Dict[str, Any],
    detection_config: Dict[str, Any],
) -> ZoneAnalysisResult:
    """Полная типизация публичного API."""
    # NOTE: пример возвращает пустой результат с метаданными
    return ZoneAnalysisResult(
        zones=[],
        statistics={"zones_count": 0, "indicator_config": indicator_config},
        hypothesis_tests={"executed": False},
    )


typed_result = analyze_zones(pd.DataFrame(), {}, {})
print(typed_result.statistics["zones_count"])
```

### Documentation
```python
class UniversalZoneAnalyzer:
    """Universal Zone Analyzer для анализа зон любого индикатора.

    Args:
        features_analyzer: Анализатор признаков зон
        hypothesis_analyzer: Анализатор статистических тестов
        sequence_analyzer: Анализатор последовательностей зон

    Example:
        >>> analyzer = UniversalZoneAnalyzer()
        >>> result = analyzer.analyze(data, config)
    """
    ...
```

### Error Handling
```python
import logging
from typing import Any

from bquant.core.exceptions import BQuantError


logger = logging.getLogger("bquant.docs.error_handling")


class OptionalModuleError(BQuantError):
    """Ошибка, возникающая при недоступности опционального компонента."""


def full_analysis(data: Any, config: dict) -> dict:
    raise OptionalModuleError("demo optional module is unavailable")


def basic_analysis(data: Any, config: dict) -> dict:
    return {"status": "fallback", "data_length": len(getattr(data, "index", []))}


def analyze_with_graceful_degradation(data, config):
    """Graceful degradation для опциональных компонентов."""

    # NOTE: пример использует BQuantError для отработки деградации
    try:
        return full_analysis(data, config)
    except BQuantError:
        logger.warning("Optional component is unavailable, switching to basic analysis")
        return basic_analysis(data, config)
```

### Performance
```python
import time
from functools import lru_cache

from bquant.core.performance import performance_context, performance_monitor


@performance_monitor()
def cached_indicator(value: int) -> int:
    """Декоратор профилирования фиксирует вызовы функции."""
    # NOTE: пример обновлен для совместимости с performance_monitor()
    return value * 2


@lru_cache(maxsize=128)
def expensive_calculation(params: int) -> int:
    """Кэширование сложных расчётов."""
    time.sleep(0.01)
    return params * 2


def create_analyzer():
    return {"name": "lazy_analyzer"}


class LazyZoneAnalyzer:
    def __init__(self):
        self._analyzer = None

    @property
    def analyzer(self):
        if self._analyzer is None:
            self._analyzer = create_analyzer()
        return self._analyzer


with performance_context("demo_operation"):
    cached_indicator(5)
    expensive_calculation(10)
```

## 🔧 Процесс разработки

### 1. Планирование
- **Issue creation** — создание задачи на GitHub
- **Requirements** — определение требований и критериев
- **Design** — проектирование решения и API

### 2. Разработка
- **Branch creation** — именование веток по шаблону `feature/` или `fix/`
- **Implementation** — реализация функциональности с покрытием тестами
- **Testing** — локальный запуск тестов и линтеров

### 3. Code Review
- **Self-review** — проверка собственного кода перед PR
- **Peer review** — ревью коллегами, использование checklist
- **CI checks** — успешное прохождение автоматических проверок

### 4. Integration
- **Merge** — слияние в основную ветку после апрува
- **Deployment** — подготовка релиза и публикация
- **Monitoring** — отслеживание метрик и логов

## 🧪 Тестирование

### Типы тестов

#### Unit Tests
```python
from datetime import datetime

import pandas as pd

from bquant.analysis.zones.models import ZoneAnalysisResult, ZoneInfo


def create_sample_zone() -> ZoneInfo:
    """Создаёт минимальную зону для unit-тестов."""
    # NOTE: пример обновлен для использования универсальных моделей v2.1
    index = pd.date_range("2024-01-01", periods=3, freq="h")
    data = pd.DataFrame({"close": [1.0, 1.1, 1.2]}, index=index)
    return ZoneInfo(
        zone_id=0,
        type="bull",
        start_idx=0,
        end_idx=2,
        start_time=index[0].to_pydatetime(),
        end_time=index[-1].to_pydatetime(),
        duration=3,
        data=data,
        indicator_context={"detection_strategy": "demo", "detection_indicator": "close"},
    )


def test_zone_result_shape():
    zone = create_sample_zone()
    result = ZoneAnalysisResult(zones=[zone], statistics={"zones_count": 1}, hypothesis_tests={})

    assert result.zones[0].zone_id == 0
    assert result.statistics["zones_count"] == 1
```

#### Integration Tests
```python
from pathlib import Path

import pandas as pd

from bquant.analysis.zones.models import ZoneAnalysisResult, ZoneInfo


def build_result() -> ZoneAnalysisResult:
    index = pd.date_range("2024-01-01", periods=2, freq="h")
    data = pd.DataFrame({"close": [1.0, 1.2]}, index=index)
    zone = ZoneInfo(
        zone_id=1,
        type="bull",
        start_idx=0,
        end_idx=1,
        start_time=index[0].to_pydatetime(),
        end_time=index[-1].to_pydatetime(),
        duration=2,
        data=data,
        indicator_context={"detection_strategy": "demo", "detection_indicator": "close"},
    )
    return ZoneAnalysisResult(zones=[zone], statistics={"zones_count": 1}, hypothesis_tests={})


def test_full_pipeline(tmp_dir: Path = Path("results")):
    """Интеграционный тест сериализации и загрузки результатов."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    target = tmp_dir / "dev_guide_demo.pkl"
    result = build_result()
    result.save(target, format="pickle", include_data=False)

    loaded = ZoneAnalysisResult.load(target, format="pickle")
    assert isinstance(loaded, ZoneAnalysisResult)

    target.unlink(missing_ok=True)
```

#### Performance Tests
```python
import time

import pandas as pd

from bquant.analysis.zones.models import ZoneAnalysisResult


def create_large_dataset(size: int = 5000) -> pd.DataFrame:
    return pd.DataFrame({"close": pd.Series(range(size))})


def test_performance_budget():
    """Тест производительности: генерация данных укладывается в бюджет."""
    start = time.perf_counter()
    data = create_large_dataset()
    elapsed = time.perf_counter() - start

    assert not data.empty
    assert elapsed < 0.5
```

### Покрытие тестами
```bash
# Генерация отчета о покрытии
pytest --cov=bquant --cov-report=html

# Минимальное покрытие
pytest --cov=bquant --cov-fail-under=80
```

## ⚡ Производительность

### Профилирование
```python
import pandas as pd

from bquant.core.performance import performance_context, performance_monitor


@performance_monitor()
def slow_function(df: pd.DataFrame) -> float:
    """Функция с профилированием."""
    return float(df["close"].mean())


with performance_context("operation_name"):
    slow_function(pd.DataFrame({"close": [1.0, 1.1, 1.2]}))
```

### Оптимизация
- **NumPy-векторизация** — избегайте Python-циклов
- **Кэширование** — сохраняйте повторно используемые расчёты
- **Параллелизм** — используйте multiprocessing для тяжёлых задач

## 🔍 Отладка

### Логирование
```python
import logging

from bquant.core.logging_config import setup_logging

# Настройка логирования
setup_logging(level="INFO")

# Использование в коде
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Обработка ошибок
```python
import logging

from bquant.core.exceptions import BQuantError, DataError


logger = logging.getLogger("bquant.docs.error")


class DummyAnalyzer:
    def analyze_complete(self, data):
        raise DataError("invalid data payload")


dummy_analyzer = DummyAnalyzer()

data = {"frame": "demo"}

try:
    dummy_analyzer.analyze_complete(data)
except DataError as e:
    logger.error(f"Data error: {e}")
except BQuantError as e:
    logger.error(f"BQuant error: {e}")
```

## 📦 Упаковка

### Структура пакета
```
bquant/
├── __init__.py
├── core/
├── data/
├── indicators/
├── analysis/
├── visualization/
└── ...
```

### Настройка pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "bquant"
version = "0.0.0"
description = "Quantitative analysis library for financial data"
# ... остальные настройки
```

## 🔄 CI/CD

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .[dev]
      - name: Run tests
        run: |
          pytest --cov=bquant
```

## 🤝 Вклад в проект

### Типы вкладов
- **Bug fixes** — исправление ошибок
- **Feature requests** — добавление функциональности
- **Documentation** — улучшение документации
- **Performance** — оптимизация производительности
- **Testing** — расширение покрытия тестами

### Процесс
1. **Fork** репозитория
2. **Create** ветку для фичи или исправления
3. **Implement** изменения с тестами
4. **Test** локально (`pytest`, `pre-commit`)
5. **Submit** Pull Request с описанием и результатами тестов

## 🔗 Связанные разделы

- **[User Guide](../user_guide/README.md)** — Руководство пользователя
- **[API Reference](../api/README.md)** — Справочник API
- **[Tutorials](../tutorials/README.md)** — Обучающие материалы
- **[Examples](../examples/README.md)** — Примеры использования

## 📞 Поддержка разработчиков

### Каналы связи
- **GitHub Issues** — для багов и проблем
- **GitHub Discussions** — для вопросов и обсуждений
- **Pull Requests** — для предложений изменений

### Ресурсы
- **[Contributing Guidelines](../../README.md)** — рекомендации по участию
- **[Code of Conduct](../../LICENSE)** — правила поведения
- **[License](../../LICENSE)** — лицензия проекта

---

**Начать изучение:** [API Pipeline](../api/analysis/pipeline.md) 🏗️
