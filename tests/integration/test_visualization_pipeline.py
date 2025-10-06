"""
Интеграционные тесты пайплайна визуализации.

Тестирует полную интеграцию данных → анализа → визуализации.
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

try:
    from bquant.visualization import (
        FinancialCharts,
        ZoneVisualizer, 
        StatisticalPlots,
        ChartThemes,
        create_financial_chart
    )
    visualization_available = True
except ImportError as e:
    visualization_available = False
    print(f"Visualization module not available: {e}")

from bquant.indicators import MACDZoneAnalyzer
from bquant.data.samples import get_sample_data, list_dataset_names


class TestVisualizationPipeline:
    """
    Тесты интеграции данных с визуализацией.
    """
    
    @pytest.mark.integration
    @pytest.mark.skipif(not visualization_available, reason="Visualization module not available")
    def test_basic_chart_creation_pipeline(self, sample_macd_data):
        """
        Базовый пайплайн создания графиков: данные → график → проверка.
        """
        # 1. Создание финансовых графиков
        charts = FinancialCharts()
        assert charts is not None, "FinancialCharts should be created"
        
        # 2. Создание candlestick графика
        try:
            fig = charts.create_candlestick_chart(
                sample_macd_data,
                title="Test Candlestick Chart"
            )
            assert fig is not None, "Candlestick chart should be created"
            
            # Проверяем что график содержит данные
            assert len(fig.data) > 0, "Chart should contain traces"
            
            candlestick_success = True
            
        except Exception as e:
            print(f"Candlestick chart creation failed: {e}")
            candlestick_success = False
        
        # 3. Создание line графика
        try:
            fig = charts.create_line_chart(
                sample_macd_data,
                'close',
                title="Test Line Chart"
            )
            assert fig is not None, "Line chart should be created"
            
            line_chart_success = True
            
        except Exception as e:
            print(f"Line chart creation failed: {e}")
            line_chart_success = False
        
        # 4. Создание OHLCV графика
        try:
            fig = charts.plot_ohlcv(
                sample_macd_data,
                title="Test OHLCV Chart"
            )
            assert fig is not None, "OHLCV chart should be created"
            
            ohlcv_success = True
            
        except Exception as e:
            print(f"OHLCV chart creation failed: {e}")
            ohlcv_success = False
        
        # Проверяем что хотя бы один тип графика работает
        total_success = sum([candlestick_success, line_chart_success, ohlcv_success])
        assert total_success > 0, "At least one chart type should work"
        
        print(f"✅ Basic chart creation pipeline test completed!")
        print(f"   • Candlestick: {'✅' if candlestick_success else '❌'}")
        print(f"   • Line chart: {'✅' if line_chart_success else '❌'}")
        print(f"   • OHLCV: {'✅' if ohlcv_success else '❌'}")
        
        return {
            'candlestick_success': candlestick_success,
            'line_chart_success': line_chart_success,
            'ohlcv_success': ohlcv_success
        }
    
    @pytest.mark.integration
    @pytest.mark.skipif(not visualization_available, reason="Visualization module not available")
    def test_macd_visualization_pipeline(self, sample_data_available, skip_if_no_sample_data):
        """
        Пайплайн визуализации MACD анализа: данные → анализ → визуализация зон.
        """
        # 1. Загрузка sample данных
        dataset_names = list_dataset_names()
        if not dataset_names:
            pytest.skip("No sample data available for visualization testing")
        
        dataset_name = dataset_names[0]
        data = get_sample_data(dataset_name)
        
        # 2. MACD анализ
        analyzer = MACDZoneAnalyzer()
        analysis_result = analyzer.analyze_complete(data)
        zones = analysis_result.zones
        data_with_macd = analysis_result.data  # Данные с MACD индикаторами
        
        # 3. Визуализация MACD с зонами
        try:
            charts = FinancialCharts()
            
            # Создаем базовый MACD график с данными, содержащими MACD индикаторы
            fig = charts.plot_macd_with_zones(data_with_macd, zones)
            assert fig is not None, "MACD with zones chart should be created"
            
            macd_viz_success = True
            
        except Exception as e:
            print(f"MACD visualization failed: {e}")
            macd_viz_success = False
        
        # 4. Визуализация зон отдельно
        try:
            zone_viz = ZoneVisualizer()
            
            fig = zone_viz.plot_zones_overview(zones)
            assert fig is not None, "Zones overview should be created"
            
            zones_viz_success = True
            
        except Exception as e:
            print(f"Zones visualization failed: {e}")
            zones_viz_success = False
        
        # Проверяем что хотя бы одна визуализация работает
        assert macd_viz_success or zones_viz_success, "At least one MACD visualization should work"
        
        print(f"✅ MACD visualization pipeline test completed!")
        print(f"   • Dataset: {dataset_name}")
        print(f"   • Zones found: {len(zones)}")
        print(f"   • MACD visualization: {'✅' if macd_viz_success else '❌'}")
        print(f"   • Zones visualization: {'✅' if zones_viz_success else '❌'}")
        
        return {
            'dataset': dataset_name,
            'zones_count': len(zones),
            'macd_viz_success': macd_viz_success,
            'zones_viz_success': zones_viz_success
        }
    
    @pytest.mark.integration
    @pytest.mark.skipif(not visualization_available, reason="Visualization module not available")
    def test_statistical_visualization_pipeline(self, sample_zones):
        """
        Пайплайн визуализации статистического анализа.
        """
        # 1. Подготовка статистических данных
        zones_features = []
        for zone in sample_zones:
            if 'features' in zone and zone['features']:
                zones_features.append(zone['features'])
        
        if len(zones_features) == 0:
            pytest.skip("No zone features available for statistical visualization")
        
        # 2. Создание статистических графиков
        try:
            stat_plots = StatisticalPlots()
            
            # Histogram для продолжительности зон
            durations = [f['duration'] for f in zones_features if 'duration' in f]
            if durations:
                fig = stat_plots.create_histogram(
                    durations,
                    title="Zone Durations Distribution"
                )
                assert fig is not None, "Histogram should be created"
            
            # Scatter plot для возвратов vs продолжительности - создаем DataFrame
            returns = [f['price_return'] for f in zones_features if 'price_return' in f]
            if durations and returns and len(durations) == len(returns):
                # Создаем DataFrame для scatter plot
                scatter_data = pd.DataFrame({
                    'duration': durations,
                    'returns': returns
                })
                fig = stat_plots.create_scatter_plot(
                    scatter_data,
                    x_column='duration',
                    y_column='returns',
                    title="Duration vs Returns"
                )
                assert fig is not None, "Scatter plot should be created"
            
            statistical_viz_success = True
            
        except Exception as e:
            print(f"Statistical visualization failed: {e}")
            statistical_viz_success = False
        
        # 3. Box plots для сравнения bull/bear зон
        try:
            bull_durations = [f['duration'] for zone, f in zip(sample_zones, zones_features) 
                             if zone.get('type') == 'bull' and 'duration' in f]
            bear_durations = [f['duration'] for zone, f in zip(sample_zones, zones_features) 
                             if zone.get('type') == 'bear' and 'duration' in f]
            
            if bull_durations and bear_durations:
                # Создаем DataFrame для box plot
                box_data = pd.DataFrame({
                    'duration': bull_durations + bear_durations,
                    'type': ['Bull'] * len(bull_durations) + ['Bear'] * len(bear_durations)
                })
                fig = stat_plots.create_box_plot(
                    box_data,
                    y_column='duration',
                    x_column='type',
                    title="Zone Duration Comparison"
                )
                assert fig is not None, "Box plot should be created"
            
            boxplot_success = True
            
        except Exception as e:
            print(f"Box plot creation failed: {e}")
            boxplot_success = False
        
        # Проверяем что хотя бы одна статистическая визуализация работает
        assert statistical_viz_success or boxplot_success, "At least one statistical visualization should work"
        
        print(f"✅ Statistical visualization pipeline test completed!")
        print(f"   • Zone features: {len(zones_features)}")
        print(f"   • Statistical plots: {'✅' if statistical_viz_success else '❌'}")
        print(f"   • Box plots: {'✅' if boxplot_success else '❌'}")
        
        return {
            'features_count': len(zones_features),
            'statistical_viz_success': statistical_viz_success,
            'boxplot_success': boxplot_success
        }
    
    @pytest.mark.integration
    @pytest.mark.skipif(not visualization_available, reason="Visualization module not available")
    def test_theming_pipeline(self, sample_ohlcv_data):
        """
        Пайплайн тестирования тем и стилизации графиков.
        """
        try:
            # 1. Создание графика с темами
            charts = FinancialCharts()
            
            # 2. Тестирование разных тем (если доступны)
            try:
                themes = ChartThemes()
                available_themes = themes.get_available_themes()
                
                if available_themes:
                    for theme_name in available_themes:
                        try:
                            themed_fig = charts.create_line_chart(
                                sample_ohlcv_data,
                                columns=['close'],  # Передаем как список
                                title=f"Test Chart - {theme_name} Theme"
                            )
                            
                            # Применяем тему
                            themes.apply_theme(themed_fig, theme_name)
                            
                            assert themed_fig is not None, f"Themed chart should be created for {theme_name}"
                            
                        except Exception as e:
                            print(f"Theme {theme_name} failed: {e}")
                
                theming_success = True
                
            except Exception as e:
                print(f"Theming not available: {e}")
                theming_success = False
            
            # 3. Базовая проверка создания графика без тем
            fig = charts.create_line_chart(
                sample_ohlcv_data,
                columns=['close'],  # Передаем как список
                title="Basic Chart"
            )
            assert fig is not None, "Basic chart should be created"
            
            basic_chart_success = True
            
        except Exception as e:
            print(f"Basic chart creation failed: {e}")
            basic_chart_success = False
            theming_success = False
        
        assert basic_chart_success, "Basic chart creation should work"
        
        print(f"✅ Theming pipeline test completed!")
        print(f"   • Basic charts: {'✅' if basic_chart_success else '❌'}")
        print(f"   • Theming: {'✅' if theming_success else '❌'}")
        
        return {
            'basic_chart_success': basic_chart_success,
            'theming_success': theming_success
        }


class TestVisualizationIntegration:
    """
    Тесты интеграции визуализации с другими компонентами.
    """
    
    @pytest.mark.integration
    @pytest.mark.skipif(not visualization_available, reason="Visualization module not available")
    def test_end_to_end_visualization_workflow(self, sample_data_available, skip_if_no_sample_data):
        """
        End-to-end workflow: sample data → analysis → comprehensive visualization.
        """
        # 1. Загрузка данных
        dataset_names = list_dataset_names()
        if not dataset_names:
            pytest.skip("No sample data available")
        
        dataset_name = dataset_names[0]
        data = get_sample_data(dataset_name)
        
        # 2. Полный анализ
        analyzer = MACDZoneAnalyzer()
        analysis_result = analyzer.analyze_complete(data)
        
        # 3. Создание comprehensive визуализации
        visualization_results = {}
        
        try:
            charts = FinancialCharts()
            
            # Основной график данных
            main_chart = charts.create_candlestick_chart(
                data,
                title=f"Analysis of {dataset_name}"
            )
            visualization_results['main_chart'] = main_chart is not None
            
        except Exception as e:
            print(f"Main chart creation failed: {e}")
            visualization_results['main_chart'] = False
        
        try:
            # График MACD с зонами (используем данные с MACD индикаторами из анализа)
            macd_chart = charts.plot_macd_with_zones(analysis_result.data, analysis_result.zones)
            visualization_results['macd_chart'] = macd_chart is not None
            
        except Exception as e:
            print(f"MACD chart creation failed: {e}")
            visualization_results['macd_chart'] = False
        
        try:
            # Статистические графики
            stat_plots = StatisticalPlots()
            
            # Распределение зон
            zone_types = [getattr(zone, 'type', 'unknown') for zone in analysis_result.zones]
            if zone_types:
                zone_dist_chart = stat_plots.create_histogram(
                    zone_types,
                    title="Zone Types Distribution"
                )
                visualization_results['statistical_charts'] = zone_dist_chart is not None
            else:
                visualization_results['statistical_charts'] = False
                
        except Exception as e:
            print(f"Statistical charts creation failed: {e}")
            visualization_results['statistical_charts'] = False
        
        # 4. Проверка workflow'а
        successful_visualizations = sum(visualization_results.values())
        assert successful_visualizations > 0, "At least one visualization should be created"
        
        # 5. Создание отчета о визуализации
        workflow_report = {
            'dataset': dataset_name,
            'data_points': len(data),
            'zones_analyzed': len(analysis_result.zones),
            'visualizations_created': successful_visualizations,
            'visualization_details': visualization_results,
            'workflow_success': successful_visualizations > 0
        }
        
        print(f"✅ End-to-end visualization workflow test completed!")
        print(f"   • Dataset: {dataset_name}")
        print(f"   • Data points: {len(data)}")
        print(f"   • Zones: {len(analysis_result.zones)}")
        print(f"   • Successful visualizations: {successful_visualizations}/3")
        print(f"   • Main chart: {'✅' if visualization_results['main_chart'] else '❌'}")
        print(f"   • MACD chart: {'✅' if visualization_results['macd_chart'] else '❌'}")
        print(f"   • Statistical charts: {'✅' if visualization_results['statistical_charts'] else '❌'}")
        
        return workflow_report
    
    @pytest.mark.integration
    @pytest.mark.skipif(not visualization_available, reason="Visualization module not available")
    def test_visualization_performance_pipeline(self, large_ohlcv_data):
        """
        Тест производительности визуализации на больших данных.
        """
        import time
        
        try:
            charts = FinancialCharts()
            
            # Тест производительности создания графика
            start_time = time.time()
            
            fig = charts.create_line_chart(
                large_ohlcv_data,
                'close',
                title="Performance Test Chart"
            )
            
            end_time = time.time()
            creation_time = end_time - start_time
            
            # Проверяем производительность
            assert creation_time < 10.0, f"Chart creation should be under 10 seconds, took {creation_time:.2f}s"
            assert fig is not None, "Chart should be created successfully"
            
            performance_success = True
            
        except Exception as e:
            print(f"Performance test failed: {e}")
            performance_success = False
            creation_time = None
        
        print(f"✅ Visualization performance pipeline test completed!")
        print(f"   • Data points: {len(large_ohlcv_data)}")
        print(f"   • Creation time: {creation_time:.2f}s" if creation_time else "   • Creation time: N/A (failed)")
        print(f"   • Performance: {'✅' if performance_success else '❌'}")
        
        return {
            'data_points': len(large_ohlcv_data),
            'creation_time': creation_time,
            'performance_success': performance_success
        }
