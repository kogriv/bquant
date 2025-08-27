"""
BQuant CLI Module

Простой CLI интерфейс для основных функций BQuant.
Работает "из коробки" без внешних зависимостей.
"""

import argparse
import sys
from typing import Optional

from .core.logging_config import get_logger
from .data.samples import get_sample_data, list_datasets, print_sample_data_status
from .indicators import MACD
from .visualization import charts

logger = get_logger(__name__)


def analyze_macd(dataset_name: str = 'tv_xauusd_1h', output_file: Optional[str] = None, quiet: bool = False):
    """
    Простой анализ MACD для sample данных.
    
    Args:
        dataset_name: Название датасета для анализа
        output_file: Путь для сохранения графика (опционально)
        quiet: Минимальный вывод (без подробной информации)
    """
    try:
        if not quiet:
            print(f"🔍 Анализ MACD для датасета: {dataset_name}")
        
        # Загружаем данные
        if not quiet:
            print("📊 Загрузка данных...")
        data = get_sample_data(dataset_name)
        if not quiet:
            print(f"   Загружено {len(data)} записей")
        
        # Рассчитываем MACD
        if not quiet:
            print("📈 Расчет MACD...")
        macd = MACD()
        result = macd.calculate(data)
        if not quiet:
            print("   MACD рассчитан успешно")
        
        # Создаем график
        if not quiet:
            print("📊 Создание графика...")
        try:
            # Создаем простой график цен с MACD
            fig = charts.create_price_chart(data, chart_type='line', title=f"Price Chart - {dataset_name}")
            
            if fig is None:
                if not quiet:
                    print("   ⚠️ Не удалось создать график")
                return
            
            # Определяем имя файла для сохранения
            if output_file:
                html_file = output_file
            else:
                # Генерируем имя файла по умолчанию в results/charts
                from datetime import datetime
                import os
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                charts_dir = "results/charts"
                os.makedirs(charts_dir, exist_ok=True)
                html_file = os.path.join(charts_dir, f"chart_{dataset_name}_{timestamp}.html")
            
            # Сохраняем график в HTML
            fig.write_html(html_file)
            if not quiet:
                print(f"   График сохранен в: {html_file}")
            else:
                print(f"График: {html_file}")
                
        except Exception as e:
            if not quiet:
                print(f"   ⚠️ Не удалось создать график: {e}")
            else:
                print(f"Ошибка создания графика: {e}")
            
        if not quiet:
            print("✅ Анализ завершен успешно!")
        
    except Exception as e:
        if not quiet:
            print(f"❌ Ошибка при анализе: {e}")
        else:
            print(f"Ошибка: {e}")
        logger.error(f"MACD analysis failed: {e}")
        sys.exit(1)


def list_available_data():
    """Показать список доступных sample данных."""
    try:
        print("📋 Доступные sample данные:")
        print("=" * 50)
        
        datasets = list_datasets()
        for i, dataset in enumerate(datasets, 1):
            print(f"{i}. {dataset['title']} ({dataset['name']})")
            print(f"   Символ: {dataset['symbol']} | Таймфрейм: {dataset['timeframe']}")
            print(f"   Записей: {dataset['rows']:,} | Размер: {dataset['size_kb']} KB")
            print()
            
        print(f"Всего доступно датасетов: {len(datasets)}")
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка данных: {e}")
        logger.error(f"Failed to list datasets: {e}")
        sys.exit(1)


def show_data_status():
    """Показать статус всех sample данных."""
    try:
        print_sample_data_status()
    except Exception as e:
        print(f"❌ Ошибка при получении статуса: {e}")
        logger.error(f"Failed to show data status: {e}")
        sys.exit(1)


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description="BQuant - Quantitative Research Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  bquant analyze                    # Анализ MACD с данными по умолчанию
  bquant analyze mt_xauusd_m15     # Анализ MACD с конкретным датасетом
  bquant analyze --output chart.html  # Сохранение графика в файл
  bquant analyze --quiet           # Минимальный вывод
  bquant analyze -q -o chart.html  # Тихий режим с сохранением в файл
  bquant list                      # Список доступных данных
  bquant status                    # Статус всех данных
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда analyze
    analyze_parser = subparsers.add_parser('analyze', help='Анализ MACD')
    analyze_parser.add_argument(
        'dataset', 
        nargs='?', 
        default='tv_xauusd_1h',
        help='Название датасета (по умолчанию: tv_xauusd_1h)'
    )
    analyze_parser.add_argument(
        '--output', '-o',
        help='Путь для сохранения графика (HTML файл)'
    )
    analyze_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Минимальный вывод (без подробной информации)'
    )
    
    # Команда list
    subparsers.add_parser('list', help='Список доступных данных')
    
    # Команда status
    subparsers.add_parser('status', help='Статус всех данных')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'analyze':
            analyze_macd(args.dataset, args.output, args.quiet)
        elif args.command == 'list':
            list_available_data()
        elif args.command == 'status':
            show_data_status()
        else:
            print(f"❌ Неизвестная команда: {args.command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Операция прервана пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        logger.error(f"Unexpected error in CLI: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
