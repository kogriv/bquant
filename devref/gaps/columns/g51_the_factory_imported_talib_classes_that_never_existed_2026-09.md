# G51 — Фабрика импортировала TA-Lib-классы, которых никогда не было

**Заведён:** 2026-09-04, при проходе по докам (волна 4, `docs/tutorials/rsi_strategy_switching.md`).
**Статус:** ✅ закрыт 2026-09-04 — мёртвая ветка заменена на ошибку, называющую библиотеку.

---

## 1. Что было

`IndicatorFactory._create_library('talib', name)` искал `talib_<name>` в реестре, а не найдя,
уходил в «шаблонную» ветку:

```python
if indicator_lower == 'rsi':
    from .library.talib import TALibRSI
    return TALibRSI(**params)
```

`bquant/indicators/library/talib.py` определяет один класс — `TALibLoader`. Ни `TALibSMA`,
ни `TALibEMA`, ни `TALibRSI`, ни `TALibMACD`, ни `TALibBBands` в нём нет и не было.
Ветка недостижима, когда TA-Lib установлен (лоадер регистрирует `talib_*`, и реестр
отвечает раньше), и **всегда** падает, когда не установлен:

```
ImportError: cannot import name 'TALibRSI' from 'bquant.indicators.library.talib'
```

Читатель туториала RSI, который прописывал `with_indicator('talib', 'rsi', timeperiod=14)`,
получал сообщение о сломанном пакете вместо «TA-Lib не установлен».

## 2. Почему это форма «проверка не видит проверяемого»

Два теста зовут `create('talib', 'sma', …)` — оба внутри `try/except`, который глотает
любое исключение и печатает `[WARN]`. Ветка исполнялась в каждом прогоне сьюта без
TA-Lib и ни разу не была замечена: её отказ был ожидаем, но ожидалась не та причина.

## 3. Что сделано

- Ветка удалена. Незарегистрированный индикатор библиотеки поднимает `KeyError`,
  называющий состояние: `… is not registered: the library is not installed or its loader
  has not run (LibraryManager.load_all_libraries())`.
- `tests/unit/test_factory_names_the_missing_library.py`: для пяти имён без
  зарегистрированного `talib_*` ошибка обязана говорить про библиотеку и не обязана
  упоминать несуществующий класс; при загруженном TA-Lib тест пропускается с причиной.
- Туториал RSI переведён на `pandas_ta` (ставится зависимостью) и говорит, что `'talib'` —
  опциональный источник.

## 4. Чего не сделано

`test_talib_availability` и аналог в `test_architecture_validation.py` по-прежнему
глотают исключение — они проверяют «доступна ли библиотека», и без неё им нечего
утверждать. Что они не различают «нет библиотеки» и «сломан путь к ней», закрывает
новый тест, а не они.
