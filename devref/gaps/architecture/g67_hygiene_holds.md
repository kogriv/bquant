# G67 — Гигиена репозитория: мёртвый код, экспорты без потребителей, артефакты на удалённый API

**Заведён:** 2026-09-05 (реестр; находки AQ-048, 049, 050, 052, 054, 055 аудита качества 2026-09-04, P3).
**Статус:** ✅ закрыт 2026-09-06 (AQ-055 закрыт G65 — `available_methods()` интроспекцией).

---

## 1. Как нашли

Аудит перечислил кандидатов; каждый проверен грепом и графом codemap (`impact` по
`plot_macd_zones_chart`, `analyze_zones_visually` — ноль ссылок в пакете). Две находки
сверх аудита всплыли при замере: сканер публичной поверхности не видел `__all__.extend`, и
в трёх файлах репозитория лежали имена личных окружений.

## 2. Замер до правки

| Находка | Что было | Замер |
|---|---|---|
| AQ-048 | `_StubIndicator`; `bquant.core.exceptions.NotImplementedError`; `ensure_logging_initialized()`; `try: pass / except: pass` в `indicators/library/__init__.py`; `core/utils.setup_project_logging` — полная вторая настройка логирования | ноль использований у первых трёх; класс перекрывал встроенное имя (доки предупреждали абзацем); `utils.py` ставил обработчики **на импорте**, а `docs/api/core/utils.md` называл функцию «тонкой обёрткой над `setup_logging()`» |
| AQ-049 | `plot_macd_zones_chart`, `analyze_zones_visually`, `DistributionPlotter`, `load_*` экспортированы без внутренних потребителей | первые три **не упомянуты в доках ни разу** — и сканер этого не видел: `bquant.visualization` и `bquant.analysis.zones` строят `__all__` через `.extend([...])`, а сканер читал только литерал `__all__ = [...]`. Всего мимо него шли 12 имён; функции работают (три `Figure`) |
| AQ-050 | `get_zone_features_summary()` без вызывающих, хардкод `bull`/`bear`, `{'error': …}` на пустом входе | вопреки открытому словарю типов (G28): зоны `overbought`/`oversold` в сводку не попадали |
| AQ-052 | `devref/gaps/zo/zodoctest/` — 30 `test_*.py` под `MACDZoneAnalyzer` (удалён в 0.0.5); `tests/API_MIGRATION_GUIDE.md`, `tcheck.md`, `README_TESTS.md` — сьют 2025-10 «670 passed, production-ready» | не исполняются, читаются как инфраструктура; `README_TESTS.md` и README архива несли имя личного окружения |
| AQ-054 | `CustomIndicator.calculate_with_cache()` = `calculate()` | `IndicatorCalculator` звал именно его — «кэш», которого нет |
| AQ-055 | `MACD.get_info()` рекламировал `get_crossovers()` | закрыто G65 |
| сверх | `set_default_theme('nope')` | `True`: результат `apply_theme()` не читался |
| сверх | имена личных окружений (`venv_*_dell*`) | `pyproject.toml` (exclude/omit), `devref/publish/{cleanup.sh,cleanup.ps1,build-instructions.md}`, `scripts/publishing/cleanup.sh`, `devref/gaps/zo/zoval.md`, `devref/archive/migration/progress.md`, два трейслога 2025-10 |

## 3. Почему это форма «проверка не видит проверяемого»

Сканер, читающий литерал там, где пакет исполняет `.extend`, отчитывался «все имена
документированы» о поверхности, которой не видел. `test_*.py` вне сьюта выглядели тестами
и не бежали. Документ, обещавший «тонкую обёртку», описывал не тот код.

## 4. Что сделано

* Снято: `_StubIndicator`, `exceptions.NotImplementedError`, `ensure_logging_initialized`,
  `try/pass`, `calculate_with_cache`; `setup_project_logging` — обёртка над
  `setup_logging()`, модульный логгер `utils.py` — `get_logger()` без обработчиков.
* Сканер публичной поверхности читает **исполненный** `__all__`; девять имён
  задокументированы с примерами из прогона (`docs/api/visualization/README.md`,
  `docs/api/analysis/zones.md`); `set_default_theme` отказывает по имени.
* `get_zone_features_summary` — по каждому типу (`by_type`), `ValueError` на пустом входе.
* `zodoctest` → `zodoctest_archive` с баннером «не исполняется»; три документа в `tests/`
  удалены, `tests/STATUS.md` говорит почему; имена личных окружений заменены на `<venv>` /
  `venv_*`. **В истории git они остаются** — редакция `HEAD` историю не чистит. Решение владельца
  2026-09-06: историю **не переписывать** (перепись меняет все sha, а потребитель пинит sha;
  чувствительность имени личного окружения низкая).

## 5. Сторожа

`tests/unit/test_hygiene_holds.py` — снятые имена не определены; ни одно исключение
пакета не перекрывает встроенное; нет `try: pass` на уровне модуля; `setup_project_logging`
делегирует и импорт `utils` не вешает обработчики; сводка по всем типам и отказ на пустом;
`test_*.py` только в `tests/`; `MACDZoneAnalyzer` никем не импортируется; сканер видит
`.extend`; неизвестная тема — `ValueError`; три экспорта без потребителей дают фигуры.

## 6. Ломает

`bquant.core.exceptions.NotImplementedError`, `ensure_logging_initialized`,
`calculate_with_cache`, `_StubIndicator` — удалены; `get_zone_features_summary` — новая форма
(`by_type`) и `ValueError` вместо `{'error': …}`; `set_default_theme` — `ValueError` вместо
`True`/`False`; `setup_project_logging` настраивает логирование пакета целиком, а не
отдельный логгер.
