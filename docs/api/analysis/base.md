# Базовые классы анализа — bquant.analysis

## Обзор

Базовая инфраструктура анализа находится в `bquant.analysis.__init__` и включает общие классы и фабрики.

## Классы

- `AnalysisResult`
  - Поля: `analysis_type`, `timestamp`, `data_size`, `results`, `metadata`
  - Методы: `to_dict()`, `save_to_csv(file_path)`

- `BaseAnalyzer`
  - Конструктор: `BaseAnalyzer(name, config=None)`
  - Методы:
    - `validate_data(data) -> bool`
    - `analyze(data, **kwargs) -> AnalysisResult` (абстрактный)
    - `prepare_data(data) -> DataFrame`
  - Атрибут класса: `is_stub: bool` — по умолчанию `False`; заглушки объявляют `True`,
    и по нему их следует отличать, а не по названию модуля (см. [обзор](README.md))

## Функции

- `get_available_analyzers() -> Dict[str, str]`: имена, которые `create_analyzer()` умеет
  **собрать и запустить**, и что каждое означает. Выводится из `SUPPORTED_ANALYSIS_TYPES`,
  и каждое имя отображено на настоящий класс — на это стоит пин.
- `get_planned_analyzers() -> Dict[str, str]`: направления, под которые есть модуль-заглушка
  (`is_stub = True`), но нет анализатора: `technical`, `chart`, `candlestick`, `timeseries`.
  Отдельный перечень, а не пометка в общем: «что запустить» и «что запланировано» — разные
  вопросы.
- `create_analyzer(analyzer_type: str, **kwargs) -> BaseAnalyzer`: фабрика. Возвращает
  настоящий класс с `kwargs` в роли `config`: `StatisticalAnalyzer` для `'statistical'`,
  `PriceLevelAnalyzer` для `'price_levels'`. Запланированное имя → `NotImplementedError`,
  незнакомое → `ValueError` (с указанием на `analyze_zones()` — анализ зон не `BaseAnalyzer`).
- `SUPPORTED_ANALYSIS_TYPES`, `PLANNED_ANALYSIS_TYPES`: словари за двумя функциями выше.

```python
from bquant.analysis import get_available_analyzers, get_planned_analyzers, create_analyzer

print(sorted(get_available_analyzers()), sorted(get_planned_analyzers()))
# ['price_levels', 'statistical'] ['candlestick', 'chart', 'technical', 'timeseries']

analyzer = create_analyzer('statistical', alpha=0.05)
print(type(analyzer).__name__, analyzer.config)
# StatisticalAnalyzer {'alpha': 0.05}
```

До 2026-09-05 каталог держал шесть имён, и на каждое фабрика возвращала `BaseAnalyzer` с
проставленным именем, чей `analyze()` поднимает `NotImplementedError`: каталог сходился с
фабрикой (G32), а фабрика — ни с чем (G59).

**Анализ зон в каталоге не значится намеренно.** Его вход — [`analyze_zones()`](pipeline.md),
а `PriceLevelAnalyzer` — уровни поддержки и сопротивления по цене, другая возможность
пакета ([zones.md](zones.md)).

### Перечни модулей — другой вопрос

У подмодулей есть свои `get_*_analyzers()` (`get_zone_analyzers`,
`get_statistical_analyzers`, `get_technical_analyzers`, `get_candlestick_analyzers`,
`get_timeseries_analyzers`, `get_chart_analyzers`). Они перечисляют **виды анализа,
которые покрывает модуль**, и их ключи в фабрику передавать не нужно — это не имена
анализаторов.

Раньше `get_available_analyzers()` был объединением этих шести перечней и объявлял
24 имени, из которых фабрика принимала 5. Разбор — `devref/gaps/docs/g32_a_catalogue_the_factory_never_agreed_with_2026-08.md`.

## Пример

```python
import pandas as pd
from bquant.analysis import BaseAnalyzer, AnalysisResult

class MyAnalyzer(BaseAnalyzer):
    def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
        if not self.validate_data(data):
            raise ValueError("Invalid data")
        return AnalysisResult('my_analysis', results={'rows': len(data)}, data_size=len(data))

an = MyAnalyzer('MyAnalyzer')
res = an.analyze(pd.DataFrame({'close': list(range(1, 11))}))
print(res.to_dict())
```

## См. также

- [Статистический анализ](statistical.md)
- [Анализ зон](zones.md)
