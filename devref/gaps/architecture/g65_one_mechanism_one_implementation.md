# G65 — Один механизм, несколько реализаций: хелперы ×3, ручные EMA, шаблоны имён, реестр ×5

**Заведён:** 2026-09-05 (реестр; находки AQ-040…043 аудита качества 2026-09-04, этап 3, P2).
**Статус:** ✅ закрыт 2026-09-06.

---

## 1. Как нашли

Аудит назвал четыре места, где один механизм написан несколько раз. Замер перед правкой
показал, что копии уже разошлись — и расхождение видно снаружи.

## 2. Замер до правки

| Находка | Что было | Замер |
|---|---|---|
| AQ-040 | `get_statistics`, `is_trending_up`, `is_trending_down`, `get_crossovers` — три копии в `PreloadedIndicator`, `CustomIndicator`, `MACDPreloadedIndicator` | `get_statistics` ×3 идентичны; trending-методы расходятся в выборе колонки; **`get_crossovers` — две разные формы ответа** под одним именем (`{'bullish': [позиции]}` с `lookback` против `{'bullish_crossovers': n, …, 'bullish_indices': [...]}`); у `CustomIndicator` метода нет, а `MACD.get_info()['available_methods']` его рекламирует: `MACD().get_crossovers(data)` → `AttributeError`. Любая ошибка расчёта — `{}` / `False` / словарь с ключом `'error'` |
| AQ-041 | `calculate_moving_averages` считал через фабрику только первый период, остальные — `rolling().mean()` / `ewm(span).mean()` на месте; `create_indicator_suite` — то же; `IndicatorCalculator.results` по голому имени | EMA расходится с `ExponentialMovingAverage` на **38 / 76 / 174** барах сэмпла (периоды 10 / 20 / 50), максимум 9.96 пункта — ручная `ewm` без прогрева и с другим `adjust`; `calculate('sma', period=50)` **затирал** `calculate('sma', period=10)`; `examples/01_basic_indicators.py` ловил `KeyError('close')` в `except` и печатал «❌», выходя с кодом 0 |
| AQ-042 | пресеты собирали `'RSI_14' if period == 14 else f'RSI_{period}'` и `f'AO_{fast}_{slow}'`; хвост `.analyze(...).with_cache(...).build()` повторён четыре раза | второе место, знавшее соглашение pandas-ta об именах (первое — схема колонок); `indicator_role='value'` из предложения аудита недоступен: библиотечные индикаторы ролей не объявляют (`get_output_roles()` честно пуст) |
| AQ-043 | `StrategyRegistry`: пять словарей, пять троек register/get/list | 286 строк, механизм один; политики конфликтов нет — второй класс под тем же именем молча заменял первый |

Побочная находка: `examples/01_basic_indicators.py` падал на верхнем уровне с
`NameError: register_builtin_indicators` (имя, которого в примере нет — см. §4) и **выходил
с кодом 0**: верхний `except` печатал трейсбек и не выходил. Батарея считала пример зелёным.

## 3. Почему это форма «проверка не видит проверяемого»

Копия — это обещание «то же самое», которое никто не сверяет. Здесь оно нарушалось трижды
одновременно: форма ответа, наличие метода, числа расчёта. Тест сравнивал бы копию с
собой; сверить копию с оригиналом мог только тот, кто знал про обе.

## 4. Что сделано

* **AQ-040** — четыре разреза определены один раз на `BaseIndicator`; форма
  `get_crossovers` — документированная (счётчики `int` + индексы, `column1`/`column2`),
  колонки по умолчанию — две первые выходные; ошибка расчёта или чужая колонка —
  исключение; `available_methods()` — интроспекция, шесть литералов в `get_info()`
  заменены на её вызов. Копии сняты (7 методов в `base.py`, 4 в `preloaded/macd.py`).
* **AQ-041** — `calculate_moving_averages` и `create_indicator_suite` считают каждый
  период объектом индикатора (EMA равна объекту побайтно); `STANDARD_SUITE` — явный
  список; ключи результатов — слаг идентичности (`sma_20`, `macd_12_26_9`, `bbands_20_2`);
  `IndicatorCalculator` хранит по `IndicatorId.key` (`custom.sma_10`), `get_result` по
  имени отвечает только при однозначности, иначе `KeyError` с перечнем;
  `calculate_multiple` не глотает ошибку. `auto_load_libraries` → `ensure_loaded()`.
* **AQ-042** — `_declared_column(source, name, **params)` спрашивает колонку у самого
  индикатора (`RSI_21`, `AO_7_21` из `get_output_columns()`); `_finish()` — один хвост.
* **AQ-043** — `StrategyRegistry`: одна корзина на семейство в одном словаре, один
  `register(family, name)` / `get` / `list_strategies`, `FAMILIES`; семейные методы —
  однострочные имена над ними; конфликт — `ValueError`, повтор того же класса — no-op.
  Фикстура `isolated_registries` в проверке доков снимает вложенные корзины deep-copy.
* Пример `01_basic_indicators.py`: цена берётся из исходного кадра, каждый `except`
  поднимает ошибку, верхний — `sys.exit(1)`.

## 5. Сторожа

`tests/unit/test_one_mechanism_one_implementation.py` — 15 проверок: хелперы определены
только на `BaseIndicator` (ast), все рекламируемые методы существуют, custom- и
preloaded-MACD отдают одну форму пересечений, отказ вместо `{}`; скользящие средние
равны объектам побайтно, набор считается объектами и ключуется идентичностью, калькулятор
держит две параметризации, в `calculators.py` нет `.rolling(`/`.ewm(`; в `presets.py` нет
литералов `RSI_`/`AO_`, RSI-пресет с `period=21` детектирует по объявленной колонке; у
реестра одна корзина на семейство, конфликт отказан, чужое семейство отказано.

## 6. Ломает

Форма ответа `PreloadedIndicator.get_crossovers` (`bullish`/`bearish` → счётчики и индексы,
без `lookback`); ошибки хелперов — исключения, не `{}`/`False`; ключи
`create_indicator_suite` и `IndicatorCalculator.results`; `calculate_multiple` поднимает
ошибку; `available_methods` в `get_info()` — имена без скобок; `StrategyRegistry._*_strategies`
исчезли (внутреннее), повторная регистрация другого класса — `ValueError`.
