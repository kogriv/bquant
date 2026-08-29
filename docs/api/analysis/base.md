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

## Функции

- `get_available_analyzers() -> Dict[str, str]`: имена, которые принимает `create_analyzer()`,
  и что каждое означает. Выводится из `SUPPORTED_ANALYSIS_TYPES` — поэтому каталог и фабрика
  не могут разойтись.
- `create_analyzer(analyzer_type: str, **kwargs) -> BaseAnalyzer`: фабрика. **Возвращает
  `BaseAnalyzer` с проставленным именем и конфигом, а не специализированный класс** — своего
  `analyze()` у результата нет. Незнакомое имя → `ValueError`.
- `SUPPORTED_ANALYSIS_TYPES`: словарь поддерживаемых направлений анализа.

```python
from bquant.analysis import get_available_analyzers, create_analyzer

print(sorted(get_available_analyzers()))
# ['candlestick', 'chart', 'statistical', 'technical', 'timeseries', 'zones']

analyzer = create_analyzer('statistical', alpha=0.05)
print(type(analyzer).__name__, analyzer.name, analyzer.config)
# BaseAnalyzer statistical {'alpha': 0.05}
```

**Для реальной работы фабрика — не тот вход.** Зоны считаются через
[`analyze_zones()`](pipeline.md), статистика — через `StatisticalAnalyzer` и функции
[statistical.md](statistical.md). Фабрика полезна там, где тип анализа приходит строкой
из конфига и нужен объект-держатель параметров.

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
