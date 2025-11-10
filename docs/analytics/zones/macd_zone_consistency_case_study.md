# Аналитический отчёт по состоятельности бычьих зон MACD

Этот отчёт фиксирует результаты запуска `research/notebooks/05_case_study_zone_consistency.py` с параметром `--no-trap` от 10.11.2025 и анализирует полученные метрики по шагам пайплайна.

## Шаг 1. Данные и гипотезы
- Исходный датасет: `tv_xauusd_1h`, 1000 баров за период 11.06.2025 20:00 (+07) — 12.08.2025 13:00 (+07).【F:research/notebooks/05_case_study_zone_consistency_log.txt†L11-L12】
- Гипотеза H1: внутри бычьих зон MACD средние ап‑свинги превышают даун‑свинги; H0 утверждает отсутствие статистически значимой разницы.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L12-L14】

## Шаг 2. Исследовательский анализ зон (EDA)
- Детектор `zero_crossing` выявил 72 зоны (37 бычьих, 35 медвежьих).【F:research/notebooks/05_case_study_zone_consistency_log.txt†L18-L21】
- Инвентаризация метрик подтвердила наличие полного набора swing-метрик в `metadata` зон.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L18-L21】
- При использовании пресета `narrow_zone` с `find_peaks` только 6 из 37 бычьих зон (16.2%) имели хотя бы один свинг; остальные 83.8% давали `num_swings = 0`, среднее число свингов — 0.19, в среднем 0.54 ап‑свинга и 0.32 даун‑свинга на зону.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L18-L21】【F:outputs/reports/macd_zone_consistency_results.json†L3-L16】

## Шаг 3. Основной эксперимент
Пайплайн повторно запускался с отключённым кэшем для двух конфигураций swing-параметров и трёх стратегий (`find_peaks`, `pivot_points`, `zigzag`).

### Конфигурация «Узкий пресет (фиксированные пороги)»
- `find_peaks`: 6/37 зон (16.2%) содержат свинги; собрано 6 пар «ап‑/даун‑свинг», этого недостаточно для теста Уилкоксона в режиме `per_zone`. В глобальном режиме покрытие растёт до 15/37 зон (40.5%), появляется 15 пар и тест выдаёт статистику 86.0 при p-value 0.0757 — тренд в пользу H1 без формальной значимости на уровне 0.05.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L31-L34】【F:outputs/reports/macd_zone_consistency_results.json†L18-L35】【F:outputs/reports/macd_zone_consistency_results.json†L116-L143】
- `pivot_points`: 3/37 зон (8.1%) со свингами; всего 3 пары и тест Уилкоксона не выполняется. При глобальных свингах покрытие подскакивает до 21/37 зон (56.8%), но p-value 0.1361 остаётся выше критерия значимости.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L38-L41】【F:outputs/reports/macd_zone_consistency_results.json†L36-L51】【F:outputs/reports/macd_zone_consistency_results.json†L144-L167】
- `zigzag`: 23/37 зон (62.2%) со свингами и 23 пары; тест Уилкоксона даёт статистику 232.0 и p-value 0.0015. В глобальном режиме покрытие вырастает до 36/37 зон (97.3%), статистика 484.0 и p-value 0.0084 подтверждают преимущество ап‑свингов и устойчивость H1.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L45-L48】【F:outputs/reports/macd_zone_consistency_results.json†L52-L67】【F:outputs/reports/macd_zone_consistency_results.json†L168-L199】

### Конфигурация «Узкий пресет + авто-пороги»
- `find_peaks`: при включённой авто-настройке порогов 0/37 зон содержат свинги как в режиме `per_zone`, так и в `global`; тест Уилкоксона не запускается из-за отсутствия пар.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L55-L58】【F:outputs/reports/macd_zone_consistency_results.json†L200-L231】
- `pivot_points`: также 0/37 зон со свингами в обоих режимах; требуется ручной подбор параметров авто-порогов перед повторным запуском исследования.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L62-L65】【F:outputs/reports/macd_zone_consistency_results.json†L232-L263】
- `zigzag`: сохраняет покрытие 23/37 зон (62.2%) и статистику 232.0 с p-value 0.0015 в `per_zone`. В глобальном режиме покрытие повышается до 36/37 зон (97.3%), а p-value снижается до 0.0073, что усиливает доверие к H1.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L69-L72】【F:outputs/reports/macd_zone_consistency_results.json†L264-L303】

## Шаг 4. Сводка и выводы
- Стратегия `zigzag` с фиксированным пресетом `narrow_zone` остаётся единственной комбинацией, которая стабильно обеспечивает покрытие ≥97% зон и значимые результаты как в `per_zone`, так и в `global` (p-value 0.0015 и 0.0084 соответственно).【F:research/notebooks/05_case_study_zone_consistency_log.txt†L45-L48】【F:outputs/reports/macd_zone_consistency_results.json†L52-L67】【F:outputs/reports/macd_zone_consistency_results.json†L168-L199】
- Режим `global` существенно повышает покрытие для `find_peaks` и `pivot_points`, но при текущих настройках тест Уилкоксона остаётся незначимым (p-value 0.0757 и 0.1361). Эти стратегии требуют дополнительного тюнинга параметров перед использованием в продуктивных отчётах.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L31-L41】【F:outputs/reports/macd_zone_consistency_results.json†L18-L51】【F:outputs/reports/macd_zone_consistency_results.json†L116-L167】
- Автоматическое масштабирование порогов (`with_auto_swing_thresholds(True)`) для `find_peaks` и `pivot_points` по-прежнему обнуляет свинги в обоих режимах, тогда как `zigzag` демонстрирует прирост доверия к гипотезе H1 благодаря снижению p-value до 0.0073 в глобальном режиме.【F:research/notebooks/05_case_study_zone_consistency_log.txt†L55-L72】【F:outputs/reports/macd_zone_consistency_results.json†L200-L303】

## Рекомендации
1. Для воспроизводимого покрытия ≥60% зон свингами использовать `with_swing_preset('narrow_zone')` без авто-порогов и отдавать приоритет стратегии `zigzag` при формировании выводов по MACD-зонам.
2. Перед включением `with_auto_swing_thresholds(True)` для `find_peaks` и `pivot_points` выполнить отдельный тюнинг параметров, чтобы избежать нулевого покрытия и недоступности статистических тестов.
3. Контролировать покрытие и статистику свингов через экспортируемый JSON-отчёт `outputs/reports/macd_zone_consistency_results.json` при каждом обновлении пресетов или стратегий, а также отслеживать p-value для подтверждения гипотезы H1.
