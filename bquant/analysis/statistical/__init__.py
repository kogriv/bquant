"""
Модуль статистического анализа BQuant

Предоставляет функции для статистического анализа финансовых данных:
- Тестирование гипотез
- Корреляционный анализ  
- Распределения данных
- Описательная статистика
- Временные ряды статистика
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime

from ...core.logging_config import get_logger
from .. import BaseAnalyzer, AnalysisResult

logger = get_logger(__name__)

# Версия модуля статистического анализа
__version__ = "0.0.0"


class StatisticalAnalyzer(BaseAnalyzer):
    """
    Базовый класс для статистических анализаторов.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация статистического анализатора.
        
        Args:
            config: Конфигурация анализатора
        """
        super().__init__("StatisticalAnalyzer", config)
        
        # Параметры по умолчанию
        self.default_alpha = self.config.get('alpha', 0.05)
        self.min_sample_size = self.config.get('min_sample_size', 30)
    
    def descriptive_statistics(self, data: pd.Series, name: str = "data") -> Dict[str, float]:
        """
        Вычисление описательных статистик.
        
        Args:
            data: Временной ряд данных
            name: Название данных
        
        Returns:
            Словарь с описательными статистиками
        """
        if data.empty:
            return {}
        
        stats_dict = {
            'count': len(data),
            'mean': data.mean(),
            'std': data.std(),
            'min': data.min(),
            'max': data.max(),
            'median': data.median(),
            'q25': data.quantile(0.25),
            'q75': data.quantile(0.75),
            'skewness': data.skew(),
            'kurtosis': data.kurtosis(),
            'variance': data.var()
        }
        
        # Добавляем коэффициент вариации
        if stats_dict['mean'] != 0:
            stats_dict['cv'] = stats_dict['std'] / abs(stats_dict['mean'])
        else:
            stats_dict['cv'] = np.nan
        
        self.logger.debug(f"Calculated descriptive statistics for {name}")
        return stats_dict
    
    def normality_test(self, data: pd.Series, alpha: float = None) -> Dict[str, Any]:
        """
        Тест на нормальность распределения.
        
        Args:
            data: Данные для тестирования
            alpha: Уровень значимости
        
        Returns:
            Результаты тестов нормальности
        """
        if alpha is None:
            alpha = self.default_alpha
        
        results = {}
        
        if len(data) < 3:
            return {'error': 'Insufficient data for normality tests'}
        
        # Shapiro-Wilk test (для небольших выборок)
        if len(data) <= 5000:
            try:
                shapiro_stat, shapiro_p = stats.shapiro(data.dropna())
                results['shapiro'] = {
                    'statistic': shapiro_stat,
                    'p_value': shapiro_p,
                    'is_normal': shapiro_p > alpha
                }
            except Exception as e:
                self.logger.warning(f"Shapiro-Wilk test failed: {e}")
        
        # Kolmogorov-Smirnov test
        try:
            ks_stat, ks_p = stats.kstest(data.dropna(), 'norm', 
                                        args=(data.mean(), data.std()))
            results['kolmogorov_smirnov'] = {
                'statistic': ks_stat,
                'p_value': ks_p,
                'is_normal': ks_p > alpha
            }
        except Exception as e:
            self.logger.warning(f"Kolmogorov-Smirnov test failed: {e}")
        
        # Anderson-Darling test
        try:
            ad_result = stats.anderson(data.dropna(), dist='norm')
            # Сравниваем с критическим значением для alpha=0.05
            critical_idx = 2  # Индекс для 5% уровня значимости
            results['anderson_darling'] = {
                'statistic': ad_result.statistic,
                'critical_value': ad_result.critical_values[critical_idx],
                'is_normal': ad_result.statistic < ad_result.critical_values[critical_idx]
            }
        except Exception as e:
            self.logger.warning(f"Anderson-Darling test failed: {e}")
        
        self.logger.debug(f"Performed normality tests on {len(data)} data points")
        return results
    
    def correlation_analysis(self, x: pd.Series, y: pd.Series, 
                           methods: List[str] = None) -> Dict[str, Any]:
        """
        Анализ корреляции между двумя переменными.
        
        Args:
            x: Первая переменная
            y: Вторая переменная  
            methods: Методы корреляции для использования
        
        Returns:
            Результаты корреляционного анализа
        """
        if methods is None:
            methods = ['pearson', 'spearman', 'kendall']
        
        results = {}
        
        # Убираем NaN значения
        combined = pd.DataFrame({'x': x, 'y': y}).dropna()
        if len(combined) < self.min_sample_size:
            return {'error': f'Insufficient data after cleaning: {len(combined)} < {self.min_sample_size}'}
        
        x_clean = combined['x']
        y_clean = combined['y']
        
        for method in methods:
            try:
                if method == 'pearson':
                    corr, p_value = stats.pearsonr(x_clean, y_clean)
                elif method == 'spearman':
                    corr, p_value = stats.spearmanr(x_clean, y_clean)
                elif method == 'kendall':
                    corr, p_value = stats.kendalltau(x_clean, y_clean)
                else:
                    self.logger.warning(f"Unknown correlation method: {method}")
                    continue
                
                results[method] = {
                    'correlation': corr,
                    'p_value': p_value,
                    'is_significant': p_value < self.default_alpha,
                    'sample_size': len(x_clean)
                }
            except Exception as e:
                self.logger.error(f"Correlation analysis failed for {method}: {e}")
                results[method] = {'error': str(e)}
        
        self.logger.debug(f"Performed correlation analysis using {methods}")
        return results
    
    def t_test(self, sample1: pd.Series, sample2: pd.Series = None, 
              mu: float = 0, alternative: str = 'two-sided') -> Dict[str, Any]:
        """
        Выполнение t-теста.
        
        Args:
            sample1: Первая выборка
            sample2: Вторая выборка (для независимых выборок)
            mu: Гипотетическое среднее (для одновыборочного теста)
            alternative: Альтернативная гипотеза ('two-sided', 'less', 'greater')
        
        Returns:
            Результаты t-теста
        """
        sample1_clean = sample1.dropna()
        
        if sample2 is None:
            # Одновыборочный t-тест
            if len(sample1_clean) < 2:
                return {'error': 'Insufficient data for one-sample t-test'}
            
            t_stat, p_value = stats.ttest_1samp(sample1_clean, mu, alternative=alternative)
            test_type = 'one_sample'
            df = len(sample1_clean) - 1
        else:
            # Двухвыборочный t-тест
            sample2_clean = sample2.dropna()
            
            if len(sample1_clean) < 2 or len(sample2_clean) < 2:
                return {'error': 'Insufficient data for two-sample t-test'}
            
            t_stat, p_value = stats.ttest_ind(sample1_clean, sample2_clean, alternative=alternative)
            test_type = 'two_sample'
            df = len(sample1_clean) + len(sample2_clean) - 2
        
        result = {
            'test_type': test_type,
            't_statistic': t_stat,
            'p_value': p_value,
            'degrees_of_freedom': df,
            'alternative': alternative,
            'is_significant': p_value < self.default_alpha,
            'alpha': self.default_alpha
        }
        
        if sample2 is None:
            result['sample_size'] = len(sample1_clean)
            result['sample_mean'] = sample1_clean.mean()
            result['hypothesized_mean'] = mu
        else:
            result['sample1_size'] = len(sample1_clean)
            result['sample2_size'] = len(sample2_clean)
            result['sample1_mean'] = sample1_clean.mean()
            result['sample2_mean'] = sample2_clean.mean()
        
        self.logger.debug(f"Performed {test_type} t-test")
        return result
    
    def analyze(self, data: pd.DataFrame, **kwargs) -> AnalysisResult:
        """
        Выполнение комплексного статистического анализа.
        
        Args:
            data: DataFrame с данными
            **kwargs: Дополнительные параметры
        
        Returns:
            AnalysisResult с результатами статистического анализа
        """
        if not self.validate_data(data):
            raise ValueError("Data validation failed")
        
        results = {}
        
        # Анализируем числовые колонки
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            col_results = {}
            
            # Описательная статистика
            col_results['descriptive'] = self.descriptive_statistics(data[col], col)
            
            # Тест на нормальность
            col_results['normality'] = self.normality_test(data[col])
            
            results[col] = col_results
        
        # Корреляционный анализ между числовыми колонками
        if len(numeric_columns) > 1:
            correlations = {}
            for i, col1 in enumerate(numeric_columns):
                for col2 in numeric_columns[i+1:]:
                    pair_key = f"{col1}_vs_{col2}"
                    correlations[pair_key] = self.correlation_analysis(data[col1], data[col2])
            
            results['correlations'] = correlations
        
        metadata = {
            'analyzer': 'StatisticalAnalyzer',
            'columns_analyzed': list(numeric_columns),
            'total_columns': len(data.columns),
            'config': self.config
        }
        
        return AnalysisResult(
            analysis_type='statistical',
            results=results,
            data_size=len(data),
            metadata=metadata
        )


def get_statistical_analyzers() -> Dict[str, str]:
    """
    Получить список доступных статистических анализаторов.
    
    Returns:
        Словарь {анализатор: описание}
    """
    return {
        'statistical': 'Комплексный статистический анализ',
        'hypothesis': 'Тестирование статистических гипотез',
        'correlation': 'Корреляционный анализ',
        'distribution': 'Анализ распределений'
    }


# Удобные функции для быстрого анализа
def quick_stats(data: pd.Series) -> Dict[str, float]:
    """
    Быстрые описательные статистики.
    
    Args:
        data: Данные для анализа
    
    Returns:
        Основные статистики
    """
    analyzer = StatisticalAnalyzer()
    return analyzer.descriptive_statistics(data)


def test_normality(data: pd.Series, alpha: float = 0.05) -> bool:
    """
    Быстрый тест нормальности.
    
    Args:
        data: Данные для тестирования
        alpha: Уровень значимости
    
    Returns:
        True если данные имеют нормальное распределение
    """
    analyzer = StatisticalAnalyzer({'alpha': alpha})
    results = analyzer.normality_test(data, alpha)
    
    # Возвращаем True если хотя бы один тест показал нормальность
    for test_name, test_result in results.items():
        if isinstance(test_result, dict) and 'is_normal' in test_result:
            if test_result['is_normal']:
                return True
    
    return False


def correlation_matrix(data: pd.DataFrame, method: str = 'pearson') -> pd.DataFrame:
    """
    Матрица корреляций с p-values.
    
    Args:
        data: DataFrame с данными
        method: Метод корреляции
    
    Returns:
        DataFrame с корреляциями
    """
    numeric_data = data.select_dtypes(include=[np.number])
    
    if method == 'pearson':
        corr_matrix = numeric_data.corr()
    elif method == 'spearman':
        corr_matrix = numeric_data.corr(method='spearman')
    elif method == 'kendall':
        corr_matrix = numeric_data.corr(method='kendall')
    else:
        raise ValueError(f"Unknown correlation method: {method}")
    
    return corr_matrix


# Импорт функций hypothesis testing
try:
    from .hypothesis_testing import (
        HypothesisTestResult,
        HypothesisTestSuite,
        run_all_hypothesis_tests,
        run_single_hypothesis_test
    )
    _hypothesis_testing_available = True
except ImportError as e:
    logger.warning(f"Hypothesis testing module not available: {e}")
    _hypothesis_testing_available = False


# Экспорт
__all__ = [
    'StatisticalAnalyzer',
    'get_statistical_analyzers',
    'quick_stats',
    'test_normality', 
    'correlation_matrix',
    '__version__'
]

# Добавляем hypothesis testing если доступен
if _hypothesis_testing_available:
    __all__.extend([
        'HypothesisTestResult',
        'HypothesisTestSuite', 
        'run_all_hypothesis_tests',
        'run_single_hypothesis_test'
    ])
