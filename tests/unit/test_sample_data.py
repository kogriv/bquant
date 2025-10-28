"""
Тесты для модуля bquant.data.samples

Проверяет корректность работы всех компонентов модуля sample data,
включая загрузку данных, валидацию, API функции и утилиты.
"""

import pytest
import pandas as pd
import sys
from typing import Dict, List, Any
from pathlib import Path

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bquant.data.samples import (
    get_sample_data,
    list_datasets,
    get_dataset_info,
    validate_dataset,
    get_sample_preview,
    get_data_statistics,
    find_datasets,
    compare_sample_datasets,
    print_sample_data_status
)

from bquant.data.samples.datasets import (
    get_dataset_registry,
    list_dataset_names,
    validate_dataset_name,
    get_datasets_by_symbol,
    get_datasets_by_timeframe,
    get_datasets_by_source
)

from bquant.data.samples.utils import (
    load_embedded_data,
    convert_to_dataframe,
    convert_to_list_of_dicts,
    validate_data_integrity,
    get_data_sample,
    get_data_info
)


class TestSampleDataAPI:
    """Тесты основного API для sample data."""
    
    def test_get_sample_data_pandas_format(self):
        """Тест загрузки данных в формате pandas DataFrame."""
        # TradingView данные
        df = get_sample_data('tv_xauusd_1h')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1000
        assert 'time' in df.columns
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        
        # MetaTrader данные
        df_mt = get_sample_data('mt_xauusd_m15')
        assert isinstance(df_mt, pd.DataFrame)
        assert len(df_mt) == 1000
        assert 'volume' in df_mt.columns
    
    def test_get_sample_data_dict_format(self):
        """Тест загрузки данных в формате списка словарей."""
        data = get_sample_data('tv_xauusd_1h', format='dict')
        assert isinstance(data, list)
        assert len(data) == 1000
        assert isinstance(data[0], dict)
        assert 'time' in data[0]
        assert 'close' in data[0]
        
        # Проверяем типы данных
        first_record = data[0]
        assert isinstance(first_record['close'], (int, float))
        assert isinstance(first_record['time'], str)
    
    def test_get_sample_data_invalid_dataset(self):
        """Тест ошибки при неправильном названии датасета."""
        with pytest.raises(KeyError) as excinfo:
            get_sample_data('nonexistent_dataset')
        
        assert "not found" in str(excinfo.value)
        assert "Available datasets" in str(excinfo.value)
    
    def test_get_sample_data_invalid_format(self):
        """Тест ошибки при неправильном формате."""
        with pytest.raises(ValueError) as excinfo:
            get_sample_data('tv_xauusd_1h', format='invalid_format')
        
        assert "Unsupported format" in str(excinfo.value)
    
    def test_list_datasets(self):
        """Тест получения списка всех датасетов."""
        datasets = list_datasets()
        assert isinstance(datasets, list)
        assert len(datasets) >= 2  # tv_xauusd_1h, mt_xauusd_m15
        
        # Проверяем структуру
        for dataset in datasets:
            assert 'name' in dataset
            assert 'title' in dataset
            assert 'rows' in dataset
            assert 'size_kb' in dataset
            assert isinstance(dataset['rows'], int)
            assert dataset['rows'] > 0
    
    def test_get_dataset_info(self):
        """Тест получения информации о датасете."""
        info = get_dataset_info('tv_xauusd_1h')
        assert isinstance(info, dict)
        assert info['name'] == 'TradingView XAUUSD 1H'
        assert info['symbol'] == 'XAUUSD'
        assert info['timeframe'] == '1H'
        assert info['rows'] == 1000
        assert 'columns' in info
        assert isinstance(info['columns'], list)
        assert len(info['columns']) > 5  # OHLCV + дополнительные
    
    def test_get_dataset_info_invalid(self):
        """Тест ошибки при неправильном названии датасета в get_dataset_info."""
        with pytest.raises(KeyError):
            get_dataset_info('nonexistent_dataset')
    
    def test_validate_dataset(self):
        """Тест валидации датасетов."""
        # TradingView
        result = validate_dataset('tv_xauusd_1h')
        assert isinstance(result, dict)
        assert 'is_valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'stats' in result
        assert result['is_valid'] is True
        
        # MetaTrader
        result_mt = validate_dataset('mt_xauusd_m15')
        assert result_mt['is_valid'] is True
    
    def test_get_sample_preview(self):
        """Тест получения предварительного просмотра."""
        preview = get_sample_preview('tv_xauusd_1h', 3)
        assert isinstance(preview, list)
        assert len(preview) == 3
        assert isinstance(preview[0], dict)
        assert 'time' in preview[0]
        assert 'close' in preview[0]
    
    def test_get_data_statistics(self):
        """Тест получения статистики по данным."""
        stats = get_data_statistics('tv_xauusd_1h')
        assert isinstance(stats, dict)
        assert 'total_records' in stats
        assert 'total_columns' in stats
        assert 'columns' in stats
        assert stats['total_records'] == 1000
        assert stats['total_columns'] > 5
    
    def test_find_datasets(self):
        """Тест поиска датасетов по критериям."""
        # По символу
        xauusd_datasets = find_datasets(symbol='XAUUSD')
        assert isinstance(xauusd_datasets, list)
        assert len(xauusd_datasets) >= 2
        assert 'tv_xauusd_1h' in xauusd_datasets
        assert 'mt_xauusd_m15' in xauusd_datasets
        
        # По таймфрейму
        hourly = find_datasets(timeframe='1H')
        assert 'tv_xauusd_1h' in hourly
        
        # По источнику
        tv_datasets = find_datasets(source='TradingView')
        assert 'tv_xauusd_1h' in tv_datasets
        
        mt_datasets = find_datasets(source='MetaTrader')
        assert 'mt_xauusd_m15' in mt_datasets
    
    def test_compare_sample_datasets(self):
        """Тест сравнения датасетов."""
        comparison = compare_sample_datasets('tv_xauusd_1h', 'mt_xauusd_m15')
        assert isinstance(comparison, dict)
        assert 'datasets' in comparison
        assert 'comparison' in comparison
        assert 'common_columns' in comparison
        assert 'unique_columns' in comparison
        
        # Общие колонки должны включать OHLCV
        common = comparison['common_columns']
        assert 'open' in common
        assert 'high' in common
        assert 'low' in common
        assert 'close' in common


class TestSampleDataRegistry:
    """Тесты модуля datasets (реестр датасетов)."""
    
    def test_get_dataset_registry(self):
        """Тест получения полного реестра."""
        registry = get_dataset_registry()
        assert isinstance(registry, dict)
        assert 'tv_xauusd_1h' in registry
        assert 'mt_xauusd_m15' in registry
        
        # Проверяем структуру записи
        tv_info = registry['tv_xauusd_1h']
        assert 'name' in tv_info
        assert 'symbol' in tv_info
        assert 'timeframe' in tv_info
        assert 'rows' in tv_info
        assert 'columns' in tv_info
    
    def test_list_dataset_names(self):
        """Тест получения списка названий датасетов."""
        names = list_dataset_names()
        assert isinstance(names, list)
        assert 'tv_xauusd_1h' in names
        assert 'mt_xauusd_m15' in names
    
    def test_validate_dataset_name(self):
        """Тест валидации названий датасетов."""
        assert validate_dataset_name('tv_xauusd_1h') is True
        assert validate_dataset_name('mt_xauusd_m15') is True
        assert validate_dataset_name('nonexistent') is False
    
    def test_get_datasets_by_criteria(self):
        """Тест поиска датасетов по различным критериям."""
        # По символу
        xauusd = get_datasets_by_symbol('XAUUSD')
        assert 'tv_xauusd_1h' in xauusd
        assert 'mt_xauusd_m15' in xauusd
        
        # По таймфрейму
        hourly = get_datasets_by_timeframe('1H')
        assert 'tv_xauusd_1h' in hourly
        
        minute15 = get_datasets_by_timeframe('15M')
        assert 'mt_xauusd_m15' in minute15
        
        # По источнику
        tv = get_datasets_by_source('TradingView')
        assert 'tv_xauusd_1h' in tv
        
        mt = get_datasets_by_source('MetaTrader')
        assert 'mt_xauusd_m15' in mt


class TestSampleDataUtils:
    """Тесты модуля utils (утилиты)."""
    
    def test_load_embedded_data(self):
        """Тест загрузки embedded данных."""
        embedded = load_embedded_data('tv_xauusd_1h')
        assert isinstance(embedded, dict)
        assert 'DATASET_INFO' in embedded
        assert 'DATA' in embedded
        
        data = embedded['DATA']
        assert isinstance(data, list)
        assert len(data) == 1000
        assert isinstance(data[0], dict)
        
        info = embedded['DATASET_INFO']
        assert isinstance(info, dict)
        assert 'name' in info
        assert 'rows' in info
    
    def test_load_embedded_data_invalid(self):
        """Тест ошибки при загрузке несуществующих данных."""
        with pytest.raises(KeyError):
            load_embedded_data('nonexistent_dataset')
    
    def test_convert_to_dataframe(self):
        """Тест конвертации в DataFrame."""
        embedded = load_embedded_data('tv_xauusd_1h')
        data = embedded['DATA']
        
        df = convert_to_dataframe(data, 'tv_xauusd_1h')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1000
        assert 'time' in df.columns
        assert 'close' in df.columns
        
        # Проверяем типы данных
        assert pd.api.types.is_numeric_dtype(df['close'])
        if 'time' in df.columns:
            # Время должно быть datetime или object (может быть с timezone)
            assert pd.api.types.is_datetime64_any_dtype(df['time']) or df['time'].dtype == 'object'
    
    def test_convert_to_list_of_dicts(self):
        """Тест конвертации DataFrame в список словарей."""
        df = get_sample_data('tv_xauusd_1h')
        data_list = convert_to_list_of_dicts(df, 'tv_xauusd_1h')
        
        assert isinstance(data_list, list)
        assert len(data_list) == len(df)
        assert isinstance(data_list[0], dict)
        
        # Проверяем корректность данных
        first_record = data_list[0]
        assert set(first_record.keys()) == set(df.columns)
    
    def test_validate_data_integrity(self):
        """Тест валидации целостности данных."""
        embedded = load_embedded_data('tv_xauusd_1h')
        data = embedded['DATA']
        info = embedded['DATASET_INFO']
        
        result = validate_data_integrity(data, info)
        assert isinstance(result, dict)
        assert 'is_valid' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'stats' in result
        
        # Для корректных данных должно быть valid
        assert result['is_valid'] is True
    
    def test_get_data_sample(self):
        """Тест получения образца данных."""
        embedded = load_embedded_data('tv_xauusd_1h')
        data = embedded['DATA']
        
        sample = get_data_sample(data, 5)
        assert isinstance(sample, list)
        assert len(sample) == 5
        assert all(isinstance(record, dict) for record in sample)
    
    def test_get_data_info(self):
        """Тест получения информации о данных."""
        embedded = load_embedded_data('tv_xauusd_1h')
        data = embedded['DATA']
        
        info = get_data_info(data, 'tv_xauusd_1h')
        assert isinstance(info, dict)
        assert 'dataset_name' in info
        assert 'total_records' in info
        assert 'total_columns' in info
        assert 'columns' in info
        assert info['total_records'] == 1000


class TestSampleDataIntegration:
    """Интеграционные тесты для sample data."""
    
    def test_integration_with_macd_analyzer(self):
        """Тест интеграции с MACD анализатором."""
        try:
            from bquant.indicators.macd import MACDZoneAnalyzer
            
            # Загружаем данные
            data = get_sample_data('tv_xauusd_1h')
            
            # Создаем анализатор и получаем результат
            analyzer = MACDZoneAnalyzer()
            result = analyzer.analyze_complete_modular(data)
            
            # Проверяем результат
            assert isinstance(result.zones, list)
            # Может быть 0 зон если данные не подходят, но это не ошибка
            
        except ImportError:
            pytest.skip("MACDZoneAnalyzer not available")
    
    def test_data_quality_for_analysis(self):
        """Тест качества данных для анализа."""
        # TradingView данные
        df = get_sample_data('tv_xauusd_1h')
        
        # Базовые проверки качества
        assert not df.empty
        assert df['open'].notna().sum() > 0
        assert df['high'].notna().sum() > 0
        assert df['low'].notna().sum() > 0
        assert df['close'].notna().sum() > 0
        
        # OHLC логика
        valid_rows = df[['open', 'high', 'low', 'close']].notna().all(axis=1)
        valid_data = df[valid_rows]
        
        if len(valid_data) > 0:
            # High должен быть >= max(open, close)
            assert (valid_data['high'] >= valid_data[['open', 'close']].max(axis=1)).all()
            # Low должен быть <= min(open, close)
            assert (valid_data['low'] <= valid_data[['open', 'close']].min(axis=1)).all()
    
    def test_multiple_datasets_consistency(self):
        """Тест консистентности между разными датасетами."""
        datasets = ['tv_xauusd_1h', 'mt_xauusd_m15']
        
        for dataset_name in datasets:
            # Проверяем, что каждый датасет загружается корректно
            data = get_sample_data(dataset_name)
            assert isinstance(data, pd.DataFrame)
            assert len(data) == 1000
            
            # Базовые колонки должны присутствовать
            required_columns = ['time', 'open', 'high', 'low', 'close']
            for col in required_columns:
                assert col in data.columns, f"Missing {col} in {dataset_name}"
            
            # Валидация должна проходить
            validation = validate_dataset(dataset_name)
            assert validation['is_valid'], f"Validation failed for {dataset_name}: {validation['errors']}"


class TestSampleDataErrorHandling:
    """Тесты обработки ошибок."""
    
    def test_nonexistent_dataset_handling(self):
        """Тест обработки несуществующих датасетов."""
        with pytest.raises(KeyError):
            get_sample_data('nonexistent_dataset')
        
        with pytest.raises(KeyError):
            get_dataset_info('nonexistent_dataset')
        
        # validate_dataset должен возвращать результат с ошибкой, а не поднимать исключение
        result = validate_dataset('nonexistent_dataset')
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
    
    def test_empty_data_handling(self):
        """Тест обработки пустых данных."""
        empty_data = []
        
        # convert_to_dataframe должен возвращать пустой DataFrame
        df = convert_to_dataframe(empty_data, 'test')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        
        # get_data_sample должен возвращать пустой список
        sample = get_data_sample(empty_data, 5)
        assert isinstance(sample, list)
        assert len(sample) == 0
    
    def test_malformed_data_handling(self):
        """Тест обработки неправильно сформированных данных."""
        malformed_data = [
            {'time': '2025-01-01', 'close': 100},  # Отсутствуют некоторые колонки
            {'time': '2025-01-02', 'close': None, 'open': 'invalid'}  # Неправильные типы
        ]
        
        # Конвертация должна работать, но с предупреждениями
        df = convert_to_dataframe(malformed_data, 'test')
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2


if __name__ == '__main__':
    # Запуск тестов
    pytest.main([__file__, '-v'])
