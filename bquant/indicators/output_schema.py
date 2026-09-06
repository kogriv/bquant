"""Схема выходного кадра индикатора.

До G64 (2026-09-06) :class:`IndicatorSchema` лежала в ``bquant.data.schemas`` и при
создании импортировала фабрику индикаторов: слой данных, чтобы описать кадр, загружал
слой индикаторов (и с ним внешние библиотеки). Схема спрашивает колонки у самого
индикатора — значит, она принадлежит индикаторам. ``bquant.data.schemas`` знает только
``ohlcv``; :func:`bquant.data.schemas.validate_with_schema` принимает экземпляр этой
схемы вместо имени.
"""

from __future__ import annotations

from ..data.schemas import DataSchema


class IndicatorSchema(DataSchema):
    """
    Схема выходов технического индикатора.

    Обязательные поля **спрашиваются у самого индикатора**
    (:meth:`get_output_columns`), а не перечисляются здесь литералами.
    """
    
    def __init__(self, indicator_name: str):
        """
        Initialize indicator schema.
        
        Args:
            indicator_name: Name of the indicator ('macd', 'rsi', etc.)
        """
        super().__init__('indicators')
        self.indicator_name = indicator_name
        
        # Define schemas for different indicators
        self._setup_indicator_schema()
    
    #: Имя схемы → имя индикатора в фабрике. Схема больше не перечисляет колонки
    #: литералами: это было **третье** место, где живут имена выходов (после
    #: самого индикатора и его потребителей), и оно расходилось бы с ними при
    #: любой правке. Теперь колонки спрашиваются у индикатора, который их и
    #: производит. Разбор: ``devref/gaps/columns/``.
    _INDICATOR_ALIASES = {
        'macd': 'macd',
        'rsi': 'rsi',
        'bollinger_bands': 'bbands',
    }

    def _setup_indicator_schema(self):
        """Setup schema from the indicator's own declared output columns."""
        factory_name = self._INDICATOR_ALIASES.get(self.indicator_name)
        if factory_name is None:
            self.logger.debug(
                "No schema known for indicator '%s'; leaving it unconstrained",
                self.indicator_name,
            )
            return

        try:
            from .base import IndicatorFactory
            indicator = IndicatorFactory.create('custom', factory_name)
            columns = indicator.get_output_columns()
        except Exception as exc:  # pragma: no cover - factory unavailable
            self.logger.warning(
                "Could not read output columns of '%s' (%s); schema left "
                "unconstrained rather than restating names that may be stale",
                factory_name, exc,
            )
            return

        for column in columns:
            self.add_required_field(column, float)

        if self.indicator_name == 'rsi':
            for column in columns:
                self.add_validation_rule(column, lambda x: 0 <= x <= 100)


#: Готовые схемы: колонки взяты у индикаторов с параметрами по умолчанию.
MACD_SCHEMA = IndicatorSchema('macd')
RSI_SCHEMA = IndicatorSchema('rsi')

__all__ = ["IndicatorSchema", "MACD_SCHEMA", "RSI_SCHEMA"]
