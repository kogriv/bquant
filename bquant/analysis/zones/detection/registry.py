"""
Zone Detection Registry - реестр стратегий детекции зон.

Обеспечивает:
- Автоматическую регистрацию стратегий через декоратор
- Хранение метаданных (описание, поддерживаемые зоны, обязательные параметры)
- Получение стратегий по имени
"""

from typing import Dict, Iterable, Type, List, Any, Optional, Union

from bquant.core.logging_config import get_logger
from ..models import ZoneType, ZoneVocabulary

logger = get_logger(__name__)


class ZoneDetectionRegistry:
    """
    Реестр стратегий определения зон.
    
    Автоматическая регистрация через декоратор @register().
    Поддержка метаданных для каждой стратегии.
    
    Example:
        @ZoneDetectionRegistry.register(
            'zero_crossing',
            description='Detect zones by zero line crossing',
            supported_zones=[
                ZoneType('bull', polarity=+1, counterpart='bear'),
                ZoneType('bear', polarity=-1, counterpart='bull'),
            ],
            required_rules=['indicator_col']
        )
        class ZeroCrossingDetection:
            def detect_zones(self, data, config):
                ...
    """
    
    _strategies: Dict[str, Type] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, 
                 description: str = "",
                 supported_zones: Optional[Iterable[Union[str, ZoneType]]] = None,
                 required_rules: List[str] = None):
        """
        Декоратор для регистрации стратегии.
        
        Args:
            name: Уникальное имя стратегии
            description: Человекочитаемое описание
            supported_zones: Типы зон, которые может обнаружить. Принимает как
                дескрипторы :class:`ZoneType`, так и голые строки — строка
                поднимается до дескриптора без объявленных свойств, и тогда
                универсальные слои сообщат о неприменимости направленного
                анализа вместо того, чтобы угадывать.

                ``None`` означает **словарь определяется во время выполнения**:
                у ``preloaded`` типы приходят из импортируемых данных, у
                ``combined`` — из ``zone_type_map`` вызывающего. Потребители
                читают :attr:`ZoneVocabulary.is_declared` и в этом случае не
                фильтруют, а не трактуют пустоту как пустой белый список.
            required_rules: Обязательные ключи в config.rules
            
        Example:
            @ZoneDetectionRegistry.register(
                'zero_crossing',
                description='Detect zones by indicator crossing zero line',
                supported_zones=[
                    ZoneType('bull', polarity=+1, counterpart='bear'),
                    ZoneType('bear', polarity=-1, counterpart='bull'),
                ],
                required_rules=['indicator_col']
            )
            class ZeroCrossingDetection:
                def detect_zones(self, data, config):
                    ...
        """
        def decorator(strategy_class):
            if name in cls._strategies:
                logger.warning(f"Overwriting existing strategy: {name}")
            
            vocabulary = ZoneVocabulary.coerce(supported_zones)
            
            cls._strategies[name] = strategy_class
            cls._metadata[name] = {
                'description': description,
                # Словарь — источник истины; список имён выводится из него для
                # логов и человекочитаемого вывода, отдельно не хранится.
                'zone_vocabulary': vocabulary,
                'supported_zones': vocabulary.names(),
                'required_rules': required_rules or [],
                'class': strategy_class.__name__
            }
            # Тихая регистрация по умолчанию: деталь на DEBUG
            logger.debug(f"Registered zone detection strategy: {name}")
            if not vocabulary.is_declared:
                logger.debug(
                    f"Strategy '{name}' declares no zone types statically; its "
                    "vocabulary is determined at runtime and consumers will not "
                    "filter on it."
                )
            return strategy_class
        
        return decorator
    
    @classmethod
    def get(cls, name: str, **init_params):
        """
        Получить экземпляр стратегии по имени.
        
        Args:
            name: Имя зарегистрированной стратегии
            **init_params: Параметры для __init__ стратегии (если нужны)
            
        Returns:
            Экземпляр стратегии
            
        Raises:
            ValueError: Если стратегия не найдена
        """
        if name not in cls._strategies:
            available = ', '.join(cls.list_strategies())
            raise ValueError(
                f"Unknown zone detection strategy: '{name}'. "
                f"Available: {available}"
            )
        
        strategy_class = cls._strategies[name]
        return strategy_class(**init_params)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """Список имен доступных стратегий."""
        return list(cls._strategies.keys())

    @classmethod
    def log_summary(cls) -> None:
        """Вывести сводку зарегистрированных стратегий одной строкой (INFO)."""
        strategies = ', '.join(sorted(cls.list_strategies()))
        logger.info("Zone detection strategies registered: %s", strategies)
    
    @classmethod
    def get_info(cls, name: str) -> Dict[str, Any]:
        """
        Получить метаданные стратегии.
        
        Args:
            name: Имя стратегии
            
        Returns:
            Словарь с метаданными
            
        Raises:
            ValueError: Если стратегия не найдена
        """
        if name not in cls._metadata:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._metadata[name].copy()
    
    @classmethod
    def list_all_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Получить информацию обо всех стратегиях.
        
        Returns:
            Словарь {имя_стратегии: метаданные}
        """
        return cls._metadata.copy()
    
    @classmethod
    def get_vocabulary(cls, name: str) -> ZoneVocabulary:
        """
        Словарь типов зон, объявленный стратегией.
        
        Это точка, ради которой заведён :class:`ZoneVocabulary`: универсальные
        слои спрашивают **объявленные свойства** типа (полярность, контрастную
        пару, подпись), а не сравнивают его имя со строковым литералом.
        
        Args:
            name: Имя стратегии
            
        Returns:
            Объявленный словарь. Если стратегия не объявляет типы статически
            (``preloaded``, ``combined``), возвращается пустой словарь с
            ``is_declared == False`` — это «определяется во время выполнения»,
            а не «типов нет».
            
        Raises:
            ValueError: Если стратегия не найдена
        """
        if name not in cls._metadata:
            raise ValueError(f"Unknown strategy: {name}")
        return cls._metadata[name]['zone_vocabulary']


def resolve_vocabulary(zones: Iterable[Any]) -> ZoneVocabulary:
    """Словарь типов зон, описывающий этот набор зон.

    Универсальным слоям (последовательности, статистика, визуализация) нужен не
    список имён, а объявленные свойства типов. Единственный, кто эти свойства
    знает, — стратегия детекции, и её имя зоны несут в
    ``indicator_context['detection_strategy']``.

    Порядок разрешения:

    1. Имя стратегии из контекста первой зоны, у которой оно есть, → объявленный
       словарь из реестра.
    2. Если стратегия не объявляет типы статически (``preloaded``, ``combined``)
       или неизвестна — собирается **голый** словарь из фактически встреченных
       имён, без свойств.

    Голый словарь — не отказ, а честная деградация: имена в нём есть, поэтому
    переходы и матрица считаются, а направленный анализ сообщит о неприменимости
    вместо того, чтобы угадать направление по имени.

    Args:
        zones: Зоны (``ZoneInfo``) либо словари с ключами ``indicator_context``/``type``.

    Returns:
        Словарь типов; может быть голым, но никогда не пустым при непустом входе.
    """
    zones = list(zones)

    def _field(zone, name, default=None):
        if isinstance(zone, dict):
            return zone.get(name, default)
        return getattr(zone, name, default)

    strategy_name = None
    for zone in zones:
        context = _field(zone, 'indicator_context') or {}
        strategy_name = context.get('detection_strategy')
        if strategy_name:
            break

    if strategy_name and strategy_name in ZoneDetectionRegistry._metadata:
        declared = ZoneDetectionRegistry.get_vocabulary(strategy_name)
        if declared.is_declared:
            return declared
    elif strategy_name:
        logger.debug(
            f"Zone context names an unregistered detection strategy "
            f"'{strategy_name}'; falling back to the observed type names."
        )

    observed = []
    for zone in zones:
        zone_type = _field(zone, 'type') or _field(zone, 'zone_type')
        if zone_type and zone_type not in observed:
            observed.append(zone_type)
    return ZoneVocabulary.coerce(observed)


# Экспорт
__all__ = [
    'ZoneDetectionRegistry',
    'resolve_vocabulary'
]
