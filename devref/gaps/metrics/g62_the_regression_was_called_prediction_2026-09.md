# G62 — Регрессия называлась prediction, объясняя завершённую зону её же признаками

**Заведён:** 2026-09-05, из аудита качества (AQ-029).
**Статус:** ✅ закрыт 2026-09-05 — `explain_*`, вид и доступность признаков в метаданных, Дарбин-Уотсон считается.

---

## 1. Что было — замер

`predict_price_return` на сэмпле: предикторы `duration`, `line_amplitude`,
`correlation_price_oscillator`, `drawdown_from_peak`, `oscillator_slope`, `num_peaks` — все
измерены по **всей завершённой** зоне (просадка от пика содержит цену конца), цель —
`price_return` той же зоны. Это объяснение постфактум; R² здесь не предсказательная сила.
`metadata['durbin_watson']` — **`None`**: читался как атрибут подогнанной модели, которого у
`OLSResults` нет.

## 2. Что сделано

- `predict_zone_duration` → `explain_zone_duration`, `predict_price_return` →
  `explain_price_return`; без алиасов. Докстринги называют, что признаки известны только по
  окончании зоны.
- `metadata['kind'] = 'in_sample_explanatory'`, `metadata['feature_availability'] = 'ex_post'`.
- `durbin_watson` — `statsmodels.stats.stattools.durbin_watson(residuals)`; на сэмпле 2.31.
- Ключи `regression_results['duration'|'return']` не менялись.
- Постоянная цель — отказ (`Target 'duration' is constant across all 12 observations`) после
  проверки дизайна: без угаданного предиктора (G61) фикстура из 4 зон × 3 подогналась с
  `R² = −inf` — OLS не отказывает сам.

Признаки на момент решения (decision-time) и out-of-sample прогноз из предложения аудита —
не строились: это новая возможность, не починка имени.

## 3. Проверка

Та же папка тестов: `kind`/`feature_availability` в метаданных обоих моделей, `durbin_watson`
в (0, 4); имён `predict_*` нет. Три файла тестов переведены на `explain_*`. Мутация:
`durbin_watson: None` — 1 красный.

## 4. Цена

Имена методов; `docs/api/analysis/statistical.md` и `zone_analysis_result.md`,
`zone_detection_strategies.md` — по новым именам с объяснением, почему они такие.
