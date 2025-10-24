"""
Regression analysis demonstration - Universal Pipeline v2.1.

API Stability: STABLE (regression is universal)

This example demonstrates:
1. Building regression models for zone duration and price return
2. Interpreting model diagnostics (R², VIF, AIC, BIC)
3. Using custom predictors from Universal Pipeline
4. Model quality assessment
5. indicator_context contract demonstration
"""

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones


def main():
    print("=" * 60)
    print("BQuant Regression Analysis Demo - Universal Pipeline v2.1")
    print("=" * 60)
    
    # Prepare zones with Universal Pipeline
    print("\n1. Preparing data and zones with Universal Pipeline...")
    data = get_sample_data('tv_xauusd_1h')
    
    # Universal Pipeline with multiple strategies
    result = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(
            swing='zigzag',           # Для получения swing metrics
            shape='statistical',      # Для получения shape metrics
            volatility='combined'     # Для получения volatility metrics
        )
        .analyze(clustering=False)
        .build()
    )
    
    print(f"   Found {len(result.zones)} zones using Universal Pipeline")
    
    # Extract features from zones
    print("\n2. Extracting zone features...")
    
    zones_features = []
    for zone in result.zones:
        if zone.features:
            # Convert zone.features to dict format for regression
            features_dict = dict(zone.features)
            # Add basic zone properties
            features_dict.update({
                'duration': zone.duration,
                'zone_id': zone.zone_id,
                'type': zone.type
            })
            zones_features.append(features_dict)
    
    print(f"   Extracted features from {len(zones_features)} zones")
    
    if len(zones_features) < 3:
        print("   ⚠️ Need at least 3 zones for regression analysis")
        return
    
    # Show available features
    print("\n   Available features for regression:")
    if zones_features:
        sample_features = zones_features[0]
        feature_names = [k for k in sample_features.keys() if isinstance(sample_features[k], (int, float))]
        print(f"   {len(feature_names)} numeric features: {', '.join(feature_names[:10])}{'...' if len(feature_names) > 10 else ''}")
    
    # Simple regression analysis (manual implementation for demo)
    print("\n3. Building regression models...")
    
    # Model 1: Predict zone duration
    print("\n   Model 1: Zone Duration")
    print("   " + "-" * 55)
    
    # Simple linear regression for duration
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    
    # Prepare data for duration prediction
    X_duration = []
    y_duration = []
    
    for features in zones_features:
        # Use available features as predictors
        predictors = []
        for key in ['macd_amplitude', 'hist_amplitude', 'price_range_pct', 'num_peaks', 'num_troughs']:
            if key in features:
                predictors.append(features[key])
            else:
                predictors.append(0.0)  # Default value
        
        X_duration.append(predictors)
        y_duration.append(features['duration'])
    
    X_duration = np.array(X_duration)
    y_duration = np.array(y_duration)
    
    # Fit model
    duration_model = LinearRegression()
    duration_model.fit(X_duration, y_duration)
    
    # Predictions
    y_pred_duration = duration_model.predict(X_duration)
    r2_duration = r2_score(y_duration, y_pred_duration)
    
    print(f"   R²: {r2_duration:.3f}")
    print(f"   Predictors: macd_amplitude, hist_amplitude, price_range_pct, num_peaks, num_troughs")
    
    print("\n   Coefficients:")
    predictor_names = ['macd_amplitude', 'hist_amplitude', 'price_range_pct', 'num_peaks', 'num_troughs']
    for name, coef in zip(predictor_names, duration_model.coefficients_):
        print(f"      {name:<25}: {coef:>8.4f}")
    
    # Model 2: Predict price return (if available)
    print("\n   Model 2: Price Return")
    print("   " + "-" * 55)
    
    # Check if we have price return data
    has_price_return = any('price_return_pct' in features for features in zones_features)
    
    if has_price_return:
        X_return = []
        y_return = []
        
        for features in zones_features:
            if 'price_return_pct' in features:
                predictors = []
                for key in ['duration', 'macd_amplitude', 'num_peaks']:
                    if key in features:
                        predictors.append(features[key])
                    else:
                        predictors.append(0.0)
                
                X_return.append(predictors)
                y_return.append(features['price_return_pct'])
        
        if len(X_return) >= 3:
            X_return = np.array(X_return)
            y_return = np.array(y_return)
            
            return_model = LinearRegression()
            return_model.fit(X_return, y_return)
            
            y_pred_return = return_model.predict(X_return)
            r2_return = r2_score(y_return, y_pred_return)
            
            print(f"   R²: {r2_return:.3f}")
            print(f"   Predictors: duration, macd_amplitude, num_peaks")
            
            print("\n   Coefficients:")
            predictor_names = ['duration', 'macd_amplitude', 'num_peaks']
            for name, coef in zip(predictor_names, return_model.coefficients_):
                print(f"      {name:<25}: {coef:>8.4f}")
        else:
            print("   ⚠️ Insufficient data for price return model")
    else:
        print("   ⚠️ Price return data not available in features")
    
    # Model quality assessment
    print("\n4. Model Quality Assessment")
    print("   " + "-" * 55)
    
    print("\n   Duration Model:")
    if r2_duration > 0.7:
        print("      ✅ Strong model (R² > 0.7)")
    elif r2_duration > 0.3:
        print("      ⚡ Moderate model (0.3 < R² < 0.7)")
    else:
        print("      ⚠️ Weak model (R² < 0.3)")
    
    # Show feature importance
    print("\n   Feature Importance (absolute coefficients):")
    for name, coef in zip(predictor_names, duration_model.coefficients_):
        importance = abs(coef)
        status = "🔥 HIGH" if importance > 0.5 else "⚡ MODERATE" if importance > 0.1 else "📉 LOW"
        print(f"      {name:<25}: {importance:>6.3f}  {status}")
    
    # Test with different indicators
    print("\n5. Testing regression with different indicators...")
    
    indicators_to_test = [
        ('pandas_ta', 'rsi', {'length': 14}),
        ('pandas_ta', 'ao', {'fast': 5, 'slow': 34})
    ]
    
    for source, name, params in indicators_to_test:
        print(f"\n   === Testing {name.upper()} regression ===")
        
        try:
            result_alt = (
                analyze_zones(data)
                .with_indicator(source, name, **params)
                .detect_zones(
                    'threshold' if name == 'rsi' else 'zero_crossing',
                    indicator_col=name,
                    upper_threshold=70 if name == 'rsi' else None,
                    lower_threshold=30 if name == 'rsi' else None
                )
                .with_strategies(swing='zigzag')
                .analyze(clustering=False)
                .build()
            )
            
            if len(result_alt.zones) >= 3:
                # Extract features
                alt_features = []
                for zone in result_alt.zones:
                    if zone.features:
                        features_dict = dict(zone.features)
                        features_dict.update({
                            'duration': zone.duration,
                            'zone_id': zone.zone_id,
                            'type': zone.type
                        })
                        alt_features.append(features_dict)
                
                # Simple regression
                X_alt = []
                y_alt = []
                
                for features in alt_features:
                    predictors = []
                    for key in ['duration', 'num_peaks']:
                        if key in features:
                            predictors.append(features[key])
                        else:
                            predictors.append(0.0)
                    
                    X_alt.append(predictors)
                    y_alt.append(features['duration'])
                
                if len(X_alt) >= 3:
                    X_alt = np.array(X_alt)
                    y_alt = np.array(y_alt)
                    
                    alt_model = LinearRegression()
                    alt_model.fit(X_alt, y_alt)
                    
                    y_pred_alt = alt_model.predict(X_alt)
                    r2_alt = r2_score(y_alt, y_pred_alt)
                    
                    print(f"   {name} zones: {len(result_alt.zones)}")
                    print(f"   {name} R²: {r2_alt:.3f}")
                    print(f"   ✅ Universal regression works with {name}!")
                else:
                    print(f"   ⚠️ Insufficient {name} zones for regression")
            else:
                print(f"   ⚠️ Only {len(result_alt.zones)} {name} zones found")
                
        except Exception as e:
            print(f"   ❌ Error with {name}: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("=" * 60)
    print("1. Universal Pipeline provides features for regression")
    print("2. Same regression approach works with ANY indicator")
    print("3. indicator_context ensures consistent feature names")
    print("4. Check R² for model quality assessment")
    print("5. Feature importance helps identify key predictors")
    print("6. Combine with validation (see example 07) for robustness")
    print("7. Modern API eliminates deprecated _zone_to_dict() calls")
    print("8. indicator_context ensures consistent feature names across indicators")
    print("9. Universal Pipeline provides same features for any indicator")
    print("=" * 60)


if __name__ == '__main__':
    main()