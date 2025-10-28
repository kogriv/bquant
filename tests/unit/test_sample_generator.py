"""
Тесты для генератора embedded sample данных
"""

import pandas as pd
import tempfile
import os
from pathlib import Path

from bquant.data.samples import SampleDataGenerator


class TestSampleDataGenerator:
    """Тесты для SampleDataGenerator."""
    
    def test_generator_creation(self):
        """Тест создания генератора."""
        generator = SampleDataGenerator()
        
        assert generator is not None
        assert hasattr(generator, 'data_sources')
        assert 'tv_xauusd_1h' in generator.data_sources
        assert 'mt_xauusd_m15' in generator.data_sources
        
        print("[OK] test_generator_creation: SampleDataGenerator создается корректно")
    
    def test_data_sources_config(self):
        """Тест конфигурации источников данных."""
        generator = SampleDataGenerator()
        
        # Проверяем структуру конфигурации
        for dataset_name, config in generator.data_sources.items():
            required_keys = ['name', 'description', 'source', 'symbol', 'timeframe', 
                           'data_source', 'quote_provider', 'rows', 'license', 'disclaimer']
            
            for key in required_keys:
                assert key in config, f"Missing key '{key}' in dataset '{dataset_name}'"
            
            # Проверяем типы значений
            assert isinstance(config['symbol'], str)
            assert isinstance(config['timeframe'], str)
            assert isinstance(config['rows'], int)
            assert config['rows'] > 0
        
        print("[OK] test_data_sources_config: Конфигурация источников данных корректна")
    
    def test_validate_source_files(self):
        """Тест валидации исходных файлов."""
        generator = SampleDataGenerator()
        
        results = generator.validate_source_files()
        
        assert isinstance(results, dict)
        assert 'tv_xauusd_1h' in results
        assert 'mt_xauusd_m15' in results
        
        # Файлы могут не существовать в тестовой среде, но метод должен работать
        for dataset, exists in results.items():
            assert isinstance(exists, bool)
        
        print("[OK] test_validate_source_files: Валидация исходных файлов работает")
    
    def test_convert_value_type(self):
        """Тест конвертации типов значений."""
        generator = SampleDataGenerator()
        
        # Тест NaN значений
        assert generator._convert_value_type(None, 'test') is None
        assert generator._convert_value_type(float('nan'), 'test') is None
        
        # Тест временных значений
        assert generator._convert_value_type('2025-01-01', 'time') == '2025-01-01'
        
        # Тест числовых значений
        assert generator._convert_value_type(123, 'close') == 123.0
        assert generator._convert_value_type('123.45', 'volume') == 123.45
        
        # Тест строковых значений
        assert generator._convert_value_type('test_string', 'symbol') == 'test_string'
        
        print("[OK] test_convert_value_type: Конвертация типов значений работает корректно")
    
    def test_identify_time_column(self):
        """Тест определения временной колонки."""
        generator = SampleDataGenerator()
        
        # Тест с временной колонкой
        columns = ['open', 'high', 'time', 'close']
        assert generator._identify_time_column(columns) == 'time'
        
        # Тест с timestamp
        columns = ['open', 'timestamp', 'close']
        assert generator._identify_time_column(columns) == 'timestamp'
        
        # Тест без временной колонки
        columns = ['open', 'high', 'low', 'close']
        assert generator._identify_time_column(columns) is None
        
        print("[OK] test_identify_time_column: Определение временной колонки работает")
    
    def test_generate_file_content(self):
        """Тест генерации содержимого файла."""
        generator = SampleDataGenerator()
        
        # Создаем тестовые данные
        metadata = {
            'name': 'Test Dataset',
            'description': 'Test description',
            'source': 'Test Source',
            'symbol': 'TEST',
            'timeframe': '1h',
            'rows': 2,
            'columns': ['time', 'close'],
            'period_start': '2025-01-01',
            'period_end': '2025-01-02',
            'license': 'Test License',
            'disclaimer': 'Test Disclaimer',
            'updated': '2025-01-01 00:00:00',
            'extracted_from': 'test.csv'
        }
        
        data = [
            {'time': '2025-01-01T00:00:00', 'close': 100.0},
            {'time': '2025-01-01T01:00:00', 'close': 101.0}
        ]
        
        content = generator._generate_file_content('test_dataset', metadata, data)
        
        # Проверяем структуру содержимого
        assert '"""' in content  # Документация
        assert 'from typing import Dict, List, Any' in content  # Импорты
        assert 'DATASET_INFO = ' in content  # Метаданные
        assert 'DATA = [' in content  # Данные
        assert "'time': '2025-01-01T00:00:00'" in content  # Конкретные данные
        assert "'close': 100.0" in content
        
        print("[OK] test_generate_file_content: Генерация содержимого файла работает")
    
    def test_generate_embedded_file(self):
        """Тест генерации embedded файла."""
        generator = SampleDataGenerator()
        
        # Создаем тестовые данные
        metadata = {
            'name': 'Test Dataset',
            'description': 'Test description',
            'source': 'Test Source',
            'symbol': 'TEST',
            'timeframe': '1h',
            'rows': 1,
            'columns': ['time', 'close'],
            'period_start': '2025-01-01',
            'period_end': '2025-01-01',
            'license': 'Test License',
            'disclaimer': 'Test Disclaimer',
            'updated': '2025-01-01 00:00:00',
            'extracted_from': 'test.csv'
        }
        
        data = [{'time': '2025-01-01T00:00:00', 'close': 100.0}]
        
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            # Временно изменяем embedded_dir
            original_dir = generator.embedded_dir
            generator.embedded_dir = Path(temp_dir)
            
            try:
                output_file = generator._generate_embedded_file('test_dataset', metadata, data)
                
                # Проверяем, что файл создан
                assert output_file.exists()
                assert output_file.name == 'test_dataset.py'
                
                # Проверяем содержимое
                content = output_file.read_text(encoding='utf-8')
                assert 'DATASET_INFO = ' in content
                assert 'DATA = [' in content
                assert "'time': '2025-01-01T00:00:00'" in content
                
                print("[OK] test_generate_embedded_file: Генерация embedded файла работает")
                
            finally:
                # Восстанавливаем оригинальную директорию
                generator.embedded_dir = original_dir


if __name__ == '__main__':
    # Запуск тестов
    test_generator = TestSampleDataGenerator()
    
    test_generator.test_generator_creation()
    test_generator.test_data_sources_config()
    test_generator.test_validate_source_files()
    test_generator.test_convert_value_type()
    test_generator.test_identify_time_column()
    test_generator.test_generate_file_content()
    test_generator.test_generate_embedded_file()
    
    print("\n🎉 Все тесты SampleDataGenerator прошли успешно!")
