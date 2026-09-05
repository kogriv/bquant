# Zone Detection Strategies — Developer Guide

## 🎯 Цель документа

Этот документ описывает процесс создания и сопровождения стратегий детекции зон для Universal Pipeline v2.1.
Он дополняет архитектурное описание и концентрируется на практических шагах,
которые необходимы разработчику для расширения слоя 1 — `ZoneDetectionStrategy`.

## 🧭 Когда нужна новая стратегия

Создавайте отдельную стратегию, если выполняется хотя бы одно условие:

- требуется другой способ маркировки зон, который нельзя выразить параметрами существующих стратегий (`zero_crossing`, `line_crossing`, `threshold`, `combined_rules`, `preloaded`);
- используются дополнительные источники данных или метрики (объём, корреляции, машинное обучение);
- нужно переиспользовать стратегию в разных пайплайнах через `ZoneDetectionRegistry`.

Если достаточно скорректировать правила (`rules`) существующей стратегии, создавайте новую конфигурацию `ZoneDetectionConfig`, а не новый класс.

## 🗂️ Структура пакета `bquant.analysis.zones.detection`

```
bquant/analysis/zones/detection/
├── __init__.py              # Экспорт Strategy, Config, Registry
├── base.py                  # Протокол ZoneDetectionStrategy + ZoneDetectionConfig
├── registry.py              # ZoneDetectionRegistry и декоратор @register
├── zero_crossing.py         # Стратегия пересечения нуля
├── line_crossing.py         # Стратегия пересечения линий
├── threshold.py             # Стратегия порогов (RSI и т.п.)
├── combined.py              # Комбинированные правила
└── preloaded.py             # Предзагруженные зоны
```

Новые стратегии размещаются рядом с существующими модулями и автоматически подключаются через `ZoneDetectionRegistry`.

## ✅ Чеклист перед реализацией

1. Определите входные данные и обязательные правила (`rules`) конфигурации.
2. Решите, какие типы зон (`zone_types`) поддерживает стратегия.
3. Продумайте набор полей `indicator_context`, который требуется для последующих анализаторов.
4. Подготовьте тесты: минимум unit-тест на `detect_zones()` и сценарий интеграции с `ZoneAnalysisPipeline` (см. раздел «Тестирование»).

## 🚀 Пошаговое создание стратегии

1. **Сверьтесь с архитектурой.** Перечитайте раздел «Точки расширения: Слой 1» (см. документацию), чтобы убедиться, что новая стратегия действительно расширяет слой детекции, а не дублирует существующие правила.
2. **Определите контракт конфигурации.** Зафиксируйте список обязательных правил (`REQUIRED_RULES`) и ожидаемые типы данных. Обновите схемы в документации или конфигураторах, если добавляете новые ключи.
3. **Соберите входные данные.** Опишите, какие поля `pd.DataFrame` обязаны присутствовать, и подключите дополнительные индикаторы/источники данных (через `indicator_requirements`).
4. **Реализуйте стратегию.** Создайте модуль, следуя шаблону ниже, и зарегистрируйте класс через `@ZoneDetectionRegistry.register` (см. документацию).
5. **Покройте контракт тестами.** Напишите unit-тесты на валидацию правил, правильность `indicator_context` и регистрационный тест на интеграцию с `ZoneDetectionRegistry`.
6. **Интегрируйте в pipeline.** Добавьте сценарий в интеграционные тесты `ZoneAnalysisPipeline`, чтобы зафиксировать ожидаемое поведение.
7. **Обновите документацию.** Кратко опишите стратегию и её правила в соответствующих справочниках (API/конфигурации).

## 🧱 Базовый шаблон стратегии

```python
# bquant/analysis/zones/detection/my_strategy.py
from typing import List

import pandas as pd

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo


@ZoneDetectionRegistry.register(
    name="my_strategy",
    indicator_requirements=["my_indicator"],  # отображается в list_strategies()
    description="Detects custom bullish/bearish zones based on My Indicator."
)
class MyStrategy(ZoneDetectionStrategy):
    """Детекция зон по кастомным правилам."""

    REQUIRED_RULES = ["my_indicator"]

    def detect_zones(
        self, data: pd.DataFrame, config: ZoneDetectionConfig
    ) -> List[ZoneInfo]:
        # 1. Валидация правил и получение параметров
        config.validate(self.REQUIRED_RULES)
        indicator = config.rules["my_indicator"]

        # 2. Собственно логика детекции
        #    (здесь примерная заготовка, замените на ваши условия)
        positives = data[data[indicator] > 0]
        if positives.empty:
            return []

        start_label = positives.index[0]
        end_label = positives.index[-1]
        start_idx = data.index.get_loc(start_label)
        end_idx = data.index.get_loc(end_label)

        # 3. Конструирование ZoneInfo с обязательным indicator_context
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
                "detection_strategy": "my_strategy",
                "detection_indicator": indicator,
                "detection_rules": config.rules,
            },
        )

        return [zone]
```

### Обязательные элементы шаблона

- `@ZoneDetectionRegistry.register(...)` — регистрирует стратегию и публикует метаданные.
- `REQUIRED_RULES` — список обязательных полей `rules`, используемый в `config.validate(...)`.
- Возвращаемые `ZoneInfo` должны заполнять `indicator_context` как минимум полями `detection_strategy` и `detection_indicator` (требования контракта v2.1).

## 🧪 Тестирование стратегии

| Тип теста | Что проверяем | Пример |
|-----------|---------------|--------|
| Unit      | Метод `detect_zones()` возвращает ожидаемые зоны и заполняет `indicator_context`. | `tests/unit/zones/detection/test_my_strategy.py` |
| Registry  | Стратегия доступна через `ZoneDetectionRegistry.get('my_strategy')`. | Используйте фикстуру `registry_cleanup` (см. `tests/conftest.py`). |
| Pipeline  | Интеграция с `ZoneAnalysisPipeline` через `ZoneDetectionConfig`. | Добавьте сценарий в `tests/integration/zones/test_pipeline_strategies.py`. |

Пример минимального unit-теста:

```python
def test_my_strategy_detects_zone(sample_indicator_df):
    strategy = MyStrategy()
    config = ZoneDetectionConfig(
        strategy_name="my_strategy",
        rules={"my_indicator": "signal"},
    )

    zones = strategy.detect_zones(sample_indicator_df, config)

    assert zones
    assert zones[0].indicator_context["detection_strategy"] == "my_strategy"
    assert zones[0].indicator_context["detection_indicator"] == "signal"
```

## 🔌 Использование в пайплайне

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .detect_zones("my_strategy", indicator_col="signal")
    .analyze()
    .build()
)
```

`analyze_zones(df)` — это и есть точка входа билдера: данные передаются ему, а не
отдельным шагом. Имя стратегии — строка из реестра, дополнительные правила уходят
в `**rules`. `.build()` возвращает уже посчитанный `ZoneAnalysisResult`; отдельного
`run()` нет.

После регистрации стратегия автоматически появится в `ZoneDetectionRegistry.list_strategies()` и станет доступна в документации API (см. `docs/api/analysis/strategies.md`).

## ♻️ Расширение UniversalZoneAnalyzer

`UniversalZoneAnalyzer` относится к слою 2 архитектуры (см. документацию) и отвечает за полный жизненный цикл анализа зон.

### Жизненный цикл анализа

1. **Извлечение признаков.** Вызывает `ZoneFeaturesAnalyzer.extract_all_zones_features` и дописывает полученные признаки обратно в `zone.features`.
2. **Статистика и гипотезы.** Передаёт признаки в `ZoneFeaturesAnalyzer.analyze_zones_distribution` и `HypothesisTestSuite.run_all_tests`.
3. **Последовательности и кластеры.** Через `ZoneSequenceAnalyzer` выполняет анализ переходов и (опционально) кластеризацию.
4. **Регрессия.** При включённом флаге делегирует работу `ZoneRegressionAnalyzer`.
5. **Сбор результатов.** Формирует `ZoneAnalysisResult` с агрегированной метаинформацией.

Валидация (`.analyze(validation=True)`) — **не** шаг анализатора: он получает готовые зоны и не владеет детекцией, а проверка обязана заново прогнать детекцию на каждом окне. Её выполняет `ZoneAnalysisPipeline` после анализа, через `ValidationSuite`, который анализатор держит как DI-компонент (`validation_suite`).

Полный код жизненного цикла см. в `bquant/analysis/zones/analyzer.py`.

### Интерфейсы расширения

Каждый компонент конструктора `UniversalZoneAnalyzer` принимает DI-объект. Чтобы расширить слой 2:

- **Features Analyzer** (`features_analyzer`): реализуйте метод `extract_all_zones_features` и опционально дополнительные анализы распределения.
- **Hypothesis Suite** (`hypothesis_suite`): предоставьте `run_all_tests`, возвращающий словарь результатов гипотез.
- **Sequence Analyzer** (`sequence_analyzer`): реализуйте `analyze_zone_transitions` и, при необходимости, `cluster_zones`.
- **Regression Analyzer** (`regression_analyzer`): предоставьте методы `explain_zone_duration` и `explain_price_return` (объясняющие, in-sample — см. [статистика](../api/analysis/statistical.md)).
- **Validation Suite** (`validation_suite`): предоставьте `out_of_sample_test(analyze_func, data, metric, train_ratio=...)`, возвращающий `ModelValidationResult` — это единственный метод, который зовёт пайплайн; `degradation_threshold` у стандартного `ValidationSuite` — способ задать свой порог без замены класса.

При добавлении новых DI-компонентов синхронизируйте описание с документацией и обновите примеры использования в API-документации.

## 🤝 Contribution guide для новых стратегий и анализаторов

Разработчики, расширяющие слой 1 (стратегии) или слой 2 (анализаторы), должны соблюдать следующие требования:

- **Тесты.**
  - Unit-тесты покрывают основную логику (`detect_zones`, кастомные анализаторы признаков и т.п.).
  - Регистрационные тесты подтверждают, что новые классы доступны через DI/registry.
  - Интеграционные сценарии `ZoneAnalysisPipeline` запускаются с новой стратегией/анализатором.
- **Документация.**
  - Обновите developer guide (этот документ) и профильные страницы API/конфигураций.
  - Добавьте примеры конфигурации и использования, включая параметры `rules` и флаги анализатора.
- **Проверки.**
  - Выполните `pytest` для затронутых пакетов.
  - Прогоните статический анализ (например, `ruff`, `mypy` или используемые в проекте инструменты) при изменении Python-кода.
  - Обновите `CHANGELOG`/`CHANGE_TRACE_LOG`, если изменение публичное.
  - Убедитесь, что линтеры и форматтеры (например, `ruff --fix`, `black`) не оставляют нарушений.

Зафиксируйте результаты проверок в описании pull request и сослались на соответствующие разделы «Точки расширения» для ревьюеров.

## 📎 Полезные ссылки

- [Zone Analysis Pipeline](../api/analysis/pipeline.md)
- Протокол и конфигурация (см. исходный код)
- Реестр стратегий (см. исходный код)
- Примеры существующих стратегий (см. исходный код)

## 📝 TODO перед завершением задачи

- [ ] Добавить стратегию в список `docs/api/analysis/strategies.md` (если это публичная возможность).
- [ ] Обновить соответствующие руководства пользователя/примеры.
- [ ] Отразить изменение в `CHANGELOG.md` и `MIGRATION_v2.md` (при наличии breaking changes).
- [ ] Запустить `pytest` для unit и integration тестов, связанные с новой стратегией.
