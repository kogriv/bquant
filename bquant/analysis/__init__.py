"""
Модуль анализа данных BQuant

Этот модуль содержит различные виды анализа финансовых данных:
- Статистический анализ
- Анализ зон
- Технический анализ 
- Анализ свечей
- Временной анализ
- Графический анализ
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

import pandas as pd
from pandas.api.types import is_dict_like

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Версия модуля анализа
__version__ = "0.0.0"

# Поддерживаемые виды анализа
SUPPORTED_ANALYSIS_TYPES = {
    'statistical': 'Статистический анализ данных и гипотез',
    'zones': 'Анализ зон и паттернов',
    'technical': 'Технический анализ индикаторов',
    'chart': 'Графический анализ и паттерны',
    'candlestick': 'Анализ свечных паттернов',
    'timeseries': 'Временной анализ данных'
}


class AnalysisResult:
    """
    Базовый класс для результатов анализа.
    
    Attributes:
        analysis_type: Тип проведенного анализа
        timestamp: Время проведения анализа
        data_size: Размер анализируемых данных
        results: Словарь с результатами анализа
        metadata: Дополнительные метаданные
    """
    
    def __init__(self, analysis_type: str, results: Dict[str, Any], 
                 data_size: int = 0, metadata: Optional[Dict[str, Any]] = None):
        """
        Инициализация результата анализа.
        
        Args:
            analysis_type: Тип анализа
            results: Результаты анализа
            data_size: Размер данных
            metadata: Дополнительные метаданные
        """
        self.analysis_type = analysis_type
        self.timestamp = datetime.now()
        self.data_size = data_size
        self.results = results or {}
        self.metadata = metadata or {}
        
        logger.debug(f"Created {analysis_type} analysis result with {data_size} data points")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертация результата в словарь.
        
        Returns:
            Словарь с результатами анализа
        """
        return {
            'analysis_type': self.analysis_type,
            'timestamp': self.timestamp.isoformat(),
            'data_size': self.data_size,
            'results': self.results,
            'metadata': self.metadata
        }
    
    def save_to_csv(self, file_path: str) -> None:
        """
        Сохранение результатов в CSV файл.
        
        Args:
            file_path: Путь к файлу для сохранения
        """
        try:
            # Пытаемся конвертировать результаты в DataFrame
            if isinstance(self.results, dict) and self.results:
                # Если результаты можно представить как табличные данные
                try:
                    df = pd.DataFrame(self.results)
                except ValueError:
                    # Поддержка словарей со скалярными значениями
                    df = pd.DataFrame([self.results])

                if df.empty:
                    df = pd.DataFrame([self.results])

                # Нормализуем вложенные словари (например, статистики)
                if any(is_dict_like(value) for value in self.results.values()):
                    normalized = pd.json_normalize(self.results)
                    if not normalized.empty:
                        df = normalized

                df.to_csv(file_path, index=False)
                logger.info(f"Analysis results saved to {file_path}")
            else:
                # Сохраняем как простую структуру
                data = self.to_dict()
                df = pd.DataFrame([data])
                df.to_csv(file_path, index=False)
                logger.info(f"Analysis metadata saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save analysis results to CSV: {e}")
            raise
    
    def __str__(self) -> str:
        """Строковое представление результата."""
        return f"AnalysisResult({self.analysis_type}, {self.data_size} points, {self.timestamp})"
    
    def __repr__(self) -> str:
        """Детальное представление результата."""
        return (f"AnalysisResult(type='{self.analysis_type}', "
                f"data_size={self.data_size}, "
                f"results_keys={list(self.results.keys())}, "
                f"timestamp='{self.timestamp}')")


class BaseAnalyzer:
    """
    Базовый класс для всех анализаторов BQuant.
    
    Обеспечивает общий интерфейс и функциональность для различных видов анализа.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация базового анализатора.
        
        Args:
            name: Имя анализатора
            config: Конфигурация анализатора
        """
        self.name = name
        self.config = config or {}
        self.logger = get_logger(f"{__name__}.{name}")
        
        self.logger.info(f"Initialized {name} analyzer")
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Валидация входных данных.
        
        Args:
            data: DataFrame с данными для анализа
        
        Returns:
            True если данные корректны
        """
        if data is None or data.empty:
            self.logger.error("Data is None or empty")
            return False
        
        if len(data) < self.config.get('min_data_points', 10):
            self.logger.error(f"Insufficient data points: {len(data)} < {self.config.get('min_data_points', 10)}")
            return False
        
        return True
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
        """
        Основной метод анализа. Должен быть переопределен в дочерних классах.
        
        Args:
            data: DataFrame с данными для анализа
            **kwargs: Дополнительные параметры
        
        Returns:
            AnalysisResult с результатами анализа
        """
        raise NotImplementedError("analyze method must be implemented in subclass")
    
    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Подготовка данных перед анализом.
        
        Args:
            data: Исходные данные
        
        Returns:
            Подготовленные данные
        """
        # Базовая подготовка - просто копируем данные
        prepared_data = data.copy()
        
        # Сортируем по индексу если это временные данные
        if isinstance(prepared_data.index, pd.DatetimeIndex):
            prepared_data = prepared_data.sort_index()
        
        self.logger.debug(f"Prepared {len(prepared_data)} data points for analysis")
        return prepared_data


def get_available_analyzers() -> Dict[str, str]:
    """
    Получить список доступных анализаторов.
    
    Returns:
        Словарь {анализатор: описание}
    """
    analyzers = {}
    
    # Статистические анализаторы
    try:
        from .statistical import get_statistical_analyzers
        analyzers.update(get_statistical_analyzers())
    except ImportError:
        logger.debug("Statistical analyzers not available")
    
    # Зональные анализаторы
    try:
        from .zones import get_zone_analyzers
        analyzers.update(get_zone_analyzers())
    except ImportError:
        logger.debug("Zone analyzers not available")
    
    # Технические анализаторы
    try:
        from .technical import get_technical_analyzers
        analyzers.update(get_technical_analyzers())
    except ImportError:
        logger.debug("Technical analyzers not available")
    
    # Свечные анализаторы
    try:
        from .candlestick import get_candlestick_analyzers
        analyzers.update(get_candlestick_analyzers())
    except ImportError:
        logger.debug("Candlestick analyzers not available")
    
    # Временные анализаторы
    try:
        from .timeseries import get_timeseries_analyzers
        analyzers.update(get_timeseries_analyzers())
    except ImportError:
        logger.debug("Timeseries analyzers not available")
    
    # Графические анализаторы
    try:
        from .chart import get_chart_analyzers
        analyzers.update(get_chart_analyzers())
    except ImportError:
        logger.debug("Chart analyzers not available")
    
    return analyzers


def create_analyzer(analyzer_type: str, **kwargs) -> BaseAnalyzer:
    """
    Фабрика для создания анализаторов.
    
    Args:
        analyzer_type: Тип анализатора
        **kwargs: Параметры для анализатора
    
    Returns:
        Экземпляр анализатора
    """
    # Здесь будет реализована фабрика анализаторов
    # Пока возвращаем базовый анализатор
    logger.info(f"Creating {analyzer_type} analyzer")
    
    if analyzer_type not in SUPPORTED_ANALYSIS_TYPES:
        raise ValueError(f"Unsupported analyzer type: {analyzer_type}")
    
    # Возвращаем базовый анализатор как заглушку
    return BaseAnalyzer(analyzer_type, kwargs)


# Ленивый импорт подмодулей для избежания циклических зависимостей
def __getattr__(name: str):
    """Ленивый импорт подмодулей."""
    import importlib
    
    if name == 'statistical':
        return importlib.import_module('.statistical', __name__)
    elif name == 'zones':
        return importlib.import_module('.zones', __name__)
    elif name == 'technical':
        return importlib.import_module('.technical', __name__)
    elif name == 'chart':
        return importlib.import_module('.chart', __name__)
    elif name == 'candlestick':
        return importlib.import_module('.candlestick', __name__)
    elif name == 'timeseries':
        return importlib.import_module('.timeseries', __name__)
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Экспорт основных классов и функций
__all__ = [
    'AnalysisResult',
    'BaseAnalyzer', 
    'get_available_analyzers',
    'create_analyzer',
    'SUPPORTED_ANALYSIS_TYPES',
    '__version__'
]