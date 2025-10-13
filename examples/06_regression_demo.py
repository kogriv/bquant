"""
Regression analysis demonstration.

API Stability: STABLE (regression is universal)

This example demonstrates:
1. Building regression models for zone duration and price return
2. Interpreting model diagnostics (R², VIF, AIC, BIC)
3. Using custom predictors
4. Model quality assessment
"""

from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer
from bquant.analysis.statistical import ZoneRegressionAnalyzer
from bquant.analysis.zones import ZoneFeaturesAnalyzer


def main():
    print("=" * 60)
    print("BQuant Regression Analysis Demo")
    print("=" * 60)
    
    # Prepare zones
    print("\n1. Preparing data and zones...")
    data = get_sample_data('tv_xauusd_1h')
    analyzer = MACDZoneAnalyzer()
    result = analyzer.analyze_complete(data, perform_clustering=False)
    print(f"   Found {len(result.zones)} zones")
    
    # Extract features with strategies
    print("\n2. Extracting zone features...")
    features_analyzer = ZoneFeaturesAnalyzer(
        swing_strategy='zigzag',
        shape_strategy='statistical',
        volatility_strategy='combined'
    )
    
    zones_features = []
    for zone in result.zones:
        zone_dict = analyzer._zone_to_dict(zone)
        features = features_analyzer.extract_zone_features(zone_dict)
        zones_features.append(features)
    
    print(f"   Extracted features from {len(zones_features)} zones")
    
    # Regression analysis
    print("\n3. Building regression models...")
    regressor = ZoneRegressionAnalyzer()
    
    # Model 1: Predict zone duration
    print("\n   Model 1: Zone Duration")
    print("   " + "-" * 55)
    
    duration_model = regressor.predict_zone_duration(
        zones_features,
        predictors=['macd_amplitude', 'hist_amplitude', 'price_range_pct']
    )
    
    print(f"   R²: {duration_model.r_squared:.3f}")
    print(f"   Adjusted R²: {duration_model.adjusted_r_squared:.3f}")
    
    print("\n   Coefficients (significance):")
    for predictor, coef in duration_model.coefficients.items():
        p_val = duration_model.p_values[predictor]
        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
        print(f"      {predictor:<25}: {coef:>8.4f} ({sig})")
    
    print("\n   Diagnostics:")
    print(f"      AIC: {duration_model.diagnostics['aic']:.1f}")
    print(f"      BIC: {duration_model.diagnostics['bic']:.1f}")
    print(f"      F-statistic: {duration_model.diagnostics['f_statistic']:.2f}")
    print(f"      Durbin-Watson: {duration_model.diagnostics['durbin_watson']:.2f}")
    
    print("\n   Multicollinearity (VIF):")
    for predictor, vif in duration_model.diagnostics['vif'].items():
        status = "⚠️ HIGH" if vif > 10 else "✅ OK" if vif < 5 else "⚡ MODERATE"
        print(f"      {predictor:<25}: {vif:>6.2f}  {status}")
    
    # Model 2: Predict price return
    print("\n   Model 2: Price Return")
    print("   " + "-" * 55)
    
    return_model = regressor.predict_price_return(
        zones_features,
        predictors=['duration', 'macd_amplitude', 'num_peaks']
    )
    
    print(f"   R²: {return_model.r_squared:.3f}")
    print(f"   Adjusted R²: {return_model.adjusted_r_squared:.3f}")
    
    print("\n   Coefficients (significance):")
    for predictor, coef in return_model.coefficients.items():
        p_val = return_model.p_values[predictor]
        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
        print(f"      {predictor:<25}: {coef:>8.4f} ({sig})")
    
    # Model quality assessment
    print("\n4. Model Quality Assessment")
    print("   " + "-" * 55)
    
    print("\n   Duration Model:")
    if duration_model.r_squared > 0.7:
        print("      ✅ Strong model (R² > 0.7)")
    elif duration_model.r_squared > 0.3:
        print("      ⚡ Moderate model (0.3 < R² < 0.7)")
    else:
        print("      ⚠️ Weak model (R² < 0.3)")
    
    vif_issues = sum(1 for vif in duration_model.diagnostics['vif'].values() if vif > 10)
    if vif_issues == 0:
        print("      ✅ No multicollinearity issues")
    else:
        print(f"      ⚠️ {vif_issues} predictor(s) with high VIF")
    
    dw = duration_model.diagnostics['durbin_watson']
    if 1.5 < dw < 2.5:
        print("      ✅ No autocorrelation (DW ~2.0)")
    else:
        print(f"      ⚠️ Potential autocorrelation (DW = {dw:.2f})")
    
    print("\n   Return Model:")
    if return_model.r_squared > 0.7:
        print("      ✅ Strong model")
    elif return_model.r_squared > 0.3:
        print("      ⚡ Moderate model")
    else:
        print("      ⚠️ Weak model")
    
    # Custom predictors example
    print("\n5. Using custom predictors (with strategy metrics)...")
    
    # Need to extract features from zone that has metadata
    if hasattr(zones_features[0], 'metadata') and zones_features[0].metadata:
        # Check if swing metrics available
        has_swing = any(hasattr(f, 'metadata') and f.metadata and 'swing_metrics' in f.metadata 
                       for f in zones_features[:5])
        
        if has_swing:
            custom_model = regressor.predict_zone_duration(
                zones_features,
                predictors=['duration', 'price_range_pct', 'num_peaks', 'num_troughs']
            )
            
            print(f"   Custom model R²: {custom_model.r_squared:.3f}")
            print("   ✅ Can use metrics from any strategy as predictors!")
        else:
            print("   ⚠️ Swing metrics not available in features")
    
    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("=" * 60)
    print("1. Regression models can predict zone characteristics")
    print("2. Check R², VIF, and Durbin-Watson for model quality")
    print("3. Can use any feature as predictor (base + strategy metrics)")
    print("4. Lower AIC/BIC indicates better model fit")
    print("5. Combine with validation (see example 07) for robustness")
    print("=" * 60)


if __name__ == '__main__':
    main()

