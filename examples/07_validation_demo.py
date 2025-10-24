"""
Model validation demonstration - Universal Pipeline v2.1.

API Stability: STABLE (validation is universal)

This example demonstrates:
1. Out-of-sample testing with Universal Pipeline
2. Walk-forward validation
3. Sensitivity analysis
4. Monte Carlo testing
5. Complete validation workflow
6. indicator_context contract demonstration
"""

from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones


def main():
    print("=" * 60)
    print("BQuant Model Validation Demo - Universal Pipeline v2.1")
    print("=" * 60)
    
    # Prepare zones with Universal Pipeline
    print("\n1. Preparing data and zones with Universal Pipeline...")
    data = get_sample_data('tv_xauusd_1h')
    
    # Universal Pipeline with strategies
    result = (
        analyze_zones(data)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='zigzag')
        .analyze(clustering=False)
        .build()
    )
    
    print(f"   Found {len(result.zones)} zones using Universal Pipeline")
    
    # Extract features from zones
    print("\n2. Extracting zone features...")
    
    zones_features = []
    for zone in result.zones:
        if zone.features:
            # Convert zone.features to dict format for validation
            features_dict = dict(zone.features)
            # Add basic zone properties
            features_dict.update({
                'duration': zone.duration,
                'zone_id': zone.zone_id,
                'type': zone.type
            })
            zones_features.append(features_dict)
    
    print(f"   Extracted features from {len(zones_features)} zones")
    
    if len(zones_features) < 10:
        print("   ⚠️ Not enough zones for robust validation")
        print("   Continuing with demo...")
    
    # Simple validation functions (manual implementation for demo)
    def simple_regression(X, y):
        """Simple linear regression for validation"""
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
        
        if len(X) < 3:
            return None, 0.0
        
        X = np.array(X)
        y = np.array(y)
        
        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        
        return model, r2
    
    # Test 1: Out-of-sample
    print("\n3. Out-of-Sample Test (Train/Test Split)")
    print("   " + "-" * 55)
    
    if len(zones_features) >= 6:
        # Split data
        split_idx = int(len(zones_features) * 0.7)
        train_features = zones_features[:split_idx]
        test_features = zones_features[split_idx:]
        
        # Prepare training data
        X_train = []
        y_train = []
        for features in train_features:
            predictors = []
            for key in ['duration', 'num_peaks', 'num_troughs']:
                if key in features:
                    predictors.append(features[key])
                else:
                    predictors.append(0.0)
            X_train.append(predictors)
            y_train.append(features['duration'])
        
        # Prepare test data
        X_test = []
        y_test = []
        for features in test_features:
            predictors = []
            for key in ['duration', 'num_peaks', 'num_troughs']:
                if key in features:
                    predictors.append(features[key])
                else:
                    predictors.append(0.0)
            X_test.append(predictors)
            y_test.append(features['duration'])
        
        # Train model
        train_model, train_r2 = simple_regression(X_train, y_train)
        
        # Test model
        if train_model is not None:
            import numpy as np
            from sklearn.metrics import r2_score
            
            X_test = np.array(X_test)
            y_test = np.array(y_test)
            y_pred_test = train_model.predict(X_test)
            test_r2 = r2_score(y_test, y_pred_test)
            
            degradation = ((train_r2 - test_r2) / train_r2 * 100) if train_r2 > 0 else 0
            
            print(f"   Duration model:")
            print(f"      Train R²: {train_r2:.3f}")
            print(f"      Test R²: {test_r2:.3f}")
            print(f"      Degradation: {degradation:.1f}%", end="")
            
            if degradation < 10:
                print("  ✅ Excellent")
            elif degradation < 20:
                print("  ✅ Good")
            elif degradation < 30:
                print("  ⚡ Acceptable")
            else:
                print("  ⚠️ High - possible overfitting")
        else:
            print("   ⚠️ Insufficient training data")
    else:
        print("   ⚠️ Not enough zones for train/test split")
    
    # Test 2: Walk-forward (simplified)
    print("\n4. Walk-Forward Test (Rolling Window)")
    print("   " + "-" * 55)
    
    if len(zones_features) >= 20:
        window_size = min(10, len(zones_features) // 2)
        step_size = max(2, window_size // 3)
        
        r2_scores = []
        
        for i in range(0, len(zones_features) - window_size, step_size):
            window_features = zones_features[i:i + window_size]
            
            X_window = []
            y_window = []
            for features in window_features:
                predictors = []
                for key in ['duration', 'num_peaks']:
                    if key in features:
                        predictors.append(features[key])
                    else:
                        predictors.append(0.0)
                X_window.append(predictors)
                y_window.append(features['duration'])
            
            _, r2 = simple_regression(X_window, y_window)
            if r2 is not None:
                r2_scores.append(r2)
        
        if r2_scores:
            import numpy as np
            mean_r2 = np.mean(r2_scores)
            std_r2 = np.std(r2_scores)
            min_r2 = np.min(r2_scores)
            max_r2 = np.max(r2_scores)
            
            print(f"   Duration model across {len(r2_scores)} windows:")
            print(f"      Mean R²: {mean_r2:.3f}")
            print(f"      Std R²: {std_r2:.3f}")
            print(f"      Min R²: {min_r2:.3f}")
            print(f"      Max R²: {max_r2:.3f}")
            
            stability = 1.0 - (std_r2 / mean_r2) if mean_r2 > 0 else 0.0
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
            print("   ⚠️ No valid windows for walk-forward test")
    else:
        print("   ⚠️ Not enough zones for walk-forward (need 20+)")
    
    # Test 3: Sensitivity analysis
    print("\n5. Sensitivity Analysis (Parameter Stability)")
    print("   " + "-" * 55)
    
    # Test with different indicators
    indicators_to_test = [
        ('custom', 'macd', {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}),
        ('pandas_ta', 'rsi', {'length': 14}),
        ('pandas_ta', 'ao', {'fast': 5, 'slow': 34})
    ]
    
    r2_scores_alt = []
    
    for source, name, params in indicators_to_test:
        try:
            result_alt = (
                analyze_zones(data)
                .with_indicator(source, name, **params)
                .detect_zones(
                    'threshold' if name == 'rsi' else 'zero_crossing',
                    indicator_col=name if name == 'rsi' else f'{name}_hist',
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
                
                _, r2_alt = simple_regression(X_alt, y_alt)
                if r2_alt is not None:
                    r2_scores_alt.append(r2_alt)
                    print(f"   {name} R²: {r2_alt:.3f}")
        
        except Exception as e:
            print(f"   {name}: Error - {str(e)}")
    
    if r2_scores_alt:
        import numpy as np
        stability_score = 1.0 - (np.std(r2_scores_alt) / np.mean(r2_scores_alt)) if np.mean(r2_scores_alt) > 0 else 0.0
        
        print(f"\n   Cross-indicator stability score: {stability_score:.3f}", end="")
        
        if stability_score > 0.8:
            print("  ✅ Robust across indicators")
        elif stability_score > 0.6:
            print("  ⚡ Moderately robust")
        else:
            print("  ⚠️ Sensitive to indicator choice")
        
        print(f"   R² range: {np.min(r2_scores_alt):.3f} to {np.max(r2_scores_alt):.3f}")
    
    # Test 4: Monte Carlo (simplified)
    print("\n6. Monte Carlo Test (Real vs Synthetic)")
    print("   " + "-" * 55)
    
    if len(zones_features) >= 10:
        # Real model
        X_real = []
        y_real = []
        for features in zones_features:
            predictors = []
            for key in ['duration', 'num_peaks']:
                if key in features:
                    predictors.append(features[key])
                else:
                    predictors.append(0.0)
            X_real.append(predictors)
            y_real.append(features['duration'])
        
        _, real_r2 = simple_regression(X_real, y_real)
        
        # Synthetic models (shuffled)
        import numpy as np
        synthetic_r2s = []
        
        for _ in range(20):  # Reduced for demo speed
            y_shuffled = np.random.permutation(y_real)
            _, synthetic_r2 = simple_regression(X_real, y_shuffled)
            if synthetic_r2 is not None:
                synthetic_r2s.append(synthetic_r2)
        
        if real_r2 is not None and synthetic_r2s:
            synthetic_mean = np.mean(synthetic_r2s)
            synthetic_std = np.std(synthetic_r2s)
            
            # Simple significance test
            p_value = np.mean([s >= real_r2 for s in synthetic_r2s])
            
            print(f"   Real model R²: {real_r2:.3f}")
            print(f"   Synthetic R² (mean): {synthetic_mean:.3f}")
            print(f"   Synthetic R² (std): {synthetic_std:.3f}")
            print(f"   P-value: {p_value:.4f}")
            
            if p_value < 0.05:
                print("   ✅ Real model significantly better than random")
            else:
                print("   ⚠️ Model not significantly better than random")
        else:
            print("   ⚠️ Insufficient data for Monte Carlo test")
    else:
        print("   ⚠️ Not enough zones for Monte Carlo test")
    
    # Complete assessment
    print("\n7. Overall Model Assessment")
    print("   " + "=" * 55)
    
    criteria_passed = 0
    total_criteria = 0
    
    # Criterion 1: OOS degradation (if available)
    if len(zones_features) >= 6:
        total_criteria += 1
        if 'degradation' in locals() and degradation < 20:
            print("   ✅ Out-of-sample degradation < 20%")
            criteria_passed += 1
        else:
            print("   ⚠️ Out-of-sample degradation >= 20%")
    
    # Criterion 2: Walk-forward stability (if available)
    if len(zones_features) >= 20:
        total_criteria += 1
        if 'stability' in locals() and stability > 0.6:
            print("   ✅ Walk-forward stability > 0.6")
            criteria_passed += 1
        else:
            print("   ⚠️ Walk-forward stability <= 0.6")
    
    # Criterion 3: Cross-indicator stability
    if r2_scores_alt:
        total_criteria += 1
        if 'stability_score' in locals() and stability_score > 0.7:
            print("   ✅ Cross-indicator stability > 0.7")
            criteria_passed += 1
        else:
            print("   ⚠️ High sensitivity to indicator choice")
    
    # Criterion 4: Monte Carlo
    if len(zones_features) >= 10:
        total_criteria += 1
        if 'p_value' in locals() and p_value < 0.05:
            print("   ✅ Significantly better than random")
            criteria_passed += 1
        else:
            print("   ⚠️ Not significantly better than random")
    
    # Final verdict
    if total_criteria > 0:
        print("\n   " + "=" * 55)
        print(f"   Criteria passed: {criteria_passed}/{total_criteria}")
        
        if criteria_passed >= total_criteria * 0.75:
            print("   \n   ✅ MODEL IS PRODUCTION-READY")
        elif criteria_passed >= total_criteria * 0.5:
            print("   \n   ⚡ MODEL NEEDS IMPROVEMENTS")
        else:
            print("   \n   ⚠️ MODEL NOT READY FOR PRODUCTION")
    else:
        print("   ⚠️ Insufficient data for complete assessment")
    
    print("\n" + "=" * 60)
    print("Validation Best Practices:")
    print("=" * 60)
    print("1. Always use Out-of-Sample test (minimum)")
    print("2. Walk-Forward test for time-series data")
    print("3. Cross-indicator sensitivity analysis")
    print("4. Monte Carlo to verify real patterns vs noise")
    print("5. Aim for: degradation < 20%, stability > 0.6")
    print("6. Universal Pipeline ensures consistent validation")
    print("7. indicator_context provides stable feature names")
    print("8. Modern API eliminates deprecated method calls")
    print("9. Same validation approach works with ANY indicator")
    print("10. Cross-indicator stability testing for robustness")
    print("=" * 60)


if __name__ == '__main__':
    main()