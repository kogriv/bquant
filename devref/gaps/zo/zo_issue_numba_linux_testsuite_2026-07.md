# Issue: pandas-ta numba ZigZag segfaults on degenerate data

**Дата:** 2026-07-06 (root cause уточнён и доказан)
**Тип:** external dependency bug / input-guarding
**Приоритет:** 🟠 Medium — краш дефолтного swing на вырожденных данных; ломает `pytest`
**Статус:** 🟢 Root cause доказан, лекарство определено (дефолт остаётся zigzag)

**Связь:** обновляет `zo_issue_numba_zoneinfo_none.md` (2025-10-19, Problem #2).

---

## 1. Симптом

Полный `pytest tests/` **падает с фатальным крашем** (exit 134 Aborted / 139 SIGSEGV)
на `tests/integration/test_truly_universal_zones.py`. Крах — в numba-коде
`pandas_ta/trend/zigzag.py:299` (`nb_rolling_hl`). До этого — ноль фейлов.

---

## 2. Root cause — ДОКАЗАН

**pandas-ta zigzag (`@njit(cache=True)`) делает segfault на вырожденных данных**
(константные high/low, нулевой диапазон цен). В nopython-режиме numba нет проверки
границ массива → выход за границу → segfault.

**Минимальный репро (5 строк, ВНЕ pytest, exit 139):**
```python
import pandas as pd, pandas_ta as ta
n = 200
ta.zigzag(pd.Series([102.0]*n), pd.Series([98.0]*n), pd.Series([100.0]*n))
# -> Segmentation fault
```

**Как это попадает в тест:** `test_fictional_indicator_with_threshold` строит
плоский DataFrame (`open=100, high=102, low=98, close=100` на всех 200 барах,
`test_truly_universal_zones.py:93-101`). Дефолтный swing = zigzag (`config.py:162`),
`swing_scope="global"` → `_calculate_global_swings` гоняет zigzag на этих плоских
данных → segfault.

**Подтверждение через изоляцию тестов:**
- `test_fictional_indicator_full_pipeline` (zigzag, данные с движением) — **проходит**.
- `test_fictional_indicator_with_threshold` (zigzag, плоские данные) — **segfault**.

---

## 3. Чем это НЕ является (важно для вопроса «доставить numba?»)

- ❌ **НЕ отсутствие/битая numba.** numba 0.61.2 установлена и **работает**: `ta.zigzag`
  на реальных данных и полный pipeline bquant со swing=zigzag отрабатывают штатно
  (**72 зоны**, exit 0). Доустановка/переустановка numba ничего не изменит.
- ❌ **НЕ специфика pytest.** Репро воспроизводится в обычном скрипте.
- ❌ **НЕ версии/threading/cache.** Проверено: `NUMBA_THREADING_LAYER=safe`,
  `OMP_NUM_THREADS=1`, `workqueue`, свежий `NUMBA_CACHE_DIR`, `-s`, `--assert=plain`,
  faulthandler off — ничего не меняет. Дело в данных, а не в окружении.
- ⚠️ **Краш неперехватываем.** Это нативный abort/segfault — `try/except` его не ловит
  (процесс умирает до Python-обработчика). Поэтому «graceful degradation» из старого
  дока против этого не работает.

**Вывод по вопросу окружения:** numba доставлять не нужно — она рабочая. Проблема —
незащищённый вход в сторонний numba-код на вырожденных данных.

---

## 4. Лекарства (дефолт остаётся zigzag — по решению владельца)

### R1. Защитить обёртку ZigZag в bquant от вырожденного входа ✅ рекомендуется
- Перед вызовом pandas-ta zigzag проверять вход: слишком мало баров, или
  `high`/`low` практически константны (диапазон ≈ 0) → вернуть **пустой
  `SwingContext`** вместо захода в numba.
- Место: `bquant/analysis/zones/strategies/swing/zigzag.py` (метод `calculate_global`).
- Плюсы: дефолт остаётся zigzag; чинит и тест, и **реальные** плоские сегменты
  (остановленный/неликвидный рынок, гэпы) — это production-корректность, а не только
  тест. Не трогает numba/окружение.

### R2. Поправить данные крашащего теста (дёшево, дополняюще)
- Тест проверяет универсальность детекции, swing там побочен. Дать данные с движением
  или `swing=None` для этого теста. При наличии R1 — необязательно (обёртка отдаст
  пустые свинги, тест пройдёт).

### R3. Апстрим/пин pandas-ta (опционально)
- Сообщить о segfault на вырожденном входе; при наличии — запинить версию pandas-ta
  с фиксом. Не на критическом пути.

---

## 5. План

1. **R1** — input-guard в `ZigZagSwingStrategy.calculate_global` (несколько строк).
   Прогнать полный `pytest` → должен уйти краш; проверить, что зелёный.
2. **R2** — при необходимости подправить данные теста.
3. Зафиксировать в `revival_plan_2026-07.md`: дефолт остаётся zigzag; «зелёный CI»
   достигается input-guard'ом, без борьбы с версиями numba.

**Критерий готовности:** полный `pytest tests/` завершается без abort/segfault;
`ta.zigzag`-путь на вырожденных данных отдаёт пустые свинги, а не роняет процесс.

---

## 6. Влияние на рисёрч (этап 1)

Практически **нулевое для реальных данных** — на XAUUSD и любых данных с движением
zigzag работает (72 зоны). Дефолт можно оставить zigzag. Осторожность нужна только
при синтетике/вырожденных сегментах — до R1 их обходить (`swing='find_peaks'` или
`swing=None`).

---

## 7. Воспроизводимость

```python
# КРАШ (exit 139), вне pytest:
import pandas as pd, pandas_ta as ta
ta.zigzag(pd.Series([102.0]*200), pd.Series([98.0]*200), pd.Series([100.0]*200))

# РАБОТАЕТ (72 зоны) на реальных данных:
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones
df = get_sample_data("tv_xauusd_1h")
analyze_zones(df).with_indicator('custom','macd') \
  .detect_zones('zero_crossing', indicator_col='macd_hist') \
  .with_strategies(swing='zigzag').analyze(clustering=False).build()
```

---

*Итог: краш — latent-баг pandas-ta numba zigzag на вырожденных данных, а не проблема
установки numba. Дефолт остаётся zigzag; лечится input-guard'ом в обёртке (R1),
который заодно защищает реальные плоские сегменты рынка.*
