"""Фабрики стратегий из конфигурации: имя, словарь ``{'type', 'params'}`` или готовый экземпляр.

До G64 (2026-09-06) пять фабрик лежали в ``bquant.core.config`` и лениво импортировали
реестр стратегий: слой-основание зависел от слоя анализа, единственное ребро
``core → analysis`` против сорока обратных. Фабрика знает реестр стратегий — значит,
она стратегиям и принадлежит. Умолчания по-прежнему читаются из
``ANALYSIS_CONFIG['zone_features']`` через :func:`bquant.core.config.get_analysis_params`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from bquant.core.config import get_analysis_params

from .registry import StrategyRegistry


def create_swing_strategy(config: Optional[Union[str, Dict[str, Any]]] = None):
    """
    Create swing calculation strategy from config or string name.
    
    Args:
        config: Strategy configuration dict with 'type' and 'params' keys,
                OR string name ('find_peaks', 'zigzag', 'pivot_points'),
                OR strategy instance (returned as-is).
                If None, uses config from ANALYSIS_CONFIG['zone_features']['swing_strategy']
    
    Returns:
        Swing strategy instance or None if type is 'none'
    
    Raises:
        ValueError: If strategy type is unknown
    
    Examples:
        strategy = create_swing_strategy({'type': 'zigzag', 'params': {'threshold': 0.02}})
        strategy = create_swing_strategy('find_peaks')  # v2.1: string support
    """
    # v2.1: Support string names (from Builder API)
    if isinstance(config, str):
        strategy_type = config
        params = {}
    elif config is None:
        config = get_analysis_params('zone_features').get('swing_strategy', {})
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    elif isinstance(config, dict):
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    else:
        # Already an object (strategy instance)
        return config
    
    if strategy_type == 'none':
        return None
    
    return StrategyRegistry.get_swing_strategy(strategy_type, **params)


def create_divergence_strategy(config: Optional[Union[str, Dict[str, Any]]] = None):
    """
    Create divergence calculation strategy from config or string name.
    
    Args:
        config: Strategy configuration dict with 'type' and 'params' keys,
                OR string name ('classic'),
                OR strategy instance (returned as-is).
                If None, uses config from ANALYSIS_CONFIG['zone_features']['divergence_strategy']
    
    Returns:
        Divergence strategy instance or None if type is 'none'
    
    Raises:
        ValueError: If strategy type is unknown
    
    Examples:
        strategy = create_divergence_strategy({'type': 'classic', 'params': {}})
        strategy = create_divergence_strategy('classic')  # v2.1: string support
    """
    # v2.1: Support string names (from Builder API)
    if isinstance(config, str):
        strategy_type = config
        params = {}
    elif config is None:
        config = get_analysis_params('zone_features').get('divergence_strategy', {})
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    elif isinstance(config, dict):
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    else:
        # Already an object (strategy instance)
        return config
    
    if strategy_type == 'none':
        return None
    
    return StrategyRegistry.get_divergence_strategy(strategy_type, **params)


def create_shape_strategy(config: Optional[Union[str, Dict[str, Any]]] = None):
    """
    Create shape calculation strategy from config or string name.
    
    Args:
        config: Strategy configuration dict with 'type' and 'params' keys,
                OR string name ('statistical'),
                OR strategy instance (returned as-is).
                If None, uses config from ANALYSIS_CONFIG['zone_features']['shape_strategy']
    
    Returns:
        Shape strategy instance or None if type is 'none'
    
    Raises:
        ValueError: If strategy type is unknown
    
    Examples:
        strategy = create_shape_strategy({'type': 'statistical', 'params': {}})
        strategy = create_shape_strategy('statistical')  # v2.1: string support
    """
    # v2.1: Support string names (from Builder API)
    if isinstance(config, str):
        strategy_type = config
        params = {}
    elif config is None:
        config = get_analysis_params('zone_features').get('shape_strategy', {})
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    elif isinstance(config, dict):
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    else:
        # Already an object (strategy instance)
        return config
    
    if strategy_type == 'none':
        return None
    
    return StrategyRegistry.get_shape_strategy(strategy_type, **params)


def create_volume_strategy(config: Optional[Union[str, Dict[str, Any]]] = None):
    """
    Create volume calculation strategy from config or string name.
    
    Args:
        config: Strategy configuration dict with 'type' and 'params' keys,
                OR string name ('standard'),
                OR strategy instance (returned as-is).
                If None, uses config from ANALYSIS_CONFIG['zone_features']['volume_strategy']
    
    Returns:
        Volume strategy instance or None if type is 'none'
    
    Raises:
        ValueError: If strategy type is unknown
    
    Examples:
        strategy = create_volume_strategy({'type': 'standard', 'params': {}})
        strategy = create_volume_strategy('standard')  # v2.1: string support
    """
    # v2.1: Support string names (from Builder API)
    if isinstance(config, str):
        strategy_type = config
        params = {}
    elif config is None:
        config = get_analysis_params('zone_features').get('volume_strategy', {})
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    elif isinstance(config, dict):
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    else:
        # Already an object (strategy instance)
        return config
    
    if strategy_type == 'none':
        return None
    
    return StrategyRegistry.get_volume_strategy(strategy_type, **params)


def create_volatility_strategy(config: Optional[Union[str, Dict[str, Any]]] = None):
    """
    Create volatility calculation strategy from config or string name.
    
    Args:
        config: Strategy configuration dict with 'type' and 'params' keys,
                OR string name (currently no standard string names),
                OR strategy instance (returned as-is).
                If None, uses config from ANALYSIS_CONFIG['zone_features']['volatility_strategy']
    
    Returns:
        Volatility strategy instance or None if type is 'none'
    
    Raises:
        ValueError: If strategy type is unknown
    
    Examples:
        strategy = create_volatility_strategy({'type': 'combined', 'params': {}})
        strategy = create_volatility_strategy(my_custom_instance)  # v2.1: object support
    """
    # v2.1: Support string names and objects (from Builder API)
    if isinstance(config, str):
        # No standard string names for volatility yet
        # Treat as strategy type
        strategy_type = config
        params = {}
    elif config is None:
        config = get_analysis_params('zone_features').get('volatility_strategy', {})
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    elif isinstance(config, dict):
        strategy_type = config.get('type', 'none')
        params = config.get('params', {})
    else:
        # Already an object (strategy instance)
        return config
    
    if strategy_type == 'none':
        return None
    
    return StrategyRegistry.get_volatility_strategy(strategy_type, **params)


__all__ = [
    "create_swing_strategy",
    "create_divergence_strategy",
    "create_shape_strategy",
    "create_volume_strategy",
    "create_volatility_strategy",
]
