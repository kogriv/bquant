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

from typing import Any, ClassVar, Dict, List, Optional
from datetime import datetime

import pandas as pd
from pandas.api.types import is_dict_like

from ..core.logging_config import get_logger

logger = get_logger(__name__)

# Версия модуля анализа
# Версия — одна на пакет. Свой литерал здесь разъезжался с пакетом молча:
# восемь модулей объявляли собственную версию, четыре из них застряли на
# "0.0.0" при пакете 0.0.9, и `get_visualization_info()` выдавал этот ноль
# наружу как факт (G33).
from bquant import __version__  # noqa: F401

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

    #: Заглушка ли это — разметка под будущую работу, а не рабочий анализатор.
    #:
    #: Признак объявляется **свойством**, а не прозой. До 0.0.10 «заглушка»
    #: была написана в четырёх местах словами (докстрока модуля, докстрока
    #: класса, строка описания в перечне) и один раз машиночитаемо — в
    #: ``metadata['implementation_status']`` результата, то есть узнать это
    #: можно было, **только вызвав** ``analyze()``. У класса не было ни одного
    #: атрибута, по которому программа отличила бы заглушку от рабочего
    #: анализатора (G31).
    #:
    #: Тот же принцип, что вывели на G20 и применяли в G8: закрыто то, на чём
    #: дискриминирует универсальный код; открыто то, что придумывает предметная
    #: область. Статус реализации — не предметная область.
    #:
    #: Заглушка обязана возвращать ``implementation_status: 'stub'``; обратное
    #: тоже обязано выполняться, и на это стоит пин
    #: (``tests/unit/test_a_stub_says_so.py``), поэтому снять маркер, не сняв
    #: заглушечность, — и наоборот — не выйдет молча.
    is_stub: ClassVar[bool] = False

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



def mark_if_stub(analyzer_cls, descriptions: Dict[str, str]) -> Dict[str, str]:
    """Пометить перечень модуля как заглушечный, если его анализатор — заглушка.

    Суффикс «(заглушка)» раньше был вписан в каждую строку описания руками.
    Это второй литерал того же факта: реализуют анализатор — снимают маркер, а
    двадцать строк описаний остаются со старым словом, и перечень начинает
    врать в другую сторону. Теперь суффикс **выводится** из
    :attr:`BaseAnalyzer.is_stub` (G31).
    """
    if not getattr(analyzer_cls, "is_stub", False):
        return dict(descriptions)
    return {key: f"{text} (заглушка)" for key, text in descriptions.items()}


def get_available_analyzers() -> Dict[str, str]:
    """
    Имена, которые принимает :func:`create_analyzer`, и что каждое означает.

    Вопрос, на который отвечает эта функция, — «что я могу передать фабрике».
    Поэтому она **выводится** из ``SUPPORTED_ANALYSIS_TYPES``, а не собирается
    отдельным списком.

    Так было не всегда: до 0.0.10 она объединяла шесть модульных перечней и
    объявляла 24 имени, из которых фабрика принимала 5 — и ни одно из четырёх
    зональных (``zone``, ``support_resistance``, ``macd_zones``,
    ``price_action``) не принималось. Два утверждения по отдельности были
    зелёными, ложной была их конъюнкция, и сверять их было нечем (G32).

    Модульные перечни (``get_zone_analyzers`` и другие) никуда не делись, но
    отвечают на **другой** вопрос — какие виды анализа покрывает модуль. Их
    ключи не предназначены для фабрики.

    Returns:
        Словарь {имя для create_analyzer: описание}
    """
    return dict(SUPPORTED_ANALYSIS_TYPES)


def create_analyzer(analyzer_type: str, **kwargs) -> BaseAnalyzer:
    """
    Создать анализатор по имени из :func:`get_available_analyzers`.

    **Что именно возвращается.** Сейчас это :class:`BaseAnalyzer` с проставленным
    именем и конфигом, а не специализированный класс: собственный ``analyze()``
    есть у ``StatisticalAnalyzer`` и у четырёх заглушек, но фабрика их пока не
    строит. Написано здесь прямо, потому что имя ``create_analyzer('statistical')``
    обещает больше, чем делает, и молчание об этом уже стоило пакету
    рассогласования каталога и фабрики (G32).

    Для анализа зон фабрика — не тот вход: пользуйтесь
    :func:`bquant.analysis.zones.analyze_zones`.

    Args:
        analyzer_type: Имя из :func:`get_available_analyzers`
        **kwargs: Параметры, которые лягут в ``config`` анализатора

    Returns:
        Экземпляр :class:`BaseAnalyzer`

    Raises:
        ValueError: если имя не из списка поддерживаемых
    """
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