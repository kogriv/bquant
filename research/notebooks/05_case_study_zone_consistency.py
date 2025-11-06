"""
Case Study: Verifying the Consistency of MACD Bull Zones

This research notebook implements a case study to answer the question:
"Are MACD bull zones structurally 'consistent'? Do upward swings inside them
statistically dominate the downward swings?"

The study will:
1.  Use `analyze_zones` to find all MACD bull zones in a sample dataset.
2.  Apply three different swing detection strategies (`find_peaks`, `pivot_points`, `zigzag`)
    to extract internal swing metrics from each zone.
3.  For each strategy, use a statistical test (Wilcoxon signed-rank test) to
    determine if upward swings are significantly larger than downward swings.
4.  Compare the results from the three strategies to draw a final conclusion.

USAGE:
python research/notebooks/05_case_study_zone_consistency.py --no-trap
"""

import pandas as pd
import numpy as np
from scipy.stats import wilcoxon
import warnings

# Configure logging and project-specific imports
from bquant.core.logging_config import setup_logging
setup_logging(profile='research')

from bquant.core.nb import NotebookSimulator
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

# Suppress warnings from stats tests with small sample sizes
warnings.filterwarnings("ignore", category=UserWarning, module='scipy.stats.morestats')

# --- Initialization ---
nb = NotebookSimulator(
    "Case Study: Verifying the Consistency of MACD Bull Zones"
)

nb.step("Шаг 1: Загрузка данных и постановка гипотезы")

nb.info("1.1. Загрузка исторических данных")
df = get_sample_data('tv_xauusd_1h')
if 'time' in df.columns:
    df = df.set_index('time')
nb.success(f"Данные загружены. Период: {df.index.min()} - {df.index.max()}, Баров: {len(df)}")

nb.info("1.2. Постановка гипотезы")
nb.log("Основная гипотеза (H1):")
nb.log("  Внутри 'бычьих зон' MACD, восходящие колебания (ап-свинги) статистически значимо превосходят по своей средней величине нисходящие колебания (даун-свинги).")
nb.log("Нулевая гипотеза (H0):")
nb.log("  Разница в величине между ап-свингами и даун-свингами внутри бычьих зон статистически не значима.")
nb.log("")
nb.log("Мы проверим эту гипотезу с помощью трех различных алгоритмов поиска свингов, чтобы оценить надежность вывода.")

nb.wait()


nb.wait()


nb.step("Шаг 2: Исследовательский анализ данных (EDA) метрик зон")

with nb.error_handling("Exploratory Data Analysis"):
    nb.info("2.1. Получение репрезентативного набора метрик")
    # Запустим анализ один раз со стратегией по умолчанию, чтобы исследовать генерируемые метрики
    eda_result = (
        analyze_zones(df)
        .with_cache(enable=False)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='find_peaks')
        .with_swing_preset('narrow_zone')
        .analyze(clustering=False)
        .build()
    )
    nb.success(f"Анализ для EDA завершен. Найдено {len(eda_result.zones)} зон.")

    nb.info("2.2. Инвентаризация доступных метрик")
    first_bull_zone = next((z for z in eda_result.zones if z.type == 'bull' and z.features), None)
    if first_bull_zone:
        nb.log("Доступные метрики верхнего уровня ('features'):")
        nb.log(f"  {list(first_bull_zone.features.keys())}")
        if 'metadata' in first_bull_zone.features and 'swing_metrics' in first_bull_zone.features['metadata']:
            nb.log("Доступные метрики свингов ('swing_metrics'):")
            nb.log(f"  {list(first_bull_zone.features['metadata']['swing_metrics'].keys())}")
        nb.log("\n(Примечание: Логика генерации этих метрик находится в классах ...Strategy в `bquant/analysis/zones/strategies`)")
    else:
        nb.warning("Не найдено ни одной бычьей зоны с метриками для инвентаризации.")

    nb.info("2.3. Сводная статистика по метрикам свингов")
    num_swings_list = []
    rally_counts = []
    drop_counts = []
    bull_zones_with_swings = 0
    bull_zones_total = 0
    pct_with_swings = 0.0
    for zone in eda_result.zones:
        if zone.type == 'bull':
            bull_zones_total += 1
            if zone.features and 'metadata' in zone.features and 'swing_metrics' in zone.features['metadata']:
                swing_metrics = zone.features['metadata']['swing_metrics']
                num_swings = swing_metrics.get('num_swings', 0)
                num_swings_list.append(num_swings)
                rally_counts.append(swing_metrics.get('rally_count', 0))
                drop_counts.append(swing_metrics.get('drop_count', 0))
                if num_swings > 0:
                    bull_zones_with_swings += 1

    if bull_zones_total > 0:
        zones_with_zero_swings = bull_zones_total - bull_zones_with_swings
        pct_zero_swings = (zones_with_zero_swings / bull_zones_total) * 100
        pct_with_swings = 100 - pct_zero_swings
        nb.log(f"Всего найдено бычьих зон: {bull_zones_total}")
        nb.log(f"Из них зон с внутренними свингами: {bull_zones_with_swings}")
        nb.log(f"Зон без внутренних свингов (num_swings = 0): {zones_with_zero_swings} ({pct_zero_swings:.1f}%)")

        if len(num_swings_list) > 0:
            nb.log(f"Статистика по количеству свингов: Min={min(num_swings_list)}, Max={max(num_swings_list)}, Avg={np.mean(num_swings_list):.2f}")
            nb.log(
                "Статистика по количеству ап- и даун-свингов в релевантных зонах: "
                f"Avg rally_count={np.mean(rally_counts):.2f}, Avg drop_count={np.mean(drop_counts):.2f}"
            )
    else:
        nb.warning("В данных не найдено бычьих зон.")

    nb.info("2.4. Решение для основного анализа")
    nb.log(
        "В основной части исследования будут участвовать только зоны с рассчитанными свинг-метриками "
        "и наличием хотя бы одного ап- и даун-свинга."
    )

nb.wait()


# --- Main Analysis Loop ---
swing_strategies = ['find_peaks', 'pivot_points', 'zigzag']
analysis_configs = [
    {
        'name': 'narrow_fixed',
        'label': "Узкий пресет (фиксированные пороги)",
        'description': "Применяем пресет 'narrow_zone' с фиксированными параметрами свинг-стратегий.",
        'apply': lambda builder: builder.with_swing_preset('narrow_zone'),
    },
    {
        'name': 'narrow_auto',
        'label': "Узкий пресет + авто-пороги",
        'description': "Используем пресет 'narrow_zone' и дополнительно включаем auto-thresholds для адаптации к волатильности.",
        'apply': lambda builder: builder.with_swing_preset('narrow_zone').with_auto_swing_thresholds(True),
    },
]

final_results = {config['name']: {} for config in analysis_configs}
report_data = {
    'eda': {
        'bull_zones_total': bull_zones_total,
        'bull_zones_with_swings': bull_zones_with_swings,
        'pct_with_swings': pct_with_swings if bull_zones_total else 0.0,
        'num_swings_stats': {
            'min': min(num_swings_list) if num_swings_list else None,
            'max': max(num_swings_list) if num_swings_list else None,
            'avg': float(np.mean(num_swings_list)) if num_swings_list else None,
        },
        'avg_rally_count': float(np.mean(rally_counts)) if rally_counts else None,
        'avg_drop_count': float(np.mean(drop_counts)) if drop_counts else None,
    },
    'analysis': {},
}

for config in analysis_configs:
    nb.section_header(f"Конфигурация: {config['label']}")
    nb.log(config['description'])

    for strategy in swing_strategies:
        nb.step(f"Шаг 2: Анализ ({config['label']}) стратегией '{strategy}'")

        with nb.error_handling(f"Analysis with {strategy} [{config['name']}]"):
            nb.info(f"2.1. Поиск зон и извлечение свингов с помощью '{strategy}'")

            builder = (
                analyze_zones(df)
                .with_cache(enable=False)
                .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .with_strategies(swing=strategy)
            )

            builder = config['apply'](builder)

            analysis_result = (
                builder
                .analyze(clustering=False)  # Clustering not needed for this analysis
                .build()
            )

            nb.success(f"Анализ завершен. Найдено {len(analysis_result.zones)} зон.")

            nb.info("2.2. Сбор данных для статистического теста")

            rallies = []
            drawdowns = []

            bull_zones = [zone for zone in analysis_result.zones if zone.type == 'bull']
            total_bull = len(bull_zones)
            zones_with_metrics = 0
            zones_with_swings = 0
            num_swings_values = []
            rally_counts = []
            drop_counts = []

            for zone in bull_zones:
                if (
                    zone.features
                    and 'metadata' in zone.features
                    and 'swing_metrics' in zone.features['metadata']
                ):
                    zones_with_metrics += 1
                    swing_metrics = zone.features['metadata']['swing_metrics']

                    num_swings = swing_metrics.get('num_swings', 0)
                    num_swings_values.append(num_swings)
                    rally_counts.append(swing_metrics.get('rally_count', 0))
                    drop_counts.append(swing_metrics.get('drop_count', 0))

                    if num_swings > 0:
                        zones_with_swings += 1

                    if (
                        swing_metrics.get('rally_count', 0) > 0
                        and swing_metrics.get('drop_count', 0) > 0
                    ):
                        rallies.append(swing_metrics['avg_rally_pct'])
                        drawdowns.append(abs(swing_metrics['avg_drop_pct']))

            if total_bull > 0:
                pct_with_metrics = (zones_with_metrics / total_bull) * 100
                pct_with_swings = (zones_with_swings / total_bull) * 100
            else:
                pct_with_metrics = 0.0
                pct_with_swings = 0.0

            nb.log(
                f"Всего бычьих зон: {total_bull}. Из них с рассчитанными свинг-метриками: {zones_with_metrics} "
                f"({pct_with_metrics:.1f}%). Доля зон с >=1 свингом: {pct_with_swings:.1f}%."
            )

            if num_swings_values:
                nb.log(
                    "Статистика по num_swings: "
                    f"Min={min(num_swings_values)}, Max={max(num_swings_values)}, Avg={np.mean(num_swings_values):.2f}"
                )
                nb.log(
                    "Средние показатели по релевантным зонам: "
                    f"avg rally_count={np.mean(rally_counts):.2f}, avg drop_count={np.mean(drop_counts):.2f}"
                )

            nb.log(
                f"Собрано {len(rallies)} парных наблюдений (ап-свинг/даун-свинг) из бычьих зон."
            )

            nb.info("2.3. Проведение статистического теста")

            run_summary = {
                'zones_total': total_bull,
                'zones_with_metrics': zones_with_metrics,
                'zones_with_swings': zones_with_swings,
                'pct_with_swings': pct_with_swings,
                'pairs_collected': len(rallies),
            }

            insufficient_data = len(rallies) < 10
            if insufficient_data:
                nb.warning("Недостаточно данных для проведения статистического теста (менее 10 наблюдений).")
                final_results[config['name']][strategy] = {
                    'p_value': None,
                    'statistic': None,
                    'summary': run_summary,
                    'insufficient_data': True,
                }
            else:
                try:
                    statistic, p_value = wilcoxon(rallies, drawdowns, alternative='greater')

                    nb.log("Используется тест Уилкоксона для парных выборок.")
                    nb.log(f"  - Статистика теста: {statistic:.4f}")
                    nb.log(f"  - P-value: {p_value:.4f}")

                    final_results[config['name']][strategy] = {
                        'p_value': p_value,
                        'statistic': statistic,
                        'summary': run_summary,
                    }

                except Exception as e:
                    nb.error(f"Ошибка при проведении теста: {e}")
                    final_results[config['name']][strategy] = {
                        'p_value': None,
                        'statistic': None,
                        'error': str(e),
                        'summary': run_summary,
                    }

            result_record = final_results[config['name']][strategy]
            report_data['analysis'].setdefault(config['name'], {})[strategy] = {
                'summary': run_summary,
                'p_value': result_record.get('p_value'),
                'statistic': result_record.get('statistic'),
                'error': result_record.get('error'),
                'insufficient_data': result_record.get('insufficient_data', False),
            }

            if insufficient_data:
                nb.wait()
                continue

    nb.wait()


nb.step("Шаг 3: Сводные данные")

nb.section_header("Результаты по конфигурациям и стратегиям")

for config in analysis_configs:
    nb.log(f"Конфигурация: {config['label']}")
    for strategy in swing_strategies:
        result = final_results[config['name']].get(strategy)
        if not result:
            nb.log(f"  - Стратегия '{strategy}': данных нет")
            continue

        summary = result['summary']
        nb.log(
            f"  - Стратегия '{strategy}': zones_with_swings={summary['zones_with_swings']}/"
            f"{summary['zones_total']} ({summary['pct_with_swings']:.1f}%), pairs={summary['pairs_collected']}"
        )
        if result['p_value'] is not None:
            nb.log(f"    statistic={result['statistic']:.4f}, p_value={result['p_value']:.4f}")
        if result.get('error'):
            nb.log(f"    error={result['error']}")
    nb.log("")

nb.info("Сохранение агрегированных данных")

from pathlib import Path
import json

output_path = Path("outputs/reports")
output_path.mkdir(parents=True, exist_ok=True)
report_file = output_path / "macd_zone_consistency_results.json"

with report_file.open("w", encoding="utf-8") as f:
    json.dump(report_data, f, ensure_ascii=False, indent=2)

nb.success(f"Агрегированные данные сохранены в {report_file}")

nb.info("Исследование завершено.")
nb.finish()
