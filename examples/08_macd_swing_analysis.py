#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BQuant Example: MACD Swing Analysis (Правильный подход)

Демонстрирует ПРАВИЛЬНОЕ использование встроенного функционала пакета:
1. SwingMetrics (23 поля) - автоматический расчет пакетом
2. ZigZag из pandas_ta - интеграция через LibraryManager
3. Анализ колебаний ВНУТРИ зон (не просто "от начала до конца")

КЛЮЧЕВОЕ ОТКРЫТИЕ:
Swing metrics сохраняются в zone.features['metadata']['swing_metrics']!

Этот скрипт НЕ хардкодит анализ - использует ТОЛЬКО встроенные средства пакета.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones
from bquant.core.logging_config import setup_logging


def analyze_zone_type_swings(swings, zone_type, min_tradable_amplitude=0.05):
    """
    Анализ swing метрик для одного типа зон (bull или bear).

    Args:
        swings: List[dict] - swing metrics для зон одного типа
        zone_type: str - тип зоны ('bull' или 'bear')
        min_tradable_amplitude: float - минимальная амплитуда для торговли (%)

    Returns:
        dict - результаты анализа с вердиктом
    """
    if not swings:
        return {'has_alpha': False, 'reason': 'No swing data'}

    print(f"\n{'='*70}")
    print(f"[{zone_type.upper()} ЗОНЫ] ({len(swings)} шт)")
    print(f"{'='*70}")

    # Агрегируем метрики из ВСТРОЕННЫХ SwingMetrics пакета
    rally_counts = [s['rally_count'] for s in swings]
    drop_counts = [s['drop_count'] for s in swings]

    avg_rally_pcts = [s['avg_rally_pct'] for s in swings if s['avg_rally_pct'] > 0]
    avg_drop_pcts = [s['avg_drop_pct'] for s in swings if s['avg_drop_pct'] > 0]

    max_rally_pcts = [s['max_rally_pct'] for s in swings if s['max_rally_pct'] > 0]
    max_drop_pcts = [s['max_drop_pct'] for s in swings if s['max_drop_pct'] > 0]

    rally_durs = [s['avg_rally_duration_bars'] for s in swings if s['avg_rally_duration_bars'] > 0]
    drop_durs = [s['avg_drop_duration_bars'] for s in swings if s['avg_drop_duration_bars'] > 0]

    rally_speeds = [s['avg_rally_speed_pct_per_bar'] for s in swings if s['avg_rally_speed_pct_per_bar'] > 0]
    drop_speeds = [s['avg_drop_speed_pct_per_bar'] for s in swings if s['avg_drop_speed_pct_per_bar'] > 0]

    # Вывод агрегированных метрик
    print(f"\n   Колебания в зоне:")
    print(f"   - Среднее RALLY в зоне: {np.mean(rally_counts):.1f}")
    print(f"   - Среднее DROPS в зоне: {np.mean(drop_counts):.1f}")

    if avg_rally_pcts:
        print(f"\n   Амплитуды (в %):")
        print(f"   - Средняя RALLY: {np.mean(avg_rally_pcts):.3f}%")
        print(f"   - Средняя DROP:  {np.mean(avg_drop_pcts):.3f}%")
        print(f"   - Макс RALLY:    {np.mean(max_rally_pcts):.3f}%")
        print(f"   - Макс DROP:     {np.mean(max_drop_pcts):.3f}%")

    if rally_durs:
        print(f"\n   Длительности (в барах):")
        print(f"   - Средняя RALLY: {np.mean(rally_durs):.1f}")
        print(f"   - Средняя DROP:  {np.mean(drop_durs):.1f}")

    if rally_speeds:
        print(f"\n   Скорости (% за бар):")
        print(f"   - Средняя RALLY: {np.mean(rally_speeds):.4f}%/bar")
        print(f"   - Средняя DROP:  {np.mean(drop_speeds):.4f}%/bar")

    # ОЦЕНКА АЛЬФЫ (3 критерия)
    print(f"\n   {'='*66}")
    print(f"   ОЦЕНКА: \"Дает ли море\" в {zone_type.upper()} зонах?")
    print(f"   {'='*66}")

    # Критерий 1: Достаточно колебаний?
    has_swings = np.mean(rally_counts) >= 1.5 and np.mean(drop_counts) >= 1.5
    print(f"\n   [1] Достаточно колебаний?")
    print(f"       {'[+]' if has_swings else '[-]'} Rally: {np.mean(rally_counts):.1f}, Drop: {np.mean(drop_counts):.1f}")

    # Критерий 2: Достаточная амплитуда?
    if avg_rally_pcts:
        sufficient_amplitude = (np.mean(avg_rally_pcts) >= min_tradable_amplitude and
                               np.mean(avg_drop_pcts) >= min_tradable_amplitude)
        print(f"\n   [2] Достаточная амплитуда для торговли (>={min_tradable_amplitude}%)?")
        print(f"       {'[+]' if sufficient_amplitude else '[-]'} Rally: {np.mean(avg_rally_pcts):.3f}%, Drop: {np.mean(avg_drop_pcts):.3f}%")
    else:
        sufficient_amplitude = False
        print(f"\n   [2] Достаточная амплитуда?")
        print(f"       [-] Нет данных")

    # Критерий 3: Асимметрия (зависит от типа зоны)
    if avg_rally_pcts and avg_drop_pcts:
        avg_rally = np.mean(avg_rally_pcts)
        avg_drop = np.mean(avg_drop_pcts)

        # Для bull зон: rally > drop
        # Для bear зон: drop > rally
        if zone_type == 'bull':
            has_asymmetry = avg_rally > avg_drop * 1.2
            ratio = avg_rally / avg_drop if avg_drop > 0 else 0
            print(f"\n   [3] Асимметрия (Rally > Drop)?")
        else:  # bear
            has_asymmetry = avg_drop > avg_rally * 1.2
            ratio = avg_drop / avg_rally if avg_rally > 0 else 0
            print(f"\n   [3] Асимметрия (Drop > Rally)?")

        print(f"       {'[+]' if has_asymmetry else '[-]'} Ratio: {ratio:.2f}")
    else:
        has_asymmetry = False
        print(f"\n   [3] Асимметрия?")
        print(f"       [-] Нет данных")

    # ВЕРДИКТ
    print(f"\n   {'='*66}")
    if has_swings and sufficient_amplitude and has_asymmetry:
        verdict = "МОРЕ ДАЕТ! Есть АЛЬФА в свингах!"
        has_alpha = True
    elif has_swings and sufficient_amplitude:
        verdict = "Потенциал есть (колебания + амплитуда), но нет асимметрии"
        has_alpha = False
    else:
        verdict = "Море НЕ дает. Свинги слабые или отсутствуют."
        has_alpha = False

    print(f"   [ВЕРДИКТ] {verdict}")
    print(f"   {'='*66}")

    return {
        'has_alpha': has_alpha,
        'has_swings': has_swings,
        'sufficient_amplitude': sufficient_amplitude,
        'has_asymmetry': has_asymmetry,
        'avg_rally_count': np.mean(rally_counts),
        'avg_drop_count': np.mean(drop_counts),
        'avg_rally_pct': np.mean(avg_rally_pcts) if avg_rally_pcts else 0,
        'avg_drop_pct': np.mean(avg_drop_pcts) if avg_drop_pcts else 0,
    }


def analyze_swing_alpha(result):
    """
    Главная функция анализа альфы в свингах.

    Использует ТОЛЬКО встроенные SwingMetrics из пакета (metadata).
    """
    print(f"\n{'='*70}")
    print(f"  SWING ANALYSIS: Дает ли море?")
    print(f"  (Анализ колебаний ВНУТРИ зон)")
    print(f"{'='*70}")

    if len(result.zones) == 0:
        print("\n[X] Зоны не найдены!")
        return

    # Собираем swing метрики из ПРАВИЛЬНОГО места: metadata!
    bull_swings = []
    bear_swings = []
    no_swing_data = 0

    for zone in result.zones:
        # КЛЮЧЕВОЕ: читаем из metadata (где пакет их сохраняет)
        metadata = zone.features.get('metadata', {})
        swing_metrics = metadata.get('swing_metrics')

        if not swing_metrics:
            no_swing_data += 1
            continue

        if zone.type == 'bull':
            bull_swings.append(swing_metrics)
        elif zone.type == 'bear':
            bear_swings.append(swing_metrics)

    print(f"\n[INFO] Зоны с swing данными: {len(bull_swings + bear_swings)}/{len(result.zones)}")
    if no_swing_data > 0:
        print(f"       Зоны БЕЗ swing данных: {no_swing_data}")

    # Анализ по типам зон (без дублирования кода)
    results = {}

    if bull_swings:
        results['bull'] = analyze_zone_type_swings(bull_swings, 'bull')

    if bear_swings:
        results['bear'] = analyze_zone_type_swings(bear_swings, 'bear')

    return results


def main():
    """
    Главная функция примера.

    Демонстрирует ПРАВИЛЬНОЕ использование встроенного функционала пакета.
    """
    setup_logging(console_level='WARNING', file_level='ERROR', log_to_file=False)

    print("\n" + "="*70)
    print("  MACD SWING ANALYSIS")
    print("  Используем встроенные SwingMetrics из пакета")
    print("="*70)

    # Загрузка данных
    print("\n[1/3] Загрузка sample данных...")
    df = get_sample_data('mt_xauusd_m15')
    print(f"      {len(df)} баров (XAUUSD 15min)\n")

    # Анализ зон с использованием ВСТРОЕННЫХ стратегий пакета
    print("[2/3] Запуск zone analysis pipeline...")
    print("      Используем встроенные стратегии:")
    print("      - swing: 'zigzag' (pandas_ta ZigZag)")
    print("      - shape: 'statistical' (Skewness, Kurtosis)")
    print("      - divergence: 'classic'")
    print("      - volume: 'standard'")

    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=3)
        .with_strategies(
            swing='zigzag',          # pandas_ta ZigZag (автоматически рассчитывает 23 метрики)
            shape='statistical',     # Skewness, Kurtosis
            divergence='classic',    # Classic divergences
            volume='standard',       # Volume analysis
        )
        .analyze(clustering=True, n_clusters=3)
        .build()
    )

    print(f"      Найдено зон: {len(result.zones)}\n")

    # Анализ swing альфы
    print("[3/3] Анализ swing альфы...")
    analyze_results = analyze_swing_alpha(result)

    # Итоговая сводка
    print(f"\n{'='*70}")
    print(f"  ИТОГИ")
    print(f"{'='*70}")

    print(f"\n[ИСПОЛЬЗОВАНО ИЗ ПАКЕТА]")
    print(f"  [+] ZoneDetection: 'zero_crossing' стратегия")
    print(f"  [+] SwingStrategy: 'zigzag' (pandas_ta ZigZag)")
    print(f"  [+] SwingMetrics: 23 поля (автоматический расчет пакетом)")
    print(f"  [+] ShapeStrategy: 'statistical'")
    print(f"  [+] DivergenceStrategy: 'classic'")
    print(f"  [+] VolumeStrategy: 'standard'")
    print(f"  [+] UniversalZoneAnalyzer: полный pipeline")
    print(f"  [+] Clustering: 3 кластера")

    print(f"\n[РЕЗУЛЬТАТЫ]")
    for zone_type, res in analyze_results.items():
        alpha_mark = "[АЛЬФА!]" if res['has_alpha'] else "[нет альфы]"
        print(f"  {zone_type.upper()}: {alpha_mark}")
        print(f"    - Колебаний: rally={res['avg_rally_count']:.1f}, drop={res['avg_drop_count']:.1f}")
        if res['avg_rally_pct'] > 0:
            print(f"    - Амплитуды: rally={res['avg_rally_pct']:.3f}%, drop={res['avg_drop_pct']:.3f}%")

    print(f"\n[РЕКОМЕНДАЦИИ]")
    print(f"  1. Оптимизировать параметры ZigZag (deviation, legs)")
    print(f"  2. Протестировать на большем датасете")
    print(f"  3. Backtesting swing торговли (TODO: добавить в пакет)")

    print(f"\n[ЧТО ОТСУТСТВУЕТ В ПАКЕТЕ - TODO]")
    print(f"  - Backtesting модуль для swing торговли")
    print(f"  - Оптимизатор параметров ZigZag (grid search)")
    print(f"  - Визуализация swing points на графиках")
    print(f"  - ML модуль для предсказания swing амплитуд")
    print(f"  - Фильтр зон по swing качеству")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
