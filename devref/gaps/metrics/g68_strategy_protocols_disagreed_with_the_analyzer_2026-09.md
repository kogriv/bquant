# G68 — Протоколы стратегий объявляли не то, что зовёт анализатор

**Заведён:** 2026-09-05, волна 5 прохода по докам (`docs/api/extension_guide.md`).
**Статус:** ✅ закрыт 2026-09-05 — протоколы совпадают с вызовами; интерфейс проверяется при создании анализатора; `global`-режим требует обе половины контракта.

---

## 1. Как нашли

Страница учила писать стратегии «по протоколам из `strategies/base.py`». Чтобы напечатать
в примере настоящее число, я написал стратегию формы ровно по протоколу
(`calculate_shape(zone_data)`) и подал в `ZoneFeaturesAnalyzer` — получил
`shape_metrics: None`. Анализатор зовёт `calculate(zone_data, indicator_col=...)`,
`AttributeError` ловился `except Exception` и превращался в `None`.

## 2. Замер

| Что | Протокол объявлял | Анализатор зовёт | Стратегия по протоколу получала |
|---|---|---|---|
| shape | `calculate_shape(zone_data)` | `calculate(zone_data, indicator_col=…)` | `shape_metrics: None` |
| divergence | `calculate_divergence(zone_data)` | `calculate_divergence(zone_data, indicator_col=…, indicator_line_col=…)` | `None` |
| volume | **`calculate_volatility`** (копия соседнего протокола) | `calculate_volume(zone_data, baseline_volume=None, indicator_col=…)` | `None` |
| swing, `global` | `calculate_global` + `aggregate_for_zone` | пайплайн проверял только `calculate_global` | `zones_with_swings: 0` из 77, 77 предупреждений, ошибки нет |

## 3. Почему это форма «проверка не видит проверяемого»

Протокол — обещание интерфейса, и оно было ложным в трёх семействах из пяти; а
единственное место, где ложь могла проявиться, стояло под `except Exception → None`.
Пайплайн проверял половину глобального контракта и пропускал стратегию, которая падала
ниже по течению — там, где падение снова было «зоной без данных».

## 4. Что сделано

- Протоколы приведены к вызовам: `ShapeCalculationStrategy.calculate(zone_data, indicator_col)`,
  `DivergenceCalculationStrategy.calculate_divergence(zone_data, indicator_col, indicator_line_col=None)`,
  `VolumeCalculationStrategy.calculate_volume(zone_data, baseline_volume=None, indicator_col=None)`.
- `ZoneFeaturesAnalyzer.__init__` проверяет наличие нужных методов у каждой стратегии и
  отказывает `TypeError` по имени — один раз, а не `None` в каждой зоне.
- В блоках расчёта метрик `AttributeError`/`TypeError` больше не глотаются: стратегия,
  которую нельзя вызвать, — ошибка программы, не зона без данных. Ошибки данных
  по-прежнему деградируют в `None` с записью в лог.
- `_calculate_global_swings` требует и `calculate_global`, и `aggregate_for_zone`, называя
  недостающее и `.with_swing_scope('per_zone')` как выход.

## 5. Проверка

`tests/unit/test_a_strategy_written_to_the_protocol_works.py`: стратегии формы и
дивергенций по протоколу используются анализатором; протокол объёма называет
`calculate_volume`; стратегия без метода отвергается при создании; свинговая без
`aggregate_for_zone` отвергается в `global` и работает в `per_zone`.

| Мутация | Краснеет |
|---|---|
| проверка интерфейса в `__init__` снята | 1 |
| `AttributeError` снова глотается | 1 |
| пайплайн проверяет только `calculate_global` | 1 |

## 6. Цена

Стратегия с неполным интерфейсом — отказ при создании анализатора или при сборке
пайплайна вместо `None`/нулей. Имя метода протокола формы — `calculate`, не
`calculate_shape` (встроенная стратегия так и называла его всегда).
