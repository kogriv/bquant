# Zone Detection Strategies — Developer Guide

## 🎯 Цель документа

Этот документ описывает процесс создания и сопровождения стратегий детекции зон для Universal Pipeline v2.1.
Он дополняет архитектурное описание из [devref/gaps/zo/zonan.md](../../devref/gaps/zo/zonan.md) и концентрируется на практических шагах,
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
from bquant.analysis.zones.pipeline import ZoneAnalysisPipeline
from bquant.analysis.zones.detection import ZoneDetectionConfig

pipeline = (
    ZoneAnalysisPipeline()
    .with_data(source="df", data=df)
    .detect_zones(
        ZoneDetectionConfig(
            strategy_name="my_strategy",
            rules={"my_indicator": "signal"},
        )
    )
    .analyze()
    .build()
)

result = pipeline.run()
```

После регистрации стратегия автоматически появится в `ZoneDetectionRegistry.list_strategies()` и станет доступна в документации API (см. `docs/api/analysis/strategies.md`).

## 📎 Полезные ссылки

- [Протокол и конфигурация](../../bquant/analysis/zones/detection/base.py)
- [Реестр стратегий](../../bquant/analysis/zones/detection/registry.py)
- [Примеры существующих стратегий](../../bquant/analysis/zones/detection/)
- [Архитектурные точки расширения](../../devref/gaps/zo/zonan.md#точки-расширения)
- [Zone Analysis Pipeline](../../docs/api/analysis/pipeline.md)

## 📝 TODO перед завершением задачи

- [ ] Добавить стратегию в список `docs/api/analysis/strategies.md` (если это публичная возможность).
- [ ] Обновить соответствующие руководства пользователя/примеры.
- [ ] Отразить изменение в `CHANGELOG.md` и `MIGRATION_v2.md` (при наличии breaking changes).
- [ ] Запустить `pytest` для unit и integration тестов, связанные с новой стратегией.
