"""
Zone Analysis Models - универсальные структуры данных для анализа зон.

Этот модуль содержит базовые модели данных, используемые во всей системе анализа зон:
- ZoneInfo: Информация о зоне (универсальная структура)
- ZoneAnalysisResult: Результат анализа зон

Модуль обеспечивает:
- Единообразие структур данных
- Методы сериализации/десериализации (pickle, JSON, parquet)
- Интеграцию с визуализацией
- Backward compatibility
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime
from pathlib import Path
from importlib import import_module
import pandas as pd
import pickle
import gzip
import json

from ...core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ZoneInfo:
    """
    Информация о зоне (универсальная структура).
    
    Attributes:
        zone_id: Уникальный идентификатор зоны
        type: Тип зоны ('bull', 'bear', 'overbought', 'neutral', 'oversold', ...)
        start_idx: Начальный индекс (integer location)
        end_idx: Конечный индекс (integer location)
        start_time: Время начала зоны (index value)
        end_time: Время окончания зоны (index value)
        duration: Длительность в барах
        data: DataFrame с данными зоны (OHLCV + все индикаторы)
        features: Рассчитанные признаки (заполняется после анализа)
        indicator_context: Контекст о том, как зона была обнаружена (заполняется detection strategy)
            Стандартные поля:
            - detection_strategy: str (имя стратегии)
            - detection_indicator: str (primary indicator column)
            - signal_line: Optional[str] (secondary indicator, если есть)
            - detection_rules: dict (полные rules для справки)
    
    NEW (v2.1): Добавлено поле indicator_context для хранения информации о том,
    какой индикатор использовался для detection.
    
    IMPORTANT: indicator_context заполняется DETECTION STRATEGY при создании ZoneInfo,
    НЕ pipeline/builder!
    """
    zone_id: int
    type: str
    start_idx: int
    end_idx: int
    start_time: datetime
    end_time: datetime
    duration: int
    data: pd.DataFrame
    features: Optional[Dict[str, Any]] = None
    indicator_context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Инициализация indicator_context как пустой dict если None."""
        if self.indicator_context is None:
            self.indicator_context = {}
    
    def get_primary_indicator_column(self) -> Optional[str]:
        """
        Get primary indicator column from context.
        
        Returns:
            str: Column name, or None if not available
        
        Example:
            zone = ZoneInfo(...)
            indicator_col = zone.get_primary_indicator_column()
            if indicator_col:
                values = zone.data[indicator_col]
        """
        return self.indicator_context.get('detection_indicator')
    
    def get_signal_line_column(self) -> Optional[str]:
        """
        Get signal line column from context (if exists).
        
        Returns:
            str: Signal line column name, or None if not available
        
        Example:
            zone = ZoneInfo(...)
            signal_col = zone.get_signal_line_column()
            if signal_col:
                signal_values = zone.data[signal_col]
        """
        return self.indicator_context.get('signal_line')
    
    def to_analyzer_format(self) -> Dict[str, Any]:
        """
        Формат для передачи в анализаторы.
        
        Returns:
            Словарь с данными зоны для анализаторов
        
        NOTE: Includes indicator_context for analytical strategies (v2.1)
        NOTE: Includes start_time/end_time/start_idx/end_idx for visualization (v2.1.1)
        """
        return {
            'zone_id': self.zone_id,
            'type': self.type,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'data': self.data,
            'indicator_context': self.indicator_context,  # Pass to analyzers
            **(self.features or {})
        }


@dataclass
class ZoneAnalysisResult:
    """
    Результат анализа зон.
    
    Attributes:
        zones: Список обнаруженных зон
        statistics: Статистические метрики зон
        hypothesis_tests: Результаты статистических тестов
        clustering: Результаты кластеризации (опционально)
        sequence_analysis: Анализ последовательностей зон (опционально)
        regression_results: Результаты регрессионного анализа (опционально)
        validation_results: Результаты валидации (опционально)
        data: Исходный DataFrame с данными (опционально)
        metadata: Дополнительные метаданные
    """
    zones: List[ZoneInfo]
    statistics: Dict[str, Any]
    hypothesis_tests: Dict[str, Any]
    clustering: Optional[Dict[str, Any]] = None
    sequence_analysis: Optional[Dict[str, Any]] = None
    regression_results: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    data: Optional[pd.DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save(self, 
             filepath: Union[str, Path],
             format: str = 'pickle',
             compress: bool = False,
             include_data: bool = True) -> None:
        """
        Сохранить результат анализа на диск.
        
        Args:
            filepath: Путь к файлу
            format: Формат сохранения
                - 'pickle': Бинарный формат Python (быстро, все данные)
                - 'json': Текстовый формат (читаемо, без DataFrame)
                - 'parquet': Columnar формат (компактно, все данные)
            compress: Сжимать ли данные (для pickle/parquet)
            include_data: Включать ли исходный DataFrame
            
        Example:
            # Полное сохранение с данными
            result.save('results/macd_zones.pkl')
            
            # Сжатое сохранение
            result.save('results/macd_zones.pkl.gz', compress=True)
            
            # JSON без исходных данных (легкий файл)
            result.save('results/macd_zones.json', format='json', include_data=False)
            
            # Parquet (оптимально для больших данных)
            result.save('results/macd_zones.parquet', format='parquet')
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'pickle':
            self._save_pickle(filepath, compress, include_data)
        elif format == 'json':
            self._save_json(filepath, include_data)
        elif format == 'parquet':
            self._save_parquet(filepath, compress, include_data)
        else:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported: 'pickle', 'json', 'parquet'"
            )
        
        logger.info(f"Saved ZoneAnalysisResult to {filepath} (format: {format})")
    
    def _save_pickle(self, filepath: Path, compress: bool, include_data: bool) -> None:
        """Сохранение в pickle."""
        # Временно удаляем data если не нужен
        data_backup = None
        if not include_data and self.data is not None:
            data_backup = self.data
            self.data = None
        
        try:
            if compress:
                with gzip.open(filepath.with_suffix('.pkl.gz'), 'wb') as f:
                    pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with open(filepath, 'wb') as f:
                    pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        finally:
            # Восстанавливаем data
            if data_backup is not None:
                self.data = data_backup
    
    def _save_json(self, filepath: Path, include_data: bool) -> None:
        """Сохранение в JSON."""
        data_dict = self.to_dict(include_data=include_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, default=str, ensure_ascii=False)
    
    def _save_parquet(self, filepath: Path, compress: bool, include_data: bool) -> None:
        """Сохранение в Parquet (набор файлов)."""
        # Создаем директорию для набора файлов
        output_dir = filepath.with_suffix('.parquet')
        output_dir.mkdir(exist_ok=True)
        
        # Сохраняем зоны
        zones_data = [self._zone_to_dict(z) for z in self.zones]
        zones_df = pd.DataFrame(zones_data)
        zones_df.to_parquet(output_dir / 'zones.parquet', compression='gzip' if compress else None)
        
        # Сохраняем метаданные и результаты анализа
        metadata = {
            'statistics': self.statistics,
            'hypothesis_tests': self.hypothesis_tests,
            'clustering': self.clustering,
            'sequence_analysis': self.sequence_analysis,
            'regression_results': self.regression_results,
            'validation_results': self.validation_results,
            'metadata': self.metadata
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        # Сохраняем исходные данные
        if include_data and self.data is not None:
            self.data.to_parquet(output_dir / 'data.parquet', compression='gzip' if compress else None)
    
    @classmethod
    def load(cls, 
             filepath: Union[str, Path],
             format: str = 'pickle') -> 'ZoneAnalysisResult':
        """
        Загрузить результат анализа из файла.
        
        Args:
            filepath: Путь к файлу
            format: Формат файла
            
        Returns:
            ZoneAnalysisResult
            
        Example:
            # Загрузка pickle
            result = ZoneAnalysisResult.load('results/macd_zones.pkl')
            
            # Загрузка сжатого pickle
            result = ZoneAnalysisResult.load('results/macd_zones.pkl.gz')
            
            # Загрузка JSON
            result = ZoneAnalysisResult.load('results/macd_zones.json', format='json')
            
            # Продолжение работы
            fig = result.visualize('overview')
            print(f"Loaded {len(result.zones)} zones")
        """
        filepath = Path(filepath)
        
        if format == 'pickle':
            result = cls._load_pickle(filepath)
        elif format == 'json':
            result = cls._load_json(filepath)
        elif format == 'parquet':
            result = cls._load_parquet(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Loaded ZoneAnalysisResult from {filepath} (format: {format})")
        return result
    
    @classmethod
    def _load_pickle(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Загрузка из pickle."""
        # Автоопределение сжатия
        if filepath.suffix == '.gz' or filepath.name.endswith('.pkl.gz'):
            with gzip.open(filepath, 'rb') as f:
                return pickle.load(f)
        else:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
    
    @classmethod
    def _load_json(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Загрузка из JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
        
        return cls.from_dict(data_dict)
    
    @classmethod
    def _load_parquet(cls, filepath: Path) -> 'ZoneAnalysisResult':
        """Загрузка из Parquet."""
        parquet_dir = filepath.with_suffix('.parquet')
        
        # Загружаем зоны
        zones_df = pd.read_parquet(parquet_dir / 'zones.parquet')
        zones = [cls._zone_from_dict(row.to_dict()) for _, row in zones_df.iterrows()]
        
        # Загружаем метаданные
        with open(parquet_dir / 'metadata.json', 'r') as f:
            metadata = json.load(f)
        
        # Загружаем исходные данные если есть
        data_file = parquet_dir / 'data.parquet'
        data = pd.read_parquet(data_file) if data_file.exists() else None
        
        return cls(
            zones=zones,
            statistics=metadata['statistics'],
            hypothesis_tests=metadata['hypothesis_tests'],
            clustering=metadata.get('clustering'),
            sequence_analysis=metadata.get('sequence_analysis'),
            regression_results=metadata.get('regression_results'),
            validation_results=metadata.get('validation_results'),
            data=data,
            metadata=metadata.get('metadata', {})
        )
    
    def to_dict(self, include_data: bool = False) -> Dict[str, Any]:
        """
        Конвертация в словарь (для JSON).
        
        Args:
            include_data: Включать ли DataFrame (warning: может быть большим)
        """
        result = {
            'zones': [self._zone_to_dict(z) for z in self.zones],
            'statistics': self.statistics,
            'hypothesis_tests': self.hypothesis_tests,
            'clustering': self.clustering,
            'sequence_analysis': self.sequence_analysis,
            'regression_results': self.regression_results,
            'validation_results': self.validation_results,
            'metadata': self.metadata
        }
        
        if include_data and self.data is not None:
            # Конвертируем DataFrame в dict (будет большой!)
            result['data'] = self.data.to_dict('records')
        
        return result
    
    @classmethod
    def from_dict(cls, data_dict: Dict[str, Any]) -> 'ZoneAnalysisResult':
        """Создание из словаря."""
        zones = [cls._zone_from_dict(z) for z in data_dict['zones']]
        
        # Восстанавливаем DataFrame если есть
        data = None
        if 'data' in data_dict and data_dict['data']:
            data = pd.DataFrame(data_dict['data'])
        
        return cls(
            zones=zones,
            statistics=data_dict['statistics'],
            hypothesis_tests=data_dict['hypothesis_tests'],
            clustering=data_dict.get('clustering'),
            sequence_analysis=data_dict.get('sequence_analysis'),
            regression_results=data_dict.get('regression_results'),
            validation_results=data_dict.get('validation_results'),
            data=data,
            metadata=data_dict.get('metadata', {})
        )
    
    @staticmethod
    def _zone_to_dict(zone: ZoneInfo) -> Dict[str, Any]:
        """Конвертация ZoneInfo в словарь."""
        return {
            'zone_id': zone.zone_id,
            'type': zone.type,
            'start_idx': zone.start_idx,
            'end_idx': zone.end_idx,
            'start_time': zone.start_time.isoformat(),
            'end_time': zone.end_time.isoformat(),
            'duration': zone.duration,
            'features': zone.features,
            'indicator_context': zone.indicator_context  # v2.1: Save indicator context
            # data не сохраняем в dict (слишком большой)
        }
    
    @staticmethod
    def _zone_from_dict(zone_dict: Dict[str, Any]) -> ZoneInfo:
        """Создание ZoneInfo из словаря."""
        return ZoneInfo(
            zone_id=zone_dict['zone_id'],
            type=zone_dict['type'],
            start_idx=zone_dict['start_idx'],
            end_idx=zone_dict['end_idx'],
            start_time=datetime.fromisoformat(zone_dict['start_time']),
            end_time=datetime.fromisoformat(zone_dict['end_time']),
            duration=zone_dict['duration'],
            data=pd.DataFrame(),  # Пустой DataFrame, нужно загружать отдельно
            features=zone_dict.get('features'),
            indicator_context=zone_dict.get('indicator_context')  # v2.1: Load indicator context
        )
    
    def visualize(self,
                  mode: str = 'overview',
                  zone_id: Optional[int] = None,
                  date_range: Optional[Tuple[datetime, datetime]] = None,
                  symbol: Optional[str] = None,
                  timeframe: Optional[str] = None,
                  source: Optional[str] = None,
                  **kwargs):
        """Создать визуализацию по сохранённому результату анализа зон.

        Параметры полностью повторяют интерактивные примеры из
        :mod:`docs.user_guide.zone_analysis`, поэтому готовые сценарии из
        руководства можно запускать непосредственно на экземпляре
        :class:`ZoneAnalysisResult`.

        Args:
            mode: Режим визуализации. Поддерживаются режимы ``'overview'``
                (обзор всех зон на графике цены), ``'detail'`` (детальный
                просмотр одной зоны), ``'comparison'`` (сравнение нескольких
                зон) и ``'statistics'`` (анализ агрегированной статистики).
            zone_id: Идентификатор зоны, обязательный для ``mode='detail'``.
            date_range: Необязательный диапазон дат для ``mode='comparison'``.
            **kwargs: Дополнительные параметры визуализации. Специальные ключи
                ``backend`` и ``visualizer_config`` используются при создании
                :class:`~bquant.visualization.zones.ZoneVisualizer`, остальные
                аргументы проксируются в целевой метод визуализатора.

        Returns:
            Объект графика (Plotly или Matplotlib в зависимости от выбранного
            backend визуализатора).

        Raises:
            ImportError: Если модуль визуализации недоступен или отсутствуют
                дополнительные зависимости.
            ValueError: При отсутствии требуемых данных или зон.

        Examples:
            >>> result.visualize('overview', title='Zones vs Price')
            >>> result.visualize('detail', zone_id=3, context_bars=20)
            >>> result.visualize('comparison', max_zones=5)
            >>> result.visualize('statistics', title='Zone Metrics')
        """
        try:
            visualization_module = import_module('bquant.visualization')
            ZoneVisualizer = getattr(visualization_module, 'ZoneVisualizer')
        except (ImportError, AttributeError):
            try:
                zones_module = import_module('bquant.visualization.zones')
                ZoneVisualizer = getattr(zones_module, 'ZoneVisualizer')
            except (ImportError, AttributeError) as exc:
                raise ImportError(
                    "ZoneVisualizer is not available. Install optional "
                    "visualization dependencies (e.g. 'bquant[viz]') "
                    "to enable chart rendering."
                ) from exc

        if self.data is None or self.data.empty:
            raise ValueError("data not available in ZoneAnalysisResult")

        if not self.zones and mode in {'overview', 'detail', 'comparison', 'statistics'}:
            raise ValueError("zones data is empty - nothing to visualize")

        visualizer_backend = kwargs.pop('backend', None)
        visualizer_config = kwargs.pop('visualizer_config', {})
        visualizer_kwargs = {**visualizer_config}
        if visualizer_backend is not None:
            visualizer_kwargs['backend'] = visualizer_backend

        visualizer = ZoneVisualizer(**visualizer_kwargs)
        
        # Собираем метаинформацию из параметров или metadata
        chart_info = {}
        if symbol or self.metadata.get('symbol'):
            chart_info['symbol'] = symbol or self.metadata.get('symbol')
        if timeframe or self.metadata.get('timeframe'):
            chart_info['timeframe'] = timeframe or self.metadata.get('timeframe')
        if source or self.metadata.get('source'):
            chart_info['source'] = source or self.metadata.get('source')
        
        # Передаем chart_info в kwargs для visualizer
        if chart_info:
            kwargs['chart_info'] = chart_info

        if mode == 'overview':
            # Поддержка date_range для режима overview
            if date_range is not None:
                start_date, end_date = date_range
                # Фильтруем данные по датам
                filtered_data = self.data[
                    (self.data.index >= start_date) & (self.data.index <= end_date)
                ]
                # Фильтруем зоны, которые реально пересекаются с диапазоном данных
                # Зона должна НАЧАТЬСЯ до конца диапазона И ЗАКОНЧИТЬСЯ после начала диапазона
                # Исключаем зоны которые заканчиваются ДО ИЛИ РОВНО в начале диапазона
                filtered_zones = [
                    z for z in self.zones
                    if z.start_time < end_date and z.end_time > start_date
                ]
                return visualizer.plot_zones_on_price_chart(
                    filtered_data, filtered_zones, **kwargs
                )
            else:
                return visualizer.plot_zones_on_price_chart(
                    self.data, self.zones, **kwargs
                )

        if mode == 'detail':
            if zone_id is None:
                raise ValueError("zone_id required for detail mode")
            zone = next((z for z in self.zones if z.zone_id == zone_id), None)
            if zone is None:
                raise ValueError(f"Zone {zone_id} not found")
            return visualizer.plot_zone_detail(self.data, zone, **kwargs)

        if mode == 'comparison':
            return visualizer.plot_zones_comparison(
                self.data, self.zones, date_range=date_range, **kwargs
            )

        if mode == 'statistics':
            if not self.statistics:
                raise ValueError("statistics data is empty - cannot build visualization")
            return visualizer.plot_zones_analysis(
                self.zones, self.statistics, **kwargs
            )

        raise ValueError(
            f"Unknown mode: {mode}. "
            f"Available: 'overview', 'detail', 'comparison', 'statistics'"
        )


# Экспорт
__all__ = [
    'ZoneInfo',
    'ZoneAnalysisResult'
]

