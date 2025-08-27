"""
Генератор embedded sample данных для BQuant

Этот модуль предоставляет функционал для создания embedded Python файлов
из исходных CSV данных с использованием loader.py и config.py.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ...core.logging_config import get_logger
from ...core.config import get_data_path, validate_timeframe
from ..loader import load_ohlcv_data

logger = get_logger(__name__)


class SampleDataGenerator:
    """
    Генератор embedded sample данных.
    
    Создает Python файлы с embedded данными из исходных CSV файлов,
    используя loader.py для загрузки и config.py для путей.
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.SampleDataGenerator")
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.embedded_dir = self.project_root / "bquant" / "data" / "samples" / "embedded"
        
        # Конфигурация источников данных (использует config.py)
        self.data_sources = {
            'tv_xauusd_1h': {
                'name': 'TradingView XAUUSD 1H',
                'description': 'Часовые данные XAUUSD с техническими индикаторами',
                'source': 'TradingView via OANDA',
                'symbol': 'XAUUSD',
                'timeframe': '1h',
                'data_source': 'tradingview',
                'quote_provider': 'oanda',
                'rows': 1000,
                'license': 'Open data, free for research and educational use',
                'disclaimer': 'For demonstration purposes only. Not for production trading.'
            },
            'mt_xauusd_m15': {
                'name': 'MetaTrader XAUUSD 15M',
                'description': '15-минутные данные XAUUSD с базовыми метриками',
                'source': 'MetaTrader',
                'symbol': 'XAUUSD',
                'timeframe': '15m',
                'data_source': 'metatrader',
                'quote_provider': 'default',
                'rows': 1000,
                'license': 'Open data, free for research and educational use',
                'disclaimer': 'For demonstration purposes only. Not for production trading.'
            }
        }
    
    def generate_embedded_data(self, dataset_name: str, custom_source: Optional[str] = None) -> str:
        """
        Создать embedded файл для указанного датасета.
        
        Args:
            dataset_name: Название датасета ('tv_xauusd_1h' или 'mt_xauusd_m15')
            custom_source: Пользовательский путь к источнику (опционально)
        
        Returns:
            Путь к созданному embedded файлу
        
        Raises:
            ValueError: Если датасет не найден
            FileNotFoundError: Если исходный файл не найден
        """
        if dataset_name not in self.data_sources:
            raise ValueError(f"Unknown dataset: {dataset_name}. Available: {list(self.data_sources.keys())}")
        
        config = self.data_sources[dataset_name]
        
        # Определяем путь к исходному файлу
        if custom_source:
            source_file = Path(custom_source)
        else:
            # Используем config.py для получения пути
            source_file = get_data_path(
                config['symbol'],
                config['timeframe'],
                config['data_source'],
                config['quote_provider']
            )
        
        self.logger.info(f"Generating embedded data for {dataset_name} from {source_file}")
        
        # Проверяем существование источника
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        # Загружаем данные используя loader.py
        try:
            df = load_ohlcv_data(source_file, config['symbol'], config['timeframe'])
            self.logger.info(f"Loaded {len(df)} rows from source file")
        except Exception as e:
            raise RuntimeError(f"Failed to load data from {source_file}: {e}")
        
        # Берем последние N строк
        rows_to_extract = config['rows']
        if len(df) < rows_to_extract:
            self.logger.warning(f"Source has only {len(df)} rows, less than requested {rows_to_extract}")
            rows_to_extract = len(df)
        
        sample_df = df.tail(rows_to_extract).copy()
        self.logger.info(f"Extracted {len(sample_df)} rows")
        
        # Конвертируем в список словарей с типизацией
        data_list = self._convert_to_typed_dicts(sample_df, dataset_name)
        
        # Создаем метаданные
        metadata = self._create_metadata(config, sample_df, dataset_name, source_file)
        
        # Генерируем embedded файл
        output_file = self._generate_embedded_file(dataset_name, metadata, data_list)
        
        return str(output_file)
    
    def generate_all(self) -> Dict[str, str]:
        """
        Создать embedded файлы для всех настроенных датасетов.
        
        Returns:
            Словарь: dataset_name -> путь к созданному файлу
        """
        self.logger.info("Generating embedded data for all configured datasets")
        
        results = {}
        
        for dataset_name in self.data_sources.keys():
            try:
                self.logger.info(f"Processing dataset: {dataset_name}")
                
                output_file = self.generate_embedded_data(dataset_name)
                results[dataset_name] = output_file
                
                self.logger.info(f"Successfully processed {dataset_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to process {dataset_name}: {e}")
                raise
        
        self.logger.info(f"Successfully generated {len(results)} embedded files")
        return results
    
    def validate_source_files(self) -> Dict[str, bool]:
        """
        Проверить доступность всех исходных файлов.
        
        Returns:
            Словарь: dataset_name -> файл существует
        """
        self.logger.info("Validating source files")
        
        results = {}
        
        for dataset_name, config in self.data_sources.items():
            try:
                source_file = get_data_path(
                    config['symbol'],
                    config['timeframe'],
                    config['data_source'],
                    config['quote_provider']
                )
                exists = source_file.exists()
                results[dataset_name] = exists
                
                if exists:
                    size = source_file.stat().st_size / (1024 * 1024)  # MB
                    self.logger.info(f"✓ {dataset_name}: {source_file} ({size:.1f} MB)")
                else:
                    self.logger.warning(f"✗ {dataset_name}: {source_file} - file not found")
                    
            except Exception as e:
                self.logger.error(f"✗ {dataset_name}: Error checking file - {e}")
                results[dataset_name] = False
        
        return results
    
    def _convert_to_typed_dicts(self, df: pd.DataFrame, dataset_name: str) -> List[Dict[str, Any]]:
        """
        Конвертировать DataFrame в список типизированных словарей.
        
        Args:
            df: DataFrame с данными
            dataset_name: Название датасета для специфической обработки
        
        Returns:
            Список словарей с типизированными значениями
        """
        self.logger.info(f"Converting {len(df)} rows to typed dictionaries")
        
        data_list = []
        
        for idx, row in df.iterrows():
            record = {}
            
            for column, value in row.items():
                # Конвертируем значения в подходящие типы
                typed_value = self._convert_value_type(value, column)
                record[column] = typed_value
            
            data_list.append(record)
        
        self.logger.info(f"Successfully converted {len(data_list)} records")
        return data_list
    
    def _convert_value_type(self, value: Any, column: str) -> Any:
        """
        Конвертировать значение в подходящий тип.
        
        Args:
            value: Исходное значение
            column: Название колонки
        
        Returns:
            Типизированное значение
        """
        # NaN и None
        if pd.isna(value) or value is None:
            return None
        
        # Время остается строкой
        if column in ['time', 'timestamp', 'date']:
            return str(value)
        
        # Числовые значения
        if isinstance(value, (int, float, np.integer, np.floating)):
            if np.isnan(value):
                return None
            # Конвертируем в float для consistency
            return float(value)
        
        # Строковые значения
        if isinstance(value, str):
            # Пытаемся конвертировать числовые строки
            try:
                float_val = float(value)
                return float_val
            except (ValueError, TypeError):
                # Оставляем как строку
                return str(value)
        
        # Остальное как есть
        return value
    
    def _create_metadata(self, config: Dict[str, Any], df: pd.DataFrame, dataset_name: str, source_file: Path) -> Dict[str, Any]:
        """
        Создать метаданные для датасета.
        
        Args:
            config: Конфигурация источника
            df: DataFrame с данными
            dataset_name: Название датасета
            source_file: Путь к исходному файлу
        
        Returns:
            Словарь с метаданными
        """
        # Определяем временной диапазон
        time_column = self._identify_time_column(df.columns)
        period_start = None
        period_end = None
        
        if time_column and len(df) > 0:
            try:
                period_start = str(df[time_column].iloc[0])
                period_end = str(df[time_column].iloc[-1])
            except Exception as e:
                self.logger.warning(f"Could not determine time period: {e}")
        
        metadata = {
            'name': config['name'],
            'description': config['description'],
            'source': config['source'],
            'symbol': config['symbol'],
            'timeframe': config['timeframe'],
            'rows': len(df),
            'columns': df.columns.tolist(),
            'period_start': period_start,
            'period_end': period_end,
            'license': config['license'],
            'disclaimer': config['disclaimer'],
            'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'extracted_from': source_file.name  # Только имя файла, без полного пути
        }
        
        return metadata
    
    def _identify_time_column(self, columns: List[str]) -> Optional[str]:
        """
        Определить колонку с временными данными.
        
        Args:
            columns: Список названий колонок
        
        Returns:
            Название временной колонки или None
        """
        time_patterns = ['time', 'timestamp', 'date', 'datetime']
        
        for col in columns:
            if any(pattern in col.lower() for pattern in time_patterns):
                return col
        
        return None
    
    def _generate_embedded_file(self, dataset_name: str, metadata: Dict[str, Any], data: List[Dict[str, Any]]) -> Path:
        """
        Сгенерировать Python файл с embedded данными.
        
        Args:
            dataset_name: Название датасета
            metadata: Метаданные датасета
            data: Данные в виде списка словарей
        
        Returns:
            Путь к созданному файлу
        """
        self.logger.info(f"Generating embedded file for {dataset_name}")
        
        # Создаем папку если не существует
        self.embedded_dir.mkdir(parents=True, exist_ok=True)
        
        # Путь к выходному файлу
        output_file = self.embedded_dir / f"{dataset_name}.py"
        
        # Генерируем содержимое файла
        file_content = self._generate_file_content(dataset_name, metadata, data)
        
        # Записываем файл
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        self.logger.info(f"Generated embedded file: {output_file}")
        self.logger.info(f"File size: {output_file.stat().st_size} bytes")
        
        return output_file
    
    def _generate_file_content(self, dataset_name: str, metadata: Dict[str, Any], data: List[Dict[str, Any]]) -> str:
        """
        Сгенерировать содержимое Python файла с embedded данными.
        
        Args:
            dataset_name: Название датасета
            metadata: Метаданные датасета
            data: Данные в виде списка словарей
        
        Returns:
            Содержимое Python файла
        """
        # Создаем заголовок файла
        header = f'''"""
Embedded sample data for {metadata['name']}

Auto-generated from original {metadata['source']} dataset
Generated on: {metadata['updated']}
Rows: {metadata['rows']}
Source: {metadata['source']}

DO NOT EDIT THIS FILE MANUALLY!
Use bquant.data.samples.generator.SampleDataGenerator to regenerate.
"""

from typing import Dict, List, Any

'''
        
        # Метаданные
        metadata_section = f'''DATASET_INFO = {repr(metadata)}

'''
        
        # Данные (разбиваем на части для читаемости)
        data_header = "DATA = [\n"
        data_footer = "]\n"
        
        data_entries = []
        for record in data:
            # Форматируем каждую запись
            formatted_record = "    {\n"
            for key, value in record.items():
                formatted_value = repr(value)
                formatted_record += f"        '{key}': {formatted_value},\n"
            formatted_record += "    },"
            data_entries.append(formatted_record)
        
        # Объединяем все части
        data_section = data_header + "\n".join(data_entries) + "\n" + data_footer
        
        # Финальное содержимое
        content = header + metadata_section + data_section
        
        return content


# Экспорт для удобства
__all__ = ['SampleDataGenerator']
