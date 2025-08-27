"""
Общие утилиты BQuant

Вспомогательные функции для проекта BQuant.
"""

import pandas as pd
import numpy as np
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from .config import PROJECT_ROOT, LOGGING


def setup_project_logging(
    name: str = 'bquant', 
    level: str = None,
    log_to_file: bool = None,
    log_file: Union[str, Path] = None
) -> logging.Logger:
    """
    Настроить логгирование для проекта BQuant
    
    Args:
        name: Имя логгера
        level: Уровень логгирования ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_to_file: Логгировать в файл
        log_file: Путь к файлу логов
    
    Returns:
        Настроенный logger
    """
    # Получаем настройки из конфигурации
    level = level or LOGGING['level']
    log_to_file = log_to_file if log_to_file is not None else LOGGING['file_logging']
    log_file = log_file or LOGGING['log_file']
    
    # Создаем логгер
    logger = logging.getLogger(name)
    
    # Если уже настроен, возвращаем
    if logger.handlers:
        return logger
    
    # Устанавливаем уровень
    logger.setLevel(getattr(logging, level.upper()))
    
    # Создаем форматтер
    formatter = logging.Formatter(LOGGING['format'])
    
    # Добавляем консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Добавляем файловый обработчик если нужно
    if log_to_file:
        # Создаем директорию для логов если не существует
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True, parents=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def calculate_returns(
    prices: pd.Series, 
    method: str = 'simple',
    periods: int = 1
) -> pd.Series:
    """
    Рассчитать доходности
    
    Args:
        prices: Серия цен
        method: Метод расчета ('simple', 'log')
        periods: Количество периодов для расчета
    
    Returns:
        Серия доходностей
    """
    if method == 'simple':
        return prices.pct_change(periods=periods)
    elif method == 'log':
        return np.log(prices / prices.shift(periods))
    else:
        raise ValueError(f"Неподдерживаемый метод: {method}. Используйте 'simple' или 'log'")


def normalize_data(
    data: pd.DataFrame, 
    method: str = 'zscore',
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Нормализовать данные
    
    Args:
        data: Данные для нормализации
        method: Метод нормализации ('zscore', 'minmax', 'robust')
        columns: Колонки для нормализации (по умолчанию все числовые)
    
    Returns:
        Нормализованные данные
    """
    result = data.copy()
    
    # Определяем колонки для нормализации
    if columns is None:
        columns = data.select_dtypes(include=[np.number]).columns.tolist()
    
    for col in columns:
        if col not in data.columns:
            continue
            
        if method == 'zscore':
            # Z-score нормализация
            mean = data[col].mean()
            std = data[col].std()
            if std != 0:
                result[col] = (data[col] - mean) / std
        
        elif method == 'minmax':
            # Min-Max нормализация
            min_val = data[col].min()
            max_val = data[col].max()
            if max_val != min_val:
                result[col] = (data[col] - min_val) / (max_val - min_val)
        
        elif method == 'robust':
            # Robust нормализация (медиана и MAD)
            median = data[col].median()
            mad = np.median(np.abs(data[col] - median))
            if mad != 0:
                result[col] = (data[col] - median) / mad
        
        else:
            raise ValueError(f"Неподдерживаемый метод: {method}")
    
    return result


def save_results(
    data: Any, 
    filepath: Union[str, Path], 
    format: str = 'csv',
    **kwargs
) -> bool:
    """
    Универсальное сохранение результатов
    
    Args:
        data: Данные для сохранения
        filepath: Путь к файлу
        format: Формат сохранения ('csv', 'json', 'parquet', 'pickle')
        **kwargs: Дополнительные параметры для функций сохранения
    
    Returns:
        True если сохранение успешно
    """
    try:
        filepath = Path(filepath)
        filepath.parent.mkdir(exist_ok=True, parents=True)
        
        if format == 'csv':
            if isinstance(data, pd.DataFrame):
                data.to_csv(filepath, **kwargs)
            else:
                raise ValueError("Для CSV формата данные должны быть DataFrame")
        
        elif format == 'json':
            import json
            if isinstance(data, pd.DataFrame):
                data.to_json(filepath, **kwargs)
            elif isinstance(data, (dict, list)):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, **kwargs)
            else:
                raise ValueError("Для JSON формата данные должны быть DataFrame, dict или list")
        
        elif format == 'parquet':
            if isinstance(data, pd.DataFrame):
                data.to_parquet(filepath, **kwargs)
            else:
                raise ValueError("Для Parquet формата данные должны быть DataFrame")
        
        elif format == 'pickle':
            import pickle
            with open(filepath, 'wb') as f:
                pickle.dump(data, f, **kwargs)
        
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")
        
        return True
    
    except Exception as e:
        logger = logging.getLogger('bquant.utils')
        logger.error(f"Ошибка сохранения данных: {e}")
        return False


def validate_ohlcv_columns(data: pd.DataFrame, strict: bool = True) -> Dict[str, Any]:
    """
    Валидация колонок OHLCV данных
    
    Args:
        data: DataFrame с данными
        strict: Строгая валидация (требуются все колонки)
    
    Returns:
        Словарь с результатами валидации
    """
    required_columns = ['open', 'high', 'low', 'close']
    optional_columns = ['volume']
    
    result = {
        'is_valid': True,
        'missing_required': [],
        'missing_optional': [],
        'extra_columns': [],
        'messages': []
    }
    
    # Проверяем обязательные колонки
    for col in required_columns:
        if col not in data.columns:
            result['missing_required'].append(col)
    
    # Проверяем опциональные колонки
    for col in optional_columns:
        if col not in data.columns:
            result['missing_optional'].append(col)
    
    # Находим дополнительные колонки
    all_expected = required_columns + optional_columns
    for col in data.columns:
        if col not in all_expected:
            result['extra_columns'].append(col)
    
    # Определяем результат валидации
    if result['missing_required']:
        result['is_valid'] = False
        result['messages'].append(f"Отсутствуют обязательные колонки: {result['missing_required']}")
    
    if strict and result['missing_optional']:
        result['is_valid'] = False
        result['messages'].append(f"Отсутствуют опциональные колонки: {result['missing_optional']}")
    
    if result['extra_columns']:
        result['messages'].append(f"Дополнительные колонки: {result['extra_columns']}")
    
    if result['is_valid'] and not result['messages']:
        result['messages'].append("Структура данных валидна")
    
    return result


def create_timestamp(format: str = 'compact') -> str:
    """
    Создать временную метку для именования файлов
    
    Args:
        format: Формат временной метки ('compact', 'readable', 'iso')
    
    Returns:
        Строка с временной меткой
    """
    from datetime import datetime
    
    now = datetime.now()
    
    if format == 'compact':
        return now.strftime('%Y%m%d_%H%M%S')
    elif format == 'readable':
        return now.strftime('%Y-%m-%d %H:%M:%S')
    elif format == 'iso':
        return now.isoformat()
    else:
        raise ValueError(f"Неподдерживаемый формат: {format}")


def memory_usage_info(data: pd.DataFrame) -> Dict[str, Any]:
    """
    Получить информацию об использовании памяти DataFrame
    
    Args:
        data: DataFrame для анализа
    
    Returns:
        Словарь с информацией о памяти
    """
    memory_usage = data.memory_usage(deep=True)
    
    return {
        'total_memory_mb': memory_usage.sum() / 1024**2,
        'index_memory_mb': memory_usage.iloc[0] / 1024**2,
        'columns_memory_mb': {
            col: memory_usage[col] / 1024**2 
            for col in data.columns
        },
        'shape': data.shape,
        'dtypes': data.dtypes.to_dict()
    }


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Убедиться, что директория существует
    
    Args:
        path: Путь к директории
    
    Returns:
        Path объект
    """
    path = Path(path)
    path.mkdir(exist_ok=True, parents=True)
    return path


# Глобальный логгер для модуля
logger = setup_project_logging('bquant.core.utils')
