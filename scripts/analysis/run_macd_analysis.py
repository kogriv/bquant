#!/usr/bin/env python3
"""
BQuant MACD Analysis Script

Выполняет полный MACD анализ для указанного инструмента и таймфрейма.
Поддерживает работу с sample данными и внешними источниками.

Usage:
    python run_macd_analysis.py XAUUSD 1h
    python run_macd_analysis.py tv_xauusd_1h --sample-data
    python run_macd_analysis.py EURUSD 15m --output results.json
    python run_macd_analysis.py XAUUSD 1h --output-format html --include-charts
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Добавляем корневую папку проекта в path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from bquant.core.logging_config import get_logger
from bquant.data.samples import get_sample_data, list_dataset_names, validate_dataset_name
from bquant.indicators import MACDZoneAnalyzer

logger = get_logger(__name__)


class MACDAnalysisScript:
    """
    Скрипт для выполнения MACD анализа финансовых инструментов.
    """
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.MACDAnalysisScript")
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
    
    def analyze_symbol(
        self, 
        symbol: str, 
        timeframe: str,
        use_sample_data: bool = False,
        output_format: str = "json",
        output_file: Optional[str] = None,
        include_charts: bool = False,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Выполнить MACD анализ для указанного символа и таймфрейма.
        
        Args:
            symbol: Символ инструмента или название sample dataset
            timeframe: Таймфрейм данных
            use_sample_data: Использовать встроенные sample данные
            output_format: Формат вывода ('json', 'html', 'text')
            output_file: Путь к файлу для сохранения результатов
            include_charts: Включить графики в отчет
            verbose: Подробный вывод
        
        Returns:
            Словарь с результатами анализа
        """
        self.logger.info(f"Starting MACD analysis for {symbol} {timeframe}")
        
        analysis_start = datetime.now()
        
        try:
            # Загрузка данных
            data = self._load_data(symbol, timeframe, use_sample_data, verbose)
            
            # Выполнение MACD анализа
            analyzer = MACDZoneAnalyzer()
            
            if verbose:
                print(f"📊 Loaded {len(data)} data points for {symbol}")
                print(f"🔧 Initializing MACD analyzer...")
            
            # Полный анализ (включает расчет MACD, идентификацию зон, расчет признаков)
            complete_analysis = analyzer.analyze_complete(data)
            
            # Извлекаем компоненты из результата анализа
            zones = complete_analysis.zones
            macd_data = data  # Данные с рассчитанными индикаторами уже в исходном data
            
            if verbose:
                print(f"🎯 Found {len(zones)} MACD zones")
                print(f"📈 Analysis completed successfully")
            
            # Формирование результатов
            results = self._format_results(
                symbol, timeframe, data, macd_data, zones, 
                complete_analysis, analysis_start, verbose
            )
            
            # Сохранение результатов
            if output_file:
                self._save_results(
                    results, output_file, output_format, 
                    include_charts, verbose
                )
            
            # Вывод результатов
            self._display_results(results, output_format, verbose)
            
            self.logger.info(f"MACD analysis completed for {symbol}")
            return results
            
        except Exception as e:
            self.logger.error(f"MACD analysis failed for {symbol}: {e}")
            if verbose:
                print(f"[ERROR] Analysis failed: {e}")
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
    
    def _format_results(
        self, 
        symbol: str, 
        timeframe: str,
        data, 
        macd_data, 
        zones, 
        complete_analysis,
        analysis_start,
        verbose: bool
    ) -> Dict[str, Any]:
        """Сформировать результаты анализа."""
        analysis_duration = datetime.now() - analysis_start
        
        # Базовая статистика
        basic_stats = {
            'total_periods': len(data),
            'data_start': str(data['time'].iloc[0]) if 'time' in data.columns else None,
            'data_end': str(data['time'].iloc[-1]) if 'time' in data.columns else None,
            'price_range': {
                'min': float(data['low'].min()),
                'max': float(data['high'].max()),
                'current': float(data['close'].iloc[-1])
            }
        }
        
        # Статистика зон
        zones_stats = {
            'total_zones': len(zones),
            'bull_zones': len([z for z in zones if hasattr(z, 'type') and z.type == 'bull']),
            'bear_zones': len([z for z in zones if hasattr(z, 'type') and z.type == 'bear']),
            'avg_duration': sum(getattr(z, 'duration', 0) for z in zones) / len(zones) if zones else 0
        }
        
        # MACD статистика
        macd_stats = {
            'current_macd': float(macd_data['macd'].iloc[-1]) if 'macd' in macd_data.columns else None,
            'current_signal': float(macd_data['signal'].iloc[-1]) if 'signal' in macd_data.columns else None,
            'current_histogram': None
        }
        
        if macd_stats['current_macd'] and macd_stats['current_signal']:
            macd_stats['current_histogram'] = macd_stats['current_macd'] - macd_stats['current_signal']
        
        results = {
            'metadata': {
                'symbol': symbol,
                'timeframe': timeframe,
                'analysis_date': datetime.now().isoformat(),
                'analysis_duration_seconds': analysis_duration.total_seconds(),
                'bquant_version': '0.0.0-dev'
            },
            'data_info': basic_stats,
            'macd_analysis': {
                'zones': [self._zone_to_dict(z) for z in zones],
                'zones_statistics': zones_stats,
                'macd_statistics': macd_stats,
                'complete_analysis': {
                    'statistics': complete_analysis.statistics,
                    'hypothesis_tests': complete_analysis.hypothesis_tests,
                    'sequence_analysis': complete_analysis.sequence_analysis,
                    'clustering': complete_analysis.clustering
                }
            },
            'summary': {
                'recommendation': self._generate_recommendation(zones, macd_stats),
                'key_insights': self._generate_insights(zones, zones_stats, macd_stats)
            }
        }
        
        if verbose:
            print(f"📊 Analysis summary:")
            print(f"   • Total zones: {zones_stats['total_zones']}")
            print(f"   • Bull zones: {zones_stats['bull_zones']}")
            print(f"   • Bear zones: {zones_stats['bear_zones']}")
            print(f"   • Current MACD: {macd_stats['current_macd']:.4f}" if macd_stats['current_macd'] else "   • Current MACD: N/A")
        
        return results
    
    def _zone_to_dict(self, zone) -> Dict[str, Any]:
        """Конвертировать ZoneInfo объект в словарь."""
        if hasattr(zone, '__dict__'):
            zone_dict = {
                'zone_id': getattr(zone, 'zone_id', None),
                'type': getattr(zone, 'type', None),
                'start_idx': getattr(zone, 'start_idx', None),
                'end_idx': getattr(zone, 'end_idx', None),
                'duration': getattr(zone, 'duration', None),
                'start_time': str(getattr(zone, 'start_time', None)),
                'end_time': str(getattr(zone, 'end_time', None)),
                'features': getattr(zone, 'features', None)
            }
            return zone_dict
        else:
            # Если это уже словарь
            return zone
    
    def _generate_recommendation(self, zones, macd_stats) -> str:
        """Сгенерировать торговую рекомендацию."""
        if not zones:
            return "Insufficient data for recommendation"
        
        latest_zone = zones[-1] if zones else None
        current_histogram = macd_stats.get('current_histogram')
        
        if latest_zone and current_histogram is not None:
            zone_type = getattr(latest_zone, 'type', None) if hasattr(latest_zone, 'type') else latest_zone.get('type')
            if zone_type == 'bull' and current_histogram > 0:
                return "BULLISH: Current uptrend with positive MACD momentum"
            elif zone_type == 'bear' and current_histogram < 0:
                return "BEARISH: Current downtrend with negative MACD momentum"
            else:
                return "NEUTRAL: Mixed signals, monitor for trend confirmation"
        
        return "NEUTRAL: Insufficient signal clarity"
    
    def _generate_insights(self, zones, zones_stats, macd_stats) -> list:
        """Сгенерировать ключевые инсайты."""
        insights = []
        
        if zones_stats['total_zones'] > 0:
            bull_ratio = zones_stats['bull_zones'] / zones_stats['total_zones']
            if bull_ratio > 0.6:
                insights.append("Predominantly bullish market sentiment")
            elif bull_ratio < 0.4:
                insights.append("Predominantly bearish market sentiment")
            else:
                insights.append("Balanced bull/bear market phases")
        
        if zones_stats['avg_duration'] > 0:
            if zones_stats['avg_duration'] > 20:
                insights.append("Long-duration zones indicate strong trends")
            else:
                insights.append("Short-duration zones suggest volatile market")
        
        current_histogram = macd_stats.get('current_histogram')
        if current_histogram is not None:
            if abs(current_histogram) > 2:
                insights.append("Strong MACD momentum detected")
            else:
                insights.append("Weak MACD momentum, potential consolidation")
        
        return insights
    
    def _save_results(
        self, 
        results: Dict[str, Any], 
        output_file: str,
        output_format: str,
        include_charts: bool,
        verbose: bool
    ):
        """Сохранить результаты в файл."""
        output_path = Path(output_file)
        
        if output_format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        elif output_format == 'html':
            html_content = self._generate_html_report(results, include_charts)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        elif output_format == 'text':
            text_content = self._generate_text_report(results)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
        
        if verbose:
            print(f"💾 Results saved to: {output_path}")
    
    def _generate_html_report(self, results: Dict[str, Any], include_charts: bool) -> str:
        """Сгенерировать HTML отчет."""
        symbol = results['metadata']['symbol']
        timeframe = results['metadata']['timeframe']
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BQuant MACD Analysis: {symbol} {timeframe}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
        .recommendation {{ padding: 15px; border-left: 4px solid #007acc; background: #f0f8ff; }}
        .insights {{ padding: 15px; background: #fff9e6; border-radius: 5px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BQuant MACD Analysis Report</h1>
        <p><strong>Symbol:</strong> {symbol} | <strong>Timeframe:</strong> {timeframe}</p>
        <p><strong>Analysis Date:</strong> {results['metadata']['analysis_date']}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <div class="recommendation">
            <strong>Recommendation:</strong> {results['summary']['recommendation']}
        </div>
    </div>
    
    <div class="section">
        <h2>Key Metrics</h2>
        <div class="metric">
            <strong>Total Zones:</strong> {results['macd_analysis']['zones_statistics']['total_zones']}
        </div>
        <div class="metric">
            <strong>Bull Zones:</strong> {results['macd_analysis']['zones_statistics']['bull_zones']}
        </div>
        <div class="metric">
            <strong>Bear Zones:</strong> {results['macd_analysis']['zones_statistics']['bear_zones']}
        </div>
        <div class="metric">
            <strong>Average Duration:</strong> {results['macd_analysis']['zones_statistics']['avg_duration']:.1f}
        </div>
    </div>
    
    <div class="section">
        <h2>Key Insights</h2>
        <div class="insights">
            <ul>
"""
        
        for insight in results['summary']['key_insights']:
            html += f"                <li>{insight}</li>\n"
        
        html += """
            </ul>
        </div>
    </div>
    
    <div class="section">
        <p><em>Generated by BQuant MACD Analysis Script</em></p>
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
BQuant MACD Analysis Report
{'=' * 50}

Symbol: {symbol}
Timeframe: {timeframe}
Analysis Date: {results['metadata']['analysis_date']}

SUMMARY
{'-' * 20}
Recommendation: {results['summary']['recommendation']}

KEY METRICS
{'-' * 20}
Total Zones: {results['macd_analysis']['zones_statistics']['total_zones']}
Bull Zones: {results['macd_analysis']['zones_statistics']['bull_zones']}
Bear Zones: {results['macd_analysis']['zones_statistics']['bear_zones']}
Average Duration: {results['macd_analysis']['zones_statistics']['avg_duration']:.1f}

KEY INSIGHTS
{'-' * 20}
"""
        
        for i, insight in enumerate(results['summary']['key_insights'], 1):
            report += f"{i}. {insight}\n"
        
        report += f"\nGenerated by BQuant v{results['metadata']['bquant_version']}\n"
        
        return report
    
    def _display_results(self, results: Dict[str, Any], output_format: str, verbose: bool):
        """Вывести результаты на экран."""
        if not verbose and output_format == 'json':
            # Краткий вывод для JSON
            print("\n" + "="*50)
            print("BQuant MACD Analysis Results")
            print("="*50)
            print(f"Symbol: {results['metadata']['symbol']}")
            print(f"Recommendation: {results['summary']['recommendation']}")
            print(f"Total Zones: {results['macd_analysis']['zones_statistics']['total_zones']}")
            return
        
        if output_format == 'text' or verbose:
            print(self._generate_text_report(results))


def main():
    """Основная функция CLI."""
    parser = argparse.ArgumentParser(
        description="BQuant MACD Analysis Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_macd_analysis.py XAUUSD 1h
  python run_macd_analysis.py tv_xauusd_1h --sample-data
  python run_macd_analysis.py EURUSD 15m --output results.json
  python run_macd_analysis.py XAUUSD 1h --output-format html --include-charts
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
        '--include-charts',
        action='store_true',
        help='Include charts in HTML output'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - validate inputs without analysis'
    )
    
    args = parser.parse_args()
    
    # Создаем экземпляр скрипта
    script = MACDAnalysisScript()
    
    try:
        if args.dry_run:
            print(f"[OK] Dry run: Would analyze {args.symbol} {args.timeframe}")
            print(f"   Sample data: {args.sample_data}")
            print(f"   Output format: {args.output_format}")
            return 0
        
        # Выполняем анализ
        results = script.analyze_symbol(
            symbol=args.symbol,
            timeframe=args.timeframe,
            use_sample_data=args.sample_data,
            output_format=args.output_format,
            output_file=args.output,
            include_charts=args.include_charts,
            verbose=args.verbose
        )
        
        if args.verbose:
            print(f"\n🎉 Analysis completed successfully!")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        logger.error(f"MACD analysis script failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
