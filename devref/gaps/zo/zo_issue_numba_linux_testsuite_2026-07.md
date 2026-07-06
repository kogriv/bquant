# Issue: Numba abort on Linux breaks the test suite (ZigZag / default swing)

**Дата:** 2026-07-06
**Тип:** environment / test-suite health
**Приоритет:** 🟠 Medium-High — нет способа получить полностью зелёный `pytest` в текущем окружении; спотыкается дефолтный swing-путь
**Статус:** 🟡 Open — диагностировано на фактах, лекарства предложены и частично проверены

**Связь:** обновляет `devref/gaps/zo/zo_issue_numba_zoneinfo_none.md` (2025-10-19),
Problem #2. Тот док считал краш **Windows-only** («на Linux не воспроизводится») и
полагался на graceful degradation. Оба тезиса теперь **неверны** — см. ниже.

---

## 1. Симптом

- Полный `pytest tests/` в обычном режиме **падает с фатальным крашем** на
  `tests/integration/test_truly_universal_zones.py`:
  `Fatal Python error: Aborted`, процесс завершается кодом **134** (SIGABRT).
  Стек — в `numba/core/caching.py` (`_load_overload` / `_index_key`) при JIT-компиляции.
- До точки краша — **ноль фейлов** (тесты идут зелёными, потом abort).
- Обход `NUMBA_DISABLE_JIT=1` убирает краш, но ломает регистрацию `zigzag`
  (`LIBRARY indicator 'zigzag' from 'pandas_ta' not found`) → **8 фейлов** в
  swing/zigzag-зависимых тестах.

**Итог: чистого зелёного прогона в этом окружении сейчас нет** — либо abort (JIT on),
либо 8 zigzag-фейлов (JIT off). Оба — про numba/pandas-ta, не про бизнес-логику.

---

## 2. Факты (замерено)

| Что | Значение |
|-----|----------|
| numba | 0.61.2 |
| llvmlite | 0.44.0 |
| pandas-ta | 0.4.67b0 (`__version__` не выставлен) |
| Платформа | Linux (cloud/CI-окружение сессии) |
| Краш-тест | `test_truly_universal_zones.py`, exit **134 (Aborted)** |
| Свежий `NUMBA_CACHE_DIR` | **НЕ лечит** — краш повторяется |
| Источник numba | только `pandas_ta` zigzag; сами swing-стратегии bquant numba не импортируют |

**Ключевая проверка — non-zigzag swing работает штатно (обычный JIT):**

```
swing=find_peaks    OK  zones=72
swing=pivot_points  OK  zones=72
```

Крашится **только** `zigzag`. `find_peaks` (scipy) и `pivot_points` (чистый Python)
проходят без проблем и дают тот же счёт зон (72).

**Дефолт указывает в крашащий путь:** `bquant/core/config.py:162` —
`DEFAULT_SWING_PRESET="default"` использует `'type': 'zigzag'`. То есть штатный
сценарий по умолчанию идёт ровно в numba-abort.

---

## 3. Корневая причина и важная поправка

- Краш — при **JIT-компиляции numba** внутри pandas-ta zigzag (numba 0.61.2 /
  llvmlite 0.44.0 в этом окружении). Это внешняя связка, не код bquant.
- **Abort (SIGABRT) НЕ перехватывается** `try/except` — процесс умирает до Python-
  обработчика. Поэтому «graceful degradation» из старого дока
  (`zone_features.py` оборачивает swing в try/except) **не защищает**: код падает
  внутри нативного numba, а не бросает Python-исключение.
- Старый тезис «на Linux не воспроизводится» устарел — на текущем окружении/версиях
  воспроизводится стабильно.

---

## 4. Лекарства (по возрастанию усилий; R1 рекомендуется)

### R1. Сменить дефолтную swing-стратегию на non-numba ✅ рекомендуется
- `find_peaks` или `pivot_points` вместо `zigzag` в `DEFAULT_SWING_PRESET`.
- Убирает numba из **дефолтного** пути; проверено — обе работают, тот же счёт зон.
- Дёшево, устойчиво, не трогает внешние зависимости. `zigzag` остаётся доступным
  явным выбором (для окружений, где numba здорова).

### R2. Изолировать zigzag-тесты, чтобы CI был зелёным
- Пометить zigzag/numba-зависимые тесты `@pytest.mark.skipif`, пропуская их, когда
  numba-zigzag недоступна/крашит.
- **Нюанс:** т.к. это abort, нельзя «попробовать и поймать» — проверку доступности
  надо делать заранее (проба в subprocess или env-флаг), а не через try/except в
  самом тесте.

### R3. Зафиксировать версии numba/llvmlite (root-cause, хрупко)
- Подобрать комбо numba/llvmlite, не дающее abort в этом окружении, и запинить в
  `pyproject`/`requirements`. Минус — привязка к окружению, может не переноситься.

### R4. Чистый Python ZigZag без numba (durable, опционально)
- Своя реализация zigzag (pandas/numpy), чтобы стратегия перестала зависеть от
  numba вовсе. Больше работы; имеет смысл, если zigzag нужен как дефолт.

---

## 5. Рекомендованный план

1. **R1** — переключить дефолтный swing на `find_peaks` (быстро, снимает боль
   дефолтного пути и большинство swing-фейлов). Обновить пресеты/доки.
2. **R2** — заскипать оставшиеся именно-zigzag тесты по проверке доступности numba,
   чтобы `pytest` был детерминированно зелёным. Явно логировать, что пропущено.
3. Зафиксировать в `revival_plan_2026-07.md`: «зелёный CI» достигается через R1+R2;
   R3/R4 — по желанию, не на критическом пути.

**Критерий готовности:** `pytest tests/` завершается без abort и без «случайных»
фейлов (только осознанные skip у zigzag-тестов при недоступной numba).

---

## 6. Влияние на рисёрч (этап 1)

Прямое: **дефолтный** `analyze_zones(...).build()` со swing сейчас идёт в abort на
этом окружении. Пока R1 не сделан — в рисёрче использовать `find_peaks`/`pivot_points`
явно (`.with_strategies(swing='find_peaks')`) либо `swing=None`. После R1 дефолт
станет безопасным.

---

## 7. Воспроизводимость

```
# abort (JIT on):
python -m pytest tests/integration/test_truly_universal_zones.py -q   # exit 134

# 8 фейлов (JIT off):
NUMBA_DISABLE_JIT=1 python -m pytest tests/ -q

# non-numba swing работает:
analyze_zones(df).with_indicator('custom','macd')
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='find_peaks').analyze(clustering=False).build()
```

---

*Итог: краш — во внешней numba/pandas-ta (zigzag), не в bquant. Дешёвое лекарство —
увести дефолтный swing на non-numba стратегию (R1) и заскипать zigzag-тесты (R2);
это возвращает зелёный прогон без борьбы с версиями numba.*
