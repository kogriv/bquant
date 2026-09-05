# G60 — ATR в пайплайне обещан и недостижим; `atr_normalized_return` делил долю на цену

**Заведён:** 2026-09-05, из аудита качества (AQ-012, AQ-013).
**Статус:** ✅ закрыт 2026-09-05 — `calculate_atr()`, колонка `atr` в кадре пайплайна с периодом в конфиге и ключе кэша, формула в единицах ATR.

---

## 1. Что было — замер

| Вход | Ответ было | Ответ стало |
|---|---|---|
| `analyze_zones(sample)…build()` — `'atr' in result.data` | **False**; `atr_normalized_return` заполнен в **0 из 77** зон | True; заполнен в 77 из 77 |
| тот же кадр с принесённой колонкой `atr = 20` (единицы цены), зона 0: `price_return = 0.00265` | `atr_normalized_return = 0.000133` | 0.453 = `(end − start) / 20` |

Ветка `if 'atr' in derived.columns` в `_prepare_data` ждала колонку от
`calculate_derived_indicators`, которая ATR не считает, — поэтому на флагманском пути
признак не существовал никогда. Там, где ATR приносили, формула `price_return / atr` делила
безразмерную долю на единицы цены: результат меньше настоящего в `start_price` раз.

## 2. Что сделано

- `bquant.data.processor.calculate_atr(df, period=14)` — скользящее среднее
  `calculate_true_range` (та же форма, что у фикстуры сьюта); первые `period − 1` — `NaN`.
- `ZoneAnalysisConfig.atr_period = 14`, в ключе кэша; билдер — `.with_atr_period(period)`;
  `_prepare_data` добавляет `atr`, если колонки нет и есть `high/low/close`.
- `atr_normalized_return = (end_price − start_price) / atr[0]` — движение за зону в единицах
  ATR на её первом баре; `None` в прогреве ATR.
- `CACHE_VERSION` 25 → 26. Кадр результата на сэмпле — 18 колонок, не 17
  (`docs/user_guide/core_concepts.md`).

## 3. Проверка

`tests/unit/test_features_and_statistics_measure_what_they_name.py` (часть G60): колонка
равна `calculate_atr(result.data, 14)` и признак заполнен во всех зонах; размерность —
`(end − start) / atr`; период в ключе кэша и отказ на `0`; `calculate_atr` = среднее TR.
Мутации: пайплайн не добавляет `atr` — 1; старая формула — 1.

## 4. Цена

`result.data` несёт колонку `atr`; `atr_normalized_return` заполнен там, где был `None`, и
в других единицах там, где был заполнен; кэш v25 не читается.
