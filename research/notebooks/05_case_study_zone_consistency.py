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
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='find_peaks')
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
    bull_zones_with_swings = 0
    bull_zones_total = 0
    for zone in eda_result.zones:
        if zone.type == 'bull':
            bull_zones_total += 1
            if zone.features and 'metadata' in zone.features and 'swing_metrics' in zone.features['metadata']:
                num_swings = zone.features['metadata']['swing_metrics'].get('num_swings', 0)
                num_swings_list.append(num_swings)
                if num_swings > 0:
                    bull_zones_with_swings += 1
    
    if bull_zones_total > 0:
        zones_with_zero_swings = bull_zones_total - bull_zones_with_swings
        pct_zero_swings = (zones_with_zero_swings / bull_zones_total) * 100
        nb.log(f"Всего найдено бычьих зон: {bull_zones_total}")
        nb.log(f"Из них зон с внутренними свингами: {bull_zones_with_swings}")
        nb.log(f"Зон без внутренних свингов (num_swings = 0): {zones_with_zero_swings} ({pct_zero_swings:.1f}%)")
        
        if len(num_swings_list) > 0:
            nb.log(f"Статистика по количеству свингов: Min={min(num_swings_list)}, Max={max(num_swings_list)}, Avg={np.mean(num_swings_list):.2f}")
    else:
        nb.warning("В данных не найдено бычьих зон.")

    nb.info("2.4. Вывод и принятие решения")
    nb.log("EDA показал, что значительная часть (~{pct_zero_swings:.1f}%) бычьих зон являются 'простыми' или 'монотонными', то есть не содержат внутренних колебаний, которые можно было бы классифицировать как свинги.")
    nb.log("Поскольку наша гипотеза касается именно сравнения ВНУТРЕННИХ ап- и даун-свингов, эти 'простые' зоны нерелевантны для основного теста.")
    nb.success("РЕШЕНИЕ: В основном исследовании мы будем анализировать только те зоны, в которых стратегия анализа нашла как минимум один ап-свинг и один даун-свинг.")

nb.wait()


# --- Main Analysis Loop ---
swing_strategies = ['find_peaks', 'pivot_points', 'zigzag']
final_results = {}

for strategy in swing_strategies:
    nb.step(f"Шаг 2: Анализ с использованием стратегии '{strategy}'")

    with nb.error_handling(f"Analysis with {strategy}"):
        nb.info(f"2.1. Поиск зон и извлечение свингов с помощью '{strategy}'")

        # Run the zone analysis pipeline with the current swing strategy
        analysis_result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing=strategy)
            .analyze(clustering=False) # Clustering not needed for this analysis
            .build()
        )

        nb.success(f"Анализ завершен. Найдено {len(analysis_result.zones)} зон.")

        nb.info("2.2. Сбор данных для статистического теста")
        
        rallies = []
        drawdowns = []

        # We are interested in bull zones only
        bull_zones = [zone for zone in analysis_result.zones if zone.type == 'bull']

        for zone in bull_zones:
            # NEW LOGIC: Use the nested swing_metrics and check for valid swings
            if (zone.features 
                and 'metadata' in zone.features 
                and 'swing_metrics' in zone.features['metadata']):
                
                swing_metrics = zone.features['metadata']['swing_metrics']
                
                # We need zones that have at least one rally and one drop to make a meaningful comparison
                if swing_metrics.get('rally_count', 0) > 0 and swing_metrics.get('drop_count', 0) > 0:
                    # We compare the average percentage change of rallies vs. drops
                    # We use abs() for drawdowns because the value is negative, but for comparison of magnitude we need a positive number
                    rallies.append(swing_metrics['avg_rally_pct'])
                    drawdowns.append(abs(swing_metrics['avg_drop_pct']))
        
        nb.log(f"Собрано {len(rallies)} парных наблюдений (ап-свинг/даун-свинг) из бычьих зон.")

        nb.info("2.3. Проведение статистического теста")

        if len(rallies) < 10:
            nb.warning("Недостаточно данных для проведения надежного статистического теста (менее 10 наблюдений).")
            final_results[strategy] = {'p_value': None, 'statistic': None, 'conclusion': 'Insufficient data'}
            continue

        # We use the Wilcoxon signed-rank test because it's suitable for paired, non-normally distributed data.
        # H1: rallies > drawdowns
        try:
            statistic, p_value = wilcoxon(rallies, drawdowns, alternative='greater')
            
            nb.log("Используется тест Уилкоксона для парных выборок.")
            nb.log(f"  - Статистика теста: {statistic:.4f}")
            nb.log(f"  - P-value: {p_value:.4f}")

            nb.info("2.4. Интерпретация результата")
            alpha = 0.05
            if p_value < alpha:
                conclusion = f"ПОДТВЕРЖДЕНА. P-value < {alpha}, отвергаем нулевую гипотезу. Ап-свинги значимо больше даун-свингов."
                nb.success(conclusion)
            else:
                conclusion = f"НЕ ПОДТВЕРЖДЕНА. P-value >= {alpha}, не можем отвергнуть нулевую гипотезу."
                nb.warning(conclusion)
            
            final_results[strategy] = {'p_value': p_value, 'statistic': statistic, 'conclusion': conclusion}

        except Exception as e:
            nb.error(f"Ошибка при проведении теста: {e}")
            final_results[strategy] = {'p_value': None, 'statistic': None, 'conclusion': f'Test Error: {e}'}

    nb.wait()


nb.step("Шаг 3: Итоговые выводы")

nb.section_header("Сравнение результатов по всем свинг-стратегиям")

for strategy, result in final_results.items():
    nb.log(f"Стратегия: '{strategy}'")
    if result['p_value'] is not None:
        nb.log(f"  - P-value: {result['p_value']:.4f}")
        nb.log(f"  - Вывод: {result['conclusion']}")
    else:
        nb.log(f"  - Вывод: {result['conclusion']}")
    nb.log("")

nb.section_header("Общий вывод исследования")

# Determine overall consensus
confirmed_strategies = [s for s, r in final_results.items() if r['p_value'] is not None and r['p_value'] < 0.05]

if len(confirmed_strategies) == len(swing_strategies):
    nb.success("Все три свинг-стратегии подтвердили основную гипотезу.")
    nb.log("Вывод: Гипотеза о 'состоятельности' бычьих зон MACD на данном наборе данных является надежной. Внутренние восходящие движения действительно структурно преобладают над нисходящими.")
elif len(confirmed_strategies) > 0:
    nb.warning(f"Гипотеза была подтверждена только для следующих стратегий: {', '.join(confirmed_strategies)}.")
    nb.log("Вывод: 'Состоятельность' бычьих зон подтверждается, но результат чувствителен к выбору алгоритма анализа свингов. Стратегии, подтвердившие гипотезу, могут быть более предпочтительными для разработки торговых систем.")
else:
    nb.error("Ни одна из свинг-стратегий не смогла статистически подтвердить гипотезу.")
    nb.log("Вывод: На данном наборе данных мы не нашли статистически значимых доказательств 'состоятельности' бычьих зон MACD с точки зрения доминирования внутренних ап-свингов.")

nb.info("Исследование завершено.")
nb.finish()
