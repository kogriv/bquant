# bquant.analysis.zones.models — Модели глобальных свингов

Структуры данных режима глобального расчёта свингов (`swing_scope='global'`, он же режим по умолчанию).

## `SwingPoint`

`SwingPoint` — дата-класс, описывающий одну точку свинга (пик или впадину), обнаруженную на **глобальном** ряду котировок. Экземпляры создаются стратегиями свингов один раз и переиспользуются для всех зон.

### Поля

| Поле | Тип | Описание |
| ---- | --- | -------- |
| `point_id` | `int` | Уникальный идентификатор точки в последовательности свингов. |
| `timestamp` | `datetime` | Метка времени, совпадающая со значением индекса исходного DataFrame. |
| `index` | `int` | Позиция точки в полном датасете (iloc). |
| `price` | `float` | Цена инструмента в момент свинга. |
| `swing_type` | `str` | Тип точки: `'peak'` или `'trough'`. |
| `amplitude_to_next` | `Optional[float]` | Процентное изменение до следующей точки свинга (если она существует). |
| `duration_to_next` | `Optional[int]` | Количество баров до следующего свинга. |
| `strategy_name` | `str` | Название стратегии, обнаружившей свинг. |
| `strategy_params` | `Dict[str, Any]` | Параметры стратегии для трассируемости (по умолчанию пустой словарь). |
| `confirmation_index` | `Optional[int]` | Бар, на котором точка становится **известной**: экстремум виден не в момент его образования, а когда стратегия его подтвердила. |

### Основные особенности

- Структура полностью сериализуема: используется в `SwingContext.to_dict()` для кэширования.
- Совместима с любыми стратегиями свингов — поля не зависят от конкретного алгоритма.
- Позволяет сохранять не только геометрию свинга, но и метаданные стратегии (например, допуски ZigZag).

**`index` и `confirmation_index` — разные вопросы, и путать их дорого.** Первый говорит,
*где* экстремум находится, второй — *с какого бара о нём можно было знать*. Разница между
ними и есть задержка подтверждения: на встроенном сэмпле (`zigzag`, 402 точки) она
составляет от 1 до 11 баров при медиане 2. Всё, что смотрит вперёд — форвардная
разметка, воспроизведение по барам, бэктест, — обязано читать `confirmation_index`;
`index` для этого непригоден, потому что помещает знание раньше, чем оно появилось.

У одной точки из 402 `confirmation_index` равен `None`: подтвердить её нечем, ряд
кончился. Это не пропуск данных, а честное «пока неизвестно», и обрабатывать его надо
как отсутствие точки, а не как ноль.

Зачем поле заведено — `devref/gaps/swing/issue110_zigzag_replay_causal_2026-07-30.md` и
`g15_auto_prominence_measurement_2026-08-22.md`.

## `SwingContext`

`SwingContext` агрегирует все `SwingPoint`, рассчитанные для полного набора данных. Контекст хранится на уровне пайплайна и передаётся в зоны, что устраняет повторные расчёты.

### Ключевые поля

- `swing_points: List[SwingPoint]` — упорядоченный список свингов.
- `indices: np.ndarray` — отсортированный массив `iloc`-индексов, используемый для быстрых срезов через `bisect`.
- `full_data_length: int` — размер исходного датафрейма (для валидации).
- `strategy_name: str` и `strategy_params: Dict[str, Any]` — метаданные стратегии.

### Методы

- `slice(start_idx: int, end_idx: int) -> List[SwingPoint]`
  - Возвращает точки, попадающие в диапазон зоны, **с захватом соседей** слева и справа. Это обеспечивает корректные амплитуды при вычислении метрик.
- `get_swings_for_zone(zone: ZoneInfo) -> List[SwingPoint]`
  - Удобный враппер над `slice`, использующий `zone.start_idx` и `zone.end_idx`.
- `to_dict() -> Dict[str, Any]`
  - Сериализует весь контекст в словарь. Используется кэшем и для трассировки.

### Типичные сценарии

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .analyze(clustering=False)
    .build()
)

context = result.zones[0].swing_context
print(context.strategy_name, len(context.swing_points), context.full_data_length)
# zigzag 402 1000

zone_swings = context.get_swings_for_zone(result.zones[0])
print(len(zone_swings))
```

Контекст один на весь прогон: `full_data_length` — длина исходного кадра, а не зоны, и
`swing_points` перечисляет свинги всего ряда. Зона получает из него срез.

## `ZoneInfo` и глобальные свинги

`ZoneInfo` несёт поле `swing_context: Optional[SwingContext]`. Пайплайн вызывает `_inject_swing_context()` сразу после детекции зон (см. соответствующий раздел), поэтому каждая зона получает ссылку на общий контекст.

### Поле `swing_context`

- Устанавливается только в режиме `swing_scope="global"`.
- Остаётся `None` в режиме `per_zone`, что сохраняет обратную совместимость.
- Попадает в метод `to_analyzer_format()`, поэтому все анализаторы признаков имеют доступ к глобальным свингам.

### Метод `get_zone_swings()`

`ZoneInfo.get_zone_swings()` извлекает список `SwingPoint` для конкретной зоны. Если контекст не инъектирован, метод возвращает пустой список — таким образом старые сценарии не ломаются.

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd')
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='zigzag')
    .analyze(clustering=False)
    .build()
)

for point in result.zones[0].get_zone_swings():
    print(point.swing_type, round(point.price, 2), point.index, point.confirmation_index)
```

Используйте этот метод в пользовательских метриках и визуализациях, чтобы работать с уже рассчитанными глобальными свингами без повторных вычислений.
