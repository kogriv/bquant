"""
Утилиты для работы с sample данными BQuant

Этот модуль предоставляет вспомогательные функции для загрузки,
валидации и конвертации sample данных.
"""

import importlib
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from ...core.logging_config import get_logger
from .datasets import (
    validate_dataset_name, 
    get_dataset_info, 
    get_dataset_file_module,
    list_dataset_names
)

logger = get_logger(__name__)


def load_embedded_data(dataset_name: str) -> Dict[str, Any]:
    """
    Загрузить embedded данные для указанного датасета.
    
    Args:
        dataset_name: Название датасета
    
    Returns:
        Словарь с ключами 'DATASET_INFO' и 'DATA'
    
    Raises:
        ImportError: Если не удается импортировать данные
        KeyError: Если датасет не найден
    """
    logger.debug(f"Loading embedded data for dataset: {dataset_name}")
    
    # Проверяем существование датасета
    if not validate_dataset_name(dataset_name):
        available = list_dataset_names()
        raise KeyError(f"Dataset '{dataset_name}' not found. Available: {available}")
    
    # Получаем имя модуля
    module_name = get_dataset_file_module(dataset_name)
    full_module_path = f"bquant.data.samples.{module_name}"
    
    try:
        # Импортируем модуль с данными
        data_module = importlib.import_module(full_module_path)
        
        # Проверяем наличие необходимых атрибутов
        if not hasattr(data_module, 'DATASET_INFO'):
            raise ImportError(f"Module {full_module_path} missing DATASET_INFO")
        
        if not hasattr(data_module, 'DATA'):
            raise ImportError(f"Module {full_module_path} missing DATA")
        
        result = {
            'DATASET_INFO': data_module.DATASET_INFO,
            'DATA': data_module.DATA
        }
        
        logger.debug(f"Successfully loaded {len(result['DATA'])} records from {dataset_name}")
        return result
        
    except ImportError as e:
        logger.error(f"Failed to import embedded data for {dataset_name}: {e}")
        raise ImportError(f"Cannot load embedded data for '{dataset_name}': {e}")


def convert_to_dataframe(data: List[Dict[str, Any]], dataset_name: str) -> pd.DataFrame:
    """
    Конвертировать список словарей в pandas DataFrame.
    
    Args:
        data: Список словарей с данными
        dataset_name: Название датасета (для логирования)
    
    Returns:
        pandas DataFrame с данными
    """
    logger.debug(f"Converting {len(data)} records to DataFrame for {dataset_name}")
    
    if not data:
        logger.warning(f"Empty data provided for {dataset_name}")
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(data)
        
        # Пытаемся конвертировать time колонку в datetime
        if 'time' in df.columns:
            try:
                df['time'] = pd.to_datetime(df['time'])
                logger.debug(f"Converted time column to datetime for {dataset_name}")
            except Exception as e:
                logger.warning(f"Could not convert time column to datetime: {e}")
        
        # Убеждаемся, что числовые колонки имеют правильный тип
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.debug(f"Successfully created DataFrame with shape {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Failed to convert data to DataFrame for {dataset_name}: {e}")
        raise ValueError(f"Cannot convert data to DataFrame: {e}")


def convert_to_list_of_dicts(df: pd.DataFrame, dataset_name: str) -> List[Dict[str, Any]]:
    """
    Конвертировать pandas DataFrame в список словарей.
    
    Args:
        df: pandas DataFrame
        dataset_name: Название датасета (для логирования)
    
    Returns:
        Список словарей с данными
    """
    logger.debug(f"Converting DataFrame with shape {df.shape} to list of dicts for {dataset_name}")
    
    try:
        # Заменяем NaN на None
        df_clean = df.where(pd.notnull(df), None)
        
        # Конвертируем в список словарей
        data_list = df_clean.to_dict('records')
        
        logger.debug(f"Successfully converted to {len(data_list)} records")
        return data_list
        
    except Exception as e:
        logger.error(f"Failed to convert DataFrame to list of dicts for {dataset_name}: {e}")
        raise ValueError(f"Cannot convert DataFrame to list: {e}")


def validate_data_integrity(data: List[Dict[str, Any]], dataset_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидировать целостность загруженных данных.
    
    Args:
        data: Данные для валидации
        dataset_info: Информация о датасете
    
    Returns:
        Словарь с результатами валидации
    """
    logger.debug("Validating data integrity")
    
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    try:
        # Проверяем количество записей
        expected_rows = dataset_info.get('rows', 0)
        actual_rows = len(data)
        
        if actual_rows != expected_rows:
            validation_result['warnings'].append(
                f"Row count mismatch: expected {expected_rows}, got {actual_rows}"
            )
        
        validation_result['stats']['rows'] = actual_rows
        
        # Проверяем структуру данных
        if not data:
            validation_result['errors'].append("Data is empty")
            validation_result['is_valid'] = False
            return validation_result
        
        # Получаем колонки из первой записи
        first_record = data[0]
        actual_columns = set(first_record.keys())
        expected_columns = set(dataset_info.get('columns', []))
        
        # Нормализуем названия для сравнения
        actual_normalized = {col.lower().replace(' ', '_').replace('/', '_') for col in actual_columns}
        expected_normalized = {col.lower().replace(' ', '_').replace('/', '_') for col in expected_columns}
        
        missing_columns = expected_normalized - actual_normalized
        extra_columns = actual_normalized - expected_normalized
        
        if missing_columns:
            validation_result['warnings'].append(
                f"Missing columns: {list(missing_columns)}"
            )
        
        if extra_columns:
            validation_result['warnings'].append(
                f"Extra columns: {list(extra_columns)}"
            )
        
        validation_result['stats']['columns'] = len(actual_columns)
        validation_result['stats']['expected_columns'] = len(expected_columns)
        
        # Проверяем основные OHLCV колонки
        required_ohlcv = ['open', 'high', 'low', 'close']
        missing_ohlcv = []
        
        for col in required_ohlcv:
            if col not in actual_normalized:
                missing_ohlcv.append(col)
        
        if missing_ohlcv:
            validation_result['errors'].append(
                f"Missing required OHLCV columns: {missing_ohlcv}"
            )
            validation_result['is_valid'] = False
        
        # Проверяем временную колонку
        time_cols = [col for col in actual_columns if 'time' in col.lower()]
        if not time_cols:
            validation_result['warnings'].append("No time column found")
        
        # Статистика по типам данных
        type_stats = {}
        for key in first_record.keys():
            values = [record.get(key) for record in data[:100]]  # Проверяем первые 100 записей
            non_null_values = [v for v in values if v is not None]
            
            if non_null_values:
                value_types = set(type(v).__name__ for v in non_null_values)
                type_stats[key] = list(value_types)
        
        validation_result['stats']['column_types'] = type_stats
        
        logger.debug(f"Validation completed: {'PASSED' if validation_result['is_valid'] else 'FAILED'}")
        
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        validation_result['errors'].append(f"Validation exception: {e}")
        validation_result['is_valid'] = False
    
    return validation_result


def get_data_sample(data: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    """
    Получить образец данных для предварительного просмотра.
    
    Args:
        data: Полные данные
        n: Количество записей для образца
    
    Returns:
        Первые n записей
    """
    return data[:n] if data else []


def get_data_info(data: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    """
    Получить статистическую информацию о данных.
    
    Args:
        data: Данные для анализа
        dataset_name: Название датасета
    
    Returns:
        Словарь со статистикой
    """
    if not data:
        return {'error': 'No data provided'}
    
    first_record = data[0]
    columns = list(first_record.keys())
    
    # Базовая статистика
    info = {
        'dataset_name': dataset_name,
        'total_records': len(data),
        'total_columns': len(columns),
        'columns': columns,
        'memory_size_bytes': 0  # Примерная оценка
    }
    
    # Примерная оценка размера в памяти
    import sys
    try:
        info['memory_size_bytes'] = sys.getsizeof(data)
    except:
        pass
    
    # Анализ временного диапазона
    time_col = None
    for col in ['time', 'timestamp', 'datetime']:
        if col in columns:
            time_col = col
            break
    
    if time_col:
        try:
            time_values = [record[time_col] for record in data if record.get(time_col)]
            if time_values:
                info['time_range'] = {
                    'start': str(time_values[0]),
                    'end': str(time_values[-1]),
                    'total_periods': len(time_values)
                }
        except:
            pass
    
    # Статистика по колонкам
    column_stats = {}
    for col in columns:
        values = [record.get(col) for record in data]
        non_null_count = sum(1 for v in values if v is not None)
        
        column_stats[col] = {
            'non_null_count': non_null_count,
            'null_count': len(values) - non_null_count,
            'null_percentage': round((len(values) - non_null_count) / len(values) * 100, 2)
        }
        
        # Для числовых колонок добавляем мин/макс
        numeric_values = []
        for v in values:
            if v is not None and isinstance(v, (int, float)):
                numeric_values.append(float(v))
        
        if numeric_values:
            column_stats[col].update({
                'min_value': min(numeric_values),
                'max_value': max(numeric_values),
                'mean_value': sum(numeric_values) / len(numeric_values)
            })
    
    info['column_statistics'] = column_stats
    
    return info


def compare_datasets(dataset1_name: str, dataset2_name: str) -> Dict[str, Any]:
    """
    Сравнить два датасета.
    
    Args:
        dataset1_name: Название первого датасета
        dataset2_name: Название второго датасета
    
    Returns:
        Словарь с результатами сравнения
    """
    try:
        # Загружаем информацию о датасетах
        info1 = get_dataset_info(dataset1_name)
        info2 = get_dataset_info(dataset2_name)
        
        comparison = {
            'datasets': [dataset1_name, dataset2_name],
            'comparison': {
                'symbols': [info1['symbol'], info2['symbol']],
                'timeframes': [info1['timeframe'], info2['timeframe']],
                'sources': [info1['source'], info2['source']],
                'rows': [info1['rows'], info2['rows']],
                'columns_count': [len(info1['columns']), len(info2['columns'])],
                'size_bytes': [info1['size_bytes'], info2['size_bytes']]
            },
            'common_columns': list(set(info1['columns']) & set(info2['columns'])),
            'unique_columns': {
                dataset1_name: list(set(info1['columns']) - set(info2['columns'])),
                dataset2_name: list(set(info2['columns']) - set(info1['columns']))
            }
        }
        
        return comparison
        
    except Exception as e:
        logger.error(f"Failed to compare datasets: {e}")
        return {'error': str(e)}


# Экспорт основных функций
__all__ = [
    'load_embedded_data',
    'convert_to_dataframe',
    'convert_to_list_of_dicts',
    'validate_data_integrity',
    'get_data_sample',
    'get_data_info',
    'compare_datasets'
]
