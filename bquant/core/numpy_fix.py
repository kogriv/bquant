"""
Исправления для совместимости numpy

Этот модуль исправляет проблемы совместимости с numpy,
которые могут возникать в различных версиях.

ИСТОЧНИК: Перенесено из scripts/core/numpy_fix.py
"""

import numpy as np
import sys


def apply_numpy_fixes():
    """
    Применить исправления для numpy
    
    Исправляет проблемы с атрибутами которые могут отсутствовать
    в некоторых версиях numpy.
    """
    # Добавляем псевдоним NaN для обратной совместимости
    if not hasattr(np, 'NaN'):
        np.NaN = np.nan
    
    # Убеждаемся что модуль numpy содержит NaN
    if not hasattr(sys.modules['numpy'], 'NaN'):
        sys.modules['numpy'].NaN = np.nan


def check_numpy_compatibility() -> dict:
    """
    Проверить совместимость numpy и применить исправления
    
    Returns:
        Словарь с информацией о совместимости
    """
    info = {
        'numpy_version': np.__version__,
        'has_nan': hasattr(np, 'nan'),
        'has_NaN': hasattr(np, 'NaN'),
        'fixes_applied': False,
        'issues': []
    }
    
    # Проверяем наличие nan
    if not info['has_nan']:
        info['issues'].append('numpy.nan недоступен')
    
    # Проверяем наличие NaN (псевдоним)
    if not info['has_NaN']:
        info['issues'].append('numpy.NaN недоступен')
        apply_numpy_fixes()
        info['fixes_applied'] = True
        info['has_NaN'] = hasattr(np, 'NaN')
    
    return info


def ensure_numpy_compatibility():
    """
    Убедиться в совместимости numpy
    
    Вызывает apply_numpy_fixes() если необходимо.
    """
    if not hasattr(np, 'NaN'):
        apply_numpy_fixes()


# Применяем исправления при импорте модуля
apply_numpy_fixes()


# Экспорт основных констант для удобства
NaN = np.nan
nan = np.nan
inf = np.inf
pi = np.pi
e = np.e


# Информация для логгирования
_COMPATIBILITY_INFO = check_numpy_compatibility()

if _COMPATIBILITY_INFO['fixes_applied']:
    import logging
    logger = logging.getLogger('bquant.core.numpy_fix')
    logger.debug(f"Применены исправления numpy: {_COMPATIBILITY_INFO}")


__all__ = [
    'apply_numpy_fixes',
    'check_numpy_compatibility', 
    'ensure_numpy_compatibility',
    'NaN',
    'nan',
    'inf',
    'pi',
    'e'
]
