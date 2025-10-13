"""
Regression analysis module for zone prediction models.

Provides tools for building regression models to predict zone characteristics
such as duration and price returns based on zone features.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ...core.logging_config import get_logger
from ...core.exceptions import StatisticalAnalysisError
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
    
    def predict_zone_duration(self,
                             zones_features: List[Dict[str, Any]],
                             predictors: Optional[List[str]] = None) -> RegressionResult:
        """
        Build regression model to predict zone duration.
        
        Model: duration ~ macd_amplitude + hist_amplitude + correlation_price_hist + ...
        
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
                predictors = ['macd_amplitude', 'hist_amplitude', 'correlation_price_hist', 
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
            
            # Add constant for intercept
            X_with_const = add_constant(X)
            
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
                'n_dropped_na': len(df) - len(model_data),
                'f_statistic': float(model.fvalue),
                'f_pvalue': float(model.f_pvalue),
                'aic': float(model.aic),
                'bic': float(model.bic),
                'vif': vif_data,
                'durbin_watson': float(model.durbin_watson) if hasattr(model, 'durbin_watson') else None,
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
    
    def predict_price_return(self,
                            zones_features: List[Dict[str, Any]],
                            predictors: Optional[List[str]] = None) -> RegressionResult:
        """
        Build regression model to predict price return.
        
        Model: price_return ~ duration + macd_amplitude + correlation_price_hist + ...
        
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
                predictors = ['duration', 'macd_amplitude', 'correlation_price_hist',
                            'drawdown_from_peak', 'hist_slope', 'num_peaks']
            
            # Validate target variable
            if 'price_return' not in df.columns:
                raise StatisticalAnalysisError("Missing target variable: 'price_return'")
            
            # Filter available predictors
            available_predictors = [p for p in predictors if p in df.columns]
            
            if not available_predictors:
                raise StatisticalAnalysisError(
                    f"No predictors available. Requested: {predictors}, Available columns: {df.columns.tolist()}"
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
            
            # Add constant for intercept
            X_with_const = add_constant(X)
            
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
                'n_dropped_na': len(df) - len(model_data),
                'f_statistic': float(model.fvalue),
                'f_pvalue': float(model.f_pvalue),
                'aic': float(model.aic),
                'bic': float(model.bic),
                'vif': vif_data,
                'durbin_watson': float(model.durbin_watson) if hasattr(model, 'durbin_watson') else None,
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

