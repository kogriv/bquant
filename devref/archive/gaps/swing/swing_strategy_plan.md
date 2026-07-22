# План разработки: восстановление свинг-метрик и устойчивого тюнинга

## Проблема и целевые ориентиры
- Дефолтные пороги свинг-стратегий отсекают движения в узких зонах, поэтому метрики `num_swings`, `rally_count`, `drop_count` остаются нулевыми даже при наличии колебаний (средний рост бычьих зон ≈0.21 %, максимум 2.32 % против порога 5 % для ZigZag и 1.5–2 % для `find_peaks`/`pivot_points`).【F:devref/gaps/swing/strat_issue.md†L15-L41】  Целевой KPI: средняя насыщенность свингов > 1 на зону для `tv_xauusd_1h`.
- Кэш `ZoneAnalysisPipeline` не учитывает выбранные стратегии и параметры, из‑за чего переключение конфигурации без ручного сброса возвращает устаревшие результаты и скрывает эффект тюнинга.【F:devref/gaps/swing/strat_issue.md†L41-L47】  Цель: изменить ключ кэша так, чтобы любые изменения стратегии инициировали перерасчёт.
- Скрипт `research/notebooks/validate_swing_pivots.py` даёт эталонную проверку: отключает кэш, сравнивает дефолтные и ослабленные пороги и валидирует pivot-точки на конкретной зоне.【F:devref/gaps/swing/strat_issue.md†L49-L63】  Требование: включить его в регрессионный сценарий проверки новых параметров.

## Этап 1. Перенастройка дефолтов и пресетов
1. **Добавление таблицы параметров**: в `bquant/core/config.py` зафиксировать структуру `SWING_PRESETS`, включающую:
   - `"default"`: текущие значения (`legs=10`, `deviation=0.05`, пороги `find_peaks`/`pivot_points`).
   - `"narrow_zone"`: параметры из наблюдений (`legs=3`, `deviation=0.008`) и сниженные амплитуды для `find_peaks`/`pivot_points`, чтобы покрывать узкие зоны.【F:devref/gaps/swing/strat_issue.md†L33-L38】  Заготовка:
     ```python
     SWING_PRESETS = {
         "default": SwingPreset(
             zigzag=dict(legs=10, deviation=0.05, backstep=3),
             find_peaks=dict(prominence=0.015, distance=5),
             pivot_points=dict(deviation=0.02),
         ),
         "narrow_zone": SwingPreset(
             zigzag=dict(legs=3, deviation=0.008, backstep=3),
             find_peaks=dict(prominence=0.004, distance=3),
             pivot_points=dict(deviation=0.006),
         ),
     }
     ```
2. **API для выбора пресета**: расширить `ZoneAnalysisPipeline` методом `with_swing_preset(name: str)`, который применяет настройки ко всем зарегистрированным стратегиям. Шаблон вызова:
   ```python
   def with_swing_preset(self, name: str) -> "ZoneAnalysisPipeline":
       preset = SWING_PRESETS[name]
       self.swing_strategies["zigzag"].configure(**preset.zigzag)
       ...
       return self
   ```
3. **Тесты этапа**:
   - ✅ `pytest tests/analysis/zones/test_swing_presets.py::test_narrow_zone_applies_parameters` — убедиться, что пресет выставляет параметры стратегий и насыщенность свингов > 1 на зону для `tv_xauusd_1h` (контрольные значения 23 зон / 55 свингов допускают ±20 %).
   - ✅ `poetry run python research/notebooks/validate_swing_pivots.py --dataset tv_xauusd_1h --preset narrow_zone --export outputs/reports/swing_narrow.json` — сверить результаты с KPI.

## Этап 2. Опциональный адаптивный расчёт порогов
1. **Утилита расчёта**: создать `bquant/analysis/zones/strategies/swing/thresholds.py` с функцией, масштабирующей пороги по диапазону цены:
   ```python
   def auto_swing_thresholds(zone_df: pd.DataFrame, *, base_deviation: float = 0.01) -> SwingThresholds:
       price_range = zone_df["high"].max() - zone_df["low"].min()
       mid_price = zone_df["close"].median() or zone_df["close"].mean()
       relative_range = price_range / mid_price if mid_price else base_deviation
       deviation = max(base_deviation, relative_range * 0.5)
       return SwingThresholds(
           zigzag_deviation=deviation,
           peak_prominence=max(base_deviation, relative_range * 0.3),
           pivot_deviation=max(base_deviation, relative_range * 0.25),
       )
   ```
2. **Переключатель в пайплайне**: добавить параметр `strategy_auto_thresholds: bool = False` в `ZoneAnalysisPipeline`. Если опция включена, стратегии получают пороги из `auto_swing_thresholds` на основе данных зоны, иначе используются пресеты.
3. **Тесты этапа**:
   - ✅ `pytest tests/analysis/zones/test_swing_thresholds.py::test_auto_thresholds_scale_with_range` — проверяет, что увеличение диапазона зоны увеличивает возвращаемые пороги и что значения не падают ниже `base_deviation`.
   - ✅ `pytest tests/analysis/zones/test_swing_thresholds.py::test_pipeline_auto_thresholds_matches_kpi` — прогоняет зону `tv_xauusd_1h` с авто-порогами и подтверждает насыщенность > 1.

## Этап 3. Обновление ключа кэша пайплайна
1. **Расширение ключа**: в `bquant/analysis/zones/pipeline.py` обновить `_generate_cache_key`, чтобы включить сериализованные параметры стратегий:
   ```python
   def _generate_cache_key(self) -> str:
       base_key = {
           "detector": self.detector_config.hash_key(),
           "strategies": {
               name: strategy.config_hash()
               for name, strategy in sorted(self.swing_strategies.items())
           },
           # существующие поля...
       }
       return hashlib.sha256(json.dumps(base_key, sort_keys=True).encode()).hexdigest()
   ```
2. **Интерфейс конфигурации**: дополнить базовый класс `SwingStrategy` абстрактным методом `config_hash`, а в `FindPeaksSwingStrategy`, `PivotPointsSwingStrategy`, `ZigZagSwingStrategy` реализовать возврат словаря параметров.
3. **Тесты этапа**:
   - ✅ `pytest tests/analysis/zones/test_pipeline_cache.py::test_cache_key_changes_on_strategy_update` — убедиться, что изменение параметров стратегии меняет ключ кэша.
   - ✅ `pytest tests/analysis/zones/test_pipeline_cache.py::test_pipeline_recomputes_after_preset_switch` — проверить, что после переключения пресета пайплайн повторно рассчитывает метрики.

## Этап 4. Документация и эксплуатационные инструкции
1. **Developer reference**: обновить/создать `devref/gaps/swing/README.md`, добавив таблицу параметров пресетов, ссылки на KPI из отчёта и инструкцию по запуску `validate_swing_pivots.py`.
2. **Пользовательская документация**: расширить `docs/analytics/zones/swing.md` примером использования `with_swing_preset("narrow_zone")` и описанием опции `strategy_auto_thresholds`.
3. **Тесты этапа**:
   - ✅ `poetry run python research/notebooks/validate_swing_pivots.py --dataset tv_xauusd_1h --preset default --export outputs/reports/swing_default.json` — зафиксировать базовый отчёт для сравнения.
   - ✅ `poetry run python research/notebooks/validate_swing_pivots.py --dataset tv_xauusd_1h --preset narrow_zone --check` — удостовериться, что pivot-валидатор проходит без нарушений.

## Этап 5. Финальная регрессия и контроль изменений
1. Собрать все тесты из предыдущих этапов в `poetry run pytest tests/analysis/zones -k "swing"` и убедиться в прохождении KPI.
2. Обновить `CHANGELOG.md` в блоке `Unreleased`, отметив: «Ослаблены дефолтные пороги свинг-стратегий, добавлен пресет `narrow_zone`, кэш учитывает параметры стратегий, описаны шаги валидации swing-метрик» с ссылкой на наблюдения из отчёта.【F:devref/gaps/swing/strat_issue.md†L15-L63】
3. Зафиксировать в issue/документе результат прогонов `validate_swing_pivots.py`, чтобы команда могла сравнивать будущие изменения с текущим состоянием.
