"""
Strategy Registry — one mechanism for five strategy families.

Until G65 (2026-09-06) register/get/list were written out five times, one copy per
family, with five private dicts and no conflict policy: registering a second class
under an existing name silently replaced the first. Now there is one bucket per
family in one dict, one ``register`` / ``get`` / ``list_strategies`` core, and the
per-family methods are thin names over it. Re-registering the **same** class is a
no-op (module reloads do that); a **different** class under a taken name is refused.
"""

from typing import Any, Dict, List, Tuple, Type

from bquant.core.logging_config import get_logger

logger = get_logger(__name__)

#: Strategy families, in the order the analyzer consumes them.
FAMILIES: Tuple[str, ...] = ('swing', 'divergence', 'shape', 'volume', 'volatility')


class StrategyRegistry:
    """
    Centralized registry for all metric calculation strategies.

    Provides decorator-based registration and factory methods for creating strategies.
    """

    _registry: Dict[str, Dict[str, Type]] = {family: {} for family in FAMILIES}

    # ------------------------------------------------------------------
    # The one mechanism
    # ------------------------------------------------------------------
    @classmethod
    def _bucket(cls, family: str) -> Dict[str, Type]:
        if family not in cls._registry:
            raise ValueError(f"Unknown strategy family '{family}'. Families: {list(FAMILIES)}")
        return cls._registry[family]

    @classmethod
    def register(cls, family: str, name: str):
        """
        Decorator: register ``strategy_class`` as ``name`` in ``family``.

        Example:
            @StrategyRegistry.register('swing', 'zigzag')
            class ZigZagSwingStrategy: ...

        Raises:
            ValueError: unknown family, or ``name`` already taken by a different class.
        """
        bucket = cls._bucket(family)

        def decorator(strategy_class):
            existing = bucket.get(name)
            if existing is not None and existing is not strategy_class:
                raise ValueError(
                    f"{family} strategy '{name}' is already registered as "
                    f"{existing.__module__}.{existing.__qualname__}; refusing to replace it with "
                    f"{strategy_class.__module__}.{strategy_class.__qualname__}"
                )
            bucket[name] = strategy_class
            logger.debug(f"Registered {family} strategy: {name}")
            return strategy_class

        return decorator

    @classmethod
    def get(cls, family: str, name: str, **params) -> Any:
        """
        Create a strategy instance by family and name.

        Raises:
            ValueError: unknown family or unknown name (the message lists what exists).
        """
        bucket = cls._bucket(family)
        if name not in bucket:
            raise ValueError(
                f"Unknown {family} strategy: '{name}'. Available: {list(bucket.keys())}"
            )
        return bucket[name](**params)

    @classmethod
    def list_strategies(cls, family: str) -> List[str]:
        """Registered names of one family."""
        return list(cls._bucket(family).keys())

    # ------------------------------------------------------------------
    # Family-named entry points (the documented decorators and factories)
    # ------------------------------------------------------------------
    @classmethod
    def register_swing_strategy(cls, name: str):
        """Decorator for registering a swing calculation strategy."""
        return cls.register('swing', name)

    @classmethod
    def get_swing_strategy(cls, name: str, **params):
        """Create swing strategy by name."""
        return cls.get('swing', name, **params)

    @classmethod
    def list_swing_strategies(cls) -> List[str]:
        """List available swing strategies."""
        return cls.list_strategies('swing')

    @classmethod
    def register_divergence_strategy(cls, name: str):
        """Decorator for registering a divergence calculation strategy."""
        return cls.register('divergence', name)

    @classmethod
    def get_divergence_strategy(cls, name: str, **params):
        """Create divergence strategy by name."""
        return cls.get('divergence', name, **params)

    @classmethod
    def list_divergence_strategies(cls) -> List[str]:
        """List available divergence strategies."""
        return cls.list_strategies('divergence')

    @classmethod
    def register_shape_strategy(cls, name: str):
        """Decorator for registering a shape calculation strategy."""
        return cls.register('shape', name)

    @classmethod
    def get_shape_strategy(cls, name: str, **params):
        """Create shape strategy by name."""
        return cls.get('shape', name, **params)

    @classmethod
    def list_shape_strategies(cls) -> List[str]:
        """List available shape strategies."""
        return cls.list_strategies('shape')

    @classmethod
    def register_volume_strategy(cls, name: str):
        """Decorator for registering a volume calculation strategy."""
        return cls.register('volume', name)

    @classmethod
    def get_volume_strategy(cls, name: str, **params):
        """Create volume strategy by name."""
        return cls.get('volume', name, **params)

    @classmethod
    def list_volume_strategies(cls) -> List[str]:
        """List available volume strategies."""
        return cls.list_strategies('volume')

    @classmethod
    def register_volatility_strategy(cls, name: str):
        """Decorator for registering a volatility calculation strategy."""
        return cls.register('volatility', name)

    @classmethod
    def get_volatility_strategy(cls, name: str, **params):
        """Create volatility strategy by name."""
        return cls.get('volatility', name, **params)

    @classmethod
    def list_volatility_strategies(cls) -> List[str]:
        """List available volatility strategies."""
        return cls.list_strategies('volatility')

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    @classmethod
    def list_all_strategies(cls) -> Dict[str, List[str]]:
        """Registered names grouped by family."""
        return {family: cls.list_strategies(family) for family in FAMILIES}

    @classmethod
    def get_registry_stats(cls) -> Dict[str, int]:
        """Counts of registered strategies by family, plus ``total``."""
        stats = {family: len(cls._registry[family]) for family in FAMILIES}
        stats['total'] = sum(stats.values())
        return stats


__all__ = ['StrategyRegistry', 'FAMILIES']
