#!/usr/bin/env python3
"""
BQuant - Zone Visualization Demo

Демонстрирует все возможности визуализации зон в BQuant:
1. Обзорная визуализация (overview) - все зоны на графике цены
2. Детальная визуализация (detail) - фокус на отдельной зоне с контекстом
3. Сравнительная визуализация (comparison) - сравнение нескольких зон
4. Статистическая визуализация (statistics) - анализ характеристик зон

Возможности:
- Автоматическое определение индикаторов из контекста зоны
- Гибкая настройка контекста (количество баров до/после зоны)
- Поддержка разных backends (Plotly/Matplotlib)
- Фильтрация зон по датам
- Интерактивные графики с Plotly

Требования:
- BQuant: pip install -e .
- Plotly (опционально): pip install plotly
- Matplotlib (опционально): pip install matplotlib
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
os.environ.setdefault("PANDAS_TA_SUPPRESS_ERRORS", "1")
os.environ.setdefault("PANDAS_TA_LOG_LEVEL", "ERROR")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.core.logging_config import setup_logging
from bquant.visualization import (
    ZoneVisualizer,
    plot_zone_detail,
    plot_zones_comparison,
    check_visualization_dependencies,
    get_available_libraries,
)

# Директория для сохранения графиков
OUTPUT_DIR = Path("output/visualization")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def print_separator(title):
    """Печать разделителя."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def save_figure(fig, filename, backend='plotly'):
    """
    Сохранить график как PNG изображение.
    
    Args:
        fig: Объект графика (Plotly или Matplotlib)
        filename: Имя файла (без расширения)
        backend: Используемый backend
    """
    filepath = OUTPUT_DIR / f"{filename}.png"
    
    try:
        if backend == 'plotly':
            # Plotly требует kaleido для экспорта в PNG
            try:
                fig.write_image(str(filepath), width=1400, height=900)
                print(f"  [SAVED] {filepath}")
                return True
            except Exception as e:
                # Если kaleido недоступен, сохраняем как HTML
                html_path = OUTPUT_DIR / f"{filename}.html"
                fig.write_html(str(html_path))
                print(f"  [SAVED] {html_path} (PNG требует: pip install kaleido)")
                return True
        else:
            # Matplotlib
            fig.savefig(str(filepath), dpi=150, bbox_inches='tight')
            print(f"  [SAVED] {filepath}")
            return True
    except Exception as e:
        print(f"  [ERROR] Не удалось сохранить график: {e}")
        return False


def check_dependencies():
    """Проверка зависимостей визуализации."""
    print_separator("Проверка зависимостей визуализации")
    
    available_libs = get_available_libraries()
    print("\nДоступные библиотеки:")
    for lib, available in available_libs.items():
        status = "[OK]" if available else "[X]"
        print(f"  {status} {lib}")
    
    if not check_visualization_dependencies():
        print("\n[!] ВНИМАНИЕ: Некоторые библиотеки визуализации недоступны!")
        print("    Установите зависимости: pip install plotly matplotlib")
        return False
    
    print("\n[OK] Все зависимости доступны")
    return True


def demo_zone_analysis(df):
    """Создание анализа зон для демонстрации."""
    print_separator("Анализ зон MACD")
    
    # Используем универсальный pipeline для анализа зон MACD
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='find_peaks', shape='statistical')
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    
    print(f"\n[OK] Обнаружено зон: {len(result.zones)}")
    print(f"  - Bull зоны: {sum(1 for z in result.zones if z.type == 'bull')}")
    print(f"  - Bear зоны: {sum(1 for z in result.zones if z.type == 'bear')}")
    
    # Выводим информацию о первых зонах
    if result.zones:
        print("\nПримеры зон:")
        for i, zone in enumerate(result.zones[:3]):
            # Форматируем время если это datetime, иначе просто показываем индекс
            start_str = zone.start_time.strftime('%Y-%m-%d') if hasattr(zone.start_time, 'strftime') else f"idx={zone.start_idx}"
            end_str = zone.end_time.strftime('%Y-%m-%d') if hasattr(zone.end_time, 'strftime') else f"idx={zone.end_idx}"
            
            print(f"  Zone {zone.zone_id}: {zone.type}, "
                  f"duration={zone.duration} bars, "
                  f"from {start_str} to {end_str}")
            
            # Показываем контекст индикатора
            if zone.indicator_context:
                print(f"    Indicator context: {zone.indicator_context}")
    
    return result


def demo_overview_visualization(result, backend='plotly'):
    """Демонстрация обзорной визуализации."""
    print_separator(f"1. Обзорная визуализация (Overview) - Backend: {backend}")
    
    print("\nОбзорная визуализация показывает все зоны на графике цены:")
    print("  - Цветовая маркировка типов зон (bull/bear)")
    print("  - Общий вид распределения зон во времени")
    print("  - Полезно для первичного анализа")
    
    try:
        fig = result.visualize(
            mode='overview',
            title=f'MACD Zones Overview ({backend.title()})',
            backend=backend
        )
        
        print(f"\n[OK] График создан с использованием {backend}")
        print("  Вызов: result.visualize('overview')")
        
        # Сохраняем график
        save_figure(fig, f"01_overview_{backend}", backend)
        
        return fig
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        return None


def demo_detail_visualization(result, zone_id=None, backend='plotly'):
    """Демонстрация детальной визуализации отдельной зоны."""
    print_separator(f"2. Детальная визуализация (Detail) - Backend: {backend}")
    
    if not result.zones:
        print("\n[ERROR] Нет зон для визуализации")
        return None
    
    # Выбираем зону для детального анализа
    if zone_id is None:
        # Берем первую достаточно длинную зону
        target_zone = None
        for zone in result.zones:
            if zone.duration >= 5:
                target_zone = zone
                break
        if target_zone is None:
            target_zone = result.zones[0]
    else:
        target_zone = next((z for z in result.zones if z.zone_id == zone_id), None)
        if target_zone is None:
            print(f"\n✗ Зона с ID={zone_id} не найдена")
            return None
    
    print(f"\nДетальная визуализация зоны #{target_zone.zone_id}:")
    print(f"  - Тип: {target_zone.type}")
    print(f"  - Длительность: {target_zone.duration} баров")
    # Форматируем время если это datetime
    start_str = target_zone.start_time.strftime('%Y-%m-%d') if hasattr(target_zone.start_time, 'strftime') else f"idx={target_zone.start_idx}"
    end_str = target_zone.end_time.strftime('%Y-%m-%d') if hasattr(target_zone.end_time, 'strftime') else f"idx={target_zone.end_idx}"
    print(f"  - Период: {start_str} - {end_str}")
    
    if target_zone.features:
        print(f"  - Характеристики: {list(target_zone.features.keys())[:5]}...")
    
    print("\nОсобенности детальной визуализации:")
    print("  - Автоматическое определение индикаторов из контекста зоны")
    print("  - Настраиваемый контекст (бары до/после зоны)")
    print("  - Отображение статистики зоны на графике")
    print("  - Поддержка панели объемов")
    
    try:
        # Вариант 1: Через result.visualize()
        fig1 = result.visualize(
            mode='detail',
            zone_id=target_zone.zone_id,
            context_bars=20,  # Показать 20 баров до/после зоны
            title=f'Zone {target_zone.zone_id} Detail ({backend.title()})',
            backend=backend
        )
        
        print(f"\n[OK] График создан через result.visualize()")
        print(f"  Вызов: result.visualize('detail', zone_id={target_zone.zone_id}, context_bars=20)")
        save_figure(fig1, f"02_detail_result_{backend}", backend)
        
        # Вариант 2: Напрямую через ZoneVisualizer
        visualizer = ZoneVisualizer(backend=backend)
        fig2 = visualizer.plot_zone_detail(
            result.data,
            target_zone,
            context_bars=30,  # Больше контекста
            title=f'Zone {target_zone.zone_id} Detail - Extended Context'
        )
        
        print(f"\n[OK] График создан через ZoneVisualizer.plot_zone_detail()")
        print(f"  Вызов: visualizer.plot_zone_detail(data, zone, context_bars=30)")
        save_figure(fig2, f"02_detail_visualizer_{backend}", backend)
        
        # Вариант 3: Через convenience функцию
        fig3 = plot_zone_detail(
            result.data,
            target_zone,
            context_bars=15,
            title=f'Zone {target_zone.zone_id} Detail - Convenience Function',
            backend=backend
        )
        
        print(f"\n[OK] График создан через convenience функцию plot_zone_detail()")
        print(f"  Вызов: plot_zone_detail(data, zone, context_bars=15)")
        save_figure(fig3, f"02_detail_convenience_{backend}", backend)
        
        return fig1
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_comparison_visualization(result, backend='plotly'):
    """Демонстрация сравнительной визуализации нескольких зон."""
    print_separator(f"3. Сравнительная визуализация (Comparison) - Backend: {backend}")
    
    if len(result.zones) < 2:
        print("\n✗ Недостаточно зон для сравнения (нужно минимум 2)")
        return None
    
    print("\nСравнительная визуализация позволяет:")
    print("  - Сравнить несколько зон на одном графике")
    print("  - Увидеть различия в поведении индикаторов")
    print("  - Фильтровать зоны по диапазону дат")
    print("  - Ограничить количество отображаемых зон")
    
    # Вариант 1: Все зоны (с ограничением)
    try:
        fig1 = result.visualize(
            mode='comparison',
            max_zones=5,  # Ограничиваем до 5 зон
            title=f'Zones Comparison - Top 5 ({backend.title()})',
            backend=backend
        )
        
        print(f"\n[OK] График создан: сравнение первых 5 зон")
        print(f"  Вызов: result.visualize('comparison', max_zones=5)")
        save_figure(fig1, f"03_comparison_top5_{backend}", backend)
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        fig1 = None
    
    # Вариант 2: Зоны в определенном диапазоне дат
    if result.zones:
        # Берем средний период данных
        all_dates = [z.start_time for z in result.zones]
        mid_point = len(all_dates) // 2
        start_date = all_dates[max(0, mid_point - 2)]
        end_date = all_dates[min(len(all_dates) - 1, mid_point + 2)]
        
        try:
            fig2 = result.visualize(
                mode='comparison',
                date_range=(start_date, end_date),
                max_zones=3,
                title=f'Zones Comparison - Date Range ({backend.title()})',
                backend=backend
            )
            
            print(f"\n[OK] График создан: зоны в диапазоне дат")
            print(f"  Диапазон: {start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date} - {end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date}")
            print(f"  Вызов: result.visualize('comparison', date_range=(start, end), max_zones=3)")
            save_figure(fig2, f"03_comparison_daterange_{backend}", backend)
            
        except Exception as e:
            print(f"\n[ERROR] Ошибка создания графика: {e}")
            fig2 = None
    
    # Вариант 3: Напрямую через visualizer
    try:
        visualizer = ZoneVisualizer(backend=backend)
        fig3 = visualizer.plot_zones_comparison(
            result.data,
            result.zones,
            max_zones=4,
            title=f'Zones Comparison - Direct Call ({backend.title()})'
        )
        
        print(f"\n[OK] График создан через ZoneVisualizer.plot_zones_comparison()")
        print(f"  Вызов: visualizer.plot_zones_comparison(data, zones, max_zones=4)")
        save_figure(fig3, f"03_comparison_visualizer_{backend}", backend)
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        fig3 = None
    
    # Вариант 4: Через convenience функцию
    try:
        fig4 = plot_zones_comparison(
            result.data,
            result.zones,
            max_zones=3,
            title=f'Zones Comparison - Convenience Function ({backend.title()})',
            backend=backend
        )
        
        print(f"\n[OK] График создан через convenience функцию plot_zones_comparison()")
        print(f"  Вызов: plot_zones_comparison(data, zones, max_zones=3)")
        save_figure(fig4, f"03_comparison_convenience_{backend}", backend)
        
        return fig4
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        return None


def demo_statistics_visualization(result, backend='plotly'):
    """Демонстрация статистической визуализации."""
    print_separator(f"4. Статистическая визуализация (Statistics) - Backend: {backend}")
    
    if not result.statistics:
        print("\n✗ Статистика недоступна")
        return None
    
    print("\nСтатистическая визуализация включает:")
    print("  - Распределение зон по типам (pie chart)")
    print("  - Распределение длительности зон (histogram)")
    print("  - Распределение доходности (histogram)")
    print("  - Временная динамика зон (scatter)")
    
    try:
        fig = result.visualize(
            mode='statistics',
            title=f'Zones Statistics ({backend.title()})',
            backend=backend
        )
        
        print(f"\n[OK] График создан с использованием {backend}")
        print(f"  Вызов: result.visualize('statistics')")
        
        # Показываем основную статистику
        print("\nОсновная статистика зон:")
        for key, value in result.statistics.items():
            if isinstance(value, (int, float)):
                print(f"  - {key}: {value:.2f}")
        
        save_figure(fig, f"04_statistics_{backend}", backend)
        
        return fig
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        return None


def demo_custom_configuration(result):
    """Демонстрация кастомной конфигурации визуализации."""
    print_separator("5. Кастомная конфигурация визуализации")
    
    print("\nВозможности настройки:")
    print("  - Размер графиков (width, height)")
    print("  - Показ/скрытие элементов (labels, stats)")
    print("  - Настройка цветовых палитр")
    print("  - Выбор backend (plotly/matplotlib)")
    
    if not result.zones:
        print("\n[ERROR] Нет зон для визуализации")
        return None
    
    try:
        # Создаем visualizer с кастомными параметрами
        visualizer = ZoneVisualizer(
            backend='plotly',
            width=1400,  # Широкий график
            height=900,  # Высокий график
            show_zone_labels=True,
            show_zone_stats=True,
            opacity=0.4,  # Более прозрачные зоны
            zone_detail_context=25,  # Больше контекста для detail
        )
        
        # Детальный график с кастомными параметрами
        target_zone = result.zones[0]
        fig = visualizer.plot_zone_detail(
            result.data,
            target_zone,
            context_bars=25,
            title='Custom Configured Zone Detail'
        )
        
        print("\n✓ График создан с кастомной конфигурацией:")
        print("  - Размер: 1400x900")
        print("  - Прозрачность зон: 40%")
        print("  - Контекст: 25 баров")
        print("  - Показ labels и статистики")
        
        print("\nКод:")
        print("  visualizer = ZoneVisualizer(")
        print("      backend='plotly',")
        print("      width=1400, height=900,")
        print("      show_zone_labels=True,")
        print("      opacity=0.4")
        print("  )")
        print("  fig = visualizer.plot_zone_detail(data, zone, context_bars=25)")
        
        save_figure(fig, "05_custom_configuration", 'plotly')
        
        return fig
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания графика: {e}")
        return None


def demo_backend_comparison(result):
    """Демонстрация сравнения разных backends."""
    print_separator("6. Сравнение backends (Plotly vs Matplotlib)")
    
    if not result.zones:
        print("\n✗ Нет зон для визуализации")
        return
    
    available_libs = get_available_libraries()
    
    print("\nДоступные backends:")
    if available_libs.get('plotly'):
        print("  [OK] Plotly - интерактивные графики (рекомендуется)")
    else:
        print("  [X] Plotly - недоступен")
    
    if available_libs.get('matplotlib'):
        print("  [OK] Matplotlib - статические графики")
    else:
        print("  [X] Matplotlib - недоступен")
    
    target_zone = result.zones[0]
    
    # Plotly
    if available_libs.get('plotly'):
        try:
            print("\nСоздание графика с Plotly...")
            fig_plotly = plot_zone_detail(
                result.data,
                target_zone,
                context_bars=15,
                title='Zone Detail - Plotly Backend',
                backend='plotly'
            )
            print("  [OK] Plotly график создан")
            print("  - Интерактивный (zoom, pan, hover)")
            print("  - Красивый дизайн")
            print("  - Экспорт в HTML/PNG")
        except Exception as e:
            print(f"  [ERROR] Ошибка Plotly: {e}")
    
    # Matplotlib
    if available_libs.get('matplotlib'):
        try:
            print("\nСоздание графика с Matplotlib...")
            fig_mpl = plot_zone_detail(
                result.data,
                target_zone,
                context_bars=15,
                title='Zone Detail - Matplotlib Backend',
                backend='matplotlib'
            )
            print("  [OK] Matplotlib график создан")
            print("  - Статический")
            print("  - Легковесный")
            print("  - Экспорт в PNG/PDF/SVG")
            
            # Закрываем matplotlib фигуру чтобы не показывать
            import matplotlib.pyplot as plt
            plt.close(fig_mpl)
        except Exception as e:
            print(f"  [ERROR] Ошибка Matplotlib: {e}")


def main():
    """Основная функция демонстрации."""
    print_separator("BQuant - Zone Visualization Demo")
    
    # Setup logging
    setup_logging("INFO")
    
    # Проверка зависимостей
    if not check_dependencies():
        print("\n[!] Продолжаем с ограниченной функциональностью...")
    
    # Загрузка данных
    print_separator("Загрузка данных")
    df = get_sample_data("mt_xauusd_m15")
    # Используем последние 500 баров для демо
    if len(df) > 500:
        df = df.iloc[-500:].copy()
        # Сброс индекса для правильного start_idx/end_idx в зонах
        df = df.reset_index(drop=True)
    print(f"[OK] Загружено {len(df)} баров данных")
    
    # Показываем дату если есть datetime index
    if hasattr(df.index, 'min'):
        try:
            print(f"  Период: {df.index.min()} - {df.index.max()}")
        except:
            print(f"  Индексов: {len(df)}")
    
    # Анализ зон
    result = demo_zone_analysis(df)
    
    if not result or not result.zones:
        print("\n[ERROR] Не удалось создать зоны для демонстрации")
        return
    
    # Определяем доступный backend
    available_libs = get_available_libraries()
    backend = 'plotly' if available_libs.get('plotly') else 'matplotlib'
    
    # Демонстрация различных типов визуализации
    demo_overview_visualization(result, backend=backend)
    demo_detail_visualization(result, backend=backend)
    demo_comparison_visualization(result, backend=backend)
    demo_statistics_visualization(result, backend=backend)
    demo_custom_configuration(result)
    demo_backend_comparison(result)
    
    # Итоги
    print_separator("Итоги демонстрации")
    
    print("\n[OK] Демонстрация завершена!")
    
    # Подсчет сохраненных файлов
    saved_files = list(OUTPUT_DIR.glob("*.png")) + list(OUTPUT_DIR.glob("*.html"))
    print(f"\n[SAVED] Создано графиков: {len(saved_files)}")
    print(f"  Директория: {OUTPUT_DIR.absolute()}")
    print("\nСохраненные файлы:")
    for filepath in sorted(saved_files):
        print(f"  - {filepath.name}")
    
    print("\nОсновные возможности визуализации зон:")
    print("  1. result.visualize('overview') - обзор всех зон")
    print("  2. result.visualize('detail', zone_id=X) - детальный анализ зоны")
    print("  3. result.visualize('comparison', max_zones=N) - сравнение зон")
    print("  4. result.visualize('statistics') - статистические графики")
    
    print("\nТри способа вызова:")
    print("  A. result.visualize() - через ZoneAnalysisResult (рекомендуется)")
    print("  B. ZoneVisualizer().plot_*() - через класс визуализатора")
    print("  C. plot_zone_*() - через convenience функции")
    
    print("\nДополнительные возможности:")
    print("  - Автоматическое определение индикаторов из контекста")
    print("  - Настройка контекста (context_bars)")
    print("  - Фильтрация по датам (date_range)")
    print("  - Кастомизация внешнего вида")
    print("  - Выбор backend (plotly/matplotlib)")
    
    print("\n[DOCS] Дополнительная информация:")
    print("  - docs/user_guide/zone_analysis.md - руководство пользователя")
    print("  - docs/api/visualization.md - API reference")
    print("  - examples/02_macd_zone_analysis.py - базовый пример анализа")
    print("  - examples/02a_universal_zones.py - универсальный API")
    
    print("\n[TIP] Для отображения графиков:")
    print("  - Plotly: fig.show() или fig.write_html('output.html')")
    print("  - Matplotlib: plt.show() или plt.savefig('output.png')")


if __name__ == "__main__":
    main()

