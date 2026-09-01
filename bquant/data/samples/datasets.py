"""
Реестр доступных тестовых датасетов BQuant

Этот модуль содержит метаданные всех доступных sample датасетов
и предоставляет функции для работы с ними.
"""

from typing import Dict, List, Any
from ...core.logging_config import get_logger

logger = get_logger(__name__)

# Реестр доступных датасетов
AVAILABLE_DATASETS = {
    'tv_xauusd_1h': {
        'name': 'TradingView XAUUSD 1H',
        'description': 'Часовые данные XAUUSD с техническими индикаторами',
        'source': 'TradingView via OANDA',
        'symbol': 'XAUUSD',
        'timeframe': '1H',
        'rows': 1000,
        'columns': [
            'time', 'open', 'high', 'low', 'close', 'volume',
            'accumulation_distribution', 'macd', 'signal', 'rsi',
            'rsi_based_ma', 'regular_bullish', 'regular_bullish_label',
            'regular_bearish', 'regular_bearish_label'
        ],
        'period_start': '2025-06-11T20:00:00+07:00',
        'period_end': '2025-08-12T13:00:00+07:00',
        'license': 'Open data, free for research and educational use',
        'disclaimer': 'For demonstration purposes only. Not for production trading.',
        'file_module': 'embedded.tv_xauusd_1h',
        'size_bytes': 555425,
        'updated': '2025-08-25 18:38:50',
        'original_filename': 'OANDA_XAUUSD, 60.csv'
    },
    'mt_xauusd_m15': {
        'name': 'MetaTrader XAUUSD 15M',
        'description': '15-минутные данные XAUUSD с базовыми метриками',
        'source': 'MetaTrader',
        'symbol': 'XAUUSD',
        'timeframe': '15M',
        'rows': 1000,
        'columns': [
            'time', 'open', 'high', 'low', 'close', 'volume', 'spread'
        ],
        # Период получен из самих данных (2026-09-01, G40): в реестре три месяца
        # стояло '2025-05-20T02:00:00' … '2025-05-30T07:30:00' при данных за август.
        # Значения обязаны совпадать с первой и последней записью DATA — это
        # проверяет validate_data_integrity().
        'period_start': '2025-08-07T19:15:00',
        'period_end': '2025-08-22T16:00:00',
        'license': 'Open data, free for research and educational use',
        'disclaimer': 'For demonstration purposes only. Not for production trading.',
        'file_module': 'embedded.mt_xauusd_m15',
        'size_bytes': 207315,
        'updated': '2025-08-25 18:38:51',
        'original_filename': 'XAUUSDM15.csv'
    }
}


def get_dataset_registry() -> Dict[str, Dict[str, Any]]:
    """
    Получить полный реестр датасетов.
    
    Returns:
        Словарь с метаданными всех доступных датасетов
    """
    return AVAILABLE_DATASETS.copy()


def get_dataset_info(dataset_name: str) -> Dict[str, Any]:
    """
    Получить информацию о конкретном датасете.
    
    Args:
        dataset_name: Название датасета
    
    Returns:
        Словарь с метаданными датасета
    
    Raises:
        KeyError: Если датасет не найден
    """
    if dataset_name not in AVAILABLE_DATASETS:
        available = list(AVAILABLE_DATASETS.keys())
        raise KeyError(f"Dataset '{dataset_name}' not found. Available datasets: {available}")
    
    return AVAILABLE_DATASETS[dataset_name].copy()


def list_dataset_names() -> List[str]:
    """
    Получить список названий всех доступных датасетов.
    
    Returns:
        Список названий датасетов
    """
    return list(AVAILABLE_DATASETS.keys())


def get_datasets_summary() -> List[Dict[str, Any]]:
    """
    Получить краткую сводку по всем датасетам.
    
    Returns:
        Список словарей с основной информацией о каждом датасете
    """
    summary = []
    
    for dataset_name, info in AVAILABLE_DATASETS.items():
        summary.append({
            'name': dataset_name,
            'title': info['name'],
            'description': info['description'],
            'symbol': info['symbol'],
            'timeframe': info['timeframe'],
            'rows': info['rows'],
            'columns_count': len(info['columns']),
            'size_kb': round(info['size_bytes'] / 1024, 1),
            'source': info['source'],
            'updated': info['updated']
        })
    
    return summary


def validate_dataset_name(dataset_name: str) -> bool:
    """
    Проверить, что название датасета корректно.
    
    Args:
        dataset_name: Название датасета для проверки
    
    Returns:
        True если датасет существует
    """
    return dataset_name in AVAILABLE_DATASETS


def get_dataset_file_module(dataset_name: str) -> str:
    """
    Получить имя модуля для загрузки данных датасета.
    
    Args:
        dataset_name: Название датасета
    
    Returns:
        Имя модуля для импорта
    
    Raises:
        KeyError: Если датасет не найден
    """
    if not validate_dataset_name(dataset_name):
        raise KeyError(f"Dataset '{dataset_name}' not found")
    
    return AVAILABLE_DATASETS[dataset_name]['file_module']


def get_datasets_by_symbol(symbol: str) -> List[str]:
    """
    Найти все датасеты для указанного символа.
    
    Args:
        symbol: Символ финансового инструмента (например, 'XAUUSD')
    
    Returns:
        Список названий датасетов для данного символа
    """
    matching_datasets = []
    
    for dataset_name, info in AVAILABLE_DATASETS.items():
        if info['symbol'].upper() == symbol.upper():
            matching_datasets.append(dataset_name)
    
    return matching_datasets


def get_datasets_by_timeframe(timeframe: str) -> List[str]:
    """
    Найти все датасеты для указанного таймфрейма.
    
    Args:
        timeframe: Таймфрейм (например, '1H', '15M')
    
    Returns:
        Список названий датасетов для данного таймфрейма
    """
    matching_datasets = []
    
    for dataset_name, info in AVAILABLE_DATASETS.items():
        if info['timeframe'].upper() == timeframe.upper():
            matching_datasets.append(dataset_name)
    
    return matching_datasets


def get_datasets_by_source(source: str) -> List[str]:
    """
    Найти все датасеты от указанного источника.
    
    Args:
        source: Источник данных (например, 'TradingView', 'MetaTrader')
    
    Returns:
        Список названий датасетов от данного источника
    """
    matching_datasets = []
    
    for dataset_name, info in AVAILABLE_DATASETS.items():
        if source.lower() in info['source'].lower():
            matching_datasets.append(dataset_name)
    
    return matching_datasets


def print_datasets_info():
    """Вывести информацию о всех доступных датасетах."""
    print("BQuant Sample Datasets")
    print("=" * 50)
    
    for dataset_name, info in AVAILABLE_DATASETS.items():
        print(f"\n📊 {info['name']} ({dataset_name})")
        print(f"   Source: {info['source']}")
        print(f"   Symbol: {info['symbol']} | Timeframe: {info['timeframe']}")
        print(f"   Rows: {info['rows']} | Columns: {len(info['columns'])}")
        print(f"   Size: {round(info['size_bytes'] / 1024, 1)} KB")
        print(f"   Period: {info['period_start']} → {info['period_end']}")
        print(f"   Updated: {info['updated']}")
    
    print(f"\nTotal datasets: {len(AVAILABLE_DATASETS)}")
    total_size_kb = sum(info['size_bytes'] for info in AVAILABLE_DATASETS.values()) / 1024
    print(f"Total size: {round(total_size_kb, 1)} KB")


# Экспорт основных функций
__all__ = [
    'AVAILABLE_DATASETS',
    'get_dataset_registry',
    'get_dataset_info',
    'list_dataset_names',
    'get_datasets_summary',
    'validate_dataset_name',
    'get_dataset_file_module',
    'get_datasets_by_symbol',
    'get_datasets_by_timeframe',
    'get_datasets_by_source',
    'print_datasets_info'
]
