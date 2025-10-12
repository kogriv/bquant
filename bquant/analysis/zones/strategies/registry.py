"""
Strategy registry for automatic registration and factory creation.

Provides centralized registry for all strategy types with decorator-based registration.
"""

from typing import Dict, Type, Any, List
from ....core.logging_config import get_logger

logger = get_logger(__name__)


class StrategyRegistry:
    """
    Centralized registry for all metric calculation strategies.
    
    Provides decorator-based registration and factory methods for creating strategies.
    """
    
    _swing_strategies: Dict[str, Type] = {}
    _divergence_strategies: Dict[str, Type] = {}
    _shape_strategies: Dict[str, Type] = {}
    _volume_strategies: Dict[str, Type] = {}
    _volatility_strategies: Dict[str, Type] = {}
    
    # Swing strategies
    
    @classmethod
    def register_swing_strategy(cls, name: str):
        """
        Decorator for registering swing calculation strategy.
        
        Args:
            name: Strategy name for registration
        
        Example:
            @StrategyRegistry.register_swing_strategy('zigzag')
            class ZigZagSwingStrategy:
                def calculate_swings(self, zone_data):
                    ...
        """
        def decorator(strategy_class):
            cls._swing_strategies[name] = strategy_class
            logger.debug(f"Registered swing strategy: {name}")
            return strategy_class
        return decorator
    
    @classmethod
    def get_swing_strategy(cls, name: str, **params):
        """
        Create swing strategy by name.
        
        Args:
            name: Strategy name
            **params: Strategy parameters
        
        Returns:
            Strategy instance
        
        Raises:
            ValueError: If strategy name is unknown
        """
        if name not in cls._swing_strategies:
            raise ValueError(
                f"Unknown swing strategy: {name}. "
                f"Available: {list(cls._swing_strategies.keys())}"
            )
        return cls._swing_strategies[name](**params)
    
    @classmethod
    def list_swing_strategies(cls) -> List[str]:
        """List available swing strategies."""
        return list(cls._swing_strategies.keys())
    
    # Divergence strategies
    
    @classmethod
    def register_divergence_strategy(cls, name: str):
        """
        Decorator for registering divergence calculation strategy.
        
        Args:
            name: Strategy name for registration
        """
        def decorator(strategy_class):
            cls._divergence_strategies[name] = strategy_class
            logger.debug(f"Registered divergence strategy: {name}")
            return strategy_class
        return decorator
    
    @classmethod
    def get_divergence_strategy(cls, name: str, **params):
        """
        Create divergence strategy by name.
        
        Args:
            name: Strategy name
            **params: Strategy parameters
        
        Returns:
            Strategy instance
        
        Raises:
            ValueError: If strategy name is unknown
        """
        if name not in cls._divergence_strategies:
            raise ValueError(
                f"Unknown divergence strategy: {name}. "
                f"Available: {list(cls._divergence_strategies.keys())}"
            )
        return cls._divergence_strategies[name](**params)
    
    @classmethod
    def list_divergence_strategies(cls) -> List[str]:
        """List available divergence strategies."""
        return list(cls._divergence_strategies.keys())
    
    # Shape strategies
    
    @classmethod
    def register_shape_strategy(cls, name: str):
        """
        Decorator for registering shape calculation strategy.
        
        Args:
            name: Strategy name for registration
        """
        def decorator(strategy_class):
            cls._shape_strategies[name] = strategy_class
            logger.debug(f"Registered shape strategy: {name}")
            return strategy_class
        return decorator
    
    @classmethod
    def get_shape_strategy(cls, name: str, **params):
        """
        Create shape strategy by name.
        
        Args:
            name: Strategy name
            **params: Strategy parameters
        
        Returns:
            Strategy instance
        
        Raises:
            ValueError: If strategy name is unknown
        """
        if name not in cls._shape_strategies:
            raise ValueError(
                f"Unknown shape strategy: {name}. "
                f"Available: {list(cls._shape_strategies.keys())}"
            )
        return cls._shape_strategies[name](**params)
    
    @classmethod
    def list_shape_strategies(cls) -> List[str]:
        """List available shape strategies."""
        return list(cls._shape_strategies.keys())
    
    # Volume strategies
    
    @classmethod
    def register_volume_strategy(cls, name: str):
        """
        Decorator for registering volume calculation strategy.
        
        Args:
            name: Strategy name for registration
        """
        def decorator(strategy_class):
            cls._volume_strategies[name] = strategy_class
            logger.debug(f"Registered volume strategy: {name}")
            return strategy_class
        return decorator
    
    @classmethod
    def get_volume_strategy(cls, name: str, **params):
        """
        Create volume strategy by name.
        
        Args:
            name: Strategy name
            **params: Strategy parameters
        
        Returns:
            Strategy instance
        
        Raises:
            ValueError: If strategy name is unknown
        """
        if name not in cls._volume_strategies:
            raise ValueError(
                f"Unknown volume strategy: {name}. "
                f"Available: {list(cls._volume_strategies.keys())}"
            )
        return cls._volume_strategies[name](**params)
    
    @classmethod
    def list_volume_strategies(cls) -> List[str]:
        """List available volume strategies."""
        return list(cls._volume_strategies.keys())
    
    # Volatility strategies
    
    @classmethod
    def register_volatility_strategy(cls, name: str):
        """
        Decorator for registering volatility calculation strategy.
        
        Args:
            name: Strategy name for registration
        """
        def decorator(strategy_class):
            cls._volatility_strategies[name] = strategy_class
            logger.debug(f"Registered volatility strategy: {name}")
            return strategy_class
        return decorator
    
    @classmethod
    def get_volatility_strategy(cls, name: str, **params):
        """
        Create volatility strategy by name.
        
        Args:
            name: Strategy name
            **params: Strategy parameters
        
        Returns:
            Strategy instance
        
        Raises:
            ValueError: If strategy name is unknown
        """
        if name not in cls._volatility_strategies:
            raise ValueError(
                f"Unknown volatility strategy: {name}. "
                f"Available: {list(cls._volatility_strategies.keys())}"
            )
        return cls._volatility_strategies[name](**params)
    
    @classmethod
    def list_volatility_strategies(cls) -> List[str]:
        """List available volatility strategies."""
        return list(cls._volatility_strategies.keys())
    
    # Utility methods
    
    @classmethod
    def list_all_strategies(cls) -> Dict[str, List[str]]:
        """
        List all registered strategies grouped by type.
        
        Returns:
            Dictionary with strategy types as keys and lists of strategy names as values
        """
        return {
            'swing': cls.list_swing_strategies(),
            'divergence': cls.list_divergence_strategies(),
            'shape': cls.list_shape_strategies(),
            'volume': cls.list_volume_strategies(),
            'volatility': cls.list_volatility_strategies()
        }
    
    @classmethod
    def get_registry_stats(cls) -> Dict[str, int]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with counts of registered strategies by type
        """
        return {
            'swing': len(cls._swing_strategies),
            'divergence': len(cls._divergence_strategies),
            'shape': len(cls._shape_strategies),
            'volume': len(cls._volume_strategies),
            'volatility': len(cls._volatility_strategies),
            'total': (len(cls._swing_strategies) + len(cls._divergence_strategies) + 
                     len(cls._shape_strategies) + len(cls._volume_strategies) + 
                     len(cls._volatility_strategies))
        }


__all__ = ['StrategyRegistry']

