#!/usr/bin/env python3
"""
BQuant Statistical Hypothesis Testing Script

Выполняет статистическое тестирование гипотез для MACD зон.
Поддерживает различные типы тестов и форматы вывода результатов.

Usage:
    python test_hypotheses.py XAUUSD 1h
    python test_hypotheses.py tv_xauusd_1h --sample-data
    python test_hypotheses.py EURUSD 15m --tests duration,slope --output results.json
    python test_hypotheses.py XAUUSD 1h --all-tests --verbose
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bquant.core.logging_config import get_logger
from bquant.data.samples import get_sample_data, list_dataset_names, validate_dataset_name
from bquant.indicators import MACDZoneAnalyzer
from bquant.analysis.statistical import run_all_hypothesis_tests, run_single_hypothesis_test

logger = get_logger(__name__)


class HypothesisTestingScript:
    """
    Скрипт для статистического тестирования гипотез MACD зон.
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.HypothesisTestingScript")
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Доступные тесты
        self.available_tests = {
            'duration': 'Zone Duration Analysis',
            'slope': 'Histogram Slope Test',
            'asymmetry': 'Bull/Bear Asymmetry Test',
            'patterns': 'Sequence Patterns Test',
            'volatility': 'Volatility Effects Test'
        }
    
    def test_hypotheses(
        self,
        symbol: str,
        timeframe: str,
        tests: Optional[List[str]] = None,
        use_sample_data: bool = False,
        all_tests: bool = False,
        alpha: float = 0.05,
        output_format: str = "json",
        output_file: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Выполнить статистическое тестирование гипотез.
        
        Args:
            symbol: Символ инструмента или название sample dataset
            timeframe: Таймфрейм данных
            tests: Список тестов для выполнения
            use_sample_data: Использовать встроенные sample данные
            all_tests: Выполнить все доступные тесты
            alpha: Уровень значимости (по умолчанию 0.05)
            output_format: Формат вывода ('json', 'html', 'text')
            output_file: Путь к файлу для сохранения результатов
            verbose: Подробный вывод
        
        Returns:
            Словарь с результатами тестирования
        """
        self.logger.info(f"Starting hypothesis testing for {symbol} {timeframe}")
        
        testing_start = datetime.now()
        
        try:
            # Загрузка данных
            data = self._load_data(symbol, timeframe, use_sample_data, verbose)
            
            # Выполнение MACD анализа для получения зон
            analyzer = MACDZoneAnalyzer()
            
            if verbose:
                print(f"📊 Loaded {len(data)} data points for {symbol}")
                print(f"🔧 Performing MACD analysis...")
            
            # Получение полного анализа зон
            zones_analysis = analyzer.analyze_complete(data)
            
            if not zones_analysis or not zones_analysis.zones:
                raise ValueError("Insufficient zone data for hypothesis testing")
            
            # Формируем zones_info для совместимости с функциями тестирования
            zones_info = {
                'zones_features': [zone.features for zone in zones_analysis.zones if zone.features],
                'zones': zones_analysis.zones,
                'statistics': zones_analysis.statistics,
                'hypothesis_tests': zones_analysis.hypothesis_tests
            }
            
            # Определение тестов для выполнения
            tests_to_run = self._determine_tests(tests, all_tests, verbose)
            
            # Выполнение тестов
            if all_tests or len(tests_to_run) > 3:
                # Выполняем все тесты сразу
                if verbose:
                    print(f"🧪 Running all available hypothesis tests...")
                
                test_results = run_all_hypothesis_tests(zones_info, alpha=alpha)
            else:
                # Выполняем отдельные тесты
                if verbose:
                    print(f"🧪 Running {len(tests_to_run)} specific tests...")
                
                test_results = {}
                for test_name in tests_to_run:
                    if test_name in self.available_tests:
                        try:
                            result = run_single_hypothesis_test(
                                zones_info, test_name, alpha=alpha
                            )
                            test_results[test_name] = result
                        except Exception as e:
                            self.logger.warning(f"Test {test_name} failed: {e}")
                            test_results[test_name] = {
                                'error': str(e),
                                'test_name': test_name
                            }
            
            # Формирование результатов
            results = self._format_results(
                symbol, timeframe, test_results, zones_info,
                testing_start, alpha, verbose
            )
            
            # Сохранение результатов
            if output_file:
                self._save_results(
                    results, output_file, output_format, verbose
                )
            
            # Вывод результатов
            self._display_results(results, output_format, verbose)
            
            self.logger.info(f"Hypothesis testing completed for {symbol}")
            return results
            
        except Exception as e:
            self.logger.error(f"Hypothesis testing failed for {symbol}: {e}")
            if verbose:
                print(f"❌ Testing failed: {e}")
            raise
    
    def _load_data(
        self, 
        symbol: str, 
        timeframe: str, 
        use_sample_data: bool,
        verbose: bool
    ):
        """Загрузить данные для анализа."""
        if use_sample_data or validate_dataset_name(symbol):
            # Используем sample данные
            if verbose:
                print(f"📦 Loading sample data: {symbol}")
            
            # Если передан symbol как dataset name
            if validate_dataset_name(symbol):
                dataset_name = symbol
            else:
                # Попытка найти подходящий dataset
                available = list_dataset_names()
                matching = [ds for ds in available if symbol.lower() in ds.lower()]
                
                if not matching:
                    raise ValueError(
                        f"No sample data found for {symbol}. "
                        f"Available datasets: {available}"
                    )
                dataset_name = matching[0]
                if verbose:
                    print(f"📦 Using dataset: {dataset_name}")
            
            data = get_sample_data(dataset_name)
            
        else:
            # Для внешних данных (пока используем sample как fallback)
            if verbose:
                print(f"⚠️  External data loading not implemented yet")
                print(f"📦 Falling back to sample data")
            
            # Fallback к sample данным
            available = list_dataset_names()
            if not available:
                raise ValueError("No sample data available")
            
            dataset_name = available[0]  # Используем первый доступный
            data = get_sample_data(dataset_name)
            
            if verbose:
                print(f"📦 Using fallback dataset: {dataset_name}")
        
        return data
    
    def _determine_tests(
        self, 
        tests: Optional[List[str]], 
        all_tests: bool,
        verbose: bool
    ) -> List[str]:
        """Определить тесты для выполнения."""
        if all_tests:
            tests_to_run = list(self.available_tests.keys())
            if verbose:
                print(f"🧪 Will run all {len(tests_to_run)} tests")
        elif tests:
            # Валидация указанных тестов
            tests_to_run = []
            for test in tests:
                if test in self.available_tests:
                    tests_to_run.append(test)
                else:
                    available = list(self.available_tests.keys())
                    self.logger.warning(f"Unknown test: {test}. Available: {available}")
            
            if not tests_to_run:
                raise ValueError(f"No valid tests specified. Available: {list(self.available_tests.keys())}")
            
            if verbose:
                print(f"🧪 Will run {len(tests_to_run)} specified tests: {tests_to_run}")
        else:
            # По умолчанию выполняем основные тесты
            tests_to_run = ['duration', 'slope', 'asymmetry']
            if verbose:
                print(f"🧪 Will run {len(tests_to_run)} default tests: {tests_to_run}")
        
        return tests_to_run
    
    def _format_results(
        self,
        symbol: str,
        timeframe: str,
        test_results: Dict[str, Any],
        zones_info: Dict[str, Any],
        testing_start,
        alpha: float,
        verbose: bool
    ) -> Dict[str, Any]:
        """Сформировать результаты тестирования."""
        testing_duration = datetime.now() - testing_start
        
        # Подсчет статистики по тестам
        successful_tests = 0
        significant_results = 0
        
        for test_name, result in test_results.items():
            if isinstance(result, dict) and 'error' not in result:
                successful_tests += 1
                if hasattr(result, 'p_value') and result.p_value < alpha:
                    significant_results += 1
                elif isinstance(result, dict) and 'p_value' in result and result['p_value'] < alpha:
                    significant_results += 1
        
        # Сводка по зонам
        zones_summary = self._summarize_zones(zones_info)
        
        # Формирование результатов
        results = {
            'metadata': {
                'symbol': symbol,
                'timeframe': timeframe,
                'testing_date': datetime.now().isoformat(),
                'testing_duration_seconds': testing_duration.total_seconds(),
                'alpha_level': alpha,
                'bquant_version': '0.0.0-dev'
            },
            'zones_summary': zones_summary,
            'test_results': test_results,
            'testing_summary': {
                'total_tests': len(test_results),
                'successful_tests': successful_tests,
                'failed_tests': len(test_results) - successful_tests,
                'significant_results': significant_results,
                'significance_rate': significant_results / successful_tests if successful_tests > 0 else 0
            },
            'interpretation': self._generate_interpretation(test_results, alpha),
            'recommendations': self._generate_recommendations(test_results, alpha)
        }
        
        if verbose:
            print(f"🧪 Testing summary:")
            print(f"   • Total tests: {results['testing_summary']['total_tests']}")
            print(f"   • Successful: {results['testing_summary']['successful_tests']}")
            print(f"   • Significant: {results['testing_summary']['significant_results']}")
        
        return results
    
    def _summarize_zones(self, zones_info: Dict[str, Any]) -> Dict[str, Any]:
        """Создать сводку по зонам."""
        zones_features = zones_info.get('zones_features', [])
        
        if not zones_features:
            return {'error': 'No zone features available'}
        
        total_zones = len(zones_features)
        bull_zones = len([z for z in zones_features if z.get('type') == 'Bull'])
        bear_zones = len([z for z in zones_features if z.get('type') == 'Bear'])
        
        durations = [z.get('duration', 0) for z in zones_features if z.get('duration')]
        returns = [z.get('price_return', 0) for z in zones_features if z.get('price_return')]
        
        summary = {
            'total_zones': total_zones,
            'bull_zones': bull_zones,
            'bear_zones': bear_zones,
            'bull_ratio': bull_zones / total_zones if total_zones > 0 else 0,
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'avg_return': sum(returns) / len(returns) if returns else 0,
            'duration_range': [min(durations), max(durations)] if durations else [0, 0],
            'return_range': [min(returns), max(returns)] if returns else [0, 0]
        }
        
        return summary
    
    def _generate_interpretation(self, test_results: Dict[str, Any], alpha: float) -> List[str]:
        """Сгенерировать интерпретацию результатов."""
        interpretations = []
        
        for test_name, result in test_results.items():
            if isinstance(result, dict) and 'error' in result:
                interpretations.append(f"{test_name}: Test failed - {result['error']}")
                continue
            
            test_title = self.available_tests.get(test_name, test_name)
            
            # Извлекаем p-value
            p_value = None
            if hasattr(result, 'p_value'):
                p_value = result.p_value
            elif isinstance(result, dict) and 'p_value' in result:
                p_value = result['p_value']
            
            if p_value is not None:
                if p_value < alpha:
                    interpretations.append(
                        f"{test_title}: Statistically significant (p={p_value:.4f})"
                    )
                else:
                    interpretations.append(
                        f"{test_title}: Not significant (p={p_value:.4f})"
                    )
            else:
                interpretations.append(f"{test_title}: Unable to determine significance")
        
        return interpretations
    
    def _generate_recommendations(self, test_results: Dict[str, Any], alpha: float) -> List[str]:
        """Сгенерировать рекомендации на основе результатов."""
        recommendations = []
        
        significant_count = 0
        total_valid_tests = 0
        
        for test_name, result in test_results.items():
            if isinstance(result, dict) and 'error' in result:
                continue
            
            total_valid_tests += 1
            
            # Проверяем значимость
            p_value = None
            if hasattr(result, 'p_value'):
                p_value = result.p_value
            elif isinstance(result, dict) and 'p_value' in result:
                p_value = result['p_value']
            
            if p_value is not None and p_value < alpha:
                significant_count += 1
        
        if total_valid_tests == 0:
            recommendations.append("Unable to generate recommendations due to test failures")
            return recommendations
        
        significance_ratio = significant_count / total_valid_tests
        
        if significance_ratio > 0.7:
            recommendations.append("Strong statistical evidence found in MACD patterns")
            recommendations.append("Consider using MACD zones for trading decisions")
        elif significance_ratio > 0.4:
            recommendations.append("Moderate statistical evidence in MACD patterns")
            recommendations.append("Use MACD analysis with additional confirmation")
        else:
            recommendations.append("Limited statistical evidence in MACD patterns")
            recommendations.append("Consider additional indicators for trading decisions")
        
        if 'duration' in test_results:
            recommendations.append("Zone duration analysis completed - review for trend persistence")
        
        if 'asymmetry' in test_results:
            recommendations.append("Bull/Bear asymmetry tested - consider market bias implications")
        
        return recommendations
    
    def _save_results(
        self,
        results: Dict[str, Any],
        output_file: str,
        output_format: str,
        verbose: bool
    ):
        """Сохранить результаты в файл."""
        output_path = Path(output_file)
        
        if output_format == 'json':
            # Для JSON нужно сериализовать специальные объекты
            json_results = self._serialize_for_json(results)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2, ensure_ascii=False)
        
        elif output_format == 'html':
            html_content = self._generate_html_report(results)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        elif output_format == 'text':
            text_content = self._generate_text_report(results)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
        
        if verbose:
            print(f"💾 Results saved to: {output_path}")
    
    def _serialize_for_json(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Сериализовать результаты для JSON."""
        import copy
        
        json_results = copy.deepcopy(results)
        
        # Обрабатываем test_results
        for test_name, result in json_results.get('test_results', {}).items():
            if hasattr(result, '__dict__'):
                # Конвертируем объект в словарь
                json_results['test_results'][test_name] = {
                    'test_name': getattr(result, 'test_name', test_name),
                    'p_value': getattr(result, 'p_value', None),
                    'statistic': getattr(result, 'statistic', None),
                    'effect_size': getattr(result, 'effect_size', None),
                    'is_significant': getattr(result, 'is_significant', None),
                    'interpretation': getattr(result, 'interpretation', None)
                }
        
        return json_results
    
    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """Сгенерировать HTML отчет."""
        symbol = results['metadata']['symbol']
        timeframe = results['metadata']['timeframe']
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BQuant Hypothesis Testing: {symbol} {timeframe}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ddd; }}
        .significant {{ border-left-color: #28a745; background: #f8fff9; }}
        .not-significant {{ border-left-color: #6c757d; background: #f8f9fa; }}
        .failed {{ border-left-color: #dc3545; background: #fff8f8; }}
        .summary {{ padding: 15px; background: #e9ecef; border-radius: 5px; }}
        .recommendations {{ padding: 15px; background: #fff3cd; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BQuant Hypothesis Testing Report</h1>
        <p><strong>Symbol:</strong> {symbol} | <strong>Timeframe:</strong> {timeframe}</p>
        <p><strong>Testing Date:</strong> {results['metadata']['testing_date']}</p>
        <p><strong>Alpha Level:</strong> {results['metadata']['alpha_level']}</p>
    </div>
    
    <div class="section">
        <h2>Testing Summary</h2>
        <div class="summary">
            <p><strong>Total Tests:</strong> {results['testing_summary']['total_tests']}</p>
            <p><strong>Successful Tests:</strong> {results['testing_summary']['successful_tests']}</p>
            <p><strong>Significant Results:</strong> {results['testing_summary']['significant_results']}</p>
            <p><strong>Significance Rate:</strong> {results['testing_summary']['significance_rate']:.1%}</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Test Results</h2>
"""
        
        for test_name, result in results['test_results'].items():
            test_title = self.available_tests.get(test_name, test_name)
            
            if isinstance(result, dict) and 'error' in result:
                html += f'        <div class="test-result failed">\n'
                html += f'            <h3>{test_title}</h3>\n'
                html += f'            <p><strong>Status:</strong> Failed</p>\n'
                html += f'            <p><strong>Error:</strong> {result["error"]}</p>\n'
                html += f'        </div>\n'
            else:
                p_value = None
                if hasattr(result, 'p_value'):
                    p_value = result.p_value
                elif isinstance(result, dict) and 'p_value' in result:
                    p_value = result['p_value']
                
                css_class = "significant" if p_value and p_value < results['metadata']['alpha_level'] else "not-significant"
                
                html += f'        <div class="test-result {css_class}">\n'
                html += f'            <h3>{test_title}</h3>\n'
                html += f'            <p><strong>P-value:</strong> {p_value:.6f if p_value else "N/A"}</p>\n'
                html += f'            <p><strong>Significant:</strong> {"Yes" if p_value and p_value < results["metadata"]["alpha_level"] else "No"}</p>\n'
                html += f'        </div>\n'
        
        html += """
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <div class="recommendations">
            <ul>
"""
        
        for recommendation in results['recommendations']:
            html += f"                <li>{recommendation}</li>\n"
        
        html += """
            </ul>
        </div>
    </div>
    
    <div class="section">
        <p><em>Generated by BQuant Hypothesis Testing Script</em></p>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_text_report(self, results: Dict[str, Any]) -> str:
        """Сгенерировать текстовый отчет."""
        symbol = results['metadata']['symbol']
        timeframe = results['metadata']['timeframe']
        
        report = f"""
BQuant Hypothesis Testing Report
{'=' * 50}

Symbol: {symbol}
Timeframe: {timeframe}
Testing Date: {results['metadata']['testing_date']}
Alpha Level: {results['metadata']['alpha_level']}

TESTING SUMMARY
{'-' * 20}
Total Tests: {results['testing_summary']['total_tests']}
Successful Tests: {results['testing_summary']['successful_tests']}
Significant Results: {results['testing_summary']['significant_results']}
Significance Rate: {results['testing_summary']['significance_rate']:.1%}

TEST RESULTS
{'-' * 20}
"""
        
        for test_name, result in results['test_results'].items():
            test_title = self.available_tests.get(test_name, test_name)
            
            if isinstance(result, dict) and 'error' in result:
                report += f"\n{test_title}: FAILED\n"
                report += f"  Error: {result['error']}\n"
            else:
                p_value = None
                if hasattr(result, 'p_value'):
                    p_value = result.p_value
                elif isinstance(result, dict) and 'p_value' in result:
                    p_value = result['p_value']
                
                significance = "SIGNIFICANT" if p_value and p_value < results['metadata']['alpha_level'] else "NOT SIGNIFICANT"
                
                report += f"\n{test_title}: {significance}\n"
                report += f"  P-value: {p_value:.6f if p_value else 'N/A'}\n"
        
        report += f"\nRECOMMENDATIONS\n{'-' * 20}\n"
        for i, recommendation in enumerate(results['recommendations'], 1):
            report += f"{i}. {recommendation}\n"
        
        report += f"\nGenerated by BQuant v{results['metadata']['bquant_version']}\n"
        
        return report
    
    def _display_results(self, results: Dict[str, Any], output_format: str, verbose: bool):
        """Вывести результаты на экран."""
        if not verbose and output_format == 'json':
            # Краткий вывод для JSON
            print("\n" + "="*50)
            print("BQuant Hypothesis Testing Results")
            print("="*50)
            print(f"Symbol: {results['metadata']['symbol']}")
            print(f"Successful Tests: {results['testing_summary']['successful_tests']}")
            print(f"Significant Results: {results['testing_summary']['significant_results']}")
            return
        
        if output_format == 'text' or verbose:
            print(self._generate_text_report(results))


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description="BQuant Statistical Hypothesis Testing Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_hypotheses.py XAUUSD 1h
  python test_hypotheses.py tv_xauusd_1h --sample-data
  python test_hypotheses.py EURUSD 15m --tests duration,slope --output results.json
  python test_hypotheses.py XAUUSD 1h --all-tests --verbose

Available Tests:
  duration    - Zone Duration Analysis
  slope       - Histogram Slope Test
  asymmetry   - Bull/Bear Asymmetry Test
  patterns    - Sequence Patterns Test
  volatility  - Volatility Effects Test
        """
    )
    
    parser.add_argument(
        'symbol',
        type=str,
        help='Symbol to analyze (e.g., XAUUSD) or sample dataset name (e.g., tv_xauusd_1h)'
    )
    
    parser.add_argument(
        'timeframe',
        type=str,
        help='Timeframe (e.g., 1h, 15m, 4h)'
    )
    
    parser.add_argument(
        '--sample-data',
        action='store_true',
        help='Use embedded sample data'
    )
    
    parser.add_argument(
        '--tests',
        type=str,
        help='Comma-separated list of tests to run (e.g., duration,slope,asymmetry)'
    )
    
    parser.add_argument(
        '--all-tests',
        action='store_true',
        help='Run all available tests'
    )
    
    parser.add_argument(
        '--alpha',
        type=float,
        default=0.05,
        help='Significance level (default: 0.05)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'html', 'text'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - validate inputs without testing'
    )
    
    args = parser.parse_args()
    
    # Обработка списка тестов
    tests_list = None
    if args.tests:
        tests_list = [t.strip() for t in args.tests.split(',')]
    
    # Создаем экземпляр скрипта
    script = HypothesisTestingScript()
    
    try:
        if args.dry_run:
            print(f"[OK] Dry run: Would test hypotheses for {args.symbol} {args.timeframe}")
            print(f"   Sample data: {args.sample_data}")
            print(f"   Tests: {tests_list or 'default'}")
            print(f"   All tests: {args.all_tests}")
            print(f"   Alpha: {args.alpha}")
            return 0
        
        # Выполняем тестирование
        results = script.test_hypotheses(
            symbol=args.symbol,
            timeframe=args.timeframe,
            tests=tests_list,
            use_sample_data=args.sample_data,
            all_tests=args.all_tests,
            alpha=args.alpha,
            output_format=args.output_format,
            output_file=args.output,
            verbose=args.verbose
        )
        
        if args.verbose:
            print(f"\n🎉 Hypothesis testing completed successfully!")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        logger.error(f"Hypothesis testing script failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
