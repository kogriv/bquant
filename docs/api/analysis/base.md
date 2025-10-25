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

- `get_available_analyzers() -> Dict[str, str]`: собирает доступные анализаторы из подмодулей.
- `create_analyzer(analyzer_type: str, **kwargs) -> BaseAnalyzer`: фабрика (пока возвращает базовый анализатор-заглушку).
- `SUPPORTED_ANALYSIS_TYPES`: словарь поддерживаемых направлений анализа.

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
