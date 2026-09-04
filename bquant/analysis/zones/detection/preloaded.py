"""
Preloaded Zones Detection Strategy

Стратегия импорта готовых зон из внешних источников.

Применение:
- Импорт зон из торговых систем (MT5, cTrader)
- Зоны, размеченные экспертами
- Результаты ML моделей
"""

import pandas as pd
from typing import List, Union
from pathlib import Path

from .base import ZoneDetectionStrategy, ZoneDetectionConfig
from .registry import ZoneDetectionRegistry
from ..models import ZoneInfo
from bquant.core.logging_config import get_logger
from bquant.data.processor import resolve_time_index


@ZoneDetectionRegistry.register(
    'preloaded',
    description='Import zones from external data source (CSV, DataFrame)',
    # Словарь определяется во время выполнения — типы приходят из импортируемых
    # данных. Потребители читают ZoneVocabulary.is_declared и не фильтруют.
    supported_zones=None,
    required_rules=['zones_data']
)
class PreloadedZonesDetection:
    """
    Стратегия: импорт готовых зон из внешних источников.
    
    Применение:
        - Импорт зон из торговых систем (MT5, cTrader)
        - Зоны, размеченные экспертами
        - Результаты ML моделей
        
    Правила (config.rules):
        - zones_data: str | Path | pd.DataFrame (обязательно)
        - time_tolerance: str (опционально, default='1min') - допуск времени для мержа
        
    Формат внешних зон (CSV/DataFrame):
        - zone_id: int - уникальный ID
        - type: str - тип зоны
        - start_time: datetime - начало зоны
        - end_time: datetime - конец зоны
    
    Example:
        # From CSV
        strategy = PreloadedZonesDetection()
        config = ZoneDetectionConfig(
            rules={'zones_data': 'expert_zones.csv'}
        )
        zones = strategy.detect_zones(ohlcv_data, config)
        
        # From DataFrame
        zones_df = pd.DataFrame({
            'zone_id': [0, 1],
            'type': ['bull', 'bear'],
            'start_time': ['2024-01-01 00:00', '2024-01-01 10:00'],
            'end_time': ['2024-01-01 09:00', '2024-01-01 19:00']
        })
        config = ZoneDetectionConfig(
            rules={'zones_data': zones_df}
        )
        zones = strategy.detect_zones(ohlcv_data, config)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def detect_zones(self, 
                     data: pd.DataFrame,
                     config: ZoneDetectionConfig) -> List[ZoneInfo]:
        """Загрузить и объединить готовые зоны с OHLCV данными."""
        config.validate(
            required_rules=['zones_data'],
            optional_rules=['time_tolerance'],
        )
        
        zones_data = config.rules['zones_data']
        time_tolerance = config.rules.get('time_tolerance', '1min')
        
        # Загрузить зоны
        zones_df = self._load_zones(zones_data)
        
        # Валидация колонок
        required_cols = ['zone_id', 'type', 'start_time', 'end_time']
        missing = [c for c in required_cols if c not in zones_df.columns]
        if missing:
            raise ValueError(f"Missing required columns in zones data: {missing}")

        # The pipeline puts time on the index before the data reaches a detector
        # (G30). load_preloaded_zones() hands the caller's frame over directly, and
        # the bundled samples carry time as a column — so resolve it here too, or
        # the merge below compares timestamps against positions inside pandas.
        data = resolve_time_index(data)
        self._require_comparable_clock(zones_df, data)

        # Объединить с OHLCV
        zones = []
        for _, zone_row in zones_df.iterrows():
            zone_info = self._merge_zone_with_ohlcv(
                zone_row, data, time_tolerance
            )
            
            if zone_info:
                # `'any'` больше не нужен: словарь этой стратегии определяется
                # импортируемыми данными, и `zone_types=None` означает «не
                # фильтровать» напрямую, без имени-заглушки, которым ни одна зона
                # в действительности не помечена.
                if config.accepts(zone_info.type):
                    zones.append(zone_info)
        
        self.logger.info(f"Loaded {len(zones)} preloaded zones")
        
        return zones
    
    def _load_zones(self, zones_data: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
        """Загрузить зоны из файла или DataFrame."""
        if isinstance(zones_data, pd.DataFrame):
            return zones_data.copy()
        
        # Загрузка из файла
        path = Path(zones_data)
        if not path.exists():
            raise FileNotFoundError(f"Zones file not found: {path}")
        
        if path.suffix == '.csv':
            df = pd.read_csv(path, parse_dates=['start_time', 'end_time'])
        elif path.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path, parse_dates=['start_time', 'end_time'])
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        return df
    
    @staticmethod
    def _require_comparable_clock(zones_df: pd.DataFrame, ohlcv: pd.DataFrame) -> None:
        """Отказать сразу, если границы зон и ось данных живут в разных системах.

        `analyze_zones()` ставит время на индекс сам (`resolve_time_index`, G30),
        а `zones_data` приходит от вызывающего в его собственных координатах. Кто
        построил границы по позиционному индексу исходного кадра — как это делал
        наш же e2e-тест, беря `df.index[10]` у кадра со временем в **колонке**, —
        получал `Timestamp(10)`, то есть 1970 год, и сравнение падало внутри
        pandas сообщением про tz-naive и tz-aware. Сообщение верное и бесполезное:
        оно называет следствие, а причина в том, что переданы позиции, а не время.
        """
        if not isinstance(ohlcv.index, pd.DatetimeIndex):
            # The mirror case: timestamps for the zones, positions for the data.
            # resolve_time_index() has already run and found no time column, so
            # there is nothing on the data side to compare a timestamp against.
            for column in ('start_time', 'end_time'):
                if pd.api.types.is_datetime64_any_dtype(zones_df[column]):
                    raise ValueError(
                        f"zones_data['{column}'] holds timestamps, but the data has no "
                        f"time axis: its index is {ohlcv.index.dtype} and no time column "
                        f"was recognised. Put the time on the index or in a 'time' column."
                    )
            return

        for column in ('start_time', 'end_time'):
            values = zones_df[column]
            if pd.api.types.is_datetime64_any_dtype(values):
                continue
            raise ValueError(
                f"zones_data['{column}'] has dtype {values.dtype}, but the data is "
                f"indexed by time ({ohlcv.index.dtype}). Zone boundaries must be "
                f"timestamps on the same clock as the data. If you built them from "
                f"a positional index, take the time column instead — for the bundled "
                f"samples that is df['time'], not df.index."
            )

    def _merge_zone_with_ohlcv(self, 
                                zone_row: pd.Series, 
                                ohlcv: pd.DataFrame,
                                time_tolerance: str) -> ZoneInfo:
        """Объединить зону с OHLCV данными по времени."""
        start_time = pd.Timestamp(zone_row['start_time'])
        end_time = pd.Timestamp(zone_row['end_time'])
        
        # Найти индексы с допуском времени
        mask = (ohlcv.index >= start_time - pd.Timedelta(time_tolerance)) & \
               (ohlcv.index <= end_time + pd.Timedelta(time_tolerance))
        
        zone_data = ohlcv[mask].copy()
        
        if zone_data.empty:
            self.logger.warning(
                f"No OHLCV data found for zone {zone_row['zone_id']} "
                f"({start_time} - {end_time})"
            )
            return None
        
        return ZoneInfo(
            zone_id=int(zone_row['zone_id']),
            type=str(zone_row['type']),
            start_idx=ohlcv.index.get_loc(zone_data.index[0]),
            end_idx=ohlcv.index.get_loc(zone_data.index[-1]),
            start_time=zone_data.index[0],
            end_time=zone_data.index[-1],
            duration=len(zone_data),
            data=zone_data,
            indicator_context={
                'detection_strategy': 'preloaded',
                'detection_indicator': zone_row.get('indicator', 'external'),
                'signal_line': None,
                'source': 'external',
                'detection_rules': {'preloaded': True}
            }
        )


def load_preloaded_zones(zones_path: Union[str, Path],
                         ohlcv_data: pd.DataFrame,
                         time_tolerance: str = '1min') -> List[ZoneInfo]:
    """
    Helper function для загрузки готовых зон.

    Args:
        zones_path: Путь к CSV/Excel с зонами
        ohlcv_data: DataFrame с OHLCV данными
        time_tolerance: Допуск времени для мержа

    Returns:
        List[ZoneInfo] — все зоны, какие есть в файле. Отсев коротких — дело
        стадии анализа (``analyze_zones(..., min_duration=N)``), которая
        сообщает, что исключила; здесь читатель ничего не выбрасывает.

    Example:
        zones = load_preloaded_zones('expert_zones.csv', df)
        analyzer = UniversalZoneAnalyzer()
        result = analyzer.analyze_zones(zones, df)
    """
    detector = PreloadedZonesDetection()
    config = ZoneDetectionConfig(
        # Фильтра нет: словарь типов приходит из импортируемых данных.
        zone_types=None,
        rules={
            'zones_data': zones_path,
            'time_tolerance': time_tolerance
        },
        strategy_name='preloaded'
    )
    
    return detector.detect_zones(ohlcv_data, config)


# Экспорт
__all__ = [
    'PreloadedZonesDetection',
    'load_preloaded_zones'
]

