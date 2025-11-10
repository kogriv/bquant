# Сравнительный отчёт по стратегиям свингов

Этот отчёт описывает результаты запуска `research/notebooks/06_swing_strategy_comparison.py` с параметром `--no-trap` от 10.11.2025 и анализирует покрытие зон, характеристики свингов и время выполнения в режимах `per_zone` и `global` для стратегий `find_peaks`, `pivot_points` и `zigzag`.

## Шаг 1. Настройка и исходные данные
- Датасет: `tv_xauusd_1h`, диапазон 11.06.2025 20:00 (+07) — 12.08.2025 13:00 (+07), 1000 баров.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L1-L13】
- Во всех прогонах применяются одинаковые параметры: пресет `narrow_zone`, автоматическая подстройка порогов (`with_auto_swing_thresholds(True)`), отключённый кэш и вычисление индикатора `custom.macd` перед детекцией зон `zero_crossing`.【F:research/notebooks/06_swing_strategy_comparison.py†L50-L78】

## Шаг 2. Результаты по стратегиям
### Find Peaks
- Локальный (`per_zone`) и глобальный (`global`) режимы не формируют свинги: 0/37 бычьих зон содержат swing-метрики, среднее количество свингов остаётся 0, покрытие 0%.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L18-L21】【F:outputs/reports/swing_strategy_comparison.json†L1-L24】
- Глобальный режим ускоряет расчёт (0.423 с против 0.527 с), но отсутствуют rally/drop серии из‑за нулевого количества свингов.【F:outputs/reports/swing_strategy_comparison.json†L1-L24】
- Требуется ручной подбор порогов, если стратегия должна участвовать в продуктивных отчётах.

### Pivot Points
- Аналогично, ни один режим не находит свингов (0/37 зон, среднее количество свингов = 0).【F:research/notebooks/06_swing_strategy_comparison_log.txt†L24-L28】【F:outputs/reports/swing_strategy_comparison.json†L23-L48】
- Глобальный расчёт оказывается быстрее (0.399 с против 0.433 с), но без настройки порогов стратегия остаётся нефункциональной в текущем наборе параметров.【F:outputs/reports/swing_strategy_comparison.json†L23-L48】

### ZigZag
- Режим `per_zone` покрывает 23/37 бычьих зон (62.2%), среднее количество свингов 1.49, время выполнения 0.482 с.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L32-L33】【F:outputs/reports/swing_strategy_comparison.json†L51-L60】
- Режим `global` покрывает 36/37 зон (97.3%), среднее количество свингов 2.70 и время 0.490 с; прирост покрытия +35.1 п.п. при сопоставимом времени расчёта.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L34-L35】【F:outputs/reports/swing_strategy_comparison.json†L63-L72】
- Глобальный режим фиксирует рост средних процентов ралли/просадки, что повышает надёжность оценки тренда внутри зон.【F:outputs/reports/swing_strategy_comparison.json†L63-L72】

## Шаг 3. Сводная статистика
- Пивот-таблица подтверждает: прирост покрытия появляется только для `zigzag` (+35.1 п.п.), `find_peaks` и `pivot_points` остаются на 0% даже после глобализации.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L37-L50】
- Диапазон времен выполнения 0.399–0.527 с; глобальный режим не замедляет расчёты, а для `find_peaks` и `pivot_points` даже ускоряет их на 0.10–0.13 с.【F:outputs/reports/swing_strategy_comparison.json†L1-L70】

## Шаг 4. Выводы и рекомендации
1. Для `zigzag` глобальный режим рекомендуется для production-сценариев: покрытие 97.3% и прирост +35.1 п.п. против локального расчёта при сопоставимой скорости.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L32-L35】【F:outputs/reports/swing_strategy_comparison.json†L51-L72】
2. Для `find_peaks` и `pivot_points` требуется переобучение/тюнинг порогов перед использованием: текущие авто-пороги обнуляют свинги даже при глобальной нарезке.【F:research/notebooks/06_swing_strategy_comparison_log.txt†L18-L28】【F:outputs/reports/swing_strategy_comparison.json†L1-L48】
3. При расширении набора стратегий следует включать в отчёты сравнение покрытий и времени выполнения по аналогичной схеме (JSON/CSV файлы `outputs/reports/swing_strategy_comparison.*`).【F:research/notebooks/06_swing_strategy_comparison_log.txt†L52-L60】【F:outputs/reports/swing_strategy_comparison.json†L1-L70】
