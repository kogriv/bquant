"""
Validation suite for model robustness testing.

Provides comprehensive validation methods including out-of-sample testing,
walk-forward analysis, sensitivity analysis, and Monte Carlo simulation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import itertools

from ...core.logging_config import get_logger
from ...core.exceptions import AnalysisError

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """
    Result of a validation test.
    
    Attributes:
        validation_type: Type of validation performed
        success: Whether validation passed
        train_metrics: Metrics on training data
        test_metrics: Metrics on test data
        degradation_pct: Percentage degradation on test vs train
        iterations: Number of iterations (for walk-forward/monte carlo)
        metadata: Additional metadata
    """
    validation_type: str
    success: bool
    train_metrics: Dict[str, Any]
    test_metrics: Dict[str, Any]
    degradation_pct: Optional[float] = None
    iterations: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'validation_type': self.validation_type,
            'success': self.success,
            'train_metrics': self.train_metrics,
            'test_metrics': self.test_metrics,
            'degradation_pct': self.degradation_pct,
            'iterations': self.iterations,
            'metadata': self.metadata
        }


class ValidationSuite:
    """
    Suite of validation methods for model robustness testing.
    
    Provides tools for:
    - Out-of-sample testing (train/test split)
    - Walk-forward analysis (rolling windows)
    - Sensitivity analysis (parameter sweeps)
    - Monte Carlo simulation (random data testing)
    """
    
    def __init__(self, degradation_threshold: float = 0.2):
        """
        Initialize validation suite.
        
        Args:
            degradation_threshold: Maximum acceptable degradation (0.2 = 20%)
        """
        self.degradation_threshold = degradation_threshold
        self.logger = get_logger(f"{__name__}.ValidationSuite")
        
        self.logger.info(
            f"Initialized validation suite with degradation_threshold={degradation_threshold}"
        )
    
    def out_of_sample_test(self,
                          analyze_func: Callable,
                          data: pd.DataFrame,
                          train_ratio: float = 0.7,
                          metric_key: str = 'total_zones') -> ValidationResult:
        """
        Out-of-sample validation using train/test split.
        
        Args:
            analyze_func: Analysis function to validate (e.g., lambda df: analyzer.analyze(df))
            data: Full dataset
            train_ratio: Ratio of data for training (0.7 = 70% train, 30% test)
            metric_key: Key metric to track for degradation
        
        Returns:
            ValidationResult with train/test comparison
        """
        self.logger.info(f"Running out-of-sample test with train_ratio={train_ratio}")
        
        try:
            if not 0 < train_ratio < 1:
                raise AnalysisError(f"train_ratio must be between 0 and 1, got {train_ratio}")
            
            if len(data) < 10:
                raise AnalysisError(f"Insufficient data for validation: need at least 10 rows, got {len(data)}")
            
            # Split data
            split_idx = int(len(data) * train_ratio)
            train_data = data.iloc[:split_idx].copy()
            test_data = data.iloc[split_idx:].copy()
            
            self.logger.info(f"Split data: train={len(train_data)} bars, test={len(test_data)} bars")
            
            # Run analysis on both sets
            train_result = analyze_func(train_data)
            test_result = analyze_func(test_data)
            
            # Extract metrics
            train_metrics = self._extract_metrics(train_result)
            test_metrics = self._extract_metrics(test_result)
            
            # Calculate degradation
            degradation = self._calculate_degradation(
                train_metrics.get(metric_key, 0),
                test_metrics.get(metric_key, 0)
            )
            
            success = abs(degradation) <= self.degradation_threshold * 100
            
            metadata = {
                'split_index': split_idx,
                'train_size': len(train_data),
                'test_size': len(test_data),
                'metric_key': metric_key,
                'train_start': str(train_data.index[0]) if len(train_data) > 0 else None,
                'train_end': str(train_data.index[-1]) if len(train_data) > 0 else None,
                'test_start': str(test_data.index[0]) if len(test_data) > 0 else None,
                'test_end': str(test_data.index[-1]) if len(test_data) > 0 else None,
                'timestamp': datetime.now().isoformat()
            }
            
            result = ValidationResult(
                validation_type='out_of_sample',
                success=success,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                degradation_pct=degradation,
                iterations=1,
                metadata=metadata
            )
            
            self.logger.info(
                f"Out-of-sample result: degradation={degradation:.1f}%, "
                f"success={success}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Out-of-sample test failed: {e}")
            raise AnalysisError(f"Out-of-sample validation failed: {e}")
    
    def walk_forward_test(self,
                         analyze_func: Callable,
                         data: pd.DataFrame,
                         train_window: int = 1000,
                         test_window: int = 200,
                         step_size: int = 100,
                         metric_key: str = 'total_zones') -> ValidationResult:
        """
        Walk-forward validation using rolling windows.
        
        Simulates real trading: train on [0:N], test on [N:N+M],
        retrain on [0:N+step], test on [N+step:N+step+M], etc.
        
        Args:
            analyze_func: Analysis function to validate
            data: Full dataset
            train_window: Training window size (bars)
            test_window: Test window size (bars)
            step_size: Step size for rolling window
            metric_key: Key metric to track
        
        Returns:
            ValidationResult with results across all iterations
        """
        self.logger.info(
            f"Running walk-forward test: train_window={train_window}, "
            f"test_window={test_window}, step={step_size}"
        )
        
        try:
            if len(data) < train_window + test_window:
                raise AnalysisError(
                    f"Insufficient data for walk-forward: need at least "
                    f"{train_window + test_window} bars, got {len(data)}"
                )
            
            iterations = []
            train_results = []
            test_results = []
            
            # Rolling window analysis
            start_idx = 0
            iteration = 0
            
            while start_idx + train_window + test_window <= len(data):
                train_end = start_idx + train_window
                test_end = train_end + test_window
                
                train_data = data.iloc[start_idx:train_end].copy()
                test_data = data.iloc[train_end:test_end].copy()
                
                # Run analysis
                train_result = analyze_func(train_data)
                test_result = analyze_func(test_data)
                
                train_metrics = self._extract_metrics(train_result)
                test_metrics = self._extract_metrics(test_result)
                
                train_results.append(train_metrics)
                test_results.append(test_metrics)
                
                iterations.append({
                    'iteration': iteration,
                    'train_start': start_idx,
                    'train_end': train_end,
                    'test_start': train_end,
                    'test_end': test_end,
                    'train_metrics': train_metrics,
                    'test_metrics': test_metrics
                })
                
                start_idx += step_size
                iteration += 1
            
            if not iterations:
                raise AnalysisError("No iterations completed in walk-forward test")
            
            # Aggregate metrics
            avg_train_metric = np.mean([m.get(metric_key, 0) for m in train_results])
            avg_test_metric = np.mean([m.get(metric_key, 0) for m in test_results])
            
            degradation = self._calculate_degradation(avg_train_metric, avg_test_metric)
            success = abs(degradation) <= self.degradation_threshold * 100
            
            metadata = {
                'iterations_count': len(iterations),
                'train_window': train_window,
                'test_window': test_window,
                'step_size': step_size,
                'metric_key': metric_key,
                'iterations_detail': iterations,
                'avg_train_metric': avg_train_metric,
                'avg_test_metric': avg_test_metric,
                'std_train_metric': np.std([m.get(metric_key, 0) for m in train_results]),
                'std_test_metric': np.std([m.get(metric_key, 0) for m in test_results]),
                'timestamp': datetime.now().isoformat()
            }
            
            result = ValidationResult(
                validation_type='walk_forward',
                success=success,
                train_metrics={'average': avg_train_metric, 'all': train_results},
                test_metrics={'average': avg_test_metric, 'all': test_results},
                degradation_pct=degradation,
                iterations=len(iterations),
                metadata=metadata
            )
            
            self.logger.info(
                f"Walk-forward result: {len(iterations)} iterations, "
                f"degradation={degradation:.1f}%, success={success}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Walk-forward test failed: {e}")
            raise AnalysisError(f"Walk-forward validation failed: {e}")
    
    def sensitivity_analysis(self,
                           analyze_func: Callable,
                           data: pd.DataFrame,
                           param_ranges: Dict[str, List[Any]],
                           metric_key: str = 'total_zones') -> ValidationResult:
        """
        Sensitivity analysis for parameter variations.
        
        Tests all combinations of parameters and measures impact on results.
        
        Args:
            analyze_func: Analysis function (must accept **params)
            data: Dataset to analyze
            param_ranges: Parameter ranges to test, e.g.:
                         {'macd_fast': [10, 12, 14], 'min_duration': [2, 3, 5]}
            metric_key: Key metric to track
        
        Returns:
            ValidationResult with results for all parameter combinations
        """
        self.logger.info(f"Running sensitivity analysis for {len(param_ranges)} parameters")
        
        try:
            if not param_ranges:
                raise AnalysisError("No parameter ranges provided")
            
            # Generate all parameter combinations
            param_names = list(param_ranges.keys())
            param_values = list(param_ranges.values())
            combinations = list(itertools.product(*param_values))
            
            self.logger.info(f"Testing {len(combinations)} parameter combinations")
            
            results = []
            metrics = []
            
            for combo in combinations:
                params = dict(zip(param_names, combo))
                
                try:
                    # Run analysis with these parameters
                    result = analyze_func(data, **params)
                    result_metrics = self._extract_metrics(result)
                    
                    results.append({
                        'params': params,
                        'metrics': result_metrics,
                        'metric_value': result_metrics.get(metric_key, 0)
                    })
                    
                    metrics.append(result_metrics.get(metric_key, 0))
                    
                except Exception as e:
                    self.logger.warning(f"Failed for params {params}: {e}")
                    results.append({
                        'params': params,
                        'metrics': None,
                        'metric_value': None,
                        'error': str(e)
                    })
            
            if not metrics:
                raise AnalysisError("No successful parameter combinations")
            
            # Find best and worst
            valid_results = [r for r in results if r['metric_value'] is not None]
            best_result = max(valid_results, key=lambda x: x['metric_value'])
            worst_result = min(valid_results, key=lambda x: x['metric_value'])
            
            # Calculate stability (coefficient of variation)
            metric_std = np.std(metrics)
            metric_mean = np.mean(metrics)
            stability = 1 - (metric_std / metric_mean) if metric_mean > 0 else 0
            
            # Success if stability > 0.8 (low variation)
            success = stability > 0.8
            
            metadata = {
                'param_ranges': param_ranges,
                'total_combinations': len(combinations),
                'successful_combinations': len(valid_results),
                'failed_combinations': len(combinations) - len(valid_results),
                'metric_key': metric_key,
                'best_params': best_result['params'],
                'best_metric': best_result['metric_value'],
                'worst_params': worst_result['params'],
                'worst_metric': worst_result['metric_value'],
                'metric_mean': metric_mean,
                'metric_std': metric_std,
                'metric_min': min(metrics),
                'metric_max': max(metrics),
                'stability_score': stability,
                'all_results': results,
                'timestamp': datetime.now().isoformat()
            }
            
            result = ValidationResult(
                validation_type='sensitivity_analysis',
                success=success,
                train_metrics={'best': best_result['metrics'], 'worst': worst_result['metrics']},
                test_metrics={'mean': metric_mean, 'std': metric_std},
                degradation_pct=None,  # Not applicable for sensitivity
                iterations=len(combinations),
                metadata=metadata
            )
            
            self.logger.info(
                f"Sensitivity analysis: {len(combinations)} combinations tested, "
                f"stability={stability:.2f}, success={success}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Sensitivity analysis failed: {e}")
            raise AnalysisError(f"Sensitivity analysis failed: {e}")
    
    def monte_carlo_test(self,
                        analyze_func: Callable,
                        data: pd.DataFrame,
                        n_simulations: int = 1000,
                        metric_key: str = 'total_zones',
                        shuffle_method: str = 'returns') -> ValidationResult:
        """
        Monte Carlo test using random data simulations.
        
        Generates synthetic data with shuffled prices to test if strategy
        performs better than on random data.
        
        Args:
            analyze_func: Analysis function to test
            data: Real data for comparison
            n_simulations: Number of random simulations
            metric_key: Key metric to compare
            shuffle_method: Method for generating random data:
                          'returns' - shuffle returns
                          'prices' - shuffle prices
                          'full' - completely random walk
        
        Returns:
            ValidationResult comparing real vs random data performance
        """
        self.logger.info(f"Running Monte Carlo test with {n_simulations} simulations")
        
        try:
            if n_simulations < 10:
                raise AnalysisError(f"Need at least 10 simulations, got {n_simulations}")
            
            if len(data) < 10:
                raise AnalysisError(f"Insufficient data: need at least 10 bars, got {len(data)}")
            
            # Analyze real data
            real_result = analyze_func(data)
            real_metrics = self._extract_metrics(real_result)
            real_metric_value = real_metrics.get(metric_key, 0)
            
            # Run simulations
            simulation_metrics = []
            
            for i in range(n_simulations):
                # Generate synthetic data
                synthetic_data = self._generate_synthetic_data(data, shuffle_method, seed=i)
                
                try:
                    sim_result = analyze_func(synthetic_data)
                    sim_metrics = self._extract_metrics(sim_result)
                    simulation_metrics.append(sim_metrics.get(metric_key, 0))
                except Exception as e:
                    self.logger.warning(f"Simulation {i} failed: {e}")
                    continue
            
            if len(simulation_metrics) < 10:
                raise AnalysisError(
                    f"Too many failed simulations: only {len(simulation_metrics)} succeeded"
                )
            
            # Compare real vs simulated
            sim_mean = np.mean(simulation_metrics)
            sim_std = np.std(simulation_metrics)
            
            # Calculate percentile of real data in simulation distribution
            percentile = np.percentile(simulation_metrics, 100 * np.sum(
                np.array(simulation_metrics) < real_metric_value
            ) / len(simulation_metrics))
            
            # Success if real data significantly better than random (>95th percentile)
            success = real_metric_value > np.percentile(simulation_metrics, 95)
            
            metadata = {
                'n_simulations': n_simulations,
                'successful_simulations': len(simulation_metrics),
                'shuffle_method': shuffle_method,
                'metric_key': metric_key,
                'real_metric_value': real_metric_value,
                'sim_mean': sim_mean,
                'sim_std': sim_std,
                'sim_min': min(simulation_metrics),
                'sim_max': max(simulation_metrics),
                'sim_median': np.median(simulation_metrics),
                'percentile_real': percentile,
                'z_score': (real_metric_value - sim_mean) / sim_std if sim_std > 0 else 0,
                'p95_threshold': np.percentile(simulation_metrics, 95),
                'timestamp': datetime.now().isoformat()
            }
            
            result = ValidationResult(
                validation_type='monte_carlo',
                success=success,
                train_metrics=real_metrics,
                test_metrics={'mean': sim_mean, 'std': sim_std, 'all': simulation_metrics},
                degradation_pct=None,  # Not applicable
                iterations=len(simulation_metrics),
                metadata=metadata
            )
            
            self.logger.info(
                f"Monte Carlo result: real={real_metric_value:.1f}, "
                f"sim_mean={sim_mean:.1f}, z={metadata['z_score']:.2f}, "
                f"success={success}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Monte Carlo test failed: {e}")
            raise AnalysisError(f"Monte Carlo test failed: {e}")
    
    def _extract_metrics(self, analysis_result: Any) -> Dict[str, Any]:
        """
        Extract metrics from analysis result.
        
        Args:
            analysis_result: Result from analyze_func
        
        Returns:
            Dictionary of extracted metrics
        """
        if isinstance(analysis_result, dict):
            return analysis_result
        elif hasattr(analysis_result, 'to_dict'):
            return analysis_result.to_dict()
        elif hasattr(analysis_result, 'results'):
            # AnalysisResult object
            if isinstance(analysis_result.results, dict):
                return analysis_result.results
            else:
                return {'result': analysis_result.results}
        else:
            return {'result': str(analysis_result)}
    
    def _calculate_degradation(self, train_metric: float, test_metric: float) -> float:
        """
        Calculate degradation percentage.
        
        Args:
            train_metric: Metric value on training data
            test_metric: Metric value on test data
        
        Returns:
            Degradation percentage (positive = worse on test, negative = better on test)
        """
        if train_metric == 0:
            return 0.0
        
        return ((train_metric - test_metric) / abs(train_metric)) * 100
    
    def _generate_synthetic_data(self,
                                 data: pd.DataFrame,
                                 method: str = 'returns',
                                 seed: Optional[int] = None) -> pd.DataFrame:
        """
        Generate synthetic data for Monte Carlo testing.
        
        Args:
            data: Original data
            method: Generation method ('returns', 'prices', 'full')
            seed: Random seed for reproducibility
        
        Returns:
            Synthetic DataFrame with same structure as original
        """
        if seed is not None:
            np.random.seed(seed)
        
        synthetic = data.copy()
        
        if method == 'returns':
            # Shuffle returns but keep structure
            if 'close' in data.columns:
                returns = data['close'].pct_change().dropna()
                shuffled_returns = np.random.permutation(returns.values)
                
                # Reconstruct prices from shuffled returns
                synthetic_close = [data['close'].iloc[0]]
                for ret in shuffled_returns:
                    synthetic_close.append(synthetic_close[-1] * (1 + ret))
                
                synthetic['close'] = synthetic_close[:len(data)]
                
                # Update OHLC proportionally if available
                if all(col in data.columns for col in ['open', 'high', 'low']):
                    ratio_oh = data['high'] / data['close']
                    ratio_ol = data['low'] / data['close']
                    ratio_oc = data['open'] / data['close']
                    
                    synthetic['high'] = synthetic['close'] * ratio_oh
                    synthetic['low'] = synthetic['close'] * ratio_ol
                    synthetic['open'] = synthetic['close'] * ratio_oc
                    
        elif method == 'prices':
            # Shuffle prices directly
            if 'close' in data.columns:
                synthetic['close'] = np.random.permutation(data['close'].values)
                
                if 'open' in data.columns:
                    synthetic['open'] = np.random.permutation(data['open'].values)
                if 'high' in data.columns:
                    synthetic['high'] = np.random.permutation(data['high'].values)
                if 'low' in data.columns:
                    synthetic['low'] = np.random.permutation(data['low'].values)
                    
        elif method == 'full':
            # Generate random walk
            if 'close' in data.columns:
                start_price = data['close'].iloc[0]
                returns_std = data['close'].pct_change().std()
                
                random_returns = np.random.normal(0, returns_std, len(data))
                synthetic_close = [start_price]
                
                for ret in random_returns[1:]:
                    synthetic_close.append(synthetic_close[-1] * (1 + ret))
                
                synthetic['close'] = synthetic_close
                
                # Generate OHLC with noise
                noise = np.random.normal(1, 0.005, len(data))
                synthetic['high'] = synthetic['close'] * (1 + abs(noise))
                synthetic['low'] = synthetic['close'] * (1 - abs(noise))
                synthetic['open'] = synthetic['close'] * noise
        
        return synthetic
    
    def _validate_result(self, result: ValidationResult) -> bool:
        """
        Validate that result meets success criteria.
        
        Args:
            result: ValidationResult to check
        
        Returns:
            True if validation successful
        """
        return result.success


# Export
__all__ = [
    'ValidationResult',
    'ValidationSuite'
]

