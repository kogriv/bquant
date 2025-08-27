#!/usr/bin/env python3
"""
BQuant Batch Analysis Script

Выполняет пакетный анализ для множества инструментов и таймфреймов.
Поддерживает параллельное выполнение и агрегированные отчеты.

Usage:
    python batch_analysis.py --symbols XAUUSD,EURUSD --timeframes 1h,4h
    python batch_analysis.py --config batch_config.yaml
    python batch_analysis.py --sample-data --all-datasets
    python batch_analysis.py --symbols XAUUSD --timeframes 1h,15m,4h --parallel
"""

import sys
import os
import argparse
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bquant.core.logging_config import get_logger
from bquant.data.samples import list_dataset_names

# Импортируем другие скрипты анализа
from run_macd_analysis import MACDAnalysisScript
from test_hypotheses import HypothesisTestingScript

logger = get_logger(__name__)


class BatchAnalysisScript:
    """
    Скрипт для пакетного анализа множества финансовых инструментов.
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.BatchAnalysisScript")
        self.output_dir = Path("./output/batch")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Инициализируем компонентные скрипты
        self.macd_script = MACDAnalysisScript()
        self.hypothesis_script = HypothesisTestingScript()
    
    def run_batch_analysis(
        self,
        symbols: List[str],
        timeframes: List[str],
        use_sample_data: bool = False,
        all_datasets: bool = False,
        include_macd: bool = True,
        include_hypotheses: bool = True,
        parallel: bool = False,
        max_workers: int = 4,
        config_file: Optional[str] = None,
        output_format: str = "json",
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Выполнить пакетный анализ.
        
        Args:
            symbols: Список символов для анализа
            timeframes: Список таймфреймов
            use_sample_data: Использовать встроенные sample данные
            all_datasets: Анализировать все доступные datasets
            include_macd: Включить MACD анализ
            include_hypotheses: Включить тестирование гипотез
            parallel: Использовать параллельное выполнение
            max_workers: Максимальное количество потоков
            config_file: Путь к файлу конфигурации
            output_format: Формат вывода
            verbose: Подробный вывод
        
        Returns:
            Словарь с результатами пакетного анализа
        """
        self.logger.info("Starting batch analysis")
        
        batch_start = datetime.now()
        
        try:
            # Загрузка конфигурации
            config = self._load_config(config_file, verbose)
            
            # Определение задач для анализа
            tasks = self._prepare_tasks(
                symbols, timeframes, use_sample_data, 
                all_datasets, config, verbose
            )
            
            if not tasks:
                raise ValueError("No analysis tasks prepared")
            
            if verbose:
                print(f"📋 Prepared {len(tasks)} analysis tasks")
                if parallel:
                    print(f"🚀 Running in parallel with {max_workers} workers")
                else:
                    print(f"⏯️  Running sequentially")
            
            # Выполнение анализа
            if parallel and len(tasks) > 1:
                results = self._run_parallel_analysis(
                    tasks, include_macd, include_hypotheses, 
                    max_workers, verbose
                )
            else:
                results = self._run_sequential_analysis(
                    tasks, include_macd, include_hypotheses, verbose
                )
            
            # Агрегация результатов
            aggregated_results = self._aggregate_results(
                results, batch_start, verbose
            )
            
            # Сохранение результатов
            self._save_batch_results(
                aggregated_results, output_format, verbose
            )
            
            # Вывод сводки
            self._display_batch_summary(aggregated_results, verbose)
            
            self.logger.info("Batch analysis completed")
            return aggregated_results
            
        except Exception as e:
            self.logger.error(f"Batch analysis failed: {e}")
            if verbose:
                print(f"❌ Batch analysis failed: {e}")
            raise
    
    def _load_config(self, config_file: Optional[str], verbose: bool) -> Dict[str, Any]:
        """Загрузить конфигурацию из файла."""
        if not config_file:
            return {}
        
        config_path = Path(config_file)
        if not config_path.exists():
            self.logger.warning(f"Config file not found: {config_file}")
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            
            if verbose:
                print(f"📄 Loaded config from: {config_file}")
            
            return config or {}
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            if verbose:
                print(f"⚠️  Failed to load config: {e}")
            return {}
    
    def _prepare_tasks(
        self,
        symbols: List[str],
        timeframes: List[str],
        use_sample_data: bool,
        all_datasets: bool,
        config: Dict[str, Any],
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """Подготовить задачи для анализа."""
        tasks = []
        
        # Получаем параметры из конфигурации
        config_symbols = config.get('symbols', [])
        config_timeframes = config.get('timeframes', [])
        
        # Объединяем символы
        all_symbols = list(set(symbols + config_symbols))
        all_timeframes = list(set(timeframes + config_timeframes))
        
        if all_datasets:
            # Используем все доступные datasets
            available_datasets = list_dataset_names()
            if verbose:
                print(f"📦 Using all {len(available_datasets)} available datasets")
            
            for dataset in available_datasets:
                # Для sample данных используем стандартные таймфреймы
                task_timeframes = all_timeframes or ['1h']
                for timeframe in task_timeframes:
                    tasks.append({
                        'symbol': dataset,
                        'timeframe': timeframe,
                        'use_sample_data': True,
                        'is_dataset': True
                    })
        
        elif use_sample_data and not all_symbols:
            # Используем доступные datasets если символы не указаны
            available_datasets = list_dataset_names()
            if available_datasets:
                if verbose:
                    print(f"📦 Using available datasets: {available_datasets}")
                
                for dataset in available_datasets[:2]:  # Ограничиваем первыми двумя
                    task_timeframes = all_timeframes or ['1h']
                    for timeframe in task_timeframes:
                        tasks.append({
                            'symbol': dataset,
                            'timeframe': timeframe,
                            'use_sample_data': True,
                            'is_dataset': True
                        })
        
        else:
            # Используем указанные символы и таймфреймы
            symbols_to_use = all_symbols or ['XAUUSD']  # Дефолтный символ
            timeframes_to_use = all_timeframes or ['1h']  # Дефолтный таймфрейм
            
            for symbol in symbols_to_use:
                for timeframe in timeframes_to_use:
                    tasks.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'use_sample_data': use_sample_data,
                        'is_dataset': False
                    })
        
        if verbose:
            print(f"📋 Prepared {len(tasks)} analysis tasks:")
            for i, task in enumerate(tasks[:5], 1):  # Показываем первые 5
                print(f"   {i}. {task['symbol']} {task['timeframe']}")
            if len(tasks) > 5:
                print(f"   ... and {len(tasks) - 5} more")
        
        return tasks
    
    def _run_sequential_analysis(
        self,
        tasks: List[Dict[str, Any]],
        include_macd: bool,
        include_hypotheses: bool,
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """Выполнить анализ последовательно."""
        results = []
        
        for i, task in enumerate(tasks, 1):
            if verbose:
                print(f"\n⏯️  Task {i}/{len(tasks)}: {task['symbol']} {task['timeframe']}")
            
            task_result = self._analyze_single_task(
                task, include_macd, include_hypotheses, verbose
            )
            
            results.append(task_result)
            
            if verbose:
                status = "✅ Success" if task_result['success'] else "❌ Failed"
                print(f"   {status}")
        
        return results
    
    def _run_parallel_analysis(
        self,
        tasks: List[Dict[str, Any]],
        include_macd: bool,
        include_hypotheses: bool,
        max_workers: int,
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """Выполнить анализ параллельно."""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запускаем все задачи
            future_to_task = {
                executor.submit(
                    self._analyze_single_task,
                    task, include_macd, include_hypotheses, False
                ): task for task in tasks
            }
            
            # Собираем результаты
            completed = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                completed += 1
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if verbose:
                        status = "✅ Success" if result['success'] else "❌ Failed"
                        print(f"🚀 [{completed}/{len(tasks)}] {task['symbol']} {task['timeframe']} - {status}")
                
                except Exception as e:
                    self.logger.error(f"Task failed: {task['symbol']} {task['timeframe']}: {e}")
                    results.append({
                        'task': task,
                        'success': False,
                        'error': str(e),
                        'macd_result': None,
                        'hypothesis_result': None
                    })
                    
                    if verbose:
                        print(f"🚀 [{completed}/{len(tasks)}] {task['symbol']} {task['timeframe']} - ❌ Failed: {e}")
        
        return results
    
    def _analyze_single_task(
        self,
        task: Dict[str, Any],
        include_macd: bool,
        include_hypotheses: bool,
        verbose: bool
    ) -> Dict[str, Any]:
        """Выполнить анализ одной задачи."""
        symbol = task['symbol']
        timeframe = task['timeframe']
        use_sample_data = task['use_sample_data']
        
        result = {
            'task': task,
            'success': False,
            'macd_result': None,
            'hypothesis_result': None,
            'error': None
        }
        
        try:
            # MACD анализ
            if include_macd:
                try:
                    macd_result = self.macd_script.analyze_symbol(
                        symbol=symbol,
                        timeframe=timeframe,
                        use_sample_data=use_sample_data,
                        verbose=False
                    )
                    result['macd_result'] = macd_result
                except Exception as e:
                    self.logger.warning(f"MACD analysis failed for {symbol}: {e}")
                    result['macd_error'] = str(e)
            
            # Тестирование гипотез
            if include_hypotheses:
                try:
                    hypothesis_result = self.hypothesis_script.test_hypotheses(
                        symbol=symbol,
                        timeframe=timeframe,
                        use_sample_data=use_sample_data,
                        verbose=False
                    )
                    result['hypothesis_result'] = hypothesis_result
                except Exception as e:
                    self.logger.warning(f"Hypothesis testing failed for {symbol}: {e}")
                    result['hypothesis_error'] = str(e)
            
            # Считаем успешным если хотя бы один анализ прошел
            if result['macd_result'] or result['hypothesis_result']:
                result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Task analysis failed for {symbol}: {e}")
        
        return result
    
    def _aggregate_results(
        self,
        results: List[Dict[str, Any]],
        batch_start,
        verbose: bool
    ) -> Dict[str, Any]:
        """Агрегировать результаты анализа."""
        batch_duration = datetime.now() - batch_start
        
        # Базовая статистика
        total_tasks = len(results)
        successful_tasks = len([r for r in results if r['success']])
        failed_tasks = total_tasks - successful_tasks
        
        macd_successful = len([r for r in results if r.get('macd_result')])
        hypothesis_successful = len([r for r in results if r.get('hypothesis_result')])
        
        # Агрегация по символам
        symbols_analysis = {}
        timeframes_analysis = {}
        
        for result in results:
            if not result['success']:
                continue
            
            task = result['task']
            symbol = task['symbol']
            timeframe = task['timeframe']
            
            # Анализ по символам
            if symbol not in symbols_analysis:
                symbols_analysis[symbol] = {
                    'total_analyses': 0,
                    'successful_analyses': 0,
                    'macd_zones_total': 0,
                    'hypothesis_significant': 0
                }
            
            symbols_analysis[symbol]['total_analyses'] += 1
            symbols_analysis[symbol]['successful_analyses'] += 1
            
            # MACD статистика
            if result.get('macd_result'):
                macd_data = result['macd_result'].get('macd_analysis', {})
                zones_stats = macd_data.get('zones_statistics', {})
                symbols_analysis[symbol]['macd_zones_total'] += zones_stats.get('total_zones', 0)
            
            # Гипотезы статистика
            if result.get('hypothesis_result'):
                hyp_data = result['hypothesis_result'].get('testing_summary', {})
                symbols_analysis[symbol]['hypothesis_significant'] += hyp_data.get('significant_results', 0)
            
            # Анализ по таймфреймам
            if timeframe not in timeframes_analysis:
                timeframes_analysis[timeframe] = {
                    'total_analyses': 0,
                    'avg_zones': 0,
                    'avg_significant_tests': 0
                }
            
            timeframes_analysis[timeframe]['total_analyses'] += 1
        
        # Вычисляем средние значения для таймфреймов
        for tf_data in timeframes_analysis.values():
            if tf_data['total_analyses'] > 0:
                tf_results = [r for r in results if r['success'] and r['task']['timeframe'] == tf_data]
                
                # Средние зоны
                total_zones = 0
                total_significant = 0
                count = 0
                
                for result in results:
                    if result['success'] and result['task']['timeframe'] in timeframes_analysis:
                        if result.get('macd_result'):
                            zones = result['macd_result'].get('macd_analysis', {}).get('zones_statistics', {}).get('total_zones', 0)
                            total_zones += zones
                        
                        if result.get('hypothesis_result'):
                            significant = result['hypothesis_result'].get('testing_summary', {}).get('significant_results', 0)
                            total_significant += significant
                        
                        count += 1
                
                if count > 0:
                    tf_data['avg_zones'] = total_zones / count
                    tf_data['avg_significant_tests'] = total_significant / count
        
        # Формирование агрегированных результатов
        aggregated = {
            'metadata': {
                'batch_date': datetime.now().isoformat(),
                'batch_duration_seconds': batch_duration.total_seconds(),
                'bquant_version': '0.0.0-dev'
            },
            'summary': {
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0,
                'macd_successful': macd_successful,
                'hypothesis_successful': hypothesis_successful
            },
            'symbols_analysis': symbols_analysis,
            'timeframes_analysis': timeframes_analysis,
            'detailed_results': results,
            'recommendations': self._generate_batch_recommendations(results, symbols_analysis)
        }
        
        if verbose:
            print(f"\n📊 Batch Analysis Summary:")
            print(f"   • Total tasks: {total_tasks}")
            print(f"   • Successful: {successful_tasks}")
            print(f"   • Success rate: {aggregated['summary']['success_rate']:.1%}")
            print(f"   • Duration: {batch_duration.total_seconds():.1f}s")
        
        return aggregated
    
    def _generate_batch_recommendations(
        self,
        results: List[Dict[str, Any]],
        symbols_analysis: Dict[str, Any]
    ) -> List[str]:
        """Сгенерировать рекомендации на основе пакетного анализа."""
        recommendations = []
        
        successful_count = len([r for r in results if r['success']])
        
        if successful_count == 0:
            recommendations.append("No successful analyses - check data availability and configurations")
            return recommendations
        
        # Анализ по символам
        if symbols_analysis:
            best_symbol = max(symbols_analysis.keys(), 
                            key=lambda s: symbols_analysis[s]['macd_zones_total'])
            
            recommendations.append(f"Most active symbol: {best_symbol} (highest MACD zone activity)")
        
        # Общие рекомендации
        macd_success_rate = len([r for r in results if r.get('macd_result')]) / len(results)
        hyp_success_rate = len([r for r in results if r.get('hypothesis_result')]) / len(results)
        
        if macd_success_rate > 0.8:
            recommendations.append("MACD analysis highly reliable across instruments")
        elif macd_success_rate < 0.5:
            recommendations.append("MACD analysis issues detected - check data quality")
        
        if hyp_success_rate > 0.8:
            recommendations.append("Statistical testing broadly applicable")
        elif hyp_success_rate < 0.5:
            recommendations.append("Statistical testing limited - consider data requirements")
        
        # Рекомендации по диверсификации
        unique_symbols = len(set(r['task']['symbol'] for r in results if r['success']))
        if unique_symbols > 3:
            recommendations.append("Good diversification across multiple instruments")
        else:
            recommendations.append("Consider expanding analysis to more instruments")
        
        return recommendations
    
    def _save_batch_results(
        self,
        results: Dict[str, Any],
        output_format: str,
        verbose: bool
    ):
        """Сохранить результаты пакетного анализа."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == 'json':
            output_file = self.output_dir / f"batch_analysis_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        elif output_format == 'html':
            output_file = self.output_dir / f"batch_analysis_{timestamp}.html"
            html_content = self._generate_batch_html_report(results)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        # Всегда создаем краткую сводку
        summary_file = self.output_dir / f"batch_summary_{timestamp}.txt"
        summary_content = self._generate_batch_summary(results)
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        if verbose:
            print(f"💾 Batch results saved:")
            print(f"   • Main: {output_file}")
            print(f"   • Summary: {summary_file}")
    
    def _generate_batch_html_report(self, results: Dict[str, Any]) -> str:
        """Сгенерировать HTML отчет пакетного анализа."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BQuant Batch Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .summary {{ padding: 15px; background: #e9ecef; border-radius: 5px; }}
        .success {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BQuant Batch Analysis Report</h1>
        <p><strong>Analysis Date:</strong> {results['metadata']['batch_date']}</p>
        <p><strong>Duration:</strong> {results['metadata']['batch_duration_seconds']:.1f} seconds</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <div class="summary">
            <p><strong>Total Tasks:</strong> {results['summary']['total_tasks']}</p>
            <p><strong>Successful:</strong> <span class="success">{results['summary']['successful_tasks']}</span></p>
            <p><strong>Failed:</strong> <span class="failed">{results['summary']['failed_tasks']}</span></p>
            <p><strong>Success Rate:</strong> {results['summary']['success_rate']:.1%}</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
"""
        
        for recommendation in results['recommendations']:
            html += f"            <li>{recommendation}</li>\n"
        
        html += """
        </ul>
    </div>
    
    <div class="section">
        <p><em>Generated by BQuant Batch Analysis Script</em></p>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_batch_summary(self, results: Dict[str, Any]) -> str:
        """Сгенерировать краткую сводку пакетного анализа."""
        summary = f"""
BQuant Batch Analysis Summary
{'=' * 50}

Analysis Date: {results['metadata']['batch_date']}
Duration: {results['metadata']['batch_duration_seconds']:.1f} seconds

OVERALL RESULTS
{'-' * 20}
Total Tasks: {results['summary']['total_tasks']}
Successful: {results['summary']['successful_tasks']}
Failed: {results['summary']['failed_tasks']}
Success Rate: {results['summary']['success_rate']:.1%}

COMPONENT ANALYSIS
{'-' * 20}
MACD Successful: {results['summary']['macd_successful']}
Hypothesis Successful: {results['summary']['hypothesis_successful']}

RECOMMENDATIONS
{'-' * 20}
"""
        
        for i, recommendation in enumerate(results['recommendations'], 1):
            summary += f"{i}. {recommendation}\n"
        
        summary += f"\nGenerated by BQuant v{results['metadata']['bquant_version']}\n"
        
        return summary
    
    def _display_batch_summary(self, results: Dict[str, Any], verbose: bool):
        """Вывести сводку пакетного анализа."""
        print("\n" + "="*60)
        print("BQuant Batch Analysis Completed")
        print("="*60)
        print(f"Total Tasks: {results['summary']['total_tasks']}")
        print(f"Successful: {results['summary']['successful_tasks']}")
        print(f"Success Rate: {results['summary']['success_rate']:.1%}")
        print(f"Duration: {results['metadata']['batch_duration_seconds']:.1f}s")
        
        if verbose:
            print(f"\nRecommendations:")
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"  {i}. {rec}")


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description="BQuant Batch Analysis Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_analysis.py --symbols XAUUSD,EURUSD --timeframes 1h,4h
  python batch_analysis.py --config batch_config.yaml
  python batch_analysis.py --sample-data --all-datasets
  python batch_analysis.py --symbols XAUUSD --timeframes 1h,15m,4h --parallel
        """
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of symbols (e.g., XAUUSD,EURUSD)'
    )
    
    parser.add_argument(
        '--timeframes',
        type=str,
        help='Comma-separated list of timeframes (e.g., 1h,4h,1d)'
    )
    
    parser.add_argument(
        '--sample-data',
        action='store_true',
        help='Use embedded sample data'
    )
    
    parser.add_argument(
        '--all-datasets',
        action='store_true',
        help='Analyze all available sample datasets'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration file path (YAML or JSON)'
    )
    
    parser.add_argument(
        '--include-macd',
        action='store_true',
        default=True,
        help='Include MACD analysis (default: True)'
    )
    
    parser.add_argument(
        '--include-hypotheses',
        action='store_true',
        default=True,
        help='Include hypothesis testing (default: True)'
    )
    
    parser.add_argument(
        '--no-macd',
        action='store_true',
        help='Exclude MACD analysis'
    )
    
    parser.add_argument(
        '--no-hypotheses',
        action='store_true',
        help='Exclude hypothesis testing'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel processing'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='Maximum number of parallel workers (default: 4)'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'html'],
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
        help='Dry run - show what would be analyzed'
    )
    
    args = parser.parse_args()
    
    # Обработка списков
    symbols = []
    timeframes = []
    
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
    
    if args.timeframes:
        timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    
    # Обработка флагов включения/исключения
    include_macd = args.include_macd and not args.no_macd
    include_hypotheses = args.include_hypotheses and not args.no_hypotheses
    
    # Создаем экземпляр скрипта
    script = BatchAnalysisScript()
    
    try:
        if args.dry_run:
            print(f"✅ Dry run: Would analyze batch processing")
            print(f"   Symbols: {symbols or 'auto-detect'}")
            print(f"   Timeframes: {timeframes or 'auto-detect'}")
            print(f"   Sample data: {args.sample_data}")
            print(f"   All datasets: {args.all_datasets}")
            print(f"   Include MACD: {include_macd}")
            print(f"   Include hypotheses: {include_hypotheses}")
            print(f"   Parallel: {args.parallel}")
            return 0
        
        # Выполняем пакетный анализ
        results = script.run_batch_analysis(
            symbols=symbols,
            timeframes=timeframes,
            use_sample_data=args.sample_data,
            all_datasets=args.all_datasets,
            include_macd=include_macd,
            include_hypotheses=include_hypotheses,
            parallel=args.parallel,
            max_workers=args.max_workers,
            config_file=args.config,
            output_format=args.output_format,
            verbose=args.verbose
        )
        
        if args.verbose:
            print(f"\n🎉 Batch analysis completed successfully!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Batch analysis script failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
