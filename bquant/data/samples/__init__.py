"""
BQuant Sample Data API

Этот модуль предоставляет unified API для работы со встроенными тестовыми данными.
Включает функции для загрузки, валидации и работы с sample датасетами.

Основные функции:
- get_sample_data(): Загрузка данных в различных форматах
- list_datasets(): Список доступных датасетов
- get_dataset_info(): Информация о конкретном датасете
- validate_dataset(): Валидация целостности датасета
- SampleDataGenerator: Генератор embedded данных

Примеры использования:
    >>> from bquant.data.samples import get_sample_data, list_datasets
    >>> 
    >>> # Получение данных как pandas DataFrame
    >>> df = get_sample_data('tv_xauusd_1h')
    >>> print(df.shape)  # (1000, 14)
    >>> 
    >>> # Получение данных как список словарей
    >>> data = get_sample_data('mt_xauusd_m15', format='dict')
    >>> print(len(data))  # 1000
    >>> 
    >>> # Список всех датасетов
    >>> datasets = list_datasets()
    >>> for dataset in datasets:
    ...     print(f"{dataset['name']}: {dataset['rows']} rows")
    >>> 
    >>> # Генерация embedded данных
    >>> from bquant.data.samples import SampleDataGenerator
    >>> generator = SampleDataGenerator()
    >>> generator.generate_all()
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Union, Literal

from ...core.logging_config import get_logger
from .datasets import (
    get_dataset_registry,
    get_dataset_info as _get_dataset_info,
    list_dataset_names,
    get_datasets_summary,
    validate_dataset_name,
    get_datasets_by_symbol,
    get_datasets_by_timeframe,
    get_datasets_by_source,
    print_datasets_info
)
from .utils import (
    load_embedded_data,
    convert_to_dataframe,
    convert_to_list_of_dicts,
    validate_data_integrity,
    get_data_sample,
    get_records_statistics,
    compare_datasets
)
from .generator import SampleDataGenerator

logger = get_logger(__name__)

# Type hints для форматов данных
DataFormat = Literal['pandas', 'dataframe', 'dict', 'list']


def get_sample_data(
    dataset_name: str, 
    format: DataFormat = 'pandas'
) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Получить sample данные в указанном формате.
    
    Args:
        dataset_name: Название датасета ('tv_xauusd_1h' или 'mt_xauusd_m15')
        format: Формат данных ('pandas'/'dataframe' или 'dict'/'list')
    
    Returns:
        Данные в запрошенном формате:
        - 'pandas'/'dataframe': pandas.DataFrame
        - 'dict'/'list': List[Dict[str, Any]]
    
    Raises:
        KeyError: Если датасет не найден
        ValueError: Если указан неподдерживаемый формат
        ImportError: Если не удается загрузить данные
    
    Examples:
        >>> # Загрузка как DataFrame (по умолчанию)
        >>> df = get_sample_data('tv_xauusd_1h')
        >>> print(df.shape)  # (1000, 14)
        >>> 
        >>> # Загрузка как список словарей
        >>> data = get_sample_data('mt_xauusd_m15', format='dict')
        >>> print(len(data))  # 1000
    """
    logger.debug(f"Loading sample data: {dataset_name}, format: {format}")
    
    # Валидация входных параметров
    if not validate_dataset_name(dataset_name):
        available = list_dataset_names()
        raise KeyError(f"Dataset '{dataset_name}' not found. Available datasets: {available}")
    
    supported_formats = ['pandas', 'dataframe', 'dict', 'list']
    if format not in supported_formats:
        raise ValueError(f"Unsupported format '{format}'. Supported: {supported_formats}")
    
    try:
        # Загружаем embedded данные
        embedded_data = load_embedded_data(dataset_name)
        raw_data = embedded_data['DATA']
        
        logger.debug(f"Loaded {len(raw_data)} records for {dataset_name}")
        
        # Конвертируем в нужный формат
        if format in ['pandas', 'dataframe']:
            result = convert_to_dataframe(raw_data, dataset_name)
            logger.debug(f"Converted to DataFrame with shape {result.shape}")
            return result
            
        elif format in ['dict', 'list']:
            logger.debug(f"Returning {len(raw_data)} records as list of dicts")
            return raw_data
        
    except Exception as e:
        logger.error(f"Failed to load sample data for {dataset_name}: {e}")
        raise


def list_datasets() -> List[Dict[str, Any]]:
    """
    Получить список всех доступных sample датасетов с их основной информацией.
    
    Returns:
        Список словарей с информацией о каждом датасете
    
    Examples:
        >>> datasets = list_datasets()
        >>> for dataset in datasets:
        ...     print(f"{dataset['title']}: {dataset['rows']} rows, {dataset['size_kb']} KB")
    """
    logger.debug("Listing all available datasets")
    
    try:
        datasets_summary = get_datasets_summary()
        logger.debug(f"Found {len(datasets_summary)} available datasets")
        return datasets_summary
        
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        return []


def get_dataset_info(dataset_name: str) -> Dict[str, Any]:
    """
    Получить детальную информацию о конкретном датасете.
    
    Args:
        dataset_name: Название датасета
    
    Returns:
        Словарь с полной информацией о датасете
    
    Raises:
        KeyError: Если датасет не найден
    
    Examples:
        >>> info = get_dataset_info('tv_xauusd_1h')
        >>> print(info['name'])  # 'TradingView XAUUSD 1H'
        >>> print(info['symbol'])  # 'XAUUSD'
        >>> print(info['columns'])  # ['time', 'open', 'high', ...]
    """
    logger.debug(f"Getting info for dataset: {dataset_name}")
    
    try:
        info = _get_dataset_info(dataset_name)
        logger.debug(f"Retrieved info for {dataset_name}")
        return info
        
    except KeyError as e:
        logger.error(f"Dataset not found: {dataset_name}")
        raise


def validate_dataset(dataset_name: str) -> Dict[str, Any]:
    """
    Валидировать целостность и корректность данных датасета.
    
    Args:
        dataset_name: Название датасета для валидации
    
    Returns:
        Словарь с результатами валидации:
        - is_valid: bool - общий статус валидации
        - errors: List[str] - критические ошибки
        - warnings: List[str] - предупреждения
        - stats: Dict - статистика по данным
    
    Examples:
        >>> result = validate_dataset('tv_xauusd_1h')
        >>> if result['is_valid']:
        ...     print("Dataset is valid!")
        ... else:
        ...     print("Errors:", result['errors'])
    """
    logger.debug(f"Validating dataset: {dataset_name}")
    
    try:
        # Загружаем данные и метаинформацию
        embedded_data = load_embedded_data(dataset_name)
        dataset_info = get_dataset_info(dataset_name)
        
        # Валидируем
        validation_result = validate_data_integrity(embedded_data['DATA'], dataset_info)
        
        logger.debug(f"Validation completed for {dataset_name}: {'PASSED' if validation_result['is_valid'] else 'FAILED'}")
        return validation_result
        
    except Exception as e:
        logger.error(f"Validation failed for {dataset_name}: {e}")
        return {
            'is_valid': False,
            'errors': [f"Validation exception: {e}"],
            'warnings': [],
            'stats': {}
        }


def get_sample_preview(dataset_name: str, n: int = 5) -> List[Dict[str, Any]]:
    """
    Получить предварительный просмотр данных (первые n записей).
    
    Args:
        dataset_name: Название датасета
        n: Количество записей для просмотра (по умолчанию 5)
    
    Returns:
        Список первых n записей
    
    Examples:
        >>> preview = get_sample_preview('tv_xauusd_1h', 3)
        >>> for record in preview:
        ...     print(f"Time: {record['time']}, Close: {record['close']}")
    """
    logger.debug(f"Getting preview for {dataset_name}, n={n}")
    
    try:
        embedded_data = load_embedded_data(dataset_name)
        sample = get_data_sample(embedded_data['DATA'], n)
        
        logger.debug(f"Retrieved {len(sample)} records for preview")
        return sample
        
    except Exception as e:
        logger.error(f"Failed to get preview for {dataset_name}: {e}")
        return []


def get_data_statistics(dataset_name: str) -> Dict[str, Any]:
    """
    Получить статистическую информацию о данных датасета.
    
    Args:
        dataset_name: Название датасета
    
    Returns:
        Словарь со статистикой по данным
    
    Examples:
        >>> stats = get_data_statistics('tv_xauusd_1h')
        >>> print(f"Total records: {stats['total_records']}")
        >>> print(f"Columns: {stats['total_columns']}")
    """
    logger.debug(f"Getting statistics for dataset: {dataset_name}")
    
    try:
        embedded_data = load_embedded_data(dataset_name)
        stats = get_records_statistics(embedded_data['DATA'], dataset_name)
        
        logger.debug(f"Retrieved statistics for {dataset_name}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get statistics for {dataset_name}: {e}")
        return {'error': str(e)}


def find_datasets(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    source: Optional[str] = None
) -> List[str]:
    """
    Найти датасеты по заданным критериям.
    
    Args:
        symbol: Символ финансового инструмента (например, 'XAUUSD')
        timeframe: Таймфрейм (например, '1H', '15M')
        source: Источник данных (например, 'TradingView', 'MetaTrader')
    
    Returns:
        Список названий датасетов, соответствующих критериям
    
    Examples:
        >>> # Найти все датасеты для XAUUSD
        >>> xauusd_datasets = find_datasets(symbol='XAUUSD')
        >>> 
        >>> # Найти все часовые датасеты
        >>> hourly_datasets = find_datasets(timeframe='1H')
        >>> 
        >>> # Найти все датасеты от TradingView
        >>> tv_datasets = find_datasets(source='TradingView')
    """
    logger.debug(f"Finding datasets: symbol={symbol}, timeframe={timeframe}, source={source}")
    
    results = set(list_dataset_names())  # Начинаем со всех датасетов
    
    try:
        if symbol:
            symbol_datasets = set(get_datasets_by_symbol(symbol))
            results = results.intersection(symbol_datasets)
        
        if timeframe:
            timeframe_datasets = set(get_datasets_by_timeframe(timeframe))
            results = results.intersection(timeframe_datasets)
        
        if source:
            source_datasets = set(get_datasets_by_source(source))
            results = results.intersection(source_datasets)
        
        result_list = list(results)
        logger.debug(f"Found {len(result_list)} datasets matching criteria")
        return result_list
        
    except Exception as e:
        logger.error(f"Failed to find datasets: {e}")
        return []


def compare_sample_datasets(dataset1: str, dataset2: str) -> Dict[str, Any]:
    """
    Сравнить два sample датасета.
    
    Args:
        dataset1: Название первого датасета
        dataset2: Название второго датасета
    
    Returns:
        Словарь с результатами сравнения
    
    Examples:
        >>> comparison = compare_sample_datasets('tv_xauusd_1h', 'mt_xauusd_m15')
        >>> print(f"Common columns: {comparison['common_columns']}")
    """
    logger.debug(f"Comparing datasets: {dataset1} vs {dataset2}")
    
    try:
        comparison = compare_datasets(dataset1, dataset2)
        logger.debug(f"Successfully compared {dataset1} and {dataset2}")
        return comparison
        
    except Exception as e:
        logger.error(f"Failed to compare datasets: {e}")
        return {'error': str(e)}


def print_sample_data_status():
    """
    Вывести статус всех sample данных.
    
    Показывает информацию о всех доступных датасетах,
    их размерах, статусе валидации и т.д.
    """
    print("🎯 BQuant Sample Data Status")
    print("=" * 50)
    
    try:
        datasets = list_datasets()
        
        if not datasets:
            print("❌ No datasets available")
            return
        
        total_size = 0
        valid_count = 0
        
        for dataset in datasets:
            dataset_name = dataset['name']
            
            print(f"\n📊 {dataset['title']} ({dataset_name})")
            print(f"   Source: {dataset['source']}")
            print(f"   Symbol: {dataset['symbol']} | Timeframe: {dataset['timeframe']}")
            print(f"   Rows: {dataset['rows']:,} | Columns: {dataset['columns_count']}")
            print(f"   Size: {dataset['size_kb']} KB")
            print(f"   Updated: {dataset['updated']}")
            
            # Валидация
            try:
                validation = validate_dataset(dataset_name)
                if validation['is_valid']:
                    print("   Status: ✅ Valid")
                    valid_count += 1
                else:
                    print("   Status: ❌ Invalid")
                    if validation['errors']:
                        print(f"   Errors: {', '.join(validation['errors'])}")
            except Exception:
                print("   Status: ❓ Could not validate")
            
            total_size += dataset['size_kb']
        
        print(f"\n📈 Summary:")
        print(f"   Total datasets: {len(datasets)}")
        print(f"   Valid datasets: {valid_count}/{len(datasets)}")
        print(f"   Total size: {total_size:.1f} KB")
        
        if valid_count == len(datasets):
            print("   🎉 All datasets are valid and ready to use!")
        
    except Exception as e:
        print(f"❌ Failed to get status: {e}")


# Алиас для обратной совместимости
load_sample_data = get_sample_data

# Основные экспорты
__all__ = [
    # Основные функции
    'get_sample_data',
    'load_sample_data',  # Алиас для обратной совместимости
    'list_datasets', 
    'get_dataset_info',
    'validate_dataset',
    
    # Генератор
    'SampleDataGenerator',
    
    # Дополнительные функции
    'get_sample_preview',
    'get_data_statistics',
    'find_datasets',
    'compare_sample_datasets',
    'print_sample_data_status',
    
    # Реэкспорт из подмодулей
    'get_datasets_by_symbol',
    'get_datasets_by_timeframe', 
    'get_datasets_by_source',
    'print_datasets_info'
]
