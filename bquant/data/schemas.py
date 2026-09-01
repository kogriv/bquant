"""
Data schemas for BQuant

Схемы данных: какие поля обязательны, каких типов и каким правилам обязаны
удовлетворять их значения. Схема умеет проверить кадр (`validate_dataframe`)
и объяснить отказ.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

from ..core.logging_config import get_logger


@dataclass
class OHLCVRecord:
    """
    Schema for a single OHLCV record.
    
    Attributes:
        timestamp: Record timestamp
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume (optional)
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    
    def validate(self) -> bool:
        """
        Validate OHLCV record consistency.
        
        Returns:
            True if record is valid
        """
        # Basic price validation
        if any(price <= 0 for price in [self.open, self.high, self.low, self.close]):
            return False
        
        # OHLC relationship validation
        if self.high < self.low:
            return False
        
        if self.high < max(self.open, self.close):
            return False
        
        if self.low > min(self.open, self.close):
            return False
        
        # Volume validation
        if self.volume is not None and self.volume < 0:
            return False
        
        return True


@dataclass
class DataSourceConfig:
    """
    Configuration for data sources.
    
    Attributes:
        name: Data source name
        file_pattern: File naming pattern
        timeframe_mapping: Timeframe mappings
        quote_providers: Available quote providers
    """
    name: str
    file_pattern: str
    timeframe_mapping: Dict[str, str]
    quote_providers: List[str]


@dataclass
class DataValidationResult:
    """
    Result of data validation.
    
    Attributes:
        is_valid: Whether data passed validation
        issues: List of critical issues
        warnings: List of warnings
        stats: Validation statistics
        recommendations: List of recommendations
    """
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    recommendations: List[str]


class DataSchema:
    """
    Базовый класс схем данных.

    Несёт перечень обязательных и опциональных полей, их типы и правила для
    значений; :meth:`validate_dataframe` проверяет кадр по всему этому разом.
    """
    
    def __init__(self, schema_type: str):
        """
        Initialize data schema.
        
        Args:
            schema_type: Type of schema ('ohlcv', 'indicators', 'analysis')
        """
        self.schema_type = schema_type
        self.required_fields = []
        self.optional_fields = []
        self.field_types = {}
        self.validation_rules = {}
        self.logger = get_logger(f"{__name__}.{schema_type}")

    def validate_dataframe(self, df: pd.DataFrame) -> DataValidationResult:
        """
        Проверить кадр по схеме: обязательные поля, типы и правила.

        До 2026-09-01 здесь стояла заглушка, безусловно возвращавшая
        ``is_valid=True`` — на любом кадре, включая пустой и не содержащий ни
        одного объявленного поля. Схема ``macd`` требует три колонки, которых у
        встроенного сэмпла нет, и всё равно объявляла его валидным (G42).
        Признание «не реализовано» стояло в ``recommendations``, то есть в поле,
        которое никто не читает, когда вердикт уже получен.

        Args:
            df: кадр для проверки

        Returns:
            DataValidationResult: вердикт, перечень проблем и статистика
        """
        issues: List[str] = []
        warnings: List[str] = []

        present = set(df.columns)
        missing = [field for field in self.required_fields if field not in present]
        if missing:
            issues.append(f"Missing required fields: {missing}")

        absent_optional = [f for f in self.optional_fields if f not in present]

        type_mismatches = []
        checked_fields = [f for f in self.required_fields + self.optional_fields
                          if f in present]
        for field in checked_fields:
            expected = self.field_types.get(field)
            if expected in (float, int) and not pd.api.types.is_numeric_dtype(df[field]):
                type_mismatches.append(f"{field}: expected {expected.__name__}, "
                                       f"got {df[field].dtype}")
        if type_mismatches:
            issues.append(f"Field type mismatches: {type_mismatches}")

        rule_violations: Dict[str, int] = {}
        for field, rules in self.validation_rules.items():
            if field not in present:
                continue
            values = df[field].dropna()
            if values.empty:
                warnings.append(f"Rules for '{field}' not applied: no values to check")
                continue
            for rule in rules:
                try:
                    failed = int((~values.map(rule).astype(bool)).sum())
                except Exception as exc:
                    warnings.append(f"Rule for '{field}' could not be applied: {exc}")
                    continue
                if failed:
                    rule_violations[field] = rule_violations.get(field, 0) + failed
        if rule_violations:
            issues.append(f"Values violating field rules: {rule_violations}")

        recommendations = []
        if missing:
            recommendations.append(f"Add the missing columns or pick another schema: {missing}")
        if type_mismatches:
            recommendations.append("Convert the listed columns to a numeric dtype")
        if rule_violations:
            recommendations.append("Inspect the rows violating field rules before analysis")

        return DataValidationResult(
            is_valid=not issues,
            issues=issues,
            warnings=warnings,
            stats={
                'rows': len(df),
                'columns': len(df.columns),
                'schema_type': self.schema_type,
                'required_fields': list(self.required_fields),
                'checked_fields': checked_fields,
                'missing_required': missing,
                'absent_optional': absent_optional,
                'rule_violations': rule_violations,
            },
            recommendations=recommendations
        )
    
    def add_required_field(self, field_name: str, field_type: type):
        """Add required field to schema."""
        self.required_fields.append(field_name)
        self.field_types[field_name] = field_type
    
    def add_optional_field(self, field_name: str, field_type: type):
        """Add optional field to schema."""
        self.optional_fields.append(field_name)
        self.field_types[field_name] = field_type
    
    def add_validation_rule(self, field_name: str, rule: callable):
        """Add validation rule for field."""
        if field_name not in self.validation_rules:
            self.validation_rules[field_name] = []
        self.validation_rules[field_name].append(rule)


class OHLCVSchema(DataSchema):
    """
    Схема OHLCV: цены обязательны и положительны, объём опционален и неотрицателен.
    """
    
    def __init__(self):
        """Initialize OHLCV schema."""
        super().__init__('ohlcv')
        
        # Define required fields
        self.add_required_field('open', float)
        self.add_required_field('high', float)
        self.add_required_field('low', float)
        self.add_required_field('close', float)
        
        # Define optional fields
        self.add_optional_field('volume', float)
        
        # Add validation rules
        self.add_validation_rule('open', lambda x: x > 0)
        self.add_validation_rule('high', lambda x: x > 0)
        self.add_validation_rule('low', lambda x: x > 0)
        self.add_validation_rule('close', lambda x: x > 0)
        self.add_validation_rule('volume', lambda x: x >= 0 if x is not None else True)


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
            from ..indicators import IndicatorFactory
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


# Предопределенные схемы
OHLCV_SCHEMA = OHLCVSchema()
MACD_SCHEMA = IndicatorSchema('macd')
RSI_SCHEMA = IndicatorSchema('rsi')

# Словарь доступных схем
AVAILABLE_SCHEMAS = {
    'ohlcv': OHLCV_SCHEMA,
    'macd': MACD_SCHEMA,
    'rsi': RSI_SCHEMA
}


def get_schema(schema_name: str) -> Optional[DataSchema]:
    """
    Get predefined schema by name.
    
    Args:
        schema_name: Name of the schema
    
    Returns:
        DataSchema object or None if not found
    """
    return AVAILABLE_SCHEMAS.get(schema_name)


def validate_with_schema(df: pd.DataFrame, schema_name: str) -> DataValidationResult:
    """
    Validate DataFrame with predefined schema.
    
    Args:
        df: DataFrame to validate
        schema_name: Name of the schema to use
    
    Returns:
        DataValidationResult object
    """
    schema = get_schema(schema_name)
    if schema is None:
        return DataValidationResult(
            is_valid=False,
            issues=[f"Schema '{schema_name}' not found"],
            warnings=[],
            stats={},
            recommendations=[f"Available schemas: {list(AVAILABLE_SCHEMAS.keys())}"]
        )
    
    return schema.validate_dataframe(df)


# Экспорт для использования
__all__ = [
    'OHLCVRecord',
    'DataSourceConfig',
    'DataValidationResult',
    'DataSchema',
    'OHLCVSchema',
    'IndicatorSchema',
    'OHLCV_SCHEMA',
    'MACD_SCHEMA',
    'RSI_SCHEMA',
    'get_schema',
    'validate_with_schema'
]
