# G58 — Реализации индикаторов не держали один контракт

**Заведён:** 2026-09-04, из аудита качества (AQ-021, AQ-022, AQ-023, AQ-028).
**Статус:** ✅ закрыт 2026-09-05 — валидация отказывает, а не логирует; float на входе; один прогрев и одна проверка периодов у обеих реализаций; идентичность неизменяема и включает источник.

---

## 1. Что было — замер

| AQ | Вход | Ответ было | Ответ стало |
|---|---|---|---|
| 021 | `MACD().calculate(10 баров)` при минимуме 35 | **10 строк `NaN`** — как прогрев | `DataValidationError: 10 rows, but at least 35 are needed` |
| 021 | `EMA(20).calculate(40 баров, period=100)` | 40 строк `NaN`, колонка `ema_100` | отказ: нужно 100 |
| 021 | `close` из строк | посчитано (`2.263…`) | отказ: `dtype object` |
| 021 | `inf` в `close` | 4 нечисловых значения на выходе | отказ: `1 infinite value` |
| 022 | `OptimizedIndicators.ema([100, 101, 103, …], 3)` | **`[100, 100, 101, 101, 103]`**, `int64` | `[…, 101.75, 101.875, 103.44]`, `float64`; RSI/MACD на `int` = на `float` |
| 023 | прогрев MACD, custom / optimized | линия 25 / **0**, сигнал 33 / **0** | 25 / 25, 33 / 33 |
| 023 | прогрев EMA, custom / optimized | 19 / **0** | 19 / 19, значения после прогрева равны |
| 023 | `macd(fast=0)`, `macd(26, 12)`, `macd(signal=0)` | optimized принимал все три; custom — `slow <= fast` | `ValueError` у обеих |
| 028 | `iid.parameters['period'] = 99` у `frozen` id | slug стал `rsi_99`, объект пропал из своего же `dict` | `TypeError` |
| 028 | custom RSI и pandas-ta RSI в одной `ColumnSchema` | **одна** запись `('rsi_14', 'value') → 'RSI_14'`, custom затёрт | две записи, `custom.rsi_14` и `pandas_ta.rsi_14` |

## 2. Почему это форма «проверка не видит проверяемого»

`validate_data()` писала ошибку в лог и возвращала `False`, а восемь вызывающих (пять
custom-индикаторов, preloaded, library, `calculators`) значение не читали: лог — не
поток управления. Минимум строк считался по конструктору, а не по параметрам вызова.
`np.zeros_like` наследовал `int64` — «оптимизированная» реализация тихо считала другую
величину на целых ценах; G44 сверял `ema` с `ewm` на float и не видел этого.
Оптимизированный MACD публиковал непрогретую голову под тем же именем, под которым
custom её маскирует (G45). `frozen=True` замораживал ссылку на `dict`, не `dict`.
`ColumnSchema` ключевала по slug, в котором нет источника, — одно имя, две серии.

## 3. Что сделано

- **`BaseIndicator.validate_data(data, **params)`** возвращает `True` или поднимает
  `DataValidationError` по имени: колонки; строки по `get_min_records(**params)`
  (`calculate(data, period=100)` требует сто); числовой dtype обязательных колонок;
  нет `inf` (`NaN` — пропуск, дело чистки, не индикатора). Пять custom-индикаторов
  зовут её с параметрами вызова, объявляют `get_required_columns() == ['close']` и
  пропускают `DataValidationError` мимо своей обёртки `IndicatorCalculationError`.
  `validate_indicator_data()` сохраняет булев контракт, ловя отказ.
- **`OptimizedIndicators`**: вход — `np.asarray(prices, dtype=float)` везде; `_ema_raw`
  для цепочек (MACD/RSI) без маски, публичная `ema` маскирует `period-1`; `macd`
  маскирует `slow-1` / `slow+signal-2`; `require_period`, `require_macd_periods`,
  `ema_warmup`, `macd_warmup` — одни на всех, custom-MACD зовёт те же.
- **`FrozenParameters`** — неизменяемое, хэшируемое, пиклящееся отображение (в отличие
  от `MappingProxyType`, который в кэш и артефакты не уедет). **`IndicatorId.key`** =
  `source.slug`; `ColumnSchema` ключует записи и индикаторы по нему; `to_dict` пишет
  `source.slug|role`; `from_dict` отказывает на артефакте, ключеванном без источника.
  `CACHE_VERSION` 24 → 25.

## 4. Чего не сделано — и почему

Значения custom-MACD и оптимизированного **после** прогрева по-прежнему расходятся
(до 3.5 пункта на часовом золоте): custom считает EMA с `adjust=True`, оптимизированный —
рекурсивно. Это записанное решение (`devref/gaps/issue_indicator_consistency.md`, §1), а не
дефект прогрева; смена `adjust` меняет число зон на флагманском пути (83 → 79) и десятки
чисел в доках — не в этой записи. Паритет утверждается там, где он есть: EMA (обе
реализации `adjust=False`) — побитово после прогрева; MACD — форма маски и проверка
периодов. Паритет с pandas-ta не утверждается: он сеет EMA по SMA (`presma`) и расходится
с обеими.

## 5. Проверка

`tests/unit/test_indicator_implementations_agree.py` — 18 проверок. Два прежних теста
держались на старом контракте и переписаны: `test_ema_matches_its_definition` сверял
`ema` с `ewm` целиком, включая непрогретую голову; `test_data_validation_compatibility`
ждал `False` вместо отказа.

| Мутация | Краснеет |
|---|---|
| `validate_data` логирует и возвращает `False` | 2 |
| минимум строк по конструктору | 1 |
| проверки dtype/inf пропущены | 2 |
| `zeros_like` на dtype входа | 1 |
| optimized MACD публикует с нулевого бара | 1 |
| `slow <= fast` принимается | 2 |
| `parameters` снова `dict` | 1 |
| схема ключует по slug | 1 |

## 6. Цена

- `validate_data()` поднимает `DataValidationError` вместо `False`; `calculate()` на
  коротком/нечисловом/бесконечном входе — отказ вместо кадра `NaN`.
- `get_min_records(**params)` — новая сигнатура у базового класса и пяти custom.
- `OptimizedIndicators.ema` — первые `period-1` значений `NaN`; `macd` — прогрев по
  контракту; периоды проверяются.
- `IndicatorId.parameters` — `FrozenParameters`, правка на месте — `TypeError`.
- `ColumnSchema.entries` ключуется `('custom.macd_12_26_9', 'hist')`; артефакты со схемой
  до 2026-09-05 не читаются (`from_dict` называет причину); кэш v24 не читается.
