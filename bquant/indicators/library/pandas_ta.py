"""Pandas-TA Loader for BQuant.

This module integrates pandas-ta indicators with the IndicatorFactory by
discovering all callable indicators dynamically and generating lightweight
wrappers for them. The goal is to avoid handwritten wrappers for every
indicator and keep the available indicator list in sync with what pandas-ta
exposes.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd

from ..base import IndicatorFactory, IndicatorResult, LibraryIndicator
from ...core.exceptions import IndicatorCalculationError
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class PandasTALoader:
    """Загрузчик индикаторов из библиотеки pandas-ta."""

    _indicators_registered: bool = False
    _available_indicators: List[str] = []
    _ta_module: Optional[Any] = None
    _function_cache: Dict[str, Callable] = {}

    _PRICE_PARAM_COLUMNS: Dict[str, str] = {
        "open": "open",
        "open_": "open",
        "high": "high",
        "high_": "high",
        "low": "low",
        "low_": "low",
        "close": "close",
        "close_": "close",
        "volume": "volume",
        "volume_": "volume",
        "source": "close",
    }

    @classmethod
    def is_available(cls) -> bool:
        """Проверить доступность pandas-ta."""

        try:
            import pandas_ta  # noqa: F401  (lazy import check)

            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    @classmethod
    def _load_module(cls):
        if cls._ta_module is None:
            import pandas_ta as ta

            cls._ta_module = ta
        return cls._ta_module

    @classmethod
    def _discover_all_functions(cls) -> Dict[str, Callable]:
        """Обнаружить все публичные функции pandas-ta."""

        if not cls.is_available():
            return {}

        ta = cls._load_module()
        functions: Dict[str, Callable] = {}

        for attr_name in dir(ta):
            if attr_name.startswith("_"):
                continue

            attr = getattr(ta, attr_name, None)
            if not callable(attr):
                continue

            module_name = getattr(attr, "__module__", "")
            if not module_name.startswith("pandas_ta"):
                # Ограничиваемся реальными индикаторами библиотеки.
                continue

            functions[attr_name] = attr

        cls._function_cache = functions
        cls._available_indicators = sorted(functions.keys())
        # Переводим на DEBUG, чтобы не засорять консоль при тихих профилях
        logger.debug(
            "Discovered %s pandas-ta callables", len(cls._available_indicators)
        )
        return functions

    @classmethod
    def get_available_indicators(cls) -> List[str]:
        """Получить список доступных индикаторов."""

        if not cls.is_available():
            return []

        if not cls._function_cache:
            cls._discover_all_functions()

        return cls._available_indicators.copy()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    @classmethod
    def register_indicators(cls) -> int:
        """Зарегистрировать индикаторы pandas-ta в IndicatorFactory."""

        if cls._indicators_registered:
            return len(cls._available_indicators)

        if not cls.is_available():
            logger.warning("pandas-ta is not available")
            return 0

        if not cls._function_cache:
            cls._discover_all_functions()

        registered = 0
        registered_names: List[str] = []

        for func_name, func in cls._function_cache.items():
            config = cls._analyze_function_dynamically(func_name, func)
            if config is None:
                continue

            try:
                indicator_class = cls._create_indicator_class_dynamically(
                    func_name, config
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug(
                    "Failed to create dynamic pandas-ta indicator %s: %s",
                    func_name,
                    exc,
                )
                continue

            registry_key = f"pandas_ta_{func_name}".lower()
            IndicatorFactory.register_indicator(registry_key, indicator_class)
            IndicatorFactory.register_library_function(registry_key, func)

            registered += 1
            registered_names.append(func_name)

        cls._available_indicators = sorted(registered_names)
        cls._indicators_registered = True
        # DEBUG вместо INFO для тихих профилей
        logger.debug("Registered %s pandas-ta indicators", registered)

        return registered

    # ------------------------------------------------------------------
    # Dynamic indicator analysis & generation
    # ------------------------------------------------------------------
    @classmethod
    def _analyze_function_dynamically(
        cls, func_name: str, func: Callable
    ) -> Optional[Dict[str, Any]]:
        """Собрать конфигурацию для динамического индикатора."""

        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):  # pragma: no cover - rare cases
            logger.debug("Failed to inspect signature for %s", func_name)
            return None

        price_params: List[Dict[str, Any]] = []
        unsupported_required: List[str] = []
        tunable_params: Dict[str, Any] = {}
        accepts_kwargs = False

        for param in signature.parameters.values():
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                # Сложно обработать произвольные *args автоматически.
                logger.debug("Skipping %s: unsupported *args", func_name)
                return None

            if param.kind == inspect.Parameter.VAR_KEYWORD:
                accepts_kwargs = True
                continue

            name = param.name
            column = cls._PRICE_PARAM_COLUMNS.get(name)
            if column:
                price_params.append(
                    {
                        "name": name,
                        "column": column,
                        "required": param.default is inspect._empty,
                    }
                )
                continue

            if param.default is inspect._empty:
                unsupported_required.append(name)
            else:
                tunable_params[name] = param.default

        if not price_params:
            logger.debug("Skipping %s: no price parameters detected", func_name)
            return None

        if unsupported_required:
            logger.debug(
                "Skipping %s: unsupported required params %s",
                func_name,
                unsupported_required,
            )
            return None

        output_columns = cls._determine_output_columns(
            func_name, func, price_params, tunable_params
        )
        if output_columns is None:
            return None

        description = (
            func.__doc__.strip().splitlines()[0]
            if getattr(func, "__doc__", None)
            else f"pandas-ta indicator {func_name}"
        )

        return {
            "function": func,
            "price_params": price_params,
            "tunable_params": tunable_params,
            "accepts_kwargs": accepts_kwargs,
            "output_columns": output_columns,
            "description": description,
        }

    @classmethod
    def _determine_output_columns(
        cls,
        func_name: str,
        func: Callable,
        price_params: Iterable[Dict[str, Any]],
        tunable_params: Dict[str, Any],
    ) -> Optional[List[str]]:
        """Попробовать определить названия колонок результата функции."""

        sample_data = cls._generate_sample_data()
        call_kwargs: Dict[str, Any] = {}

        for price_param in price_params:
            column = price_param["column"]
            if column not in sample_data.columns:
                if price_param["required"]:
                    logger.debug(
                        "Skipping %s: missing column '%s' in sample data",
                        func_name,
                        column,
                    )
                    return None
                call_kwargs[price_param["name"]] = None
                continue

            call_kwargs[price_param["name"]] = sample_data[column]

        # Используем значения по умолчанию только если они заданы и не None.
        for param_name, default_value in tunable_params.items():
            if default_value is not inspect._empty and default_value is not None:
                call_kwargs[param_name] = default_value

        try:
            result = func(**call_kwargs)
        except Exception as exc:
            logger.debug(
                "Skipping %s: failed to evaluate with sample data (%s)",
                func_name,
                exc,
            )
            return None

        if result is None:
            logger.debug(
                "Skipping %s: function returned None for sample data", func_name
            )
            return None

        if isinstance(result, pd.DataFrame):
            columns = list(result.columns)
            if not columns:
                columns = [f"{func_name}_value"]
            return columns

        if isinstance(result, pd.Series):
            column_name = result.name or f"{func_name}_value"
            return [column_name]

        # Поддержка scalar/iterable результатов: приводим к одной колонке.
        return [f"{func_name}_value"]

    @classmethod
    def _generate_sample_data(cls) -> pd.DataFrame:
        index = pd.date_range("2020-01-01", periods=200, freq="D")
        base = pd.Series(range(len(index)), index=index, dtype=float)

        return pd.DataFrame(
            {
                "open": base + 1.0,
                "high": base + 2.0,
                "low": base,
                "close": base + 1.5,
                "volume": (base + 1000).abs(),
            }
        )

    @classmethod
    def _create_indicator_class_dynamically(
        cls, func_name: str, config: Dict[str, Any]
    ) -> type:
        """Создать класс индикатора для функции pandas-ta."""

        base_name = f"pandas_ta_{func_name}".lower()
        class_name = "PandasTA" + "".join(
            part.capitalize() for part in func_name.split("_")
        )

        price_params = config["price_params"]
        required_columns = sorted(
            {
                param["column"]
                for param in price_params
                if param["required"] and param["column"] is not None
            }
        )
        tunable_params = config["tunable_params"]
        output_columns = config["output_columns"]
        description = config["description"]
        library_function = config["function"]

        def __init__(self, **kwargs):
            parameters = dict(tunable_params)
            parameters.update(kwargs)
            LibraryIndicator.__init__(
                self,
                base_name,
                library_function,
                parameters=parameters,
            )
            self._price_params = price_params
            self.config.columns = output_columns
            self.config.description = description

        def get_required_columns(self) -> List[str]:
            return required_columns
        
        def get_statistics(self, data: pd.DataFrame) -> pd.DataFrame:
            """Получить статистику по результатам индикатора."""
            try:
                result = self.calculate(data)
                if result.data is not None and not result.data.empty:
                    return result.data.describe()
                return pd.DataFrame()
            except Exception:
                # Если расчет не удался, возвращаем пустой DataFrame
                return pd.DataFrame()

        def calculate(self, data: pd.DataFrame, **kwargs) -> IndicatorResult:
            if not self.validate_data(data):
                raise IndicatorCalculationError(
                    f"Invalid data provided for {base_name}"
                )

            params = {**self.config.parameters, **kwargs}
            call_kwargs: Dict[str, Any] = {}

            for price_param in price_params:
                param_name = price_param["name"]
                column = price_param["column"]
                if param_name in params:
                    value = params.pop(param_name)
                elif column and column in data.columns:
                    value = data[column]
                elif price_param["required"]:
                    raise IndicatorCalculationError(
                        f"Data does not contain required column '{column}' for {base_name}"
                    )
                else:
                    value = None

                call_kwargs[param_name] = value

            call_kwargs.update(params)

            try:
                result = library_function(**call_kwargs)
            except Exception as exc:
                raise IndicatorCalculationError(
                    f"Failed to calculate {base_name}: {exc}"
                ) from exc

            if isinstance(result, pd.DataFrame):
                result_df = result.copy()
                if output_columns and len(result_df.columns) == len(output_columns):
                    result_df.columns = output_columns
            elif isinstance(result, pd.Series):
                column_name = output_columns[0] if output_columns else base_name
                result_df = result.to_frame(name=column_name)
            else:
                column_name = output_columns[0] if output_columns else base_name
                result_df = pd.DataFrame(
                    {column_name: result}, index=getattr(data, "index", None)
                )

            return IndicatorResult(
                name=base_name,
                data=result_df,
                config=self.config,
                metadata={
                    "library": "pandas_ta",
                    "function": func_name,
                    "price_parameters": [p["name"] for p in price_params],
                },
            )

        attributes = {
            "__init__": __init__,
            "calculate": calculate,
            "get_required_columns": get_required_columns,
            "get_statistics": get_statistics,
            "__module__": __name__,
        }

        return type(class_name, (LibraryIndicator,), attributes)


__all__ = ["PandasTALoader"]

