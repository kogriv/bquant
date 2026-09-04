"""
Validation suite for model robustness testing.

Provides out-of-sample testing, walk-forward analysis, sensitivity analysis and
Monte Carlo simulation. Every method compares **one metric** between windows or
against a simulated distribution, and the metric is described by a
:class:`MetricSpec` — which key to read, which direction is good, and whether a
count must be divided by the number of bars before windows of different length
can be compared at all.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Callable, Literal
from dataclasses import dataclass, field
from datetime import datetime
import itertools

from ...core.logging_config import get_logger
from ...core.exceptions import AnalysisError

logger = get_logger(__name__)


Direction = Literal['higher_is_better', 'lower_is_better', 'stable']
_DIRECTIONS = ('higher_is_better', 'lower_is_better', 'stable')


@dataclass(frozen=True)
class MetricSpec:
    """What the validation suite compares, and how to read the comparison.

    A bare metric name is not enough for a verdict (G55). Until 2026-09-04 the
    suite compared raw ``total_zones`` between a 70 % and a 30 % window and
    reported a stationary process as **57 % degraded**; treated a metric that
    doubled on the test window as a failure, because it only looked at
    ``abs(change)``; and reported a zero train metric as "0 % degradation" no
    matter what the test window held.

    Attributes:
        key: Name of the metric in what ``analyze_func`` returns.
        direction: ``'higher_is_better'`` — a drop on the test window is a
            degradation, a rise is not; ``'lower_is_better'`` — the mirror;
            ``'stable'`` — a move in either direction beyond the threshold
            is a failure (use it for rates that should hold, such as zones
            per bar).
        per_bar: Divide the value by the number of rows in the window before
            comparing. **Required for counts**: windows of different length
            hold different numbers of anything, and a raw count says nothing
            about the process that produced it.
    """

    key: str
    direction: Direction
    per_bar: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("MetricSpec.key must be a non-empty string")
        if self.direction not in _DIRECTIONS:
            raise ValueError(
                f"MetricSpec.direction must be one of {_DIRECTIONS}, got {self.direction!r}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {'key': self.key, 'direction': self.direction, 'per_bar': self.per_bar}

    def __str__(self) -> str:
        unit = ' per bar' if self.per_bar else ''
        return f"{self.key}{unit} ({self.direction})"


@dataclass
class ModelValidationResult:
    """
    Result of a validation test.

    Attributes:
        validation_type: Type of validation performed
        success: Whether validation passed
        train_metrics: Metrics on training data (raw, as ``analyze_func`` returned them)
        test_metrics: Metrics on test data (raw)
        degradation_pct: How much **worse** the test window is than the train
            window, in percent of the train value, in the metric's own
            direction: positive = worse, negative = better. For a ``'stable'``
            metric the sign only says which way the value moved (positive =
            lower on test); the verdict looks at the magnitude.
        iterations: Number of iterations (for walk-forward/monte carlo)
        metadata: Additional metadata; always carries ``metric`` (the spec) and
            the compared values (``train_value``/``test_value`` or
            ``real_value``), which are normalized when the spec says so.
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

    Each method takes a :class:`MetricSpec` — there is no default metric,
    because the suite cannot know which of your numbers is a quality and in
    which direction.
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
                          metric: MetricSpec,
                          train_ratio: float = 0.7) -> ModelValidationResult:
        """
        Out-of-sample validation using train/test split.

        Args:
            analyze_func: Analysis function to validate (e.g., lambda df: analyzer.analyze(df))
            data: Full dataset
            metric: What to compare between the two windows and how to read it.
            train_ratio: Ratio of data for training (0.7 = 70% train, 30% test)

        Returns:
            ModelValidationResult with train/test comparison
        """
        self.logger.info(f"Running out-of-sample test with train_ratio={train_ratio}")

        try:
            self._require_spec(metric)
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

            train_value = self._value(train_metrics, metric, len(train_data), 'train window')
            test_value = self._value(test_metrics, metric, len(test_data), 'test window')

            degradation = self._degradation(train_value, test_value, metric)
            success = self._holds(degradation, metric)

            metadata = {
                'split_index': split_idx,
                'train_size': len(train_data),
                'test_size': len(test_data),
                'metric': metric.to_dict(),
                'train_value': train_value,
                'test_value': test_value,
                'train_start': str(train_data.index[0]) if len(train_data) > 0 else None,
                'train_end': str(train_data.index[-1]) if len(train_data) > 0 else None,
                'test_start': str(test_data.index[0]) if len(test_data) > 0 else None,
                'test_end': str(test_data.index[-1]) if len(test_data) > 0 else None,
                'timestamp': datetime.now().isoformat()
            }

            result = ModelValidationResult(
                validation_type='out_of_sample',
                success=success,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                degradation_pct=degradation,
                iterations=1,
                metadata=metadata
            )

            self.logger.info(
                f"Out-of-sample result: {metric}: degradation={degradation:.1f}%, "
                f"success={success}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Out-of-sample test failed: {e}")
            raise AnalysisError(f"Out-of-sample validation failed: {e}")

    def walk_forward_test(self,
                         analyze_func: Callable,
                         data: pd.DataFrame,
                         metric: MetricSpec,
                         train_window: int = 1000,
                         test_window: int = 200,
                         step_size: int = 100) -> ModelValidationResult:
        """
        Walk-forward validation using rolling windows.

        Simulates real trading: train on [0:N], test on [N:N+M],
        retrain on [0:N+step], test on [N+step:N+step+M], etc.

        Args:
            analyze_func: Analysis function to validate
            data: Full dataset
            metric: What to compare between the windows and how to read it.
                The windows differ in length, so a count needs ``per_bar``.
            train_window: Training window size (bars)
            test_window: Test window size (bars)
            step_size: Step size for rolling window

        Returns:
            ModelValidationResult with results across all iterations
        """
        self.logger.info(
            f"Running walk-forward test: train_window={train_window}, "
            f"test_window={test_window}, step={step_size}"
        )

        try:
            self._require_spec(metric)
            if len(data) < train_window + test_window:
                raise AnalysisError(
                    f"Insufficient data for walk-forward: need at least "
                    f"{train_window + test_window} bars, got {len(data)}"
                )

            iterations = []
            train_results = []
            test_results = []
            train_values = []
            test_values = []

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
                train_values.append(
                    self._value(train_metrics, metric, len(train_data), 'walk-forward train window')
                )
                test_values.append(
                    self._value(test_metrics, metric, len(test_data), 'walk-forward test window')
                )

                iterations.append({
                    'iteration': iteration,
                    'train_start': start_idx,
                    'train_end': train_end,
                    'test_start': train_end,
                    'test_end': test_end,
                    'train_metrics': train_metrics,
                    'test_metrics': test_metrics,
                    'train_value': train_values[-1],
                    'test_value': test_values[-1],
                })

                start_idx += step_size
                iteration += 1

            if not iterations:
                raise AnalysisError("No iterations completed in walk-forward test")

            # Aggregate metrics
            avg_train_metric = float(np.mean(train_values))
            avg_test_metric = float(np.mean(test_values))

            degradation = self._degradation(avg_train_metric, avg_test_metric, metric)
            success = self._holds(degradation, metric)

            metadata = {
                'iterations_count': len(iterations),
                'train_window': train_window,
                'test_window': test_window,
                'step_size': step_size,
                'metric': metric.to_dict(),
                'iterations_detail': iterations,
                'train_value': avg_train_metric,
                'test_value': avg_test_metric,
                'avg_train_metric': avg_train_metric,
                'avg_test_metric': avg_test_metric,
                'std_train_metric': float(np.std(train_values)),
                'std_test_metric': float(np.std(test_values)),
                'timestamp': datetime.now().isoformat()
            }

            result = ModelValidationResult(
                validation_type='walk_forward',
                success=success,
                train_metrics={'average': avg_train_metric, 'all': train_results},
                test_metrics={'average': avg_test_metric, 'all': test_results},
                degradation_pct=degradation,
                iterations=len(iterations),
                metadata=metadata
            )

            self.logger.info(
                f"Walk-forward result: {len(iterations)} iterations, {metric}: "
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
                           metric: MetricSpec) -> ModelValidationResult:
        """
        Sensitivity analysis for parameter variations.

        Tests all combinations of parameters and measures impact on results.

        Args:
            analyze_func: Analysis function (must accept **params)
            data: Dataset to analyze
            param_ranges: Parameter ranges to test, e.g.:
                         {'macd_fast': [10, 12, 14], 'min_duration': [2, 3, 5]}
            metric: What to track across the combinations. ``direction``
                decides which combination is "best"; for ``'stable'`` there
                is no best or worst, only the spread.

        Returns:
            ModelValidationResult with results for all parameter combinations
        """
        self.logger.info(f"Running sensitivity analysis for {len(param_ranges)} parameters")

        try:
            self._require_spec(metric)
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
                    value = self._value(result_metrics, metric, len(data), 'sensitivity run')

                    results.append({
                        'params': params,
                        'metrics': result_metrics,
                        'metric_value': value
                    })

                    metrics.append(value)

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

            # Find best and worst — only meaningful when the metric has a direction
            valid_results = [r for r in results if r['metric_value'] is not None]
            if metric.direction == 'higher_is_better':
                best_result = max(valid_results, key=lambda x: x['metric_value'])
                worst_result = min(valid_results, key=lambda x: x['metric_value'])
            elif metric.direction == 'lower_is_better':
                best_result = min(valid_results, key=lambda x: x['metric_value'])
                worst_result = max(valid_results, key=lambda x: x['metric_value'])
            else:
                best_result = worst_result = None

            # Stability: 1 - coefficient of variation
            metric_std = float(np.std(metrics))
            metric_mean = float(np.mean(metrics))
            stability = self._stability(metric_mean, metric_std, metric)

            # Success if stability > 0.8 (low variation)
            success = bool(stability > 0.8)

            metadata = {
                'param_ranges': param_ranges,
                'total_combinations': len(combinations),
                'successful_combinations': len(valid_results),
                'failed_combinations': len(combinations) - len(valid_results),
                'metric': metric.to_dict(),
                'best_params': best_result['params'] if best_result else None,
                'best_metric': best_result['metric_value'] if best_result else None,
                'worst_params': worst_result['params'] if worst_result else None,
                'worst_metric': worst_result['metric_value'] if worst_result else None,
                'metric_mean': metric_mean,
                'metric_std': metric_std,
                'metric_min': min(metrics),
                'metric_max': max(metrics),
                'stability_score': stability,
                'all_results': results,
                'timestamp': datetime.now().isoformat()
            }

            result = ModelValidationResult(
                validation_type='sensitivity_analysis',
                success=success,
                train_metrics={
                    'best': best_result['metrics'] if best_result else None,
                    'worst': worst_result['metrics'] if worst_result else None,
                },
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
                        metric: MetricSpec,
                        n_simulations: int = 1000,
                        shuffle_method: str = 'returns') -> ModelValidationResult:
        """
        Monte Carlo test using random data simulations.

        Generates synthetic data with shuffled prices to test whether the
        real data stands out from random data on the chosen metric.

        Args:
            analyze_func: Analysis function to test
            data: Real data for comparison
            metric: What to compare, and on which side the real value has to
                land: ``'higher_is_better'`` — above the simulations' 95th
                percentile; ``'lower_is_better'`` — below the 5th;
                ``'stable'`` — outside the central 95 % (the question is then
                only whether real data is distinguishable from random).
            n_simulations: Number of random simulations
            shuffle_method: Method for generating random data:
                          'returns' - shuffle returns
                          'prices' - shuffle prices
                          'full' - completely random walk

        Returns:
            ModelValidationResult comparing real vs random data performance
        """
        self.logger.info(f"Running Monte Carlo test with {n_simulations} simulations")

        try:
            self._require_spec(metric)
            if n_simulations < 10:
                raise AnalysisError(f"Need at least 10 simulations, got {n_simulations}")

            if len(data) < 10:
                raise AnalysisError(f"Insufficient data: need at least 10 bars, got {len(data)}")

            # Analyze real data
            real_result = analyze_func(data)
            real_metrics = self._extract_metrics(real_result)
            real_value = self._value(real_metrics, metric, len(data), 'real data')

            # Run simulations
            simulation_metrics = []

            for i in range(n_simulations):
                # Generate synthetic data
                synthetic_data = self._generate_synthetic_data(data, shuffle_method, seed=i)

                try:
                    sim_result = analyze_func(synthetic_data)
                    sim_metrics = self._extract_metrics(sim_result)
                    simulation_metrics.append(
                        self._value(sim_metrics, metric, len(synthetic_data), 'monte-carlo simulation')
                    )
                except Exception as e:
                    self.logger.warning(f"Simulation {i} failed: {e}")
                    continue

            if len(simulation_metrics) < 10:
                raise AnalysisError(
                    f"Too many failed simulations: only {len(simulation_metrics)} succeeded"
                )

            sims = np.asarray(simulation_metrics, dtype=float)
            sim_mean = float(sims.mean())
            sim_std = float(sims.std())

            # Percentile rank of the real value in the simulated distribution
            # (mid-rank for ties: counts tie a lot). Until G55 this key held
            # `np.percentile(sims, rank)` — a metric *value* named as a rank.
            percentile_rank = float(
                100.0 * (np.mean(sims < real_value) + 0.5 * np.mean(sims == real_value))
            )

            p025, p05, p95, p975 = (float(v) for v in np.percentile(sims, [2.5, 5, 95, 97.5]))
            if metric.direction == 'higher_is_better':
                success = bool(real_value > p95)
                rule = 'real > p95 of simulations'
            elif metric.direction == 'lower_is_better':
                success = bool(real_value < p05)
                rule = 'real < p05 of simulations'
            else:
                success = bool(real_value < p025 or real_value > p975)
                rule = 'real outside [p2.5, p97.5] of simulations'

            metadata = {
                'n_simulations': n_simulations,
                'successful_simulations': len(simulation_metrics),
                'shuffle_method': shuffle_method,
                'metric': metric.to_dict(),
                'real_value': real_value,
                'sim_mean': sim_mean,
                'sim_std': sim_std,
                'sim_min': float(sims.min()),
                'sim_max': float(sims.max()),
                'sim_median': float(np.median(sims)),
                'percentile_rank': percentile_rank,
                'z_score': (real_value - sim_mean) / sim_std if sim_std > 0 else 0.0,
                'p025_threshold': p025,
                'p05_threshold': p05,
                'p95_threshold': p95,
                'p975_threshold': p975,
                'success_rule': rule,
                'timestamp': datetime.now().isoformat()
            }

            result = ModelValidationResult(
                validation_type='monte_carlo',
                success=success,
                train_metrics=real_metrics,
                test_metrics={'mean': sim_mean, 'std': sim_std, 'all': simulation_metrics},
                degradation_pct=None,  # Not applicable
                iterations=len(simulation_metrics),
                metadata=metadata
            )

            self.logger.info(
                f"Monte Carlo result: {metric}: real={real_value:.4g}, "
                f"sim_mean={sim_mean:.4g}, rank={percentile_rank:.1f}, "
                f"z={metadata['z_score']:.2f}, success={success}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Monte Carlo test failed: {e}")
            raise AnalysisError(f"Monte Carlo test failed: {e}")

    @staticmethod
    def _require_spec(metric: Any) -> None:
        if not isinstance(metric, MetricSpec):
            raise AnalysisError(
                f"metric must be a MetricSpec (key, direction, per_bar), got "
                f"{type(metric).__name__}. A bare name cannot say whether a rise "
                "is an improvement, nor whether a count needs to be divided by "
                "the window length before windows of different size are compared."
            )

    @staticmethod
    def _metric(metrics: Dict[str, Any], metric_key: str, where: str) -> float:
        """Достать метрику или сказать, что её нет.

        Раньше здесь стояло `metrics.get(metric_key, 0)` — девять раз по файлу. Отсутствие
        метрики превращалось в ноль, ноль сравнивался с нулём, и валидация сообщала
        «деградация 0%, модель устойчива», не измерив ничего. Для модуля, который
        отвечает ровно на вопрос «держится ли модель», это худший из возможных отказов:
        правдоподобный вердикт вместо признания, что вердикта нет (G39).
        """

        if metric_key not in metrics:
            raise AnalysisError(
                f"Metric {metric_key!r} is missing from the analysis result ({where}). "
                f"Available keys: {sorted(metrics)}. "
                "The validation suite compares this metric between windows; without it "
                "there is nothing to compare, and reporting zero would be a verdict "
                "made up out of nothing."
            )

        value = metrics[metric_key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AnalysisError(
                f"Metric {metric_key!r} must be a number to be compared between windows, "
                f"got {type(value).__name__} ({where})."
            )
        return float(value)

    def _value(self, metrics: Dict[str, Any], spec: MetricSpec, n_bars: int, where: str) -> float:
        """The value the verdict is built on: the metric, per bar if the spec says so."""

        value = self._metric(metrics, spec.key, where)
        if spec.per_bar:
            if n_bars <= 0:
                raise AnalysisError(f"Cannot normalize {spec.key!r} per bar: empty window ({where})")
            value /= n_bars
        return value

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

        # Порядок ветвей существен. `AnalysisResult` имеет и `results`, и `to_dict()`,
        # но метрики лежат в первом, а `to_dict()` кладёт их **на уровень глубже**, под
        # ключ `results`. Пока проверка на `to_dict` стояла раньше, запрошенная метрика
        # не находилась ни разу — и вместо отказа получался ноль (G39).
        if hasattr(analysis_result, 'results'):
            if isinstance(analysis_result.results, dict):
                return analysis_result.results
            return {'result': analysis_result.results}

        if hasattr(analysis_result, 'to_dict'):
            return analysis_result.to_dict()

        return {'result': str(analysis_result)}

    @staticmethod
    def _degradation(train_value: float, test_value: float, spec: MetricSpec) -> float:
        """How much worse the test window is, in percent of the train value.

        Positive = worse in the metric's own direction, negative = better. For a
        ``'stable'`` metric positive means "lower on test"; only the magnitude
        matters for the verdict.

        A zero train value has no "percent of": until G55 this returned ``0.0``
        for it, so ``train=0, test=7`` read as "no change, holds". Zero against
        zero is a measured no-change; zero against anything else is refused.
        """

        if train_value == 0:
            if test_value == 0:
                return 0.0
            raise AnalysisError(
                f"Relative change of {spec.key!r} is undefined: the train value is 0 "
                f"and the test value is {test_value}. A percentage of zero does not "
                "exist, and reporting 0 % here would call any test value 'stable'. "
                "Use a longer train window, or a metric that is not zero on it."
            )

        change = (test_value - train_value) / abs(train_value) * 100.0
        if spec.direction == 'lower_is_better':
            return change
        return -change + 0.0  # `+ 0.0` turns -0.0 into 0.0

    def _holds(self, degradation: float, spec: MetricSpec) -> bool:
        limit = self.degradation_threshold * 100.0
        if spec.direction == 'stable':
            return bool(abs(degradation) <= limit)
        return bool(degradation <= limit)

    @staticmethod
    def _stability(mean: float, std: float, spec: MetricSpec) -> float:
        """1 - coefficient of variation, on the metric's magnitude."""

        if mean == 0:
            if std == 0:
                return 1.0
            raise AnalysisError(
                f"Stability of {spec.key!r} is undefined: the values average to 0 "
                f"with spread {std:.4g}. The coefficient of variation has no zero "
                "baseline; choose a metric that does not cancel out."
            )
        return float(1.0 - std / abs(mean))

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

    def _validate_result(self, result: ModelValidationResult) -> bool:
        """
        Validate that result meets success criteria.

        Args:
            result: ModelValidationResult to check

        Returns:
            True if validation successful
        """
        return result.success


# Export
__all__ = [
    'MetricSpec',
    'ModelValidationResult',
    'ValidationSuite'
]
