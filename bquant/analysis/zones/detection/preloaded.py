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


@ZoneDetectionRegistry.register(
    'preloaded',
    description='Import zones from external data source (CSV, DataFrame)',
    supported_zones=['any'],
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
            min_duration=2,
            zone_types=['any'],
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
        config.validate(required_rules=['zones_data'])
        
        zones_data = config.rules['zones_data']
        time_tolerance = config.rules.get('time_tolerance', '1min')
        
        # Загрузить зоны
        zones_df = self._load_zones(zones_data)
        
        # Валидация колонок
        required_cols = ['zone_id', 'type', 'start_time', 'end_time']
        missing = [c for c in required_cols if c not in zones_df.columns]
        if missing:
            raise ValueError(f"Missing required columns in zones data: {missing}")
        
        # Объединить с OHLCV
        zones = []
        for _, zone_row in zones_df.iterrows():
            zone_info = self._merge_zone_with_ohlcv(
                zone_row, data, time_tolerance
            )
            
            if zone_info and zone_info.duration >= config.min_duration:
                if zone_info.type in config.zone_types or 'any' in config.zone_types:
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
                         time_tolerance: str = '1min',
                         min_duration: int = 2) -> List[ZoneInfo]:
    """
    Helper function для загрузки готовых зон.
    
    Args:
        zones_path: Путь к CSV/Excel с зонами
        ohlcv_data: DataFrame с OHLCV данными
        time_tolerance: Допуск времени для мержа
        min_duration: Минимальная длительность зоны
        
    Returns:
        List[ZoneInfo]
        
    Example:
        zones = load_preloaded_zones('expert_zones.csv', df)
        analyzer = UniversalZoneAnalyzer()
        result = analyzer.analyze_zones(zones, df)
    """
    detector = PreloadedZonesDetection()
    config = ZoneDetectionConfig(
        min_duration=min_duration,
        zone_types=['any'],
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

