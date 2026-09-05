"""
Regression analysis module for zone prediction models.

Provides tools for building regression models to predict zone characteristics
such as duration and price returns based on zone features.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ...core.logging_config import get_logger
from ...core.exceptions import StatisticalAnalysisError
from statsmodels.stats.stattools import durbin_watson
from .. import BaseAnalyzer

logger = get_logger(__name__)


@dataclass
class RegressionResult:
    """
    Result of a regression analysis.
    
    Attributes:
        target_variable: Name of the predicted variable
        r_squared: R-squared of the model (goodness of fit)
        adjusted_r_squared: Adjusted R-squared accounting for predictors
        coefficients: Dictionary of predictor coefficients
        p_values: Dictionary of predictor p-values
        predictions: Array of predicted values
        residuals: Array of residuals (actual - predicted)
        n_observations: Number of observations used
        n_predictors: Number of predictors in model
        model_summary: Full model summary (optional)
        metadata: Additional metadata
    """
    target_variable: str
    r_squared: float
    adjusted_r_squared: float
    coefficients: Dict[str, float]
    p_values: Dict[str, float]
    predictions: np.ndarray
    residuals: np.ndarray
    n_observations: int
    n_predictors: int
    model_summary: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'target_variable': self.target_variable,
            'r_squared': self.r_squared,
            'adjusted_r_squared': self.adjusted_r_squared,
            'coefficients': self.coefficients,
            'p_values': self.p_values,
            'predictions': self.predictions.tolist() if isinstance(self.predictions, np.ndarray) else self.predictions,
            'residuals': self.residuals.tolist() if isinstance(self.residuals, np.ndarray) else self.residuals,
            'n_observations': self.n_observations,
            'n_predictors': self.n_predictors,
            'model_summary': self.model_summary,
            'metadata': self.metadata
        }
    
    def get_significant_predictors(self, alpha: float = 0.05) -> Dict[str, float]:
        """Get predictors with p-value < alpha."""
        return {k: v for k, v in self.coefficients.items() 
                if self.p_values.get(k, 1.0) < alpha}


def _usable_predictors(
    df: pd.DataFrame,
    requested: List[str],
    logger,
) -> Tuple[List[str], List[str]]:
    """Split requested predictors into usable ones and empty ones.

    A predictor that is ``NaN`` in every row carries no information, but it is
    not harmless: the model frame is built with ``dropna()``, so one such column
    takes **every** observation with it. The failure then surfaced as

        Insufficient data for regression: need at least 8 observations, got 0

    which points at the amount of data when the cause is a column empty by
    construction. `line_amplitude` is exactly that for any non-MACD zone set: it
    is the amplitude of the indicator's *line*, and an RSI zone has no line, so
    `.analyze(regression=True)` over RSI zones raised and killed the whole build.

    Dropping such a column is what a person would do — but it has to be said out
    loud, in the log and in the result metadata. A silently narrowed model is the
    defect this project keeps finding (``devref/gaps/``), and swapping a loud
    wrong answer for a quiet one would not be an improvement.
    """
    usable, empty = [], []
    for name in requested:
        if df[name].notna().any():
            usable.append(name)
        else:
            empty.append(name)
    if empty:
        logger.warning(
            "Dropping predictor(s) with no observations at all: %s. They are NaN "
            "in every zone, so keeping them would empty the model frame instead "
            "of adding information.",
            ", ".join(empty),
        )
    return usable, empty


def _reject_degenerate_design(
    X_with_const: pd.DataFrame,
    predictors: List[str],
) -> None:
    """Refuse to fit a design matrix that cannot support the model.

    Two failures used to hide here, both worse than an error.

    When every observation carries the same predictor values, ``add_constant``
    finds a constant column already present and silently **does not add**
    ``const``; the next line then read ``model.params['const']`` and the whole
    thing surfaced as ``regression failed: 'const'`` — a leaked KeyError naming
    nothing a caller could act on.

    Force the constant in and the second failure takes over: the matrix is rank
    deficient, ``OLS`` falls back to a pseudo-inverse and returns a well-formed
    set of coefficients that means nothing. A fabricated answer is the failure
    mode this project keeps digging out (``devref/gaps/``); an explicit refusal
    is the cheaper outcome.
    """
    rank = int(np.linalg.matrix_rank(X_with_const.values))
    needed = X_with_const.shape[1]
    if rank < needed:
        constant_cols = [c for c in predictors if X_with_const[c].nunique(dropna=False) <= 1]
        detail = (
            f" Predictor(s) constant across all observations: {constant_cols}."
            if constant_cols else
            " The predictors are linearly dependent."
        )
        raise StatisticalAnalysisError(
            f"Design matrix is rank deficient (rank {rank} of {needed} columns), "
            f"so the coefficients would not be identified.{detail} "
            "Refusing to fit rather than returning numbers the data does not support."
        )


class ZoneRegressionAnalyzer(BaseAnalyzer):
    """
    OLS regression analyzer for modeling zone dependencies.
    
    Provides methods for:
    - Predicting zone duration based on zone features
    - Predicting price returns based on zone characteristics
    - Model diagnostics and validation
    """
    
    def __init__(self, alpha: float = 0.05):
        """
        Initialize the regression analyzer.
        
        Args:
            alpha: Significance level for statistical tests
        """
        super().__init__("ZoneRegressionAnalyzer")
        self.alpha = alpha
        self.logger = get_logger(f"{__name__}.ZoneRegressionAnalyzer")
        
        self.logger.info(f"Initialized zone regression analyzer with alpha={alpha}")
    
    def explain_zone_duration(self,
                             zones_features: List[Dict[str, Any]],
                             predictors: Optional[List[str]] = None) -> RegressionResult:
        """
        Fit an **in-sample, explanatory** regression of zone duration on zone features.

        Model: duration ~ line_amplitude + oscillator_amplitude + correlation_price_oscillator + ...

        The predictors are measured over the **whole, finished** zone — the same
        zone whose duration is the target. This explains variance ex post; it
        is not a forecast, and R² here is not predictive evidence. The method
        was called ``predict_zone_duration`` until G62.
        
        Args:
            zones_features: List of zone feature dictionaries
            predictors: List of predictor variable names. If None, uses default set.
        
        Returns:
            RegressionResult with model statistics and predictions
        """
        self.logger.info("Building zone duration regression model")
        
        try:
            from statsmodels.api import OLS, add_constant
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            
            df = pd.DataFrame(zones_features)
            
            # Default predictors
            if predictors is None:
                predictors = ['line_amplitude', 'oscillator_amplitude', 'correlation_price_oscillator', 
                            'price_range_pct', 'num_peaks', 'num_troughs']
            
            # Validate target variable
            if 'duration' not in df.columns:
                raise StatisticalAnalysisError("Missing target variable: 'duration'")
            
            # Filter available predictors
            available_predictors = [p for p in predictors if p in df.columns]
            
            if not available_predictors:
                raise StatisticalAnalysisError(
                    f"No predictors available. Requested: {predictors}, Available columns: {df.columns.tolist()}"
                )            
            available_predictors, empty_predictors = _usable_predictors(
                df, available_predictors, self.logger
            )
            if not available_predictors:
                raise StatisticalAnalysisError(
                    f"Every requested predictor is empty for this zone set: "
                    f"{empty_predictors}. Nothing to regress on."
                )
            
            self.logger.info(f"Using predictors: {available_predictors}")
            
            # Prepare data (remove NaN)
            model_data = df[['duration'] + available_predictors].dropna()
            
            if len(model_data) < len(available_predictors) + 2:
                raise StatisticalAnalysisError(
                    f"Insufficient data for regression: need at least {len(available_predictors) + 2} "
                    f"observations, got {len(model_data)}"
                )
            
            # Separate target and predictors
            y = model_data['duration']
            X = model_data[available_predictors]
            
            # Add constant for intercept. `has_constant='add'` is deliberate:
            # with the default, a design whose columns are already constant gets
            # no `const` column, and the coefficient lookup below then failed
            # with a bare KeyError.
            X_with_const = add_constant(X, has_constant='add')
            _reject_degenerate_design(X_with_const, available_predictors)
            if y.nunique(dropna=True) <= 1:
                # A constant target has no variance to explain; OLS would still
                # fit and report R² = -inf (G62).
                raise StatisticalAnalysisError(
                    f"Target 'duration' is constant across all {len(y)} observations "
                    f"(value {y.iloc[0]!r}); there is nothing to explain."
                )
            
            # Fit OLS model
            model = OLS(y, X_with_const).fit()
            
            # Extract results
            coefficients = {}
            p_values = {}
            
            coefficients['intercept'] = model.params['const']
            p_values['intercept'] = model.pvalues['const']
            
            for pred in available_predictors:
                coefficients[pred] = model.params[pred]
                p_values[pred] = model.pvalues[pred]
            
            # Predictions and residuals
            predictions = model.predict(X_with_const)
            residuals = model.resid
            
            # Calculate VIF for multicollinearity check (if >2 predictors)
            vif_data = {}
            if len(available_predictors) >= 2:
                try:
                    for i, col in enumerate(available_predictors):
                        vif_data[col] = variance_inflation_factor(X.values, i)
                except Exception as e:
                    self.logger.warning(f"Could not calculate VIF: {e}")
            
            # Metadata
            metadata = {
                'available_predictors': available_predictors,
                'requested_predictors': predictors,
                'missing_predictors': [p for p in predictors if p not in df.columns],
                'empty_predictors': empty_predictors,
                'n_dropped_na': len(df) - len(model_data),
                'f_statistic': float(model.fvalue),
                'f_pvalue': float(model.f_pvalue),
                'aic': float(model.aic),
                'bic': float(model.bic),
                'vif': vif_data,
                # Computed explicitly: a fitted OLS has no `durbin_watson`
                # attribute, and `getattr(..., None)` reported None forever (G62).
                'durbin_watson': float(durbin_watson(residuals.values)),
                'kind': 'in_sample_explanatory',
                'feature_availability': 'ex_post',
                'condition_number': float(model.condition_number),
                'target_mean': float(y.mean()),
                'target_std': float(y.std()),
                'timestamp': datetime.now().isoformat()
            }
            
            result = RegressionResult(
                target_variable='duration',
                r_squared=float(model.rsquared),
                adjusted_r_squared=float(model.rsquared_adj),
                coefficients=coefficients,
                p_values=p_values,
                predictions=predictions.values,
                residuals=residuals.values,
                n_observations=len(model_data),
                n_predictors=len(available_predictors),
                model_summary=str(model.summary()),
                metadata=metadata
            )
            
            self.logger.info(
                f"Duration model: R²={result.r_squared:.3f}, "
                f"Adj R²={result.adjusted_r_squared:.3f}, "
                f"n={result.n_observations}, "
                f"p={result.n_predictors}"
            )
            
            significant_predictors = result.get_significant_predictors(self.alpha)
            if significant_predictors:
                self.logger.info(f"Significant predictors: {list(significant_predictors.keys())}")
            
            return result
            
        except ImportError:
            self.logger.error("statsmodels not installed, cannot perform regression")
            raise StatisticalAnalysisError(
                "Regression analysis requires statsmodels. Install with: pip install statsmodels"
            )
        except Exception as e:
            self.logger.error(f"Zone duration regression failed: {e}")
            raise StatisticalAnalysisError(f"Duration regression failed: {e}")
    
    def explain_price_return(self,
                            zones_features: List[Dict[str, Any]],
                            predictors: Optional[List[str]] = None) -> RegressionResult:
        """
        Fit an **in-sample, explanatory** regression of the zone's return on its features.

        Model: price_return ~ duration + line_amplitude + correlation_price_oscillator + ...

        Every default predictor is known only when the zone is over — its
        duration, its drawdown from the peak (which contains the end price), its
        peak count, its oscillator slope — and the target is the return of that
        same zone. This explains, it does not predict; the method was called
        ``predict_price_return`` until G62.
        
        Args:
            zones_features: List of zone feature dictionaries
            predictors: List of predictor variable names. If None, uses default set.
        
        Returns:
            RegressionResult with model statistics and predictions
        """
        self.logger.info("Building price return regression model")
        
        try:
            from statsmodels.api import OLS, add_constant
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            
            df = pd.DataFrame(zones_features)
            
            # Default predictors
            if predictors is None:
                predictors = ['duration', 'line_amplitude', 'correlation_price_oscillator',
                            'drawdown_from_peak', 'oscillator_slope', 'num_peaks']
            
            # Validate target variable
            if 'price_return' not in df.columns:
                raise StatisticalAnalysisError("Missing target variable: 'price_return'")
            
            # Filter available predictors
            available_predictors = [p for p in predictors if p in df.columns]
            
            if not available_predictors:
                raise StatisticalAnalysisError(
                    f"No predictors available. Requested: {predictors}, Available columns: {df.columns.tolist()}"
                )            
            available_predictors, empty_predictors = _usable_predictors(
                df, available_predictors, self.logger
            )
            if not available_predictors:
                raise StatisticalAnalysisError(
                    f"Every requested predictor is empty for this zone set: "
                    f"{empty_predictors}. Nothing to regress on."
                )
            
            self.logger.info(f"Using predictors: {available_predictors}")
            
            # Prepare data (remove NaN)
            model_data = df[['price_return'] + available_predictors].dropna()
            
            if len(model_data) < len(available_predictors) + 2:
                raise StatisticalAnalysisError(
                    f"Insufficient data for regression: need at least {len(available_predictors) + 2} "
                    f"observations, got {len(model_data)}"
                )
            
            # Separate target and predictors
            y = model_data['price_return']
            X = model_data[available_predictors]
            
            # Add constant for intercept. `has_constant='add'` is deliberate:
            # with the default, a design whose columns are already constant gets
            # no `const` column, and the coefficient lookup below then failed
            # with a bare KeyError.
            X_with_const = add_constant(X, has_constant='add')
            _reject_degenerate_design(X_with_const, available_predictors)
            if y.nunique(dropna=True) <= 1:
                # A constant target has no variance to explain; OLS would still
                # fit and report R² = -inf (G62).
                raise StatisticalAnalysisError(
                    f"Target 'price_return' is constant across all {len(y)} observations "
                    f"(value {y.iloc[0]!r}); there is nothing to explain."
                )
            
            # Fit OLS model
            model = OLS(y, X_with_const).fit()
            
            # Extract results
            coefficients = {}
            p_values = {}
            
            coefficients['intercept'] = model.params['const']
            p_values['intercept'] = model.pvalues['const']
            
            for pred in available_predictors:
                coefficients[pred] = model.params[pred]
                p_values[pred] = model.pvalues[pred]
            
            # Predictions and residuals
            predictions = model.predict(X_with_const)
            residuals = model.resid
            
            # Calculate VIF for multicollinearity check
            vif_data = {}
            if len(available_predictors) >= 2:
                try:
                    for i, col in enumerate(available_predictors):
                        vif_data[col] = variance_inflation_factor(X.values, i)
                except Exception as e:
                    self.logger.warning(f"Could not calculate VIF: {e}")
            
            # Metadata
            metadata = {
                'available_predictors': available_predictors,
                'requested_predictors': predictors,
                'missing_predictors': [p for p in predictors if p not in df.columns],
                'empty_predictors': empty_predictors,
                'n_dropped_na': len(df) - len(model_data),
                'f_statistic': float(model.fvalue),
                'f_pvalue': float(model.f_pvalue),
                'aic': float(model.aic),
                'bic': float(model.bic),
                'vif': vif_data,
                # Computed explicitly: a fitted OLS has no `durbin_watson`
                # attribute, and `getattr(..., None)` reported None forever (G62).
                'durbin_watson': float(durbin_watson(residuals.values)),
                'kind': 'in_sample_explanatory',
                'feature_availability': 'ex_post',
                'condition_number': float(model.condition_number),
                'target_mean': float(y.mean()),
                'target_std': float(y.std()),
                'timestamp': datetime.now().isoformat()
            }
            
            result = RegressionResult(
                target_variable='price_return',
                r_squared=float(model.rsquared),
                adjusted_r_squared=float(model.rsquared_adj),
                coefficients=coefficients,
                p_values=p_values,
                predictions=predictions.values,
                residuals=residuals.values,
                n_observations=len(model_data),
                n_predictors=len(available_predictors),
                model_summary=str(model.summary()),
                metadata=metadata
            )
            
            self.logger.info(
                f"Price return model: R²={result.r_squared:.3f}, "
                f"Adj R²={result.adjusted_r_squared:.3f}, "
                f"n={result.n_observations}, "
                f"p={result.n_predictors}"
            )
            
            significant_predictors = result.get_significant_predictors(self.alpha)
            if significant_predictors:
                self.logger.info(f"Significant predictors: {list(significant_predictors.keys())}")
            
            return result
            
        except ImportError:
            self.logger.error("statsmodels not installed, cannot perform regression")
            raise StatisticalAnalysisError(
                "Regression analysis requires statsmodels. Install with: pip install statsmodels"
            )
        except Exception as e:
            self.logger.error(f"Price return regression failed: {e}")
            raise StatisticalAnalysisError(f"Price return regression failed: {e}")


# Export
__all__ = [
    'RegressionResult',
    'ZoneRegressionAnalyzer'
]

