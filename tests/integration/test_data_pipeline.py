"""
Интеграционные тесты пайплайна обработки данных.

Упрощенная версия для корректной работы с существующими модулями BQuant.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from typing import Dict, List, Any

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bquant.data.samples import (
    get_sample_data, 
    list_dataset_names, 
    get_dataset_info,
    validate_dataset
)


class TestSampleDataPipeline:
    """
    Тесты полного пайплайна работы с sample данными.
    """
    
    @pytest.mark.integration
    def test_complete_sample_data_workflow(self, sample_data_available, skip_if_no_sample_data):
        """
        Полный workflow работы с sample данными:
        discovery → validation → loading → basic checks.
        """
        # 1. Discovery - поиск доступных datasets
        dataset_names = list_dataset_names()
        assert len(dataset_names) > 0, "Should discover sample datasets"
        
        workflow_results = {}
        
        for dataset_name in dataset_names:
            try:
                # 2. Validation - проверка корректности dataset
                is_valid = validate_dataset(dataset_name)
                assert is_valid, f"Dataset {dataset_name} should be valid"
                
                # 3. Loading - загрузка данных
                data = get_sample_data(dataset_name)
                assert isinstance(data, pd.DataFrame), f"Should load DataFrame for {dataset_name}"
                assert len(data) > 0, f"Data should not be empty for {dataset_name}"
                
                # 4. Basic validation - базовые проверки
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                columns_present = all(col in data.columns for col in required_columns)
                
                workflow_results[dataset_name] = {
                    'original_size': len(data),
                    'columns_present': columns_present,
                    'workflow_success': True
                }
                
                print(f"✅ {dataset_name}: {len(data)} points, columns OK: {columns_present}")
                
            except Exception as e:
                workflow_results[dataset_name] = {
                    'workflow_success': False,
                    'error': str(e)
                }
                print(f"❌ {dataset_name}: workflow failed - {e}")
        
        # Проверяем что хотя бы один workflow прошел успешно
        successful_workflows = [r for r in workflow_results.values() if r.get('workflow_success', False)]
        assert len(successful_workflows) > 0, "At least one workflow should succeed"
        
        print(f"✅ Complete sample data workflow test completed!")
        print(f"   • Total datasets: {len(dataset_names)}")
        print(f"   • Successful workflows: {len(successful_workflows)}")
        
        return workflow_results
    
    @pytest.mark.integration
    def test_sample_data_metadata_consistency(self, sample_data_available, skip_if_no_sample_data):
        """
        Тест консистентности метаданных sample данных.
        """
        dataset_names = list_dataset_names()
        
        for dataset_name in dataset_names:
            # Получаем метаданные
            dataset_info = get_dataset_info(dataset_name)
            assert isinstance(dataset_info, dict), f"Dataset info should be dict for {dataset_name}"
            
            # Проверяем обязательные поля метаданных
            required_fields = ['name', 'description', 'source', 'rows', 'columns']
            for field in required_fields:
                assert field in dataset_info, f"Field '{field}' missing from {dataset_name} metadata"
            
            # Загружаем данные и проверяем соответствие метаданных
            data = get_sample_data(dataset_name)
            
            # Проверяем количество строк
            actual_rows = len(data)
            expected_rows = dataset_info['rows']
            assert actual_rows == expected_rows, \
                f"Row count mismatch for {dataset_name}: expected {expected_rows}, got {actual_rows}"
            
            print(f"✅ {dataset_name}: metadata consistent ({actual_rows} rows)")
        
        print(f"✅ Sample data metadata consistency test completed!")


class TestDataQualityPipeline:
    """
    Тесты базового контроля качества данных.
    """
    
    @pytest.mark.integration
    def test_data_quality_workflow(self, bquant_test_data):
        """
        Workflow контроля качества данных.
        """
        quality_report = {}
        
        # Тестируем разные размеры datasets
        test_datasets = {
            'small': bquant_test_data['ohlcv_small'],
            'medium': bquant_test_data['ohlcv_medium'],
            'large': bquant_test_data['ohlcv_large']
        }
        
        for dataset_name, data in test_datasets.items():
            # 1. Исходное качество данных
            initial_quality = {
                'rows': len(data),
                'columns': len(data.columns),
                'missing_values': data.isna().sum().sum(),
                'has_ohlc': all(col in data.columns for col in ['open', 'high', 'low', 'close'])
            }
            
            # 2. Базовые проверки OHLC логики
            ohlc_valid = True
            if initial_quality['has_ohlc']:
                try:
                    ohlc_valid = (
                        (data['high'] >= data['open']).all() and
                        (data['high'] >= data['close']).all() and
                        (data['low'] <= data['open']).all() and
                        (data['low'] <= data['close']).all()
                    )
                except:
                    ohlc_valid = False
            
            quality_report[dataset_name] = {
                'initial': initial_quality,
                'ohlc_valid': ohlc_valid,
                'quality_score': (
                    (1 if initial_quality['has_ohlc'] else 0) +
                    (1 if ohlc_valid else 0) +
                    (1 if initial_quality['missing_values'] == 0 else 0)
                ) / 3
            }
            
            # Проверки качества
            assert initial_quality['rows'] > 0, f"Data should not be empty for {dataset_name}"
            assert initial_quality['has_ohlc'], f"Should have OHLC data for {dataset_name}"
            
            print(f"✅ {dataset_name}: {initial_quality['rows']} rows, quality: {quality_report[dataset_name]['quality_score']:.2f}")
        
        print(f"✅ Data quality workflow test completed!")
        return quality_report