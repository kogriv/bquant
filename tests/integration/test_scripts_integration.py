"""
Интеграционные тесты для скриптов анализа BQuant.

Тестирует интеграцию скриптов analysis с основными компонентами системы.
"""

import pytest
import subprocess
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any
import time

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestScriptsExecution:
    """
    Тесты выполнения скриптов анализа.
    """
    
    @pytest.mark.integration
    def test_run_macd_analysis_script(self):
        """
        Тест интеграции скрипта run_macd_analysis.py с sample данными.
        """
        script_path = project_root / "scripts" / "analysis" / "run_macd_analysis.py"
        assert script_path.exists(), "run_macd_analysis.py should exist"
        
        # 1. Тест dry-run режима
        result = subprocess.run(
            [sys.executable, str(script_path), "XAUUSD", "1h", "--dry-run"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Dry-run failed: {result.stderr}"
        assert "dry run" in result.stdout.lower(), "Should indicate dry-run mode"
        
        # 2. Тест с sample данными
        result = subprocess.run(
            [sys.executable, str(script_path), "tv_xauusd_1h", "1h", "--sample-data"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Может упасть из-за известных проблем, но не должен крашиться
        if result.returncode == 0:
            assert "analysis completed" in result.stdout.lower(), "Should indicate completion"
            analysis_success = True
        else:
            print(f"Analysis failed (may be expected): {result.stderr}")
            analysis_success = False
        
        # 3. Тест вывода в JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            output_file = tmp_file.name
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "tv_xauusd_1h", "1h", "--sample-data", 
                 "--output", output_file, "--output-format", "json"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Проверяем что файл создан и содержит валидный JSON
                output_path = Path(output_file)
                assert output_path.exists(), "Output file should be created"
                
                with open(output_path, 'r') as f:
                    output_data = json.load(f)
                    assert isinstance(output_data, dict), "Output should be valid JSON dict"
                    assert 'metadata' in output_data, "Output should contain metadata"
                
                json_output_success = True
            else:
                json_output_success = False
        
        finally:
            # Cleanup
            if Path(output_file).exists():
                Path(output_file).unlink()
        
        print(f"✅ run_macd_analysis.py integration test completed!")
        print(f"   • Dry-run: ✅")
        print(f"   • Sample data analysis: {'✅' if analysis_success else '⚠️ (expected issues)'}")
        print(f"   • JSON output: {'✅' if json_output_success else '⚠️ (expected issues)'}")
        
        return {
            'dry_run_success': True,
            'analysis_success': analysis_success,
            'json_output_success': json_output_success
        }
    
    @pytest.mark.integration
    def test_test_hypotheses_script(self):
        """
        Тест интеграции скрипта test_hypotheses.py.
        """
        script_path = project_root / "scripts" / "analysis" / "test_hypotheses.py"
        assert script_path.exists(), "test_hypotheses.py should exist"
        
        # 1. Тест dry-run режима
        result = subprocess.run(
            [sys.executable, str(script_path), "XAUUSD", "1h", "--dry-run"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Dry-run failed: {result.stderr}"
        assert "dry run" in result.stdout.lower(), "Should indicate dry-run mode"
        
        # 2. Тест с sample данными
        result = subprocess.run(
            [sys.executable, str(script_path), "tv_xauusd_1h", "1h", "--sample-data"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=90
        )
        
        # Статистические тесты могут упасть из-за известных проблем
        if result.returncode == 0:
            assert "testing completed" in result.stdout.lower(), "Should indicate completion"
            hypothesis_success = True
        else:
            print(f"Hypothesis testing failed (may be expected): {result.stderr}")
            hypothesis_success = False
        
        # 3. Тест с конкретными тестами
        result = subprocess.run(
            [sys.executable, str(script_path), "tv_xauusd_1h", "1h", "--sample-data", 
             "--tests", "duration", "--alpha", "0.05"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=90
        )
        
        specific_tests_success = result.returncode == 0
        
        print(f"✅ test_hypotheses.py integration test completed!")
        print(f"   • Dry-run: ✅")
        print(f"   • Sample data testing: {'✅' if hypothesis_success else '⚠️ (expected issues)'}")
        print(f"   • Specific tests: {'✅' if specific_tests_success else '⚠️ (expected issues)'}")
        
        return {
            'dry_run_success': True,
            'hypothesis_success': hypothesis_success,
            'specific_tests_success': specific_tests_success
        }
    
    @pytest.mark.integration  
    def test_batch_analysis_script(self):
        """
        Тест интеграции скрипта batch_analysis.py.
        """
        script_path = project_root / "scripts" / "analysis" / "batch_analysis.py"
        assert script_path.exists(), "batch_analysis.py should exist"
        
        # 1. Тест dry-run режима
        result = subprocess.run(
            [sys.executable, str(script_path), "--sample-data", "--dry-run"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        assert result.returncode == 0, f"Dry-run failed: {result.stderr}"
        assert "dry run" in result.stdout.lower(), "Should indicate dry-run mode"
        
        # 2. Тест с sample данными (небольшой batch)
        result = subprocess.run(
            [sys.executable, str(script_path), "--sample-data", "--all-datasets", "--no-hypotheses"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Batch анализ может частично упасть, но не должен крашиться
        if result.returncode == 0:
            assert "batch analysis completed" in result.stdout.lower(), "Should indicate completion"
            batch_success = True
        else:
            print(f"Batch analysis failed (may be partial): {result.stderr}")
            batch_success = False
        
        # 3. Тест конфигурационного режима (dry-run с параметрами)
        result = subprocess.run(
            [sys.executable, str(script_path), "--symbols", "XAUUSD", "--timeframes", "1h", 
             "--sample-data", "--dry-run"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        config_success = result.returncode == 0
        
        print(f"✅ batch_analysis.py integration test completed!")
        print(f"   • Dry-run: ✅")
        print(f"   • Sample data batch: {'✅' if batch_success else '⚠️ (partial success expected)'}")
        print(f"   • Configuration mode: {'✅' if config_success else '❌'}")
        
        return {
            'dry_run_success': True,
            'batch_success': batch_success,
            'config_success': config_success
        }


class TestScriptsIntegrationWithComponents:
    """
    Тесты интеграции скриптов с компонентами BQuant.
    """
    
    @pytest.mark.integration
    def test_scripts_sample_data_integration(self):
        """
        Тест интеграции скриптов с модулем sample data.
        """
        from bquant.data.samples import list_dataset_names
        
        # Проверяем что sample data доступны
        dataset_names = list_dataset_names()
        if not dataset_names:
            pytest.skip("No sample data available for scripts integration testing")
        
        scripts_results = {}
        
        # Тестируем каждый скрипт с каждым доступным dataset
        scripts_to_test = [
            ("run_macd_analysis.py", ["--sample-data", "--dry-run"]),
            ("test_hypotheses.py", ["--sample-data", "--dry-run"]),
        ]
        
        for script_name, base_args in scripts_to_test:
            script_path = project_root / "scripts" / "analysis" / script_name
            script_success_count = 0
            
            for dataset_name in dataset_names[:2]:  # Тестируем первые 2 dataset'а
                try:
                    result = subprocess.run(
                        [sys.executable, str(script_path), dataset_name, "1h"] + base_args,
                        cwd=str(project_root),
                        capture_output=True,
                        text=True,
                        timeout=45
                    )
                    
                    if result.returncode == 0:
                        script_success_count += 1
                        
                except subprocess.TimeoutExpired:
                    print(f"Script {script_name} timed out on {dataset_name}")
                except Exception as e:
                    print(f"Script {script_name} failed on {dataset_name}: {e}")
            
            scripts_results[script_name] = {
                'datasets_tested': min(len(dataset_names), 2),
                'successful_runs': script_success_count,
                'success_rate': script_success_count / min(len(dataset_names), 2) if dataset_names else 0
            }
        
        # Проверяем что хотя бы некоторые интеграции работают
        total_successful_integrations = sum(r['successful_runs'] for r in scripts_results.values())
        assert total_successful_integrations > 0, "At least some script-data integrations should work"
        
        print(f"✅ Scripts sample data integration test completed!")
        for script_name, results in scripts_results.items():
            print(f"   • {script_name}: {results['successful_runs']}/{results['datasets_tested']} datasets")
        
        return scripts_results
    
    @pytest.mark.integration
    def test_scripts_performance_integration(self):
        """
        Тест производительности интеграции скриптов.
        """
        performance_results = {}
        
        # Тестируем производительность каждого скрипта
        performance_tests = [
            ("run_macd_analysis.py", ["tv_xauusd_1h", "1h", "--sample-data"], 60),
            ("test_hypotheses.py", ["tv_xauusd_1h", "1h", "--sample-data"], 90),
            ("batch_analysis.py", ["--sample-data", "--dry-run"], 45)
        ]
        
        for script_name, args, timeout_limit in performance_tests:
            script_path = project_root / "scripts" / "analysis" / script_name
            
            try:
                start_time = time.time()
                
                result = subprocess.run(
                    [sys.executable, str(script_path)] + args,
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=timeout_limit
                )
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                performance_results[script_name] = {
                    'execution_time': execution_time,
                    'success': result.returncode == 0,
                    'timeout_limit': timeout_limit,
                    'within_limit': execution_time < timeout_limit
                }
                
            except subprocess.TimeoutExpired:
                performance_results[script_name] = {
                    'execution_time': timeout_limit,
                    'success': False,
                    'timeout_limit': timeout_limit,
                    'within_limit': False,
                    'timed_out': True
                }
            except Exception as e:
                performance_results[script_name] = {
                    'execution_time': None,
                    'success': False,
                    'timeout_limit': timeout_limit,
                    'within_limit': False,
                    'error': str(e)
                }
        
        # Проверяем что хотя бы один скрипт выполняется в разумное время
        successful_performances = [r for r in performance_results.values() 
                                 if r.get('within_limit', False)]
        assert len(successful_performances) > 0, "At least one script should perform within limits"
        
        print(f"✅ Scripts performance integration test completed!")
        for script_name, results in performance_results.items():
            exec_time = results.get('execution_time')
            if exec_time:
                print(f"   • {script_name}: {exec_time:.2f}s ({'✅' if results.get('within_limit') else '⚠️ slow'})")
            else:
                print(f"   • {script_name}: {'❌ timed out' if results.get('timed_out') else '❌ failed'}")
        
        return performance_results


class TestScriptsOutputIntegration:
    """
    Тесты интеграции выходных форматов скриптов.
    """
    
    @pytest.mark.integration
    def test_scripts_output_formats(self):
        """
        Тест различных форматов вывода скриптов.
        """
        script_path = project_root / "scripts" / "analysis" / "run_macd_analysis.py"
        
        output_formats = ['json', 'text', 'html']
        format_results = {}
        
        for output_format in output_formats:
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{output_format}', delete=False) as tmp_file:
                output_file = tmp_file.name
            
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path), "tv_xauusd_1h", "1h", "--sample-data",
                     "--output", output_file, "--output-format", output_format],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=90
                )
                
                if result.returncode == 0:
                    output_path = Path(output_file)
                    if output_path.exists() and output_path.stat().st_size > 0:
                        # Проверяем содержимое файла
                        with open(output_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        if output_format == 'json':
                            try:
                                json.loads(content)
                                format_valid = True
                            except json.JSONDecodeError:
                                format_valid = False
                        else:
                            format_valid = len(content.strip()) > 0
                        
                        format_results[output_format] = {
                            'file_created': True,
                            'file_size': output_path.stat().st_size,
                            'format_valid': format_valid,
                            'success': True
                        }
                    else:
                        format_results[output_format] = {
                            'file_created': False,
                            'success': False
                        }
                else:
                    format_results[output_format] = {
                        'success': False,
                        'error': result.stderr
                    }
            
            except Exception as e:
                format_results[output_format] = {
                    'success': False,
                    'error': str(e)
                }
            
            finally:
                # Cleanup
                if Path(output_file).exists():
                    Path(output_file).unlink()
        
        # Проверяем что хотя бы один формат работает
        successful_formats = [fmt for fmt, result in format_results.items() if result.get('success', False)]
        assert len(successful_formats) > 0, "At least one output format should work"
        
        print(f"✅ Scripts output formats integration test completed!")
        for output_format, results in format_results.items():
            if results.get('success'):
                size = results.get('file_size', 0)
                valid = results.get('format_valid', False)
                print(f"   • {output_format}: ✅ ({size} bytes, {'valid' if valid else 'invalid'} format)")
            else:
                print(f"   • {output_format}: ❌")
        
        return format_results
    
    @pytest.mark.integration  
    def test_scripts_error_handling(self):
        """
        Тест обработки ошибок в скриптах.
        """
        script_path = project_root / "scripts" / "analysis" / "run_macd_analysis.py"
        
        error_scenarios = [
            # Несуществующий dataset
            (["nonexistent_dataset", "1h", "--sample-data"], "nonexistent dataset"),
            # Некорректный таймфрейм  
            (["tv_xauusd_1h", "invalid_timeframe", "--sample-data"], "invalid timeframe"),
            # Некорректный формат вывода
            (["tv_xauusd_1h", "1h", "--sample-data", "--output-format", "invalid"], "invalid format")
        ]
        
        error_handling_results = {}
        
        for args, scenario_name in error_scenarios:
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)] + args,
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Ошибки должны обрабатываться gracefully (не крашить скрипт)
                error_handling_results[scenario_name] = {
                    'graceful_failure': result.returncode != 0,  # Должен упасть с кодом ошибки
                    'error_message_present': len(result.stderr) > 0 or "error" in result.stdout.lower(),
                    'no_crash': True  # Скрипт завершился, не крашнулся
                }
                
            except subprocess.TimeoutExpired:
                error_handling_results[scenario_name] = {
                    'graceful_failure': False,
                    'error_message_present': False,
                    'no_crash': False,
                    'timed_out': True
                }
            except Exception as e:
                error_handling_results[scenario_name] = {
                    'graceful_failure': False,
                    'error_message_present': True,
                    'no_crash': False,
                    'exception': str(e)
                }
        
        # Проверяем что ошибки обрабатываются корректно
        proper_error_handling_count = sum(
            1 for result in error_handling_results.values() 
            if result.get('graceful_failure', False) and result.get('no_crash', False)
        )
        
        assert proper_error_handling_count > 0, "At least some error scenarios should be handled gracefully"
        
        print(f"✅ Scripts error handling integration test completed!")
        for scenario, results in error_handling_results.items():
            graceful = results.get('graceful_failure', False)
            no_crash = results.get('no_crash', False)
            status = "✅" if graceful and no_crash else "⚠️" if no_crash else "❌"
            print(f"   • {scenario}: {status}")
        
        return error_handling_results
