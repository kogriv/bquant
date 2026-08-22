#!/usr/bin/env python3
"""
Скрипт для извлечения sample данных из исходных CSV файлов
и генерации embedded Python структур.

Usage:
    python scripts/data/extract_samples.py --extract-all
    python scripts/data/extract_samples.py --dataset tv_xauusd_1h --source "path/to/source.csv"
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bquant.core.logging_config import get_logger

logger = get_logger(__name__)


class SampleDataExtractor:
    """
    Класс для извлечения sample данных из исходных CSV файлов
    и генерации embedded Python структур.
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.SampleDataExtractor")
        self.project_root = project_root
        self.samples_dir = self.project_root / "bquant" / "data" / "samples"
        self.embedded_dir = self.samples_dir / "embedded"
        
        # Конфигурация источников данных
        self.data_sources = {
            'tv_xauusd_1h': {
                'name': 'TradingView XAUUSD 1H',
                'description': 'Часовые данные XAUUSD с техническими индикаторами',
                'source': 'TradingView via OANDA',
                'symbol': 'XAUUSD',
                'timeframe': '1H',
                # Placeholder: the raw file lives outside the repo. Override with
                # --source / custom_source when regenerating the embedded sample.
                'source_file': 'data/raw/OANDA_XAUUSD, 60.csv',
                'rows': 1000,
                'license': 'Open data, free for research and educational use',
                'disclaimer': 'For demonstration purposes only. Not for production trading.'
            },
            'mt_xauusd_m15': {
                'name': 'MetaTrader XAUUSD 15M',
                'description': '15-минутные данные XAUUSD с базовыми метриками',
                'source': 'MetaTrader',
                'symbol': 'XAUUSD',
                'timeframe': '15M',
                # Placeholder: see the note above.
                'source_file': 'data/raw/XAUUSDM15.csv',
                'rows': 1000,
                'license': 'Open data, free for research and educational use',
                'disclaimer': 'For demonstration purposes only. Not for production trading.'
            }
        }
    
    def extract_sample_data(self, dataset_name: str, custom_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Извлечь sample данные из исходного CSV файла.
        
        Args:
            dataset_name: Название датасета ('tv_xauusd_1h' или 'mt_xauusd_m15')
            custom_source: Пользовательский путь к источнику (опционально)
        
        Returns:
            Словарь с извлеченными данными и метаданными
        """
        if dataset_name not in self.data_sources:
            raise ValueError(f"Unknown dataset: {dataset_name}. Available: {list(self.data_sources.keys())}")
        
        config = self.data_sources[dataset_name]
        source_file = custom_source or config['source_file']
        
        self.logger.info(f"Extracting sample data for {dataset_name} from {source_file}")
        
        # Проверяем существование источника
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        # Читаем CSV файл с автоматическим определением кодировки
        try:
            # Сначала пытаемся UTF-8
            try:
                df = pd.read_csv(source_file, encoding='utf-8')
            except UnicodeDecodeError:
                # Затем пытаемся UTF-16 (для некоторых MetaTrader файлов)
                try:
                    df = pd.read_csv(source_file, encoding='utf-16')
                    self.logger.info("Used utf-16 encoding")
                except UnicodeDecodeError:
                    # Затем пытаемся Windows-1251 (для других MetaTrader файлов)
                    try:
                        df = pd.read_csv(source_file, encoding='windows-1251')
                        self.logger.info("Used windows-1251 encoding")
                    except UnicodeDecodeError:
                        # Наконец пытаемся latin-1 (универсальная кодировка)
                        df = pd.read_csv(source_file, encoding='latin-1')
                        self.logger.info("Used latin-1 encoding")
            
            self.logger.info(f"Loaded {len(df)} rows from source file")
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV file: {e}")
        
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
        metadata = self._create_metadata(config, sample_df, dataset_name)
        
        return {
            'metadata': metadata,
            'data': data_list,
            'original_rows': len(df),
            'extracted_rows': len(sample_df)
        }
    
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
        
        # Нормализуем названия колонок
        df_normalized = df.copy()
        df_normalized.columns = self._normalize_column_names(df.columns, dataset_name)
        
        data_list = []
        
        for idx, row in df_normalized.iterrows():
            record = {}
            
            for column, value in row.items():
                # Конвертируем значения в подходящие типы
                typed_value = self._convert_value_type(value, column)
                record[column] = typed_value
            
            data_list.append(record)
        
        self.logger.info(f"Successfully converted {len(data_list)} records")
        return data_list
    
    def _normalize_column_names(self, columns: List[str], dataset_name: str) -> List[str]:
        """
        Нормализовать названия колонок для consistency.
        
        Args:
            columns: Исходные названия колонок
            dataset_name: Название датасета
        
        Returns:
            Нормализованные названия колонок
        """
        normalized = []
        
        # Специальная обработка для MetaTrader файлов
        if dataset_name == 'mt_xauusd_m15':
            # MetaTrader стандартные колонки: Date Time, Open, High, Low, Close, Volume, Spread
            if len(columns) >= 7:
                expected_columns = ['time', 'open', 'high', 'low', 'close', 'volume', 'spread']
                return expected_columns[:len(columns)]
        
        for col in columns:
            # Общие нормализации
            normalized_col = col.lower().strip()
            
            # Специфические замены
            replacements = {
                'accumulation/distribution': 'accumulation_distribution',
                'rsi-based ma': 'rsi_based_ma',
                'regular bullish': 'regular_bullish',
                'regular bullish label': 'regular_bullish_label', 
                'regular bearish': 'regular_bearish',
                'regular bearish label': 'regular_bearish_label'
            }
            
            for old, new in replacements.items():
                if normalized_col == old:
                    normalized_col = new
                    break
            
            # Заменяем пробелы и специальные символы на подчеркивания
            normalized_col = normalized_col.replace(' ', '_').replace('/', '_').replace('-', '_')
            
            normalized.append(normalized_col)
        
        return normalized
    
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
    
    def _create_metadata(self, config: Dict[str, Any], df: pd.DataFrame, dataset_name: str) -> Dict[str, Any]:
        """
        Создать метаданные для датасета.
        
        Args:
            config: Конфигурация источника
            df: DataFrame с данными
            dataset_name: Название датасета
        
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
            'extracted_from': config['source_file']
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
    
    def generate_embedded_file(self, dataset_name: str, extracted_data: Dict[str, Any]) -> str:
        """
        Сгенерировать Python файл с embedded данными.
        
        Args:
            dataset_name: Название датасета
            extracted_data: Извлеченные данные
        
        Returns:
            Путь к созданному файлу
        """
        self.logger.info(f"Generating embedded file for {dataset_name}")
        
        # Создаем папку если не существует
        self.embedded_dir.mkdir(parents=True, exist_ok=True)
        
        # Путь к выходному файлу
        output_file = self.embedded_dir / f"{dataset_name}.py"
        
        # Генерируем содержимое файла
        file_content = self._generate_file_content(dataset_name, extracted_data)
        
        # Записываем файл
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        self.logger.info(f"Generated embedded file: {output_file}")
        self.logger.info(f"File size: {os.path.getsize(output_file)} bytes")
        
        return str(output_file)
    
    def _generate_file_content(self, dataset_name: str, extracted_data: Dict[str, Any]) -> str:
        """
        Сгенерировать содержимое Python файла с embedded данными.
        
        Args:
            dataset_name: Название датасета
            extracted_data: Извлеченные данные
        
        Returns:
            Содержимое Python файла
        """
        metadata = extracted_data['metadata']
        data = extracted_data['data']
        
        # Создаем заголовок файла (без персональных данных)
        source_filename = os.path.basename(metadata['extracted_from'])
        header = f'''"""
Embedded sample data for {metadata['name']}

Auto-generated from original {metadata['source']} dataset
Generated on: {metadata['updated']}
Rows: {metadata['rows']}
Source: {metadata['source']}

DO NOT EDIT THIS FILE MANUALLY!
Use scripts/data/extract_samples.py to regenerate.
"""

from typing import Dict, List, Any

'''
        
        # Метаданные (удаляем персональные пути)
        metadata_safe = metadata.copy()
        if 'extracted_from' in metadata_safe:
            # Оставляем только имя файла, без полного пути
            metadata_safe['extracted_from'] = os.path.basename(metadata_safe['extracted_from'])
        
        metadata_section = f'''DATASET_INFO = {repr(metadata_safe)}

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
    
    def extract_all_datasets(self) -> Dict[str, str]:
        """
        Извлечь все настроенные датасеты.
        
        Returns:
            Словарь: dataset_name -> путь к сгенерированному файлу
        """
        self.logger.info("Extracting all configured datasets")
        
        results = {}
        
        for dataset_name in self.data_sources.keys():
            try:
                self.logger.info(f"Processing dataset: {dataset_name}")
                
                # Извлекаем данные
                extracted_data = self.extract_sample_data(dataset_name)
                
                # Генерируем embedded файл
                output_file = self.generate_embedded_file(dataset_name, extracted_data)
                
                results[dataset_name] = output_file
                
                self.logger.info(f"Successfully processed {dataset_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to process {dataset_name}: {e}")
                raise
        
        self.logger.info(f"Successfully extracted {len(results)} datasets")
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
            source_file = config['source_file']
            exists = os.path.exists(source_file)
            results[dataset_name] = exists
            
            if exists:
                size = os.path.getsize(source_file) / (1024 * 1024)  # MB
                self.logger.info(f"✓ {dataset_name}: {source_file} ({size:.1f} MB)")
            else:
                self.logger.warning(f"✗ {dataset_name}: {source_file} - file not found")
        
        return results


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description="Extract sample data from source CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/data/extract_samples.py --extract-all
  python scripts/data/extract_samples.py --dataset tv_xauusd_1h
  python scripts/data/extract_samples.py --validate-sources
        """
    )
    
    parser.add_argument(
        '--extract-all',
        action='store_true',
        help='Extract all configured datasets'
    )
    
    parser.add_argument(
        '--dataset',
        type=str,
        help='Extract specific dataset (tv_xauusd_1h or mt_xauusd_m15)'
    )
    
    parser.add_argument(
        '--source',
        type=str,
        help='Custom source file path (use with --dataset)'
    )
    
    parser.add_argument(
        '--validate-sources',
        action='store_true',
        help='Validate that all source files exist'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    extractor = SampleDataExtractor()
    
    try:
        if args.validate_sources:
            print("Validating source files...")
            results = extractor.validate_source_files()
            
            all_valid = all(results.values())
            
            print("\nValidation Results:")
            for dataset, valid in results.items():
                status = "✓" if valid else "✗"
                print(f"  {status} {dataset}")
            
            if all_valid:
                print("\n🎉 All source files are available!")
                return 0
            else:
                print("\n⚠️  Some source files are missing!")
                return 1
        
        elif args.extract_all:
            print("Extracting all datasets...")
            results = extractor.extract_all_datasets()
            
            print("\nExtraction Results:")
            for dataset, file_path in results.items():
                print(f"  ✓ {dataset} -> {file_path}")
            
            print(f"\n🎉 Successfully extracted {len(results)} datasets!")
            return 0
        
        elif args.dataset:
            print(f"Extracting dataset: {args.dataset}")
            
            extracted_data = extractor.extract_sample_data(args.dataset, args.source)
            output_file = extractor.generate_embedded_file(args.dataset, extracted_data)
            
            print(f"\nExtracted {extracted_data['extracted_rows']} rows from {extracted_data['original_rows']} total")
            print(f"Generated: {output_file}")
            print("\n🎉 Extraction completed successfully!")
            return 0
        
        else:
            parser.print_help()
            return 1
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
