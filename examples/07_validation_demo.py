"""
Model validation demonstration.

API Stability: STABLE (validation is universal)

This example demonstrates:
1. Out-of-sample testing
2. Walk-forward validation
3. Sensitivity analysis
4. Monte Carlo testing
5. Complete validation workflow
"""

from bquant.data.samples import get_sample_data
from bquant.indicators.macd import MACDZoneAnalyzer
from bquant.analysis.validation import ValidationSuite
from bquant.analysis.zones import ZoneFeaturesAnalyzer


def main():
    print("=" * 60)
    print("BQuant Model Validation Demo")
    print("=" * 60)
    
    # Prepare zones
    print("\n1. Preparing data and zones...")
    data = get_sample_data('tv_xauusd_1h')
    analyzer = MACDZoneAnalyzer()
    result = analyzer.analyze_complete(data, perform_clustering=False)
    print(f"   Found {len(result.zones)} zones")
    
    # Extract features
    print("\n2. Extracting zone features...")
    features_analyzer = ZoneFeaturesAnalyzer(swing_strategy='zigzag')
    
    zones_features = []
    for zone in result.zones:
        zone_dict = analyzer._zone_to_dict(zone)
        features = features_analyzer.extract_zone_features(zone_dict)
        zones_features.append(features)
    
    print(f"   Extracted features from {len(zones_features)} zones")
    
    if len(zones_features) < 30:
        print("   ⚠️ Not enough zones for robust validation")
        print("   Continuing with demo...")
    
    # Validation suite
    validator = ValidationSuite()
    
    # Test 1: Out-of-sample
    print("\n3. Out-of-Sample Test (Train/Test Split)")
    print("   " + "-" * 55)
    
    oos = validator.out_of_sample_test(
        zones_features,
        test_size=0.3,
        metrics=['duration', 'price_return']
    )
    
    print(f"   Duration:")
    print(f"      Train R²: {oos.metrics.get('duration_train_r2', 0):.3f}")
    print(f"      Test R²: {oos.metrics.get('duration_test_r2', 0):.3f}")
    degradation_dur = oos.metrics.get('duration_degradation_pct', 0)
    print(f"      Degradation: {degradation_dur:.1f}%", end="")
    
    if degradation_dur < 10:
        print("  ✅ Excellent")
    elif degradation_dur < 20:
        print("  ✅ Good")
    elif degradation_dur < 30:
        print("  ⚡ Acceptable")
    else:
        print("  ⚠️ High - possible overfitting")
    
    print(f"\n   Price Return:")
    print(f"      Train R²: {oos.metrics.get('price_return_train_r2', 0):.3f}")
    print(f"      Test R²: {oos.metrics.get('price_return_test_r2', 0):.3f}")
    degradation_ret = oos.metrics.get('price_return_degradation_pct', 0)
    print(f"      Degradation: {degradation_ret:.1f}%", end="")
    
    if degradation_ret < 10:
        print("  ✅ Excellent")
    elif degradation_ret < 20:
        print("  ✅ Good")
    elif degradation_ret < 30:
        print("  ⚡ Acceptable")
    else:
        print("  ⚠️ High - possible overfitting")
    
    # Test 2: Walk-forward
    print("\n4. Walk-Forward Test (Rolling Window)")
    print("   " + "-" * 55)
    
    if len(zones_features) >= 50:
        wf = validator.walk_forward_test(
            zones_features,
            window_size=30,
            step_size=10,
            metrics=['duration']
        )
        
        print(f"   Duration model across windows:")
        print(f"      Mean R²: {wf.metrics.get('duration_mean_r2', 0):.3f}")
        print(f"      Std R²: {wf.metrics.get('duration_std_r2', 0):.3f}")
        print(f"      Min R²: {wf.metrics.get('duration_min_r2', 0):.3f}")
        print(f"      Max R²: {wf.metrics.get('duration_max_r2', 0):.3f}")
        
        stability = wf.metrics.get('duration_stability_score', 0)
        print(f"      Stability score: {stability:.3f}", end="")
        
        if stability > 0.8:
            print("  ✅ Very stable")
        elif stability > 0.6:
            print("  ✅ Acceptably stable")
        elif stability > 0.4:
            print("  ⚡ Moderately stable")
        else:
            print("  ⚠️ Unstable")
    else:
        print("   ⚠️ Not enough zones for walk-forward (need 50+)")
    
    # Test 3: Sensitivity analysis
    print("\n5. Sensitivity Analysis (Parameter Stability)")
    print("   " + "-" * 55)
    
    sens = validator.sensitivity_analysis(
        zones_features,
        param_grid={
            'min_duration': [2, 5, 10]
        },
        metric='duration'
    )
    
    print(f"   Stability score: {sens.metrics.get('stability_score', 0):.3f}", end="")
    
    stability = sens.metrics.get('stability_score', 0)
    if stability > 0.8:
        print("  ✅ Robust to parameter changes")
    elif stability > 0.6:
        print("  ⚡ Moderately sensitive")
    else:
        print("  ⚠️ Highly sensitive to parameters")
    
    print(f"   R² range: {sens.metrics.get('r2_min', 0):.3f} to {sens.metrics.get('r2_max', 0):.3f}")
    
    if 'best_params' in sens.metadata:
        print(f"   Best params: {sens.metadata['best_params']}")
    
    # Test 4: Monte Carlo
    print("\n6. Monte Carlo Test (Real vs Synthetic)")
    print("   " + "-" * 55)
    
    mc = validator.monte_carlo_test(
        zones_features,
        n_simulations=50,  # Reduced for demo speed
        shuffle_method='bootstrap',
        metric='duration'
    )
    
    print(f"   Real model R²: {mc.metrics.get('real_mean', 0):.3f}")
    print(f"   Synthetic R² (mean): {mc.metrics.get('synthetic_mean', 0):.3f}")
    print(f"   Synthetic R² (std): {mc.metrics.get('synthetic_std', 0):.3f}")
    print(f"   P-value: {mc.metrics.get('p_value', 1):.4f}")
    
    if mc.success:
        print("   ✅ Real model significantly better than random")
    else:
        print("   ⚠️ Model not significantly better than random")
    
    # Complete assessment
    print("\n7. Overall Model Assessment")
    print("   " + "=" * 55)
    
    criteria_passed = 0
    total_criteria = 0
    
    # Criterion 1: OOS degradation
    total_criteria += 1
    if degradation_dur < 20:
        print("   ✅ Out-of-sample degradation < 20%")
        criteria_passed += 1
    else:
        print("   ⚠️ Out-of-sample degradation >= 20%")
    
    # Criterion 2: Walk-forward stability (if available)
    if len(zones_features) >= 50:
        total_criteria += 1
        if wf.metrics.get('duration_stability_score', 0) > 0.6:
            print("   ✅ Walk-forward stability > 0.6")
            criteria_passed += 1
        else:
            print("   ⚠️ Walk-forward stability <= 0.6")
    
    # Criterion 3: Sensitivity
    total_criteria += 1
    if sens.metrics.get('stability_score', 0) > 0.7:
        print("   ✅ Parameter sensitivity < 0.3")
        criteria_passed += 1
    else:
        print("   ⚠️ High parameter sensitivity")
    
    # Criterion 4: Monte Carlo
    total_criteria += 1
    if mc.success:
        print("   ✅ Significantly better than random")
        criteria_passed += 1
    else:
        print("   ⚠️ Not significantly better than random")
    
    # Final verdict
    print("\n   " + "=" * 55)
    print(f"   Criteria passed: {criteria_passed}/{total_criteria}")
    
    if criteria_passed >= total_criteria * 0.75:
        print("   \n   ✅ MODEL IS PRODUCTION-READY")
    elif criteria_passed >= total_criteria * 0.5:
        print("   \n   ⚡ MODEL NEEDS IMPROVEMENTS")
    else:
        print("   \n   ⚠️ MODEL NOT READY FOR PRODUCTION")
    
    print("\n" + "=" * 60)
    print("Validation Best Practices:")
    print("=" * 60)
    print("1. Always use Out-of-Sample test (minimum)")
    print("2. Walk-Forward test for time-series data")
    print("3. Sensitivity analysis to ensure parameter robustness")
    print("4. Monte Carlo to verify real patterns vs noise")
    print("5. Aim for: degradation < 20%, stability > 0.6")
    print("=" * 60)


if __name__ == '__main__':
    main()

